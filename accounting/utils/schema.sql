DROP TABLE IF EXISTS fx_rates;

CREATE TABLE fx_rates (
    currency    TEXT NOT NULL,
    rate_date   TEXT NOT NULL,
    rate_to_chf REAL NOT NULL,
    PRIMARY KEY (currency, rate_date)
);
