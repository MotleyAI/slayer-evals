## Why

SLayer's DSL can express partitioned aggregates, re-aggregation, transforms, rolling windows, ranking, multi-stage
queries and more, but nothing measures whether an agent handed SLayer's MCP server actually reaches for those
features instead of pulling raw rows and post-processing them. This change builds that measurement as a standalone,
public, agent-agnostic benchmark (`MotleyAI/slayer-evals`, MIT), so failures can be traced to the MCP surface and
fixed there.

## What Changes

- New Python project `slayer_evals` (Poetry, Python ≥3.12) with ruff, basedpyright, pytest (live agent runs marked
  `integration`) and a GitHub Actions workflow for lint, type check and unit tests.
- A seeded, deterministic dataset generator reproducing the schema and edge cases of SLayer's comparison probe
  dataset at realistic size, plus a SLayer store template (datasource, models, saved measures and queries).
- Task files for matrix rows Q1–Q18, Q20, Q21, Q23–Q25 (Q19 and Q22 out of scope; Q21 and Q24 limited to their
  supported subset), each with truth SQL, comparison rules, capability predicates, hack-rule allowances and an
  optional xfail issue; committed truth snapshots generated from the built database.
- A rule-based grader scoring each trial on (a) answer correctness, (b) use of the intended capability by a SLayer
  query whose own result matches the truth, and (c) absence of hacks (raw-SQL escape hatches, direct database
  access from Python, reads of benchmark files).
- An agent-agnostic adapter contract (`Submission` + normalized `Trace`) and a hermetic Claude Agent SDK adapter with
  two profiles: `slayer` (SLayer MCP + `submit_answer`) and `slayer+python` (adds a sandboxed Python tool).
- A runner and CLI: task/row/profile/model selection, `repeat` and `until-pass` modes with N trials, concurrency,
  explicit auth mode and env file, per-trial isolation, results, traces and a markdown report.
- The living-architecture model (`architecture/`) for the new package, and `architecture: true` in the repo config.
- A welcoming README and a committed single-trial baseline (Opus 5.5, both profiles).

## Capabilities

### New Capabilities
- `benchmark-dataset`: deterministic generator, planted edge cases, built DuckDB and SLayer store template.
- `benchmark-tasks`: task file format, task loading, truth computation and truth snapshots.
- `grading`: correctness, capability and hack verdicts over a submission and a normalized trace.
- `agent-harness`: the adapter contract and the hermetic Claude Agent SDK adapter with its two profiles.
- `benchmark-runs`: run selection, run modes, per-trial isolation, auth, concurrency and result files.
- `benchmark-report`: the markdown report and the committed baseline.

### Modified Capabilities

## Impact

- New repository content only; no existing code changes.
- Dependencies: `motley-slayer` (exact pin; its parser is used by the grader), `claude-agent-sdk` (pinned), `duckdb`,
  `pydantic`, `pyyaml`; pandas and numpy for the Python sandbox profile.
- Relative-date tasks depend on SLayer pinning "now" (DEV-2058) and stay xfail until a release has it.
- Running the benchmark needs Claude credentials (subscription OAuth token or API key) supplied via an env file.
