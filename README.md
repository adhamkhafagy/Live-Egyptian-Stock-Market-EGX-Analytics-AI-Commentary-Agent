# EGX Live Analytics + AI Commentary Agent

Live-data analytics project on the Egyptian Exchange (EGX) — daily price
collection, a Power BI dashboard, and an AI agent that generates plain-language
commentary on daily stock moves.

## Status: Phases 1–3 complete, running on daily automation

### Setup

```bash
pip install -r requirements.txt
python fetch_egx_data.py
```

This fetches the last 5 trading days of OHLCV data for EGX30 constituents
(via Yahoo Finance's `.CA` ticker suffix) and stores it in `data/egx.db`
(SQLite).

### AI Commentary Agent

```bash
# requires a free Groq API key from https://console.groq.com
export GROQ_API_KEY="your-key-here"   # Windows: set GROQ_API_KEY=your-key-here
python ai_commentary.py
```

Reads the latest price moves from `data/egx.db` and generates a short
natural-language market summary via the Groq API (`openai/gpt-oss-120b`),
saved to `data/latest_commentary.txt`.

### Power BI Dashboard

Two pages, connected to `data/egx.db`:
- **Overview** — top 5 gainers / bottom 5 losers bar chart, plus the latest
  AI commentary text pulled in via Power Query
- **Stock Detail** — ticker slicer, price history line chart, daily change
  and latest close cards

Connect via **Get Data → Python script** (simplest, no ODBC driver needed):
```python
import sqlite3
import pandas as pd

conn = sqlite3.connect(r"<full path to>\data\egx.db")
prices = pd.read_sql_query("SELECT * FROM prices", conn)
conn.close()
```

### Automation — GitHub Actions

`.github/workflows/daily-update.yml` runs the full pipeline automatically,
Sunday–Thursday (EGX trading days), without needing your machine to be on:

1. Fetches the latest prices
2. Generates the AI commentary
3. Commits `data/egx.db` and `data/latest_commentary.txt` back to the repo

**Setup:**
- Push this repo to GitHub
- Add your Groq key as a repo secret: **Settings → Secrets and variables →
  Actions → New repository secret** → name it `GROQ_API_KEY`
- Trigger it manually once from the **Actions** tab (`Run workflow`) to
  confirm it works before waiting for the schedule

Power BI won't auto-refresh from a local file on its own — after each
automated run, either manually hit **Refresh** in Power BI Desktop, or
publish the report to the Power BI Service and set up a scheduled refresh
pointing at the repo's data file.

## Roadmap

- [x] Phase 1: Data collection script + SQLite storage
- [x] Phase 2: Power BI dashboard (overview + stock detail pages)
- [x] Phase 3: AI commentary agent (Groq API)
- [x] Automation: GitHub Actions daily workflow

