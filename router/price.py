# from utils.raise_exception import raise_exception
# from fastapi import APIRouter
# from utils.dbconn import DBConn

# router = APIRouter()
# db_conn = DBConn()


# @router.get(
#     "/price/{symbol}/{date}", summary="Get stock close price for a specific month"
# )
# def price(symbol: str, date: str):
#     """
#     Get the close stock price for the given month.

#     Parameters:
#     - **symbol**: Stock symbol as used in Yahoo Finance (e.g., VWCE.DE)
#     - **date**: Month in YYYY-MM format (e.g., 2025-01)
#     """
#     # Check date format 'YYYY-MM'
#     if not date or len(date) != 7 or date[4] != "-":
#         raise_exception("Date must be in 'YYYY-MM' format")

#     # Query the database for the price
#     with db_conn as conn:
#         cursor = conn.cursor()
#         cursor.execute(
#             "SELECT close FROM prices WHERE symbol = ? AND date = ?", (symbol, date)
#         )
#         result = cursor.fetchone()

#     if not result:
#         raise_exception(f"No data found for symbol '{symbol}' on date '{date}'")

#     return result[0]
