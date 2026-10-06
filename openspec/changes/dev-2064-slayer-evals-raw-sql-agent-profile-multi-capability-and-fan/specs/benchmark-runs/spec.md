## MODIFIED Requirements

### Requirement: Run selection
A run SHALL be selectable by task ids, covered rows, profiles and models; the defaults SHALL be all tasks, all three
profiles (`slayer`, `slayer+python`, `sql+python`), model Opus 5.5 (`claude-opus-5-5`), and N = 1 trial.

#### Scenario: Row filter
- **WHEN** a run is started with rows Q1 and Q4
- **THEN** exactly the tasks covering Q1 or Q4 run

#### Scenario: Default profiles
- **WHEN** a run is started without a profile selection
- **THEN** every selected task runs in `slayer`, `slayer+python` and `sql+python`

### Requirement: Run output
A run SHALL write, under a timestamped run directory: one results line per trial (task, covers, profile, model, trial
index, verdict with reasons, end reason, usage, cost, duration), the normalized trace and the raw transcript per trial,
the run metadata, and the report. Results SHALL be written as each trial completes, so an interrupted run keeps
completed trials. Tasks marked `xfail` SHALL run and be reported separately from the pass rate.

#### Scenario: Interrupted run keeps results
- **WHEN** a run is interrupted after some trials completed
- **THEN** the results file holds a line for each completed trial

## ADDED Requirements

### Requirement: Auto-failed trials
A trial of a task with `uses_saved` in profile `sql+python` SHALL NOT start an agent: it SHALL be recorded as a trial
with end reason `auto_fail`, a trace holding only the profile, and the verdict grading gives it, and it counts in every
total like any other trial. In `until-pass` mode such a combination SHALL have exactly one trial.

#### Scenario: Saved-definition task in raw SQL
- **WHEN** a run includes task `q23-monthly-by-region` (which uses `monthly_rev`) in `sql+python`
- **THEN** its results line has end reason `auto_fail`, a failed verdict naming `monthly_rev`, and no transcript, and no agent process was started
