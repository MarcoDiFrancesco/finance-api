import datetime
import os
import shutil
import sqlite3
from pathlib import Path

import pandas as pd
import yfinance as yf

from accounting.config import (
    CASHEW_DIR,
    EXPENSES_PATH,
    FILENAME_PATTERN,
    REQUIRED_TABLES,
    SCHEMA_PATH,
    SQLITE_MAGIC,
)


def _validate_filename(filename):
    """Ensure filename is present and matches the Cashew export pattern."""
    if not filename:
        raise ValueError("Missing filename.")

    safe_name = Path(filename).name
    if safe_name != filename or not FILENAME_PATTERN.fullmatch(safe_name):
        raise ValueError(
            f"Unexpected filename '{filename}'. Expected format: cashew-YYYY-MM-DD-HH-MM-SS-*.sql"
        )
    return safe_name


def _validate_sqlite(db_path: Path):
    """Check SQLite 3 magic header, `PRAGMA integrity_check`, and required Cashew tables."""
    with db_path.open("rb") as f:
        header = f.read(16)
    if header != SQLITE_MAGIC:
        raise ValueError("Uploaded file is not a valid SQLite 3 database.")

    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        integrity = conn.execute("PRAGMA integrity_check;").fetchone()
        if not integrity or integrity[0] != "ok":
            raise ValueError(f"SQLite integrity check failed: {integrity}")

        tables = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table';"
            ).fetchall()
        }
        missing = REQUIRED_TABLES - tables
        if missing:
            raise ValueError(f"Missing required Cashew tables: {sorted(missing)}")
    finally:
        conn.close()


def _save_raw(content: bytes, safe_name: str):
    """Reject duplicate raw filenames and write upload bytes to `raw/`."""
    raw_dir = CASHEW_DIR / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)

    raw_path = raw_dir / safe_name
    if raw_path.exists():
        raise FileExistsError(f"Raw file already exists: {raw_path.name}")

    raw_path.write_bytes(content)
    return raw_path


def _copy_to_processed(raw_path: Path):
    """Reject duplicate processed filenames and copy `raw_path` to `processed/`."""
    processed_dir = CASHEW_DIR / "processed"
    processed_dir.mkdir(parents=True, exist_ok=True)

    processed_path = processed_dir / f"{raw_path.stem}-processed{raw_path.suffix}"
    if processed_path.exists():
        raise FileExistsError(f"Processed file already exists: {processed_path.name}")

    shutil.copy2(raw_path, processed_path)
    return processed_path


def _fetch_fx_rows(db_path: Path):
    """Fetch Yahoo Finance daily `{CURRENCY}CHF=X` closes for all non-CHF wallets."""
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        tx_count, min_ts = conn.execute(
            "SELECT COUNT(*), MIN(date_created) FROM transactions;"
        ).fetchone()
        if not tx_count or min_ts is None:
            raise ValueError("No transactions found in uploaded database.")

        currencies = [
            row[0]
            for row in conn.execute(
                "SELECT DISTINCT lower(currency) FROM wallets WHERE currency IS NOT NULL ORDER BY 1;"
            ).fetchall()
        ]
    finally:
        conn.close()

    # Start 7 days early so Jan 1 / weekend transactions have a prior market close
    min_date = datetime.datetime.fromtimestamp(min_ts, tz=datetime.timezone.utc).date()
    start_date = (min_date - datetime.timedelta(days=7)).isoformat()

    fx_rows = []
    for currency in currencies:
        if currency == "chf":
            continue

        ticker = f"{currency.upper()}CHF=X"
        df = yf.download(ticker, start=start_date, interval="1d", auto_adjust=True, progress=False)
        if df is None or df.empty:
            raise RuntimeError(f"No FX data returned by Yahoo Finance for {ticker}")

        # yfinance >=0.2.50 can return MultiIndex columns even for a single ticker
        close = df["Close"]
        if isinstance(close, pd.DataFrame):
            close = close.iloc[:, 0]

        for dt, val in close.dropna().items():
            fx_rows.append((currency, dt.strftime("%Y-%m-%d"), float(val)))

    return tx_count, fx_rows, currencies


def _build_tables(db_path: Path, fx_rows):
    """Set DELETE journal mode, create `fx_rates`, insert rows, and build `expenses`."""
    schema_sql = SCHEMA_PATH.read_text(encoding="utf-8")
    expenses_sql = EXPENSES_PATH.read_text(encoding="utf-8")

    conn = sqlite3.connect(db_path)
    try:
        # Single-file journal mode ensures Grafana can mount cashew/ read-only
        conn.execute("PRAGMA journal_mode=DELETE;")
        conn.executescript(schema_sql)
        conn.executemany(
            "INSERT INTO fx_rates (currency, rate_date, rate_to_chf) VALUES (?, ?, ?);",
            fx_rows,
        )
        conn.executescript(expenses_sql)
        conn.commit()
    finally:
        conn.close()


def process_cashew_upload(content: bytes, filename):
    """Validate upload, save raw/processed SQLite copies with FX rates, and update cashew.db."""
    safe_name = _validate_filename(filename)

    raw_path = _save_raw(content, safe_name)
    _validate_sqlite(raw_path)

    # Copy to processed/, fetch FX closes, and build fx_rates + expenses
    processed_path = _copy_to_processed(raw_path)
    tx_count, fx_rows, currencies = _fetch_fx_rows(processed_path)
    _build_tables(processed_path, fx_rows)

    # Point cashew.db at the new processed file
    active_path = CASHEW_DIR / "cashew.db"
    active_path.unlink(missing_ok=True)
    os.link(processed_path, active_path)

    return {
        "raw_file": str(raw_path),
        "processed_file": str(processed_path),
        "active_db": str(active_path),
        "transactions_count": tx_count,
        "fx_rates_count": len(fx_rows),
        "currencies": currencies,
    }
