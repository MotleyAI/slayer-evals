# Baseline failures, by profile and pitfall

Where Claude Opus 5.5 failed in the [committed baseline](../results/baseline/report.md): every task once in each of
the three profiles (`slayer`, `slayer+python`, `sql+python`), SLayer at commit `1653a91` (reported as 1.1.0, the first
commit with the fix for a saved ratio measure plus a transform over it). It is a **single-trial snapshot**: one flip
is noise, a failure across profiles is a pattern.

The two SLayer profiles ran first (2026-10-06 17:31 UTC). Their `sql+python` counterpart was then rerun (18:50 UTC)
after the system prompt gained one sentence for every profile: *"Submit exact values without rounding, and use null
as the label of a group whose key is unknown."* Without it the raw-SQL agent labelled the unknown-region group
"Unknown", rounded to two decimals or added empty rows, and the strict grader marked 7 of its 17 traps wrong although
it had avoided every one of those traps (10/17 correct before, 16/17 after). The SLayer profiles had only two such answers, so
they were not rerun; their transcripts show the shorter prompt. `q12-net-revenue` failed in all three profiles the same
way (agents counted orders without a customer with a discount of 0, which the truth leaves out); its prompt now says
those orders are left out, and it was rerun in all three profiles (19:02 UTC), passing in each.

✓ pass · ✗ correct answer, but not one query's own result · **✗c** wrong answer · auto: the task names a saved SLayer
definition, so it fails in `sql+python` without running

## Headline

| Suite | Profile | Trials | Correct | Single query | Passed |
| --- | --- | --- | --- | --- | --- |
| capability | `slayer` | 24 | 23 | 20 | 19 |
| capability | `slayer+python` | 24 | 23 | 16 | 16 |
| capability | `sql+python` | 24 (2 auto) | 20 | 17 | 17 |
| combo | `slayer` | 11 | 11 | 4 | 4 |
| combo | `slayer+python` | 11 | 11 | 4 | 4 |
| combo | `sql+python` | 11 (1 auto) | 10 | 6 | 6 |
| trap | `slayer` | 17 | **17** | 10 | 10 |
| trap | `slayer+python` | 17 | 16 | 9 | 8 |
| trap | `sql+python` | 17 | 16 | 16 | 15 |

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
| t-city-size | non_unique_key | Q6 | ✓ | **✗c** | ✓ |
| t-zero-regions | outer_join_filter | Q8 | ✗ | ✗ | ✓ |
| t-never-returned | not_in_null | Q10 | ✓ | ✗ | ✓ |
| t-orders-per-customer | count_outer_join | Q8 | ✓ | ✗ | ✓ |
| t-ok-share | filtered_total | Q2 | ✓ | ✓ | ✓ |
| t-orders-per-category | distinct_reagg | Q1 | ✗ | ✗ | ✓ |
| t-monthly-gaps | missing_periods | Q4 | ✓ | ✓ | ✓ |
| t-prev-month | filter_before_window | Q4 | ✓ | ✓ | ✗ |
| t-all-time-running | filter_before_window | Q4, Q15 | ✗ | ✓ | ✓ |
| t-rolling-gap | rows_window_gap | Q11 | ✗ | ✗ | ✓ |
| t-march-events | timestamp_bounds | Q20 | ✓ | ✓ | ✓ |
| t-overall-aov | avg_of_avgs | Q1 | ✗ | ✗ | ✓ |

No profile fell into a trap's naive SQL. Neither wrong trap answer is about the pitfall: on `t-fan-out-items`
`sql+python` added an empty row for the region without customers, and on `t-city-size` `slayer+python` labelled the
unknown group "(not in reference table)" (the SLayer profiles ran before the null-label sentence). Opus 5.5 writing
raw SQL knows these pitfalls well; on this set the semantic layer's advantage is not correctness but that the SLayer agent
never had to think about them.

The SLayer agents' trap failures are all ✗: right answers assembled from several queries. On `t-chasm`,
`t-fan-out-credit`, `t-overall-aov` and `t-orders-per-category` they queried each fact or grain separately and
combined the results, where one query with cross-model measures or `partition_by=[]` would have done it; on
`t-zero-regions` and `t-rolling-gap` they missed the one-query idioms (a conditional sum rooted at `regions`, a
`window='3m'` aggregate) and pieced the months together.

## Wrong answers outside the traps

| Task | Row(s) | `slayer` | `slayer+python` | `sql+python` | Why |
| --- | --- | --- | --- | --- | --- |
| q3-avg-city-revenue | Q3 | **✗c** | ✗ | **✗c** | `slayer` labelled the unknown group; `sql+python` left the orders without a customer out of it (one city instead of two) |
| q6-region-credit | Q6 | ✗ | **✗c** | ✓ | an extra, empty row for the region without customers |
| q9-credit-by-status | Q9 | ✓ | ✓ | **✗c** | the raw-SQL agent explained the overlap but still submitted the (overlapping) totals |
| q20-last-three-months (xfail) | Q20 | **✗c** | ✗ | **✗c** | "last three months" read from today's date, where the truth assumes January 2026 |

## Not one query (✗), outside the traps

| Task | Row(s) | `slayer` | `slayer+python` | `sql+python` |
| --- | --- | --- | --- | --- |
| q13-top-cities-count | Q13 | ✗ | ✗ | ✗ |
| q11-rolling-customers | Q11 | ✗ | ✗ | ✓ |
| q7-cumulative-change | Q7 | ✗ | ✗ | ✓ |
| q14-top-customer-per-region | Q14 | ✓ | ✗ | ✓ |
| q2-city-share | Q2 | ✓ | ✗ | ✓ |
| q24-top-two-per-region | Q24 | ✓ | ✗ | ✗ |
| q4-prior-year | Q4 | ✓ | ✓ | ✗ |
| c-aov-change | Q17, Q4 | ✗ | ✗ | ✗ |
| c-region-credit-rank | Q6, Q14 | ✗ | ✗ | ✗ |
| c-top-growth-months | Q13, Q4 | ✗ | ✗ | ✗ |
| c-region-month-share | Q2, Q4 | ✗ | ✗ | ✓ |
| c-size-class-months | Q16, Q2, Q4 | ✗ | ✗ | ✓ |
| c-top-two-q1-share | Q24, Q2, Q20 | ✓ | ✗ | ✗ |
| c-spend-band-share | Q5, Q2 | ✗ | ✓ | ✓ |
| c-top-customer-share | Q14, Q2 | ✗ | ✓ | ✓ |
| c-net-region-tier | Q6, Q12, Q1 | ✓ | ✗ | ✓ |

The persistent patterns, as in the previous baseline:

- **Order by what you don't show (Q13).** Every profile projects the sort measure, so no query's result has
  exactly the asked-for columns; SLayer's `order` on an unselected measure is never reached.
- **Transforms over a date range (Q4, Q7, Q11).** The SLayer agents query an extra month (or all months) so that a
  change or rolling value has its predecessor, then drop rows, instead of relying on `time_shift` / `change` /
  `window=` reaching outside the range.
- **Combos cost single-query passes in every profile:** 4/11 for both SLayer profiles, 6/10 for raw SQL. With two or
  three capabilities in play, agents build the answer in steps.

`slayer+python` passes less often than `slayer` (28 against 33 of 52): with Python available, the agent more often
pulls partial results and finishes the work in pandas.
