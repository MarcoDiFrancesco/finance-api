from investments.utils.raise_exception import raise_exception


def close_value(db_conn, symbol, year):
    """Get close value of an asset at the end of the year, or the latest month available."""
    with db_conn as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT close
            FROM prices
            WHERE symbol = ? AND date LIKE ?
            ORDER BY date DESC
            LIMIT 1
            """,
            (symbol, f"{year}-%"),
        )
        res = cursor.fetchone()
        if not res:
            raise_exception(f"Data in DB not available for [{symbol}, {year}]")
        price = res[0]
    return price


def exch_rate(db_conn, source, target, year):
    rate = 1
    if source != target:
        # Yahoo Finance's naming convention for forex
        forex_symbol = f"{source}{target}=X"
        rate = close_value(db_conn, forex_symbol, year)
    return rate
