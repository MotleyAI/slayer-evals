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
issue key with a reason, and optionally the `profiles` it applies to; without `profiles` it applies to every profile).
The pitfall kinds SHALL be the closed list `fan_out`, `count_after_join`, `chasm`, `bridge`, `non_unique_key`,
`outer_join_filter`, `not_in_null`, `count_outer_join`, `filtered_total`, `distinct_reagg`, `missing_periods`,
`filter_before_window`, `rows_window_gap`, `timestamp_bounds`, `avg_of_avgs`, `bucket_reaggregation`. Loading MUST
reject a file with an unknown key, a missing required key, a duplicate id, an unknown or repeated `covers` entry, a
`covers` without a row, row Q19 or Q22, a trap without `naive_sql`, `naive_sql` on a task that is not a trap, or an
`xfail` naming an unknown profile.

#### Scenario: Valid task loads
- **WHEN** a well-formed task file is loaded
- **THEN** it yields a task whose fields equal the file's values, with defaults applied

#### Scenario: Malformed task rejected
- **WHEN** a task file has an unknown key, lacks `truth_sql` or `slayer_query`, reuses another task's id, covers Q19 or Q22, covers only pitfalls, repeats a `covers` entry, names an unknown pitfall, or has an `xfail` naming an unknown profile
- **THEN** loading fails with an error naming the file and the problem

#### Scenario: Naive SQL tied to traps
- **WHEN** a task covering `chasm` has no `naive_sql`, or a task covering only rows has one
- **THEN** loading fails naming the file and `naive_sql`

#### Scenario: Profile-scoped xfail loads
- **WHEN** a task file has `xfail: {issue: DEV-1951, reason: ..., profiles: [motley, motley+python]}`
- **THEN** the task's xfail applies to `motley` and `motley+python` only
