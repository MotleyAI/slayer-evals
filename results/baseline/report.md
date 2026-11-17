# SLayer capability benchmark report

> **Single-trial snapshot:** every task ran once per profile and model, so individual rates are noisy.

| Run |  |
| --- | --- |
| SLayer | 1.8.2 (188 trials), 1.8.5 (282 trials) |
| Agent SDK | 0.2.163 |
| Models | claude-opus-5-5 |
| Profiles | slayer, slayer+python, sql+python, motley, motley+python |
| Mode | repeat, N = 1 |
| Budgets | 60 turns, 900 s per trial |
| Auth | subscription |
| Started | 2026-11-17 10:22 UTC |
| Trials | 470 |
| Motley MCP | http://localhost:8100/api/v1/mcp/ |
| MCP server info | motley 1.30.0 |

A trial passes when its answer is **correct** (the submitted table matches the truth) and is a **single query**'s result (the own result of one SLayer query or one SQL statement matches the truth, with no combining or post-processing). The flag columns count trials that used Python, used raw SQL, edited models, hit query errors or ran several queries; they do not affect passing.

## Results by suite

**Correct** is the cross-profile comparison: every profile can reach a correct answer. **Single query** is not equally hard across profiles, since one raw SQL statement can express almost any answer, while SLayer needs its DSL to do the same in one query. Expected failures (xfail) are left out.

| Suite | Profile | Model | Trials | Correct | Single query | Passed |
| --- | --- | --- | --- | --- | --- | --- |
| capability | `slayer` | `claude-opus-5-5` | 32 | 31 | 30 | 30 |
| capability | `slayer+python` | `claude-opus-5-5` | 32 | 31 | 30 | 30 |
| capability | `sql+python` | `claude-opus-5-5` | 33 | 29 | 25 | 25 |
| capability | `motley` | `claude-opus-5-5` | 31 | 30 | 27 | 27 |
| capability | `motley+python` | `claude-opus-5-5` | 31 | 30 | 26 | 26 |
| combo | `slayer` | `claude-opus-5-5` | 15 | 15 | 14 | 14 |
| combo | `slayer+python` | `claude-opus-5-5` | 15 | 15 | 13 | 13 |
| combo | `sql+python` | `claude-opus-5-5` | 15 | 13 | 7 | 7 |
| combo | `motley` | `claude-opus-5-5` | 15 | 15 | 12 | 12 |
| combo | `motley+python` | `claude-opus-5-5` | 15 | 15 | 10 | 10 |
| trap | `slayer` | `claude-opus-5-5` | 21 | 21 | 21 | 21 |
| trap | `slayer+python` | `claude-opus-5-5` | 21 | 21 | 21 | 21 |
| trap | `sql+python` | `claude-opus-5-5` | 21 | 21 | 20 | 20 |
| trap | `motley` | `claude-opus-5-5` | 21 | 21 | 19 | 19 |
| trap | `motley+python` | `claude-opus-5-5` | 21 | 21 | 18 | 18 |
| jaffle | `slayer` | `claude-opus-5-5` | 24 | 23 | 19 | 18 |
| jaffle | `slayer+python` | `claude-opus-5-5` | 24 | 22 | 17 | 16 |
| jaffle | `sql+python` | `claude-opus-5-5` | 24 | 23 | 17 | 17 |
| jaffle | `motley` | `claude-opus-5-5` | 24 | 23 | 14 | 14 |
| jaffle | `motley+python` | `claude-opus-5-5` | 24 | 23 | 12 | 12 |

### Traps by pitfall

| Pitfall | Profile | Model | Trials | Correct |
| --- | --- | --- | --- | --- |
| fan_out | `slayer` | `claude-opus-5-5` | 2 | 2 |
| fan_out | `slayer+python` | `claude-opus-5-5` | 2 | 2 |
| fan_out | `sql+python` | `claude-opus-5-5` | 2 | 2 |
| fan_out | `motley` | `claude-opus-5-5` | 2 | 2 |
| fan_out | `motley+python` | `claude-opus-5-5` | 2 | 2 |
| count_after_join | `slayer` | `claude-opus-5-5` | 1 | 1 |
| count_after_join | `slayer+python` | `claude-opus-5-5` | 1 | 1 |
| count_after_join | `sql+python` | `claude-opus-5-5` | 1 | 1 |
| count_after_join | `motley` | `claude-opus-5-5` | 1 | 1 |
| count_after_join | `motley+python` | `claude-opus-5-5` | 1 | 1 |
| chasm | `slayer` | `claude-opus-5-5` | 1 | 1 |
| chasm | `slayer+python` | `claude-opus-5-5` | 1 | 1 |
| chasm | `sql+python` | `claude-opus-5-5` | 1 | 1 |
| chasm | `motley` | `claude-opus-5-5` | 1 | 1 |
| chasm | `motley+python` | `claude-opus-5-5` | 1 | 1 |
| bridge | `slayer` | `claude-opus-5-5` | 1 | 1 |
| bridge | `slayer+python` | `claude-opus-5-5` | 1 | 1 |
| bridge | `sql+python` | `claude-opus-5-5` | 1 | 1 |
| bridge | `motley` | `claude-opus-5-5` | 1 | 1 |
| bridge | `motley+python` | `claude-opus-5-5` | 1 | 1 |
| non_unique_key | `slayer` | `claude-opus-5-5` | 1 | 1 |
| non_unique_key | `slayer+python` | `claude-opus-5-5` | 1 | 1 |
| non_unique_key | `sql+python` | `claude-opus-5-5` | 1 | 1 |
| non_unique_key | `motley` | `claude-opus-5-5` | 1 | 1 |
| non_unique_key | `motley+python` | `claude-opus-5-5` | 1 | 1 |
| outer_join_filter | `slayer` | `claude-opus-5-5` | 1 | 1 |
| outer_join_filter | `slayer+python` | `claude-opus-5-5` | 1 | 1 |
| outer_join_filter | `sql+python` | `claude-opus-5-5` | 1 | 1 |
| outer_join_filter | `motley` | `claude-opus-5-5` | 1 | 1 |
| outer_join_filter | `motley+python` | `claude-opus-5-5` | 1 | 1 |
| not_in_null | `slayer` | `claude-opus-5-5` | 1 | 1 |
| not_in_null | `slayer+python` | `claude-opus-5-5` | 1 | 1 |
| not_in_null | `sql+python` | `claude-opus-5-5` | 1 | 1 |
| not_in_null | `motley` | `claude-opus-5-5` | 1 | 1 |
| not_in_null | `motley+python` | `claude-opus-5-5` | 1 | 1 |
| count_outer_join | `slayer` | `claude-opus-5-5` | 1 | 1 |
| count_outer_join | `slayer+python` | `claude-opus-5-5` | 1 | 1 |
| count_outer_join | `sql+python` | `claude-opus-5-5` | 1 | 1 |
| count_outer_join | `motley` | `claude-opus-5-5` | 1 | 1 |
| count_outer_join | `motley+python` | `claude-opus-5-5` | 1 | 1 |
| filtered_total | `slayer` | `claude-opus-5-5` | 1 | 1 |
| filtered_total | `slayer+python` | `claude-opus-5-5` | 1 | 1 |
| filtered_total | `sql+python` | `claude-opus-5-5` | 1 | 1 |
| filtered_total | `motley` | `claude-opus-5-5` | 1 | 1 |
| filtered_total | `motley+python` | `claude-opus-5-5` | 1 | 1 |
| distinct_reagg | `slayer` | `claude-opus-5-5` | 1 | 1 |
| distinct_reagg | `slayer+python` | `claude-opus-5-5` | 1 | 1 |
| distinct_reagg | `sql+python` | `claude-opus-5-5` | 1 | 1 |
| distinct_reagg | `motley` | `claude-opus-5-5` | 1 | 1 |
| distinct_reagg | `motley+python` | `claude-opus-5-5` | 1 | 1 |
| missing_periods | `slayer` | `claude-opus-5-5` | 1 | 1 |
| missing_periods | `slayer+python` | `claude-opus-5-5` | 1 | 1 |
| missing_periods | `sql+python` | `claude-opus-5-5` | 1 | 1 |
| missing_periods | `motley` | `claude-opus-5-5` | 1 | 1 |
| missing_periods | `motley+python` | `claude-opus-5-5` | 1 | 1 |
| filter_before_window | `slayer` | `claude-opus-5-5` | 2 | 2 |
| filter_before_window | `slayer+python` | `claude-opus-5-5` | 2 | 2 |
| filter_before_window | `sql+python` | `claude-opus-5-5` | 2 | 2 |
| filter_before_window | `motley` | `claude-opus-5-5` | 2 | 2 |
| filter_before_window | `motley+python` | `claude-opus-5-5` | 2 | 2 |
| rows_window_gap | `slayer` | `claude-opus-5-5` | 1 | 1 |
| rows_window_gap | `slayer+python` | `claude-opus-5-5` | 1 | 1 |
| rows_window_gap | `sql+python` | `claude-opus-5-5` | 1 | 1 |
| rows_window_gap | `motley` | `claude-opus-5-5` | 1 | 1 |
| rows_window_gap | `motley+python` | `claude-opus-5-5` | 1 | 1 |
| timestamp_bounds | `slayer` | `claude-opus-5-5` | 1 | 1 |
| timestamp_bounds | `slayer+python` | `claude-opus-5-5` | 1 | 1 |
| timestamp_bounds | `sql+python` | `claude-opus-5-5` | 1 | 1 |
| timestamp_bounds | `motley` | `claude-opus-5-5` | 1 | 1 |
| timestamp_bounds | `motley+python` | `claude-opus-5-5` | 1 | 1 |
| avg_of_avgs | `slayer` | `claude-opus-5-5` | 1 | 1 |
| avg_of_avgs | `slayer+python` | `claude-opus-5-5` | 1 | 1 |
| avg_of_avgs | `sql+python` | `claude-opus-5-5` | 1 | 1 |
| avg_of_avgs | `motley` | `claude-opus-5-5` | 1 | 1 |
| avg_of_avgs | `motley+python` | `claude-opus-5-5` | 1 | 1 |
| count_after_unnest | `slayer` | `claude-opus-5-5` | 1 | 1 |
| count_after_unnest | `slayer+python` | `claude-opus-5-5` | 1 | 1 |
| count_after_unnest | `sql+python` | `claude-opus-5-5` | 1 | 1 |
| count_after_unnest | `motley` | `claude-opus-5-5` | 1 | 1 |
| count_after_unnest | `motley+python` | `claude-opus-5-5` | 1 | 1 |
| unnest_fan_out | `slayer` | `claude-opus-5-5` | 1 | 1 |
| unnest_fan_out | `slayer+python` | `claude-opus-5-5` | 1 | 1 |
| unnest_fan_out | `sql+python` | `claude-opus-5-5` | 1 | 1 |
| unnest_fan_out | `motley` | `claude-opus-5-5` | 1 | 1 |
| unnest_fan_out | `motley+python` | `claude-opus-5-5` | 1 | 1 |
| null_element | `slayer` | `claude-opus-5-5` | 1 | 1 |
| null_element | `slayer+python` | `claude-opus-5-5` | 1 | 1 |
| null_element | `sql+python` | `claude-opus-5-5` | 1 | 1 |
| null_element | `motley` | `claude-opus-5-5` | 1 | 1 |
| null_element | `motley+python` | `claude-opus-5-5` | 1 | 1 |
| same_element_and | `slayer` | `claude-opus-5-5` | 1 | 1 |
| same_element_and | `slayer+python` | `claude-opus-5-5` | 1 | 1 |
| same_element_and | `sql+python` | `claude-opus-5-5` | 1 | 1 |
| same_element_and | `motley` | `claude-opus-5-5` | 1 | 1 |
| same_element_and | `motley+python` | `claude-opus-5-5` | 1 | 1 |

## Jaffle Shop sub-suite

Yann's nao-vs-Motley questions over the Jaffle Shop database. Several depend on business rules (revenue is pre-tax, the data cut-off, what a new customer is): the raw-SQL profile receives the business rules in its system prompt, while the SLayer and Motley profiles must find them through search of the stored memories. Expected failures (xfail) are left out.

| Task | Profile | Model | Trials | Correct | Single query | Passed |
| --- | --- | --- | --- | --- | --- | --- |
| j-c01-peak-weekday-hour | `motley` | `claude-opus-5-5` | 1 | 1 | 0 | 0 |
| j-c01-peak-weekday-hour | `motley+python` | `claude-opus-5-5` | 1 | 1 | 0 | 0 |
| j-c01-peak-weekday-hour | `slayer` | `claude-opus-5-5` | 1 | 1 | 0 | 0 |
| j-c01-peak-weekday-hour | `slayer+python` | `claude-opus-5-5` | 1 | 1 | 0 | 0 |
| j-c01-peak-weekday-hour | `sql+python` | `claude-opus-5-5` | 1 | 1 | 0 | 0 |
| j-c02-order-value-bands | `motley` | `claude-opus-5-5` | 1 | 1 | 1 | 1 |
| j-c02-order-value-bands | `motley+python` | `claude-opus-5-5` | 1 | 1 | 1 | 1 |
| j-c02-order-value-bands | `slayer` | `claude-opus-5-5` | 1 | 1 | 1 | 1 |
| j-c02-order-value-bands | `slayer+python` | `claude-opus-5-5` | 1 | 1 | 1 | 1 |
| j-c02-order-value-bands | `sql+python` | `claude-opus-5-5` | 1 | 1 | 1 | 1 |
| j-c03-basket-mix | `motley` | `claude-opus-5-5` | 1 | 1 | 1 | 1 |
| j-c03-basket-mix | `motley+python` | `claude-opus-5-5` | 1 | 1 | 1 | 1 |
| j-c03-basket-mix | `slayer` | `claude-opus-5-5` | 1 | 1 | 1 | 1 |
| j-c03-basket-mix | `slayer+python` | `claude-opus-5-5` | 1 | 1 | 1 | 1 |
| j-c03-basket-mix | `sql+python` | `claude-opus-5-5` | 1 | 1 | 1 | 1 |
| j-c04-ltv-by-first-store | `motley` | `claude-opus-5-5` | 1 | 1 | 1 | 1 |
| j-c04-ltv-by-first-store | `motley+python` | `claude-opus-5-5` | 1 | 1 | 0 | 0 |
| j-c04-ltv-by-first-store | `slayer` | `claude-opus-5-5` | 1 | 1 | 1 | 1 |
| j-c04-ltv-by-first-store | `slayer+python` | `claude-opus-5-5` | 1 | 1 | 1 | 1 |
| j-c04-ltv-by-first-store | `sql+python` | `claude-opus-5-5` | 1 | 1 | 1 | 1 |
| j-c05-median-orders-per-customer | `motley` | `claude-opus-5-5` | 1 | 1 | 1 | 1 |
| j-c05-median-orders-per-customer | `motley+python` | `claude-opus-5-5` | 1 | 1 | 1 | 1 |
| j-c05-median-orders-per-customer | `slayer` | `claude-opus-5-5` | 1 | 1 | 1 | 1 |
| j-c05-median-orders-per-customer | `slayer+python` | `claude-opus-5-5` | 1 | 1 | 1 | 1 |
| j-c05-median-orders-per-customer | `sql+python` | `claude-opus-5-5` | 1 | 1 | 1 | 1 |
| j-c06-top-decile-share | `motley` | `claude-opus-5-5` | 1 | 1 | 0 | 0 |
| j-c06-top-decile-share | `motley+python` | `claude-opus-5-5` | 1 | 1 | 0 | 0 |
| j-c06-top-decile-share | `slayer` | `claude-opus-5-5` | 1 | 1 | 1 | 1 |
| j-c06-top-decile-share | `slayer+python` | `claude-opus-5-5` | 1 | 1 | 0 | 0 |
| j-c06-top-decile-share | `sql+python` | `claude-opus-5-5` | 1 | 1 | 1 | 1 |
| j-c07-best-month-vs-avg | `motley` | `claude-opus-5-5` | 1 | 1 | 1 | 1 |
| j-c07-best-month-vs-avg | `motley+python` | `claude-opus-5-5` | 1 | 1 | 0 | 0 |
| j-c07-best-month-vs-avg | `slayer` | `claude-opus-5-5` | 1 | 1 | 1 | 1 |
| j-c07-best-month-vs-avg | `slayer+python` | `claude-opus-5-5` | 1 | 1 | 1 | 1 |
| j-c07-best-month-vs-avg | `sql+python` | `claude-opus-5-5` | 1 | 1 | 1 | 1 |
| j-c08-growth-streak | `motley` | `claude-opus-5-5` | 1 | 1 | 0 | 0 |
| j-c08-growth-streak | `motley+python` | `claude-opus-5-5` | 1 | 1 | 0 | 0 |
| j-c08-growth-streak | `slayer` | `claude-opus-5-5` | 1 | 1 | 0 | 0 |
| j-c08-growth-streak | `slayer+python` | `claude-opus-5-5` | 1 | 1 | 0 | 0 |
| j-c08-growth-streak | `sql+python` | `claude-opus-5-5` | 1 | 1 | 0 | 0 |
| j-c09-brooklyn-cogs-margin | `motley` | `claude-opus-5-5` | 1 | 1 | 0 | 0 |
| j-c09-brooklyn-cogs-margin | `motley+python` | `claude-opus-5-5` | 1 | 1 | 0 | 0 |
| j-c09-brooklyn-cogs-margin | `slayer` | `claude-opus-5-5` | 1 | 1 | 1 | 1 |
| j-c09-brooklyn-cogs-margin | `slayer+python` | `claude-opus-5-5` | 1 | 1 | 1 | 1 |
| j-c09-brooklyn-cogs-margin | `sql+python` | `claude-opus-5-5` | 1 | 1 | 1 | 1 |
| j-c10-top-supply-component | `motley` | `claude-opus-5-5` | 1 | 1 | 0 | 0 |
| j-c10-top-supply-component | `motley+python` | `claude-opus-5-5` | 1 | 1 | 0 | 0 |
| j-c10-top-supply-component | `slayer` | `claude-opus-5-5` | 1 | 1 | 0 | 0 |
| j-c10-top-supply-component | `slayer+python` | `claude-opus-5-5` | 1 | 1 | 0 | 0 |
| j-c10-top-supply-component | `sql+python` | `claude-opus-5-5` | 1 | 1 | 0 | 0 |
| j-c11-tweeters-aov | `motley` | `claude-opus-5-5` | 1 | 1 | 1 | 1 |
| j-c11-tweeters-aov | `motley+python` | `claude-opus-5-5` | 1 | 1 | 1 | 1 |
| j-c11-tweeters-aov | `slayer` | `claude-opus-5-5` | 1 | 1 | 1 | 1 |
| j-c11-tweeters-aov | `slayer+python` | `claude-opus-5-5` | 1 | 1 | 1 | 1 |
| j-c11-tweeters-aov | `sql+python` | `claude-opus-5-5` | 1 | 1 | 1 | 1 |
| j-c12-jaffle-beverage-attach | `motley` | `claude-opus-5-5` | 1 | 1 | 1 | 1 |
| j-c12-jaffle-beverage-attach | `motley+python` | `claude-opus-5-5` | 1 | 1 | 1 | 1 |
| j-c12-jaffle-beverage-attach | `slayer` | `claude-opus-5-5` | 1 | 1 | 1 | 1 |
| j-c12-jaffle-beverage-attach | `slayer+python` | `claude-opus-5-5` | 1 | 1 | 1 | 1 |
| j-c12-jaffle-beverage-attach | `sql+python` | `claude-opus-5-5` | 1 | 0 | 0 | 0 |
| j-q01-stores | `motley` | `claude-opus-5-5` | 1 | 1 | 1 | 1 |
| j-q01-stores | `motley+python` | `claude-opus-5-5` | 1 | 1 | 1 | 1 |
| j-q01-stores | `slayer` | `claude-opus-5-5` | 1 | 1 | 1 | 1 |
| j-q01-stores | `slayer+python` | `claude-opus-5-5` | 1 | 1 | 1 | 1 |
| j-q01-stores | `sql+python` | `claude-opus-5-5` | 1 | 1 | 1 | 1 |
| j-q02-orders-2025 | `motley` | `claude-opus-5-5` | 1 | 1 | 1 | 1 |
| j-q02-orders-2025 | `motley+python` | `claude-opus-5-5` | 1 | 1 | 1 | 1 |
| j-q02-orders-2025 | `slayer` | `claude-opus-5-5` | 1 | 1 | 1 | 1 |
| j-q02-orders-2025 | `slayer+python` | `claude-opus-5-5` | 1 | 1 | 1 | 1 |
| j-q02-orders-2025 | `sql+python` | `claude-opus-5-5` | 1 | 1 | 1 | 1 |
| j-q03-revenue-by-store-2025 | `motley` | `claude-opus-5-5` | 1 | 1 | 1 | 1 |
| j-q03-revenue-by-store-2025 | `motley+python` | `claude-opus-5-5` | 1 | 1 | 1 | 1 |
| j-q03-revenue-by-store-2025 | `slayer` | `claude-opus-5-5` | 1 | 1 | 1 | 1 |
| j-q03-revenue-by-store-2025 | `slayer+python` | `claude-opus-5-5` | 1 | 1 | 1 | 1 |
| j-q03-revenue-by-store-2025 | `sql+python` | `claude-opus-5-5` | 1 | 1 | 1 | 1 |
| j-q04-monthly-orders-2026 | `motley` | `claude-opus-5-5` | 1 | 1 | 1 | 1 |
| j-q04-monthly-orders-2026 | `motley+python` | `claude-opus-5-5` | 1 | 1 | 1 | 1 |
| j-q04-monthly-orders-2026 | `slayer` | `claude-opus-5-5` | 1 | 1 | 1 | 1 |
| j-q04-monthly-orders-2026 | `slayer+python` | `claude-opus-5-5` | 1 | 1 | 1 | 1 |
| j-q04-monthly-orders-2026 | `sql+python` | `claude-opus-5-5` | 1 | 1 | 1 | 1 |
| j-q05-top-products-2025 | `motley` | `claude-opus-5-5` | 1 | 1 | 0 | 0 |
| j-q05-top-products-2025 | `motley+python` | `claude-opus-5-5` | 1 | 1 | 0 | 0 |
| j-q05-top-products-2025 | `slayer` | `claude-opus-5-5` | 1 | 1 | 0 | 0 |
| j-q05-top-products-2025 | `slayer+python` | `claude-opus-5-5` | 1 | 1 | 0 | 0 |
| j-q05-top-products-2025 | `sql+python` | `claude-opus-5-5` | 1 | 1 | 0 | 0 |
| j-q06-type-share-2025 | `motley` | `claude-opus-5-5` | 1 | 1 | 1 | 1 |
| j-q06-type-share-2025 | `motley+python` | `claude-opus-5-5` | 1 | 1 | 1 | 1 |
| j-q06-type-share-2025 | `slayer` | `claude-opus-5-5` | 1 | 1 | 1 | 1 |
| j-q06-type-share-2025 | `slayer+python` | `claude-opus-5-5` | 1 | 1 | 1 | 1 |
| j-q06-type-share-2025 | `sql+python` | `claude-opus-5-5` | 1 | 1 | 1 | 1 |
| j-q07-aov-by-store | `motley` | `claude-opus-5-5` | 1 | 1 | 1 | 1 |
| j-q07-aov-by-store | `motley+python` | `claude-opus-5-5` | 1 | 1 | 1 | 1 |
| j-q07-aov-by-store | `slayer` | `claude-opus-5-5` | 1 | 1 | 1 | 1 |
| j-q07-aov-by-store | `slayer+python` | `claude-opus-5-5` | 1 | 1 | 1 | 1 |
| j-q07-aov-by-store | `sql+python` | `claude-opus-5-5` | 1 | 1 | 1 | 1 |
| j-q08-tax-rate-check | `motley` | `claude-opus-5-5` | 1 | 1 | 1 | 1 |
| j-q08-tax-rate-check | `motley+python` | `claude-opus-5-5` | 1 | 1 | 1 | 1 |
| j-q08-tax-rate-check | `slayer` | `claude-opus-5-5` | 1 | 1 | 1 | 1 |
| j-q08-tax-rate-check | `slayer+python` | `claude-opus-5-5` | 1 | 1 | 1 | 1 |
| j-q08-tax-rate-check | `sql+python` | `claude-opus-5-5` | 1 | 1 | 1 | 1 |
| j-q09-store-growth-2024-2025 | `motley` | `claude-opus-5-5` | 1 | 1 | 0 | 0 |
| j-q09-store-growth-2024-2025 | `motley+python` | `claude-opus-5-5` | 1 | 1 | 0 | 0 |
| j-q09-store-growth-2024-2025 | `slayer` | `claude-opus-5-5` | 1 | 1 | 1 | 1 |
| j-q09-store-growth-2024-2025 | `slayer+python` | `claude-opus-5-5` | 1 | 1 | 1 | 1 |
| j-q09-store-growth-2024-2025 | `sql+python` | `claude-opus-5-5` | 1 | 1 | 0 | 0 |
| j-q10-new-customers-by-year | `motley` | `claude-opus-5-5` | 1 | 1 | 0 | 0 |
| j-q10-new-customers-by-year | `motley+python` | `claude-opus-5-5` | 1 | 1 | 0 | 0 |
| j-q10-new-customers-by-year | `slayer` | `claude-opus-5-5` | 1 | 1 | 0 | 0 |
| j-q10-new-customers-by-year | `slayer+python` | `claude-opus-5-5` | 1 | 1 | 0 | 0 |
| j-q10-new-customers-by-year | `sql+python` | `claude-opus-5-5` | 1 | 1 | 1 | 1 |
| j-q11-ytd-growth-same-store | `motley` | `claude-opus-5-5` | 1 | 1 | 0 | 0 |
| j-q11-ytd-growth-same-store | `motley+python` | `claude-opus-5-5` | 1 | 1 | 0 | 0 |
| j-q11-ytd-growth-same-store | `slayer` | `claude-opus-5-5` | 1 | 1 | 1 | 1 |
| j-q11-ytd-growth-same-store | `slayer+python` | `claude-opus-5-5` | 1 | 0 | 0 | 0 |
| j-q11-ytd-growth-same-store | `sql+python` | `claude-opus-5-5` | 1 | 1 | 0 | 0 |
| j-q12-best-unit-margin | `motley` | `claude-opus-5-5` | 1 | 0 | 0 | 0 |
| j-q12-best-unit-margin | `motley+python` | `claude-opus-5-5` | 1 | 0 | 0 | 0 |
| j-q12-best-unit-margin | `slayer` | `claude-opus-5-5` | 1 | 0 | 1 | 0 |
| j-q12-best-unit-margin | `slayer+python` | `claude-opus-5-5` | 1 | 0 | 1 | 0 |
| j-q12-best-unit-margin | `sql+python` | `claude-opus-5-5` | 1 | 1 | 1 | 1 |

## `slayer` · `claude-opus-5-5`

A task counts under every row it covers, so a multi-row task adds to several rows.

| Row | Feature | Tasks | Trials | Correct | Single query | Passed | Python | Raw SQL | Model edits | Query errors | Several queries |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Q1 | Coarser grain in the same query | 4 | 4 | 4 | 4 | 4 | 0 | 0 | 0 | 0 | 1 |
| Q2 | Arithmetic across grains | 9 | 9 | 9 | 9 | 9 | 0 | 0 | 0 | 0 | 1 |
| Q3 | Re-aggregation | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| Q4 | Transforms / time shift | 11 | 11 | 11 | 11 | 11 | 0 | 0 | 0 | 0 | 1 |
| Q5 | Calculated dimensions, filters, order | 2 | 2 | 2 | 2 | 2 | 0 | 0 | 0 | 0 | 2 |
| Q6 | Fields from many models, fan-out safe | 7 | 7 | 7 | 6 | 6 | 0 | 0 | 0 | 0 | 2 |
| Q7 | Deep composition | 1 | 1 | 1 | 1 | 1 | 0 | 0 | 0 | 0 | 0 |
| Q8 | Population inference | 4 | 4 | 4 | 4 | 4 | 0 | 0 | 0 | 0 | 0 |
| Q9 | No silently wrong numbers | 1 | 1 | 1 | 1 | 1 | 0 | 0 | 0 | 0 | 0 |
| Q10 | Filters across one-to-many joins | 4 | 4 | 4 | 4 | 4 | 0 | 1 | 0 | 0 | 0 |
| Q11 | Rolling time windows | 2 | 2 | 2 | 2 | 2 | 0 | 0 | 0 | 0 | 0 |
| Q12 | Aggregates as arguments | 2 | 2 | 2 | 2 | 2 | 0 | 0 | 0 | 0 | 1 |
| Q13 | Order by what you don't show | 2 | 2 | 2 | 1 | 1 | 0 | 0 | 0 | 0 | 1 |
| Q14 | Ranking and streaks | 4 | 4 | 4 | 3 | 3 | 0 | 0 | 0 | 1 | 1 |
| Q15 | Multi-stage queries | 3 | 3 | 3 | 3 | 3 | 0 | 0 | 0 | 1 | 2 |
| Q16 | Inline model extension | 2 | 2 | 2 | 2 | 2 | 0 | 0 | 0 | 0 | 0 |
| Q17 | Saved measures that compose | 2 | 2 | 2 | 2 | 2 | 0 | 0 | 0 | 0 | 0 |
| Q18 | Time-bucket safety | 1 | 1 | 1 | 1 | 1 | 0 | 0 | 0 | 1 | 0 |
| Q19 | Agent & API surface | not covered |  |  |  |  |  |  |  |  |  |
| Q20 | Relative & typed filters | 3 | 3 | 3 | 3 | 3 | 0 | 0 | 0 | 0 | 1 |
| Q21 | Calendar expressions | 2 | 2 | 2 | 2 | 2 | 0 | 0 | 0 | 0 | 0 |
| Q22 | Nested source data | not covered |  |  |  |  |  |  |  |  |  |
| Q23 | Saved queries & refinement | 2 | 2 | 2 | 2 | 2 | 0 | 0 | 0 | 0 | 0 |
| Q24 | Nested / hierarchical results | 2 | 2 | 2 | 2 | 2 | 0 | 0 | 0 | 0 | 0 |
| Q25 | Explicit aggregate locality | 1 | 1 | 1 | 1 | 1 | 0 | 0 | 0 | 0 | 0 |
| Q26 | Metrics without a join path | 1 | 1 | 1 | 1 | 1 | 0 | 0 | 0 | 0 | 1 |
| Q27 | List columns | 15 | 15 | 15 | 15 | 15 | 0 | 0 | 0 | 1 | 2 |

| Task | Suite | Covers | Pass rate | pass^1 |
| --- | --- | --- | --- | --- |
| c-aov-change | combo | Q17, Q4 | 1/1 | 1.000 |
| c-net-region-tier | combo | Q6, Q12, Q1 | 1/1 | 1.000 |
| c-region-credit-rank | combo | Q6, Q14 | 0/1 | 0.000 |
| c-region-month-share | combo | Q2, Q4 | 1/1 | 1.000 |
| c-saved-running | combo | Q23, Q4 | 1/1 | 1.000 |
| c-size-class-months | combo | Q16, Q2, Q4 | 1/1 | 1.000 |
| c-spend-band-share | combo | Q5, Q2 | 1/1 | 1.000 |
| c-tier-credit-tags | combo | Q27, Q6 | 1/1 | 1.000 |
| c-top-customer-share | combo | Q14, Q2 | 1/1 | 1.000 |
| c-top-customers-per-tag | combo | Q27, Q14, Q15 | 1/1 | 1.000 |
| c-top-growth-months | combo | Q13, Q4 | 1/1 | 1.000 |
| c-top-two-q1-share | combo | Q24, Q2, Q20 | 1/1 | 1.000 |
| c-vip-monthly-change | combo | Q27, Q4 | 1/1 | 1.000 |
| c-vip-region-share | combo | Q27, Q2 | 1/1 | 1.000 |
| c-weekday-share | combo | Q21, Q2 | 1/1 | 1.000 |
| j-c01-peak-weekday-hour | jaffle | — | 0/1 | 0.000 |
| j-c02-order-value-bands | jaffle | — | 1/1 | 1.000 |
| j-c03-basket-mix | jaffle | — | 1/1 | 1.000 |
| j-c04-ltv-by-first-store | jaffle | — | 1/1 | 1.000 |
| j-c05-median-orders-per-customer | jaffle | — | 1/1 | 1.000 |
| j-c06-top-decile-share | jaffle | — | 1/1 | 1.000 |
| j-c07-best-month-vs-avg | jaffle | — | 1/1 | 1.000 |
| j-c08-growth-streak | jaffle | — | 0/1 | 0.000 |
| j-c09-brooklyn-cogs-margin | jaffle | — | 1/1 | 1.000 |
| j-c10-top-supply-component | jaffle | — | 0/1 | 0.000 |
| j-c11-tweeters-aov | jaffle | — | 1/1 | 1.000 |
| j-c12-jaffle-beverage-attach | jaffle | — | 1/1 | 1.000 |
| j-q01-stores | jaffle | — | 1/1 | 1.000 |
| j-q02-orders-2025 | jaffle | — | 1/1 | 1.000 |
| j-q03-revenue-by-store-2025 | jaffle | — | 1/1 | 1.000 |
| j-q04-monthly-orders-2026 | jaffle | — | 1/1 | 1.000 |
| j-q05-top-products-2025 | jaffle | — | 0/1 | 0.000 |
| j-q06-type-share-2025 | jaffle | — | 1/1 | 1.000 |
| j-q07-aov-by-store | jaffle | — | 1/1 | 1.000 |
| j-q08-tax-rate-check | jaffle | — | 1/1 | 1.000 |
| j-q09-store-growth-2024-2025 | jaffle | — | 1/1 | 1.000 |
| j-q10-new-customers-by-year | jaffle | — | 0/1 | 0.000 |
| j-q11-ytd-growth-same-store | jaffle | — | 1/1 | 1.000 |
| j-q12-best-unit-margin | jaffle | — | 0/1 | 0.000 |
| q1-region-total | capability | Q1 | 1/1 | 1.000 |
| q10-bronze-or-ok | capability | Q10 | 1/1 | 1.000 |
| q11-rolling-customers | capability | Q11 | 1/1 | 1.000 |
| q12-net-revenue | capability | Q12 | 1/1 | 1.000 |
| q13-top-cities-count | capability | Q13 | 0/1 | 0.000 |
| q14-top-customer-per-region | capability | Q14 | 1/1 | 1.000 |
| q15-revenue-bands | capability | Q15 | 1/1 | 1.000 |
| q16-order-size | capability | Q16 | 1/1 | 1.000 |
| q17-running-aov | capability | Q17 | 1/1 | 1.000 |
| q18-day-of-monthly | capability | Q18 | 1/1 | 1.000 |
| q2-city-share | capability | Q2 | 1/1 | 1.000 |
| q20-quarter-region | capability | Q20 | 1/1 | 1.000 |
| q21-weekday-revenue | capability | Q21 | 1/1 | 1.000 |
| q23-monthly-by-region | capability | Q23 | 1/1 | 1.000 |
| q24-top-two-per-region | capability | Q24 | 1/1 | 1.000 |
| q25-credit-per-order | capability | Q25 | 1/1 | 1.000 |
| q26-events-per-customer | capability | Q26 | 1/1 | 1.000 |
| q27-category-ratings | capability | Q27 | 1/1 | 1.000 |
| q27-customers-per-tag | capability | Q27 | 1/1 | 1.000 |
| q27-region-distinct-tags | capability | Q27 | 1/1 | 1.000 |
| q27-region-tag-set | capability | Q27 | 1/1 | 1.000 |
| q27-vip-and-eu | capability | Q27 | 1/1 | 1.000 |
| q27-vip-customers | capability | Q27 | 1/1 | 1.000 |
| q27-vip-or-partner | capability | Q27 | 1/1 | 1.000 |
| q3-avg-city-revenue | capability | Q3 | 0/1 | 0.000 |
| q4-prior-year | capability | Q4 | 1/1 | 1.000 |
| q4-running-total | capability | Q4 | 1/1 | 1.000 |
| q5-spend-band | capability | Q5 | 1/1 | 1.000 |
| q6-region-credit | capability | Q6 | 1/1 | 1.000 |
| q7-cumulative-change | capability | Q7 | 1/1 | 1.000 |
| q8-tier-customers | capability | Q8 | 1/1 | 1.000 |
| q9-credit-by-status | capability | Q9 | 1/1 | 1.000 |
| t-all-time-running | trap | Q4, Q15, filter_before_window | 1/1 | 1.000 |
| t-bridge-email | trap | Q10, bridge | 1/1 | 1.000 |
| t-chasm | trap | Q6, chasm | 1/1 | 1.000 |
| t-city-size | trap | Q6, non_unique_key | 1/1 | 1.000 |
| t-count-after-join | trap | Q10, count_after_join | 1/1 | 1.000 |
| t-fan-out-credit | trap | Q8, fan_out | 1/1 | 1.000 |
| t-fan-out-items | trap | Q6, fan_out | 1/1 | 1.000 |
| t-march-events | trap | Q20, timestamp_bounds | 1/1 | 1.000 |
| t-monthly-gaps | trap | Q4, missing_periods | 1/1 | 1.000 |
| t-never-returned | trap | Q10, not_in_null | 1/1 | 1.000 |
| t-ok-share | trap | Q2, filtered_total | 1/1 | 1.000 |
| t-orders-per-category | trap | Q1, distinct_reagg | 1/1 | 1.000 |
| t-orders-per-customer | trap | Q8, count_outer_join | 1/1 | 1.000 |
| t-overall-aov | trap | Q1, avg_of_avgs | 1/1 | 1.000 |
| t-prev-month | trap | Q4, filter_before_window | 1/1 | 1.000 |
| t-rolling-gap | trap | Q11, rows_window_gap | 1/1 | 1.000 |
| t-tagged-credit | trap | Q27, unnest_fan_out | 1/1 | 1.000 |
| t-vip-and-eu-region | trap | Q27, same_element_and | 1/1 | 1.000 |
| t-vip-per-tier | trap | Q27, count_after_unnest | 1/1 | 1.000 |
| t-without-vip | trap | Q27, null_element | 1/1 | 1.000 |
| t-zero-regions | trap | Q8, outer_join_filter | 1/1 | 1.000 |

## `slayer+python` · `claude-opus-5-5`

A task counts under every row it covers, so a multi-row task adds to several rows.

| Row | Feature | Tasks | Trials | Correct | Single query | Passed | Python | Raw SQL | Model edits | Query errors | Several queries |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Q1 | Coarser grain in the same query | 4 | 4 | 4 | 4 | 4 | 0 | 0 | 0 | 0 | 2 |
| Q2 | Arithmetic across grains | 9 | 9 | 9 | 9 | 9 | 0 | 1 | 0 | 0 | 1 |
| Q3 | Re-aggregation | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| Q4 | Transforms / time shift | 11 | 11 | 11 | 10 | 10 | 0 | 1 | 0 | 1 | 1 |
| Q5 | Calculated dimensions, filters, order | 2 | 2 | 2 | 2 | 2 | 0 | 0 | 0 | 0 | 2 |
| Q6 | Fields from many models, fan-out safe | 7 | 7 | 7 | 6 | 6 | 0 | 0 | 0 | 0 | 2 |
| Q7 | Deep composition | 1 | 1 | 1 | 1 | 1 | 0 | 0 | 0 | 0 | 0 |
| Q8 | Population inference | 4 | 4 | 4 | 4 | 4 | 0 | 0 | 0 | 0 | 0 |
| Q9 | No silently wrong numbers | 1 | 1 | 1 | 1 | 1 | 0 | 0 | 0 | 0 | 0 |
| Q10 | Filters across one-to-many joins | 4 | 4 | 4 | 4 | 4 | 0 | 0 | 0 | 0 | 2 |
| Q11 | Rolling time windows | 2 | 2 | 2 | 2 | 2 | 0 | 0 | 0 | 0 | 0 |
| Q12 | Aggregates as arguments | 2 | 2 | 2 | 2 | 2 | 0 | 0 | 0 | 0 | 1 |
| Q13 | Order by what you don't show | 2 | 2 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| Q14 | Ranking and streaks | 4 | 4 | 4 | 3 | 3 | 0 | 0 | 0 | 1 | 1 |
| Q15 | Multi-stage queries | 3 | 3 | 3 | 3 | 3 | 0 | 0 | 0 | 1 | 1 |
| Q16 | Inline model extension | 2 | 2 | 2 | 2 | 2 | 0 | 1 | 0 | 0 | 0 |
| Q17 | Saved measures that compose | 2 | 2 | 2 | 2 | 2 | 0 | 0 | 0 | 0 | 0 |
| Q18 | Time-bucket safety | 1 | 1 | 1 | 1 | 1 | 0 | 0 | 0 | 1 | 0 |
| Q19 | Agent & API surface | not covered |  |  |  |  |  |  |  |  |  |
| Q20 | Relative & typed filters | 3 | 3 | 3 | 3 | 3 | 0 | 0 | 0 | 0 | 1 |
| Q21 | Calendar expressions | 2 | 2 | 2 | 2 | 2 | 0 | 0 | 0 | 0 | 0 |
| Q22 | Nested source data | not covered |  |  |  |  |  |  |  |  |  |
| Q23 | Saved queries & refinement | 2 | 2 | 2 | 2 | 2 | 0 | 0 | 0 | 1 | 2 |
| Q24 | Nested / hierarchical results | 2 | 2 | 2 | 2 | 2 | 0 | 0 | 0 | 0 | 0 |
| Q25 | Explicit aggregate locality | 1 | 1 | 1 | 1 | 1 | 0 | 0 | 0 | 0 | 0 |
| Q26 | Metrics without a join path | 1 | 1 | 1 | 1 | 1 | 0 | 0 | 0 | 0 | 0 |
| Q27 | List columns | 15 | 15 | 15 | 15 | 15 | 0 | 0 | 0 | 1 | 3 |

| Task | Suite | Covers | Pass rate | pass^1 |
| --- | --- | --- | --- | --- |
| c-aov-change | combo | Q17, Q4 | 1/1 | 1.000 |
| c-net-region-tier | combo | Q6, Q12, Q1 | 1/1 | 1.000 |
| c-region-credit-rank | combo | Q6, Q14 | 0/1 | 0.000 |
| c-region-month-share | combo | Q2, Q4 | 1/1 | 1.000 |
| c-saved-running | combo | Q23, Q4 | 1/1 | 1.000 |
| c-size-class-months | combo | Q16, Q2, Q4 | 1/1 | 1.000 |
| c-spend-band-share | combo | Q5, Q2 | 1/1 | 1.000 |
| c-tier-credit-tags | combo | Q27, Q6 | 1/1 | 1.000 |
| c-top-customer-share | combo | Q14, Q2 | 1/1 | 1.000 |
| c-top-customers-per-tag | combo | Q27, Q14, Q15 | 1/1 | 1.000 |
| c-top-growth-months | combo | Q13, Q4 | 0/1 | 0.000 |
| c-top-two-q1-share | combo | Q24, Q2, Q20 | 1/1 | 1.000 |
| c-vip-monthly-change | combo | Q27, Q4 | 1/1 | 1.000 |
| c-vip-region-share | combo | Q27, Q2 | 1/1 | 1.000 |
| c-weekday-share | combo | Q21, Q2 | 1/1 | 1.000 |
| j-c01-peak-weekday-hour | jaffle | — | 0/1 | 0.000 |
| j-c02-order-value-bands | jaffle | — | 1/1 | 1.000 |
| j-c03-basket-mix | jaffle | — | 1/1 | 1.000 |
| j-c04-ltv-by-first-store | jaffle | — | 1/1 | 1.000 |
| j-c05-median-orders-per-customer | jaffle | — | 1/1 | 1.000 |
| j-c06-top-decile-share | jaffle | — | 0/1 | 0.000 |
| j-c07-best-month-vs-avg | jaffle | — | 1/1 | 1.000 |
| j-c08-growth-streak | jaffle | — | 0/1 | 0.000 |
| j-c09-brooklyn-cogs-margin | jaffle | — | 1/1 | 1.000 |
| j-c10-top-supply-component | jaffle | — | 0/1 | 0.000 |
| j-c11-tweeters-aov | jaffle | — | 1/1 | 1.000 |
| j-c12-jaffle-beverage-attach | jaffle | — | 1/1 | 1.000 |
| j-q01-stores | jaffle | — | 1/1 | 1.000 |
| j-q02-orders-2025 | jaffle | — | 1/1 | 1.000 |
| j-q03-revenue-by-store-2025 | jaffle | — | 1/1 | 1.000 |
| j-q04-monthly-orders-2026 | jaffle | — | 1/1 | 1.000 |
| j-q05-top-products-2025 | jaffle | — | 0/1 | 0.000 |
| j-q06-type-share-2025 | jaffle | — | 1/1 | 1.000 |
| j-q07-aov-by-store | jaffle | — | 1/1 | 1.000 |
| j-q08-tax-rate-check | jaffle | — | 1/1 | 1.000 |
| j-q09-store-growth-2024-2025 | jaffle | — | 1/1 | 1.000 |
| j-q10-new-customers-by-year | jaffle | — | 0/1 | 0.000 |
| j-q11-ytd-growth-same-store | jaffle | — | 0/1 | 0.000 |
| j-q12-best-unit-margin | jaffle | — | 0/1 | 0.000 |
| q1-region-total | capability | Q1 | 1/1 | 1.000 |
| q10-bronze-or-ok | capability | Q10 | 1/1 | 1.000 |
| q11-rolling-customers | capability | Q11 | 1/1 | 1.000 |
| q12-net-revenue | capability | Q12 | 1/1 | 1.000 |
| q13-top-cities-count | capability | Q13 | 0/1 | 0.000 |
| q14-top-customer-per-region | capability | Q14 | 1/1 | 1.000 |
| q15-revenue-bands | capability | Q15 | 1/1 | 1.000 |
| q16-order-size | capability | Q16 | 1/1 | 1.000 |
| q17-running-aov | capability | Q17 | 1/1 | 1.000 |
| q18-day-of-monthly | capability | Q18 | 1/1 | 1.000 |
| q2-city-share | capability | Q2 | 1/1 | 1.000 |
| q20-quarter-region | capability | Q20 | 1/1 | 1.000 |
| q21-weekday-revenue | capability | Q21 | 1/1 | 1.000 |
| q23-monthly-by-region | capability | Q23 | 1/1 | 1.000 |
| q24-top-two-per-region | capability | Q24 | 1/1 | 1.000 |
| q25-credit-per-order | capability | Q25 | 1/1 | 1.000 |
| q26-events-per-customer | capability | Q26 | 1/1 | 1.000 |
| q27-category-ratings | capability | Q27 | 1/1 | 1.000 |
| q27-customers-per-tag | capability | Q27 | 1/1 | 1.000 |
| q27-region-distinct-tags | capability | Q27 | 1/1 | 1.000 |
| q27-region-tag-set | capability | Q27 | 1/1 | 1.000 |
| q27-vip-and-eu | capability | Q27 | 1/1 | 1.000 |
| q27-vip-customers | capability | Q27 | 1/1 | 1.000 |
| q27-vip-or-partner | capability | Q27 | 1/1 | 1.000 |
| q3-avg-city-revenue | capability | Q3 | 0/1 | 0.000 |
| q4-prior-year | capability | Q4 | 1/1 | 1.000 |
| q4-running-total | capability | Q4 | 1/1 | 1.000 |
| q5-spend-band | capability | Q5 | 1/1 | 1.000 |
| q6-region-credit | capability | Q6 | 1/1 | 1.000 |
| q7-cumulative-change | capability | Q7 | 1/1 | 1.000 |
| q8-tier-customers | capability | Q8 | 1/1 | 1.000 |
| q9-credit-by-status | capability | Q9 | 1/1 | 1.000 |
| t-all-time-running | trap | Q4, Q15, filter_before_window | 1/1 | 1.000 |
| t-bridge-email | trap | Q10, bridge | 1/1 | 1.000 |
| t-chasm | trap | Q6, chasm | 1/1 | 1.000 |
| t-city-size | trap | Q6, non_unique_key | 1/1 | 1.000 |
| t-count-after-join | trap | Q10, count_after_join | 1/1 | 1.000 |
| t-fan-out-credit | trap | Q8, fan_out | 1/1 | 1.000 |
| t-fan-out-items | trap | Q6, fan_out | 1/1 | 1.000 |
| t-march-events | trap | Q20, timestamp_bounds | 1/1 | 1.000 |
| t-monthly-gaps | trap | Q4, missing_periods | 1/1 | 1.000 |
| t-never-returned | trap | Q10, not_in_null | 1/1 | 1.000 |
| t-ok-share | trap | Q2, filtered_total | 1/1 | 1.000 |
| t-orders-per-category | trap | Q1, distinct_reagg | 1/1 | 1.000 |
| t-orders-per-customer | trap | Q8, count_outer_join | 1/1 | 1.000 |
| t-overall-aov | trap | Q1, avg_of_avgs | 1/1 | 1.000 |
| t-prev-month | trap | Q4, filter_before_window | 1/1 | 1.000 |
| t-rolling-gap | trap | Q11, rows_window_gap | 1/1 | 1.000 |
| t-tagged-credit | trap | Q27, unnest_fan_out | 1/1 | 1.000 |
| t-vip-and-eu-region | trap | Q27, same_element_and | 1/1 | 1.000 |
| t-vip-per-tier | trap | Q27, count_after_unnest | 1/1 | 1.000 |
| t-without-vip | trap | Q27, null_element | 1/1 | 1.000 |
| t-zero-regions | trap | Q8, outer_join_filter | 1/1 | 1.000 |

## `sql+python` · `claude-opus-5-5`

A task counts under every row it covers, so a multi-row task adds to several rows.

| Row | Feature | Tasks | Trials | Correct | Single query | Passed | Python | Raw SQL | Model edits | Query errors | Several queries |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Q1 | Coarser grain in the same query | 4 | 4 | 4 | 4 | 4 | 0 | 4 | 0 | 1 | 4 |
| Q2 | Arithmetic across grains | 9 | 9 | 9 | 6 | 6 | 0 | 9 | 0 | 7 | 9 |
| Q3 | Re-aggregation | 1 | 1 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 1 |
| Q4 | Transforms / time shift | 11 | 11 | 10 | 6 | 6 | 0 | 10 | 0 | 5 | 10 |
| Q5 | Calculated dimensions, filters, order | 2 | 2 | 2 | 2 | 2 | 0 | 2 | 0 | 1 | 2 |
| Q6 | Fields from many models, fan-out safe | 7 | 7 | 7 | 6 | 6 | 0 | 7 | 0 | 0 | 7 |
| Q7 | Deep composition | 1 | 1 | 1 | 1 | 1 | 0 | 1 | 0 | 1 | 1 |
| Q8 | Population inference | 4 | 4 | 4 | 4 | 4 | 0 | 4 | 0 | 0 | 4 |
| Q9 | No silently wrong numbers | 1 | 1 | 1 | 1 | 1 | 0 | 1 | 0 | 0 | 1 |
| Q10 | Filters across one-to-many joins | 4 | 4 | 4 | 4 | 4 | 0 | 4 | 0 | 0 | 4 |
| Q11 | Rolling time windows | 2 | 2 | 2 | 2 | 2 | 0 | 2 | 0 | 1 | 2 |
| Q12 | Aggregates as arguments | 2 | 2 | 2 | 2 | 2 | 0 | 2 | 0 | 0 | 2 |
| Q13 | Order by what you don't show | 2 | 2 | 2 | 0 | 0 | 0 | 2 | 0 | 0 | 2 |
| Q14 | Ranking and streaks | 4 | 4 | 3 | 0 | 0 | 0 | 4 | 0 | 1 | 4 |
| Q15 | Multi-stage queries | 3 | 3 | 2 | 2 | 2 | 0 | 3 | 0 | 1 | 3 |
| Q16 | Inline model extension | 2 | 2 | 2 | 2 | 2 | 0 | 2 | 0 | 1 | 2 |
| Q17 | Saved measures that compose | 2 | 2 | 2 | 2 | 2 | 0 | 2 | 0 | 2 | 2 |
| Q18 | Time-bucket safety | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| Q19 | Agent & API surface | not covered |  |  |  |  |  |  |  |  |  |
| Q20 | Relative & typed filters | 3 | 3 | 3 | 2 | 2 | 0 | 3 | 0 | 1 | 3 |
| Q21 | Calendar expressions | 2 | 2 | 2 | 2 | 2 | 0 | 2 | 0 | 1 | 2 |
| Q22 | Nested source data | not covered |  |  |  |  |  |  |  |  |  |
| Q23 | Saved queries & refinement | 2 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| Q24 | Nested / hierarchical results | 2 | 2 | 2 | 0 | 0 | 0 | 2 | 0 | 1 | 2 |
| Q25 | Explicit aggregate locality | 1 | 1 | 1 | 1 | 1 | 0 | 1 | 0 | 0 | 1 |
| Q26 | Metrics without a join path | 1 | 1 | 1 | 1 | 1 | 0 | 1 | 0 | 1 | 1 |
| Q27 | List columns | 16 | 16 | 14 | 12 | 12 | 0 | 16 | 0 | 3 | 16 |

| Task | Suite | Covers | Pass rate | pass^1 |
| --- | --- | --- | --- | --- |
| c-aov-change | combo | Q17, Q4 | 1/1 | 1.000 |
| c-net-region-tier | combo | Q6, Q12, Q1 | 1/1 | 1.000 |
| c-region-credit-rank | combo | Q6, Q14 | 0/1 | 0.000 |
| c-region-month-share | combo | Q2, Q4 | 0/1 | 0.000 |
| c-saved-running | combo | Q23, Q4 | 0/1 | 0.000 |
| c-size-class-months | combo | Q16, Q2, Q4 | 1/1 | 1.000 |
| c-spend-band-share | combo | Q5, Q2 | 1/1 | 1.000 |
| c-tier-credit-tags | combo | Q27, Q6 | 1/1 | 1.000 |
| c-top-customer-share | combo | Q14, Q2 | 0/1 | 0.000 |
| c-top-customers-per-tag | combo | Q27, Q14, Q15 | 0/1 | 0.000 |
| c-top-growth-months | combo | Q13, Q4 | 0/1 | 0.000 |
| c-top-two-q1-share | combo | Q24, Q2, Q20 | 0/1 | 0.000 |
| c-vip-monthly-change | combo | Q27, Q4 | 0/1 | 0.000 |
| c-vip-region-share | combo | Q27, Q2 | 1/1 | 1.000 |
| c-weekday-share | combo | Q21, Q2 | 1/1 | 1.000 |
| j-c01-peak-weekday-hour | jaffle | — | 0/1 | 0.000 |
| j-c02-order-value-bands | jaffle | — | 1/1 | 1.000 |
| j-c03-basket-mix | jaffle | — | 1/1 | 1.000 |
| j-c04-ltv-by-first-store | jaffle | — | 1/1 | 1.000 |
| j-c05-median-orders-per-customer | jaffle | — | 1/1 | 1.000 |
| j-c06-top-decile-share | jaffle | — | 1/1 | 1.000 |
| j-c07-best-month-vs-avg | jaffle | — | 1/1 | 1.000 |
| j-c08-growth-streak | jaffle | — | 0/1 | 0.000 |
| j-c09-brooklyn-cogs-margin | jaffle | — | 1/1 | 1.000 |
| j-c10-top-supply-component | jaffle | — | 0/1 | 0.000 |
| j-c11-tweeters-aov | jaffle | — | 1/1 | 1.000 |
| j-c12-jaffle-beverage-attach | jaffle | — | 0/1 | 0.000 |
| j-q01-stores | jaffle | — | 1/1 | 1.000 |
| j-q02-orders-2025 | jaffle | — | 1/1 | 1.000 |
| j-q03-revenue-by-store-2025 | jaffle | — | 1/1 | 1.000 |
| j-q04-monthly-orders-2026 | jaffle | — | 1/1 | 1.000 |
| j-q05-top-products-2025 | jaffle | — | 0/1 | 0.000 |
| j-q06-type-share-2025 | jaffle | — | 1/1 | 1.000 |
| j-q07-aov-by-store | jaffle | — | 1/1 | 1.000 |
| j-q08-tax-rate-check | jaffle | — | 1/1 | 1.000 |
| j-q09-store-growth-2024-2025 | jaffle | — | 0/1 | 0.000 |
| j-q10-new-customers-by-year | jaffle | — | 1/1 | 1.000 |
| j-q11-ytd-growth-same-store | jaffle | — | 0/1 | 0.000 |
| j-q12-best-unit-margin | jaffle | — | 1/1 | 1.000 |
| q1-region-total | capability | Q1 | 1/1 | 1.000 |
| q10-bronze-or-ok | capability | Q10 | 1/1 | 1.000 |
| q11-rolling-customers | capability | Q11 | 1/1 | 1.000 |
| q12-net-revenue | capability | Q12 | 1/1 | 1.000 |
| q13-top-cities-count | capability | Q13 | 0/1 | 0.000 |
| q14-top-customer-per-region | capability | Q14 | 0/1 | 0.000 |
| q15-revenue-bands | capability | Q15 | 1/1 | 1.000 |
| q16-order-size | capability | Q16 | 1/1 | 1.000 |
| q17-running-aov | capability | Q17 | 1/1 | 1.000 |
| q18-day-of-monthly | capability | Q18 | 0/1 | 0.000 |
| q2-city-share | capability | Q2 | 1/1 | 1.000 |
| q20-quarter-region | capability | Q20 | 1/1 | 1.000 |
| q21-weekday-revenue | capability | Q21 | 1/1 | 1.000 |
| q23-monthly-by-region | capability | Q23 | 0/1 | 0.000 |
| q24-top-two-per-region | capability | Q24 | 0/1 | 0.000 |
| q25-credit-per-order | capability | Q25 | 1/1 | 1.000 |
| q26-events-per-customer | capability | Q26 | 1/1 | 1.000 |
| q27-category-ratings | capability | Q27 | 1/1 | 1.000 |
| q27-customers-per-tag | capability | Q27 | 0/1 | 0.000 |
| q27-region-distinct-tags | capability | Q27 | 1/1 | 1.000 |
| q27-region-tag-set | capability | Q27 | 1/1 | 1.000 |
| q27-tag-count-groups | capability | Q27 | 1/1 | 1.000 |
| q27-vip-and-eu | capability | Q27 | 1/1 | 1.000 |
| q27-vip-customers | capability | Q27 | 1/1 | 1.000 |
| q27-vip-or-partner | capability | Q27 | 1/1 | 1.000 |
| q3-avg-city-revenue | capability | Q3 | 0/1 | 0.000 |
| q4-prior-year | capability | Q4 | 0/1 | 0.000 |
| q4-running-total | capability | Q4 | 1/1 | 1.000 |
| q5-spend-band | capability | Q5 | 1/1 | 1.000 |
| q6-region-credit | capability | Q6 | 1/1 | 1.000 |
| q7-cumulative-change | capability | Q7 | 1/1 | 1.000 |
| q8-tier-customers | capability | Q8 | 1/1 | 1.000 |
| q9-credit-by-status | capability | Q9 | 1/1 | 1.000 |
| t-all-time-running | trap | Q4, Q15, filter_before_window | 1/1 | 1.000 |
| t-bridge-email | trap | Q10, bridge | 1/1 | 1.000 |
| t-chasm | trap | Q6, chasm | 1/1 | 1.000 |
| t-city-size | trap | Q6, non_unique_key | 1/1 | 1.000 |
| t-count-after-join | trap | Q10, count_after_join | 1/1 | 1.000 |
| t-fan-out-credit | trap | Q8, fan_out | 1/1 | 1.000 |
| t-fan-out-items | trap | Q6, fan_out | 1/1 | 1.000 |
| t-march-events | trap | Q20, timestamp_bounds | 1/1 | 1.000 |
| t-monthly-gaps | trap | Q4, missing_periods | 1/1 | 1.000 |
| t-never-returned | trap | Q10, not_in_null | 1/1 | 1.000 |
| t-ok-share | trap | Q2, filtered_total | 1/1 | 1.000 |
| t-orders-per-category | trap | Q1, distinct_reagg | 1/1 | 1.000 |
| t-orders-per-customer | trap | Q8, count_outer_join | 1/1 | 1.000 |
| t-overall-aov | trap | Q1, avg_of_avgs | 1/1 | 1.000 |
| t-prev-month | trap | Q4, filter_before_window | 1/1 | 1.000 |
| t-rolling-gap | trap | Q11, rows_window_gap | 1/1 | 1.000 |
| t-tagged-credit | trap | Q27, unnest_fan_out | 1/1 | 1.000 |
| t-vip-and-eu-region | trap | Q27, same_element_and | 1/1 | 1.000 |
| t-vip-per-tier | trap | Q27, count_after_unnest | 1/1 | 1.000 |
| t-without-vip | trap | Q27, null_element | 0/1 | 0.000 |
| t-zero-regions | trap | Q8, outer_join_filter | 1/1 | 1.000 |

## `motley` · `claude-opus-5-5`

Motley's `query` cannot run a saved query by name with `refine` yet (DEV-2260); saved-query tasks are answered with one inline query.

A task counts under every row it covers, so a multi-row task adds to several rows.

| Row | Feature | Tasks | Trials | Correct | Single query | Passed | Python | Raw SQL | Model edits | Query errors | Several queries |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Q1 | Coarser grain in the same query | 4 | 4 | 4 | 4 | 4 | 0 | 0 | 0 | 0 | 2 |
| Q2 | Arithmetic across grains | 9 | 9 | 9 | 9 | 9 | 0 | 0 | 0 | 1 | 3 |
| Q3 | Re-aggregation | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| Q4 | Transforms / time shift | 11 | 11 | 11 | 10 | 10 | 0 | 0 | 0 | 0 | 2 |
| Q5 | Calculated dimensions, filters, order | 2 | 2 | 2 | 2 | 2 | 0 | 0 | 0 | 0 | 2 |
| Q6 | Fields from many models, fan-out safe | 7 | 7 | 7 | 6 | 6 | 0 | 0 | 0 | 0 | 4 |
| Q7 | Deep composition | 1 | 1 | 1 | 1 | 1 | 0 | 0 | 0 | 0 | 0 |
| Q8 | Population inference | 4 | 4 | 4 | 3 | 3 | 0 | 0 | 0 | 0 | 1 |
| Q9 | No silently wrong numbers | 0 | 0 |  |  |  |  |  |  |  |  |
| Q10 | Filters across one-to-many joins | 4 | 4 | 4 | 4 | 4 | 0 | 0 | 0 | 1 | 3 |
| Q11 | Rolling time windows | 2 | 2 | 2 | 1 | 1 | 0 | 0 | 0 | 0 | 0 |
| Q12 | Aggregates as arguments | 2 | 2 | 2 | 2 | 2 | 0 | 1 | 0 | 0 | 2 |
| Q13 | Order by what you don't show | 2 | 2 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| Q14 | Ranking and streaks | 4 | 4 | 4 | 1 | 1 | 0 | 0 | 0 | 1 | 2 |
| Q15 | Multi-stage queries | 3 | 3 | 3 | 1 | 1 | 0 | 0 | 0 | 1 | 3 |
| Q16 | Inline model extension | 2 | 2 | 2 | 2 | 2 | 0 | 0 | 0 | 0 | 0 |
| Q17 | Saved measures that compose | 2 | 2 | 2 | 2 | 2 | 0 | 0 | 0 | 0 | 0 |
| Q18 | Time-bucket safety | 1 | 1 | 1 | 1 | 1 | 0 | 0 | 0 | 1 | 0 |
| Q19 | Agent & API surface | not covered |  |  |  |  |  |  |  |  |  |
| Q20 | Relative & typed filters | 3 | 3 | 3 | 3 | 3 | 0 | 0 | 0 | 0 | 1 |
| Q21 | Calendar expressions | 2 | 2 | 2 | 2 | 2 | 0 | 1 | 0 | 1 | 1 |
| Q22 | Nested source data | not covered |  |  |  |  |  |  |  |  |  |
| Q23 | Saved queries & refinement | 2 | 2 | 2 | 2 | 2 | 0 | 0 | 0 | 0 | 1 |
| Q24 | Nested / hierarchical results | 2 | 2 | 2 | 2 | 2 | 0 | 0 | 0 | 0 | 0 |
| Q25 | Explicit aggregate locality | 1 | 1 | 1 | 1 | 1 | 0 | 0 | 0 | 0 | 1 |
| Q26 | Metrics without a join path | 1 | 1 | 1 | 1 | 1 | 0 | 0 | 0 | 0 | 0 |
| Q27 | List columns | 15 | 15 | 15 | 14 | 14 | 0 | 0 | 0 | 3 | 10 |

| Task | Suite | Covers | Pass rate | pass^1 |
| --- | --- | --- | --- | --- |
| c-aov-change | combo | Q17, Q4 | 1/1 | 1.000 |
| c-net-region-tier | combo | Q6, Q12, Q1 | 1/1 | 1.000 |
| c-region-credit-rank | combo | Q6, Q14 | 0/1 | 0.000 |
| c-region-month-share | combo | Q2, Q4 | 1/1 | 1.000 |
| c-saved-running | combo | Q23, Q4 | 1/1 | 1.000 |
| c-size-class-months | combo | Q16, Q2, Q4 | 1/1 | 1.000 |
| c-spend-band-share | combo | Q5, Q2 | 1/1 | 1.000 |
| c-tier-credit-tags | combo | Q27, Q6 | 1/1 | 1.000 |
| c-top-customer-share | combo | Q14, Q2 | 1/1 | 1.000 |
| c-top-customers-per-tag | combo | Q27, Q14, Q15 | 0/1 | 0.000 |
| c-top-growth-months | combo | Q13, Q4 | 0/1 | 0.000 |
| c-top-two-q1-share | combo | Q24, Q2, Q20 | 1/1 | 1.000 |
| c-vip-monthly-change | combo | Q27, Q4 | 1/1 | 1.000 |
| c-vip-region-share | combo | Q27, Q2 | 1/1 | 1.000 |
| c-weekday-share | combo | Q21, Q2 | 1/1 | 1.000 |
| j-c01-peak-weekday-hour | jaffle | — | 0/1 | 0.000 |
| j-c02-order-value-bands | jaffle | — | 1/1 | 1.000 |
| j-c03-basket-mix | jaffle | — | 1/1 | 1.000 |
| j-c04-ltv-by-first-store | jaffle | — | 1/1 | 1.000 |
| j-c05-median-orders-per-customer | jaffle | — | 1/1 | 1.000 |
| j-c06-top-decile-share | jaffle | — | 0/1 | 0.000 |
| j-c07-best-month-vs-avg | jaffle | — | 1/1 | 1.000 |
| j-c08-growth-streak | jaffle | — | 0/1 | 0.000 |
| j-c09-brooklyn-cogs-margin | jaffle | — | 0/1 | 0.000 |
| j-c10-top-supply-component | jaffle | — | 0/1 | 0.000 |
| j-c11-tweeters-aov | jaffle | — | 1/1 | 1.000 |
| j-c12-jaffle-beverage-attach | jaffle | — | 1/1 | 1.000 |
| j-q01-stores | jaffle | — | 1/1 | 1.000 |
| j-q02-orders-2025 | jaffle | — | 1/1 | 1.000 |
| j-q03-revenue-by-store-2025 | jaffle | — | 1/1 | 1.000 |
| j-q04-monthly-orders-2026 | jaffle | — | 1/1 | 1.000 |
| j-q05-top-products-2025 | jaffle | — | 0/1 | 0.000 |
| j-q06-type-share-2025 | jaffle | — | 1/1 | 1.000 |
| j-q07-aov-by-store | jaffle | — | 1/1 | 1.000 |
| j-q08-tax-rate-check | jaffle | — | 1/1 | 1.000 |
| j-q09-store-growth-2024-2025 | jaffle | — | 0/1 | 0.000 |
| j-q10-new-customers-by-year | jaffle | — | 0/1 | 0.000 |
| j-q11-ytd-growth-same-store | jaffle | — | 0/1 | 0.000 |
| j-q12-best-unit-margin | jaffle | — | 0/1 | 0.000 |
| q1-region-total | capability | Q1 | 1/1 | 1.000 |
| q10-bronze-or-ok | capability | Q10 | 1/1 | 1.000 |
| q11-rolling-customers | capability | Q11 | 1/1 | 1.000 |
| q12-net-revenue | capability | Q12 | 1/1 | 1.000 |
| q13-top-cities-count | capability | Q13 | 0/1 | 0.000 |
| q14-top-customer-per-region | capability | Q14 | 0/1 | 0.000 |
| q15-revenue-bands | capability | Q15 | 0/1 | 0.000 |
| q16-order-size | capability | Q16 | 1/1 | 1.000 |
| q17-running-aov | capability | Q17 | 1/1 | 1.000 |
| q18-day-of-monthly | capability | Q18 | 1/1 | 1.000 |
| q2-city-share | capability | Q2 | 1/1 | 1.000 |
| q20-quarter-region | capability | Q20 | 1/1 | 1.000 |
| q21-weekday-revenue | capability | Q21 | 1/1 | 1.000 |
| q23-monthly-by-region | capability | Q23 | 1/1 | 1.000 |
| q24-top-two-per-region | capability | Q24 | 1/1 | 1.000 |
| q25-credit-per-order | capability | Q25 | 1/1 | 1.000 |
| q26-events-per-customer | capability | Q26 | 1/1 | 1.000 |
| q27-category-ratings | capability | Q27 | 1/1 | 1.000 |
| q27-customers-per-tag | capability | Q27 | 1/1 | 1.000 |
| q27-region-distinct-tags | capability | Q27 | 1/1 | 1.000 |
| q27-region-tag-set | capability | Q27 | 1/1 | 1.000 |
| q27-vip-and-eu | capability | Q27 | 1/1 | 1.000 |
| q27-vip-customers | capability | Q27 | 1/1 | 1.000 |
| q27-vip-or-partner | capability | Q27 | 1/1 | 1.000 |
| q3-avg-city-revenue | capability | Q3 | 0/1 | 0.000 |
| q4-prior-year | capability | Q4 | 1/1 | 1.000 |
| q4-running-total | capability | Q4 | 1/1 | 1.000 |
| q5-spend-band | capability | Q5 | 1/1 | 1.000 |
| q6-region-credit | capability | Q6 | 1/1 | 1.000 |
| q7-cumulative-change | capability | Q7 | 1/1 | 1.000 |
| q8-tier-customers | capability | Q8 | 1/1 | 1.000 |
| t-all-time-running | trap | Q4, Q15, filter_before_window | 1/1 | 1.000 |
| t-bridge-email | trap | Q10, bridge | 1/1 | 1.000 |
| t-chasm | trap | Q6, chasm | 1/1 | 1.000 |
| t-city-size | trap | Q6, non_unique_key | 1/1 | 1.000 |
| t-count-after-join | trap | Q10, count_after_join | 1/1 | 1.000 |
| t-fan-out-credit | trap | Q8, fan_out | 1/1 | 1.000 |
| t-fan-out-items | trap | Q6, fan_out | 1/1 | 1.000 |
| t-march-events | trap | Q20, timestamp_bounds | 1/1 | 1.000 |
| t-monthly-gaps | trap | Q4, missing_periods | 1/1 | 1.000 |
| t-never-returned | trap | Q10, not_in_null | 1/1 | 1.000 |
| t-ok-share | trap | Q2, filtered_total | 1/1 | 1.000 |
| t-orders-per-category | trap | Q1, distinct_reagg | 1/1 | 1.000 |
| t-orders-per-customer | trap | Q8, count_outer_join | 1/1 | 1.000 |
| t-overall-aov | trap | Q1, avg_of_avgs | 1/1 | 1.000 |
| t-prev-month | trap | Q4, filter_before_window | 1/1 | 1.000 |
| t-rolling-gap | trap | Q11, rows_window_gap | 0/1 | 0.000 |
| t-tagged-credit | trap | Q27, unnest_fan_out | 1/1 | 1.000 |
| t-vip-and-eu-region | trap | Q27, same_element_and | 1/1 | 1.000 |
| t-vip-per-tier | trap | Q27, count_after_unnest | 1/1 | 1.000 |
| t-without-vip | trap | Q27, null_element | 1/1 | 1.000 |
| t-zero-regions | trap | Q8, outer_join_filter | 0/1 | 0.000 |

## `motley+python` · `claude-opus-5-5`

Motley's `query` cannot run a saved query by name with `refine` yet (DEV-2260); saved-query tasks are answered with one inline query.

A task counts under every row it covers, so a multi-row task adds to several rows.

| Row | Feature | Tasks | Trials | Correct | Single query | Passed | Python | Raw SQL | Model edits | Query errors | Several queries |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Q1 | Coarser grain in the same query | 4 | 4 | 4 | 4 | 4 | 0 | 0 | 0 | 0 | 3 |
| Q2 | Arithmetic across grains | 9 | 9 | 9 | 7 | 7 | 1 | 1 | 0 | 0 | 4 |
| Q3 | Re-aggregation | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 |
| Q4 | Transforms / time shift | 11 | 11 | 11 | 8 | 8 | 1 | 0 | 0 | 1 | 1 |
| Q5 | Calculated dimensions, filters, order | 2 | 2 | 2 | 2 | 2 | 0 | 0 | 0 | 0 | 2 |
| Q6 | Fields from many models, fan-out safe | 7 | 7 | 7 | 6 | 6 | 0 | 0 | 0 | 0 | 5 |
| Q7 | Deep composition | 1 | 1 | 1 | 0 | 0 | 1 | 0 | 0 | 0 | 0 |
| Q8 | Population inference | 4 | 4 | 4 | 3 | 3 | 0 | 0 | 0 | 0 | 1 |
| Q9 | No silently wrong numbers | 0 | 0 |  |  |  |  |  |  |  |  |
| Q10 | Filters across one-to-many joins | 4 | 4 | 4 | 3 | 3 | 0 | 0 | 0 | 0 | 2 |
| Q11 | Rolling time windows | 2 | 2 | 2 | 1 | 1 | 1 | 0 | 0 | 0 | 0 |
| Q12 | Aggregates as arguments | 2 | 2 | 2 | 2 | 2 | 0 | 0 | 0 | 0 | 2 |
| Q13 | Order by what you don't show | 2 | 2 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| Q14 | Ranking and streaks | 4 | 4 | 4 | 2 | 2 | 0 | 0 | 0 | 1 | 2 |
| Q15 | Multi-stage queries | 3 | 3 | 3 | 2 | 2 | 0 | 0 | 0 | 1 | 2 |
| Q16 | Inline model extension | 2 | 2 | 2 | 2 | 2 | 0 | 0 | 0 | 0 | 1 |
| Q17 | Saved measures that compose | 2 | 2 | 2 | 2 | 2 | 0 | 0 | 0 | 0 | 0 |
| Q18 | Time-bucket safety | 1 | 1 | 1 | 1 | 1 | 0 | 0 | 0 | 1 | 0 |
| Q19 | Agent & API surface | not covered |  |  |  |  |  |  |  |  |  |
| Q20 | Relative & typed filters | 3 | 3 | 3 | 2 | 2 | 0 | 0 | 0 | 0 | 1 |
| Q21 | Calendar expressions | 2 | 2 | 2 | 2 | 2 | 0 | 2 | 0 | 0 | 0 |
| Q22 | Nested source data | not covered |  |  |  |  |  |  |  |  |  |
| Q23 | Saved queries & refinement | 2 | 2 | 2 | 2 | 2 | 0 | 0 | 0 | 0 | 1 |
| Q24 | Nested / hierarchical results | 2 | 2 | 2 | 1 | 1 | 0 | 0 | 0 | 0 | 0 |
| Q25 | Explicit aggregate locality | 1 | 1 | 1 | 1 | 1 | 0 | 0 | 0 | 0 | 1 |
| Q26 | Metrics without a join path | 1 | 1 | 1 | 1 | 1 | 0 | 0 | 0 | 0 | 0 |
| Q27 | List columns | 15 | 15 | 15 | 13 | 13 | 0 | 0 | 0 | 1 | 10 |

| Task | Suite | Covers | Pass rate | pass^1 |
| --- | --- | --- | --- | --- |
| c-aov-change | combo | Q17, Q4 | 1/1 | 1.000 |
| c-net-region-tier | combo | Q6, Q12, Q1 | 1/1 | 1.000 |
| c-region-credit-rank | combo | Q6, Q14 | 0/1 | 0.000 |
| c-region-month-share | combo | Q2, Q4 | 0/1 | 0.000 |
| c-saved-running | combo | Q23, Q4 | 1/1 | 1.000 |
| c-size-class-months | combo | Q16, Q2, Q4 | 1/1 | 1.000 |
| c-spend-band-share | combo | Q5, Q2 | 1/1 | 1.000 |
| c-tier-credit-tags | combo | Q27, Q6 | 1/1 | 1.000 |
| c-top-customer-share | combo | Q14, Q2 | 1/1 | 1.000 |
| c-top-customers-per-tag | combo | Q27, Q14, Q15 | 0/1 | 0.000 |
| c-top-growth-months | combo | Q13, Q4 | 0/1 | 0.000 |
| c-top-two-q1-share | combo | Q24, Q2, Q20 | 0/1 | 0.000 |
| c-vip-monthly-change | combo | Q27, Q4 | 1/1 | 1.000 |
| c-vip-region-share | combo | Q27, Q2 | 1/1 | 1.000 |
| c-weekday-share | combo | Q21, Q2 | 1/1 | 1.000 |
| j-c01-peak-weekday-hour | jaffle | — | 0/1 | 0.000 |
| j-c02-order-value-bands | jaffle | — | 1/1 | 1.000 |
| j-c03-basket-mix | jaffle | — | 1/1 | 1.000 |
| j-c04-ltv-by-first-store | jaffle | — | 0/1 | 0.000 |
| j-c05-median-orders-per-customer | jaffle | — | 1/1 | 1.000 |
| j-c06-top-decile-share | jaffle | — | 0/1 | 0.000 |
| j-c07-best-month-vs-avg | jaffle | — | 0/1 | 0.000 |
| j-c08-growth-streak | jaffle | — | 0/1 | 0.000 |
| j-c09-brooklyn-cogs-margin | jaffle | — | 0/1 | 0.000 |
| j-c10-top-supply-component | jaffle | — | 0/1 | 0.000 |
| j-c11-tweeters-aov | jaffle | — | 1/1 | 1.000 |
| j-c12-jaffle-beverage-attach | jaffle | — | 1/1 | 1.000 |
| j-q01-stores | jaffle | — | 1/1 | 1.000 |
| j-q02-orders-2025 | jaffle | — | 1/1 | 1.000 |
| j-q03-revenue-by-store-2025 | jaffle | — | 1/1 | 1.000 |
| j-q04-monthly-orders-2026 | jaffle | — | 1/1 | 1.000 |
| j-q05-top-products-2025 | jaffle | — | 0/1 | 0.000 |
| j-q06-type-share-2025 | jaffle | — | 1/1 | 1.000 |
| j-q07-aov-by-store | jaffle | — | 1/1 | 1.000 |
| j-q08-tax-rate-check | jaffle | — | 1/1 | 1.000 |
| j-q09-store-growth-2024-2025 | jaffle | — | 0/1 | 0.000 |
| j-q10-new-customers-by-year | jaffle | — | 0/1 | 0.000 |
| j-q11-ytd-growth-same-store | jaffle | — | 0/1 | 0.000 |
| j-q12-best-unit-margin | jaffle | — | 0/1 | 0.000 |
| q1-region-total | capability | Q1 | 1/1 | 1.000 |
| q10-bronze-or-ok | capability | Q10 | 0/1 | 0.000 |
| q11-rolling-customers | capability | Q11 | 1/1 | 1.000 |
| q12-net-revenue | capability | Q12 | 1/1 | 1.000 |
| q13-top-cities-count | capability | Q13 | 0/1 | 0.000 |
| q14-top-customer-per-region | capability | Q14 | 1/1 | 1.000 |
| q15-revenue-bands | capability | Q15 | 1/1 | 1.000 |
| q16-order-size | capability | Q16 | 1/1 | 1.000 |
| q17-running-aov | capability | Q17 | 1/1 | 1.000 |
| q18-day-of-monthly | capability | Q18 | 1/1 | 1.000 |
| q2-city-share | capability | Q2 | 1/1 | 1.000 |
| q20-quarter-region | capability | Q20 | 1/1 | 1.000 |
| q21-weekday-revenue | capability | Q21 | 1/1 | 1.000 |
| q23-monthly-by-region | capability | Q23 | 1/1 | 1.000 |
| q24-top-two-per-region | capability | Q24 | 1/1 | 1.000 |
| q25-credit-per-order | capability | Q25 | 1/1 | 1.000 |
| q26-events-per-customer | capability | Q26 | 1/1 | 1.000 |
| q27-category-ratings | capability | Q27 | 1/1 | 1.000 |
| q27-customers-per-tag | capability | Q27 | 1/1 | 1.000 |
| q27-region-distinct-tags | capability | Q27 | 1/1 | 1.000 |
| q27-region-tag-set | capability | Q27 | 0/1 | 0.000 |
| q27-vip-and-eu | capability | Q27 | 1/1 | 1.000 |
| q27-vip-customers | capability | Q27 | 1/1 | 1.000 |
| q27-vip-or-partner | capability | Q27 | 1/1 | 1.000 |
| q3-avg-city-revenue | capability | Q3 | 0/1 | 0.000 |
| q4-prior-year | capability | Q4 | 1/1 | 1.000 |
| q4-running-total | capability | Q4 | 1/1 | 1.000 |
| q5-spend-band | capability | Q5 | 1/1 | 1.000 |
| q6-region-credit | capability | Q6 | 1/1 | 1.000 |
| q7-cumulative-change | capability | Q7 | 0/1 | 0.000 |
| q8-tier-customers | capability | Q8 | 1/1 | 1.000 |
| t-all-time-running | trap | Q4, Q15, filter_before_window | 1/1 | 1.000 |
| t-bridge-email | trap | Q10, bridge | 1/1 | 1.000 |
| t-chasm | trap | Q6, chasm | 1/1 | 1.000 |
| t-city-size | trap | Q6, non_unique_key | 1/1 | 1.000 |
| t-count-after-join | trap | Q10, count_after_join | 1/1 | 1.000 |
| t-fan-out-credit | trap | Q8, fan_out | 1/1 | 1.000 |
| t-fan-out-items | trap | Q6, fan_out | 1/1 | 1.000 |
| t-march-events | trap | Q20, timestamp_bounds | 1/1 | 1.000 |
| t-monthly-gaps | trap | Q4, missing_periods | 0/1 | 0.000 |
| t-never-returned | trap | Q10, not_in_null | 1/1 | 1.000 |
| t-ok-share | trap | Q2, filtered_total | 1/1 | 1.000 |
| t-orders-per-category | trap | Q1, distinct_reagg | 1/1 | 1.000 |
| t-orders-per-customer | trap | Q8, count_outer_join | 1/1 | 1.000 |
| t-overall-aov | trap | Q1, avg_of_avgs | 1/1 | 1.000 |
| t-prev-month | trap | Q4, filter_before_window | 1/1 | 1.000 |
| t-rolling-gap | trap | Q11, rows_window_gap | 0/1 | 0.000 |
| t-tagged-credit | trap | Q27, unnest_fan_out | 1/1 | 1.000 |
| t-vip-and-eu-region | trap | Q27, same_element_and | 1/1 | 1.000 |
| t-vip-per-tier | trap | Q27, count_after_unnest | 1/1 | 1.000 |
| t-without-vip | trap | Q27, null_element | 1/1 | 1.000 |
| t-zero-regions | trap | Q8, outer_join_filter | 0/1 | 0.000 |

## Expected failures (xfail)

These tasks run but are left out of the pass counts until the linked issue is fixed.

| Task | Issue | Profile | Model | Trials | Passed |
| --- | --- | --- | --- | --- | --- |
| q20-last-three-months | DEV-2058 | motley | claude-opus-5-5 | 1 | 0 |
| q20-last-three-months | DEV-2058 | motley+python | claude-opus-5-5 | 1 | 0 |
| q20-last-three-months | DEV-2058 | slayer | claude-opus-5-5 | 1 | 0 |
| q20-last-three-months | DEV-2058 | slayer+python | claude-opus-5-5 | 1 | 0 |
| q20-last-three-months | DEV-2058 | sql+python | claude-opus-5-5 | 1 | 0 |
| q27-tag-count-groups | DEV-2209 | motley | claude-opus-5-5 | 1 | 0 |
| q27-tag-count-groups | DEV-2209 | motley+python | claude-opus-5-5 | 1 | 0 |
| q27-tag-count-groups | DEV-2209 | slayer | claude-opus-5-5 | 1 | 1 |
| q27-tag-count-groups | DEV-2209 | slayer+python | claude-opus-5-5 | 1 | 1 |
| q9-credit-by-status | DEV-1951 | motley | claude-opus-5-5 | 1 | 0 |
| q9-credit-by-status | DEV-1951 | motley+python | claude-opus-5-5 | 1 | 0 |

## Totals

| Total | Value |
| --- | --- |
| Trials | 470 |
| Input tokens | 3248 |
| Output tokens | 293753 |
| Cache read tokens | 66331145 |
| Cache write tokens | 2930102 |
| Cost (USD) | 33.80 |
| Duration (s) | 6442 |

## Failed trials

- **c-region-credit-rank** (Q6, Q14) · motley · claude-opus-5-5 · trial 1 · submitted
  - single query: no single query returns the answer (last, query #4: result has 5 rows, truth has 4)
  - #1 `inspect` {"entity_type":"model"} → ok
  - #2 `inspect` {"entity_type":"model","reference":"customers"} → ok
  - #3 `inspect` {"entity_type":"model","reference":"regions"} → ok
  - #4 `query` customers dimensions=["regions.name"] measures=[{"formula":"sum(orders.amount)","name":"revenue"},{"formula":"rank(sum(orders.amount), direction='desc')","name":"rank"},{"formula":"sum(credit)","name":"credit_total"}] → 5 rows
- **c-region-credit-rank** (Q6, Q14) · motley+python · claude-opus-5-5 · trial 1 · submitted
  - single query: no single query returns the answer (last, query #4: result has 5 rows, truth has 4)
  - #1 `inspect` {"entity_type":"model"} → ok
  - #2 `inspect` {"entity_type":"model","reference":"customers","num_rows":3} → ok
  - #3 `inspect` {"entity_type":"model","reference":"regions","num_rows":5} → ok
  - #4 `query` regions dimensions=["name"] measures=[{"formula":"sum(customers.orders.amount)","name":"revenue"},{"formula":"rank(sum(customers.orders.amount), direction='desc')","name":"rank"},{"formula":"sum(customers.credit)","name":"credit"}] → 5 rows
- **c-region-credit-rank** (Q6, Q14) · slayer · claude-opus-5-5 · trial 1 · submitted
  - single query: no single query returns the answer (last, query #4: result has 5 rows, truth has 4)
  - #1 `list_datasources` {} → ok
  - #2 `models_summary` {"datasource_name":"bench"} → ok
  - #3 `inspect` {"reference":["bench.customers","bench.regions","bench.cities","bench.orders"],"entity_type":"model","compact":false} → ok
  - #4 `query` regions dimensions=["name"] measures=[{"formula":"sum(customers.orders.amount)","name":"revenue"},{"formula":"rank(sum(customers.orders.amount), direction='desc')","name":"revenue_rank"},{"formula":"sum(customers.credit)","name":"total_cre… → 5 rows
- **c-region-credit-rank** (Q6, Q14) · slayer+python · claude-opus-5-5 · trial 1 · submitted
  - single query: no single query returns the answer (last, query #4: result has 5 rows, truth has 4)
  - #1 `list_datasources` {} → ok
  - #2 `models_summary` {"datasource_name":"bench"} → ok
  - #3 `inspect` {"reference":["bench.customers","bench.regions","bench.cities"],"entity_type":"model","compact":false} → ok
  - #4 `query` regions dimensions=["name"] measures=[{"formula":"sum(customers.orders.amount)","name":"revenue"},{"formula":"rank(sum(customers.orders.amount), direction='desc')","name":"revenue_rank"},{"formula":"sum(customers.credit)","name":"total_cre… → 5 rows
- **c-region-credit-rank** (Q6, Q14) · sql+python · claude-opus-5-5 · trial 1 · submitted
  - single query: no single query returns the answer (last, query #4: result has 5 rows, truth has 4)
  - flags: Raw SQL, Several queries
  - #1 `sql` select table_name, column_name, data_type from information_schema.columns order by table_name, ordinal_position → 53 rows
  - #2 `sql` select (select count(*) from customers where region_id is null) nullreg, (select count(*) from customers c where region_id is not null and region_id not in (select id from regions)) orphan, (select count(*) from regions) nr, (select count(… → 1 rows
  - #3 `sql` select * from regions → 5 rows
  - #4 `sql` with rev as (select c.region_id, sum(o.amount) revenue from orders o join customers c on c.id=o.customer_id where c.region_id is not null group by 1), cr as (select region_id, sum(credit) credit, count(*) n from customers where region_id i… → 5 rows
- **c-region-month-share** (Q2, Q4) · motley+python · claude-opus-5-5 · trial 1 · submitted
  - single query: no single query returns the answer (last, query #4: result has 17 rows, truth has 12)
  - flags: Python
  - #1 `inspect` {"entity_type":"model"} → ok
  - #2 `inspect` {"entity_type":"model","reference":"customers","num_rows":3} → ok
  - #3 `inspect` {"entity_type":"model","reference":"orders","num_rows":3} → ok
  - #4 `query` orders dimensions=["customers.regions.name"] time_dimensions=[{"dimension":{"name":"order_date"},"granularity":"month","date_range":["2024-12-01","2025-03-31"]}] measures=[{"formula":"sum(amount)","name":"revenue"}] → 17 rows
- **c-region-month-share** (Q2, Q4) · sql+python · claude-opus-5-5 · trial 1 · submitted
  - single query: no single query returns the answer (last, query #4: result has 15 rows, truth has 12)
  - flags: Raw SQL, Several queries
  - #1 `sql` select table_name, column_name, data_type from information_schema.columns order by table_name, ordinal_position → 53 rows
  - #2 `sql` select (select count(*) from orders where customer_id is null) nullcust, (select count(*) from orders o where customer_id not in (select id from customers)) orphan, (select count(*) from customers where region_id is null) nullreg, (select … → 1 rows
  - #3 `sql` with b as (select date_trunc('month', o.order_date)::date m, r.name region, sum(o.amount) rev from orders o left join customers c on c.id=o.customer_id left join regions r on r.id=c.region_id where o.order_date >= '2024-12-01' and o.order_… → 15 rows
  - #4 `sql` select date_trunc('month', o.order_date) m, sum(amount), count(*) from orders o left join customers c on c.id=o.customer_id where c.region_id is null group by 1 order by 1 → 15 rows
- **c-saved-running** (Q23, Q4) · sql+python · claude-opus-5-5 · trial 1 · auto_fail
  - correct: needs the saved SLayer definitions monthly_rev
  - single query: needs the saved SLayer definitions monthly_rev
  - no query calls
- **c-top-customer-share** (Q14, Q2) · sql+python · claude-opus-5-5 · trial 1 · submitted
  - single query: no single query returns the answer (last, query #3: result has 8 rows, truth has 4)
  - flags: Raw SQL, Query errors, Several queries
  - #1 `sql` select table_name, column_name, data_type from information_schema.columns order by table_name → 53 rows
  - #2 `sql` with r as (select c.region_id, rg.name, o.customer_id, sum(o.amount) rev from orders o join customers c on c.id=o.customer_id left join regions rg on rg.id=c.region_id where c.region_id is not null group by all), t as (select *, sum(rev) o… → error
  - #3 `sql` with r as (select c.region_id, rg.name, o.customer_id, sum(o.amount) rev from orders o join customers c on c.id=o.customer_id left join regions rg on rg.id=c.region_id where c.region_id is not null group by all), t as (select *, sum(rev) o… → 8 rows
- **c-top-customers-per-tag** (Q27, Q14, Q15) · motley · claude-opus-5-5 · trial 1 · submitted
  - single query: no single query returns the answer (last, query #7: no result column has the values of 'tag', 'customer_id', 'name', 'revenue')
  - flags: Query errors, Several queries
  - #1 `inspect` {"entity_type":"model"} → ok
  - #2 `inspect` {"entity_type":"model","reference":"customers","num_rows":3} → ok
  - #3 `inspect` {"entity_type":"model","reference":"tags"} → ok
  - #4 `query` customers dimensions=["tags.value","id","name"] measures=[{"formula":"sum(orders.amount)","name":"revenue"},{"formula":"rank(sum(orders.amount), partition_by=tags.value, direction='desc')","name":"rk"}] filters=["rank(sum(orders.amount), p… → error PartitionKeyError
  - #5 `query` customers dimensions=["tags.value","id","name"] measures=[{"formula":"sum(orders.amount)","name":"revenue"}] ; s1 dimensions=["tags__value","id","name"] measures=[{"formula":"sum(revenue)","name":"revenue"},{"formula":"rank(sum(revenue), p… → error MeasureNameCollidesWithColumnError
  - #6 `query` customers dimensions=["tags.value","id","name"] measures=[{"formula":"sum(orders.amount)","name":"rev"}] ; s1 dimensions=["tags__value","id","name"] measures=[{"formula":"sum(rev)","name":"revenue"},{"formula":"rank(sum(rev), partition_by=… → 24 rows
  - #7 `query` customers dimensions=["id"] measures=[{"formula":"sum(orders.amount)","name":"rev"}] filters=["id in (119,171,93,111,129,53,138,130,64,116,153,94,83,68,87,38)"] → 16 rows
- **c-top-customers-per-tag** (Q27, Q14, Q15) · motley+python · claude-opus-5-5 · trial 1 · submitted
  - single query: no single query returns the answer (last, query #4: result has 24 rows, truth has 16)
  - flags: Query errors, Several queries
  - #1 `inspect` {"entity_type":"model"} → ok
  - #2 `inspect` {"entity_type":"model","reference":"customers","num_rows":3} → ok
  - #3 `query` customers dimensions=["tags.value","id","name"] measures=[{"formula":"sum(orders.amount)","name":"revenue"}] filters=["rank(sum(orders.amount), partition_by=tags.value, direction='desc') <= 3"] order=[{"column":"tags.value","direction":"as… → error PartitionKeyError
  - #4 `query` customers dimensions=["tags.value","id","name"] measures=[{"formula":"sum(orders.amount)","name":"revenue"}] ; s1 dimensions=["tags__value","id","name","revenue"] measures=[{"formula":"rank(sum(revenue), partition_by=tags__value, direction… → 24 rows
- **c-top-customers-per-tag** (Q27, Q14, Q15) · sql+python · claude-opus-5-5 · trial 1 · submitted
  - correct: result has 17 rows, truth has 16
  - single query: no single query returns the answer (last, query #3: result has 25 rows, truth has 16)
  - flags: Raw SQL, Several queries
  - #1 `sql` select table_name, column_name, data_type from information_schema.columns order by table_name, ordinal_position → 53 rows
  - #2 `sql` with t as (select id, name, unnest(tags) tag from customers), r as (select customer_id, sum(amount) rev, count(*) n, count(amount) na from orders group by 1) select tag, count(*), count(distinct id), sum(case when r.customer_id is null the… → 9 rows
  - #3 `sql` with t as (select distinct id, name, unnest(tags) tag from customers), r as (select customer_id, sum(amount) rev from orders group by 1), x as (select tag, id, name, rev, rank() over (partition by tag order by rev desc nulls last) rk, row_… → 25 rows
- **c-top-growth-months** (Q13, Q4) · motley · claude-opus-5-5 · trial 1 · submitted
  - single query: no single query returns the answer (last, query #4: result has 3 columns, expected exactly 2)
  - #1 `inspect` {"entity_type":"model"} → ok
  - #2 `inspect` {"entity_type":"model","reference":"orders","num_rows":3} → ok
  - #3 `search` {"question":"revenue definition orders status bad","entities":["orders","monthly_rev"]} → ok
  - #4 `query` orders time_dimensions=[{"dimension":"order_date","granularity":"month","date_range":"2025"}] measures=[{"formula":"sum(amount)","name":"revenue"},{"formula":"change(sum(amount))","name":"inc"}] order=[{"column":"inc","direction":"desc"}] → 12 rows
- **c-top-growth-months** (Q13, Q4) · motley+python · claude-opus-5-5 · trial 1 · submitted
  - single query: no single query returns the answer (last, query #3: result has 3 columns, expected exactly 2)
  - #1 `inspect` {"entity_type":"model"} → ok
  - #2 `inspect` {"entity_type":"model","reference":"orders","num_rows":3} → ok
  - #3 `query` orders time_dimensions=[{"dimension":{"name":"order_date"},"granularity":"month","date_range":"2025"}] measures=[{"formula":"sum(amount)","name":"revenue"},{"formula":"change(sum(amount))","name":"inc"}] → 12 rows
- **c-top-growth-months** (Q13, Q4) · slayer+python · claude-opus-5-5 · trial 1 · submitted
  - single query: no single query returns the answer (last, query #3: result has 3 columns, expected exactly 2)
  - #1 `search` {"question":"orders amount revenue"} → ok
  - #2 `inspect` {"reference":"bench.orders","entity_type":"model","compact":false} → ok
  - #3 `query` orders time_dimensions=[{"dimension":"order_date","granularity":"month","date_range":"2025"}] measures=[{"formula":"sum(amount)","name":"revenue"},{"formula":"change(sum(amount))","name":"inc"}] order=[{"column":"inc","direction":"desc"}] → 12 rows
- **c-top-growth-months** (Q13, Q4) · sql+python · claude-opus-5-5 · trial 1 · submitted
  - single query: no single query returns the answer (last, query #3: result has 2 rows, truth has 3)
  - flags: Raw SQL, Several queries
  - #1 `sql` select table_name, column_name, data_type from information_schema.columns order by table_name → 53 rows
  - #2 `sql` select date_trunc('month', order_date) m, sum(amount) rev, count(*), count(amount) from orders group by 1 order by 1 → 35 rows
  - #3 `sql` select status, count(*) from orders group by 1 → 2 rows
- **c-top-two-q1-share** (Q24, Q2, Q20) · motley+python · claude-opus-5-5 · trial 1 · submitted
  - single query: no single query returns the answer (last, query #4: result has 12 rows, truth has 8)
  - #1 `inspect` {"entity_type":"model"} → ok
  - #2 `inspect` {"entity_type":"model","reference":"customers","num_rows":3} → ok
  - #3 `inspect` {"entity_type":"model","reference":"orders","num_rows":3} → ok
  - #4 `query` orders dimensions=["customers.regions.name","customers.region_id","customer_id"] measures=[{"formula":"sum(amount)","name":"revenue"},{"formula":"sum(amount)/sum(amount, partition_by=[customers.regions.name, customers.region_id])","name":"… → 12 rows
- **c-top-two-q1-share** (Q24, Q2, Q20) · sql+python · claude-opus-5-5 · trial 1 · submitted
  - single query: no single query returns the answer (last, query #5: result has 12 rows, truth has 8)
  - flags: Raw SQL, Query errors, Several queries
  - #1 `sql` select table_name, column_name, data_type from information_schema.columns order by table_name → 53 rows
  - #2 `sql` select status, count(*), count(amount), sum(amount), min(order_date), max(order_date) from orders group by all → 2 rows
  - #3 `sql` select (select count(*) from regions), (select count(distinct id) from regions), (select count(*) from customers),(select count(distinct id) from customers),(select count(*) from customers where region_id is null), (select count(*) from cu… → 1 rows
  - #4 `sql` with c as (select r.name region, o.customer_id, sum(o.amount) rev from orders o join customers cu on cu.id=o.customer_id join regions r on r.id=cu.region_id where o.order_date>='2025-01-01' and o.order_date<'2025-04-01' group by all), t as… → error
  - #5 `sql` with c as (select r.name region, o.customer_id, sum(o.amount) rev from orders o join customers cu on cu.id=o.customer_id join regions r on r.id=cu.region_id where o.order_date>='2025-01-01' and o.order_date<'2025-04-01' group by all), t as… → 12 rows
- **c-vip-monthly-change** (Q27, Q4) · sql+python · claude-opus-5-5 · trial 1 · submitted
  - single query: no single query returns the answer (last, query #6: result has 13 rows, truth has 12)
  - flags: Raw SQL, Query errors, Several queries
  - #1 `sql` select table_name, column_name, data_type from information_schema.columns order by table_name, ordinal_position → 53 rows
  - #2 `sql` select distinct unnest(tags) t, count(*) from customers group by all → error
  - #3 `sql` select status, count(*), min(order_date), max(order_date), count(*) filter (where amount is null) from orders group by 1 → 2 rows
  - #4 `sql` select t, count(*) from (select unnest(tags) t from customers) group by 1 → 9 rows
  - #5 `sql` with m as (select range::date mo from range(date '2024-12-01', date '2026-01-01', interval 1 month)), r as (select date_trunc('month', o.order_date)::date mo, sum(o.amount) rev from orders o join customers c on c.id=o.customer_id where lis… → error
  - #6 `sql` with m as (select range::date mo from range(date '2024-12-01', date '2026-01-01', interval 1 month)), r as (select date_trunc('month', o.order_date)::date mo, sum(o.amount) rev, count(*) n from orders o join customers c on c.id=o.customer_… → 13 rows
- **j-c01-peak-weekday-hour** (—) · motley · claude-opus-5-5 · trial 1 · submitted
  - single query: no single query returns the answer (last, query #5: no result column has the values of 'weekday', 'hour', 'share')
  - flags: Query errors, Several queries
  - #1 `search` {"question":"pre-tax sales order time weekday hour"} → ok
  - #2 `query` orders dimensions=["order_weekday","order_hour"] measures=["net_sales",{"formula":"net_sales / net_sales(partition_by=[])","name":"share"}] filters=["ordered_at >= '2025-01-01'","ordered_at < '2026-01-01'"] order=[{"column":"net_sales","di… → error UnknownFunctionError
  - #3 `inspect` {"entity_type":"measure","reference":"orders.net_sales"} → ok
  - #4 `query` orders dimensions=["order_weekday","order_hour"] measures=["net_sales",{"formula":"net_sales / subtotal:dollars(partition_by=[])","name":"share"}] filters=["ordered_at >= '2025-01-01'","ordered_at < '2026-01-01'"] order=[{"column":"net_sal… → 3 rows, truncated warning
  - #5 `query` orders measures=["net_sales"] filters=["ordered_at >= '2025-01-01'","ordered_at < '2026-01-01'"] → 1 rows
- **j-c01-peak-weekday-hour** (—) · motley+python · claude-opus-5-5 · trial 1 · submitted
  - single query: no single query returns the answer (last, query #6: result has 3 rows, truth has 1)
  - flags: Query errors, Several queries
  - #1 `search` {"question":"pre-tax sales orders subtotal ordered_at"} → ok
  - #2 `inspect` {"entity_type":"model","reference":"orders"} → ok
  - #3 `inspect` {"entity_type":"column","reference":"orders.order_weekday","show_sql":true} → ok
  - #4 `inspect` {"entity_type":"column","reference":"orders.order_hour","show_sql":true} → ok
  - #5 `query` orders dimensions=["order_weekday","order_hour"] measures=["net_sales",{"formula":"net_sales / net_sales(partition_by=[])","name":"share"}] filters=["ordered_at in '2025'"] order=[{"column":"net_sales","direction":"desc"}] → error UnknownFunctionError
  - #6 `query` orders dimensions=["order_weekday","order_hour"] measures=["net_sales",{"formula":"sum(subtotal) / sum(subtotal, partition_by=[])","name":"share"},"sum(subtotal)"] filters=["ordered_at in '2025'"] order=[{"column":"net_sales","direction":"… → 3 rows, truncated warning
- **j-c01-peak-weekday-hour** (—) · slayer · claude-opus-5-5 · trial 1 · submitted
  - single query: no single query returns the answer (last, query #4: result has 2 rows, truth has 1)
  - flags: Several queries
  - #1 `search` {"question":"pre-tax sales orders weekday hour"} → ok
  - #2 `inspect` {"reference":"demo_database.orders","entity_type":"model","compact":false,"sections":["columns","measures","aggregations"]} → ok
  - #3 `query` orders dimensions=["order_weekday","order_hour"] measures=[{"formula":"net_sales","name":"sales"},{"formula":"subtotal:dollars / subtotal:dollars(partition_by=[])","name":"share"}] filters=["ordered_at in '2025'"] order=[{"column":"sales",… → 3 rows
  - #4 `query` orders dimensions=["order_weekday","order_hour"] measures=[{"formula":"subtotal:sum","name":"cents"},{"formula":"net_sales","name":"sales"},{"formula":"subtotal:sum(partition_by=[])","name":"tot"}] filters=["ordered_at in '2025'"] order=[{… → 2 rows
- **j-c01-peak-weekday-hour** (—) · slayer+python · claude-opus-5-5 · trial 1 · submitted
  - single query: no single query returns the answer (last, query #4: result has 3 rows, truth has 1)
  - flags: Query errors, Several queries
  - #1 `search` {"question":"pre-tax sales order time"} → ok
  - #2 `inspect` {"reference":"demo_database.orders","entity_type":"model","compact":false} → ok
  - #3 `query` orders dimensions=["order_weekday","order_hour"] measures=[{"formula":"net_sales","name":"sales"},{"formula":"net_sales / net_sales(partition_by=[])","name":"share"}] filters=["ordered_at in '2025'"] order=[{"column":"sales","direction":"d… → error UnknownFunctionError
  - #4 `query` orders dimensions=["order_weekday","order_hour"] measures=[{"formula":"subtotal:dollars","name":"sales"},{"formula":"subtotal:sum / subtotal:sum(partition_by=[])","name":"share"}] filters=["ordered_at in '2025'"] order=[{"column":"sales","… → 3 rows
- **j-c01-peak-weekday-hour** (—) · sql+python · claude-opus-5-5 · trial 1 · submitted
  - single query: no single query returns the answer (last, query #2: result has 3 rows, truth has 1)
  - flags: Raw SQL, Query errors, Several queries
  - #1 `sql` WITH t AS (SELECT dayname(ordered_at) d, hour(ordered_at) h, SUM(subtotal)/100.0 s FROM orders WHERE ordered_at>='2025-01-01' AND ordered_at<'2026-01-01' GROUP BY 1,2) SELECT d,h,s, s/SUM(s) OVER () share, (SELECT max(ordered_at) FROM orde… → error
  - #2 `sql` WITH t AS (SELECT dayname(ordered_at) d, hour(ordered_at) h, SUM(subtotal)/100.0 s FROM orders WHERE ordered_at>='2025-01-01' AND ordered_at<'2026-01-01' GROUP BY 1,2) SELECT d,h,s, s/SUM(s) OVER () AS shr, (SELECT max(ordered_at) FROM ord… → 3 rows
- **j-c04-ltv-by-first-store** (—) · motley+python · claude-opus-5-5 · trial 1 · submitted
  - single query: no single query returns the answer (last, query #5: no result column has the values of 'store', 'customers', 'avg_lifetime_spend')
  - flags: Several queries
  - #1 `inspect` {"entity_type":"model"} → ok
  - #2 `inspect` {"entity_type":"model","reference":"orders","num_rows":3} → ok
  - #3 `search` {"question":"customer lifetime spend first order store pre-tax"} → ok
  - #4 `query` orders dimensions=["customer"] measures=[{"formula":"store_id:first","name":"first_store"},{"formula":"net_sales","name":"spend"},{"formula":"ordered_at:min","name":"first_at"}] ; cust dimensions=["first_store"] measures=[{"formula":"*:cou… → 6 rows
  - #5 `query` stores dimensions=["id","name"] → 6 rows
- **j-c06-top-decile-share** (—) · motley · claude-opus-5-5 · trial 1 · submitted
  - single query: no single query returns the answer (last, query #7: result has 2 rows, truth has 1)
  - flags: Query errors, Several queries
  - #1 `search` {"question":"pre-tax sales by customer orders"} → ok
  - #2 `inspect` {"entity_type":"model","reference":"orders"} → ok
  - #3 `query` orders dimensions=["customer"] measures=["net_sales","count(*)"] filters=["ordered_at >= '2025-01-01'","ordered_at < '2026-01-01'"] order=[{"column":"net_sales","direction":"desc"}] → ok
  - #4 `query` orders measures=["net_sales","unique_customers","count(*)"] filters=["ordered_at >= '2025-01-01'","ordered_at < '2026-01-01'"] → 1 rows
  - #5 `query` orders dimensions=["customer"] measures=[{"formula":"net_sales","name":"ns"}] filters=["ordered_at >= '2025-01-01'","ordered_at < '2026-01-01'"] ; pc measures=[{"formula":"sum(ns)","name":"top_sales"},{"formula":"count(*)","name":"n"},{"fo… → 1 rows
  - #6 `query` orders dimensions=["customer"] measures=[{"formula":"net_sales","name":"ns"}] filters=["ordered_at >= '2025-01-01'","ordered_at < '2026-01-01'"] ; pc dimensions=["customer"] measures=[{"formula":"sum(ns)","name":"s"},{"formula":"rank(sum(n… → error UnknownFunctionError
  - #7 `query` orders dimensions=["customer"] measures=[{"formula":"net_sales","name":"ns"}] filters=["ordered_at >= '2025-01-01'","ordered_at < '2026-01-01'"] ; pc dimensions=["customer"] measures=[{"formula":"sum(ns)","name":"s"},{"formula":"rank(sum(n… → 2 rows
- **j-c06-top-decile-share** (—) · motley+python · claude-opus-5-5 · trial 1 · submitted
  - single query: no single query returns the answer (last, query #7: no result column has the values of 'top_decile_share', 'top_decile_customers')
  - flags: Python, Query errors, Several queries
  - #1 `search` {"question":"pre-tax sales per customer orders 2025"} → ok
  - #2 `query` orders dimensions=["customer"] measures=["net_sales"] filters=["ordered_at >= '2025-01-01'","ordered_at < '2026-01-01'"] order=[{"column":"net_sales","direction":"desc"}] → error
  - #3 `query` orders dimensions=["customer"] measures=["net_sales"] filters=["ordered_at >= '2025-01-01'","ordered_at < '2026-01-01'"] order=[{"column":"net_sales","direction":"desc"}] → ok
  - #7 `query` orders measures=["net_sales","unique_customers","count(*)"] filters=["ordered_at >= '2025-01-01'","ordered_at < '2026-01-01'"] → 1 rows
- **j-c06-top-decile-share** (—) · slayer+python · claude-opus-5-5 · trial 1 · submitted
  - single query: no single query returns the answer (last, query #6: no result column has the values of 'top_decile_share', 'top_decile_customers')
  - flags: Query errors, Several queries
  - #1 `search` {"question":"2025 pre-tax sales by customer"} → ok
  - #2 `inspect` {"reference":"demo_database.orders","entity_type":"model","compact":false} → ok
  - #3 `query` orders dimensions=["customer"] measures=[{"formula":"net_sales","name":"spend"},{"formula":"rank(net_sales, direction='desc')","name":"rk"},{"formula":"count(*, partition_by=[])","name":"dummy"}] filters=["ordered_at >= '2025-01-01'","orde… → error
  - #4 `query` orders dimensions=["customer"] measures=[{"formula":"net_sales","name":"spend"},{"formula":"rank(net_sales, direction='desc')","name":"rk"}] filters=["ordered_at >= '2025-01-01'","ordered_at < '2026-01-01'"] ; cs measures=[{"formula":"coun… → 1 rows
  - #5 `query` orders dimensions=["customer"] measures=[{"formula":"net_sales","name":"spend"},{"formula":"rank(net_sales, direction='desc')","name":"rk"}] filters=["ordered_at >= '2025-01-01'","ordered_at < '2026-01-01'"] ; cs dimensions=["rk","spend"] … → 7 rows
  - #6 `query` orders dimensions=["customer"] measures=[{"formula":"net_sales","name":"spend"},{"formula":"rank(net_sales, direction='desc')","name":"rk"}] filters=["ordered_at >= '2025-01-01'","ordered_at < '2026-01-01'"] ; cs measures=[{"formula":"sum(… → 1 rows
- **j-c07-best-month-vs-avg** (—) · motley+python · claude-opus-5-5 · trial 1 · submitted
  - single query: no single query returns the answer (last, query #2: result has 58 rows, truth has 6)
  - flags: Python
  - #1 `search` {"question":"store monthly sales pre-tax"} → ok
  - #2 `query` orders dimensions=["stores.name","stores.opened_at"] time_dimensions=[{"dimension":"ordered_at","granularity":"month","date_range":"2025"}] measures=["net_sales"] → 58 rows
- **j-c08-growth-streak** (—) · motley · claude-opus-5-5 · trial 1 · submitted
  - single query: no single query returns the answer (last, query #2: result has 42 rows, truth has 1)
  - #1 `search` {"question":"Brooklyn pre-tax sales by month"} → ok
  - #2 `query` orders time_dimensions=[{"dimension":"ordered_at","granularity":"month","date_range":["2023-05-01","2026-10-31"]}] measures=["net_sales"] filters=["stores.name == 'Brooklyn'"] order=[{"column":"ordered_at","direction":"asc"}] → 42 rows
- **j-c08-growth-streak** (—) · motley+python · claude-opus-5-5 · trial 1 · submitted
  - single query: no single query returns the answer (last, query #2: result has 42 rows, truth has 1)
  - #1 `search` {"question":"Brooklyn pre-tax sales by month"} → ok
  - #2 `query` orders time_dimensions=[{"dimension":"ordered_at","granularity":"month","date_range":["2023-04-01","2026-11-30"]}] measures=["net_sales"] filters=["stores.name == 'Brooklyn'"] → 42 rows
- **j-c08-growth-streak** (—) · slayer · claude-opus-5-5 · trial 1 · submitted
  - single query: no single query returns the answer (last, query #3: result has 41 rows, truth has 1)
  - #1 `search` {"question":"Brooklyn pre-tax sales"} → ok
  - #2 `inspect` {"reference":"demo_database.stores.name","entity_type":"column","compact":false} → ok
  - #3 `query` orders time_dimensions=[{"dimension":"ordered_at","granularity":"month","date_range":["2023-05-01","2026-09-30"]}] measures=["net_sales",{"formula":"change(net_sales)","name":"chg"},{"formula":"consecutive_periods(change(net_sales) > 0)","… → 41 rows
- **j-c08-growth-streak** (—) · slayer+python · claude-opus-5-5 · trial 1 · submitted
  - single query: no single query returns the answer (last, query #2: result has 40 rows, truth has 1)
  - #1 `search` {"question":"Brooklyn pre-tax sales"} → ok
  - #2 `query` orders dimensions=[{"name":"name","model":"stores"}] time_dimensions=[{"dimension":{"name":"ordered_at"},"granularity":"month","date_range":["2023-06-01","2026-09-30"]}] measures=["net_sales"] filters=["stores.name like '%Brooklyn%'"] → 40 rows
- **j-c08-growth-streak** (—) · sql+python · claude-opus-5-5 · trial 1 · submitted
  - single query: no single query returns the answer (last, query #1: result has 42 rows, truth has 1)
  - flags: Raw SQL
  - #1 `sql` select date_trunc('month', o.ordered_at) m, sum(subtotal)/100.0 s, (select max(ordered_at) from orders) mx from orders o join stores s on o.store_id=s.id where s.name='Brooklyn' group by 1 order by 1 → 42 rows
- **j-c09-brooklyn-cogs-margin** (—) · motley · claude-opus-5-5 · trial 1 · submitted
  - single query: no single query returns the answer (last, query #4: result has 10 rows, truth has 1)
  - flags: Query errors, Several queries
  - #1 `search` {"question":"supply cost of items sold by store Brooklyn, product sales pre-tax"} → ok
  - #2 `query` items dimensions=["product_id"] measures=["count(*)","line_sales"] filters=["orders.stores.name == 'Brooklyn'","orders.ordered_at >= '2025-01-01'","orders.ordered_at < '2026-01-01'"] → error UnknownReferenceError
  - #3 `query` supplies dimensions=["sku"] measures=["total_supply_cost","count(*)"] → 10 rows
  - #4 `query` items dimensions=["sku"] measures=["count(*)","line_sales"] filters=["orders.stores.name == 'Brooklyn'","orders.ordered_at >= '2025-01-01'","orders.ordered_at < '2026-01-01'"] → 10 rows
  - #5 `inspect` {"entity_type":"model","reference":"supplies","num_rows":5} → ok
- **j-c09-brooklyn-cogs-margin** (—) · motley+python · claude-opus-5-5 · trial 1 · submitted
  - single query: no single query returns the answer (last, query #5: result has 10 rows, truth has 1)
  - flags: Python, Several queries
  - #1 `search` {"question":"supply cost of items sold by store Brooklyn, product sales pre-tax"} → ok
  - #2 `inspect` {"entity_type":"model","reference":"supplies","num_rows":5} → ok
  - #3 `inspect` {"entity_type":"model","reference":"items"} → ok
  - #4 `query` items dimensions=["sku"] measures=["units_sold","line_sales"] filters=["orders.stores.name == 'Brooklyn'","orders.ordered_at >= '2025-01-01'","orders.ordered_at < '2026-01-01'"] → 10 rows
  - #5 `query` supplies dimensions=["sku"] measures=["cost:sum","*:count"] → 10 rows
- **j-c10-top-supply-component** (—) · motley · claude-opus-5-5 · trial 1 · submitted
  - single query: no single query returns the answer (last, query #5: result has 65 rows, truth has 1)
  - flags: Several queries
  - #1 `search` {"question":"supply component cost per product (bread, cup)"} → ok
  - #2 `inspect` {"entity_type":"model","reference":"supplies","num_rows":5} → ok
  - #3 `inspect` {"entity_type":"model","reference":"items"} → ok
  - #4 `query` items dimensions=["sku"] measures=["units_sold"] filters=["orders.ordered_at >= '2025-01-01'","orders.ordered_at < '2026-01-01'"] → 10 rows
  - #5 `query` supplies dimensions=["name","sku"] measures=["cost:sum","*:count"] → 65 rows
- **j-c10-top-supply-component** (—) · motley+python · claude-opus-5-5 · trial 1 · submitted
  - single query: no single query returns the answer (last, query #5: result has 65 rows, truth has 1)
  - flags: Several queries
  - #1 `inspect` {"entity_type":"model"} → ok
  - #2 `inspect` {"entity_type":"model","reference":"supplies","num_rows":5} → ok
  - #3 `inspect` {"entity_type":"model","reference":"items","num_rows":3} → ok
  - #4 `query` items dimensions=["sku"] measures=["count(*)"] filters=["orders.ordered_at in '2025'"] → 10 rows
  - #5 `query` supplies dimensions=["id","name","sku","cost"] measures=["count(*)"] → 65 rows
- **j-c10-top-supply-component** (—) · slayer · claude-opus-5-5 · trial 1 · submitted
  - single query: no single query returns the answer (last, query #4: result has 5 rows, truth has 1)
  - flags: Raw SQL
  - #1 `search` {"question":"supply component cost per product (bread, cup)"} → ok
  - #2 `inspect` {"reference":["demo_database.supplies","demo_database.items"],"entity_type":"model","compact":false} → ok
  - #3 `inspect` {"reference":"demo_database.orders","entity_type":"model","sections":["columns"]} → ok
  - #4 `query` {'name': 'supply_usage', 'data_source': 'demo_database', 'sql': 'SELECT s.name AS supply_name, s.cost AS cost, o.ordered_at AS ordered_at FROM items i JOIN orders o ON i.order_id = o.id JOIN supplies s ON s.sku = i.sku', 'columns': [{'name… → 5 rows
- **j-c10-top-supply-component** (—) · slayer+python · claude-opus-5-5 · trial 1 · submitted
  - single query: no single query returns the answer (last, query #4: result has 5 rows, truth has 1)
  - flags: Raw SQL
  - #1 `search` {"question":"supply component cost per product"} → ok
  - #2 `inspect` {"reference":["supplies","items"],"entity_type":"model","compact":false} → ok
  - #3 `inspect` {"reference":"orders","entity_type":"model","sections":["columns"]} → ok
  - #4 `query` {'name': 'supply_usage', 'data_source': 'demo_database', 'sql': "select s.name as supply_name, s.cost as cost from items i join orders o on i.order_id = o.id join supplies s on s.sku = i.sku where o.ordered_at >= '2025-01-01' and o.ordered… → 5 rows
- **j-c10-top-supply-component** (—) · sql+python · claude-opus-5-5 · trial 1 · submitted
  - single query: no single query returns the answer (last, query #3: result has 5 rows, truth has 1)
  - flags: Raw SQL, Several queries
  - #1 `sql` select table_name, column_name, data_type from information_schema.columns where table_name in ('supplies','items','products','orders') order by 1 → 20 rows
  - #2 `sql` select id, name, count(*), count(distinct sku), min(cost), max(cost) from supplies group by all order by 1 → 29 rows
  - #3 `sql` select s.id, s.name, sum(s.cost)/100.0 total from items i join orders o on i.order_id=o.id join supplies s on s.sku=i.sku where year(o.ordered_at)=2025 group by all order by total desc limit 5 → 5 rows
- **j-c12-jaffle-beverage-attach** (—) · sql+python · claude-opus-5-5 · trial 1 · error
  - correct: no submission
  - single query: no submission
  - flags: Raw SQL, Query errors, Several queries
  - error: session ended without submitting an answer
  - #1 `sql` select table_name, column_name, data_type from information_schema.columns order by table_name → 30 rows
  - #2 `sql` select type, count(*) from products group by 1 → 2 rows
  - #3 `sql` with o as ( select o.id, o.store_id, max(case when p.type='jaffle' then 1 else 0 end) j, max(case when p.type='beverage' then 1 else 0 end) b from orders o join items i on i.order_id=o.id join products p on p.sku=i.sku where o.ordered_at>=… → error
  - #4 `sql` with o as ( select o.id, o.store_id, max(case when p.type='jaffle' then 1 else 0 end) j, max(case when p.type='beverage' then 1 else 0 end) b from orders o join items i on i.order_id=o.id join products p on p.sku=i.sku where o.ordered_at>=… → 6 rows
- **j-q05-top-products-2025** (—) · motley · claude-opus-5-5 · trial 1 · submitted
  - single query: no single query returns the answer (last, query #2: result has 8 rows, truth has 5)
  - #1 `search` {"question":"units sold by product and product type"} → ok
  - #2 `query` items dimensions=["products.name","products.type","sku"] measures=["units_sold"] filters=["orders.ordered_at >= '2025-01-01'","orders.ordered_at < '2026-01-01'"] order=[{"column":"units_sold","direction":"desc"}] → 8 rows, truncated warning
  - #3 `report_feedback` {"user_question":"Top 5 products by units sold in 2025 with type","category":"unclear_docs","body":"Memory jaffle-product-margin claims 'chai and mighty is the #1 product by units in 2025', but items.units_sold by products.name filtered to… → ok
- **j-q05-top-products-2025** (—) · motley+python · claude-opus-5-5 · trial 1 · submitted
  - single query: no single query returns the answer (last, query #2: result has 8 rows, truth has 5)
  - #1 `search` {"question":"units sold by product in 2025, product type"} → ok
  - #2 `query` items dimensions=["products.name","products.type"] measures=["units_sold"] filters=["orders.ordered_at >= '2025-01-01'","orders.ordered_at < '2026-01-01'"] order=[{"column":"units_sold","direction":"desc"}] → 8 rows, truncated warning
  - #3 `report_feedback` {"user_question":"Top 5 products by units sold in 2025 with type","category":"unclear_docs","body":"Memory jaffle-product-margin claims 'chai and mighty is the #1 product by units in 2025', but items.units_sold by products.name for 2025 sh… → ok
- **j-q05-top-products-2025** (—) · slayer · claude-opus-5-5 · trial 1 · submitted
  - single query: no single query returns the answer (last, query #2: result has 8 rows, truth has 5)
  - #1 `search` {"question":"product units sold quantity type"} → ok
  - #2 `query` items dimensions=["products.name","products.type"] measures=["units_sold"] filters=["orders.ordered_at in '2025'"] order=[{"column":"units_sold","direction":"desc"}] → 8 rows
- **j-q05-top-products-2025** (—) · slayer+python · claude-opus-5-5 · trial 1 · submitted
  - single query: no single query returns the answer (last, query #2: result has 8 rows, truth has 5)
  - #1 `search` {"question":"units sold by product in 2025, product type"} → ok
  - #2 `query` items dimensions=[{"name":"name","model":"products"},{"name":"type","model":"products"}] measures=["units_sold"] filters=["orders.ordered_at in '2025'"] order=[{"column":"units_sold","direction":"desc"}] → 8 rows
- **j-q05-top-products-2025** (—) · sql+python · claude-opus-5-5 · trial 1 · submitted
  - single query: no single query returns the answer (last, query #3: result has 0 rows, truth has 5)
  - flags: Raw SQL, Several queries
  - #1 `sql` select p.name, p.type, count(*) units from items i join orders o on i.order_id=o.id join products p on p.sku=i.sku where year(o.ordered_at)=2025 group by all order by units desc limit 7 → 7 rows
  - #2 `sql` select table_name, column_name, data_type from information_schema.columns where table_name in ('items','products','orders') → 15 rows
  - #3 `sql` select sku, count(*) from products group by 1 having count(*)>1 → 0 rows
- **j-q09-store-growth-2024-2025** (—) · motley · claude-opus-5-5 · trial 1 · submitted
  - single query: no single query returns the answer (last, query #2: result has 10 rows, truth has 4)
  - #1 `search` {"question":"store revenue by year"} → ok
  - #2 `query` orders dimensions=["stores.name"] time_dimensions=[{"dimension":"ordered_at","granularity":"year","date_range":["2024-01-01","2025-12-31"]}] measures=["net_sales"] → 10 rows
  - #3 `inspect` {"entity_type":"measure","reference":"orders.net_sales"} → ok
- **j-q09-store-growth-2024-2025** (—) · motley+python · claude-opus-5-5 · trial 1 · submitted
  - single query: no single query returns the answer (last, query #2: result has 10 rows, truth has 4)
  - flags: Python
  - #1 `search` {"question":"store revenue by year"} → ok
  - #2 `query` orders dimensions=["stores.name"] time_dimensions=[{"dimension":"ordered_at","granularity":"year","date_range":["2024-01-01","2025-12-31"]}] measures=["net_sales"] → 10 rows
- **j-q09-store-growth-2024-2025** (—) · sql+python · claude-opus-5-5 · trial 1 · submitted
  - single query: no single query returns the answer (last, query #1: result has 6 rows, truth has 4)
  - flags: Python, Raw SQL
  - #1 `sql` select s.name, min(s.opened_at) opened, sum(case when year(o.ordered_at)=2024 then subtotal end)/100.0 r2024, sum(case when year(o.ordered_at)=2025 then subtotal end)/100.0 r2025, (select max(ordered_at) from orders) mx from orders o left … → 6 rows
- **j-q10-new-customers-by-year** (—) · motley · claude-opus-5-5 · trial 1 · submitted
  - single query: no single query returns the answer (last, query #3: result has 1 rows, truth has 5)
  - flags: Several queries
  - #1 `search` {"question":"new customers acquired per year"} → ok
  - #2 `query` orders dimensions=["customer"] measures=[{"name":"first_order_at","formula":"ordered_at:min"}] ; first_orders dimensions=[{"expression":"year(first_order_at)","name":"year"}] measures=["count(*)"] order=[{"column":"year","direction":"asc"}] → 5 rows
  - #3 `query` orders measures=["count(*)"] filters=["customer is null"] → 1 rows
- **j-q10-new-customers-by-year** (—) · motley+python · claude-opus-5-5 · trial 1 · submitted
  - single query: no single query returns the answer (last, query #3: result has 1 rows, truth has 5)
  - flags: Several queries
  - #1 `search` {"question":"new customers acquired per year"} → ok
  - #2 `query` orders dimensions=["customer"] measures=[{"name":"first_order_at","formula":"ordered_at:min"}] ; first_orders time_dimensions=[{"dimension":"first_order_at","granularity":"year"}] measures=["*:count"] → 5 rows
  - #3 `query` orders measures=["*:count"] filters=["customer is null"] → 1 rows
- **j-q10-new-customers-by-year** (—) · slayer · claude-opus-5-5 · trial 1 · submitted
  - single query: no single query returns the answer (last, query #4: no result column has the values of 'year')
  - #1 `search` {"question":"new customers acquired per year"} → ok
  - #2 `inspect` {"reference":"memory:jaffle-new-customers","entity_type":"memory","compact":false} → ok
  - #3 `inspect` {"reference":"demo_database.customers","entity_type":"model","compact":false} → ok
  - #4 `query` orders dimensions=["customer"] measures=[{"formula":"min(ordered_at)","name":"first_order_at"}] ; first_orders time_dimensions=[{"dimension":"first_order_at","granularity":"year"}] measures=[{"formula":"count(*)","name":"new_customers"}] o… → 5 rows
- **j-q10-new-customers-by-year** (—) · slayer+python · claude-opus-5-5 · trial 1 · submitted
  - single query: no single query returns the answer (last, query #4: truth row [2022.0, 177.0] has no match in the result)
  - #1 `search` {"question":"new customers acquired per year"} → ok
  - #2 `inspect` {"reference":"memory:jaffle-new-customers","entity_type":"memory","compact":false} → ok
  - #3 `inspect` {"reference":"demo_database.customers","entity_type":"model","compact":false} → ok
  - #4 `query` orders dimensions=["customer"] measures=[{"name":"first_order_at","formula":"min(ordered_at)"}] ; first_orders dimensions=[{"expression":"year(first_order_at)","name":"year"}] measures=[{"formula":"count(*)","name":"new_customers"}] order=… → 5 rows
- **j-q11-ytd-growth-same-store** (—) · motley · claude-opus-5-5 · trial 1 · submitted
  - single query: no single query returns the answer (last, query #5: result has 4 rows, truth has 1)
  - flags: Several queries
  - #1 `search` {"question":"revenue year to date same-store comparable stores"} → ok
  - #2 `query` orders measures=["ordered_at:max","ordered_at:min"] → 1 rows
  - #3 `query` orders dimensions=["stores.name","stores.opened_at"] measures=["net_sales","ordered_at:min"] filters=["ordered_at >= '2025-01-01'","ordered_at < '2026-10-30'"] → 6 rows
  - #4 `inspect` {"entity_type":"measure","reference":"orders.net_sales","show_sql":true} → ok
  - #5 `query` orders dimensions=[{"expression":"stores.opened_at < '2025-01-01'","name":"comparable"}] time_dimensions=[{"dimension":"ordered_at","granularity":"year"}] measures=["net_sales","subtotal:sum"] filters=["(ordered_at >= '2025-01-01' and orde… → 4 rows
- **j-q11-ytd-growth-same-store** (—) · motley+python · claude-opus-5-5 · trial 1 · submitted
  - single query: no single query returns the answer (last, query #5: result has 5 rows, truth has 1)
  - flags: Python, Several queries
  - #1 `search` {"question":"revenue same-store comparable stores year to date"} → ok
  - #2 `query` orders measures=["ordered_at:max","ordered_at:min"] → 1 rows
  - #3 `query` stores dimensions=["name","opened_at"] → 6 rows
  - #4 `query` orders dimensions=[{"expression":"iif(stores.opened_at < '2025-01-01', 'comp', 'noncomp')","name":"comp"}] time_dimensions=["year(ordered_at)"] measures=["net_sales"] filters=["(ordered_at >= '2025-01-01' and ordered_at < '2025-10-30') or … → 4 rows
  - #5 `query` orders dimensions=["stores.name"] measures=["net_sales"] filters=["ordered_at >= '2025-01-01' and ordered_at < '2025-10-30'"] → 5 rows
- **j-q11-ytd-growth-same-store** (—) · slayer+python · claude-opus-5-5 · trial 1 · submitted
  - correct: no result column has the values of 'ytd_2025', 'ytd_2026', 'headline_growth', 'ss_2025', 'ss_2026'
  - single query: no single query returns the answer (last, query #6: no result column has the values of 'ytd_2025', 'ytd_2026', 'headline_growth', 'ss_2025', 'ss_2026', 'same_store_growth')
  - flags: Several queries
  - #1 `search` {"question":"revenue same-store comparable stores year to date"} → ok
  - #2 `inspect` {"reference":["jaffle-data-coverage","jaffle-same-store-growth"],"entity_type":"memory","compact":false} → ok
  - #3 `inspect` {"reference":"demo_database.orders","entity_type":"model","compact":false} → ok
  - #4 `inspect` {"reference":["memory:jaffle-same-store-growth","memory:jaffle-data-coverage"],"entity_type":"memory","compact":false} → ok
  - #5 `query` stores dimensions=["name","opened_at"] measures=["max(orders.ordered_at)"] → 6 rows
  - #6 `query` orders measures=[{"formula":"sum(iif(ordered_at < '2025-10-30', order_total, 0)) / 100.0","name":"ly"},{"formula":"sum(iif(ordered_at >= '2026-01-01', order_total, 0)) / 100.0","name":"ty"},{"formula":"sum(iif(ordered_at >= '2026-01-01', o… → 1 rows
- **j-q11-ytd-growth-same-store** (—) · sql+python · claude-opus-5-5 · trial 1 · submitted
  - single query: no single query returns the answer (last, query #3: no result column has the values of 'ytd_2025', 'ytd_2026', 'headline_growth', 'ss_2025', 'ss_2026', 'same_store_growth')
  - flags: Python, Raw SQL, Several queries
  - #1 `sql` select max(ordered_at), min(ordered_at) from orders → 1 rows
  - #2 `sql` select * from stores → 6 rows
  - #3 `sql` select sum(case when ordered_at>='2025-01-01' and ordered_at<'2025-10-30' then subtotal end)/100.0 ly, sum(case when ordered_at>='2026-01-01' and ordered_at<'2026-10-30' then subtotal end)/100.0 ty, sum(case when ordered_at>='2025-01-01' a… → 1 rows
- **j-q12-best-unit-margin** (—) · motley · claude-opus-5-5 · trial 1 · submitted
  - correct: result has 1 rows, truth has 10
  - single query: no single query returns the answer (last, query #2: no result column has the values of 'product', 'unit_margin', 'margin_pct')
  - #1 `search` {"question":"product supply cost price gross margin"} → ok
  - #2 `query` supplies dimensions=["sku","products.name","products.price"] measures=["total_supply_cost"] → 10 rows
- **j-q12-best-unit-margin** (—) · motley+python · claude-opus-5-5 · trial 1 · submitted
  - correct: result has 1 rows, truth has 10
  - single query: no single query returns the answer (last, query #5: no result column has the values of 'product', 'unit_margin', 'margin_pct')
  - flags: Query errors, Several queries
  - #1 `inspect` {"entity_type":"model"} → ok
  - #2 `inspect` {"entity_type":"model","reference":"supplies","num_rows":10} → ok
  - #3 `inspect` {"entity_type":"model","reference":"products","num_rows":10} → ok
  - #4 `query` products dimensions=["sku","name"] measures=[{"formula":"avg(price)","name":"price"},{"formula":"sum(supplies.cost)","name":"cost"},{"formula":"count(supplies.id)","name":"n"},{"formula":"count_distinct(supplies.id)","name":"nd"}] → error MeasureNameCollidesWithColumnError
  - #5 `query` products dimensions=["sku","name"] measures=[{"formula":"avg(price)","name":"p"},{"formula":"sum(supplies.cost)","name":"c"},{"formula":"count(supplies.id)","name":"n"},{"formula":"count_distinct(supplies.id)","name":"nd"}] → 10 rows
- **j-q12-best-unit-margin** (—) · slayer · claude-opus-5-5 · trial 1 · submitted
  - correct: result has 1 rows, truth has 10
  - flags: Query errors, Several queries
  - #1 `search` {"question":"product supply cost gross margin price"} → ok
  - #2 `inspect` {"reference":"demo_database.supplies","entity_type":"model","compact":false,"num_rows":5} → ok
  - #3 `inspect` {"reference":"demo_database.products","entity_type":"model","compact":false} → ok
  - #4 `query` products dimensions=["name"] measures=[{"formula":"price:dollars - supplies.cost:dollars","name":"margin"},{"formula":"(price:dollars - supplies.cost:dollars) / price:dollars","name":"margin_pct"},{"formula":"price:dollars","name":"price"}… → error MeasureNameCollidesWithColumnError
  - #5 `query` products dimensions=["name"] measures=[{"formula":"price:dollars - supplies.cost:dollars","name":"margin"},{"formula":"(price:dollars - supplies.cost:dollars) / price:dollars","name":"margin_pct"},{"formula":"price:dollars","name":"price_d… → 10 rows
- **j-q12-best-unit-margin** (—) · slayer+python · claude-opus-5-5 · trial 1 · submitted
  - correct: result has 1 rows, truth has 10
  - #1 `search` {"question":"product supply cost price gross margin"} → ok
  - #2 `inspect` {"reference":["demo_database.supplies","demo_database.products"],"entity_type":"model","compact":false} → ok
  - #3 `query` products dimensions=["name"] measures=[{"formula":"(avg(price) - sum(supplies.cost))/100.0","name":"margin_per_unit"},{"formula":"(avg(price) - sum(supplies.cost))/avg(price)","name":"margin_pct"},{"formula":"avg(price)","name":"price_cent… → 10 rows
- **q10-bronze-or-ok** (Q10) · motley+python · claude-opus-5-5 · trial 1 · submitted
  - single query: no single query returns the answer (last, query #6: result has 3 rows, truth has 1)
  - flags: Several queries
  - #1 `inspect` {"entity_type":"model"} → ok
  - #2 `inspect` {"entity_type":"model","reference":"customers","num_rows":3} → ok
  - #3 `inspect` {"entity_type":"model","reference":"orders","num_rows":3} → ok
  - #4 `query` customers dimensions=[{"expression":"iif(tier == 'bronze' or sum(orders.amount * 0 + iif(orders.status == 'ok',1,0), partition_by=id) > 0, 'y','n')","name":"flag"}] measures=["count(*)","count_distinct(id)"] → 2 rows
  - #5 `query` customers dimensions=["id","tier"] measures=[{"formula":"count(orders.id)","name":"n"}] filters=["orders.status == 'ok'"] → 201 rows
  - #6 `query` customers dimensions=["id","tier","name"] measures=["count(*)"] filters=["id > 199 or id is null"] → 3 rows
- **q13-top-cities-count** (Q13) · motley · claude-opus-5-5 · trial 1 · submitted
  - single query: no single query returns the answer (last, query #5: result has 12 rows, truth has 3)
  - #1 `inspect` {"entity_type":"model"} → ok
  - #2 `inspect` {"entity_type":"model","reference":"orders","num_rows":3} → ok
  - #3 `inspect` {"entity_type":"model","reference":"customers","num_rows":3} → ok
  - #4 `inspect` {"entity_type":"model","reference":"cities","num_rows":3} → ok
  - #5 `query` orders dimensions=["customers.region_id","customers.city"] measures=["sum(amount)","count(*)"] order=[{"column":"sum(amount)","direction":"desc"}] → 12 rows
- **q13-top-cities-count** (Q13) · motley+python · claude-opus-5-5 · trial 1 · submitted
  - single query: no single query returns the answer (last, query #5: result has 12 rows, truth has 3)
  - #1 `inspect` {"entity_type":"model"} → ok
  - #2 `inspect` {"entity_type":"model","reference":"cities","num_rows":3} → ok
  - #3 `inspect` {"entity_type":"model","reference":"orders","num_rows":3} → ok
  - #4 `inspect` {"entity_type":"model","reference":"customers","num_rows":3} → ok
  - #5 `query` orders dimensions=["customers.city","customers.region_id"] measures=["sum(amount)","count(*)"] order=[{"column":"sum(amount)","direction":"desc"}] → 12 rows
- **q13-top-cities-count** (Q13) · slayer · claude-opus-5-5 · trial 1 · submitted
  - single query: no single query returns the answer (last, query #4: result has 5 rows, truth has 3)
  - #1 `search` {"question":"city revenue orders amount region"} → ok
  - #2 `models_summary` {"datasource_name":"bench","compact":false} → ok
  - #3 `inspect` {"reference":"bench.customers","entity_type":"model","compact":false} → ok
  - #4 `query` orders dimensions=["customers.region_id","customers.city"] measures=[{"formula":"count(*)","name":"order_count"}] order=[{"column":"sum(amount)","direction":"desc"}] → 5 rows
- **q13-top-cities-count** (Q13) · slayer+python · claude-opus-5-5 · trial 1 · submitted
  - single query: no single query returns the answer (last, query #4: result has 6 rows, truth has 3)
  - #1 `search` {"question":"city revenue order amount"} → ok
  - #2 `models_summary` {"datasource_name":"bench","compact":false} → ok
  - #3 `inspect` {"reference":"bench.customers","entity_type":"model","sections":["joins","samples"]} → ok
  - #4 `query` orders dimensions=["customers.region_id","customers.city"] measures=["count(*)","sum(amount)"] order=[{"column":"sum(amount)","direction":"desc"}] → 6 rows
- **q13-top-cities-count** (Q13) · sql+python · claude-opus-5-5 · trial 1 · submitted
  - single query: no single query returns the answer (last, query #3: result has 1 rows, truth has 3)
  - flags: Raw SQL, Several queries
  - #1 `sql` select table_name, column_name, data_type from information_schema.columns order by table_name → 53 rows
  - #2 `sql` select c.city, c.region_id, count(o.id) n, sum(o.amount) rev, count(*) rows_ from orders o left join customers c on o.customer_id=c.id group by 1,2 order by rev desc nulls last limit 6 → 6 rows
  - #3 `sql` select (select count(*)-count(distinct id) from customers) dup, (select count(*) from orders o left join customers c on o.customer_id=c.id where c.city is null) nullcity, (select sum(amount) from orders o left join customers c on o.custome… → 1 rows
- **q14-top-customer-per-region** (Q14) · motley · claude-opus-5-5 · trial 1 · submitted
  - single query: no single query returns the answer (last, query #5: result has 8 rows, truth has 4)
  - flags: Several queries
  - #1 `inspect` {"entity_type":"model"} → ok
  - #2 `inspect` {"entity_type":"model","reference":"customers","num_rows":3} → ok
  - #3 `inspect` {"entity_type":"model","reference":"orders","num_rows":3} → ok
  - #4 `query` regions dimensions=["id","name"] measures=["count(*)"] → 5 rows
  - #5 `query` customers dimensions=["regions.name","id"] measures=[{"formula":"sum(orders.amount)","name":"revenue"}] filters=["regions.name is not null","rank(sum(orders.amount), partition_by=regions.name, direction='desc') <= 2"] order=[{"column":"reg… → 8 rows
- **q14-top-customer-per-region** (Q14) · sql+python · claude-opus-5-5 · trial 1 · submitted
  - single query: no single query returns the answer (last, query #2: result has 8 rows, truth has 4)
  - flags: Raw SQL, Several queries
  - #1 `sql` select table_name, column_name, data_type from information_schema.columns order by table_name → 53 rows
  - #2 `sql` with r as (select c.region_id, rg.name, c.id, sum(o.amount) rev from customers c join orders o on o.customer_id=c.id left join regions rg on rg.id=c.region_id where c.region_id is not null group by all), k as (select *, rank() over (partit… → 8 rows
- **q15-revenue-bands** (Q15) · motley · claude-opus-5-5 · trial 1 · submitted
  - single query: no single query returns the answer (last, query #5: result has 1 rows, truth has 4)
  - flags: Several queries
  - #1 `inspect` {"entity_type":"model"} → ok
  - #2 `inspect` {"entity_type":"model","reference":"orders","num_rows":3} → ok
  - #3 `query` orders dimensions=["customer_id"] measures=[{"formula":"sum(amount)","name":"rev"}] ; per_cust dimensions=[{"expression":"iif(rev < 1000, 0, iif(rev < 2000, 1000, iif(rev < 3000, 2000, 3000)))","name":"band"}] measures=[{"formula":"count(*… → 4 rows
  - #4 `query` orders measures=["count(*)","count_distinct(customer_id)","count(amount)"] → 1 rows
  - #5 `query` orders measures=["count(*)","sum(amount)"] filters=["customer_id is null"] → 1 rows
- **q18-day-of-monthly** (Q18) · sql+python · claude-opus-5-5 · trial 1 · auto_fail
  - correct: needs the saved SLayer definitions monthly_rev
  - single query: needs the saved SLayer definitions monthly_rev
  - no query calls
- **q20-last-three-months** (Q20) · motley · claude-opus-5-5 · trial 1 · submitted · xfail DEV-2058
  - correct: result has 0 rows, truth has 3
  - single query: no single query returns the answer (last, query #3: result has 0 rows, truth has 3)
  - #1 `search` {"question":"order amount revenue"} → ok
  - #2 `inspect` {"entity_type":"model","reference":"orders","num_rows":3} → ok
  - #3 `query` orders time_dimensions=[{"dimension":"order_date","granularity":"month","date_range":["2026-08-01","2026-10-31"]}] measures=["sum(amount)","count(*)"] → 0 rows
- **q20-last-three-months** (Q20) · motley+python · claude-opus-5-5 · trial 1 · submitted · xfail DEV-2058
  - correct: result has 0 rows, truth has 3
  - flags: Several queries
  - #1 `search` {"question":"order amount revenue"} → ok
  - #2 `inspect` {"entity_type":"model","reference":"orders"} → ok
  - #3 `query` orders time_dimensions=[{"dimension":"order_date","granularity":"month","date_range":["2026-06-01","2026-11-30"]}] measures=["sum(amount)","count(*)","order_date:max"] → 0 rows
  - #4 `query` orders measures=["order_date:min","order_date:max","count(*)"] → 1 rows
  - #5 `query` orders time_dimensions=[{"dimension":"order_date","granularity":"month","date_range":["2025-10-01","2025-12-31"]}] measures=["sum(amount)"] → 3 rows
- **q20-last-three-months** (Q20) · slayer · claude-opus-5-5 · trial 1 · submitted · xfail DEV-2058
  - correct: result has 0 rows, truth has 3
  - single query: no single query returns the answer (last, query #3: result has 0 rows, truth has 3)
  - #1 `search` {"question":"orders amount revenue"} → ok
  - #2 `inspect` {"reference":"bench.orders","entity_type":"model","compact":false} → ok
  - #3 `query` orders time_dimensions=[{"dimension":"order_date","granularity":"month","date_range":["2026-08-01","2026-10-31"]}] measures=[{"formula":"sum(amount)","name":"revenue"}] → 0 rows
  - #4 `inspect` {"reference":"bench.monthly_rev","entity_type":"model","compact":false} → ok
- **q20-last-three-months** (Q20) · slayer+python · claude-opus-5-5 · trial 1 · submitted · xfail DEV-2058
  - correct: result has 0 rows, truth has 3
  - single query: no single query returns the answer (last, query #3: result has 0 rows, truth has 3)
  - #1 `search` {"question":"order amount revenue"} → ok
  - #2 `inspect` {"reference":"bench.orders","entity_type":"model","compact":false} → ok
  - #3 `query` orders time_dimensions=[{"dimension":{"name":"order_date"},"granularity":"month","date_range":["2026-08-01","2026-10-31"]}] measures=[{"formula":"sum(amount)","name":"revenue"}] → 0 rows
  - #4 `inspect` {"reference":"bench.monthly_rev","entity_type":"model","compact":false} → ok
- **q20-last-three-months** (Q20) · sql+python · claude-opus-5-5 · trial 1 · submitted · xfail DEV-2058
  - correct: truth row ['2025-10-01', 9750.920000000007] has no match in the result
  - single query: no single query returns the answer (last, query #3: result has 1 rows, truth has 3)
  - flags: Raw SQL, Several queries
  - #1 `sql` select table_name, column_name, data_type from information_schema.columns order by table_name → 53 rows
  - #2 `sql` select date_trunc('month',order_date) m, count(*), sum(amount), count(amount) from orders group by 1 order by 1 desc limit 8 → 8 rows
  - #3 `sql` select min(order_date), max(order_date), count(*) filter (where order_date is null), list(distinct status) from orders → 1 rows
- **q23-monthly-by-region** (Q23) · sql+python · claude-opus-5-5 · trial 1 · auto_fail
  - correct: needs the saved SLayer definitions monthly_rev
  - single query: needs the saved SLayer definitions monthly_rev
  - no query calls
- **q24-top-two-per-region** (Q24) · sql+python · claude-opus-5-5 · trial 1 · submitted
  - single query: no single query returns the answer (last, query #2: result has 12 rows, truth has 8)
  - flags: Raw SQL, Several queries
  - #1 `sql` select table_name, column_name, data_type from information_schema.columns order by table_name, ordinal_position → 53 rows
  - #2 `sql` with c as (select c.id, c.region_id, r.name region, sum(o.amount) rev from customers c join orders o on o.customer_id=c.id left join regions r on r.id=c.region_id where c.region_id is not null group by all), t as (select *, sum(rev) over (… → 12 rows
- **q27-customers-per-tag** (Q27) · sql+python · claude-opus-5-5 · trial 1 · submitted
  - correct: result has 9 rows, truth has 8
  - single query: no single query returns the answer (last, query #3: result has 1 rows, truth has 8)
  - flags: Raw SQL, Several queries
  - #1 `sql` select table_name, column_name, data_type from information_schema.columns where table_name ilike '%tag%' or table_name ilike '%customer%' → 8 rows
  - #2 `sql` select tag, count(distinct id) n, count(*) c from (select id, unnest(tags) tag from customers) group by tag order by n desc → 9 rows
  - #3 `sql` select count(*), count(distinct id), count(tags), sum(case when len(tags)=0 then 1 else 0 end) from customers → 1 rows
- **q27-region-tag-set** (Q27) · motley+python · claude-opus-5-5 · trial 1 · submitted
  - single query: no single query returns the answer (last, query #4: result has 26 rows, truth has 5)
  - #1 `inspect` {"entity_type":"model"} → ok
  - #2 `inspect` {"entity_type":"model","reference":"customers","num_rows":3} → ok
  - #3 `inspect` {"entity_type":"model","reference":"regions","num_rows":10} → ok
  - #4 `query` regions dimensions=["name","customers.tags.value"] measures=["count(*)"] → 26 rows
- **q27-tag-count-groups** (Q27) · motley · claude-opus-5-5 · trial 1 · submitted · xfail DEV-2209
  - single query: no single query returns the answer (last, query #3: no result column has the values of 'tag_count')
  - #1 `search` {"question":"customer tags"} → ok
  - #2 `inspect` {"entity_type":"model","reference":"customers","num_rows":5,"show_sql":true} → ok
  - #3 `query` customers dimensions=["id",{"expression":"tags is null","name":"tags_null"}] measures=[{"formula":"count_distinct(tags.value)","name":"n_tags"}] ; per_cust dimensions=["tags_null","n_tags"] measures=[{"formula":"count(*)","name":"customers… → 6 rows
- **q27-tag-count-groups** (Q27) · motley+python · claude-opus-5-5 · trial 1 · submitted · xfail DEV-2209
  - single query: no single query returns the answer (last, query #3: no result column has the values of 'tag_count')
  - #1 `search` {"question":"customer tags"} → ok
  - #2 `inspect` {"entity_type":"model","reference":"customers","num_rows":5,"show_sql":true} → ok
  - #3 `query` customers dimensions=["id",{"expression":"tags is null","name":"tags_null"}] measures=[{"formula":"count_distinct(tags.value)","name":"n_tags"}] ; per_cust dimensions=["tags_null","n_tags"] measures=[{"formula":"count(*)","name":"customers… → 6 rows
- **q3-avg-city-revenue** (Q3) · motley · claude-opus-5-5 · trial 1 · submitted
  - correct: truth row [None, 677.83] has no match in the result
  - single query: no single query returns the answer (last, query #4: truth row [None, 677.83] has no match in the result)
  - #1 `inspect` {"entity_type":"model"} → ok
  - #2 `inspect` {"entity_type":"model","reference":"customers"} → ok
  - #3 `inspect` {"entity_type":"model","reference":"cities"} → ok
  - #4 `query` orders dimensions=["customers.regions.name"] measures=[{"formula":"avg(sum(amount, partition_by=[customers.regions.name, customers.city]), partition_by=[customers.regions.name])","name":"avg_city_revenue"}] → 5 rows
- **q3-avg-city-revenue** (Q3) · motley+python · claude-opus-5-5 · trial 1 · submitted
  - correct: truth row [None, 677.83] has no match in the result
  - single query: no single query returns the answer (last, query #6: truth row [None, 677.83] has no match in the result)
  - flags: Several queries
  - #1 `inspect` {"entity_type":"model"} → ok
  - #2 `inspect` {"entity_type":"model","reference":"customers","num_rows":3} → ok
  - #3 `inspect` {"entity_type":"model","reference":"cities","num_rows":3} → ok
  - #4 `query` orders dimensions=["customers.regions.name","customers.region_id","customers.city"] measures=["sum(amount)","count(*)"] → 12 rows
  - #5 `query` orders dimensions=["customer_id","customers.id","customers.city"] measures=["count(*)"] filters=["customers.region_id is null"] → 2 rows
  - #6 `query` orders dimensions=["customers.regions.name"] measures=[{"formula":"avg(sum(amount, partition_by=[customers.regions.name, customers.city]), partition_by=[customers.regions.name])","name":"avg_city_revenue"}] → 5 rows
- **q3-avg-city-revenue** (Q3) · slayer · claude-opus-5-5 · trial 1 · submitted
  - correct: truth row [None, 677.83] has no match in the result
  - single query: no single query returns the answer (last, query #3: truth row [None, 677.83] has no match in the result)
  - #1 `search` {"question":"orders amount customer city region"} → ok
  - #2 `inspect` {"reference":["bench.orders","bench.customers","bench.cities","bench.orders_flat"],"entity_type":"model","compact":false} → ok
  - #3 `query` orders dimensions=["customers.regions.name"] measures=[{"formula":"avg(sum(amount, partition_by=[customers.regions.name, customers.city]), partition_by=[customers.regions.name])","name":"avg_city_revenue"},{"formula":"count_distinct(custom… → 5 rows
- **q3-avg-city-revenue** (Q3) · slayer+python · claude-opus-5-5 · trial 1 · submitted
  - correct: truth row [None, 677.83] has no match in the result
  - single query: no single query returns the answer (last, query #3: truth row [None, 677.83] has no match in the result)
  - #1 `search` {"question":"order amount city region customer"} → ok
  - #2 `inspect` {"reference":["bench.orders","bench.customers","bench.cities","bench.orders_flat"],"entity_type":"model","compact":false} → ok
  - #3 `query` orders dimensions=["customers.regions.name"] measures=[{"formula":"avg(sum(amount, partition_by=[customers.regions.name, customers.city]), partition_by=[customers.regions.name])","name":"avg_city_revenue"},{"formula":"count_distinct(custom… → 5 rows
- **q3-avg-city-revenue** (Q3) · sql+python · claude-opus-5-5 · trial 1 · submitted
  - correct: truth row [None, 677.83] has no match in the result
  - single query: no single query returns the answer (last, query #3: truth row [None, 677.83] has no match in the result)
  - flags: Raw SQL, Several queries
  - #1 `sql` select table_name, column_name, data_type from information_schema.columns order by table_name, ordinal_position → 53 rows
  - #2 `sql` select c.region_id, r.name, c.city, count(*) n, sum(o.amount), count(o.amount) from orders o left join customers c on o.customer_id=c.id left join regions r on r.id=c.region_id group by all order by 1,3 → 12 rows
  - #3 `sql` select region, avg(rev) avg_city_revenue, count(*) cities from (select r.name region, c.city, sum(o.amount) rev from orders o left join customers c on o.customer_id=c.id left join regions r on r.id=c.region_id group by all) group by 1 orde… → 5 rows
- **q4-prior-year** (Q4) · sql+python · claude-opus-5-5 · trial 1 · submitted
  - single query: no single query returns the answer (last, query #2: result has 14 rows, truth has 3)
  - flags: Raw SQL, Several queries
  - #1 `sql` select table_name, column_name, data_type from information_schema.columns order by table_name → 53 rows
  - #2 `sql` select date_trunc('month',order_date) m, sum(amount), count(*), count(amount) from orders where order_date between '2024-01-01' and '2025-03-31' group by 1 order by 1 → 14 rows
- **q7-cumulative-change** (Q7) · motley+python · claude-opus-5-5 · trial 1 · submitted
  - single query: no single query returns the answer (last, query #3: result has 13 rows, truth has 12)
  - flags: Python
  - #1 `inspect` {"entity_type":"model"} → ok
  - #2 `inspect` {"entity_type":"model","reference":"orders","num_rows":3} → ok
  - #3 `query` orders time_dimensions=[{"dimension":{"name":"order_date"},"granularity":"month","date_range":["2024-12-01","2025-12-31"]}] measures=[{"formula":"sum(amount)","name":"rev"}] order=[{"column":"order_date","direction":"asc"}] → 13 rows
- **q9-credit-by-status** (Q9) · motley · claude-opus-5-5 · trial 1 · submitted · xfail DEV-1951
  - correct: message mentions 'counted in both'; the trace lacks a broadcast or associated result
  - single query: no call returned broadcast or associated
  - #1 `inspect` {"entity_type":"model"} → ok
  - #2 `inspect` {"entity_type":"model","reference":"customers"} → ok
  - #3 `inspect` {"entity_type":"model","reference":"orders"} → ok
  - #4 `query` orders dimensions=["status"] measures=["sum(customers.credit)"] → 2 rows
- **q9-credit-by-status** (Q9) · motley+python · claude-opus-5-5 · trial 1 · submitted · xfail DEV-1951
  - correct: message mentions 'overlap'; the trace lacks a broadcast or associated result
  - single query: no call returned broadcast or associated
  - #1 `inspect` {"entity_type":"model"} → ok
  - #2 `inspect` {"entity_type":"model","reference":"customers"} → ok
  - #3 `inspect` {"entity_type":"model","reference":"orders"} → ok
  - #4 `query` orders dimensions=["status"] measures=["sum(customers.credit)"] → 2 rows
- **t-monthly-gaps** (Q4, missing_periods) · motley+python · claude-opus-5-5 · trial 1 · submitted
  - single query: no single query returns the answer (last, query #4: result has 11 rows, truth has 12)
  - flags: Query errors, Several queries
  - #1 `inspect` {"entity_type":"model"} → ok
  - #2 `inspect` {"entity_type":"model","reference":"orders","num_rows":3} → ok
  - #3 `query` time_spine time_dimensions=[{"dimension":"time_spine.timestamp","granularity":"month","date_range":"2024"}] measures=[{"formula":"coalesce(sum(orders.amount),0)","name":"revenue"},{"formula":"cumsum(coalesce(sum(orders.amount),0))","name":… → error
  - #4 `query` orders time_dimensions=[{"dimension":"order_date","granularity":"month","date_range":"2024"}] measures=[{"formula":"sum(amount)","name":"revenue"},{"formula":"cumsum(sum(amount))","name":"running_total"}] → 11 rows
- **t-rolling-gap** (Q11, rows_window_gap) · motley · claude-opus-5-5 · trial 1 · submitted
  - single query: no single query returns the answer (last, query #3: result has 6 rows, truth has 4)
  - #1 `inspect` {"entity_type":"model"} → ok
  - #2 `inspect` {"entity_type":"model","reference":"orders","num_rows":3} → ok
  - #3 `query` orders time_dimensions=[{"dimension":"order_date","granularity":"month","date_range":["2024-06-01","2024-12-31"]}] measures=["sum(amount)",{"formula":"sum(amount, window='3m')","name":"rev_3m"}] → 6 rows
- **t-rolling-gap** (Q11, rows_window_gap) · motley+python · claude-opus-5-5 · trial 1 · submitted
  - single query: no single query returns the answer (last, query #3: result has 6 rows, truth has 4)
  - flags: Python
  - #1 `inspect` {"entity_type":"model"} → ok
  - #2 `inspect` {"entity_type":"model","reference":"orders","num_rows":3} → ok
  - #3 `query` orders time_dimensions=[{"dimension":"time_spine.timestamp","granularity":"month","date_range":["2024-07-01","2024-12-31"]}] measures=["sum(orders.amount)"] → 6 rows
- **t-without-vip** (Q27, null_element) · sql+python · claude-opus-5-5 · trial 1 · submitted
  - single query: no single query returns the answer (last, query #5: result has 1 rows, truth has 4)
  - flags: Raw SQL, Several queries
  - #1 `sql` select table_name, column_name, data_type from information_schema.columns order by table_name → 53 rows
  - #2 `sql` select r.name, c.region_id, count(*) total, count(c.tags) tagged, count(*) filter (where c.tags is not null and not list_contains(c.tags,'vip')) nonvip, count(*) filter (where len(c.tags)=0) empty, count(*) filter (where list_contains(c.ta… → 5 rows
  - #3 `sql` select t, count(*) from (select unnest(tags) t from customers) group by 1 → 9 rows
  - #4 `sql` select id, region_id, tags from customers where len(list_filter(tags, x -> x is null))>0 or region_id is null → 2 rows
  - #5 `sql` select list_contains(['newsletter',null],'vip') → 1 rows
- **t-zero-regions** (Q8, outer_join_filter) · motley · claude-opus-5-5 · trial 1 · submitted
  - single query: no single query returns the answer (last, query #6: no result column has the values of 'region', 'orders')
  - flags: Several queries
  - #1 `inspect` {"entity_type":"model"} → ok
  - #2 `inspect` {"entity_type":"model","reference":"customers","num_rows":3} → ok
  - #3 `inspect` {"entity_type":"model","reference":"orders","num_rows":3} → ok
  - #4 `query` regions dimensions=["id","name"] measures=[{"formula":"count(customers.orders.id)","name":"orders_2025"}] filters=["customers.orders.order_date in '2025'"] → 4 rows
  - #5 `query` regions dimensions=["id","name"] measures=["count(*)"] → 5 rows
  - #6 `query` orders dimensions=["customers.region_id"] measures=["count(*)"] filters=["order_date in '2025'"] → 5 rows
- **t-zero-regions** (Q8, outer_join_filter) · motley+python · claude-opus-5-5 · trial 1 · submitted
  - single query: no single query returns the answer (last, query #5: no result column has the values of 'region', 'orders')
  - flags: Several queries
  - #1 `inspect` {"entity_type":"model"} → ok
  - #2 `inspect` {"entity_type":"model","reference":"customers","num_rows":3} → ok
  - #3 `inspect` {"entity_type":"model","reference":"orders","num_rows":3} → ok
  - #4 `query` regions dimensions=["id","name"] measures=[{"formula":"count(customers.orders.id)","name":"orders_2025"}] filters=["customers.orders.order_date in '2025'"] → 4 rows
  - #5 `query` regions dimensions=["id","name"] measures=["count(*)"] → 5 rows
