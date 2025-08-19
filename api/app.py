from fastapi import FastAPI, HTTPException
import yfinance as yf
import datetime
import pandas as pd
import sqlite3
import os
from pydantic import BaseModel
import pandas as pd
import sqlite3
from typing import List

app = FastAPI(
    title="Finance API",
    description="API for retrieving financial data from Yahoo Finance",
    root_path="/api",
)

# SQLite database configuration
DB_PATH = "/db/finance.db"


# Initialize database if it doesn't exist
def init_db():
    """Initialize SQLite database with required tables if they don't exist"""
    if not os.path.exists(os.path.dirname(DB_PATH)):
        os.makedirs(os.path.dirname(DB_PATH))

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        """
    CREATE TABLE IF NOT EXISTS prices (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        symbol TEXT NOT NULL,
        date TEXT NOT NULL,
        open REAL,
        close REAL, 
        high REAL,
        low REAL,
        volume REAL,
        average REAL,
        UNIQUE(symbol, date)
    )
    """
    )
    conn.commit()
    conn.close()


# Initialize the database on startup
init_db()


@app.get("/")
def root():
    """
    Root endpoint that returns a welcome message with documentation link.
    """
    return {"Welcome to the Finance API!": "Check out documentation at /api/docs"}


def raise_exception(detail):
    raise HTTPException(status_code=500, detail=detail)


@app.get("/price/{symbol}/{date}", summary="Get stock price for a specific month")
def price(symbol: str, date: str):
    """
    Get the average stock price for a specific month.

    Parameters:
    - **symbol**: Stock symbol as used in Yahoo Finance (e.g., VWCE.DE)
    - **date**: Month in YYYY-MM format (e.g., 2025-01)
    """
    # Check date format 'YYYY-MM'
    if not date or len(date) != 7 or date[4] != "-":
        raise_exception("Date must be in 'YYYY-MM' format")

    # Query the database for the price
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT average FROM prices WHERE symbol = ? AND date = ?", (symbol, date)
    )
    result = cursor.fetchone()
    conn.close()

    if not result:
        raise_exception(f"No data found for symbol '{symbol}' on date '{date}'")

    return result[0]


@app.get("/update/{symbol}/", summary="Update stock price data")
def update(symbol: str):
    """
    Pull monthly prices from Yahoo Finance for the given symbol.

    Parameters:
    - **symbol**: Stock symbol as used in Yahoo Finance (e.g., VWCE.DE)
    """
    # Check if symbol is valid
    try:
        yf.Ticker(symbol).info
    except Exception as e:
        raise_exception(f"Invalid Yahoo Finance symbol '{symbol}'")

    end_date = get_last_month_day()

    # Fetch data from Yahoo Finance
    df = yf.download(symbol, end=end_date, interval="1mo")
    df = df.reset_index()
    df.columns = ["date", "close", "high", "low", "open", "volume"]
    df["symbol"] = symbol
    # Average is calculated as the mean of close and open prices
    df["average"] = df[["close", "open"]].mean(axis=1)
    # Convert date to YYYY-MM format
    df["date"] = df["date"].dt.strftime("%Y-%m")

    # Store data in SQLite database
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Insert data into the database (replace if already exists)
    for _, row in df.iterrows():
        cursor.execute(
            """
            INSERT OR REPLACE INTO prices 
            (symbol, date, open, close, high, low, volume, average) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                row["symbol"],
                row["date"],
                row["open"],
                row["close"],
                row["high"],
                row["low"],
                row["volume"],
                row["average"],
            ),
        )

    conn.commit()
    conn.close()

    return {
        "message": f"Prices of '{symbol}' updated successfully up to '{end_date}'"
    }


def get_last_month_day():
    """
    Get the last day of the previous month.

    E.g., if today is 2023-10-15, return 2023-09-30.
    """
    today = datetime.datetime.now()
    first_day_of_current_month = today.replace(day=1)
    last_day_of_prev_month = first_day_of_current_month - datetime.timedelta(days=1)
    # Format the date to YYYY-MM-DD
    return last_day_of_prev_month.strftime("%Y-%m-%d")


class PortfolioPayload(BaseModel):
    year: int
    dates: List[str]  # Assumes 'YYYY-MM' format from purchase history
    symbols: List[str]
    amounts: List[float]
    currencies: List[str]
    target_currency: str


@app.post("/portfolio-current-value")
def portfolio_current_value(payload: PortfolioPayload):
    """
    Calculates the total value of a portfolio at the beginning of a given year.

    Consider closing prices of previous year.
    """
    # Load the incoming data into a pandas DataFrame for easier processing
    try:
        df_purchases = pd.DataFrame({
            'date': payload.dates,
            'symbol': payload.symbols,
            'amount': payload.amounts,
            'currency': payload.currencies
        })
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Input lists must have the same length."
        )

    # Filter for transactions made before the start of the target year
    start_of_year = f"{payload.year}-01"
    df_filtered = df_purchases[df_purchases['date'] < start_of_year].copy()

    # Aggregate total amount for each symbol
    holdings = df_filtered.groupby(['symbol', 'currency'])['amount'].sum().reset_index()

    total_portfolio_value = 0.0
    price_date = f"{payload.year - 1}-12"  # Use price from the end of the previous year

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    for _, row in holdings.iterrows():
        # Get the latest price from the database
        cursor.execute(
            "SELECT average FROM prices WHERE symbol = ? AND date = ?",
            (row['symbol'], price_date)
        )
        price = cursor.fetchone()[0]

        value = row['amount'] * price

        # Apply dummy currency conversion
        # TODO: Fix this convertion
        if row['currency'] == 'EUR' and payload.target_currency == 'CHF':
            value *= 1.08
        
        total_portfolio_value += value

    conn.close()
    return total_portfolio_value
