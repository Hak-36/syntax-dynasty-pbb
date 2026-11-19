"""Every LLM call in our project goes through Bifrost, via this file."""
import os
import time

import httpx
from dotenv import load_dotenv

load_dotenv()

BIFROST_BASE_URL = os.getenv("BIFROST_BASE_URL", "http://localhost:8080").rstrip("/")
BIFROST_VIRTUAL_KEY = os.getenv("BIFROST_VIRTUAL_KEY", "")
PRIMARY_MODEL = os.getenv("PRIMARY_MODEL", "")
FALLBACK_MODELS = [m.strip() for m in os.getenv("FALLBACK_MODELS", "").split(",") if m.strip()]
DEMO_FORCE_FALLBACK = os.getenv("DEMO_FORCE_FALLBACK", "0") == "1"


class BifrostError(Exception):
    pass


def chat(messages, model=None, fallbacks=None, temperature=0.2, timeout=60):
    """Returns {"text", "model_used", "provider_used", "fallback_used", "latency"}."""
    model = model or PRIMARY_MODEL
    if not model:
        raise BifrostError("PRIMARY_MODEL is empty. Set it in .env")
    if not BIFROST_VIRTUAL_KEY:
        raise BifrostError("BIFROST_VIRTUAL_KEY is empty. Set it in .env")
    fallbacks = FALLBACK_MODELS if fallbacks is None else fallbacks

    sent_model = model
    if DEMO_FORCE_FALLBACK:
        if not fallbacks:
            raise BifrostError("DEMO_FORCE_FALLBACK=1 but FALLBACK_MODELS is empty")
        provider = model.split("/")[0]
        sent_model = f"{provider}/this-model-does-not-exist"  # primary fails on purpose

    body = {"model": sent_model, "messages": messages, "temperature": temperature}
    if fallbacks:
        body["fallbacks"] = fallbacks

    start = time.time()
    try:
        resp = httpx.post(
            f"{BIFROST_BASE_URL}/v1/chat/completions",
            headers={"x-bf-vk": BIFROST_VIRTUAL_KEY},
            json=body,
            timeout=timeout,
        )
    except httpx.HTTPError as e:
        raise BifrostError(f"Could not reach Bifrost at {BIFROST_BASE_URL}: {e}")
    latency = round(time.time() - start, 2)

    if resp.status_code != 200:
        raise BifrostError(f"Bifrost returned {resp.status_code}: {resp.text[:300]}")

    data = resp.json()
    try:
        text = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError):
        raise BifrostError(f"Unexpected response shape: {str(data)[:300]}")

    fb_index = resp.headers.get("x-bifrost-fallback-index")
    return {
        "text": text,
        "model_used": resp.headers.get("x-bifrost-resolved-model") or sent_model,
        "provider_used": resp.headers.get("x-bifrost-provider") or model.split("/")[0],
        "fallback_used": bool(fb_index) and fb_index != "0",
        "latency": latency,
    }


if __name__ == "__main__":
    print(chat([{"role": "user", "content": "Say hello in one short sentence."}]))
