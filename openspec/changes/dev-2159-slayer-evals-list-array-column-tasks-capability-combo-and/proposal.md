## Why

SLayer 1.7.0 supports list (array) columns: `contains`, `contains_any`, `contains_all` and `length` over a list,
element access through `L.value`, and the `collect` aggregation. The benchmark has no task that needs them. So nobody
measures whether agents answer "how many customers have tag x" or "customers with both x and y" with one SLayer query,
or whether naive SQL over lists silently returns wrong numbers. The matrix's row Q26 (metrics without a join path) is
also uncovered.

## What Changes

- Dataset: `customers.tags VARCHAR[]` and `products.ratings INTEGER[]`, filled from their own seeded streams and
  holding a repeated element, a NULL element, an empty list and a NULL list. The probe freeze covers the probe
  columns, so no existing value or truth moves.
- Rows Q1–Q27: Q26 "Metrics without a join path" and Q27 "List columns" become covered rows. Q27 gets row markers;
  the prompt deny-list gains the list DSL names.
- Four new pitfall kinds: `count_after_unnest`, `unnest_fan_out`, `null_element` and `same_element_and`.
- 17 new tasks: 8 Q27 capability tasks, 1 Q26 capability task, 4 Q27 combo tasks (one also covering Q14 and Q15) and
  4 traps.
- Grading: a list cell compares as the set of its non-NULL elements (numbers within tolerance); JSON-list or
  comma-separated text matches a list truth column.
- Results: every results line carries its SLayer version; the report lists the versions when a results file mixes
  them. **BREAKING** for results files written before this change: they lack `slayer_version` until backfilled.
- `motley-slayer` pinned to the PyPI release 1.7.0 (replacing the git rev). The baseline gains the new tasks in all three
  profiles, run on that pin; README and the baseline failure breakdown are updated.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities
- `benchmark-dataset`: list columns and their edge cases; the probe freeze and layout cover the probe columns.
- `benchmark-tasks`: covered rows Q1–Q27 with Q26 and Q27; new pitfall kinds; Q27 markers; list DSL in the deny-list.
- `grading`: list-valued cells compare as sets of normalized elements.
- `benchmark-runs`: each results line records the SLayer version.
- `benchmark-report`: rows Q1–Q27; per-version trial counts; a baseline may combine runs.

## Impact

- Code: `src/slayer_evals/dataset/generator.py`, `dataset/models/customers.yaml` and `products.yaml`,
  `core/task.py`, `core/results.py`, `tasks/suite.py`, `grading/tables.py`, `runner/run.py` and `report/render.py`.
- Tasks: 17 new task files under `tasks/`, plus their truth snapshots.
- Tests: `test_dataset.py`, `test_core_schemas.py`, `test_task_format.py`, `test_task_suite.py`,
  `test_table_compare.py`, `test_runner.py`, `test_report.py` and fixtures (`probe_table_hashes.json` unchanged;
  `run_repeat/results.jsonl` backfilled).
- Dependencies: `pyproject.toml` / `poetry.lock` (`motley-slayer` rev).
- Docs and results: `README.md`, `docs/baseline-failures.md` and `results/baseline/`.
- Coordination: the DEV-2065 worktree's uncommitted `q6-events-per-customer` duplicates the new
  `q26-events-per-customer`; the duplicate task id makes loading fail until one copy is dropped.
