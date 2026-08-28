"""Shared constants and text profiles for quota probes and pricing."""

from pathlib import Path

# Project root: parent of the scripts/ directory containing this file.
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# --- API ---
MODEL = "glm-5.2:cloud"
HOST = "https://ollama.com"

# --- Paths ---
TEXTS_DIR = PROJECT_ROOT / "texts"
LOGS_DIR = PROJECT_ROOT / "logs"
_MODEL_TAG = MODEL.replace(":", "-")
MISS_PATH = LOGS_DIR / f"miss_{_MODEL_TAG}.json"
HIT_PATH = LOGS_DIR / f"hit_{_MODEL_TAG}.json"
OUTPUT_PATH = LOGS_DIR / f"output_{_MODEL_TAG}.json"

# Text profiles: (label, path, miss_cap, hit_cap)
# miss_cap / hit_cap = max number of requests for that probe type on this
# text. Miss requests burn the full prompt price, so few are needed (large
# texts move the meter by ~1%+ per request). Hit requests are cheap (cache
# discount), so more of them are needed to reach TARGET_WEEK.
# The adaptive target (TARGET_WEEK) usually stops a group before its caps;
# caps only bound the worst case (cheap models, tiny deltas).
SMALL = ("P1", TEXTS_DIR / "P1.txt", 50, 200)   # ~120 KB: 15 miss, 25 hit
LARGE = ("P2", TEXTS_DIR / "P2.txt", 10, 50)    # ~575 KB: 3 miss, 10 hit
TEXT_PROFILES = (SMALL, LARGE)

# --- Probe parameters ---
NUM_PREDICT_CACHE = 1        # near-zero output, so quota spend reflects input
NUM_PREDICT_OUTPUT = 10000   # large output, so quota spend reflects output
TARGET_WEEK = 0.5            # goal: accumulate weekly delta >= 0.5%
OUTPUT_CAP = 50              # request cap for the output probe
REPEAT_COUNT = 3             # how many times each text is repeated in a prompt

# --- Subscription economics ---
MONTHLY_PRICE = 20.0         # $/month
DAYS_IN_MONTH = 30.5
WEEKLY_CYCLES = DAYS_IN_MONTH / 7
FIVE_H_RAW_CYCLES = DAYS_IN_MONTH * 24 / 5
PRICE_PER_PCT_WEEK = MONTHLY_PRICE / WEEKLY_CYCLES / 100  # $ per 1% of weekly quota