Source bundle: `~/Downloads/nao-vs-motley-slim.zip` (unpack into a fresh scratch directory; it unpacks to
`nao-vs-motley/`). Probe notes for the reference queries are in design.md, "Reference-query notes".

## 1. Core schemas

- [ ] 1.1 Add `Dataset`, `DatasetSpec` and `DATASET_SPECS` (bench → datasource `bench`, `bench.duckdb`; jaffle →
  `demo_database`, `jaffle.duckdb`) to `core`; verify with a core schema test
- [ ] 1.2 `Task.dataset` (default `bench`), `covers` required on bench and forbidden on jaffle, `Suite` gains
  `jaffle`, suite derivation; verify with task-format tests for every "Task file format" and "Task suites" scenario
- [ ] 1.3 `TrialEnv.business_rules` and `TrialResult.dataset` (default `bench`); verify old results lines without
  `dataset` still load, and trace/env round-trips

## 2. Jaffle dataset

- [ ] 2.1 Seeded jafgen build in a child process (seeds `random`, NumPy and jafgen's module-level Faker, patches
  `uuid.uuid4`, temp working directory), 4 years, 7 raw tables, dates shifted to end 2026-10-29; verify two builds
  give equal canonical hashes and the builder process's random state, ids and cwd are unchanged
- [ ] 2.2 Commit the 7 tables' canonical content hashes and add the shape/range checks (6 stores and their opening
  dates, money columns integer, 1.1–1.25M orders, date range); verify with dataset tests
- [ ] 2.3 Commit Yann's 7 model YAMLs (sampled values stripped) and the 9 `jaffle-*` memories under
  `src/slayer_evals/dataset/`; build the Jaffle store (datasource `demo_database`, models through the engine,
  memories through SLayer's memory API — query-bearing ones with their query — help memories seeded, no embeddings);
  verify the "Jaffle store template" scenarios, including the pinned entity set per memory and `search` finding
  `jaffle-revenue-definition` for "revenue pre-tax"
- [ ] 2.4 Write the plain-SQL rules text (one section per memory, titled with its id, same order, SLayer mechanics
  replaced by table terms, figures kept); verify the section/order test and the no-SLayer-vocabulary test
- [ ] 2.5 `build` writes `<out>/bench/` and `<out>/jaffle/`; per-dataset `load_built`; verify the build-layout test

## 3. Tasks, truth and proofs

- [ ] 3.1 Suite checks: `tasks/jaffle/` layout, coverage bench-only, prompt deny list and truth sizes over all tasks;
  verify the "Row coverage" and "Misplaced file" scenarios
- [ ] 3.2 Truth and snapshots per task dataset; `truth --write` always over every loaded task; verify the
  "Writing keeps every dataset's snapshots" scenario
- [ ] 3.3 Proofs per task dataset (the dataset's store and datasource); `uses_saved` checked against the task's store;
  verify proof tests on a Jaffle task
- [ ] 3.4 Write the 24 Jaffle task files (verbatim question + shape sentence per design.md's table, adapted reference
  SQL, `compare`, proven `slayer_query`), regenerate snapshots; verify the "Jaffle tasks" scenarios and that all
  proofs pass

## 4. Runner, CLI and agents

- [ ] 4.1 `--suites` selection; verify the "Suite filter" scenario
- [ ] 4.2 Build or load only the datasets a run needs; `--dataset-dir` as build root, all missing datasets named
  together; verify the "Datasets of a run" scenarios
- [ ] 4.3 Per-trial copies of the task's own dataset; `business_rules` set only for jaffle × `sql` surface;
  `dataset` written on each results line; verify the trial-isolation and agent-contract scenarios
- [ ] 4.4 Motley: seed `--db` with the run's database file of the trial's dataset; warm-up per dataset with
  `warm-up:<dataset>` identities, only for datasets with Motley trials; verify the "Warm-up per dataset" and
  "Seed before each Motley trial" scenarios
- [ ] 4.5 `system_prompt` appends the business rules under a fixed heading when the env carries them; verify the
  "Business rules in the system prompt" and "System prompt per profile" scenarios

## 5. Report

- [ ] 5.1 Suite from `dataset`/`covers`; `jaffle` headline row only when present; Jaffle section with per-task table
  and the business-rules note; row and pitfall tables count bench trials only; verify the "Jaffle trials in the
  report" and "Run without Jaffle" scenarios and byte-identical regeneration

## 6. Architecture and docs

- [ ] 6.1 Apply the approved Purpose wording in `architecture/system.arc42.md` (design.md decision 14); verify
  `la-arch-check` and `npx likec4 validate` pass with `legacy_arrows` 0
- [ ] 6.2 README: Jaffle section (source, how rules reach each profile, `--suites jaffle`, new build layout)

## 7. Baseline

- [ ] 7.1 Re-run the baseline: all tasks × `slayer`, `slayer+python`, `sql+python`, Opus 5.5, `repeat`, N = 1; commit
  `results/baseline/`; verify the "Baseline covers every task" and "Baseline is reproducible from its files" tests
- [ ] 7.2 Update the README baseline summary per suite and profile, and redo `docs/baseline-failures.md` (by profile
  and pitfall, and the Jaffle suite by business rule); verify the baseline tests
