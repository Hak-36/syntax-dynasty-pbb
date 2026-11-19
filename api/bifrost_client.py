"""Small helper so every LLM call goes through Bifrost (never straight to a provider)."""
import os

import httpx
from dotenv import load_dotenv

load_dotenv()

BASE_URL = os.getenv("BIFROST_BASE_URL", "http://localhost:8080")
VIRTUAL_KEY = os.getenv("BIFROST_VIRTUAL_KEY", "")
PRIMARY_MODEL = os.getenv("PRIMARY_MODEL", "")
FALLBACK_MODELS = [m.strip() for m in os.getenv("FALLBACK_MODELS", "").split(",") if m.strip()]


def chat(messages, model=None, temperature=0.2, timeout=60):
    """Send a chat request through Bifrost.

    Returns (text, info). info has: models_used, provider_used, fallback_used.
    """
    body = {"model": model or PRIMARY_MODEL, "messages": messages,
            "temperature": temperature}
    if FALLBACK_MODELS:
        body["fallbacks"] = FALLBACK_MODELS

    r = httpx.post(f"{BASE_URL}/v1/chat/completions",
                   headers={"x-bf-vk": VIRTUAL_KEY}, json=body, timeout=timeout)
    r.raise_for_status()

    data = r.json()
    resolved = r.headers.get("x-bifrost-resolved-model") or body["model"]
    fb_index = r.headers.get("x-bifrost-fallback-index")
    info = {
        "models_used": [resolved],
        "provider_used": r.headers.get("x-bifrost-provider"),
        # Matches your fallback demo: index 1 meant the fallback answered.
        "fallback_used": bool(fb_index) and fb_index != "0",
    }
    return data["choices"][0]["message"]["content"], info