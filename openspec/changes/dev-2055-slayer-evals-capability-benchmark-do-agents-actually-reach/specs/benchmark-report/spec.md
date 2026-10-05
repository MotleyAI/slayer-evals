## Purpose

Turns a run's results into a readable markdown report — where agents do and do not reach for each capability, and
why — and publishes the baseline with the repository.

## ADDED Requirements

### Requirement: Run report
The report SHALL show the run metadata (SLayer and SDK versions, model, mode, N, budgets, auth mode, date); a table per
profile and model of rows Q1–Q25 with tasks, trials, and pass counts for `correct`, `capability`, `no_hack` and overall;
for `repeat` the pass rate k/N and pass^N per task; for `until-pass` first-try passes, eventual passes and attempts
used; xfail tasks in their own section with their issue key; totals of tokens, cost and duration; and for every failed
trial its unmet criteria with reasons and a digest of its SLayer calls. Rows Q19 and Q22 SHALL appear as not covered.
A single-trial run SHALL be labelled as a single-trial snapshot.

#### Scenario: Report from results
- **WHEN** a report is generated from a results file with passes and failures in both profiles
- **THEN** the counts per row and profile equal those in the results, and each failure appears with its reasons

#### Scenario: Until-pass report
- **WHEN** the results come from an `until-pass` run
- **THEN** the report shows first-try passes, eventual passes and attempts used instead of k/N

#### Scenario: Report regenerates offline
- **WHEN** a report is generated twice from the same run directory
- **THEN** both reports are byte-identical, and no agent or network is involved

### Requirement: Committed baseline
The repository SHALL include a baseline: the report, results and normalized traces of a run of all tasks in both
profiles with model Opus 5.5 and N = 1, and the README SHALL summarise it and link to it.

#### Scenario: Baseline is reproducible from its files
- **WHEN** the report is regenerated from the committed baseline results
- **THEN** it equals the committed baseline report
