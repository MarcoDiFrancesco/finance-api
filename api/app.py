from fastapi import FastAPI


app = FastAPI(root_path="/api")


@app.get("/")
def root():
    return {"Welcome to the OCR API!": "Check out documentation at /api/docs"}


@app.get("/amount/{symbol}/{date}")
def get_amount(symbol, date):
    return 3

