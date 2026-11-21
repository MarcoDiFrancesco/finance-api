from fastapi import FastAPI, Request

from accounting.routers import (
    upload as accounting_upload,
    upload_page as accounting_upload_page,
)
from investments.routers import (
    portfolio_value,
    update,
    yearly_investment,
    yearly_market_percentage_return,
)

app = FastAPI(
    title="API",
    description="API for investments (Yahoo Finance) and accounting (Cashew SQLite ETL)",
)


@app.middleware("http")
async def honor_forwarded_prefix(request: Request, call_next):
    """Apply Traefik's X-Forwarded-Prefix header so /docs works behind stripPrefix."""
    prefix = request.headers.get("x-forwarded-prefix", "").rstrip("/")
    if prefix:
        request.scope["root_path"] = prefix
    return await call_next(request)


@app.get("/")
def root(request: Request):
    """Return a welcome message with documentation link."""
    docs_path = f"{request.scope.get('root_path', '')}/docs"
    return {"Welcome to the API!": f"Check out documentation at {docs_path}"}


# Investments (backwards-compatible root endpoints)
app.include_router(portfolio_value.router, tags=["Investments"])
app.include_router(update.router, tags=["Investments"])
app.include_router(yearly_investment.router, tags=["Investments"])
app.include_router(yearly_market_percentage_return.router, tags=["Investments"])

# Accounting (Cashew SQLite ETL)
app.include_router(accounting_upload_page.router, tags=["Accounting"])
app.include_router(accounting_upload.router, tags=["Accounting"])
