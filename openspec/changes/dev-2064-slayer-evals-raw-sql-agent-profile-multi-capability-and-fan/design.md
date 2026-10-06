## Context

See proposal.md (Why). The harness from the archived change `dev-2055-…` runs a hermetic Claude Agent SDK session per
trial with SLayer's MCP server and an in-process `bench` server (`submit_answer`, `python`). Grading is pure over
(task, truth, submission, trace). Tasks carry one `row`. The dataset is the probe schema plus planted edge cases.

## Goals / Non-Goals

**Goals:**
- A raw-SQL flavor as hermetic as the SLayer ones, graded with the same verdict shape.
- Tasks whose fairness is proven: a single SLayer query answers each; each trap's naive SQL demonstrably misses.
- A three-flavor baseline at N = 3 whose headline is correctness.

**Non-Goals:**
- Changing SLayer. Gaps found while authoring reference queries are raised with the user, never routed around.
- A third-party DuckDB MCP server, or giving the raw-SQL Python tool database access.
- Database views mirroring SLayer saved definitions: reusing saved definitions is the semantic layer's job, so tasks
  that rely on them auto-fail in `sql+python`.

## Decisions

### Raw-SQL access: our own `sql` tool on the `bench` server
Alternatives: a third-party DuckDB MCP server (output format, extra tools and capabilities outside our control; harder
to prove hermetic) or SQL only inside Python (no per-query trace entry, so no `single_query`). The tool lives in
`agents` (new `agents/sql.py`), registered on the `bench` server only for `sql+python`.
- One connection per call: `duckdb.connect(db_path, read_only=True, config={"enable_external_access": False,
  "lock_configuration": True})`. Exactly one statement, checked with DuckDB's statement extractor before execution.
- Execution and a `fetchmany(1001)` run in a dedicated worker thread; the coroutine waits with a 60 s timeout, then
  calls `interrupt()`, joins the worker within a short bound and closes the connection, so a timed-out statement never
  overlaps the next call. Hermeticity is proven by behavioural tests (host file read, `ATTACH`, `COPY … TO`, `INSTALL`,
  `LOAD`, `SET enable_external_access=true`, `INSERT`), not by inspecting options.
- Output `{"columns", "rows", "truncated"}`; `ParsedResult.from_text` learns this shape so `trace.py` parses `sql` like
  `query`.

### Profile travels in the trace
Grading must differ by flavor for refusal tasks and `uses_saved` tasks. Putting `profile` on `Trace` keeps a verdict a
function of (task, truth, submission, trace), so arc42 principle 1 stands unchanged, and keeps agents blind (they
already know their profile).

### Auto-fail without running an agent
For a `uses_saved` task in `sql+python`, the runner skips the trial process and grades `Trace(profile=…,
end_reason="auto_fail")`; grading returns the failed verdict naming the definitions. No transcript is written. In
`until-pass` the combination stops after that one trial. This keeps the rule in grading (pure) and the cost at zero.

### `single_query` across flavors
Generalized to `query` or `sql` calls. Raw SQL can always express an answer in one statement, so `single_query` is not
equally hard across flavors; the report leads with `correct` and says so. Refusal tasks in `sql+python`: `correct` iff
no rows and a `message_any` phrase; `single_query` equals `correct` (no SQL call can produce SLayer's warning kind).

### Task schema: `covers` mixes rows and pitfalls
`covers: list[str]` replaces `row`; the pitfall kinds are a closed `Literal` in `core`. The suite is a derived
property. `TrialResult.covers` replaces `row`; row selection matches any covered row. All task files move under
`tasks/<suite>/`; the loader still globs recursively.

### Task proofs in `tasks`
New `tasks/proofs.py` (imports `core`, the SLayer engine and DuckDB) runs a task's `slayer_query` and `naive_sql` and
returns their tables (or the raised error kind / warning kinds), and holds the marker check. Matching against the truth
with `grading.match_tables` happens in `tests/test_task_proofs.py`, so the model's import law (`tasks -> core` only)
is unchanged.
- The engine runs on a temporary copy of the store whose `bench` datasource is rewritten to the built database's
  absolute path (the template stores the trial-relative `bench.duckdb`); no `chdir`.
- Row markers (Q-row → DSL substrings that must appear in `slayer_query`'s JSON) are a small table in `tasks/suite.py`;
  rows without a clean tell (e.g. Q8, Q9, Q10, Q18, Q19, Q22, Q25) have none.

### Dataset extension without perturbing existing truth
New tables use their own `_rng(seed, "<table>")` streams and are created after the existing ones; no planted row is
added to an existing table. `order_items` splits each order's amount in cents across 1–4 lines (last line takes the
remainder). Planted witnesses for traps live in the new tables or are chosen from existing data and asserted (e.g. two
equal-amount multi-item orders in one region; if the seed has none, a dedicated witness is planted in `order_items` and
`orders` is left untouched). A committed hash file pins the probe tables and `orders_flat`.

### Prototype findings on SLayer 1.0.2 (scratch build, before tests)
- chasm from a `customers` root with `sum(orders.amount)`, `sum(returns.amount)` by `regions.name`: correct.
- `time_spine.timestamp` by month with both facts: the returns-only month 2024-08 is present (orders NULL).
- `sum(amount, window='3m')` (not `'3 months'`, which raises `WindowDurationError`) is calendar-based and not clipped by
  the date range; `time_shift(sum(amount), -1, 'month')` reaches December 2024 for January 2025.
- `customers` with filter `orders.id is null`: 1 customer, `semi_join_pushed` warning.
- `cumsum(sum(amount))` IS clipped by a date range or filter; the running-total trap's reference query is two-stage
  (running total over all months in stage one, filtered in stage two), which the user accepted.

### Prompt deny-list as whole-word patterns
Entries compile to case-insensitive regexes with word boundaries on alphabetic edges; DSL tokens such as `rank(` keep a
leading boundary only.

## Risks / Trade-offs

- [A trap's reference SLayer query fails or disagrees with the truth] → stop and raise it with the user (rewording,
  narrowing, xfail or an issue are the user's call).
- [The Q18 raw-SQL lure (weekly buckets re-aggregated to months) has no unambiguous wording] → Q18 stays a refusal task
  that auto-fails in `sql+python` (user-approved fallback).
- [NULL foreign-key orders merge into SLayer's NULL-region cell] → truths of affected tasks define the NULL group the
  way SLayer does, and prompts state how unknown-region orders are grouped.
- [`single_query` easier for raw SQL] → report leads with `correct`; README says so.
- [Subscription rate limits during a 468-trial baseline] → results are written per trial; reruns by task selection.

## Migration Plan

Result files from the old baseline do not load into the new `TrialResult` (`row` → `covers`, flag rename); the
baseline is replaced in this change and test fixtures are regenerated. No other consumers.
