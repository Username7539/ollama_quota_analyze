"""Cache probe: measure input-token price for cache miss and cache hit.

For each text profile it runs two groups:
  - cache miss: every request uses a fresh UUID prefix, so the provider
    re-evaluates the prompt (price a per input token);
  - cache hit: the last miss request is repeated verbatim, so the provider
    serves the prompt from cache (price b per cached input token).

Results are written to logs/miss.json and logs/hit.json.
"""

import uuid
from datetime import datetime

from client import make_client
from config import (HIT_PATH, MISS_PATH, MODEL, NUM_PREDICT_CACHE,
                    REPEAT_COUNT, TEXT_PROFILES)
from jsonio import save_json
from runner import run_group
from usage import get_api_key


def build_prompt_body(path, repeat):
    """Read a text file and repeat its content `repeat` times."""
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()
    return (text + "\n") * repeat


def make_miss_factory(prompt_body):
    """Return a factory that emits a fresh-UUID miss request each call.

    `last` is a shared dict the factory writes the latest (uuid, content)
    into, so the hit group can repeat it verbatim.
    """
    last = {}

    def make():
        u = uuid.uuid4()
        content = f"[{u}]\n" + prompt_body
        last["uuid"] = str(u)
        last["content"] = content
        return last["uuid"], content

    return make, last


def make_hit_factory(cached_content):
    """Return a factory that always emits the same (cached) request."""
    cached_uuid = cached_content.split("]\n", 1)[0].lstrip("[")

    def make():
        return cached_uuid, cached_content

    return make


def main():
    api_key = get_api_key()
    client = make_client()

    miss_groups = []
    hit_groups = []

    for label, path, miss_cap, hit_cap in TEXT_PROFILES:
        print(f"\n>>> text {label}: {path.name} x{REPEAT_COUNT}")
        prompt_body = build_prompt_body(path, REPEAT_COUNT)

        miss_factory, miss_last = make_miss_factory(prompt_body)
        miss_group = run_group(
            client, label=label, group_name="cache miss",
            num_predict=NUM_PREDICT_CACHE, cap=miss_cap,
            make_content=miss_factory, api_key=api_key,
        )
        miss_groups.append(miss_group)

        hit_factory = make_hit_factory(miss_last["content"])
        hit_group = run_group(
            client, label=label, group_name="cache hit",
            num_predict=NUM_PREDICT_CACHE, cap=hit_cap,
            make_content=hit_factory, api_key=api_key,
        )
        hit_groups.append(hit_group)

    timestamp = datetime.now().isoformat()
    miss_data = {
        "metadata": {
            "model": MODEL,
            "num_predict": NUM_PREDICT_CACHE,
            "repeat_count": REPEAT_COUNT,
            "timestamp": timestamp,
        },
        "groups": miss_groups,
    }
    hit_data = {
        "metadata": {
            "model": MODEL,
            "num_predict": NUM_PREDICT_CACHE,
            "repeat_count": REPEAT_COUNT,
            "timestamp": timestamp,
        },
        "groups": hit_groups,
    }

    save_json(miss_data, MISS_PATH)
    save_json(hit_data, HIT_PATH)
    print(f"\nDone. Logs: {MISS_PATH}, {HIT_PATH}")


if __name__ == "__main__":
    main()