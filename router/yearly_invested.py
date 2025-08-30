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
    amounts: List[float]
    prices: List[float]
    currencies: List[str]
    target_currency: str


@router.post("/yearly-invested")
def yearly_invested(payload: Payload):
    """
    Calculates the value of assets invested on a given year for a given currency.

    Details:
    - Currency exchange of current year
    """
    # Load the incoming data into a pandas DataFrame for easier processing
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
        # Apply currency conversion
        exch_rate = 1
        if asset.currency != payload.target_currency:
            source = asset.currency
            target = payload.target_currency
            # Yahoo Finance's naming convention for forex
            symbol = f"{source}{target}=X"
            # End of current year, or latest month available
            year = payload.year
            exch_rate = query.close_value(db_conn, symbol, year)

        total_portfolio_value += asset.amount * asset.price * exch_rate

    return total_portfolio_value
