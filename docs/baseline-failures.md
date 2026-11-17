# Baseline failures, by profile and pitfall

Where Claude Opus 5.5 failed in the [committed baseline](../results/baseline/report.md): every task once in each of
the five profiles (`slayer`, `slayer+python`, `motley`, `motley+python`, `sql+python`), run on 17 Nov 2026 through
Claude Code 2.1.286 (bundled with `claude-agent-sdk` 0.2.163). The SLayer and SQL profiles ran on SLayer 1.8.5; the
Motley profiles ran against a local Motley backend (`motley 1.30.0`, storyline `main`) whose SLayer is 1.8.2. It is a
**single-trial snapshot**: one flip is noise, a failure across profiles is a pattern.

✓ pass · ✗ correct answer, but not one query's own result · **✗c** wrong answer · auto: the task names a saved SLayer
definition, so it fails in `sql+python` without running · (xfail): an expected failure, left out of the counts

## Headline

| Suite | Profile | Trials | Correct | Single query | Passed |
| --- | --- | --- | --- | --- | --- |
| capability | `slayer` | 32 | 31 | 30 | 30 |
| capability | `slayer+python` | 32 | 31 | 30 | 30 |
| capability | `motley` | 31 | 30 | 27 | 27 |
| capability | `motley+python` | 31 | 30 | 26 | 26 |
| capability | `sql+python` | 33 (2 auto) | 29 | 25 | 25 |
| combo | `slayer` | 15 | 15 | 14 | 14 |
| combo | `slayer+python` | 15 | 15 | 13 | 13 |
| combo | `motley` | 15 | 15 | 12 | 12 |
| combo | `motley+python` | 15 | 15 | 10 | 10 |
| combo | `sql+python` | 15 (1 auto) | 13 | 7 | 7 |
| trap | `slayer` | 21 | 21 | 21 | 21 |
| trap | `slayer+python` | 21 | 21 | 21 | 21 |
| trap | `motley` | 21 | 21 | 19 | 19 |
| trap | `motley+python` | 21 | 21 | 18 | 18 |
| trap | `sql+python` | 21 | 21 | 20 | 20 |
| jaffle | `slayer` | 24 | 23 | 19 | 18 |
| jaffle | `slayer+python` | 24 | 22 | 17 | 16 |
| jaffle | `motley` | 24 | 23 | 14 | 14 |
| jaffle | `motley+python` | 24 | 23 | 12 | 12 |
| jaffle | `sql+python` | 24 | 23 | 17 | 17 |

Expected failures are left out: `q20-last-three-months` in every profile, `q9-credit-by-status` in the Motley
profiles and `q27-tag-count-groups` in the four SLayer-backed profiles. **Correct** is the comparison across profiles;
single query is much easier with raw SQL, where one statement can express nearly any answer.

## Traps, by pitfall

| Task | Pitfall | Row | `slayer` | `slayer+python` | `motley` | `motley+python` | `sql+python` |
| --- | --- | --- | --- | --- | --- | --- | --- |
| t-fan-out-credit | fan_out | Q8 | ✓ | ✓ | ✓ | ✓ | ✓ |
| t-fan-out-items | fan_out | Q6 | ✓ | ✓ | ✓ | ✓ | ✓ |
| t-count-after-join | count_after_join | Q10 | ✓ | ✓ | ✓ | ✓ | ✓ |
| t-chasm | chasm | Q6 | ✓ | ✓ | ✓ | ✓ | ✓ |
| t-bridge-email | bridge | Q10 | ✓ | ✓ | ✓ | ✓ | ✓ |
| t-city-size | non_unique_key | Q6 | ✓ | ✓ | ✓ | ✓ | ✓ |
| t-zero-regions | outer_join_filter | Q8 | ✓ | ✓ | ✗ | ✗ | ✓ |
| t-never-returned | not_in_null | Q10 | ✓ | ✓ | ✓ | ✓ | ✓ |
| t-orders-per-customer | count_outer_join | Q8 | ✓ | ✓ | ✓ | ✓ | ✓ |
| t-ok-share | filtered_total | Q2 | ✓ | ✓ | ✓ | ✓ | ✓ |
| t-orders-per-category | distinct_reagg | Q1 | ✓ | ✓ | ✓ | ✓ | ✓ |
| t-monthly-gaps | missing_periods | Q4 | ✓ | ✓ | ✓ | ✗ | ✓ |
| t-all-time-running | filter_before_window | Q4, Q15 | ✓ | ✓ | ✓ | ✓ | ✓ |
| t-prev-month | filter_before_window | Q4 | ✓ | ✓ | ✓ | ✓ | ✓ |
| t-rolling-gap | rows_window_gap | Q11 | ✓ | ✓ | ✗ | ✗ | ✓ |
| t-march-events | timestamp_bounds | Q20 | ✓ | ✓ | ✓ | ✓ | ✓ |
| t-overall-aov | avg_of_avgs | Q1 | ✓ | ✓ | ✓ | ✓ | ✓ |
| t-vip-per-tier | count_after_unnest | Q27 | ✓ | ✓ | ✓ | ✓ | ✓ |
| t-tagged-credit | unnest_fan_out | Q27 | ✓ | ✓ | ✓ | ✓ | ✓ |
| t-without-vip | null_element | Q27 | ✓ | ✓ | ✓ | ✓ | ✗ |
| t-vip-and-eu-region | same_element_and | Q27 | ✓ | ✓ | ✓ | ✓ | ✓ |

No profile fell into a trap's naive SQL: every trap answer is correct in every profile. The few ✗ are right answers
assembled from several queries: the Motley agents on `t-zero-regions`, `t-rolling-gap` and (`motley+python`)
`t-monthly-gaps`, where one query rooted at `regions` or one `window=` aggregate would have done; and `sql+python` on
`t-without-vip`, whose main query also returned the empty unknown-region group. The SLayer profiles answered every
trap with one query.

## Wrong answers outside the traps

| Task | Row(s) | `slayer` | `slayer+python` | `motley` | `motley+python` | `sql+python` | Why |
| --- | --- | --- | --- | --- | --- | --- | --- |
| c-top-customers-per-tag | Q27, Q14, Q15 | ✓ | ✓ | ✗ | ✗ | **✗c** | `sql+python` ranked customers under a NULL tag as if it were one; the two Motley agents assembled the per-tag ranking from several queries after a rank partitioned by the tag was refused |
| q20-last-three-months | Q20 | **✗c** (xfail) | **✗c** (xfail) | **✗c** (xfail) | **✗c** (xfail) | **✗c** (xfail) | xfail (DEV-2058): "last three months" is read from today's date, where the truth assumes January 2026 |
| q27-customers-per-tag | Q27 | ✓ | ✓ | ✓ | ✓ | **✗c** | `sql+python` counted the NULL element as a tag |
| q3-avg-city-revenue | Q3 | **✗c** | **✗c** | **✗c** | **✗c** | **✗c** | every profile averaged the 6 orders without a customer in as one more "city" of the unknown region |
| q9-credit-by-status | Q9 | ✓ | ✓ | **✗c** (xfail) | **✗c** (xfail) | ✓ | xfail in the Motley profiles (DEV-1951): Motley's `query` drops SLayer's result warnings |

The one wrong answer every profile shares is a NULL-group pitfall: orders without a customer have no city, yet every
agent averaged them in as a city. The other two are the raw-SQL agent treating a list's NULL element as a value, the
pitfall the list-column tasks plant; the SLayer and Motley agents, whose `L.value` drops NULL elements, never did.

## Not one query (✗), outside the traps

| Task | Row(s) | `slayer` | `slayer+python` | `motley` | `motley+python` | `sql+python` |
| --- | --- | --- | --- | --- | --- | --- |
| c-region-credit-rank | Q6, Q14 | ✗ | ✗ | ✗ | ✗ | ✗ |
| c-region-month-share | Q2, Q4 | ✓ | ✓ | ✓ | ✗ | ✗ |
| c-top-customer-share | Q14, Q2 | ✓ | ✓ | ✓ | ✓ | ✗ |
| c-top-growth-months | Q13, Q4 | ✓ | ✗ | ✗ | ✗ | ✗ |
| c-top-two-q1-share | Q24, Q2, Q20 | ✓ | ✓ | ✓ | ✗ | ✗ |
| c-vip-monthly-change | Q27, Q4 | ✓ | ✓ | ✓ | ✓ | ✗ |
| q10-bronze-or-ok | Q10 | ✓ | ✓ | ✓ | ✗ | ✓ |
| q13-top-cities-count | Q13 | ✗ | ✗ | ✗ | ✗ | ✗ |
| q14-top-customer-per-region | Q14 | ✓ | ✓ | ✗ | ✓ | ✗ |
| q15-revenue-bands | Q15 | ✓ | ✓ | ✗ | ✓ | ✓ |
| q24-top-two-per-region | Q24 | ✓ | ✓ | ✓ | ✓ | ✗ |
| q27-region-tag-set | Q27 | ✓ | ✓ | ✓ | ✗ | ✓ |
| q27-tag-count-groups | Q27 | ✓ (xfail) | ✓ (xfail) | ✗ (xfail) | ✗ (xfail) | ✓ |
| q4-prior-year | Q4 | ✓ | ✓ | ✓ | ✓ | ✗ |
| q7-cumulative-change | Q7 | ✓ | ✓ | ✓ | ✗ | ✓ |

- **Order by what you don't show (Q13).** On `q13-top-cities-count` no profile's query returned exactly the three
  cities asked for (the `slayer` agent wrote the intended query but with `limit 5`), and `c-region-credit-rank` was
  assembled from several queries in every profile.
- **Motley needs more queries than SLayer.** Across the capability, combo and trap suites, `motley` and
  `motley+python` miss single query on 9 and 13 tasks against 3 and 4 for `slayer` and `slayer+python`; most are
  answers built from several queries where SLayer's agents wrote one (`c-top-growth-months`, `q14-top-customer-per-region`,
  the per-tag ranking of `c-top-customers-per-tag`).
- **Combos cost the raw-SQL agent most:** 7 single-query passes of 15, against 14 for `slayer`.

## Jaffle Shop sub-suite, by business rule

The 24 questions of Yann's nao-vs-Motley experiment. The raw-SQL agent gets a plain-SQL rendering of the nine
`jaffle-*` business rules in its system prompt; the SLayer and Motley agents have the same rules as memories and see
one only if they call `search`. "Search" says whether the `slayer` / `slayer+python` / `motley` / `motley+python`
trial called it at least once.

| Task | Business rules it needs | `slayer` | `slayer+python` | `motley` | `motley+python` | `sql+python` | Search |
| --- | --- | --- | --- | --- | --- | --- | --- |
| j-c01-peak-weekday-hour | money-in-cents | ✗ | ✗ | ✗ | ✗ | ✗ | 1 / 1 / 1 / 1 |
| j-c02-order-value-bands | money-in-cents | ✓ | ✓ | ✓ | ✓ | ✓ | 1 / 1 / 1 / 1 |
| j-c03-basket-mix | — | ✓ | ✓ | ✓ | ✓ | ✓ | 1 / 1 / 0 / 0 |
| j-c04-ltv-by-first-store | money-in-cents | ✓ | ✓ | ✓ | ✗ | ✓ | 1 / 1 / 1 / 1 |
| j-c05-median-orders-per-customer | — | ✓ | ✓ | ✓ | ✓ | ✓ | 1 / 1 / 0 / 0 |
| j-c06-top-decile-share | — | ✓ | ✗ | ✗ | ✗ | ✓ | 1 / 1 / 1 / 1 |
| j-c07-best-month-vs-avg | money-in-cents | ✓ | ✓ | ✓ | ✗ | ✓ | 1 / 1 / 1 / 1 |
| j-c08-growth-streak | — | ✗ | ✗ | ✗ | ✗ | ✗ | 1 / 1 / 1 / 1 |
| j-c09-brooklyn-cogs-margin | product-margin, sales-by-product, money-in-cents | ✓ | ✓ | ✗ | ✗ | ✓ | 1 / 1 / 1 / 1 |
| j-c10-top-supply-component | product-margin, money-in-cents | ✗ | ✗ | ✗ | ✗ | ✗ | 1 / 1 / 1 / 0 |
| j-c11-tweeters-aov | money-in-cents | ✓ | ✓ | ✓ | ✓ | ✓ | 1 / 1 / 0 / 0 |
| j-c12-jaffle-beverage-attach | — | ✓ | ✓ | ✓ | ✓ | **✗c** | 1 / 1 / 0 / 0 |
| j-q01-stores | — | ✓ | ✓ | ✓ | ✓ | ✓ | 1 / 1 / 1 / 1 |
| j-q02-orders-2025 | — | ✓ | ✓ | ✓ | ✓ | ✓ | 1 / 1 / 1 / 1 |
| j-q03-revenue-by-store-2025 | revenue-definition, money-in-cents | ✓ | ✓ | ✓ | ✓ | ✓ | 1 / 1 / 1 / 1 |
| j-q04-monthly-orders-2026 | data-coverage | ✓ | ✓ | ✓ | ✓ | ✓ | 1 / 1 / 0 / 0 |
| j-q05-top-products-2025 | — | ✗ | ✗ | ✗ | ✗ | ✗ | 1 / 1 / 1 / 1 |
| j-q06-type-share-2025 | sales-by-product, revenue-definition, money-in-cents | ✓ | ✓ | ✓ | ✓ | ✓ | 1 / 1 / 1 / 1 |
| j-q07-aov-by-store | revenue-definition, money-in-cents | ✓ | ✓ | ✓ | ✓ | ✓ | 1 / 1 / 1 / 1 |
| j-q08-tax-rate-check | — | ✓ | ✓ | ✓ | ✓ | ✓ | 1 / 1 / 1 / 0 |
| j-q09-store-growth-2024-2025 | revenue-definition, money-in-cents | ✓ | ✓ | ✗ | ✗ | ✗ | 1 / 1 / 1 / 1 |
| j-q10-new-customers-by-year | new-customers | ✗ | ✗ | ✗ | ✗ | ✓ | 1 / 1 / 1 / 1 |
| j-q11-ytd-growth-same-store | data-coverage, same-store-growth, revenue-definition | ✓ | **✗c** | ✗ | ✗ | ✗ | 1 / 1 / 1 / 1 |
| j-q12-best-unit-margin | product-margin, money-in-cents | **✗c** | **✗c** | **✗c** | **✗c** | ✓ | 1 / 1 / 1 / 0 |

The complex questions (`j-c…`) state "pre-tax" in the question itself, so their revenue basis needs no lookup.

### By rule

- **`jaffle-revenue-definition`** (revenue, sales and AOV are pre-tax): the SLayer agents now search on nearly every
  question, and every pre-tax answer is right except `j-q11-ytd-growth-same-store` in `slayer+python`, which reported
  revenue including tax (3,648,715 against 3,452,838 for last year). The raw-SQL agent, with the rule in its prompt,
  used pre-tax figures throughout.
- **`jaffle-product-margin`** (unit COGS from `supplies`): on `j-q12-best-unit-margin` the four SLayer-backed agents
  answered the question's "which product has the highest gross margin per unit sold?" with that one product (flame
  impala, $10.57, 0.755 of its price), where the answer-shape sentence asks for one row per product; only `sql+python`
  listed all ten. `j-c10-top-supply-component` was correct everywhere but never one query.
- **`jaffle-data-coverage`**, **`jaffle-same-store-growth`** and **`jaffle-new-customers`**: no wrong answer outside
  `j-q11-ytd-growth-same-store` in `slayer+python`; the others needed several queries for the multi-step definitions.
- **`jaffle-sales-by-product`** and **`jaffle-money-in-cents`**: no wrong answer.
- **`jaffle-monthly-store-revenue`** and **`jaffle-tweets-limits`**: no question depends on them alone.
- `j-c12-jaffle-beverage-attach` in `sql+python` computed the exact answer but posted it as text instead of calling
  `submit_answer`, so it counts as no submission.

### Not one query

Every profile missed single query on `j-q05-top-products-2025` (no query returned exactly the five rows),
`j-c01-peak-weekday-hour`, `j-c08-growth-streak` and `j-c10-top-supply-component`. The Motley profiles miss it most
(14 and 12 passes against 18, 16 and 17), mostly on questions that need a per-order or per-month stage and then an
aggregate over it, which they built as separate queries; `j-q10-new-customers-by-year` went that way in all four
SLayer-backed profiles.
