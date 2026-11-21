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
    amounts: List[float]
    prices: List[float]
    currencies: List[str]
    target_currency: str


@router.post("/yearly-investment")
def yearly_investment(payload: Payload):
    """
    Return amount paid for assets in a given year.

    For example: 2025 -> Sum paid for asset costs of purchases between 01-2025 - 12-2025.
    """
    db_conn = DBConn()
    try:
        df_purchases = pd.DataFrame(
            {
                "date": payload.dates,
                "amount": payload.amounts,
                "price": payload.prices,
                "currency": payload.currencies,
            }
        )
    except ValueError:
        raise_exception("Input columns must have the same length.")

    # Filter for transactions made before the start of the target year
    start_of_year = f"{payload.year}-01"
    end_of_year = f"{payload.year}-12"
    portfolio = df_purchases[
        (df_purchases["date"] >= start_of_year) & (df_purchases["date"] <= end_of_year)
    ].copy()

    total_portfolio_value = 0.0

    for asset in portfolio.itertuples(index=False):
        price = asset.price
        
        # Apply currency conversion
        exch_rate = 1
        if asset.currency != payload.target_currency:
            source = asset.currency
            target = payload.target_currency
            # Yahoo Finance's naming convention for forex
            forex_symbol = f"{source}{target}=X"
            # End of current year, or latest month available
            year = payload.year
            exch_rate = query.close_value(db_conn, forex_symbol, year)

        total_portfolio_value += asset.amount * price * exch_rate

    return total_portfolio_value
