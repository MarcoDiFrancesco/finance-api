from fastapi import FastAPI, HTTPException
import yfinance as yf
import datetime
import pandas as pd

app = FastAPI(
    title="Finance API",
    description="API for retrieving financial data from Yahoo Finance",
    root_path="/api",
)
csv_price = "/db/price.csv"


@app.get("/")
def root():
    """
    Root endpoint that returns a welcome message with documentation link.
    """
    return {"Welcome to the Finance API!": "Check out documentation at /api/docs"}


def raise_exception(detail):
    raise HTTPException(status_code=500, detail=detail)


@app.get("/price/{symbol}/{date}", summary="Get stock price for a specific month")
def get_amount(symbol: str, date: str):
    """
    Get the average stock price for a specific month.

    Parameters:
    - **symbol**: Stock symbol as used in Yahoo Finance (e.g., VWCE.DE)
    - **date**: Month in YYYY-MM format (e.g., 2025-01)
    """
    # Check date format 'YYYY-MM'
    if not date or len(date) != 7 or date[4] != "-":
        raise_exception("Date must be in 'YYYY-MM' format")

    df = pd.read_csv(csv_price)
    # Yahoo Finance marks
    df = df[(df["date"] == date) & (df["symbol"] == symbol)]
    if df.empty:
        raise_exception(f"No data found for symbol '{symbol}' on date '{date}'")
    return df.iloc[0]["average"]


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
    start_date = "2025-01-01"
    end_date = get_last_month_day()
    df = yf.download(symbol, start=start_date, end=end_date, interval="1mo")
    df = df.reset_index()
    df.columns = ["date", "close", "high", "low", "open", "volume"]
    df["symbol"] = symbol
    # Average is calculated as the mean of close and open prices
    df["average"] = df[["close", "open"]].mean(axis=1)
    # Convert date to YYYY-MM format
    df["date"] = df["date"].dt.strftime("%Y-%m")
    df.to_csv(csv_price)
    return {
        "message": f"Prices of '{symbol}' updated successfully from '{start_date}' to '{end_date}'"
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
