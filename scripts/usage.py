"""Client for the undocumented /api/usage endpoint."""

import json
import math
import os
import time

import urllib.request

from dotenv import load_dotenv

from config import HOST

USAGE_URL = HOST + "/api/usage"


def get_api_key():
    load_dotenv()
    key = os.environ.get("OLLAMA_API")
    if not key:
        raise SystemExit("OLLAMA_API not found in .env")
    return key


def fetch_usage(api_key=None):
    """Return the raw usage dict from /api/usage."""
    key = api_key or get_api_key()
    req = urllib.request.Request(USAGE_URL, headers={
        "Authorization": f"Bearer {key}",
    })
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode("utf-8"))


def read_quota(api_key=None):
    """Return (session_used, weekly_used) as percentages (0-100).

    Both meters quantise at 0.1%, so round to 1 decimal to strip float noise.
    """
    data = fetch_usage(api_key)
    limits = data["limits"]
    session = round(limits["session"]["usage"] * 100, 1)
    weekly = round(limits["weekly"]["usage"] * 100, 1)
    return session, weekly


def next_session_reset(now=None, epoch_ts=1786535700, period=5 * 3600):
    """Unix timestamp of the next fixed 5h session-quota reset.

    anchor: 2026-08-12 11:55 UTC. Reset blocks are fixed,
    so boundaries land at epoch + k*5h for integer k.
    """
    if now is None:
        now = time.time()
    k = math.floor((now - epoch_ts) / period) + 1
    return epoch_ts + k * period