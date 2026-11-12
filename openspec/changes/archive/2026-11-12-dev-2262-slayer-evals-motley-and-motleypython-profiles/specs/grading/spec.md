## MODIFIED Requirements

### Requirement: Correctness criterion
For a `match` task, `correct` SHALL be true iff the submitted table matches the truth. For an error or warning task in
a SLayer or Motley profile, `correct` SHALL be true iff the submitted message contains at least one `message_any`
phrase (case-insensitive) and the trace contains a call that produced one of the expected error or warning kinds
(exception class for errors, warning `kind` for warnings). The exception class of an error result SHALL be read from
either the `Error executing tool <tool>: <Class>: ...` form or a result that starts with `<Class>: ...` where the class
name ends in `Error` or `Exception`. For an error or warning task in `sql+python`, `correct` SHALL be true iff the
submission has no rows and its message contains at least one `message_any` phrase.

#### Scenario: Right answer
- **WHEN** the submission equals the truth table
- **THEN** `correct` is true

#### Scenario: Refusal surfaced
- **WHEN** a warning task's submission message mentions a `message_any` phrase and the trace has the warning
- **THEN** `correct` is true

#### Scenario: Raw-SQL refusal
- **WHEN** in `sql+python` a warning task's submission has no rows and its message mentions a `message_any` phrase
- **THEN** `correct` is true, and it is false if the submission has rows

#### Scenario: Bare error class
- **WHEN** in `motley` an error task expects `TimeDimensionColumnError`, a call failed with `TimeDimensionColumnError: A time dimension must reference ...`, and the message mentions a `message_any` phrase
- **THEN** `correct` is true

#### Scenario: Labelled text is not an error class
- **WHEN** a failed call's result starts with `Invalid arguments: ...` or `SQL: ...`
- **THEN** no exception class is read from it

### Requirement: Single-query criterion
For a `match` task, `single_query` SHALL be true iff some successful call to SLayer's or Motley's `query` tool or to
the `sql` tool returns a result that itself matches the truth, so that the answer needed no combination of queries and
no post-processing. Which DSL features or SQL constructs that call uses is not checked: a task forces its intended
feature through its wording. For an error or warning task, `single_query` SHALL be true iff some call in the trace
returned one of the expected kinds in a SLayer or Motley profile, and SHALL equal `correct` in `sql+python`. Results
SHALL be parsed from markdown, a bare JSON array, a JSON object with `data` and `warnings`, a JSON object with
`columns` (names) and `rows` (lists), or a JSON object with `columns` (objects with a unique `name`) and `rows`
(records keyed by exactly those names); a truncation flag or a truncation footer SHALL become a `truncated` warning. A
JSON object matching none of these shapes SHALL not be parsed as a table.

#### Scenario: One query returns the answer
- **WHEN** a Q1 trace has a query whose result matches the truth
- **THEN** `single_query` is true, whatever functions the query uses

#### Scenario: One SQL statement returns the answer
- **WHEN** a `sql+python` trace has a `sql` call whose result matches the truth
- **THEN** `single_query` is true

#### Scenario: One Motley query returns the answer
- **WHEN** a `motley` trace has a `query` call whose JSON result, with column objects and records keyed `<model>.<column>`, matches the truth
- **THEN** `single_query` is true

#### Scenario: Answer combined from two queries
- **WHEN** the agent pulls per-city totals and per-region totals in two queries and submits the correctly combined table
- **THEN** `correct` is true and `single_query` is false

#### Scenario: Result parsing in both formats
- **WHEN** calls return markdown, a bare JSON array, a JSON object with `data` and `warnings`, a JSON object with `columns` and `rows`, Motley's JSON, or Motley's markdown with a SQL block, a footer and a trailing note
- **THEN** each is parsed into the same columns and rows for comparison

#### Scenario: Truncated Motley result
- **WHEN** a Motley result is marked truncated, in JSON or by its markdown footer
- **THEN** the parsed result carries a `truncated` warning

#### Scenario: Malformed Motley result
- **WHEN** a Motley JSON result has a column object without a name, two columns with one name, or a record missing a column's key
- **THEN** it is not parsed as a table

### Requirement: Trace flags
The verdict SHALL carry informational booleans that do not affect `passed`: `used_python` (any call to the Python
tool), `raw_sql` (any `sql` call, or any SQL-bearing argument of a SLayer or Motley tool: a model's or column's `sql`, a
column `filter`, an aggregation formula, model filters, or SQL inside an inline `source_model`), `edited_models` (any
`create_model` or `edit_model` call), `query_errors` and `several_queries` (more than one `query` or `sql` call).
`query_errors` SHALL be true iff a data tool call returned an error, where the data tools are every SLayer tool in the
SLayer profiles, the `sql` tool in `sql+python`, and Motley's `query`, `inspect`, `search`, `create_model`,
`edit_model`, `delete`, `save_memory` and `switch_branch` in the Motley profiles.

#### Scenario: Flags from a trace
- **WHEN** a trace has two `query` calls, one failed, a `create_model` with `sql`, and a Python call
- **THEN** `several_queries`, `query_errors`, `edited_models`, `raw_sql` and `used_python` are all true, and `passed` depends only on `correct` and `single_query`

#### Scenario: Flags from a raw-SQL trace
- **WHEN** a `sql+python` trace has two `sql` calls, one failed
- **THEN** `raw_sql`, `query_errors` and `several_queries` are true and `edited_models` is false

#### Scenario: Motley product-tool errors are not query errors
- **WHEN** a `motley` trace has a failed `create_document` call and no other failed call
- **THEN** `query_errors` is false, and it is true when an `inspect` or `query` call fails instead
