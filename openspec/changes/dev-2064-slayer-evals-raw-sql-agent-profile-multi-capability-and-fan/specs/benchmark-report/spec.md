## MODIFIED Requirements

### Requirement: Run report
The report SHALL show the run metadata (SLayer and SDK versions, model, mode, N, budgets, auth mode, date); a headline
table of suite (`capability`, `combo`, `trap`) by profile and model with trials and counts for `correct`,
`single_query` and `passed`, stating that `correct` is the cross-profile comparison; a table of pitfall kind by profile
and model with trials and `correct` counts; and per profile and model a table of rows Q1–Q25 with tasks, trials, counts
for `correct`, `single_query` and `passed`, and counts of the trace flags, where a task counts under every row it
covers and the table says so; for `repeat` the pass rate k/N and pass^N per task with its suite; for `until-pass`
first-try passes, eventual passes and attempts used; xfail tasks in their own section with their issue key; totals of
tokens, cost and duration; and for every failed trial its unmet criteria with reasons and a digest of its SLayer and
`sql` calls. Rows Q19 and Q22 SHALL appear as not covered. A single-trial run SHALL be labelled as a single-trial
snapshot.

#### Scenario: Report from results
- **WHEN** a report is generated from a results file with passes and failures in all three profiles
- **THEN** the counts per suite, pitfall, row and profile equal those in the results, and each failure appears with its reasons

#### Scenario: Multi-row task counted per row
- **WHEN** a passing trial covers Q2 and Q4
- **THEN** it adds one trial and one pass to both the Q2 and the Q4 rows of its profile's table

#### Scenario: Until-pass report
- **WHEN** the results come from an `until-pass` run
- **THEN** the report shows first-try passes, eventual passes and attempts used instead of k/N

#### Scenario: Report regenerates offline
- **WHEN** a report is generated twice from the same run directory
- **THEN** both reports are byte-identical, and no agent or network is involved

### Requirement: Committed baseline
The repository SHALL include a baseline: the report, results and normalized traces of a run of all tasks in all three
profiles with model Opus 5.5 in `repeat` mode with N = 3; the README SHALL summarise it per suite and profile and link to
it, and `docs/baseline-failures.md` SHALL break its failures down by profile and pitfall.

#### Scenario: Baseline is reproducible from its files
- **WHEN** the report is regenerated from the committed baseline results
- **THEN** it equals the committed baseline report
