from utils.raise_exception import raise_exception
from fastapi import APIRouter
from utils.dbconn import DBConn
import yfinance as yf
import datetime

router = APIRouter()
db_conn = DBConn()


# Define the list of symbols in your Python code
API_SYMBOLS = [
    "VWCE.DE",  # Vanguard FTSE All-world
    "AYEM.DE",  # Vanguard EM
    "CSPX.AS",  # S&P 500
    "SXR8.DE",  # S&P 500
    "SGLD.MI",  # Gold
    "CHDVD.SW",  # iShares Swiss Dividend
    "ANAU.MI",  # NASDAQ 100
    "VAPX.SW", # FTSE Developed Asia Pacific ex Japan
    "H50E.SW", # EURO STOXX 50
    "EIMI.SW", # MSCI EM IMI
    # EUR
    "EURCHF=X",
    "EURUSD=X",
    # CHF
    "CHFEUR=X",
    "CHFUSD=X",
    # USD
    "USDEUR=X",
    "USDCHF=X",
]


def _get_last_month_day():
    """
    Get the last day of the previous month.

    E.g., if today is 2023-10-15, return 2023-09-30.
    """
    today = datetime.datetime.now()
    first_day_of_current_month = today.replace(day=1)
    last_day_of_prev_month = first_day_of_current_month - datetime.timedelta(days=1)
    # Format the date to YYYY-MM-DD
    return last_day_of_prev_month.strftime("%Y-%m-%d")


def _update_one(symbol: str):
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

    end_date = _get_last_month_day()

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
    with db_conn as conn:
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

    return {"message": f"Prices of '{symbol}' updated successfully up to '{end_date}'"}


@router.get("/update/", summary="Update all asset price data")
def update():
    results = []
    for symbol in API_SYMBOLS:
        result = _update_one(symbol)
        results.append(result)

    return {"update_results": results}
