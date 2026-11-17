# benchmark-tasks Specification

## Purpose
Defines what a benchmark task is — a business question with machine-checkable truth, worded so that one SLayer query
using the row's capability answers it — and how tasks are loaded and their truth computed and pinned.

## Requirements

### Requirement: Task file format
Each task SHALL be one YAML file with: `id` (unique), `dataset` (`bench` by default, or `jaffle`), `covers` (required
on a `bench` task and forbidden on a `jaffle` task; on a `bench` task a non-empty list without duplicates, each entry
a covered row — one of Q1–Q18, Q20, Q21, Q23–Q27 — or a pitfall kind, with at least one row), `prompt` (a natural
language business question), `truth_sql` (DuckDB SQL over the task's built dataset), `slayer_query` (the intended
single SLayer query, in the argument shape of the SLayer MCP `query` tool), `compare` (`keys`, `values`, `tolerance`
default 1e-6, `ordered` default false, `columns_exact` default false, `null_as_zero` default false, `extra_zero_rows`
default false), `expect` (`match` by default, or `{error: <kind or list of kinds>, message_any: [...]}` / `{warning:
<kind or list of kinds>, message_any: [...]}`), `naive_sql` (one DuckDB statement or a list of them; required iff
`covers` holds a pitfall kind, forbidden otherwise), optional `uses_saved` (the saved SLayer definitions the prompt
names) and optional `xfail` (an issue key with a reason, and optionally the `profiles` it applies to; without
`profiles` it applies to every profile). The pitfall kinds SHALL be the closed list `fan_out`, `count_after_join`,
`chasm`, `bridge`, `non_unique_key`, `outer_join_filter`, `not_in_null`, `count_outer_join`, `filtered_total`,
`distinct_reagg`, `missing_periods`, `filter_before_window`, `rows_window_gap`, `timestamp_bounds`, `avg_of_avgs`,
`bucket_reaggregation`, `count_after_unnest`, `unnest_fan_out`, `null_element`, `same_element_and`. Loading MUST
reject a file with an unknown key, a missing required key, an unknown dataset, a duplicate id, a `bench` task without
`covers`, a `jaffle` task with `covers`, an unknown or repeated `covers` entry, a `covers` without a row, row Q19 or
Q22, a row outside Q1–Q27, a trap without `naive_sql`, `naive_sql` on a task that is not a trap, or an `xfail` naming
an unknown profile.

#### Scenario: Valid task loads
- **WHEN** a well-formed task file is loaded
- **THEN** it yields a task whose fields equal the file's values, with defaults applied and dataset `bench` when the file names none

#### Scenario: Malformed task rejected
- **WHEN** a task file has an unknown key, lacks `truth_sql` or `slayer_query`, reuses another task's id, covers Q19, Q22 or Q28, covers only pitfalls, repeats a `covers` entry, names an unknown pitfall, has an `xfail` naming an unknown profile, or names an unknown dataset
- **THEN** loading fails with an error naming the file and the problem

#### Scenario: Covers tied to the dataset
- **WHEN** a `bench` task has no `covers`, or a `jaffle` task has one
- **THEN** loading fails naming the file and `covers`

#### Scenario: Naive SQL tied to traps
- **WHEN** a task covering `chasm` has no `naive_sql`, or a task covering only rows has one
- **THEN** loading fails naming the file and `naive_sql`

#### Scenario: Profile-scoped xfail loads
- **WHEN** a task file has `xfail: {issue: DEV-1951, reason: ..., profiles: [motley, motley+python]}`
- **THEN** the task's xfail applies to `motley` and `motley+python` only

#### Scenario: New rows and pitfalls accepted
- **WHEN** a task covers `[Q26]`, and a trap covers `[Q27, null_element]` with `naive_sql`
- **THEN** both load

### Requirement: Prompts are capability-neutral
A task prompt MUST NOT name SLayer DSL features or syntax (for example `partition_by`, `time_shift`, `cumsum`,
`window=`, `rank(`, `refine`, `source_model`, `multi-stage`, `contains(`, `contains_any`, `contains_all`, `length(`,
`collect(`, `unnest`), nor hint at a pitfall's mechanism (for example `join`, `duplicate`, `double count`, `fan-out`,
`chasm`, `null`, `not in`, `counted once`, `count each`). Deny-list entries SHALL match as whole words or phrases,
case-insensitively, so that ordinary words containing them (such as `adjoining`) pass; an entry ending in `(` matches
only when the parenthesis follows. The check SHALL run over every committed task.

#### Scenario: Leaky prompt detected
- **WHEN** a task's prompt contains a DSL keyword or a pitfall hint from the deny list
- **THEN** the task-suite check fails naming that task and keyword

#### Scenario: Embedded word passes
- **WHEN** a prompt says "adjoining regions"
- **THEN** the check does not flag `join`

#### Scenario: List function syntax detected, prose passes
- **WHEN** one prompt says "customers where contains(tags, 'vip')" and another says "whose tag list contains vip, by length of stay"
- **THEN** the first is flagged for `contains(` and the second is not flagged

### Requirement: Row coverage
The committed `bench` task set SHALL contain at least one task covering each of Q1–Q18, Q20, Q21 and Q23–Q27, and
none covering Q19 or Q22; at least 12 trap tasks; and at least 2 tasks covering three or more rows. Tasks for Q21 and
Q24 SHALL exercise only what SLayer supports for those rows. Rows Q9 and Q18 SHALL include at least one refusal or
warning task. Row Q27 SHALL have tasks for membership of one value, of all of several values and of any of several
values; entities per element value; distinct elements per group; the element set per group; list length; and an
aggregate over the elements of a numeric list; combo tasks pairing it with a partitioned share, a time bucket with a
change from the previous period, a top N per element, and an entity-level measure next to an element aggregate; and
traps for each of `count_after_unnest`, `unnest_fan_out`, `null_element` and `same_element_and`. `jaffle` tasks SHALL
NOT count towards any of these.

#### Scenario: Coverage check
- **WHEN** the task suite is loaded
- **THEN** every covered row (including Q26 and Q27) has a `bench` task, Q19 and Q22 have none, Q9 and Q18 each have a task whose `expect` is an error or warning, there are at least 12 trap tasks, and at least 2 tasks cover three or more rows

#### Scenario: Uncovered new row detected
- **WHEN** a task set has no task covering Q27
- **THEN** the coverage check fails naming Q27

#### Scenario: Jaffle tasks outside coverage
- **WHEN** the coverage check runs over a task set holding `jaffle` tasks
- **THEN** it reports the same problems as over the `bench` tasks alone

### Requirement: Truth computation and snapshots
Truth SHALL be computed by running each task's `truth_sql` against the task's built dataset; truth values MUST NOT be
hand-typed. The build SHALL write a truth snapshot per task (columns and rows), committed to the repository, and a
check MUST fail when regenerated truth differs from the committed snapshot. Writing snapshots SHALL always cover every
loaded task of every dataset, so that it never removes the snapshot of a task that still exists. A truth result SHALL
have at most 20 rows unless the task deliberately tests result limiting.

#### Scenario: Snapshot drift detected
- **WHEN** the generator or a `truth_sql` changes so that a task's truth rows change
- **THEN** the snapshot check fails naming the task until the snapshot is regenerated explicitly

#### Scenario: Truth SQL error surfaces
- **WHEN** a task's `truth_sql` fails on its built dataset
- **THEN** truth computation fails naming the task and the database error

#### Scenario: Writing keeps every dataset's snapshots
- **WHEN** snapshots are written for a task set holding `bench` and `jaffle` tasks
- **THEN** there is exactly one snapshot per task of both datasets and the snapshot check then passes

### Requirement: Task suites
Each task SHALL belong to exactly one suite, derived and never stored: `jaffle` if its dataset is `jaffle`; otherwise
`trap` if it covers a pitfall kind, else `combo` if it covers two or more rows, else `capability`. Task files SHALL live
under `tasks/capability/`, `tasks/combo/`, `tasks/traps/` and `tasks/jaffle/` according to their suite.

#### Scenario: Suite derivation
- **WHEN** tasks covering `[Q4]`, `[Q2, Q4]` and `[Q6, fan_out]`, and a `jaffle` task, are loaded
- **THEN** their suites are `capability`, `combo`, `trap` and `jaffle`

#### Scenario: Misplaced file
- **WHEN** a task whose suite is `trap` sits under `tasks/combo/`, or a `jaffle` task sits outside `tasks/jaffle/`
- **THEN** the task-suite check fails naming the file

### Requirement: Task proofs
Every task's `slayer_query` SHALL be run through SLayer, in process, on the task's built store and database: for a
`match` task its result MUST match the truth under the task's `compare`; for an error or warning task it MUST raise or
warn with one of the expected kinds. Every `naive_sql` statement SHALL run on the built database, return a table whose
columns resolve against the truth's, and MUST NOT match the truth. For every covered row that has DSL markers (for
example Q2 and Q3 `partition_by`, Q4 `time_shift`, `cumsum` or `change`, Q11 `window=`, Q14 `rank(`, Q27 `contains`,
`.value`, `length(` or `collect(`), the `slayer_query` MUST contain one of that row's markers. Every `uses_saved` entry
MUST name a saved definition in the task's store template.

#### Scenario: Reference query answers the task
- **WHEN** the proofs run over the committed tasks
- **THEN** every `slayer_query` result, on its task's dataset, matches its truth or produces the expected kind

#### Scenario: Dead trap detected
- **WHEN** a trap's `naive_sql` returns the truth on the built database
- **THEN** the proof fails naming the task

#### Scenario: Mislabelled cover detected
- **WHEN** a task covers Q14 but its `slayer_query` contains no ranking marker
- **THEN** the proof fails naming the task and Q14

#### Scenario: List row without a list construct
- **WHEN** a task covers Q27 but its `slayer_query` uses none of `contains`, `.value`, `length(` or `collect(`
- **THEN** the proof fails naming the task and Q27

### Requirement: Jaffle tasks
The committed task set SHALL hold 24 `jaffle` tasks, one per question of Yann's nao-vs-Motley experiment (first set
q01–q12, complex set c01–c12), with ids `j-<question id>-<slug>` (for example `j-q01-stores`). Each prompt SHALL be
the question's text verbatim followed by an answer-shape sentence that fixes only the answer's rows, columns, units
and invented labels and states no business rule (no tax basis, data cut-off, money unit of the source data, new
customer or same-store definition). Each `truth_sql` SHALL be the question's reference SQL adapted only to that shape.
Each SHALL have a `slayer_query` answering it on the Jaffle store.

#### Scenario: All 24 questions present
- **WHEN** the task set is loaded
- **THEN** it holds exactly 24 `jaffle` tasks, one for each of q01–q12 and c01–c12

#### Scenario: Prompt starts with the verbatim question
- **WHEN** each `jaffle` task's prompt is compared with the source question text
- **THEN** the prompt begins with that text unchanged
