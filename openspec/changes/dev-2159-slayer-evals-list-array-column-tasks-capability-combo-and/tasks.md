## 1. SLayer pin

- [x] 1.1 Replace the git dependency in `pyproject.toml` with `motley-slayer = "1.7.0"` from PyPI and update
  `poetry.lock`. Verify: `poetry install` succeeds and `importlib.metadata.version("motley-slayer")` is `1.7.0`.
- [x] 1.2 Pin compatibility gate, before any other change: run the full non-integration suite (including
  `tests/test_task_proofs.py` over the committed tasks), ruff and basedpyright on 1.7.0. Verify: all green. A failing
  pre-existing test or reference is a suspected gap: STOP and ask the user, never adapt it silently.

## 2. Tests first (pr-tests stage)

- [x] 2.1 `tests/test_core_schemas.py` and `tests/test_task_format.py`:
  - the row range is Q1–Q27;
  - Q26 and Q27 are accepted, and Q28 is rejected;
  - the four new pitfall kinds are accepted, and a trap covering `[Q27, null_element]` loads.

  Verify: the new tests fail before implementation.
- [x] 2.2 `tests/test_task_suite.py`:
  - coverage fails without a Q27 task;
  - the Q27 marker check;
  - deny-list entries `contains(`, `contains_any`, `contains_all`, `length(`, `collect(` and `unnest`;
  - "contains" and "length" in prose pass.

  Verify: the new tests fail before implementation.
- [x] 2.3 `tests/test_table_compare.py`, for every scenario of the grading delta:
  - list sets with order, repeats and NULL elements;
  - JSON and comma text against a list truth column;
  - text outside list columns stays text;
  - NULL ≠ `[]`;
  - numeric elements within and outside tolerance.

  Verify: the new tests fail before implementation.
- [x] 2.4 `tests/test_dataset.py`:
  - the probe hash is computed over the probe columns, and `probe_table_hashes.json` stays unchanged;
  - the layout check covers the probe columns plus `customers.tags`;
  - list edge-case invariants for `customers.tags` and `products.ratings`: a repeated element, a NULL element next to
    non-NULL ones, an empty list, a NULL list, and both `vip` and `eu`;
  - different seeds give different tags and ratings;
  - the store's list columns are usable.

  Verify: the new tests fail before implementation.
- [x] 2.5 `tests/test_runner.py` and `tests/test_report.py`:
  - every results line carries `slayer_version`;
  - a line without it fails loading;
  - the report lists mixed versions with their trial counts;
  - the per-row table has rows Q26 and Q27 with their names.

  Verify: the new tests fail before implementation.
- [x] 2.6 Write the 17 task files from the design's task table, each with a capability-neutral prompt, `truth_sql`
  spelling out the SLayer list semantics (non-NULL elements; NULL list ≠ empty list), `slayer_query`, `compare`, and
  `naive_sql` on traps. Verify: `test_task_format` loads them; the proofs fail only for lack of the dataset columns.
  The two task-specific shapes:
  - `c-top-customers-per-tag` covers `[Q27, Q14, Q15]` with the two-stage reference (stage 1: `customers.tags.value`,
    `customers.id` and `customers.name` (names are not unique), `sum(amount)`, `to_many_handling: associate`; stage 2: `rank(..., partition_by=
    customers__tags__value, direction='desc') <= 2`; the stage-2 measure name must not equal a stage column). It
    carries a one-line comment naming DEV-1932 as the future single-stage fix.
  - `q27-region-tag-set` asks for every region, so Arctic gets `[]`, and its reference sources `regions` with
    `collect(customers.tags.value)`.
- [x] 2.7 Backfill each fixture's own metadata version (`"slayer_version": "1.0.2"`) into
  `tests/fixtures/run_repeat/results.jsonl` and `tests/fixtures/run_until_pass/results.jsonl` (and any other committed
  results fixture). Verify: the fixtures load once the field exists.

## 3. Implementation (pr-implement stage)

- [x] 3.1 Generator:
  - `customers.tags VARCHAR[]` from stream `customer_tags`;
  - `products.ratings INTEGER[]` from stream `product_ratings`;
  - deterministic witnesses on fixed existing ids.

  Verify: 2.4 passes, and every pre-existing truth snapshot is byte-identical (`slayer-evals truth` without `--write`
  reports no drift for old tasks).
- [x] 3.2 Store models: `customers.yaml` gets `tags` (`type: ARRAY`, `element_type: TEXT`), and `products.yaml` gets
  `ratings` (`type: ARRAY`, `element_type: INT`), in uppercase because 1.7.0 rejects lowercase. Verify: the
  store-template list-column scenario passes.
- [x] 3.3 `core/task.py`, `tasks/suite.py` and `report/render.py`: the row range, the pitfall kinds, the Q27 markers,
  the deny-list, and the Q26/Q27 row names. Verify: 2.1, 2.2 and the row part of 2.5 pass.
- [x] 3.4 `grading/tables.py`: list-cell normalization and matching per the grading delta (pure, imports only `core`).
  Verify: 2.3 passes.
- [x] 3.5 `core/results.py`, `runner/run.py` and `report/render.py`: the required `TrialResult.slayer_version` stamped
  from the run's version, and the report's per-version trial counts. Verify: 2.5 passes.
- [x] 3.6 Regenerate the truth snapshots for the 17 new tasks (`poetry run slayer-evals truth --write`). Verify:
  `test_task_proofs.py` passes on the committed set, with every new reference matching and every new trap live, and
  each truth has at most 20 rows. A reference query SLayer cannot express, or a pre-existing reference that fails on
  1.7.0, is a suspected gap: STOP and ask the user.
- [x] 3.7 README:
  - suite counts: capability 34, combo 15, trap 21;
  - the pitfall table gains the four new rows;
  - Covered rows gains Q26 and Q27;
  - the SLayer pin text, naming SLayer 1.7.0.

  Verify: by reading it; the counts match `load_tasks`.
- [x] 3.8 Run the full non-integration suite, ruff and basedpyright. Verify: all green.

## 4. Baseline

- [x] 4.1 Backfill `"slayer_version": "1.1.0"` into every existing line of `results/baseline/results.jsonl`. Verify:
  `slayer-evals report results/baseline` loads it.
- [x] 4.2 Run every task of every suite in all five profiles, Opus 5.5, `repeat` N = 1: the default profiles on
  SLayer 1.8.5, the Motley profiles against a local Motley backend (the list tasks first). This supersedes running the
  17 new tasks in three profiles. This needs the user's
  `.env.agents`; ask for the go-ahead before spending on agent runs. Merge their results lines and traces into
  `results/baseline/` and regenerate `report.md`. Verify:
  - the report regenerates byte-identically;
  - every committed task has a baseline trial in each profile;
  - the report lists both SLayer versions with their trial counts.
- [x] 4.3 Update the README baseline table and paragraph, naming both SLayer versions, and the failure breakdown in
  `docs/baseline-failures.md`. Verify: the numbers equal the regenerated report.

## 5. Follow-ups from the baseline run

- [x] 5.1 Pin `motley-slayer = "1.8.5"` and re-run the pin compatibility gate (1.2) on it.
- [x] 5.2 Merge `origin/main` (Motley profiles, Jaffle suite); rebase the delta specs on main's requirement text.
- [x] 5.3 `--motley-slayer-version`: required with a Motley profile; Motley trials record it.
- [x] 5.4 `q27-tag-count-groups`: distinct-tag truth, two-stage reference, xfail DEV-2209 in the SLayer-backed profiles,
  the repeated-tag sentence; `t-tagged-credit` reference with `contains_any`.
- [x] 5.5 Task fixes: `t-without-vip` prompt, `q13-top-cities-count` truth, reference and prompt,
  `q9-credit-by-status` phrases, `q3-avg-city-revenue` truth and reference; rerun each in the affected profiles.
- [x] 5.6 Grading: refusals without the expected error; raw-SQL warning answers with rows; `extra_zero_rows` on the 11
  every-region tasks.
- [x] 5.7 Assemble the five-profile baseline, regenerate its report, and rewrite the README baseline section and
  `docs/baseline-failures.md`.
