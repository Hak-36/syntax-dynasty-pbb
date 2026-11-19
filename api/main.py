import asyncio
import json
import logging
import os
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from api.models import GenerateRequest, GenerateResponse, Source

load_dotenv()
BASE_DIR = Path(__file__).resolve().parent.parent
MOCK_MODE = os.getenv("MOCK_MODE", "1") == "1"
TIMEOUT_SECONDS = float(os.getenv("REQUEST_TIMEOUT", "60"))
CACHE_TTL_SECONDS = 600

# --- pipeline imports: real if available, else stubs ---
def _load_pipeline():
    if MOCK_MODE:
        from api.stubs import research, synthesize
        return research, synthesize, True

    try:
        from research.pipeline import research  # real Tavily research
        from ai_core.synthesize import synthesize  # real LLM synthesis
        return research, synthesize, False
    except Exception as exc:
        logger.warning("Real pipeline import failed (%r); falling back to stubs.", exc)
        from api.stubs import research, synthesize
        return research, synthesize, True

logger = logging.getLogger("briefing")  # move this up before _load_pipeline
research, synthesize, USING_STUBS = _load_pipeline()

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("briefing")

app = FastAPI(title="Pre-Meeting Briefing Agent")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # fine for a hackathon demo
    allow_methods=["*"],
    allow_headers=["*"],
)

_cache = {}  # key -> (time_saved, GenerateResponse)


@app.exception_handler(StarletteHTTPException)
async def http_error(request: Request, exc: StarletteHTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"status": exc.status_code, "message": str(exc.detail)}},
    )


def parse_iso(value: str) -> datetime:
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="meeting_time must be an ISO date-time, e.g. 2026-11-20T15:00:00Z",
        )
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def run_pipeline(req: GenerateRequest):
    """Runs in a worker thread so we can put a timeout around it."""
    t = time.perf_counter()
    results = research(req.name, req.entity_type, req.meeting_time, days=30)
    research_s = time.perf_counter() - t

    t = time.perf_counter()
    draft = synthesize(req.name, req.entity_type, req.meeting_type, results, meeting_time=req.meeting_time)
    synth_s = time.perf_counter() - t
    return results, draft, research_s, synth_s


@app.get("/health")
def health():
    return {"status": "ok", "mock_mode": MOCK_MODE}


@app.post("/generate", response_model=GenerateResponse)
async def generate(req: GenerateRequest):
    t0 = time.perf_counter()
    meeting_dt = parse_iso(req.meeting_time)
    now = datetime.now(timezone.utc)

    key = (req.name.strip().lower(), req.entity_type, req.meeting_type,
           meeting_dt.date().isoformat())
    hit = _cache.get(key)
    if hit and time.time() - hit[0] < CACHE_TTL_SECONDS:
        logger.info(json.dumps({"event": "generate", "name": req.name,
                                "cached": True,
                                "total_s": round(time.perf_counter() - t0, 3)}))
        return hit[1]

    window_end = min(now, meeting_dt)
    window_start = window_end - timedelta(days=30)

    try:
        results, draft, research_s, synth_s = await asyncio.wait_for(
            asyncio.to_thread(run_pipeline, req), timeout=TIMEOUT_SECONDS
        )
    except asyncio.TimeoutError:
        logger.info(json.dumps({"event": "generate", "name": req.name,
                                "error": "timeout"}))
        raise HTTPException(
            status_code=504,
            detail=f"Took longer than {TIMEOUT_SECONDS:g}s. Please try again.",
        )
    except Exception as exc:
        logger.info(json.dumps({"event": "generate", "name": req.name,
                                "error": repr(exc)}))
        raise HTTPException(
            status_code=502,
            detail="The research or AI step failed. Please try again.",
        )

    # Sources come ONLY from research() output, never from the LLM.
    sources = [
        Source(id=i, title=r["title"], url=r["url"],
               published_date=r["published_date"], domain=r["domain"])
        for i, r in enumerate(results, start=1)
    ]

    response = GenerateResponse(
        entity=draft["entity"],
        meeting={"time": req.meeting_time, "type": req.meeting_type,
                 "window_start": window_start.date().isoformat(),
                 "window_end": window_end.date().isoformat()},
        snapshot=draft["snapshot"],
        snapshot_source_ids=draft["snapshot_source_ids"],
        key_developments=draft["key_developments"],
        talking_points=draft["talking_points"],
        risks=draft["risks"],
        questions=draft["questions"],
        sources=sources,
        meta={"generated_at": now.isoformat(),
              "models_used": draft["meta"]["models_used"],
              "provider_used": draft["meta"]["provider_used"],
              "fallback_used": draft["meta"]["fallback_used"],
              "latency_seconds": round(time.perf_counter() - t0, 3),
              "notes": draft["meta"]["notes"]},
    )

    _cache[key] = (time.time(), response)
    logger.info(json.dumps({
        "event": "generate", "name": req.name, "cached": False,
        "research_s": round(research_s, 3), "synthesize_s": round(synth_s, 3),
        "total_s": round(time.perf_counter() - t0, 3),
        "n_sources": len(sources), "models_used": draft["meta"]["models_used"],
        "provider_used": draft["meta"]["provider_used"],
        "fallback_used": draft["meta"]["fallback_used"],
    }))
    return response


# Must stay LAST: serves /frontend at "/" so one URL runs everything.
app.mount("/", StaticFiles(directory=BASE_DIR / "frontend", html=True), name="frontend")
