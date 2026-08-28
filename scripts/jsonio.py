"""JSON load/save helpers for probe results."""

import json


def load_json(path):
    """Load JSON from path; return None if the file is missing."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"  File not found: {path}")
        return None


def save_json(data, path):
    """Save data as UTF-8 JSON, creating parent directories if needed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)