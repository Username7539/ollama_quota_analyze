"""Output probe: measure output-token price.

A tiny prompt (unique UUID each request, so nothing is cached) with a large
num_predict produces a long essay, so the quota spend is dominated by output
tokens. The input contribution is subtracted later in pricing using the
cache-miss estimate `a`.

Result is written to logs/output.json.
"""

import uuid
from datetime import datetime

from client import make_client
from config import (MODEL, NUM_PREDICT_OUTPUT, OUTPUT_CAP, OUTPUT_PATH)
from jsonio import save_json
from runner import run_group
from usage import get_api_key

PROMPT = (
    "Write an unbelievably long, exhaustive, detailed essay about the "
    "history of human civilization from prehistory to the present day. "
    "Make it as long and comprehensive as possible. Cover every possible "
    "aspect, period, figure, and development. Do not stop or summarize - "
    "write continuously at maximum length."
)


def make_output_factory(prompt_body):
    """Return a factory that emits a fresh-UUID output request each call."""
    def make():
        u = uuid.uuid4()
        content = f"[{u}]\n" + prompt_body
        return str(u), content
    return make


def main():
    api_key = get_api_key()
    client = make_client()

    factory = make_output_factory(PROMPT)
    group = run_group(
        client, label="output", group_name="output probe",
        num_predict=NUM_PREDICT_OUTPUT, cap=OUTPUT_CAP,
        make_content=factory, api_key=api_key,
    )

    output_data = {
        "metadata": {
            "model": MODEL,
            "num_predict": NUM_PREDICT_OUTPUT,
            "timestamp": datetime.now().isoformat(),
        },
        **group,
    }

    save_json(output_data, OUTPUT_PATH)
    print(f"\nDone. Log: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()