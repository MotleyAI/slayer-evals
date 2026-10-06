## Purpose

Scores one trial deterministically on answer correctness, use of the intended SLayer capability, and absence of hacks,
from the task, its truth, the initial store manifest, the agent's submission and its normalized trace.

## ADDED Requirements

### Requirement: Deterministic, self-contained verdict
A verdict SHALL be a function of (task, truth, store manifest, submission, trace) only: no file, network or database
access, no agent or SDK objects. It SHALL report three booleans — `correct`, `capability`, `no_hack` — each with
human-readable reasons, and `passed` = all three. A trial without a submission MUST fail all three with reason
`no submission`.

#### Scenario: Same inputs, same verdict
- **WHEN** a verdict is computed twice from identical inputs
- **THEN** the two verdicts are equal

#### Scenario: Missing submission
- **WHEN** the trace ends without a submission
- **THEN** `correct`, `capability` and `no_hack` are false and the reasons say `no submission`

### Requirement: Table comparison
Two tables SHALL match when, after column resolution, the key and value columns' rows are equal as multisets
(or as sequences when `ordered`), with numeric values equal within `tolerance`, NULL equal only to NULL, NaN treated
as NULL, and dates and timestamps compared after normalization to ISO form. Column resolution SHALL map each truth
column to a result column by exact name, else by `.name` suffix, else by a flattened `a__b` form; a truth column that
resolves by name to more than one column MUST make the match fail with a reason naming it. Truth columns that resolve
by name to no column SHALL be matched by values: the tables match if some one-to-one assignment of those truth columns
to the result columns not already used makes the rows match, preferring, when several do, the assignment whose result
column names are closest to the truth names; if none does, the match fails with a reason naming those columns. A
successful match SHALL record the column mapping it used, and the verdict SHALL carry the mappings of its correctness
and capability matches. Extra result columns SHALL be ignored unless `columns_exact`. The row counts MUST be equal.

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

### Requirement: Correctness criterion
For a `match` task, `correct` SHALL be true iff the submitted table matches the truth. For an error or warning task,
`correct` SHALL be true iff the submitted message contains at least one `message_any` phrase (case-insensitive) and
the trace contains a call that produced that error or warning kind (see the capability criterion).

#### Scenario: Right answer
- **WHEN** the submission equals the truth table
- **THEN** `correct` is true

#### Scenario: Refusal surfaced
- **WHEN** a warning task's submission message mentions a `message_any` phrase and the trace has the warning
- **THEN** `correct` is true

### Requirement: Capability criterion
For a `match` task, `capability` SHALL be true iff some successful SLayer `query` call in the trace both satisfies
the task's capability predicates and returns a result that itself matches the truth. Predicates SHALL be evaluated on
the query as parsed by SLayer's own expression parser, after expanding saved measures from the store manifest and from
measures the agent saved earlier in the trace. Predicates SHALL support: a function call, optionally with a named
keyword argument (e.g. `sum` with `partition_by`); a list-valued multi-stage query whose later stages reference
earlier named stages; a run of a saved query by name with `refine`; ordering by a column not selected; an inline
`source_model` extension; a relative or typed time filter; and an ordered trace pattern (e.g. a `create_model` from a
query followed by a `query` on that model). `any_of` SHALL accept alternative predicate sets. For an error or warning
task, `capability` SHALL be true iff the trace contains a call whose arguments satisfy the task's predicates and that
returned the expected kind (exception class for errors, warning `kind` for warnings).

#### Scenario: Capability used, result right
- **WHEN** a Q1 trace has a query with `sum(amount, partition_by=region)` whose result matches the truth
- **THEN** `capability` is true

#### Scenario: Right answer without the capability
- **WHEN** the agent pulls per-city totals and per-region totals in two queries and submits the correctly combined table
- **THEN** `correct` is true and `capability` is false with a reason naming the unmet predicate

#### Scenario: Saved measure hides the composition
- **WHEN** a Q17 query uses saved measure `aov` inside `cumsum(aov)` and the manifest defines `aov`
- **THEN** the predicate requiring a transform over the saved measure is evaluated on the expansion and is satisfied

#### Scenario: Multi-stage query
- **WHEN** a Q15 trace has a list-valued query whose second stage selects from the first stage by name, with the right result
- **THEN** `capability` is true; a single-stage query with the same result does not satisfy it

#### Scenario: Wrong-call refusal does not count
- **WHEN** a Q18 trace's only error is a granularity error from a query unrelated to the task's predicates
- **THEN** `capability` is false

#### Scenario: Result parsing in both formats
- **WHEN** qualifying calls return markdown, a bare JSON array, or a JSON object with `data` and `warnings`
- **THEN** each is parsed into the same columns and rows for comparison

### Requirement: No-hack criterion
`no_hack` SHALL be false when any tool call in the trace supplies raw SQL — in `create_model`'s `sql`, a column's
`sql` in `create_model` or `edit_model`, an inline `source_model` column, or any other SQL-bearing argument of a SLayer
tool — unless the task's `allow` exempts that specific construct; an exemption for row-level scalar SQL MUST still
reject aggregates, window functions and subqueries. In the `slayer+python` profile, `no_hack` SHALL also be false when
the Python tool's audit log shows a file opened outside its sandbox directory (other than the interpreter's own
installation), or the code imports or calls `duckdb` or `sqlite3`, or references the database file path.

#### Scenario: Raw aggregate SQL in a model
- **WHEN** the agent calls `create_model` with `sql` containing `GROUP BY`
- **THEN** `no_hack` is false with a reason naming the call

#### Scenario: Allowed scalar inline column
- **WHEN** a Q16 task allows row-level scalar inline SQL and the agent adds an inline column `amount * 1.1`
- **THEN** `no_hack` is true; an inline column with `sum(amount) over ()` makes it false

#### Scenario: Python opens the database
- **WHEN** in the `slayer+python` profile the Python tool runs `duckdb.connect('<db path>')`
- **THEN** `no_hack` is false

#### Scenario: Python reads benchmark files
- **WHEN** the Python tool's audit log shows an open of a task or truth file
- **THEN** `no_hack` is false
