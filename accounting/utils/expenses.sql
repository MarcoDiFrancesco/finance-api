DROP TABLE IF EXISTS expenses;

CREATE TABLE expenses AS
-- Materialized at ETL time with daily fx_rates, Europe/Zurich time, and active expense rules:
--   paid = 1                           (exclude future scheduled/unpaid transactions)
--   AND paired_transaction_fk IS NULL  (exclude internal transfers between wallets)
--   AND date_zurich < first of upload month (exclude incomplete current month, frozen at ETL time)
WITH tx_enriched AS (
    SELECT
        t.*,
        lower(w.currency) AS currency,
        w.name AS account,
        c.name AS category,
        o.name AS objective,
        CASE
            WHEN lower(w.currency) = 'chf' THEN 1.0
            ELSE (
                SELECT fx.rate_to_chf
                FROM fx_rates fx
                WHERE fx.currency = lower(w.currency)
                  AND fx.rate_date <= date(t.date_created, 'unixepoch')
                ORDER BY fx.rate_date DESC
                LIMIT 1
            )
        END AS rate_to_chf,
        -- Europe/Zurich local time (CEST: last Sunday Mar 01:00 UTC .. last Sunday Oct 01:00 UTC)
        datetime(
            t.date_created,
            'unixepoch',
            CASE
                WHEN datetime(t.date_created, 'unixepoch') >= datetime(strftime('%Y', t.date_created, 'unixepoch') || '-03-31', 'weekday 0', '-7 days', '+1 hours')
                 AND datetime(t.date_created, 'unixepoch') <  datetime(strftime('%Y', t.date_created, 'unixepoch') || '-10-31', 'weekday 0', '-7 days', '+1 hours')
                THEN '+2 hours'
                ELSE '+1 hours'
            END
        ) AS date_zurich
    FROM transactions t
    LEFT JOIN wallets w ON t.wallet_fk = w.wallet_pk
    LEFT JOIN categories c ON t.category_fk = c.category_pk
    LEFT JOIN objectives o ON t.objective_fk = o.objective_pk
)
SELECT
    transaction_pk,
    name AS title,
    note,
    amount,                                                     -- original wallet currency amount (negative = expense, positive = refund)
    amount * rate_to_chf AS amount_chf,                         -- unrounded CHF conversion (signed)
    -amount * rate_to_chf AS spent_chf,                         -- net spending in CHF (positive = expense, negative = refund)
    currency,
    rate_to_chf,
    account,
    CASE WHEN account LIKE '%C' THEN 'Cash' ELSE 'Card' END AS payment_method, -- '*C' wallets (CHFC, EURC) = Cash
    category,
    objective,                                                  -- trip/goal name (nullable)
    income,                                                     -- 0 = expense, 1 = income
    paid,                                                       -- 1 = settled, 0 = future/unpaid
    type,                                                       -- NULL = default, 1 = subscription, 2 = repetitive
    paired_transaction_fk,                                      -- non-NULL = paired wallet transfer
    date_created,                                               -- Unix epoch seconds (UTC)
    date_zurich,                                                -- Europe/Zurich local datetime
    strftime('%Y', date_zurich) AS year,
    strftime('%m', date_zurich) AS month,
    CASE strftime('%m', date_zurich)
        WHEN '01' THEN 'Jan'
        WHEN '02' THEN 'Feb'
        WHEN '03' THEN 'Mar'
        WHEN '04' THEN 'Apr'
        WHEN '05' THEN 'May'
        WHEN '06' THEN 'Jun'
        WHEN '07' THEN 'Jul'
        WHEN '08' THEN 'Aug'
        WHEN '09' THEN 'Sep'
        WHEN '10' THEN 'Oct'
        WHEN '11' THEN 'Nov'
        WHEN '12' THEN 'Dec'
    END AS month_name
FROM tx_enriched
WHERE paid = 1
  AND paired_transaction_fk IS NULL
  AND date_zurich < strftime(
      '%Y-%m-01',
      'now',
      CASE
          WHEN datetime('now') >= datetime(strftime('%Y', 'now') || '-03-31', 'weekday 0', '-7 days', '+1 hours')
           AND datetime('now') <  datetime(strftime('%Y', 'now') || '-10-31', 'weekday 0', '-7 days', '+1 hours')
          THEN '+2 hours'
          ELSE '+1 hours'
      END
  );
