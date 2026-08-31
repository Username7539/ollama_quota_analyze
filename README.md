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
