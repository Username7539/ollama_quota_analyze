"""Sanity-check probe logs before pricing analysis.

Quota-based checks use the 5h meter only: both meters quantise at 0.1%, but
the 5h quota drains faster (smaller budget, resets every 5h), so each request
moves it by a larger step (~0.8% vs ~0.1% for weekly). The same 0.1% quantum
produces far less relative noise on 5h deltas. Token-count checks
(eval_count, pec) are quota-independent.
"""

from statistics import median

from config import (HIT_PATH, MISS_PATH, NUM_PREDICT_CACHE,
                    NUM_PREDICT_OUTPUT, OUTPUT_PATH)
from jsonio import load_json

TOL = 0.11  # both meters quantise at 0.1%; TOL covers quantum + float noise


def _groups(data):
    return data["groups"] if "groups" in data else [data]


def _deltas(group):
    return [r["delta5h"] for r in group["requests"]]


def _by_label(data):
    return {g["text_label"]: g for g in _groups(data)}


def _print_result(name, failures):
    ok = len(failures) == 0
    detail = "; ".join(failures) if failures else "ok"
    print(f"  {'PASS' if ok else 'FAIL'}  {name}  {detail}")
    return ok


def check_invariant(miss, hit, out):
    """Sum of per-request 5h deltas + settle == group 5h total."""
    name = "invariant sum==group (5h)"
    eps = 1e-9
    failures = []
    for data, tag in [(miss, "miss"), (hit, "hit"), (out, "output")]:
        if data is None:
            failures.append(f"{tag}: file missing")
            continue
        for g in _groups(data):
            s = sum(_deltas(g)) + g["settle_delta5h"]
            if abs(s - g["delta5h"]) > eps:
                failures.append(f"{tag}/{g['text_label']}: diff={s - g['delta5h']:.10f}")
    return _print_result(name, failures)


def check_spread(miss, hit):
    """No value deviates from its series median by more than TOL (miss+hit)."""
    name = "series spread (miss+hit)"
    failures = []
    for data, tag in [(miss, "miss"), (hit, "hit")]:
        if data is None:
            failures.append(f"{tag}: file missing")
            continue
        for g in _groups(data):
            vals = _deltas(g)
            if len(vals) == 0:
                failures.append(f"{tag}/{g['text_label']}: no requests")
                continue
            m = median(vals)
            dev = max(abs(v - m) for v in vals)
            if dev > TOL:
                failures.append(f"{tag}/{g['text_label']}: median={m:.4f} maxdev={dev:.4f}")
    return _print_result(name, failures)


def check_hit_cheaper(miss, hit):
    """Every hit delta < min miss delta / 2, per text label."""
    name = "hit<miss/2"
    if miss is None or hit is None:
        return _print_result(name, ["missing miss or hit data"])
    failures = []
    miss_map = _by_label(miss)
    for label, hg in _by_label(hit).items():
        mg = miss_map.get(label)
        if mg is None:
            failures.append(f"{label}: no matching miss group")
            continue
        miss_vals = [v for v in _deltas(mg) if v > 0]
        if len(miss_vals) == 0:
            failures.append(f"{label}: all miss deltas <= 0")
            continue
        ref = min(miss_vals) / 2
        bad = [v for v in _deltas(hg) if v >= ref]
        if bad:
            failures.append(f"{label}: ref={ref:.4f} violations={bad}")
    return _print_result(name, failures)


def check_pec_match(miss, hit):
    """Cache-hit pec should equal the last cache-miss pec for the same text."""
    name = "pec match"
    if miss is None or hit is None:
        return _print_result(name, ["missing miss or hit data"])
    failures = []
    miss_map = _by_label(miss)
    for label, hg in _by_label(hit).items():
        mg = miss_map.get(label)
        if mg is None:
            failures.append(f"{label}: no matching miss group")
            continue
        last_miss_pec = mg["requests"][-1]["prompt_eval_count"]
        bad = [r["prompt_eval_count"] for r in hg["requests"]
               if r["prompt_eval_count"] != last_miss_pec]
        if bad:
            failures.append(f"{label}: last_miss={last_miss_pec} hit={bad}")
    return _print_result(name, failures)


def check_eval_cache(miss, hit):
    """Cache probes: eval_count == NUM_PREDICT_CACHE (miss + hit)."""
    name = "eval==np (cache)"
    failures = []
    for data, tag in [(miss, "miss"), (hit, "hit")]:
        if data is None:
            failures.append(f"{tag}: file missing")
            continue
        for g in _groups(data):
            bad = [r["eval_count"] for r in g["requests"]
                   if r["eval_count"] != NUM_PREDICT_CACHE]
            if bad:
                failures.append(f"{tag}/{g['text_label']}: {bad}")
    return _print_result(name, failures)


def check_eval_output(out):
    """Output probe: NUM_PREDICT_CACHE < eval_count <= NUM_PREDICT_OUTPUT."""
    name = "eval in range (output)"
    if out is None:
        return _print_result(name, ["no output data"])
    bad = [r["eval_count"] for r in out["requests"]
           if not (NUM_PREDICT_CACHE < r["eval_count"] <= NUM_PREDICT_OUTPUT)]
    return _print_result(name, bad)


def main():
    miss = load_json(MISS_PATH)
    hit = load_json(HIT_PATH)
    out = load_json(OUTPUT_PATH)

    results = [
        check_invariant(miss, hit, out),
        check_spread(miss, hit),
        check_hit_cheaper(miss, hit),
        check_pec_match(miss, hit),
        check_eval_cache(miss, hit),
        check_eval_output(out),
    ]

    print(f"\n{sum(results)}/{len(results)} checks passed")
    if not all(results):
        raise SystemExit(1)


if __name__ == "__main__":
    main()