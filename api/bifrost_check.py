"""Quick check that Bifrost works from Python.

Run:  python -m api.bifrost_check
Fallback demo:  python -m api.bifrost_check --fallback
"""
import os
import sys

import httpx
from dotenv import load_dotenv

load_dotenv()

BASE_URL = os.getenv("BIFROST_BASE_URL", "http://localhost:8080")
VIRTUAL_KEY = os.getenv("BIFROST_VIRTUAL_KEY", "")
PRIMARY = os.getenv("PRIMARY_MODEL", "groq/openai/gpt-oss-120b")


def call_bifrost(model, fallbacks=None):
    body = {
        "model": model,
        "messages": [{"role": "user", "content": "Say hello in 5 words"}],
    }
    if fallbacks:
        body["fallbacks"] = fallbacks  # see the fallbacks page in docs.getbifrost.ai

    r = httpx.post(
        f"{BASE_URL}/v1/chat/completions",
        headers={"x-bf-vk": VIRTUAL_KEY},
        json=body,
        timeout=60,
    )
    print("Status:", r.status_code)
    print("Provider header:", r.headers.get("x-bifrost-provider"))
    print("Resolved model:", r.headers.get("x-bifrost-resolved-model"))
    print("Fallback index:", r.headers.get("x-bifrost-fallback-index"))
    if r.status_code == 200:
        print("Reply:", r.json()["choices"][0]["message"]["content"])
    else:
        print("Error body:", r.text[:500])


if __name__ == "__main__":
    if not VIRTUAL_KEY:
        sys.exit("BIFROST_VIRTUAL_KEY is empty. Put it in your .env file.")
    if "--fallback" in sys.argv:
        # Deliberately wrong primary model, so Bifrost has to use the fallback.
        call_bifrost("groq/this-model-does-not-exist", fallbacks=[PRIMARY])
    else:
        call_bifrost(PRIMARY)