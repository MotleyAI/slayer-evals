# benchmark-tasks Specification

## Purpose
Defines what a benchmark task is — a business question with machine-checkable truth, worded so that one SLayer query
using the row's capability answers it — and how tasks are loaded and their truth computed and pinned.

## Requirements

### Requirement: Task file format
Each task SHALL be one YAML file with: `id` (unique), `row` (one of Q1–Q18, Q20, Q21, Q23–Q25), `prompt` (a natural
language business question), `truth_sql` (DuckDB SQL over the built dataset), `compare` (`keys`, `values`,
`tolerance` default 1e-6, `ordered` default false, `columns_exact` default false), `expect` (`match` by default, or
`{error: <kind or list of kinds>, message_any: [...]}` / `{warning: <kind or list of kinds>, message_any: [...]}`), and optional `xfail` (an issue key
with a reason). Loading MUST reject a file with an unknown key, a missing required key, a duplicate id, or a row
outside the covered set.

#### Scenario: Valid task loads
- **WHEN** a well-formed task file is loaded
- **THEN** it yields a task whose fields equal the file's values, with defaults applied

#### Scenario: Malformed task rejected
- **WHEN** a task file has an unknown key, lacks `truth_sql`, reuses another task's id, or names row Q19 or Q22
- **THEN** loading fails with an error naming the file and the problem

### Requirement: Prompts are capability-neutral
A task prompt MUST NOT name SLayer DSL features or syntax (for example `partition_by`, `time_shift`, `cumsum`,
`window=`, `rank(`, `refine`, `source_model`, `multi-stage`). The check SHALL run over every committed task.

#### Scenario: Leaky prompt detected
- **WHEN** a task's prompt contains a DSL keyword from the deny list
- **THEN** the task-suite check fails naming that task and keyword

### Requirement: Row coverage
The committed task set SHALL contain at least one task for each of Q1–Q18, Q20, Q21, Q23, Q24 and Q25, and none for
Q19 or Q22. Tasks for Q21 and Q24 SHALL exercise only what SLayer supports for those rows. Rows Q9 and Q18 SHALL
include at least one refusal or warning task.

#### Scenario: Coverage check
- **WHEN** the task suite is loaded
- **THEN** every covered row has at least one task, Q19 and Q22 have none, and Q9 and Q18 each have a task whose `expect` is an error or warning

### Requirement: Truth computation and snapshots
Truth SHALL be computed by running each task's `truth_sql` against the built dataset; truth values MUST NOT be
hand-typed. The build SHALL write a truth snapshot per task (columns and rows), committed to the repository, and a
check MUST fail when regenerated truth differs from the committed snapshot. A truth result SHALL have at most 20 rows
unless the task deliberately tests result limiting.

#### Scenario: Snapshot drift detected
- **WHEN** the generator or a `truth_sql` changes so that a task's truth rows change
- **THEN** the snapshot check fails naming the task until the snapshot is regenerated explicitly

#### Scenario: Truth SQL error surfaces
- **WHEN** a task's `truth_sql` fails on the built dataset
- **THEN** truth computation fails naming the task and the database error
