## 1. Project scaffold

- [ ] 1.1 Create `pyproject.toml` (Poetry, Python ≥3.12, package `slayer_evals` under `src/`, exact pins for `motley-slayer==1.0.2` and `claude-agent-sdk`, plus duckdb, pydantic, pyyaml, pandas, numpy), ruff and basedpyright config, pytest config with an `integration` marker excluded by default and `asyncio_mode = "auto"`; verify `poetry install` and `poetry run pytest -m "not integration"` run
- [ ] 1.2 Add `.gitignore` (`.env*`, `runs/`, build outputs) and a GitHub Actions workflow running ruff, basedpyright and the non-integration tests; verify the workflow file parses (`actionlint` or a YAML load) and the same commands pass locally

## 2. Architecture model (every model, `index.yaml` and arc42 edit needs the user's OK on the exact text before it lands)

- [ ] 2.1 Write `architecture/index.yaml` (python section: `root_package: slayer_evals`, `source_root: src`; `legacy_arrows: {baseline: 0}`), `architecture/model/specification.c4`, `architecture/model/slayer_evals.c4` with the eight nodes, arrows and `specs:` per design.md, and `architecture/views.c4`; verify `npx likec4 validate` (or the lightest parsing command) passes
- [ ] 2.2 Write `architecture/system.arc42.md` with the six principles from design.md, each status-tagged; verify `la-arch-diagrams` embeds fresh diagrams and `la-arch-check` passes once the packages exist
- [ ] 2.3 Set `architecture: true` in `living-architecture.yaml` once `la-arch-check` passes; verify `la-doctor --require-config` passes

## 3. Core schemas

- [ ] 3.1 Implement `core` pydantic models (task, compare, predicates incl. `any_of` and trace patterns, allowances, expectations, store manifest, submission, tool call, trace, usage, verdict, trial result, run metadata); verify JSON round-trip tests pass

## 4. Dataset

- [ ] 4.1 Implement the seeded generator and DuckDB build with the probe schema and planted edge cases; verify the determinism, different-seed, schema and edge-case invariant tests pass
- [ ] 4.2 Implement the store template (datasource `bench` with `fiscal_year` and `quarter_hour`, models adapted from the probe suite, saved measures and queries, help memories) and the manifest; verify a SLayer MCP server on a copy lists the datasource and models and answers a query, and the manifest test passes

## 5. Tasks

- [ ] 5.1 Implement task loading and validation (unknown/missing keys, duplicate ids, row set); verify the task-format tests pass
- [ ] 5.2 Implement truth computation and snapshot write/compare; verify snapshot-drift and truth-SQL-error tests pass
- [ ] 5.3 Implement the suite checks (row coverage, Q9/Q18 refusal tasks present, prompt DSL deny-list, truth ≤20 rows unless flagged); verify they run over the committed task set

## 6. Grading

- [ ] 6.1 Implement result parsing (markdown, JSON array, JSON object with `data`/`warnings`) and table comparison (column resolution with ambiguity failure, multiset/ordered, tolerance, NULL/NaN, dates, row counts); verify table-driven tests including fixtures captured from real MCP responses
- [ ] 6.2 Implement capability predicates on SLayer-parsed queries, saved-measure expansion (manifest + in-trace), multi-stage, saved query + refine, unselected order, inline extension, time filters, ordered trace patterns, `any_of`, and refusal matching; verify per-predicate tests, parser fixture tests and adversarial traces
- [ ] 6.3 Implement hack rules (default-deny raw SQL with construct-specific allowances; Python audit-log and static checks) and the verdict; verify adversarial tests (CTEs, comments, quoted functions, windows, subqueries, query-backed models, file reads)

## 7. Agents

- [ ] 7.1 Implement the adapter protocol and trace normalization from SDK messages (tool calls, parsed query results, errors, usage from the final result message with partial fallback, end reasons); verify tests on recorded SDK message fixtures
- [ ] 7.2 Implement the hermetic Claude session (empty config dir, no built-ins, no settings sources, profile MCP servers, leak check, telemetry and caching env, sanitized SLayer env, generic system prompt) with `submit_answer`; verify unit tests for option construction, env sanitization, leak abort and ragged-submission rejection
- [ ] 7.3 Implement the Python sandbox tool (subprocess, temp cwd, env allow-list, rlimits, timeout, audit hook log) for `slayer+python`; verify tests for audit logging of outside opens, timeout and env contents
- [ ] 7.4 Live smoke test (integration): one Q1 task in each profile via the real SDK and SLayer; verify a trace, a submission and a verdict are produced

## 8. Runner and CLI

- [ ] 8.1 Implement trial isolation (fresh DB and store copies per trial, one process per trial, concurrency limit), selection (ids, rows, profiles, models), run modes `repeat` and `until-pass`, budgets and SLayer command override; verify tests with a fake agent covering both modes and isolation
- [ ] 8.2 Implement explicit auth mode and `--env-file` handling; verify refusal-to-start tests for missing mode and missing credential
- [ ] 8.3 Implement run output (per-trial results lines written as trials finish, traces, transcripts, metadata) and the CLI commands (`build`, `run`, `report`, `truth`); verify an end-to-end fake-agent run produces the expected files

## 9. Report

- [ ] 9.1 Implement the markdown report (metadata, per-row × profile tables, repeat vs until-pass statistics, xfail section, totals, failure digests, Q19/Q22 not covered, single-trial label); verify tests from synthetic results and byte-identical regeneration

## 10. Tasks: pilot, then full set

- [ ] 10.1 Author pilot tasks (Q1, Q4, Q15, Q18) with truth snapshots; run them live in both profiles (Opus 5.5, N=1, `--subscription-auth --env-file /home/james/GitHub/SLayer/.env.agents`); fix the format or grader if the pilots expose a problem (raise any plan change with the user first); verify each pilot's verdict reasons are sensible from the report
- [ ] 10.2 Author the remaining tasks for every covered row per the design catalogue, adapting each row's probes; relative-date tasks `xfail: DEV-2058`; verify the suite checks and snapshot tests pass

## 11. Baseline and README

- [ ] 11.1 Run the full baseline (all tasks, both profiles, Opus 5.5, N=1, `--subscription-auth --env-file /home/james/GitHub/SLayer/.env.agents`) and commit `results/baseline/` (report, results, normalized traces); verify the report regenerates byte-identically from the committed results
- [ ] 11.2 Write a welcoming README: what the benchmark measures and why, covered-row table, five-minute quickstart (incl. `claude setup-token` and the env file), reading the report, the baseline summary (labelled a single-trial snapshot), plugging in your own agent, adding a task, why Q19 and Q22 are skipped, link to the comparison post, licence; verify every command in the quickstart runs as written

## 12. Gates

- [ ] 12.1 Run the full non-integration suite, ruff, basedpyright, `la-arch-check` and `openspec validate dev-2055-slayer-evals-capability-benchmark-do-agents-actually-reach --strict`; verify all pass
