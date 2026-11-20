from utils.raise_exception import raise_exception
from fastapi import APIRouter
from utils.dbconn import DBConn
from typing import List
from pydantic import BaseModel
import pandas as pd
from utils import query

router = APIRouter()


class Payload(BaseModel):
    year: int
    dates: List[str]  # 'YYYY-MM' format
    symbols: List[str]
    amounts: List[float]
    currencies: List[str]
    target_currency: str


@router.post("/yearly-market-percentage-return")
def yearly_market_percentage_return(payload: Payload):
    """
    Return the market yield of a portfolio of a given year.

    Implementation:
    - Price difference calculated between closing price of previous year and current year.
      For example, 2025 -> difference between 2025-12-31 and 2024-12-31.
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

    prev_year = payload.year - 1
    curr_year = payload.year
    # Previous year closing price
    asset_date = f"{curr_year}-12"

    # Filter for transactions made before the beginning of last year
    df_filtered = df_purchases[df_purchases["date"] <= asset_date].copy()

    # Aggregate total amount for each symbol
    portfolio = (
        df_filtered.groupby(["symbol", "currency"])["amount"].sum().reset_index()
    )

    # tot_yield_perc = sum_for_each_asset [ ( (close * amount)  * ((close - open) / open)) ] / total_allocation
    # tot_yield_perc = sum_for_each_asset [ ( asset_alloc_price *     asset_yield_perc   ) ] / total_allocation
    # tot_yield_perc = sum_for_each_asset [ (                  tot_yield                 ) ] / total_allocation

    tot_yield = 0.0
    tot_alloc_price = 0

    for asset in portfolio.itertuples(index=False):
        # Asset price at open, e.g. 100 EUR
        open = query.close_value(db_conn, asset.symbol, prev_year)
        # Asset price at close, e.g. 120 EUR
        close = query.close_value(db_conn, asset.symbol, curr_year)
        # Exchange rate at open and close, e.g. 1.01 and 1.03 for EUR-CHF
        # WARNING: closing price 2024 != opening price 2025 -> just below 0.1% so acceptable
        exch_rate_open = query.exch_rate(
            db_conn, asset.currency, payload.target_currency, prev_year
        )
        exch_rate_close = query.exch_rate(
            db_conn, asset.currency, payload.target_currency, curr_year
        )
        # Asset total allocation, e.g. 20.000 EUR for VWCE
        asset_alloc_price = asset.amount * open * exch_rate_open
        # Asset yield in percentage for target currency, e.g. 20% for EUR-VWCE -> 15% for CHF-VWCE
        open_e = open * exch_rate_open
        close_e = close * exch_rate_close
        asset_yield_perc = (close_e - open_e) / (open_e)
        # Asset yield, e.g. 4.000 EUR for VWCE
        asset_yield = asset_alloc_price * asset_yield_perc

        # Total yield, e.g. 5.000 for VWCE and AYEM
        tot_yield += asset_yield
        # Total allocation price, e.g. 25.000 EUR for VWCE and AYEM
        tot_alloc_price += asset_alloc_price

    # Total yield percentage, e.g. 18% as weighted average for VWCE and AYEM
    tot_yield_perc = tot_yield / tot_alloc_price if tot_alloc_price != 0 else 0
    return tot_yield_perc
