# grading Specification

## Purpose
Scores one trial deterministically on two questions — is the answer correct, and is it exactly the result of a single
SLayer query — and records informational flags about the trace, from the task, its truth, the agent's submission and
its normalized trace.

## Requirements

### Requirement: Deterministic, self-contained verdict
A verdict SHALL be a function of (task, truth, submission, trace) only, where the trace carries the trial's profile:
no file, network or database access, no agent or SDK objects. It SHALL report two booleans — `correct` and
`single_query` — each with human-readable reasons, and `passed` = both. A trial without a submission MUST fail both with
reason `no submission`. In profile `sql+python`, a task that names a saved SLayer definition (`uses_saved`) MUST fail
both with a reason naming the definitions, whatever the trace holds.

#### Scenario: Same inputs, same verdict
- **WHEN** a verdict is computed twice from identical inputs
- **THEN** the two verdicts are equal

#### Scenario: Missing submission
- **WHEN** the trace ends without a submission
- **THEN** `correct` and `single_query` are false and the reasons say `no submission`

#### Scenario: Saved definition auto-fails raw SQL
- **WHEN** a task with `uses_saved: [monthly_rev]` is graded for profile `sql+python`
- **THEN** `correct` and `single_query` are false and the reasons name `monthly_rev`

### Requirement: Table comparison
Two tables SHALL match when, after column resolution, the key and value columns' rows are equal as multisets
(or as sequences when `ordered`), with numeric values equal within `tolerance`, NULL equal only to NULL (or, when the
task sets `null_as_zero`, NULL also equal to 0 in value columns), NaN treated as NULL, and dates and timestamps compared
after normalization to ISO form. Column resolution SHALL map each truth column to a result column by exact name, else
by `.name` suffix, else by a flattened `a__b` form; a truth column that resolves by name to more than one column MUST
make the match fail with a reason naming it. Truth columns that resolve by name to no column SHALL be matched by values:
the tables match if some one-to-one assignment of those truth columns to the result columns not already used makes the
rows match, preferring, when several do, the assignment whose result column names are closest to the truth names; if
none does, the match fails with a reason naming those columns. A successful match SHALL record the column mapping it
used, and the verdict SHALL carry the mappings of its correctness and single-query matches. Extra result columns SHALL
be ignored unless `columns_exact`. The row counts MUST be equal.

#### Scenario: Order-insensitive match with tolerance
- **WHEN** a result has the truth rows in a different order and a value off by 1e-9
- **THEN** the tables match

#### Scenario: Ambiguous column fails
- **WHEN** truth column `name` matches both `customers.name` and `regions.name` in the result
- **THEN** the match fails with a reason naming `name` as ambiguous

#### Scenario: Columns matched by values
- **WHEN** a result names its columns `orders.customers.regions.name` and `orders.rev` for truth columns `region` and `revenue`, with matching rows
- **THEN** the tables match and the recorded mapping is `region` → `orders.customers.regions.name`, `revenue` → `orders.rev`

#### Scenario: Truncated result fails
- **WHEN** a result holds 20 of the truth's 25 rows
- **THEN** the tables do not match and the reason gives both row counts

#### Scenario: Ordered task
- **WHEN** a task sets `ordered` and the result has the right rows in the wrong order
- **THEN** the tables do not match

#### Scenario: NULL as zero
- **WHEN** the truth has NULL revenue for a month and the result has 0
- **THEN** the tables match if the task sets `null_as_zero`, and do not match otherwise

### Requirement: Correctness criterion
For a `match` task, `correct` SHALL be true iff the submitted table matches the truth. For an error or warning task in
a SLayer profile, `correct` SHALL be true iff the submitted message contains at least one `message_any` phrase
(case-insensitive) and the trace contains a call that produced one of the expected error or warning kinds (exception
class for errors, warning `kind` for warnings). For an error or warning task in `sql+python`, `correct` SHALL be true
iff the submission has no rows and its message contains at least one `message_any` phrase.

#### Scenario: Right answer
- **WHEN** the submission equals the truth table
- **THEN** `correct` is true

#### Scenario: Refusal surfaced
- **WHEN** a warning task's submission message mentions a `message_any` phrase and the trace has the warning
- **THEN** `correct` is true

#### Scenario: Raw-SQL refusal
- **WHEN** in `sql+python` a warning task's submission has no rows and its message mentions a `message_any` phrase
- **THEN** `correct` is true, and it is false if the submission has rows

### Requirement: Single-query criterion
For a `match` task, `single_query` SHALL be true iff some successful call to SLayer's `query` tool or to the `sql` tool
returns a result that itself matches the truth, so that the answer needed no combination of queries and no
post-processing. Which DSL features or SQL constructs that call uses is not checked: a task forces its intended feature
through its wording. For an error or warning task, `single_query` SHALL be true iff some call in the trace returned one
of the expected kinds in a SLayer profile, and SHALL equal `correct` in `sql+python`. Results SHALL be parsed from
markdown, a bare JSON array, a JSON object with `data` and `warnings`, or a JSON object with `columns` and `rows`.

#### Scenario: One query returns the answer
- **WHEN** a Q1 trace has a query whose result matches the truth
- **THEN** `single_query` is true, whatever functions the query uses

#### Scenario: One SQL statement returns the answer
- **WHEN** a `sql+python` trace has a `sql` call whose result matches the truth
- **THEN** `single_query` is true

#### Scenario: Answer combined from two queries
- **WHEN** the agent pulls per-city totals and per-region totals in two queries and submits the correctly combined table
- **THEN** `correct` is true and `single_query` is false

#### Scenario: Result parsing in both formats
- **WHEN** calls return markdown, a bare JSON array, a JSON object with `data` and `warnings`, or a JSON object with `columns` and `rows`
- **THEN** each is parsed into the same columns and rows for comparison

### Requirement: Trace flags
The verdict SHALL carry informational booleans that do not affect `passed`: `used_python` (any call to the Python
tool), `raw_sql` (any `sql` call, or any SQL-bearing argument of a SLayer tool: a model's or column's `sql`, a column
`filter`, an aggregation formula, model filters, or SQL inside an inline `source_model`), `edited_models` (any
`create_model` or `edit_model` call), `query_errors` (any SLayer tool or `sql` call that returned an error) and
`several_queries` (more than one `query` or `sql` call).

#### Scenario: Flags from a trace
- **WHEN** a trace has two `query` calls, one failed, a `create_model` with `sql`, and a Python call
- **THEN** `several_queries`, `query_errors`, `edited_models`, `raw_sql` and `used_python` are all true, and `passed` depends only on `correct` and `single_query`

#### Scenario: Flags from a raw-SQL trace
- **WHEN** a `sql+python` trace has two `sql` calls, one failed
- **THEN** `raw_sql`, `query_errors` and `several_queries` are true and `edited_models` is false
