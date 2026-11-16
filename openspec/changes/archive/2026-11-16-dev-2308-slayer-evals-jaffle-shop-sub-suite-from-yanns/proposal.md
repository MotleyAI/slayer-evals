## Why

Yann's nao-vs-Motley experiment (6 Nov 2026) scored 24 business questions over a Jaffle Shop database by hand. Its
main finding — every SLayer miss came from a business rule the agent did not retrieve — is not something the current
benchmark can measure: every task runs on one seeded demo database, states its definitions in the prompt, and has no
business rules to find. Adding the 24 questions as a graded sub-suite lets every profile be scored on them
automatically and repeatedly.

## What Changes

- A second dataset, `jaffle`: a seeded, deterministic jafgen build in the raw shape Yann used (7 tables, money in
  integer cents, last order on 2026-10-29), with its own SLayer store template holding Yann's 7 models from
  `MotleyAI/my_model_repo` and the 9 `jaffle-*` memories, and a committed plain-SQL rendering of those rules.
- Tasks gain a `dataset` field (default `bench`); a Jaffle task belongs to the new suite `jaffle`, lives under
  `tasks/jaffle/` and carries no `covers`. 24 Jaffle tasks: Yann's question verbatim plus an answer-shape sentence,
  truth from his reference SQL, and a proven single `slayer_query` each.
- Business rules reach the SQL profiles through the system prompt on Jaffle tasks; the SLayer and Motley profiles
  must find them through `search`, as in Yann's run.
- Runs select by suite (`--suites`), build or load only the datasets their tasks need, and give each trial its task's
  dataset; the Motley warm-up runs once per dataset with its own identity.
- **BREAKING**: `build` writes one subdirectory per dataset (`<out>/bench/`, `<out>/jaffle/`), and `--dataset-dir`
  names that build root.
- The report adds `jaffle` to the headline suite table and a per-task Jaffle section; row and pitfall tables stay
  bench-only. The committed baseline is re-run over all 77 tasks.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `benchmark-dataset`: a second, seeded Jaffle Shop dataset with its own store template and rules text; one build
  directory per dataset.
- `benchmark-tasks`: the `dataset` field, the `jaffle` suite and folder, coverage checks scoped to bench tasks,
  truth and proofs per dataset.
- `benchmark-runs`: suite selection, per-dataset environments, per-dataset Motley warm-up, results carrying the
  dataset.
- `agent-harness`: the trial environment may carry business rules, which the SQL profiles' system prompt includes.
- `benchmark-report`: the `jaffle` suite row and section; the baseline covers all suites.

## Impact

- Code: `core` (dataset registry, task and result schemas, trial environment), `dataset` (Jaffle generator, store,
  rules), `tasks` (loading, suite checks, truth, proofs), `runner` and `cli` (selection, per-dataset builds,
  Motley warm-up), `agents` (system prompt), `report` (suite row, Jaffle section).
- Data: `tasks/jaffle/` (24 tasks), `tasks/truth/` (24 snapshots), the Jaffle models, memories and rules text under
  `src/slayer_evals/dataset/`, a re-run `results/baseline/`.
- Docs: README (baseline summary, Jaffle section), `docs/baseline-failures.md`, `architecture/system.arc42.md`
  (Purpose wording).
- Dependencies: none new (jafgen already ships with the pinned SLayer). CI builds a second dataset (about 1.2M
  orders).
