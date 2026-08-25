"""
ai_commentary.py
-----------------
Reads the latest daily price data from the SQLite database and uses the
Groq API (Llama model) to generate a short, plain-language market summary
explaining the day's notable gainers and losers.

Setup:
    1. Get a free API key from https://console.groq.com
    2. Set it as an environment variable before running:
         Windows (PowerShell): $env:GROQ_API_KEY="your-key-here"
         Windows (cmd):        set GROQ_API_KEY=your-key-here
         Mac/Linux:             export GROQ_API_KEY="your-key-here"
    3. pip install groq
    4. python ai_commentary.py

Usage:
    python ai_commentary.py
"""

import os
import sqlite3

from groq import Groq

DB_PATH = "data/egx.db"
MODEL_NAME = "openai/gpt-oss-120b"  # Groq deprecated the llama-3.3 models; this is the current recommended general-purpose model


def get_latest_moves(conn: sqlite3.Connection) -> list[dict]:
    """
    Returns each ticker's latest close, previous close, and % change,
    computed directly from the prices table using SQL window functions.
    """
    query = """
    WITH ranked AS (
        SELECT
            ticker,
            company,
            date,
            close,
            ROW_NUMBER() OVER (PARTITION BY ticker ORDER BY date DESC) AS rn
        FROM prices
    ),
    latest AS (
        SELECT ticker, company, date, close FROM ranked WHERE rn = 1
    ),
    previous AS (
        SELECT ticker, close AS prev_close FROM ranked WHERE rn = 2
    )
    SELECT
        latest.ticker,
        latest.company,
        latest.date,
        latest.close,
        previous.prev_close,
        ROUND((latest.close - previous.prev_close) * 100.0 / previous.prev_close, 2) AS pct_change
    FROM latest
    JOIN previous ON latest.ticker = previous.ticker
    ORDER BY pct_change DESC
    """
    cursor = conn.execute(query)
    columns = [c[0] for c in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


def build_prompt(moves: list[dict]) -> str:
    """Formats the day's price moves into a prompt for the LLM."""
    lines = [
        f"{m['company']} ({m['ticker']}): {m['pct_change']:+.2f}% -> EGP {m['close']:.2f}"
        for m in moves
    ]
    data_block = "\n".join(lines)

    return f"""You are a financial analyst summarizing today's Egyptian Exchange (EGX) session.

Here is today's closing data (percent change vs. previous close):
{data_block}

Write a concise market summary in both languages (english and arabic) (4-6 sentences) that:
- Opens with the overall tone of the session (mostly up / mostly down / mixed)
- Names the top 2 gainers and top 2 losers with their % change
- Avoids generic filler phrases -- be specific to the numbers given
- Is written in a professional but accessible tone, suitable for a daily report

Do not invent any news or reasons not present in the data -- only describe the price movements themselves.
"""


def generate_commentary(moves: list[dict]) -> str:
    client = Groq(api_key=os.environ["GROQ_API_KEY"])
    prompt = build_prompt(moves)

    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.4,
        max_tokens=400,
    )
    return response.choices[0].message.content


def main() -> None:
    if "GROQ_API_KEY" not in os.environ:
        print("[ERROR] GROQ_API_KEY environment variable is not set. See the setup instructions at the top of this file.")
        return

    conn = sqlite3.connect(DB_PATH)
    moves = get_latest_moves(conn)
    conn.close()

    if not moves:
        print("[ERROR] No price data found. Run fetch_egx_data.py first.")
        return

    print(f"Generating commentary for {len(moves)} stocks...\n")
    commentary = generate_commentary(moves)

    print("=" * 60)
    print(commentary)
    print("=" * 60)

    # Save alongside the data for later reference / dashboard use.
    with open("data/latest_commentary.txt", "w", encoding="utf-8") as f:
        f.write(commentary)
    print("\nSaved to data/latest_commentary.txt")


if __name__ == "__main__":
    main()
