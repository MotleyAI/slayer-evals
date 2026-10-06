# benchmark-runs Specification

## Purpose
Runs selected tasks against agents in isolated trials, in a chosen run mode, and records every verdict, trace and
transcript so a run can be reported and audited.

## Requirements

### Requirement: Run selection
A run SHALL be selectable by task ids, covered rows, profiles and models; the defaults SHALL be all tasks, all three
profiles (`slayer`, `slayer+python`, `sql+python`), model Opus 5.5 (`claude-opus-5-5`), and N = 1 trial.

#### Scenario: Row filter
- **WHEN** a run is started with rows Q1 and Q4
- **THEN** exactly the tasks covering Q1 or Q4 run

#### Scenario: Default profiles
- **WHEN** a run is started without a profile selection
- **THEN** every selected task runs in `slayer`, `slayer+python` and `sql+python`

### Requirement: Run modes
A run SHALL take a mode chosen at launch: `repeat`, which runs every selected (task, profile, model) N times; or
`until-pass`, which runs it until a trial passes or N trials have run, whichever comes first. A trial passes iff its
verdict passed; trials ending in `timeout`, `max_turns` or `error` count as failed and are retried in `until-pass`.

#### Scenario: Repeat runs N times
- **WHEN** mode is `repeat` with N = 3
- **THEN** each selected combination has exactly 3 trials

#### Scenario: Until-pass stops at first pass
- **WHEN** mode is `until-pass` with N = 3 and the second trial passes
- **THEN** that combination has exactly 2 trials and is recorded as passed after 2 attempts

#### Scenario: Until-pass exhausts
- **WHEN** mode is `until-pass` with N = 3 and no trial passes
- **THEN** that combination has 3 trials and is recorded as failed

### Requirement: Trial isolation
Each trial SHALL run on its own fresh copy of the database and of the store template, in its own process, so that
no trial can observe another's models, memories or data changes. Trials SHALL run concurrently up to a configurable
limit (default 3).

#### Scenario: Agent-created model does not leak
- **WHEN** a trial creates a model and a later trial of another task lists models
- **THEN** the later trial does not see it

### Requirement: Explicit authentication
A run MUST be told explicitly whether to use subscription authentication or an API key, and SHALL read credentials
from an optional env file. In subscription mode it MUST require `CLAUDE_CODE_OAUTH_TOKEN` and blank any API key in the
agent's environment; in API-key mode it MUST require `ANTHROPIC_API_KEY` and blank the OAuth token. It MUST NOT infer
the mode from which credential happens to be present.

#### Scenario: Mode not given
- **WHEN** a run is started without choosing an auth mode
- **THEN** it refuses to start and says how to choose

#### Scenario: Missing credential
- **WHEN** subscription mode is chosen and no OAuth token is available
- **THEN** the run refuses to start naming the missing variable

### Requirement: SLayer under test
A run SHALL use the pinned SLayer release by default and accept an alternative `slayer` command (for a local checkout).
It SHALL record the SLayer version, the agent SDK version, the model id, budgets, run mode, N and auth mode.

#### Scenario: Local SLayer override
- **WHEN** a run is started with a custom SLayer command
- **THEN** every trial launches that command and the recorded SLayer version is the one it reports

### Requirement: Run output
A run SHALL write, under a timestamped run directory: one results line per trial (task, covers, profile, model, trial
index, verdict with reasons, end reason, usage, cost, duration), the normalized trace and the raw transcript per trial,
the run metadata, and the report. Results SHALL be written as each trial completes, so an interrupted run keeps
completed trials. Tasks marked `xfail` SHALL run and be reported separately from the pass rate.

#### Scenario: Interrupted run keeps results
- **WHEN** a run is interrupted after some trials completed
- **THEN** the results file holds a line for each completed trial

### Requirement: Auto-failed trials
A trial of a task with `uses_saved` in profile `sql+python` SHALL NOT start an agent: it SHALL be recorded as a trial
with end reason `auto_fail`, a trace holding only the profile, and the verdict grading gives it, and it counts in every
total like any other trial. In `until-pass` mode such a combination SHALL have exactly one trial.

#### Scenario: Saved-definition task in raw SQL
- **WHEN** a run includes task `q23-monthly-by-region` (which uses `monthly_rev`) in `sql+python`
- **THEN** its results line has end reason `auto_fail`, a failed verdict naming `monthly_rev`, and no transcript, and no agent process was started
