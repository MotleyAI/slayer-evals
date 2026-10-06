## 1. Architecture (approved wording, apply verbatim)

- [x] 1.1 Replace the Purpose paragraph of `architecture/system.arc42.md` with: "A capability benchmark for agents answering analytics questions over a seeded demo database: it measures whether an agent given SLayer's MCP server reaches for SLayer's DSL (partitioned aggregates, transforms, multi-stage queries, …) rather than pulling raw rows and post-processing them, and how it compares with an agent given direct SQL access, including on traps where naive SQL silently returns wrong numbers. Each trial is graded on correctness and on whether a single query's own result is the answer. Any agent can be benchmarked through one adapter." Verify `la-arch-check` stays green.
- [x] 1.2 Add principle "7. Proven tasks: every task has a single SLayer query that answers it, and every trap a naive SQL query that misses it. [enforced: test:tests/test_task_proofs.py]". Verify `la-arch-check` resolves the enforcement pointer once 4.x exists.

## 2. Core schemas

- [x] 2.1 `Profile`/`PROFILES` gain `sql+python`; `EndReason` gains `auto_fail`; `Trace` gains `profile`. Verify trace round-trip test.
- [x] 2.2 `Task`: `row` → `covers` (rows + closed pitfall `Literal`, incl. `avg_of_avgs` and `bucket_reaggregation`), `slayer_query`, `naive_sql` (str | list, required iff trap), `uses_saved`, derived `suite`; `Compare.null_as_zero`. Verify loader accept/reject tests per the benchmark-tasks scenarios.
- [x] 2.3 `TrialResult.covers` replaces `row`; `TraceFlags.slayer_errors` → `query_errors`. Verify schema tests.
- [x] 2.4 `ParsedResult.from_text` parses `{columns, rows, truncated}`. Verify result-parsing tests in all four shapes.

## 3. Agents

- [x] 3.1 `agents/sql.py`: per-call read-only connection (external access off, config locked), single-statement check, worker thread + 60 s timeout with interrupt/join/close, `fetchmany(1001)`, JSON output, DB errors as tool errors. Verify the SQL-tool scenarios (result, batch rejected, escape attempts, timeout isolation, row cap).
- [x] 3.2 `claude.py`: `sql+python` registers `submit_answer`, `python`, `sql` on `bench` and no SLayer server; leak check per profile; JSON sentence only in SLayer profiles; trace carries profile. Verify profile tool-set, leak and system-prompt tests.
- [x] 3.3 `trace.py`: parse `sql` results. Verify a normalized `sql` call has `parsed`.

## 4. Grading

- [x] 4.1 `single_query` over `query` + `sql`; `null_as_zero` in table matching. Verify grading scenarios.
- [x] 4.2 Refusal grading in `sql+python` (no rows + phrase; `single_query` = `correct`); `uses_saved` auto-fail in `sql+python`. Verify grading scenarios.
- [x] 4.3 Flags: `raw_sql` for `sql` calls, `query_errors`, `several_queries` counts `sql`. Verify both flag scenarios.

## 5. Dataset

- [x] 5.1 Commit canonical hashes of the probe tables and `orders_flat` (computed on the current generator BEFORE any change) and a test asserting them. Verify it passes on main's generator.
- [x] 5.2 Generator: `products`, `order_items` (cents split, sums to amount), `campaigns`, `campaign_members`, `cities` with keys/FKs, own RNG streams, created after existing tables; witnesses for every trap. Verify determinism, items-sum, edge-case and hash tests.
- [x] 5.3 Store models for the new tables with joins/cardinalities (`customers`→`cities` on city + region_id). Verify store-template test lists them.

## 6. Tasks

- [x] 6.1 Move the 25 tasks to `tasks/capability/qNN/`, convert `row` → `covers`, add `slayer_query` to each; reword q3, q6, q10, q25 prompts (same meaning; truth snapshots unchanged); `uses_saved: [monthly_rev]` on q18 and q23. Verify snapshot test unchanged and task proofs pass.
- [x] 6.2 Suite checks: coverage minimums (>= 12 traps, >= 2 tasks with >= 3 rows), suite/folder agreement, whole-word deny-list with the pitfall-hint entries. Verify the coverage, misplaced-file, leaky-prompt and embedded-word tests.
- [x] 6.3 `tasks/proofs.py` + `tests/test_task_proofs.py`: reference queries on a store copy with an absolute datasource path, naive SQL must run with resolvable columns and miss the truth, row markers, `uses_saved` names exist. Verify the three proof scenarios.
- [x] 6.4 Author the 17 trap tasks under `tasks/traps/` (fan_out ×2, count_after_join, chasm, bridge, non_unique_key, outer_join_filter, not_in_null, count_outer_join, filtered_total — denominator worded as the company's 'ok' revenue, distinct_reagg, missing_periods, filter_before_window ×2 — the running-total one with a two-stage reference query, rows_window_gap — `window='3m'`, timestamp_bounds, avg_of_avgs); prompts state the expected rows but never the pitfall mechanism; `null_as_zero` where an empty period or zero count is involved. Verify truth snapshots (<= 20 rows) and task proofs.
- [x] 6.5 Author the 11 combo tasks under `tasks/combo/` ([Q2,Q4], [Q14,Q2], [Q5,Q2], [Q17,Q4], [Q6,Q14], [Q21,Q2], [Q23,Q4] with `uses_saved`, [Q13,Q4], [Q6,Q12,Q1], [Q24,Q2,Q20], [Q16,Q2,Q4]). Verify truth snapshots and task proofs.
- [x] 6.6 Try to author a Q18 trap (`bucket_reaggregation`) that lures raw SQL into re-aggregating weekly buckets into months, with an unambiguous prompt; if none is unambiguous, record that here and add nothing. Verify proofs if added.
  - None is unambiguous: the database has no weekly table, so a raw-SQL agent computes months from the raw orders and is never lured through weekly buckets; nothing added, Q18 stays the refusal task `q18-day-of-monthly`.
- [x] 6.7 Any task whose `slayer_query` cannot match its truth: STOP and raise it with the user (no rewording, narrowing or xfail without approval).

## 7. Runner and report

- [x] 7.1 Runner: default three profiles; row selection matches any covered row; `uses_saved` × `sql+python` recorded as `auto_fail` without a trial process (one trial in `until-pass`). Verify run-selection and auto-fail tests.
- [x] 7.2 Report: headline suite × profile table with the `correct`-first note, pitfall × profile table, per-row tables counting multi-row tasks per row, suite column in per-task table, `Query errors` flag column, digest lists `sql` calls. Verify report tests; regenerate `tests/fixtures/run_*` for the new schema.
- [x] 7.3 CLI: profile choices include `sql+python`; `--rows` help mentions covered rows. Verify CLI tests.

## 8. Baseline and docs

- [x] 8.1 Full non-integration suite, ruff and basedpyright green.
- [ ] 8.2 Run all tasks × three profiles, Opus 5.5, `--mode repeat --trials 3`, subscription auth with the same env file as the previous baseline; rerun trials that died on API overload before their first turn and note it.
- [ ] 8.3 Replace `results/baseline/` (report, results, metadata, traces); verify the baseline-reproducibility test.
- [ ] 8.4 Update README (flavors, suites, `sql+python` profile, task format fields, new baseline table led by `correct`) and rewrite `docs/baseline-failures.md` as a per-profile, per-pitfall failure breakdown.
