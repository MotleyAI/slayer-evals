# Baseline failures, by profile and pitfall

Where Claude Opus 5.5 failed in the [committed baseline](../results/baseline/report.md): every task of every suite
once in each of the three profiles (`slayer`, `slayer+python`, `sql+python`), SLayer at commit `1653a91` (reported as
1.1.0), run on 2026-11-16 from 14:57 UTC. It is a **single-trial snapshot**: one flip is noise, a failure across
profiles is a pattern.

✓ pass · ✗ correct answer, but not one query's own result · **✗c** wrong answer · auto: the task names a saved SLayer
definition, so it fails in `sql+python` without running

## Headline

| Suite | Profile | Trials | Correct | Single query | Passed |
| --- | --- | --- | --- | --- | --- |
| capability | `slayer` | 24 | 23 | 19 | 18 |
| capability | `slayer+python` | 24 | 24 | 15 | 15 |
| capability | `sql+python` | 24 (2 auto) | 19 | 14 | 14 |
| combo | `slayer` | 11 | 11 | 7 | 7 |
| combo | `slayer+python` | 11 | 11 | 5 | 5 |
| combo | `sql+python` | 11 (1 auto) | 10 | 5 | 5 |
| trap | `slayer` | 17 | **17** | 11 | 11 |
| trap | `slayer+python` | 17 | **17** | 8 | 8 |
| trap | `sql+python` | 17 | 16 | 15 | 14 |
| jaffle | `slayer` | 24 | 22 | 10 | 10 |
| jaffle | `slayer+python` | 24 | 21 | 9 | 9 |
| jaffle | `sql+python` | 24 | **23** | 18 | 18 |

The relative-date task `q20-last-three-months` is xfail and not counted. **Correct** is the comparison across
profiles; single query is much easier with raw SQL, where one statement can express nearly any answer.

## Traps, by pitfall

| Task | Pitfall | Row | `slayer` | `slayer+python` | `sql+python` |
| --- | --- | --- | --- | --- | --- |
| t-fan-out-items | fan_out | Q6 | ✓ | ✓ | **✗c** |
| t-fan-out-credit | fan_out | Q8 | ✗ | ✗ | ✓ |
| t-count-after-join | count_after_join | Q10 | ✓ | ✓ | ✓ |
| t-chasm | chasm | Q6 | ✗ | ✗ | ✓ |
| t-bridge-email | bridge | Q10 | ✓ | ✓ | ✓ |
| t-city-size | non_unique_key | Q6 | ✓ | ✓ | ✓ |
| t-zero-regions | outer_join_filter | Q8 | ✗ | ✗ | ✓ |
| t-never-returned | not_in_null | Q10 | ✓ | ✓ | ✓ |
| t-orders-per-customer | count_outer_join | Q8 | ✓ | ✗ | ✓ |
| t-ok-share | filtered_total | Q2 | ✓ | ✗ | ✓ |
| t-orders-per-category | distinct_reagg | Q1 | ✗ | ✗ | ✓ |
| t-monthly-gaps | missing_periods | Q4 | ✓ | ✓ | ✗ |
| t-prev-month | filter_before_window | Q4 | ✓ | ✓ | ✗ |
| t-all-time-running | filter_before_window | Q4, Q15 | ✗ | ✗ | ✓ |
| t-rolling-gap | rows_window_gap | Q11 | ✗ | ✗ | ✓ |
| t-march-events | timestamp_bounds | Q20 | ✓ | ✓ | ✓ |
| t-overall-aov | avg_of_avgs | Q1 | ✓ | ✗ | ✓ |

No profile fell into a trap's naive SQL. The one wrong trap answer is not about the pitfall: on `t-fan-out-items`
`sql+python` added a zero row for the region without customers. Opus 5.5 writing raw SQL knows these pitfalls well; on
this set the semantic layer's advantage is not correctness but that the SLayer agent never had to think about them.

The SLayer agents' trap failures are all ✗: right answers assembled from several queries. On `t-chasm`,
`t-fan-out-credit` and `t-orders-per-category` they queried each fact or grain separately and combined the results,
where one query with cross-model measures or `partition_by=[]` would have done it; on `t-zero-regions` and
`t-rolling-gap` they missed the one-query idioms (a conditional sum rooted at `regions`, a `window='3m'` aggregate)
and pieced the months together; on `t-all-time-running` they queried extra months and dropped them.

## Wrong answers outside the traps

| Task | Row(s) | `slayer` | `slayer+python` | `sql+python` | Why |
| --- | --- | --- | --- | --- | --- |
| q3-avg-city-revenue | Q3 | ✓ | ✗ | **✗c** | `sql+python`'s unknown-region group came to 677.83 against the truth's 596.65 |
| q6-region-credit | Q6 | ✗ | ✗ | **✗c** | an extra, empty row for the region without customers |
| q9-credit-by-status | Q9 | **✗c** | ✓ | **✗c** | `slayer` explained the overlap in words the grader does not accept ("counted under each one"); `sql+python` explained it but still submitted the overlapping totals |
| q20-last-three-months (xfail) | Q20 | **✗c** | **✗c** | **✗c** | "last three months" read from today's date, where the truth assumes January 2026 |

## Not one query (✗), outside the traps

| Task | Row(s) | `slayer` | `slayer+python` | `sql+python` |
| --- | --- | --- | --- | --- |
| q13-top-cities-count | Q13 | ✗ | ✗ | ✗ |
| q24-top-two-per-region | Q24 | ✗ | ✗ | ✗ |
| q7-cumulative-change | Q7 | ✗ | ✗ | ✗ |
| q11-rolling-customers | Q11 | ✗ | ✗ | ✓ |
| q6-region-credit | Q6 | ✗ | ✗ | **✗c** |
| q14-top-customer-per-region | Q14 | ✓ | ✗ | ✗ |
| q2-city-share | Q2 | ✓ | ✗ | ✓ |
| q3-avg-city-revenue | Q3 | ✓ | ✗ | **✗c** |
| q4-running-total | Q4 | ✓ | ✗ | ✓ |
| q4-prior-year | Q4 | ✓ | ✓ | ✗ |
| c-region-credit-rank | Q6, Q14 | ✗ | ✗ | ✗ |
| c-region-month-share | Q2, Q4 | ✗ | ✗ | ✗ |
| c-top-growth-months | Q13, Q4 | ✗ | ✗ | ✗ |
| c-aov-change | Q17, Q4 | ✓ | ✗ | ✗ |
| c-top-two-q1-share | Q24, Q2, Q20 | ✓ | ✗ | ✗ |
| c-size-class-months | Q16, Q2, Q4 | ✓ | ✗ | ✓ |
| c-top-customer-share | Q14, Q2 | ✗ | ✓ | ✓ |

The persistent patterns, as in the previous baseline:

- **Order by what you don't show (Q13).** Every profile projects the sort measure, so no query's result has
  exactly the asked-for columns; SLayer's `order` on an unselected measure is never reached.
- **Transforms over a date range (Q4, Q7, Q11).** The agents query an extra month (or all months) so that a change or
  rolling value has its predecessor, then drop rows, instead of relying on `time_shift` / `change` / `window=`
  reaching outside the range.
- **Combos cost single-query passes in every profile:** 7/11 for `slayer`, 5/11 for `slayer+python`, 5/10 for raw
  SQL. With two or three capabilities in play, agents build the answer in steps.

`slayer+python` passes less often than `slayer` (28 against 36 of 52): with Python available, the agent more often
pulls partial results and finishes the work in pandas.

## Jaffle Shop sub-suite, by business rule

The 24 questions of Yann's nao-vs-Motley experiment. The raw-SQL agent gets a plain-SQL rendering of the nine
`jaffle-*` business rules in its system prompt; the SLayer agents have the same rules as memories and see one only if
they call `search`. "Search" counts the SLayer trials (`slayer` / `slayer+python`) that called it at least once.

| Task | Business rules it needs | `slayer` | `slayer+python` | `sql+python` | Search |
| --- | --- | --- | --- | --- | --- |
| j-q01-stores | — | ✓ | ✓ | ✓ | 1 / 0 |
| j-q02-orders-2025 | — | ✓ | ✓ | ✓ | 1 / 1 |
| j-q03-revenue-by-store-2025 | revenue-definition, money-in-cents | ✓ | ✓ | ✓ | 1 / 1 |
| j-q04-monthly-orders-2026 | data-coverage | ✓ | ✓ | ✓ | 0 / 0 |
| j-q05-top-products-2025 | — | ✗ | ✗ | ✗ | 0 / 0 |
| j-q06-type-share-2025 | sales-by-product, revenue-definition, money-in-cents | ✓ | ✗ | ✓ | 1 / 0 |
| j-q07-aov-by-store | revenue-definition, money-in-cents | ✓ | **✗c** | ✓ | 1 / 0 |
| j-q08-tax-rate-check | — | ✓ | ✓ | ✓ | 1 / 0 |
| j-q09-store-growth-2024-2025 | revenue-definition, money-in-cents | **✗c** | **✗c** | ✗ | 0 / 0 |
| j-q10-new-customers-by-year | new-customers | ✗ | ✗ | ✓ | 1 / 0 |
| j-q11-ytd-growth-same-store | data-coverage, same-store-growth, revenue-definition | ✗ | ✗ | **✗c** | 1 / 1 |
| j-q12-best-unit-margin | product-margin, money-in-cents | **✗c** | **✗c** | ✓ | 0 / 0 |
| j-c01-peak-weekday-hour | money-in-cents | ✗ | ✗ | ✗ | 1 / 1 |
| j-c02-order-value-bands | money-in-cents | ✗ | ✓ | ✓ | 0 / 0 |
| j-c03-basket-mix | — | ✗ | ✗ | ✓ | 0 / 0 |
| j-c04-ltv-by-first-store | money-in-cents | ✓ | ✓ | ✓ | 1 / 1 |
| j-c05-median-orders-per-customer | — | ✓ | ✓ | ✓ | 0 / 0 |
| j-c06-top-decile-share | — | ✗ | ✗ | ✓ | 1 / 0 |
| j-c07-best-month-vs-avg | money-in-cents | ✗ | ✗ | ✓ | 0 / 0 |
| j-c08-growth-streak | — | ✗ | ✗ | ✗ | 1 / 1 |
| j-c09-brooklyn-cogs-margin | product-margin, sales-by-product, money-in-cents | ✗ | ✗ | ✓ | 1 / 1 |
| j-c10-top-supply-component | product-margin, money-in-cents | ✗ | ✗ | ✗ | 0 / 0 |
| j-c11-tweeters-aov | money-in-cents | ✓ | ✗ | ✓ | 0 / 0 |
| j-c12-jaffle-beverage-attach | — | ✗ | ✓ | ✓ | 0 / 0 |

The complex questions (`j-c…`) state "pre-tax" in the question itself, so their revenue basis needs no lookup.

### By rule

- **`jaffle-revenue-definition`** (revenue, sales and AOV are pre-tax) — the rule behind most wrong SLayer answers.
  On `j-q09-store-growth-2024-2025` neither SLayer agent searched, and both reported revenue including tax; on
  `j-q07-aov-by-store` `slayer` searched, found the rule and was right, while `slayer+python` did not search and gave
  the tax-inclusive AOV. Where an agent did search (`j-q03-revenue-by-store-2025`, `j-q11-ytd-growth-same-store`) it
  used pre-tax figures. The raw-SQL agent, with the rule in its prompt, used pre-tax figures throughout.
- **`jaffle-data-coverage`** (partial periods) — `j-q11-ytd-growth-same-store` is the raw-SQL agent's only wrong
  answer: it followed the rule's "treat the current month as incomplete" and compared January to September of each
  year, where the truth, like Yann's reference SQL, compares both years up to 29 October. The SLayer agents searched,
  found the same memory, and compared up to 29 October; both still needed several queries.
- **`jaffle-same-store-growth`** (stores open for both full periods) — every profile picked the four stores open
  before 2025 on `j-q11-ytd-growth-same-store`.
- **`jaffle-new-customers`** (a customer's first-ever order) — every answer to `j-q10-new-customers-by-year` was
  correct; the SLayer agents needed several queries for the two-stage count the memory spells out.
- **`jaffle-product-margin`** (unit COGS from `supplies`) — the margins were right everywhere, but on
  `j-q12-best-unit-margin` both SLayer agents answered only with the top product, although the prompt asks for one row
  per product. `j-c09-brooklyn-cogs-margin` and `j-c10-top-supply-component` were correct in every profile but rarely
  one query: units sold × unit cost needs a join to a computed stage.
- **`jaffle-sales-by-product`** and **`jaffle-money-in-cents`** — no wrong answer: every profile summed item prices
  per item sold and reported dollars.
- **`jaffle-monthly-store-revenue`** and **`jaffle-tweets-limits`** — no question depends on them alone.

### Not one query

Apart from the rules, the Jaffle suite's gap is single query: 10 and 9 SLayer passes against 18 for raw SQL. The
SLayer agents' ✗ answers on `j-c03-basket-mix`, `j-c06-top-decile-share`, `j-c07-best-month-vs-avg`,
`j-c09-brooklyn-cogs-margin`, `j-c12-jaffle-beverage-attach` and `j-q10-new-customers-by-year` all need a multi-stage
query (a per-order, per-customer or per-month stage, then an aggregate over it), which they built as separate queries
instead. Every profile missed single query on `j-q05-top-products-2025` (no query returned exactly the five rows),
`j-c01-peak-weekday-hour` (several top slots fetched, the share computed apart), `j-c08-growth-streak` (the monthly series fetched and the run
counted outside the query) and `j-c10-top-supply-component` (more components fetched than the one asked for). `j-c02-order-value-bands`,
`j-q06-type-share-2025` and `j-c11-tweeters-aov` each failed it in one SLayer profile only.
