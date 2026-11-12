# benchmark-runs Specification

## Purpose
Runs selected tasks against agents in isolated trials, in a chosen run mode, and records every verdict, trace and
transcript so a run can be reported and audited.

## Requirements

### Requirement: Run selection
A run SHALL be selectable by task ids, covered rows, profiles and models. The profiles SHALL be `slayer`,
`slayer+python`, `sql+python`, `motley` and `motley+python`. The defaults SHALL be all tasks, the three profiles
`slayer`, `slayer+python` and `sql+python`, model Opus 5.5 (`claude-opus-5-5`), and N = 1 trial; the Motley profiles
run only when selected.

#### Scenario: Row filter
- **WHEN** a run is started with rows Q1 and Q4
- **THEN** exactly the tasks covering Q1 or Q4 run

#### Scenario: Default profiles
- **WHEN** a run is started without a profile selection
- **THEN** every selected task runs in `slayer`, `slayer+python` and `sql+python`, and in no Motley profile

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
no trial can observe another's models, memories or data changes. A trial in a Motley profile SHALL additionally get its
own Motley organization, seeded from its store copy, so that it cannot observe another trial's models or memories; all
Motley organizations of a run SHALL read the run's one database file, which the Motley backend opens read-only. Trials
SHALL run concurrently up to a configurable limit (default 3).

#### Scenario: Agent-created model does not leak
- **WHEN** a trial creates a model and a later trial of another task lists models
- **THEN** the later trial does not see it

#### Scenario: Motley trials get their own organization
- **WHEN** two Motley trials run
- **THEN** each is seeded under its own user id, and their agents send different user ids

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
completed trials. A trial whose task is marked `xfail` for the trial's profile SHALL run and be reported separately
from the pass rate; a trial in a profile the task's `xfail` does not name SHALL count normally.

#### Scenario: Interrupted run keeps results
- **WHEN** a run is interrupted after some trials completed
- **THEN** the results file holds a line for each completed trial

#### Scenario: Profile-scoped xfail
- **WHEN** a task's `xfail` names only `motley` and `motley+python`, and the task runs in `slayer` and `motley`
- **THEN** the `motley` trial's results line carries the xfail issue and the `slayer` trial's does not

### Requirement: Auto-failed trials
A trial of a task with `uses_saved` in profile `sql+python` SHALL NOT start an agent: it SHALL be recorded as a trial
with end reason `auto_fail`, a trace holding only the profile, and the verdict grading gives it, and it counts in every
total like any other trial. In `until-pass` mode such a combination SHALL have exactly one trial.

#### Scenario: Saved-definition task in raw SQL
- **WHEN** a run includes task `q23-monthly-by-region` (which uses `monthly_rev`) in `sql+python`
- **THEN** its results line has end reason `auto_fail`, a failed verdict naming `monthly_rev`, and no transcript, and no agent process was started

### Requirement: Motley under test
A run that selects a Motley profile SHALL take the Motley MCP URL (default `http://localhost:8000/api/v1/mcp/`) and a
seed command, and MUST refuse to start, naming the missing option, when no seed command is given. Before each Motley
trial it SHALL run the seed command with `--user-id <id> --store <the trial's store copy> --db <the run's database
file, as an absolute path>`, with the run's environment minus the Claude and Anthropic credentials, within the trial's
concurrency slot, under a timeout, and SHALL stop the command and every process it started when the timeout passes or
the run is interrupted. The user id SHALL match `[A-Za-z0-9_-]{1,64}`, SHALL be derived from the run directory and the
trial, and SHALL differ between any two trials and between any two runs. A seed that fails or times out SHALL end that
trial with end reason `error` and an error carrying the end of the seed's error output, without starting an agent.
Before the first trial the run SHALL seed one warm-up organization and SHALL complete an MCP `initialize` with the
warm-up user's id; any failure of either MUST stop the run before any trial, naming the cause. The run metadata SHALL
record the Motley URL and the server name and version that `initialize` reports, and SHALL record neither when no
Motley profile is selected.

#### Scenario: Motley profile without a seed command
- **WHEN** a run selects `motley` and gives no seed command
- **THEN** it refuses to start and names the missing option

#### Scenario: Seed before each Motley trial
- **WHEN** a Motley trial runs
- **THEN** the seed command ran first with the trial's user id, the trial's store copy and the run's database file as an absolute path, and the agent receives the same user id

#### Scenario: Seed failure ends the trial
- **WHEN** the seed command exits with an error for a trial
- **THEN** that trial ends with end reason `error`, its error carries the seed's error output, and no agent is started

#### Scenario: Seed timeout leaves no processes
- **WHEN** the seed command, and a process it started, run past the seed timeout
- **THEN** the trial ends with end reason `error` and neither process survives

#### Scenario: Warm-up failure stops the run
- **WHEN** the warm-up seed fails, or the Motley server cannot be reached or refuses the request
- **THEN** the run stops before any trial with an error naming the cause

#### Scenario: Motley metadata
- **WHEN** a run with a Motley profile completes
- **THEN** its metadata records the Motley URL and the server name and version reported by `initialize`
