"""Adaptive probe loop shared by all probe types.

Simple scheme: read quota, send a request, read quota again. Each request
gets its own delta; zero deltas (lag or meter quantisation) just accumulate
into later readings. The group stops when the accumulated weekly delta
reaches the target or the request cap is hit. One settled reading at the end
absorbs the meter lag of the final requests.
"""

import time
from datetime import datetime

from client import send_request
from config import TARGET_WEEK
from usage import next_session_reset, read_quota


def _seconds_to_session_reset():
    return max(0.0, next_session_reset() - time.time())


def run_group(client, *, label, group_name, num_predict, cap, make_content,
              api_key=None):
    """Run one adaptive probe group.

    make_content() -> (uuid_str, user_content) builds the next request.
    cap limits the number of requests.
    Returns a group dict compatible with the legacy JSON schema; each entry
    in "requests" holds one request and its surrounding quota readings.
    """
    if _seconds_to_session_reset() < 900:
        print("WARNING: <15 min until the 5h session quota reset; "
              "results of this group may be invalid")

    q5h_start, qweek_start = read_quota(api_key)
    q5h_last, qweek_last = q5h_start, qweek_start

    sent = 0
    requests = []

    print(f"\n--- {label}: group '{group_name}' (cap={cap}, "
          f"np={num_predict}) ---")

    while sent < cap:
        uid, content = make_content()
        print(f">>> {label} '{group_name}' request {sent + 1}/{cap} "
              f"(uuid={uid}, np={num_predict})...")
        resp = send_request(client, content, num_predict)
        print(f"    pec={resp.prompt_eval_count} ec={resp.eval_count} "
              f"dr={resp.done_reason} td={resp.total_duration}")
        sent += 1

        q5h_after, qweek_after = read_quota(api_key)
        delta5h = q5h_after - q5h_last
        deltaweek = qweek_after - qweek_last
        req = {
            "uuid": uid,
            "prompt_eval_count": resp.prompt_eval_count,
            "eval_count": resp.eval_count,
            "total_duration": resp.total_duration,
            "q5h_before": q5h_last,
            "qweek_before": qweek_last,
            "q5h_after": q5h_after,
            "qweek_after": qweek_after,
            "delta5h": delta5h,
            "deltaweek": deltaweek,
            "valid5h": delta5h >= 0,
            "timestamp": datetime.now().isoformat(),
        }
        requests.append(req)
        print(f"    d5h={delta5h:+.3f}% dweek={deltaweek:+.3f}%")
        q5h_last, qweek_last = q5h_after, qweek_after

        if qweek_after - qweek_start >= TARGET_WEEK:
            print(f"    Target reached: "
                  f"dweek={qweek_after - qweek_start}% >= {TARGET_WEEK}%")
            break

    # One settled reading absorbs the meter lag of the final requests.
    # The lag is kept separate (not attributed to any request) so per-request
    # deltas stay honest; group totals include it for pricing accuracy.
    time.sleep(60)
    q5h_settled, qweek_settled = read_quota(api_key)
    settle_delta5h = q5h_settled - q5h_last
    settle_deltaweek = qweek_settled - qweek_last
    if settle_deltaweek != 0 or settle_delta5h != 0:
        print(f"    final settle: d5h {q5h_last:+.3f} -> {q5h_settled:+.3f} "
              f"(+{settle_delta5h:+.3f}), "
              f"dweek {qweek_last:+.3f} -> {qweek_settled:+.3f} "
              f"(+{settle_deltaweek:+.3f})")
        q5h_last, qweek_last = q5h_settled, qweek_settled

    return {
        "text_label": label,
        "group": group_name,
        "num_predict": num_predict,
        "cap": cap,
        "q5h_before": q5h_start,
        "qweek_before": qweek_start,
        "q5h_after": q5h_last,
        "qweek_after": qweek_last,
        "delta5h": q5h_last - q5h_start,
        "deltaweek": qweek_last - qweek_start,
        "settle_delta5h": settle_delta5h,
        "settle_deltaweek": settle_deltaweek,
        "valid5h": (q5h_last - q5h_start) >= 0,
        "requests": requests,
    }