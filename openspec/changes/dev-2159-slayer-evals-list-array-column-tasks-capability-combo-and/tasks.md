## 1. SLayer pin

- [ ] 1.1 Raise the `motley-slayer` rev in `pyproject.toml` to the SLayer main commit that contains merged DEV-2137 and
  update `poetry.lock`. If DEV-2137 is not on SLayer main yet when this task starts, STOP and ask the user (the plan
  assumes it is released). Verify: `poetry install` succeeds and `python -c "import slayer"` reports the new version.

## 2. Tests first (pr-tests stage)

- [ ] 2.1 `tests/test_core_schemas.py` and `tests/test_task_format.py`:
  - the row range is Q1–Q27;
  - Q26 and Q27 are accepted, and Q28 is rejected;
  - the four new pitfall kinds are accepted, and a trap covering `[Q27, null_element]` loads.

  Verify: the new tests fail before implementation.
- [ ] 2.2 `tests/test_task_suite.py`:
  - coverage fails without a Q27 task;
  - the Q27 marker check;
  - deny-list entries `contains(`, `contains_any`, `contains_all`, `length(`, `collect(` and `unnest`;
  - "contains" and "length" in prose pass.

  Verify: the new tests fail before implementation.
- [ ] 2.3 `tests/test_table_compare.py`, for every scenario of the grading delta:
  - list sets with order, repeats and NULL elements;
  - JSON and comma text against a list truth column;
  - text outside list columns stays text;
  - NULL ≠ `[]`;
  - numeric elements within and outside tolerance.

  Verify: the new tests fail before implementation.
- [ ] 2.4 `tests/test_dataset.py`:
  - the probe hash is computed over the probe columns, and `probe_table_hashes.json` stays unchanged;
  - the layout check covers the probe columns plus `customers.tags`;
  - list edge-case invariants for `customers.tags` and `products.ratings`: a repeated element, a NULL element next to
    non-NULL ones, an empty list, a NULL list, and both `vip` and `eu`;
  - different seeds give different tags and ratings;
  - the store's list columns are usable.

  Verify: the new tests fail before implementation.
- [ ] 2.5 `tests/test_runner.py` and `tests/test_report.py`:
  - every results line carries `slayer_version`;
  - a line without it fails loading;
  - the report lists mixed versions with their trial counts;
  - the per-row table has rows Q26 and Q27 with their names.

  Verify: the new tests fail before implementation.
- [ ] 2.6 Write the 17 task files from the design's task table, each with a capability-neutral prompt, `truth_sql`
  spelling out the SLayer list semantics (non-NULL elements; NULL list ≠ empty list), `slayer_query`, `compare`, and
  `naive_sql` on traps. Verify: `test_task_format` loads them; the proofs fail only for lack of the dataset columns.
- [ ] 2.7 Backfill `"slayer_version": "1.1.0"` into `tests/fixtures/run_repeat/results.jsonl` and
  `tests/fixtures/run_until_pass/results.jsonl` (and any other committed results fixture). Verify: the fixtures load
  once the field exists.

## 3. Implementation (pr-implement stage)

- [ ] 3.1 Generator:
  - `customers.tags VARCHAR[]` from stream `customer_tags`;
  - `products.ratings INTEGER[]` from stream `product_ratings`;
  - deterministic witnesses on fixed existing ids.

  Verify: 2.4 passes, and every pre-existing truth snapshot is byte-identical (`slayer-evals truth` without `--write`
  reports no drift for old tasks).
- [ ] 3.2 Store models: `customers.yaml` gets `tags` (list of text), and `products.yaml` gets `ratings` (list of int),
  spelled as merged DEV-2137 requires. Verify: the store-template list-column scenario passes.
- [ ] 3.3 `core/task.py`, `tasks/suite.py` and `report/render.py`: the row range, the pitfall kinds, the Q27 markers,
  the deny-list, and the Q26/Q27 row names. Verify: 2.1, 2.2 and the row part of 2.5 pass.
- [ ] 3.4 `grading/tables.py`: list-cell normalization and matching per the grading delta (pure, imports only `core`).
  Verify: 2.3 passes.
- [ ] 3.5 `core/results.py`, `runner/run.py` and `report/render.py`: the required `TrialResult.slayer_version` stamped
  from the run's version, and the report's per-version trial counts. Verify: 2.5 passes.
- [ ] 3.6 Regenerate the truth snapshots for the 17 new tasks (`poetry run slayer-evals truth --write`). Verify:
  `test_task_proofs.py` passes on the committed set, with every new reference matching and every new trap live, and
  each truth has at most 20 rows. A reference query SLayer cannot express is a suspected gap: STOP and ask the user.
- [ ] 3.7 README:
  - suite counts: capability 34, combo 15, trap 21;
  - the pitfall table gains the four new rows;
  - Covered rows gains Q26 and Q27;
  - the SLayer pin text.

  Verify: by reading it; the counts match `load_tasks`.
- [ ] 3.8 Run the full non-integration suite, ruff and basedpyright. Verify: all green.

## 4. Baseline

- [ ] 4.1 Backfill `"slayer_version": "1.1.0"` into every existing line of `results/baseline/results.jsonl`. Verify:
  `slayer-evals report results/baseline` loads it.
- [ ] 4.2 Run the 17 new tasks in all three profiles, Opus 5.5, `repeat` N = 1, on the new pin. This needs the user's
  `.env.agents`; ask for the go-ahead before spending on agent runs. Merge their results lines and traces into
  `results/baseline/` and regenerate `report.md`. Verify:
  - the report regenerates byte-identically;
  - every committed task has a baseline trial in each profile;
  - the report lists both SLayer versions with their trial counts.
- [ ] 4.3 Update the README baseline table and paragraph, naming both SLayer versions, and the failure breakdown in
  `docs/baseline-failures.md`. Verify: the numbers equal the regenerated report.
