"""
fetch_egx_data.py
------------------
Fetches daily OHLCV price data for EGX30 constituent stocks using yfinance
(Yahoo Finance covers EGX stocks with a ".CA" ticker suffix, e.g. COMI.CA)
and stores it in a local SQLite database.

Run this daily via cron / Task Scheduler to build up a live historical dataset.

Usage:
    python fetch_egx_data.py
"""

import os
import sqlite3
from datetime import datetime

import yfinance as yf

# EGX30 constituents (Yahoo Finance tickers, ".CA" suffix = Cairo).
# NOTE: verify/update this list periodically -- EGX30 membership changes
# and some Yahoo tickers may need adjustment (check finance.yahoo.com manually
# if a symbol below returns no data).
EGX30_TICKERS = {
    "COMI.CA": "Commercial International Bank",
    "HRHO.CA": "EFG Holding",
    "TMGH.CA": "Talaat Moustafa Group",
    "SWDY.CA": "Elsewedy Electric",
    "EAST.CA": "Eastern Company",
    "ETEL.CA": "Telecom Egypt",
    "ABUK.CA": "Abou Kir Fertilizers",
    "ORWE.CA": "Oriental Weavers",
    "AMOC.CA": "Alexandria Mineral Oils",
    "EFIH.CA": "e-Finance Investment Group",
    "MFPC.CA": "Misr Fertilizers Production",
    "ORAS.CA": "Orascom Construction",
    "PHDC.CA": "Palm Hills Development",
    "CIEB.CA": "Credit Agricole Egypt",
    "HELI.CA": "Heliopolis Housing",
    # Add remaining EGX30 names as needed.
}

DB_PATH = "data/egx.db"


def init_db(conn: sqlite3.Connection) -> None:
    """Create the prices table if it doesn't already exist."""
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS prices (
            ticker      TEXT NOT NULL,
            company     TEXT NOT NULL,
            date        TEXT NOT NULL,
            open        REAL,
            high        REAL,
            low         REAL,
            close       REAL,
            volume      INTEGER,
            fetched_at  TEXT NOT NULL,
            PRIMARY KEY (ticker, date)
        )
        """
    )
    conn.commit()


def fetch_and_store(conn: sqlite3.Connection) -> None:
    """Fetch recent daily data for every ticker and upsert into SQLite."""
    fetched_at = datetime.utcnow().isoformat()

    for ticker, company in EGX30_TICKERS.items():
        try:
            # period="5d" keeps requests light; the daily cron job only
            # needs to backfill a few recent sessions in case a run was missed.
            hist = yf.Ticker(ticker).history(period="5d")
        except Exception as exc:
            print(f"[WARN] Failed to fetch {ticker}: {exc}")
            continue

        if hist.empty:
            print(f"[WARN] No data returned for {ticker} ({company})")
            continue

        for date, row in hist.iterrows():
            conn.execute(
                """
                INSERT INTO prices (ticker, company, date, open, high, low, close, volume, fetched_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(ticker, date) DO UPDATE SET
                    open=excluded.open, high=excluded.high, low=excluded.low,
                    close=excluded.close, volume=excluded.volume, fetched_at=excluded.fetched_at
                """,
                (
                    ticker,
                    company,
                    date.strftime("%Y-%m-%d"),
                    float(row["Open"]),
                    float(row["High"]),
                    float(row["Low"]),
                    float(row["Close"]),
                    int(row["Volume"]),
                    fetched_at,
                ),
            )
        print(f"[OK] {ticker} ({company}) — {len(hist)} rows upserted")

    conn.commit()


def main() -> None:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    init_db(conn)
    fetch_and_store(conn)
    conn.close()
    print("Done.")


if __name__ == "__main__":
    main()
