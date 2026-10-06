## Why

The benchmark only shows whether agents reach for SLayer's DSL; it cannot show what SLayer buys over an agent that
queries the database directly. A raw-SQL flavor, tasks that combine capabilities, and trap tasks where naive SQL
silently returns wrong numbers turn it into a three-way comparison of correctness, which is the claim a semantic layer
has to back up.

## What Changes

- New tooling flavor `sql+python`: no SLayer; a read-only, hermetic `sql` tool on the trial's DuckDB copy plus the same
  Python sandbox. Runs default to all three flavors.
- `single_query` generalizes to "one successful `query` or `sql` call's own result is the answer"; the
  `slayer_errors` flag is renamed `query_errors` (**BREAKING** for result files). Refusal tasks in `sql+python` are graded
  on the message; tasks that name a saved SLayer definition auto-fail in `sql+python`.
- Task format: `row` becomes `covers`, a list of capability rows and pitfall kinds (**BREAKING** for task files and
  results); new required `slayer_query` on every task; `naive_sql` required on trap tasks; optional `uses_saved`;
  compare option `null_as_zero`. Task files move under `tasks/capability/`, `tasks/combo/`, `tasks/traps/`.
- Task proofs: every task's `slayer_query` answers it through SLayer, every trap's `naive_sql` misses it, and each
  covered row's DSL marker appears in the reference query.
- Dataset: new tables `products`, `order_items`, `campaigns`, `campaign_members`, `cities` with store models; existing
  tables unchanged.
- 17 trap tasks and 11 multi-capability tasks (3 of them with three rows); prompts q3, q6, q10, q25 reworded to pass a
  wider hint deny-list.
- Report: suite × flavor and pitfall × flavor tables; rows counted per covered row.
- New committed baseline: all tasks, all three flavors, Opus 5.5, N = 1; README and failure breakdown rewritten.
- `architecture/system.arc42.md`: Purpose rewritten for three flavors and traps; new principle 7 (proven tasks).

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `agent-harness`: third profile `sql+python` and its `sql` tool; per-flavor system prompt sentence; trace parsing of
  `sql` results.
- `grading`: `single_query` over `query` or `sql`; refusal grading without a SLayer trace in `sql+python`; auto-fail
  for saved-definition tasks; `null_as_zero`; flag changes.
- `benchmark-tasks`: `covers`, suites, `slayer_query`, `naive_sql`, `uses_saved`, prompt deny-list, coverage minimums,
  task proofs.
- `benchmark-dataset`: extra tables and planted witnesses for the traps; existing tables fixed.
- `benchmark-runs`: three default profiles; auto-failed trials recorded without running an agent.
- `benchmark-report`: suite, pitfall and per-row tables over three flavors; committed baseline at N = 3.

## Impact

- Code: `core` (Profile, Task, TrialResult, TraceFlags, ParsedResult), `agents` (new `sql.py`, `claude.py`, `trace.py`),
  `grading`, `tasks` (loading, suite checks, new `proofs.py`), `dataset` (generator, models), `runner`, `report`, `cli`.
- Data: every task file, all truth snapshots for new tasks, `results/baseline/`, `README.md`,
  `docs/baseline-failures.md`, test fixtures under `tests/fixtures/`.
- Dependencies: none new (DuckDB and SLayer are already pinned).
- Architecture: `system.arc42.md` Purpose and principle 7; no new nodes or arrows.
