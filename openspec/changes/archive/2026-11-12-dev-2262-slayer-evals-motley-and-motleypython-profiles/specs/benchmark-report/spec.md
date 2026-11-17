## MODIFIED Requirements

### Requirement: Run report
The report SHALL show the run metadata (SLayer and SDK versions, model, mode, N, budgets, auth mode, date, and when a
Motley profile ran, the Motley URL and the MCP server info `initialize` reported); a headline table of suite
(`capability`, `combo`, `trap`) by profile and model with trials and counts for `correct`, `single_query` and `passed`,
stating that `correct` is the cross-profile comparison; a table of pitfall kind by profile and model with trials and
`correct` counts; and per profile and model a table of rows Q1–Q25 with tasks, trials, counts for `correct`,
`single_query` and `passed`, and counts of the trace flags, where a task counts under every row it covers and the
table says so; each Motley profile's section SHALL state that Motley's `query` cannot yet run a saved query by name
with `refine`, so saved-query tasks are answered with one inline query; for `repeat` the pass rate k/N and pass^N per
task with its suite; for `until-pass` first-try passes, eventual passes and attempts used; xfail trials in their own
section with their issue key; totals of tokens, cost and duration; and for every failed trial its unmet criteria with
reasons and a digest of its SLayer, Motley and `sql` calls. Rows Q19 and Q22 SHALL appear as not covered. A
single-trial run SHALL be labelled as a single-trial snapshot.

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

#### Scenario: Motley run report
- **WHEN** a report is generated for a run with `motley` trials
- **THEN** the metadata shows the Motley URL and MCP server info, the `motley` section states that saved queries cannot yet be run by name with `refine`, and a failed Motley call's digest names the bare error class

#### Scenario: Run without Motley
- **WHEN** a report is generated for a run without Motley profiles
- **THEN** it shows no Motley metadata rows and no Motley note
