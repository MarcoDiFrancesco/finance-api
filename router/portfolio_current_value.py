from utils.raise_exception import raise_exception
from fastapi import APIRouter
from utils.dbconn import DBConn
from typing import List
from pydantic import BaseModel
import pandas as pd
from utils import query

router = APIRouter()
db_conn = DBConn()


class Payload(BaseModel):
    year: int
    dates: List[str]  # 'YYYY-MM' format
    symbols: List[str]
    amounts: List[float]
    currencies: List[str]
    target_currency: str


@router.post("/portfolio-current-value")
def portfolio_current_value(payload: Payload):
    """
    Calculates the total value of a portfolio at the beginning of a given year for a given currency.

    'In 2025 when I turned 24 I had already invested 5k'

    Details:
    - Asset price of previous year
    - Currency exchange of previous year
    """
    # Load the incoming data into a pandas DataFrame for easier processing
    try:
        df_purchases = pd.DataFrame(
            {
                "date": payload.dates,
                "symbol": payload.symbols,
                "amount": payload.amounts,
                "currency": payload.currencies,
            }
        )
    except ValueError:
        raise_exception("Input columns must have the same length.")

    # Previous year closing price
    target_year = payload.year - 1
    target_date = f"{target_year}-12"

    # Filter for transactions made before the beginning of last year
    df_filtered = df_purchases[df_purchases["date"] <= target_date].copy()

    # Aggregate total amount for each symbol
    portfolio = (
        df_filtered.groupby(["symbol", "currency"])["amount"].sum().reset_index()
    )

    total_portfolio_value = 0.0

    for asset in portfolio.itertuples(index=False):
        price = query.close_value(db_conn, asset.symbol, target_year)

        # Apply currency conversion
        exch_rate = 1
        if asset.currency != payload.target_currency:
            source = asset.currency
            target = payload.target_currency
            # Yahoo Finance's naming convention for forex
            forex_symbol = f"{source}{target}=X"
            exch_rate = query.close_value(db_conn, forex_symbol, target_year)

        total_portfolio_value += asset.amount * price * exch_rate

    return total_portfolio_value
