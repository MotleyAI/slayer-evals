## MODIFIED Requirements

### Requirement: Task file format
Each task SHALL be one YAML file with: `id` (unique), `covers` (a non-empty list without duplicates, each entry a
covered row — one of Q1–Q18, Q20, Q21, Q23–Q25 — or a pitfall kind, with at least one row), `prompt` (a natural
language business question), `truth_sql` (DuckDB SQL over the built dataset), `slayer_query` (the intended single
SLayer query, in the argument shape of the SLayer MCP `query` tool), `compare` (`keys`, `values`, `tolerance` default
1e-6, `ordered` default false, `columns_exact` default false, `null_as_zero` default false), `expect` (`match` by
default, or `{error: <kind or list of kinds>, message_any: [...]}` / `{warning: <kind or list of kinds>,
message_any: [...]}`), `naive_sql` (one DuckDB statement or a list of them; required iff `covers` holds a pitfall kind,
forbidden otherwise), optional `uses_saved` (the saved SLayer definitions the prompt names) and optional `xfail` (an
issue key with a reason). The pitfall kinds SHALL be the closed list `fan_out`, `count_after_join`, `chasm`, `bridge`,
`non_unique_key`, `outer_join_filter`, `not_in_null`, `count_outer_join`, `filtered_total`, `distinct_reagg`,
`missing_periods`, `filter_before_window`, `rows_window_gap`, `timestamp_bounds`, `avg_of_avgs`,
`bucket_reaggregation`. Loading MUST reject a file with an unknown key, a missing required key, a duplicate id, an
unknown or repeated `covers` entry, a `covers` without a row, row Q19 or Q22, a trap without `naive_sql`, or `naive_sql`
on a task that is not a trap.

#### Scenario: Valid task loads
- **WHEN** a well-formed task file is loaded
- **THEN** it yields a task whose fields equal the file's values, with defaults applied

#### Scenario: Malformed task rejected
- **WHEN** a task file has an unknown key, lacks `truth_sql` or `slayer_query`, reuses another task's id, covers Q19 or Q22, covers only pitfalls, repeats a `covers` entry, or names an unknown pitfall
- **THEN** loading fails with an error naming the file and the problem

#### Scenario: Naive SQL tied to traps
- **WHEN** a task covering `chasm` has no `naive_sql`, or a task covering only rows has one
- **THEN** loading fails naming the file and `naive_sql`

### Requirement: Prompts are capability-neutral
A task prompt MUST NOT name SLayer DSL features or syntax (for example `partition_by`, `time_shift`, `cumsum`,
`window=`, `rank(`, `refine`, `source_model`, `multi-stage`), nor hint at a pitfall's mechanism (for example `join`,
`duplicate`, `double count`, `fan-out`, `chasm`, `null`, `not in`, `counted once`, `count each`). Deny-list entries
SHALL match as whole words or phrases, case-insensitively, so that ordinary words containing them (such as
`adjoining`) pass. The check SHALL run over every committed task.

#### Scenario: Leaky prompt detected
- **WHEN** a task's prompt contains a DSL keyword or a pitfall hint from the deny list
- **THEN** the task-suite check fails naming that task and keyword

#### Scenario: Embedded word passes
- **WHEN** a prompt says "adjoining regions"
- **THEN** the check does not flag `join`

### Requirement: Row coverage
The committed task set SHALL contain at least one task covering each of Q1–Q18, Q20, Q21, Q23, Q24 and Q25, and none
covering Q19 or Q22; at least 12 trap tasks; and at least 2 tasks covering three or more rows. Tasks for Q21 and Q24
SHALL exercise only what SLayer supports for those rows. Rows Q9 and Q18 SHALL include at least one refusal or warning
task.

#### Scenario: Coverage check
- **WHEN** the task suite is loaded
- **THEN** every covered row has a task, Q19 and Q22 have none, Q9 and Q18 each have a task whose `expect` is an error or warning, there are at least 12 trap tasks, and at least 2 tasks cover three or more rows

## ADDED Requirements

### Requirement: Task suites
Each task SHALL belong to exactly one suite, derived from `covers` and never stored: `trap` if it covers a pitfall
kind, else `combo` if it covers two or more rows, else `capability`. Task files SHALL live under `tasks/capability/`,
`tasks/combo/` and `tasks/traps/` according to their suite.

#### Scenario: Suite derivation
- **WHEN** tasks covering `[Q4]`, `[Q2, Q4]` and `[Q6, fan_out]` are loaded
- **THEN** their suites are `capability`, `combo` and `trap`

#### Scenario: Misplaced file
- **WHEN** a task whose suite is `trap` sits under `tasks/combo/`
- **THEN** the task-suite check fails naming the file

### Requirement: Task proofs
Every task's `slayer_query` SHALL be run through SLayer, in process, on the built store and database: for a `match`
task its result MUST match the truth under the task's `compare`; for an error or warning task it MUST raise or warn
with one of the expected kinds. Every `naive_sql` statement SHALL run on the built database, return a table whose
columns resolve against the truth's, and MUST NOT match the truth. For every covered row that has DSL markers (for
example Q2 and Q3 `partition_by`, Q4 `time_shift`, `cumsum` or `change`, Q11 `window=`, Q14 `rank(`), the
`slayer_query` MUST contain one of that row's markers. Every `uses_saved` entry MUST name a saved definition in the
store template.

#### Scenario: Reference query answers the task
- **WHEN** the proofs run over the committed tasks
- **THEN** every `slayer_query` result matches its truth or produces the expected kind

#### Scenario: Dead trap detected
- **WHEN** a trap's `naive_sql` returns the truth on the built database
- **THEN** the proof fails naming the task

#### Scenario: Mislabelled cover detected
- **WHEN** a task covers Q14 but its `slayer_query` contains no ranking marker
- **THEN** the proof fails naming the task and Q14
