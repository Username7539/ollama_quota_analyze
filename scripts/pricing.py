"""Pricing analysis: errors, linearity, ratio, and dollar prices."""

from config import (HIT_PATH, MISS_PATH, OUTPUT_PATH, PRICE_PER_PCT_WEEK)
from jsonio import load_json

READING_ERR = 0.1
DELTA_ERR = 2 * READING_ERR


def _groups(data):
    return data["groups"] if "groups" in data else [data]


def _rel_err(delta, G=1):
    """Relative error of a delta (or pooled sum of G deltas)."""
    if delta == 0:
        return float("inf")
    return DELTA_ERR * G / abs(delta)


def group_errors(data, tag):
    """Print per-group and pooled errors for both 5h and weekly deltas."""
    groups = _groups(data)
    G = len(groups)

    print(f"=== {tag} ===")
    for g in groups:
        label = g.get("text_label", "output")
        name = g.get("group", "")
        d5 = g["delta5h"]
        dw = g["deltaweek"]
        print(f"  {label}/{name}:")
        print(f"    5h:    delta={d5:.1f}%  rel_err={_rel_err(d5):.1%}")
        print(f"    week:  delta={dw:.1f}%  rel_err={_rel_err(dw):.1%}")

    total5h = sum(g["delta5h"] for g in groups)
    totalweek = sum(g["deltaweek"] for g in groups)
    print(f"  pooled (G={G}):")
    print(f"    5h:    sum={total5h:.1f}%  rel_err={_rel_err(total5h, G):.1%}")
    print(f"    week:  sum={totalweek:.1f}%  rel_err={_rel_err(totalweek, G):.1%}")
    print()


def check_linearity(data, tag, symbol):
    """Check if per-token pricing is linear across texts."""

    groups = _groups(data)
    estimates = []
    for g in groups:
        delta = g["delta5h"]
        total_pec = sum(r["prompt_eval_count"] for r in g["requests"])
        price = delta / total_pec
        estimates.append((g["text_label"], price, delta, total_pec))

    print(f"=== linearity ({tag}) ===")
    for label, price, delta, total_pec in estimates:
        print(f"  {label}: {symbol}={price:.2e}  delta5h={delta:.1f}%  total_pec={total_pec}")

    vals = [e[1] for e in estimates]
    v_min, v_max = min(vals), max(vals)
    v_mean = sum(vals) / len(vals)
    spread = (v_max - v_min) / v_mean if v_mean != 0 else float("inf")

    G = len(estimates)
    total_delta = sum(e[2] for e in estimates)
    err = _rel_err(total_delta, G)

    print(f"  spread = {spread:.1%}  err = {err:.1%}")
    if spread < err:
        print(f"  VERDICT: linear (spread < err)")
    else:
        print(f"  VERDICT: non-linear (spread > err)")
    print()


def check_ratio(miss, hit, out):
    """Compute r = delta5h / deltaweek per probe type and pooled."""
    print("=== ratio r = 5h / week ===")
    rs = []
    for data, tag in [(miss, "miss"), (hit, "hit"), (out, "output")]:
        groups = _groups(data)
        G = len(groups)
        d5 = sum(g["delta5h"] for g in groups)
        dw = sum(g["deltaweek"] for g in groups)
        r = d5 / dw
        err5h = _rel_err(d5, G)
        errweek = _rel_err(dw, G)
        err_r = err5h + errweek
        rs.append(r)
        print(f"  {tag}: r={r:.2f}  err=+/-{err_r:.0%}  "
              f"range=[{r*(1-err_r):.2f}, {r*(1+err_r):.2f}]")

    if len(rs) >= 2:
        r_min, r_max = min(rs), max(rs)
        print(f"  cross-probe: min={r_min:.2f} max={r_max:.2f} "
              f"spread={r_max - r_min:.2f}")

    G_all = sum(len(_groups(d)) for d in [miss, hit, out])
    d5_all = sum(g["delta5h"] for d in [miss, hit, out] for g in _groups(d))
    dw_all = sum(g["deltaweek"] for d in [miss, hit, out] for g in _groups(d))
    r_val = d5_all / dw_all
    err_r = _rel_err(d5_all, G_all) + _rel_err(dw_all, G_all)
    print(f"  pooled: r={r_val:.2f}  err=+/-{err_r:.0%}")
    print()


def _input_price(data, key):
    """Price per input token: sum(delta) / sum(pec). Returns (price, err)."""
    groups = _groups(data)
    G = len(groups)
    delta = sum(g[key] for g in groups)
    total_pec = sum(r["prompt_eval_count"] for g in groups
                    for r in g["requests"])
    return delta / total_pec, _rel_err(delta, G)


def compute_prices(miss, hit, out):
    """Compute a, b, c in $/1M tokens directly from weekly deltas."""
    print("=== prices ($/1M tokens, from weekly quota) ===")

    a, err_a = _input_price(miss, "deltaweek")
    b, err_b = _input_price(hit, "deltaweek")

    groups = _groups(out)
    G = len(groups)
    dw = sum(g["deltaweek"] for g in groups)
    total_pec = sum(r["prompt_eval_count"] for g in groups
                    for r in g["requests"])
    total_eval = sum(r["eval_count"] for g in groups
                     for r in g["requests"])
    c = (dw - a * total_pec) / total_eval
    err_c = _rel_err(dw, G)

    print(f"  b/a = {b/a:.1%}  (cache discount = {1 - b/a:.1%})")
    print(f"  c/a = {c/a:.2f}  (output vs input)")
    print()

    k = PRICE_PER_PCT_WEEK * 1_000_000
    for name, price, err_p in [("A", a, err_a),
                               ("B", b, err_b),
                               ("C", c, err_c)]:
        dollars = price * k
        lo = dollars * (1 - err_p)
        hi = dollars * (1 + err_p)
        print(f"  {name} = ${dollars:.3f}/1M  err=+/-{err_p:.0%}  "
              f"range=[${lo:.3f}, ${hi:.3f}]")
    print()


def main():
    miss = load_json(MISS_PATH)
    hit = load_json(HIT_PATH)
    out = load_json(OUTPUT_PATH)

    if miss:
        group_errors(miss, "miss")
    if hit:
        group_errors(hit, "hit")
    if out:
        group_errors(out, "output")

    check_linearity(miss, "miss", "a")
    check_linearity(hit, "hit", "b")
    check_ratio(miss, hit, out)
    compute_prices(miss, hit, out)


if __name__ == "__main__":
    main()