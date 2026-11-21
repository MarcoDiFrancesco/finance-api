from investments.utils.raise_exception import raise_exception
from fastapi import APIRouter
from investments.utils.dbconn import DBConn
from typing import List
from pydantic import BaseModel
import pandas as pd
from investments.utils import query

router = APIRouter()


class Payload(BaseModel):
    year: int
    dates: List[str]  # 'YYYY-MM' format
    symbols: List[str]
    amounts: List[float]
    currencies: List[str]
    target_currency: str


@router.post("/portfolio-value")
def portfolio_value(payload: Payload):
    """
    Return value of the portfolio at the end of a given year (2025) using
    closing prices (31-12-2025).
    """
    db_conn = DBConn()
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

    # Year closing price
    target_year = payload.year
    target_date = f"{target_year}-12"

    # Get transactions made this year or earlier (31-12-2025)
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
