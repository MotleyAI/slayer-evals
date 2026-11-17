## MODIFIED Requirements

### Requirement: Run output
A run SHALL write, under a timestamped run directory: one results line per trial (task, dataset, covers, profile,
model, trial index, SLayer version, verdict with reasons, end reason, usage, cost, duration), the normalized trace and
the raw transcript per trial, the run metadata, and the report. A results line's SLayer version SHALL be the version of
the SLayer that answered the trial: the version the run recorded for the local SLayer, or, for a Motley trial, the
Motley backend's SLayer version the run was given. Results SHALL be written as each trial completes, so an interrupted
run keeps completed trials. A results line without a dataset SHALL read as dataset `bench`. A trial whose task is
marked `xfail` for the trial's profile SHALL run and be reported separately from the pass rate; a trial in a profile
the task's `xfail` does not name SHALL count normally.

#### Scenario: Interrupted run keeps results
- **WHEN** a run is interrupted after some trials completed
- **THEN** the results file holds a line for each completed trial

#### Scenario: Results carry the dataset
- **WHEN** a `jaffle` task's trial completes
- **THEN** its results line records dataset `jaffle`

#### Scenario: Profile-scoped xfail
- **WHEN** a task's `xfail` names only `motley` and `motley+python`, and the task runs in `slayer` and `motley`
- **THEN** the `motley` trial's results line carries the xfail issue and the `slayer` trial's does not

#### Scenario: Results line names its SLayer version
- **WHEN** a run with the Motley backend's SLayer version `1.8.2` completes a trial in `slayer` and one in `motley`
- **THEN** the `slayer` line carries the SLayer version recorded in the run metadata and the `motley` line carries `1.8.2`

#### Scenario: Results line without a version rejected
- **WHEN** a report is generated from a results file whose line lacks the SLayer version
- **THEN** loading fails naming the missing field

### Requirement: Motley under test
A run that selects a Motley profile SHALL take the Motley MCP URL (default `http://localhost:8100/api/v1/mcp/`), a
seed command and the SLayer version the Motley backend runs, and MUST refuse to start, naming the missing option, when
no seed command or no backend SLayer version is given. Before each Motley trial it SHALL run the seed command with
`--user-id <id> --store <the trial's store copy> --db <the run's database file of the trial's dataset, as an absolute
path>`, with the run's environment minus the Claude and Anthropic credentials, within the trial's concurrency slot,
under a timeout, and SHALL stop the command and every process it started when the timeout passes or the run is
interrupted. The user id SHALL match `[A-Za-z0-9_-]{1,64}`, SHALL be derived from the run directory and the trial, and
SHALL differ between any two trials and between any two runs. A seed that fails or times out SHALL end that trial with
end reason `error` and an error carrying the end of the seed's error output, without starting an agent. Before the
first trial the run SHALL, for each dataset that the run's Motley trials use, seed one warm-up organization from that
dataset's store and database under a user id of its own, and SHALL complete an MCP `initialize` with a warm-up user's
id; any failure of either MUST stop the run before any trial, naming the cause. The run metadata SHALL record the
Motley URL and the server name and version that `initialize` reports, and SHALL record neither when no Motley profile
is selected.

#### Scenario: Motley profile without a seed command
- **WHEN** a run selects `motley` and gives no seed command
- **THEN** it refuses to start and names the missing option

#### Scenario: Motley profile without the backend's SLayer version
- **WHEN** a run selects `motley` with a seed command but no backend SLayer version
- **THEN** it refuses to start, names the missing option, and seeds nothing

#### Scenario: Seed before each Motley trial
- **WHEN** a Motley trial runs
- **THEN** the seed command ran first with the trial's user id, the trial's store copy and the run's database file of the trial's dataset as an absolute path, and the agent receives the same user id

#### Scenario: Warm-up per dataset
- **WHEN** a run selects `motley` with a `bench` task and a `jaffle` task
- **THEN** two warm-up organizations are seeded under two different user ids, each from its own dataset's store and database

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
