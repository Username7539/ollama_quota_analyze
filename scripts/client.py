"""Ollama Cloud client and request helper."""

import os
import time

from dotenv import load_dotenv
from ollama import Client

from config import HOST, MODEL

RETRIES = 3
RETRY_DELAY = 5.0


def make_client():
    """Build an authenticated Ollama client from the OLLAMA_API env var."""
    load_dotenv()
    api_key = os.environ.get("OLLAMA_API")
    if not api_key:
        raise SystemExit("OLLAMA_API not found in .env")
    return Client(host=HOST, headers={"Authorization": f"Bearer {api_key}"})


def send_request(client, user_content, num_predict,
                 retries=RETRIES, delay=RETRY_DELAY):
    """Send one chat request; temperature 0 for reproducibility."""
    last_err = None
    for attempt in range(1, retries + 1):
        try:
            return client.chat(
                model=MODEL,
                messages=[{"role": "user", "content": user_content}],
                stream=False,
                options={"num_predict": num_predict, "temperature": 0},
            )
        except Exception as e:
            last_err = f"{type(e).__name__}: {e}"
        print(f"    request failed ({last_err}); "
              f"retry {attempt}/{retries} in {delay}s...")
        if attempt < retries:
            time.sleep(delay)
    raise RuntimeError(f"request failed after {retries} attempts "
                       f"(last: {last_err})")