# Ollama Quota Analyzer

Scripts to measure actual token pricing and cache discounts on Ollama Cloud via `/api/usage`.

### Structure

- `scripts/`
  - `config.py` — Model and probe settings
  - `usage.py` — Fetches quota from `/api/usage`
  - `runner.py` — Probe execution loop
  - `probe_cache.py` — Tests cache miss / hit
  - `probe_output.py` — Tests output token cost
  - `pricing.py` — Calculates final $/1M prices
  - `validate.py` — Sanity checks for log data
- `texts/` — Test inputs (P1, P2)
- `logs/` — Probe JSON logs
- `result/` — Analysis summaries

### Usage

```bash
pip install -r requirements.txt
# Set OLLAMA_API in .env
python scripts/probe_cache.py
python scripts/probe_output.py
python scripts/pricing.py
```


Decided to go on a quick 20-minute adventure. In and out.

Ended up sitting here the entire day.

I was trying to estimate the actual pricing of Ollama Cloud Pro in dollars per million tokens ($/1M), knowing that the weekly quota is worth roughly $4.59.

TL;DR:

1. This is a pretty tedious endeavor.
2. GLM-5.2 in Ollama Cloud is roughly 20x cheaper than official non-discounted pricing (assuming you squeeze the quota bone-dry):

2026-08-28

    Miss = 0.072/1M
    Hit = 0.013/1M
    Output = 0.237/1M

3. DeepSeek v4 pro is extremely cheap, provided you keep sending it the exact same text and don't ask it any questions:

2026-08-28

    Miss = 0.133/1M
    Hit = 0.005/1M
    Output = 0.396/1M

4. GLM-5.3:

2026-08-28 (carried out shortly after the model appeared)

    Miss = 0.173/1M
    Hit = 0.032/1M
    Output = 0.429/1M

2026-08-31

    Miss = 0.105/1M
    Hit = 0.020/1M
    Output = 0.343/1M

5. In a weekly quota there are 5.6 five-hour quotas.

6. I could have mixed up a plus and a minus in the code and all of this might be complete nonsense.

Methodology:

I sent 3 types of requests:

1. (new uuid with each request) + (large text) With response length limited to 1 token, virtually the entire request goes towards cache miss.
2. (saved uuid from last cache\_miss request) + (the exact same large text) Response length limited to 1 token again. If the server didn't mess up the cache (which I verified by comparing request cost against miss requests and other hit requests), the entire request is a cache hit.
3. A small prompt instructing the model to write a large answer. Almost the entire cost of the response goes towards output.

I wrapped this core logic into a system that kept sending requests until sufficient statistical precision was reached (1.5% of the weekly quota per request type; 7.5% total weekly quota, since miss and hit probes were run across two different large texts of different sizes, P1 and P2, where P2 is roughly 5x larger than P1).

Note on Output pricing: Since output tokens were measured using a small input prompt, the calculated Output price is likely a lower bound. In real-world scenarios with massive context, generating output tokens might cost slightly more

TOTAL:

GLM-5.2

low-precision test run 2026-08-28

    === ratio r = 5h / week ===
    miss: r=6.18  err=+/-26%  range=[4.57, 7.79]
    hit: r=5.10  err=+/-29%  range=[3.63, 6.57]
    output: r=4.80  err=+/-41%  range=[2.84, 6.76]
    cross-probe: min=4.80 max=6.18 spread=1.38
    pooled: r=5.50  err=+/-17%
    === prices ($/1M tokens, from weekly quota) ===
    b/a = 22.1%  (cache discount = 77.9%)
    c/a = 3.94  (output vs input)
    Miss = 0.065/1M  err=+/-26%  range=[0.048, 0.082]
    Hit = 0.014/1M  err=+/-28%  range=[0.010, 0.018]
    Output = 0.256/1M  err=+/-40%  range=[0.153, 0.359]

full run-through 2026-08-28

    === ratio r = 5h / week ===
    miss: r=5.55  err=+/-8%  range=[5.13, 5.97]
    hit: r=5.83  err=+/-10%  range=[5.28, 6.39]
    output: r=5.27  err=+/-14%  range=[4.55, 5.98]
    cross-probe: min=5.27 max=5.83 spread=0.57
    pooled: r=5.60  err=+/-5%
    === prices ($/1M tokens, from weekly quota) ===
    b/a = 17.8%  (cache discount = 82.2%)
    c/a = 3.31  (output vs input)
    Miss = 0.072/1M  err=+/-7%  range=[0.066, 0.077]
    Hit = 0.013/1M  err=+/-9%  range=[0.012, 0.014]
    Output = 0.237/1M  err=+/-13%  range=[0.205, 0.269]

To burn through the weekly $4.59 using only input tokens without cache you'd need to feed the model roughly 64 million tokens. Sounds pretty plausible to me.

Just in case, a reminder of official prices without discounts:

    Miss = 1.4/1M
    Hit = 0.26/1M
    Output = 4.4/1M

DeepSeek v4 pro

full run-through 2026-08-28

    === ratio r = 5h / week ===
    miss: r=5.67  err=+/-7%  range=[5.27, 6.08]
    hit: r=5.53  err=+/-10%  range=[5.00, 6.06]
    output: r=5.67  err=+/-14%  range=[4.90, 6.43]
    cross-probe: min=5.53 max=5.67 spread=0.14
    pooled: r=5.62  err=+/-5%
    === prices ($/1M tokens, from weekly quota) ===
    b/a = 3.4%  (cache discount = 96.6%)
    c/a = 2.97  (output vs input)
    Miss = 0.133/1M  err=+/-7%  range=[0.124, 0.143]
    Hit = 0.005/1M  err=+/-9%  range=[0.004, 0.005]
    Output = 0.396/1M  err=+/-13%  range=[0.343, 0.448]

GLM-5.3

full run-through 2026-08-28 (carried out shortly after the model appeared)

    === ratio r = 5h / week ===
    miss: r=5.56  err=+/-7%  range=[5.19, 5.93]
    hit: r=5.78  err=+/-9%  range=[5.26, 6.30]
    output: r=5.87  err=+/-14%  range=[5.07, 6.66]
    cross-probe: min=5.56 max=5.87 spread=0.31
    pooled: r=5.69  err=+/-5%
    === prices ($/1M tokens, from weekly quota) ===
    b/a = 18.6%  (cache discount = 81.4%)
    c/a = 2.48  (output vs input)
    Miss = 0.173/1M  err=+/-7%  range=[0.161, 0.184]
    Hit = 0.032/1M  err=+/-9%  range=[0.029, 0.035]
    Output = 0.429/1M  err=+/-13%  range=[0.371, 0.486]

full run-through 2026-08-31

    === ratio r = 5h / week ===
    miss: r=5.70  err=+/-9%  range=[5.20, 6.19]
    hit: r=5.60  err=+/-10%  range=[5.06, 6.14]
    output: r=5.53  err=+/-14%  range=[4.78, 6.28]
    cross-probe: min=5.53 max=5.70 spread=0.16
    pooled: r=5.63  err=+/-6%
    === prices ($/1M tokens, from weekly quota) ===
    b/a = 19.0%  (cache discount = 81.0%)
    c/a = 3.28  (output vs input)
    Miss = 0.105/1M  err=+/-9%  range=[0.096, 0.114]
    Hit = 0.020/1M  err=+/-9%  range=[0.018, 0.022]
    Output = 0.343/1M  err=+/-13%  range=[0.297, 0.389]

That's basically it.

Draw your own conclusions.

Scripts and raw logs are in the comments.

If you decide to dig into this as well, I'd be curious to hear what you find.


PS:


GLM-5.3 full run-through 2026-09-01

    === ratio r = 5h / week ===
      miss: r=5.70  err=+/-9%  range=[5.20, 6.19]
      hit: r=5.60  err=+/-10%  range=[5.06, 6.14]
      output: r=5.47  err=+/-14%  range=[4.73, 6.21]
      cross-probe: min=5.47 max=5.70 spread=0.23
      pooled: r=5.62  err=+/-6%

    === prices ($/1M tokens, from weekly quota) ===
      b/a = 19.0%  (cache discount = 81.0%)
      c/a = 3.28  (output vs input)

      Miss = $0.105/1M  err=+/-9%  range=[$0.096, $0.114]
      Hit = $0.020/1M  err=+/-9%  range=[$0.018, $0.022]
      Output = $0.343/1M  err=+/-13%  range=[$0.297, $0.389]