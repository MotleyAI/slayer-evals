# SLayer capability benchmark report

> **Single-trial snapshot:** every task ran once per profile and model, so individual rates are noisy.

| Run |  |
| --- | --- |
| SLayer | 1.0.2 |
| Agent SDK | 0.2.163 |
| Models | claude-opus-5-5 |
| Profiles | slayer, slayer+python |
| Mode | repeat, N = 1 |
| Budgets | 60 turns, 900 s per trial |
| Auth | subscription |
| Started | 2026-10-06 12:38 UTC |
| Trials | 50 |

A trial passes when its answer is **correct** (the submitted table matches the truth) and is a **single query**'s result (one SLayer query's own result matches the truth, with no combining or post-processing). The flag columns count trials that used Python, handed SLayer raw SQL, edited models, hit SLayer errors or ran several queries; they do not affect passing.

## `slayer` · `claude-opus-5-5`

| Row | Feature | Tasks | Trials | Correct | Single query | Passed | Python | Raw SQL | Model edits | SLayer errors | Several queries |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Q1 | Coarser grain in the same query | 1 | 1 | 1 | 1 | 1 | 0 | 0 | 0 | 0 | 0 |
| Q2 | Arithmetic across grains | 1 | 1 | 1 | 1 | 1 | 0 | 0 | 0 | 0 | 0 |
| Q3 | Re-aggregation | 1 | 1 | 1 | 1 | 1 | 0 | 0 | 0 | 0 | 1 |
| Q4 | Transforms / time shift | 2 | 2 | 2 | 2 | 2 | 0 | 0 | 0 | 0 | 1 |
| Q5 | Calculated dimensions, filters, order | 1 | 1 | 1 | 1 | 1 | 0 | 0 | 0 | 0 | 1 |
| Q6 | Fields from many models, fan-out safe | 1 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 1 |
| Q7 | Deep composition | 1 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| Q8 | Population inference | 1 | 1 | 1 | 1 | 1 | 0 | 0 | 0 | 0 | 0 |
| Q9 | No silently wrong numbers | 1 | 1 | 1 | 1 | 1 | 0 | 0 | 0 | 0 | 0 |
| Q10 | Filters across one-to-many joins | 1 | 1 | 1 | 1 | 1 | 0 | 0 | 0 | 0 | 1 |
| Q11 | Rolling time windows | 1 | 1 | 1 | 0 | 0 | 0 | 1 | 0 | 0 | 0 |
| Q12 | Aggregates as arguments | 1 | 1 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 1 |
| Q13 | Order by what you don't show | 1 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| Q14 | Ranking and streaks | 1 | 1 | 1 | 1 | 1 | 0 | 0 | 0 | 0 | 1 |
| Q15 | Multi-stage queries | 1 | 1 | 1 | 1 | 1 | 0 | 0 | 0 | 0 | 1 |
| Q16 | Inline model extension | 1 | 1 | 1 | 1 | 1 | 0 | 0 | 0 | 0 | 0 |
| Q17 | Saved measures that compose | 1 | 1 | 1 | 1 | 1 | 0 | 0 | 0 | 1 | 1 |
| Q18 | Time-bucket safety | 1 | 1 | 1 | 1 | 1 | 0 | 0 | 0 | 1 | 0 |
| Q19 | Agent & API surface | not covered |  |  |  |  |  |  |  |  |  |
| Q20 | Relative & typed filters | 1 | 1 | 1 | 1 | 1 | 0 | 0 | 0 | 0 | 1 |
| Q21 | Calendar expressions | 1 | 1 | 1 | 1 | 1 | 0 | 1 | 0 | 1 | 1 |
| Q22 | Nested source data | not covered |  |  |  |  |  |  |  |  |  |
| Q23 | Saved queries & refinement | 1 | 1 | 1 | 1 | 1 | 0 | 0 | 0 | 0 | 1 |
| Q24 | Nested / hierarchical results | 1 | 1 | 1 | 1 | 1 | 0 | 0 | 0 | 0 | 1 |
| Q25 | Explicit aggregate locality | 1 | 1 | 1 | 1 | 1 | 0 | 0 | 0 | 0 | 1 |

| Task | Row | Pass rate | pass^1 |
| --- | --- | --- | --- |
| q1-region-total | Q1 | 1/1 | 1.000 |
| q10-bronze-or-ok | Q10 | 1/1 | 1.000 |
| q11-rolling-customers | Q11 | 0/1 | 0.000 |
| q12-net-revenue | Q12 | 0/1 | 0.000 |
| q13-top-cities-count | Q13 | 0/1 | 0.000 |
| q14-top-customer-per-region | Q14 | 1/1 | 1.000 |
| q15-revenue-bands | Q15 | 1/1 | 1.000 |
| q16-order-size | Q16 | 1/1 | 1.000 |
| q17-running-aov | Q17 | 1/1 | 1.000 |
| q18-day-of-monthly | Q18 | 1/1 | 1.000 |
| q2-city-share | Q2 | 1/1 | 1.000 |
| q20-quarter-region | Q20 | 1/1 | 1.000 |
| q21-weekday-revenue | Q21 | 1/1 | 1.000 |
| q23-monthly-by-region | Q23 | 1/1 | 1.000 |
| q24-top-two-per-region | Q24 | 1/1 | 1.000 |
| q25-credit-per-order | Q25 | 1/1 | 1.000 |
| q3-avg-city-revenue | Q3 | 1/1 | 1.000 |
| q4-prior-year | Q4 | 1/1 | 1.000 |
| q4-running-total | Q4 | 1/1 | 1.000 |
| q5-spend-band | Q5 | 1/1 | 1.000 |
| q6-region-credit | Q6 | 0/1 | 0.000 |
| q7-cumulative-change | Q7 | 0/1 | 0.000 |
| q8-tier-customers | Q8 | 1/1 | 1.000 |
| q9-credit-by-status | Q9 | 1/1 | 1.000 |

## `slayer+python` · `claude-opus-5-5`

| Row | Feature | Tasks | Trials | Correct | Single query | Passed | Python | Raw SQL | Model edits | SLayer errors | Several queries |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Q1 | Coarser grain in the same query | 1 | 1 | 1 | 1 | 1 | 0 | 0 | 0 | 0 | 0 |
| Q2 | Arithmetic across grains | 1 | 1 | 1 | 1 | 1 | 0 | 0 | 0 | 0 | 1 |
| Q3 | Re-aggregation | 1 | 1 | 1 | 1 | 1 | 0 | 0 | 0 | 0 | 1 |
| Q4 | Transforms / time shift | 2 | 2 | 2 | 1 | 1 | 0 | 0 | 0 | 0 | 2 |
| Q5 | Calculated dimensions, filters, order | 1 | 1 | 1 | 1 | 1 | 0 | 0 | 0 | 0 | 1 |
| Q6 | Fields from many models, fan-out safe | 1 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 1 | 1 |
| Q7 | Deep composition | 1 | 1 | 1 | 0 | 0 | 1 | 0 | 0 | 0 | 0 |
| Q8 | Population inference | 1 | 1 | 1 | 1 | 1 | 0 | 0 | 0 | 0 | 0 |
| Q9 | No silently wrong numbers | 1 | 1 | 1 | 1 | 1 | 0 | 0 | 0 | 0 | 0 |
| Q10 | Filters across one-to-many joins | 1 | 1 | 1 | 1 | 1 | 0 | 0 | 0 | 1 | 1 |
| Q11 | Rolling time windows | 1 | 1 | 1 | 0 | 0 | 1 | 0 | 0 | 0 | 1 |
| Q12 | Aggregates as arguments | 1 | 1 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 |
| Q13 | Order by what you don't show | 1 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| Q14 | Ranking and streaks | 1 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 1 |
| Q15 | Multi-stage queries | 1 | 1 | 1 | 1 | 1 | 0 | 0 | 0 | 0 | 1 |
| Q16 | Inline model extension | 1 | 1 | 1 | 1 | 1 | 0 | 0 | 0 | 0 | 0 |
| Q17 | Saved measures that compose | 1 | 1 | 1 | 1 | 1 | 0 | 0 | 0 | 1 | 1 |
| Q18 | Time-bucket safety | 1 | 1 | 1 | 1 | 1 | 0 | 0 | 0 | 1 | 0 |
| Q19 | Agent & API surface | not covered |  |  |  |  |  |  |  |  |  |
| Q20 | Relative & typed filters | 1 | 1 | 1 | 1 | 1 | 0 | 0 | 0 | 0 | 1 |
| Q21 | Calendar expressions | 1 | 1 | 1 | 1 | 1 | 0 | 1 | 0 | 1 | 1 |
| Q22 | Nested source data | not covered |  |  |  |  |  |  |  |  |  |
| Q23 | Saved queries & refinement | 1 | 1 | 1 | 1 | 1 | 0 | 0 | 0 | 0 | 1 |
| Q24 | Nested / hierarchical results | 1 | 1 | 1 | 1 | 1 | 0 | 0 | 0 | 1 | 1 |
| Q25 | Explicit aggregate locality | 1 | 1 | 1 | 1 | 1 | 0 | 0 | 0 | 0 | 1 |

| Task | Row | Pass rate | pass^1 |
| --- | --- | --- | --- |
| q1-region-total | Q1 | 1/1 | 1.000 |
| q10-bronze-or-ok | Q10 | 1/1 | 1.000 |
| q11-rolling-customers | Q11 | 0/1 | 0.000 |
| q12-net-revenue | Q12 | 0/1 | 0.000 |
| q13-top-cities-count | Q13 | 0/1 | 0.000 |
| q14-top-customer-per-region | Q14 | 0/1 | 0.000 |
| q15-revenue-bands | Q15 | 1/1 | 1.000 |
| q16-order-size | Q16 | 1/1 | 1.000 |
| q17-running-aov | Q17 | 1/1 | 1.000 |
| q18-day-of-monthly | Q18 | 1/1 | 1.000 |
| q2-city-share | Q2 | 1/1 | 1.000 |
| q20-quarter-region | Q20 | 1/1 | 1.000 |
| q21-weekday-revenue | Q21 | 1/1 | 1.000 |
| q23-monthly-by-region | Q23 | 1/1 | 1.000 |
| q24-top-two-per-region | Q24 | 1/1 | 1.000 |
| q25-credit-per-order | Q25 | 1/1 | 1.000 |
| q3-avg-city-revenue | Q3 | 1/1 | 1.000 |
| q4-prior-year | Q4 | 0/1 | 0.000 |
| q4-running-total | Q4 | 1/1 | 1.000 |
| q5-spend-band | Q5 | 1/1 | 1.000 |
| q6-region-credit | Q6 | 0/1 | 0.000 |
| q7-cumulative-change | Q7 | 0/1 | 0.000 |
| q8-tier-customers | Q8 | 1/1 | 1.000 |
| q9-credit-by-status | Q9 | 1/1 | 1.000 |

## Expected failures (xfail)

These tasks run but are left out of the pass counts until the linked issue is fixed.

| Task | Issue | Profile | Model | Trials | Passed |
| --- | --- | --- | --- | --- | --- |
| q20-last-three-months | DEV-2058 | slayer | claude-opus-5-5 | 1 | 0 |
| q20-last-three-months | DEV-2058 | slayer+python | claude-opus-5-5 | 1 | 0 |

## Totals

| Total | Value |
| --- | --- |
| Trials | 50 |
| Input tokens | 488 |
| Output tokens | 51791 |
| Cache read tokens | 5938079 |
| Cache write tokens | 255980 |
| Cost (USD) | 3.51 |
| Duration (s) | 985 |

## Failed trials

- **q11-rolling-customers** (Q11) · slayer · claude-opus-5-5 · trial 1 · submitted
  - single query: no single query returns the answer (last, query #7: no result column has the values of 'month')
  - flags: Raw SQL
  - #1 `inspect` {"entity_type":"model"} → ok
  - #2 `inspect` {"entity_type":"model","reference":["bench.orders","bench.time_spine"],"num_rows":5} → ok
  - #3 `search` {"question":"rolling window distinct count customers last 90 days per month"} → ok
  - #4 `inspect` {"entity_type":"memory","reference":"help.intro"} → ok
  - #5 `inspect` {"entity_type":"memory","reference":"memory:help.intro"} → ok
  - #6 `inspect` {"entity_type":"model","reference":"bench.orders","compact":false,"show_sql":true} → ok
  - #7 `query` {'name': 'rolling90', 'data_source': 'bench', 'sql': "SELECT m.month_end, COUNT(DISTINCT o.customer_id) AS customers, COUNT(DISTINCT CASE WHEN o.status='ok' THEN o.customer_id END) AS ok_customers FROM (SELECT CAST(last_day(make_date(2025,… → 12 rows
- **q11-rolling-customers** (Q11) · slayer+python · claude-opus-5-5 · trial 1 · submitted
  - single query: no single query returns the answer (last, query #5: result has 20 rows, truth has 12)
  - flags: Python, Several queries
  - #1 `inspect` {"entity_type":"model"} → ok
  - #2 `inspect` {"entity_type":"model","reference":["bench.orders","bench.time_spine"],"show_sql":true} → ok
  - #3 `inspect` {"entity_type":"model","reference":"bench.orders","sections":["columns"]} → ok
  - #4 `inspect_model` {"model_name":"orders","sections":["columns","samples"]} → ok
  - #5 `query` orders dimensions=["customer_id","order_date"] filters=["order_date >= '2024-09-01'"] → 20 rows, truncated warning
  - #6 `query` orders dimensions=["customer_id","order_date"] filters=["order_date >= '2024-09-01'"] → ok
- **q12-net-revenue** (Q12) · slayer · claude-opus-5-5 · trial 1 · submitted
  - correct: no result column has the values of 'net_revenue'
  - single query: no single query returns the answer (last, query #4: result has 2 rows, truth has 5)
  - flags: Raw SQL, Several queries
  - #1 `inspect` {"entity_type":"model"} → ok
  - #2 `inspect` {"entity_type":"model","reference":["customers","orders","regions"],"compact":false} → ok
  - #3 `query` {'source_name': 'orders', 'columns': [{'name': 'net_amt', 'sql': 'amount - COALESCE(customers.discount, 0)', 'type': 'DOUBLE'}]} dimensions=["customers.regions.name"] measures=[{"formula":"sum(net_amt)","name":"net"},{"formula":"count(*)",… → 5 rows
  - #4 `query` {'source_name': 'orders', 'columns': [{'name': 'has_cust', 'sql': 'customers.id IS NOT NULL', 'type': 'BOOLEAN'}, {'name': 'disc_null', 'sql': 'customers.discount IS NULL', 'type': 'BOOLEAN'}]} dimensions=["has_cust","disc_null"] measures=… → 2 rows
- **q12-net-revenue** (Q12) · slayer+python · claude-opus-5-5 · trial 1 · submitted
  - correct: no result column has the values of 'net_revenue'
  - #1 `inspect` {"entity_type":"model"} → ok
  - #2 `inspect` {"entity_type":"model","reference":["orders","customers","regions"],"compact":false} → ok
  - #3 `query` orders dimensions=["customers.regions.name"] measures=[{"formula":"sum(amount - coalesce(customers.discount, 0))","name":"net"},{"formula":"sum(amount - customers.discount)","name":"net_raw"},{"formula":"count(*)","name":"n"},{"formula":"c… → 5 rows
- **q13-top-cities-count** (Q13) · slayer · claude-opus-5-5 · trial 1 · submitted
  - single query: no single query returns the answer (last, query #3: result has 3 columns, expected exactly 2)
  - #1 `inspect` {"entity_type":"model"} → ok
  - #2 `inspect` {"entity_type":"model","reference":["orders","customers","orders_flat"]} → ok
  - #3 `query` orders dimensions=["customers.city"] measures=["sum(amount)","count(*)"] order=[{"column":"sum(amount)","direction":"desc"}] → 11 rows
- **q13-top-cities-count** (Q13) · slayer+python · claude-opus-5-5 · trial 1 · submitted
  - single query: no single query returns the answer (last, query #3: result has 3 columns, expected exactly 2)
  - #1 `inspect` {"entity_type":"model"} → ok
  - #2 `inspect` {"entity_type":"model","reference":["orders","customers","orders_flat"]} → ok
  - #3 `query` orders dimensions=["customers.city"] measures=["sum(amount)","count(*)"] order=[{"column":"sum(amount)","direction":"desc"}] → 11 rows
- **q14-top-customer-per-region** (Q14) · slayer+python · claude-opus-5-5 · trial 1 · submitted
  - single query: no single query returns the answer (last, query #4: result has 1 rows, truth has 4)
  - flags: Several queries
  - #1 `inspect` {"entity_type":"model"} → ok
  - #2 `inspect` {"entity_type":"model","reference":["customers","orders","regions"],"compact":false} → ok
  - #3 `query` orders dimensions=["customers.region_id","customers.regions.name","customer_id"] measures=[{"formula":"sum(amount)","name":"rev"}] filters=["customers.region_id is not null"] order=[{"column":"rev","direction":"desc"}] → 20 rows, truncated warning
  - #4 `query` customers measures=[{"formula":"count(*)","name":"n"},{"formula":"count_distinct(id)","name":"nd"},{"formula":"count(region_id)","name":"nr"}] → 1 rows
- **q20-last-three-months** (Q20) · slayer · claude-opus-5-5 · trial 1 · submitted · xfail DEV-2058
  - correct: truth row ['2025-10-01', 9750.920000000007] has no match in the result
  - single query: no single query returns the answer (last, query #5: result has 1 rows, truth has 3)
  - flags: Several queries
  - #1 `inspect` {"entity_type":"model"} → ok
  - #2 `inspect` {"entity_type":"model","reference":["bench.orders","bench.monthly_rev"]} → ok
  - #3 `query` orders time_dimensions=["month(order_date)"] measures=["sum(amount)","count(*)"] order=[{"column":"order_date","direction":"desc"}] → 20 rows, truncated warning
  - #4 `query` orders measures=["max(order_date)","min(order_date)","count(*)"] filters=["order_date >= '2026-01-01'"] → 1 rows
  - #5 `query` orders measures=["max(order_date)"] → 1 rows
- **q20-last-three-months** (Q20) · slayer+python · claude-opus-5-5 · trial 1 · submitted · xfail DEV-2058
  - correct: result has 0 rows, truth has 3
  - single query: no single query returns the answer (last, query #4: result has 7 rows, truth has 3)
  - #1 `inspect` {"entity_type":"model"} → ok
  - #2 `inspect` {"entity_type":"model","reference":["bench.orders","bench.monthly_rev"],"compact":false} → ok
  - #3 `search` {"question":"revenue last complete months order status"} → ok
  - #4 `query` orders time_dimensions=[{"dimension":"order_date","granularity":"month","date_range":["2025-06-01","2026-12-31"]}] measures=["sum(amount)","count(*)"] → 7 rows
- **q4-prior-year** (Q4) · slayer+python · claude-opus-5-5 · trial 1 · submitted
  - single query: no single query returns the answer (last, query #4: result has 14 rows, truth has 3)
  - flags: Several queries
  - #1 `inspect` {"entity_type":"model"} → ok
  - #2 `inspect` {"entity_type":"model","reference":"bench.orders"} → ok
  - #3 `query` orders time_dimensions=[{"dimension":"order_date","granularity":"month","date_range":["2024-01-01","2025-03-31"]}] measures=[{"formula":"sum(amount)","name":"revenue"}] order=[{"column":"order_date","direction":"asc"}] → 14 rows
  - #4 `query` orders time_dimensions=[{"dimension":"order_date","granularity":"month"}] measures=[{"formula":"sum(amount)","name":"revenue"},{"formula":"time_shift(sum(amount), -1, 'year')","name":"prev"}] filters=["order_date >= '2024-01-01'","order_da… → 14 rows
- **q6-region-credit** (Q6) · slayer · claude-opus-5-5 · trial 1 · submitted
  - single query: no single query returns the answer (last, query #4: result has 1 rows, truth has 5)
  - flags: Several queries
  - #1 `inspect` {"entity_type":"model","compact":false} → ok
  - #2 `query` orders dimensions=["customers.regions.name"] measures=["sum(amount)"] → 5 rows
  - #3 `query` customers dimensions=["regions.name"] measures=["sum(credit)","count(*)"] → 5 rows
  - #4 `query` customers measures=["count(*)","count_distinct(id)"] → 1 rows
- **q6-region-credit** (Q6) · slayer+python · claude-opus-5-5 · trial 1 · submitted
  - single query: no single query returns the answer (last, query #5: no result column has the values of 'region', 'revenue')
  - flags: SLayer errors, Several queries
  - #1 `inspect` {"entity_type":"model","compact":false} → ok
  - #2 `inspect` {"entity_type":"model","reference":["bench.orders","bench.customers","bench.regions"],"sections":["columns","joins"]} → ok
  - #3 `query` orders dimensions=["customers.regions.name"] measures=[{"formula":"sum(amount)","name":"revenue"},{"formula":"count(*)","name":"n"}] → 5 rows
  - #4 `query` customers dimensions=["regions.name"] measures=[{"formula":"sum(credit)","name":"credit"},{"formula":"count(*)","name":"n"},{"formula":"count_distinct(id)","name":"nd"}] → error MeasureNameCollidesWithColumnError
  - #5 `query` customers dimensions=["regions.name"] measures=[{"formula":"sum(credit)","name":"total_credit"},{"formula":"count(*)","name":"n"},{"formula":"count_distinct(id)","name":"nd"}] → 5 rows
- **q7-cumulative-change** (Q7) · slayer · claude-opus-5-5 · trial 1 · submitted
  - single query: no single query returns the answer (last, query #3: result has 13 rows, truth has 12)
  - #1 `inspect` {"entity_type":"model"} → ok
  - #2 `inspect` {"entity_type":"model","reference":"bench.orders"} → ok
  - #3 `query` orders time_dimensions=[{"dimension":"order_date","granularity":"month","date_range":["2024-12-01","2025-12-31"]}] measures=[{"formula":"sum(amount)","name":"revenue"},{"formula":"change(sum(amount))","name":"chg"},{"formula":"cumsum(chang… → 13 rows
- **q7-cumulative-change** (Q7) · slayer+python · claude-opus-5-5 · trial 1 · submitted
  - single query: no single query returns the answer (last, query #4: result has 14 rows, truth has 12)
  - flags: Python
  - #1 `inspect` {"entity_type":"model"} → ok
  - #2 `inspect` {"entity_type":"model","reference":"bench.orders"} → ok
  - #3 `inspect` {"entity_type":"model","reference":"bench.monthly_rev"} → ok
  - #4 `query` orders time_dimensions=[{"dimension":"order_date","granularity":"month","date_range":["2024-11-01","2026-01-31"]}] measures=["sum(amount)","count(*)"] order=[{"column":"order_date","direction":"asc"}] → 14 rows
