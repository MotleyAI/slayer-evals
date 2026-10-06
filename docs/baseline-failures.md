# Baseline failures, compared

Where Claude Opus 5.5 failed in the [committed baseline](../results/baseline/report.md) (run 2026-10-06 13:47 UTC),
compared across the two profiles and against the previous baseline (12:38 UTC the same day, same code under test).
Every task ran once per profile, so a single flip between runs is noise; a failure in all four cells is a pattern.

A trial **passes** when its answer is correct *and* one SLayer query's own result contains it. The usual failure is
a correct answer that the agent assembled itself, by combining queries, writing SQL, using Python or doing the
arithmetic in its head.

## Headline

| Profile | Correct | Single query | Passed | Previous baseline |
| --- | --- | --- | --- | --- |
| `slayer` | 22/24 | 19/24 | **18/24** | 19/24 |
| `slayer+python` | 22/24 | 18/24 | **17/24** | 17/24 |

The relative-date task (Q20) is xfail and not counted. Two trials of this run hit API overload (HTTP 529) before
their first turn and were re-run; both passed.

## Failure matrix

✓ pass · ✗ fail · **✗c** wrong answer (the others are correct answers that are not one query's result)

| Task | Row | Intended SLayer idiom | `slayer` now | `slayer` before | `+python` now | `+python` before |
| --- | --- | --- | --- | --- | --- | --- |
| q11-rolling-customers | Q11 | `count_distinct(customer_id, window='90d')` | ✗ | ✗ | ✗ | ✗ |
| q13-top-cities-count | Q13 | `order` on an unselected measure | ✗ | ✗ | ✗ | ✗ |
| q7-cumulative-change | Q7 | `cumsum(change(sum(amount)))` | ✗ | ✗ | ✗ | ✗ |
| q6-region-credit | Q6 | fan-out-safe `sum(customers.credit)` | **✗c** | ✗ | **✗c** | ✗ |
| q12-net-revenue | Q12 | `sum(amount - customers.discount)` | **✗c** | **✗c** | **✗c** | **✗c** |
| q14-top-customer-per-region | Q14 | `rank(...)` | ✓ | ✓ | ✗ | ✗ |
| q3-avg-city-revenue | Q3 | `avg(sum(amount, partition_by=[city, region]))` | ✗ | ✓ | ✓ | ✓ |
| q2-city-share | Q2 | `sum(amount) / sum(amount, partition_by=region)` | ✓ | ✓ | ✗ | ✓ |
| q4-prior-year | Q4 | `time_shift(sum(amount), -1, 'year')` | ✓ | ✓ | ✓ | ✗ |

The other 15 tasks passed in all four cells.

## Persistent: the capability is never reached

**Q11, rolling windows.** No trial used a rolling window. In `slayer` the agent wrote raw SQL through a `sql`-backed
inline model; in `slayer+python` it ran twelve separate `count_distinct(customer_id)` queries, one 90-day date
filter per month. Both answers were right. The `slayer` agent searched for *"rolling 90 day distinct customers
window count_distinct"*, and `search` returned generic models, columns and the `help.models` / `help.intro`
memories, nothing about windows. This is the clearest gap on the MCP surface.

**Q13, ordering by a measure that is not shown.** All four trials put revenue into the query to order by it, then
dropped the column when submitting. The agent never tried `order` on a measure it does not select, so the query
returns three columns where the task asks for two.

**Q7, deep composition.** The `slayer` agent did use `change(sum(amount))`, but widened the date range to get
December 2024 as the base for January and then summed the changes itself. The `slayer+python` agent pulled monthly
revenue and computed both steps in Python. Neither nested the transforms into one measure or limited the output to
2025 inside the query.

**Q14, ranking (`slayer+python` only).** With Python available, the agent pulled all 200 customer-by-region revenue
rows, sorted, and picked each region's top customer itself. Without Python (`slayer`) it passed in both runs, in this
run with one multi-stage query that keeps the rows where revenue equals `max(revenue, partition_by=region)` (not
`rank`, but one SLayer query). Having an escape hatch made the agent skip the DSL here.

## Persistent: wrong answers that read as task ambiguity

These two need a call on the task rather than on SLayer: the agent's answer is defensible, and its own message
states the alternative reading.

**Q12, net revenue.** Some orders point to customer ids that do not exist in `customers`. The truth uses plain SQL
subtraction, so `amount - NULL` drops those orders and the no-region group totals 627.83. Every trial treated the
missing discount as 0 and submitted 1,143.30, in both runs. In this run a query in each trial already returned the
truth's numbers, so `single_query` passes but `correct` fails, and both agents' messages give the 627.83 alternative. The prompt does not say
how to treat orders without a known customer.

**Q6, region credit.** Both trials in this run added an `Arctic` row (a region with no customers and no orders, with
empty values), giving six rows where the truth has five; the truth starts from orders, so it never sees Arctic. The
prompt says "for each region", which supports including it. In the previous baseline both trials left Arctic out,
were correct, but still failed `single_query`: they queried orders and customers separately and joined the results
by hand instead of one fan-out-safe query. Three of the four trials hit `MeasureNameCollidesWithColumnError` when
naming a measure `credit` after the column it sums.

## Run-to-run flips (noise at N = 1)

| Task | Profile | Before → now | What happened in the failing trial |
| --- | --- | --- | --- |
| q3-avg-city-revenue | `slayer` | ✓ → ✗ | Pulled the 12 city totals and averaged them per region in its head (no Python in this profile); correct, but no re-aggregation query. |
| q2-city-share | `slayer+python` | ✓ → ✗ | Pulled region × city revenue and computed both shares in Python. |
| q4-prior-year | `slayer+python` | ✗ → ✓ | Before: used `time_shift` but returned 14 months and trimmed them itself. Now one query. |

## What this suggests for the SLayer MCP surface

- **Rolling windows are not discoverable.** `search` and the help memories never point to `window=`, even when the
  agent asks for it almost by name (Q11).
- **Ordering by an unselected measure is not discoverable** (Q13); every trial assumed the order column must be
  selected.
- **Limiting a transform's output range** (Q7, and Q4 before) is where the agent falls back to trimming rows itself.
- **Python access lowers DSL use** on tasks the agent can otherwise do in SLayer (Q14, and Q2 this run).
- **The measure/column name collision** (Q6) costs a turn each time; the error could suggest a free name.
