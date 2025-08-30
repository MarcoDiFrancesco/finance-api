from fastapi import FastAPI
from router import portfolio_current_value, price, update, yearly_invested, yearly_market_percentage_return


app = FastAPI(
    title="Finance API",
    description="API for retrieving financial data from Yahoo Finance",
    root_path="/api",
)


@app.get("/")
def root():
    """
    Root endpoint that returns a welcome message with documentation link.
    """
    return {"Welcome to the Finance API!": "Check out documentation at /api/docs"}


app.include_router(portfolio_current_value.router)
# app.include_router(price.router)
app.include_router(update.router)
app.include_router(yearly_invested.router)
app.include_router(yearly_market_percentage_return.router)
