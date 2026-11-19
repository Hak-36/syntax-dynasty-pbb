"""
pipeline.py - RESEARCH LAYER (Tavily)

research(name, entity_type, meeting_time_iso, days=30) -> list[dict]

CONTRACT 1 - every item in the returned list has exactly these keys:
    title          str
    url            str
    domain         str          (e.g. "reuters.com", no "www.")
    published_date str | None   ("YYYY-MM-DD" or None if unknown)
    content        str
    category       str          (which query group found it, e.g. "news")
    score          float        (Tavily relevance score)
    query          str          (the exact query text that found it)

Rules:
  * Only the last `days` days (default 30) are searched.
  * Nothing found -> returns [] (never None).
  * Tavily/network errors are caught and logged -> never crashes the caller.
  * The API key is read from the TAVILY_API_KEY environment variable only.
    No .env file and no key is stored in this file.

Run the self-test:   python pipeline.py
Run one live search: python pipeline.py --live "Satya Nadella" person
"""

from __future__ import annotations

import logging
import os
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from typing import Any, Optional
from urllib.parse import urlparse

import requests

log = logging.getLogger("research")

TAVILY_URL = "https://api.tavily.com/search"
REQUEST_TIMEOUT = 20      # seconds per HTTP call
MAX_RESULTS = 5           # per query
MAX_WORKERS = 4           # parallel queries

# category -> query template. {name} is filled in per call.
QUERY_TEMPLATES: dict[str, dict[str, str]] = {
    "person": {
        "news": "{name} latest news",
        "role": "{name} current role company announcement",
        "interview": "{name} interview OR podcast OR talk",
    },
    "company": {
        "news": "{name} latest news",
        "funding": "{name} funding OR revenue OR acquisition",
        "product": "{name} product launch OR partnership",
    },
}
DEFAULT_TEMPLATES = QUERY_TEMPLATES["company"]


# --------------------------------------------------------------------------
# Small helpers
# --------------------------------------------------------------------------
def _domain(url: str) -> str:
    host = urlparse(url).netloc.lower()
    return host[4:] if host.startswith("www.") else host


def _parse_date(raw: Any) -> Optional[datetime]:
    """Turn Tavily's date string into an aware datetime, or None."""
    if not raw or not isinstance(raw, str):
        return None
    raw = raw.strip()
    try:  # RFC 2822, e.g. "Tue, 12 Nov 2026 10:00:00 GMT"
        dt = parsedate_to_datetime(raw)
    except (TypeError, ValueError, IndexError):
        dt = None
    if dt is None:
        try:  # ISO 8601, e.g. "2026-11-12T10:00:00Z" or "2026-11-12"
            dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except ValueError:
            m = re.match(r"(\d{4})-(\d{2})-(\d{2})", raw)
            if not m:
                return None
            dt = datetime(int(m[1]), int(m[2]), int(m[3]))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _score(raw: Any) -> float:
    try:
        return round(float(raw), 4)
    except (TypeError, ValueError):
        return 0.0


# --------------------------------------------------------------------------
# One Tavily call (never raises)
# --------------------------------------------------------------------------
def _search_one(api_key: str, query: str, days: int) -> list[dict]:
    """Return Tavily's raw result dicts for one query, or [] on any error."""
    payload = {
        "query": query,
        "topic": "news",          # news topic returns published_date
        "days": days,             # only the last N days
        "search_depth": "basic",
        "max_results": MAX_RESULTS,
        "include_answer": False,
        "include_raw_content": False,
    }
    headers = {"Authorization": f"Bearer {api_key}"}
    try:
        resp = requests.post(
            TAVILY_URL, json=payload, headers=headers, timeout=REQUEST_TIMEOUT
        )
    except requests.RequestException as exc:  # timeout, DNS, connection...
        log.warning("Tavily request failed for %r: %s", query, exc)
        return []

    if resp.status_code != 200:
        # Don't log resp.request headers - they contain the key.
        log.warning("Tavily HTTP %s for %r: %s", resp.status_code, query, resp.text[:200])
        return []

    try:
        data = resp.json()
    except ValueError:
        log.warning("Tavily returned non-JSON for %r", query)
        return []

    results = data.get("results") if isinstance(data, dict) else None
    return results if isinstance(results, list) else []


# --------------------------------------------------------------------------
# Public function
# --------------------------------------------------------------------------
def research(
    name: str,
    entity_type: str,
    meeting_time_iso: str,
    days: int = 30,
) -> list[dict]:
    """Search Tavily for `name` over the last `days` days. See module docstring."""
    try:
        name = (name or "").strip()
        if not name:
            return []

        api_key = os.environ.get("TAVILY_API_KEY", "").strip()
        if not api_key:
            log.error("TAVILY_API_KEY is not set - returning empty list")
            return []

        days = max(1, min(int(days), 30))  # hard cap: never search past 30 days

        # meeting_time_iso is validated but the window always ends "now":
        # we want the freshest news before the meeting.
        if meeting_time_iso and _parse_date(meeting_time_iso) is None:
            log.warning("Could not parse meeting_time_iso=%r (ignored)", meeting_time_iso)

        templates = QUERY_TEMPLATES.get((entity_type or "").lower(), DEFAULT_TEMPLATES)
        jobs = [(cat, tpl.format(name=name)) for cat, tpl in templates.items()]

        # Run the queries in parallel (they are network-bound, so threads fit).
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
            raw_lists = list(
                pool.map(lambda j: _search_one(api_key, j[1], days), jobs)
            )

        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        best: dict[str, dict] = {}  # url -> best item (dedupe)

        for (category, query), raw_results in zip(jobs, raw_lists):
            for r in raw_results:
                if not isinstance(r, dict):
                    continue
                url = (r.get("url") or "").strip()
                if not url:
                    continue

                dt = _parse_date(r.get("published_date"))
                if dt is not None and dt < cutoff:
                    continue  # belt and braces: drop anything older than window

                item = {
                    "title": (r.get("title") or "").strip(),
                    "url": url,
                    "domain": _domain(url),
                    "published_date": dt.strftime("%Y-%m-%d") if dt else None,
                    "content": (r.get("content") or "").strip(),
                    "category": category,
                    "score": _score(r.get("score")),
                    "query": query,
                }
                if url not in best or item["score"] > best[url]["score"]:
                    best[url] = item

        return sorted(best.values(), key=lambda i: i["score"], reverse=True)

    except Exception as exc:  # last-resort guard: the caller must never crash
        log.exception("research() failed unexpectedly: %s", exc)
        return []


# --------------------------------------------------------------------------
# Self-test (no network, no key needed)
# --------------------------------------------------------------------------
CONTRACT_KEYS = {
    "title", "url", "domain", "published_date",
    "content", "category", "score", "query",
}


class _FakeResp:
    def __init__(self, status=200, body=None, text=""):
        self.status_code, self._body, self.text = status, body, text

    def json(self):
        if self._body is None:
            raise ValueError("no json")
        return self._body


def _self_test() -> int:
    logging.basicConfig(level=logging.ERROR, format="  [log] %(message)s")
    real_post = requests.post
    old_key = os.environ.get("TAVILY_API_KEY")
    os.environ["TAVILY_API_KEY"] = "test-key-not-real"
    now = datetime.now(timezone.utc)
    recent = (now - timedelta(days=3)).strftime("%a, %d %b %Y %H:%M:%S GMT")
    old = (now - timedelta(days=90)).strftime("%a, %d %b %Y %H:%M:%S GMT")
    passed = failed = 0

    def check(label: str, ok: bool) -> None:
        nonlocal passed, failed
        passed, failed = (passed + 1, failed) if ok else (passed, failed + 1)
        print(f"  {'PASS' if ok else 'FAIL'}  {label}")

    try:
        # 1. Normal results -> contract shape, dedupe, old item dropped
        def ok_post(url, json=None, headers=None, timeout=None):
            return _FakeResp(200, {"results": [
                {"title": "A", "url": "https://www.reuters.com/a", "content": "x",
                 "score": 0.91, "published_date": recent},
                {"title": "Old", "url": "https://old.com/o", "content": "y",
                 "score": 0.99, "published_date": old},
                {"title": "NoDate", "url": "https://blog.example.org/n", "content": "z",
                 "score": 0.4},
            ]})
        requests.post = ok_post
        out = research("Jane Doe", "person", "2026-11-25T10:00:00Z")
        print(f"\nsample output ({len(out)} items):")
        for item in out:
            print("  ", item)
        check("returns a list", isinstance(out, list))
        check("every item has exactly the 8 contract keys",
              all(set(i) == CONTRACT_KEYS for i in out))
        check("domain strips www.", out[0]["domain"] == "reuters.com")
        check("published_date is YYYY-MM-DD",
              re.fullmatch(r"\d{4}-\d{2}-\d{2}", out[0]["published_date"]) is not None)
        check("missing date -> None",
              any(i["published_date"] is None for i in out))
        check("90-day-old article dropped", all(i["url"] != "https://old.com/o" for i in out))
        check("deduped by url (3 queries, same urls)", len({i["url"] for i in out}) == len(out))
        check("sorted by score desc", [i["score"] for i in out] == sorted((i["score"] for i in out), reverse=True))
        check("score is float", all(isinstance(i["score"], float) for i in out))

        # 2. Request sends days=30 and topic=news
        seen = {}
        def spy_post(url, json=None, headers=None, timeout=None):
            seen.update(json or {})
            return _FakeResp(200, {"results": []})
        requests.post = spy_post
        research("Acme", "company", "2026-11-25T10:00:00Z")
        check("request uses days=30", seen.get("days") == 30)
        research("Acme", "company", "2026-11-25T10:00:00Z", days=999)
        check("days capped at 30", seen.get("days") == 30)

        # 3. Nothing found -> []
        check("empty results -> []", research("Nobody", "person", "") == [])

        # 4. Error handling
        requests.post = lambda *a, **k: _FakeResp(401, text="unauthorized")
        check("HTTP 401 -> [] no crash", research("X", "person", "") == [])
        requests.post = lambda *a, **k: _FakeResp(200, body=None)
        check("bad JSON -> [] no crash", research("X", "person", "") == [])

        def boom(*a, **k):
            raise requests.ConnectionError("network down")
        requests.post = boom
        check("network error -> [] no crash", research("X", "person", "") == [])

        requests.post = lambda *a, **k: _FakeResp(200, {"results": [None, 5, {"url": ""}]})
        check("garbage result rows skipped", research("X", "person", "") == [])

        # 5. Missing key / empty name
        os.environ.pop("TAVILY_API_KEY", None)
        check("missing API key -> []", research("X", "person", "") == [])
        os.environ["TAVILY_API_KEY"] = "test-key-not-real"
        check("empty name -> []", research("  ", "person", "") == [])
    finally:
        requests.post = real_post
        if old_key is None:
            os.environ.pop("TAVILY_API_KEY", None)
        else:
            os.environ["TAVILY_API_KEY"] = old_key

    print(f"\n{passed} passed, {failed} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    if len(sys.argv) >= 3 and sys.argv[1] == "--live":
        logging.basicConfig(level=logging.INFO)
        entity = sys.argv[3] if len(sys.argv) > 3 else "person"
        for row in research(sys.argv[2], entity, ""):
            print(row)
    else:
        print("pipeline.py self-test (mocked Tavily, no network, no key)")
        sys.exit(_self_test())
