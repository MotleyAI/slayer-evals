## MODIFIED Requirements

### Requirement: Run output
A run SHALL write, under a timestamped run directory: one results line per trial (task, covers, profile, model, trial
index, SLayer version, verdict with reasons, end reason, usage, cost, duration), the normalized trace and the raw
transcript per trial, the run metadata, and the report. Each results line's SLayer version SHALL be the version the run
recorded. Results SHALL be written as each trial completes, so an interrupted run keeps completed trials. Tasks marked
`xfail` SHALL run and be reported separately from the pass rate.

#### Scenario: Interrupted run keeps results
- **WHEN** a run is interrupted after some trials completed
- **THEN** the results file holds a line for each completed trial

#### Scenario: Results line names its SLayer version
- **WHEN** a run completes a trial in any profile
- **THEN** its results line carries the SLayer version recorded in the run metadata

#### Scenario: Results line without a version rejected
- **WHEN** a report is generated from a results file whose line lacks the SLayer version
- **THEN** loading fails naming the missing field
