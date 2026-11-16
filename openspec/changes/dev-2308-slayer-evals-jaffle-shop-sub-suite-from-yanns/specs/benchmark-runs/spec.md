## MODIFIED Requirements

### Requirement: Run selection
A run SHALL be selectable by task ids, covered rows, suites, profiles and models. The suites SHALL be `capability`,
`combo`, `trap` and `jaffle`. The profiles SHALL be `slayer`, `slayer+python`, `sql+python`, `motley` and
`motley+python`. The defaults SHALL be all tasks of every suite, the three profiles `slayer`, `slayer+python` and
`sql+python`, model Opus 5.5 (`claude-opus-5-5`), and N = 1 trial; the Motley profiles run only when selected.

#### Scenario: Row filter
- **WHEN** a run is started with rows Q1 and Q4
- **THEN** exactly the tasks covering Q1 or Q4 run

#### Scenario: Suite filter
- **WHEN** a run is started with suite `jaffle`
- **THEN** exactly the `jaffle` tasks run

#### Scenario: Default profiles
- **WHEN** a run is started without a profile selection
- **THEN** every selected task runs in `slayer`, `slayer+python` and `sql+python`, and in no Motley profile

### Requirement: Trial isolation
Each trial SHALL run on its own fresh copy of its task's dataset — the database and the store template — in its own
process, so that no trial can observe another's models, memories or data changes. A trial in a Motley profile SHALL
additionally get its own Motley organization, seeded from its store copy, so that it cannot observe another trial's
models or memories; all Motley organizations of a run whose tasks share a dataset SHALL read the run's one database
file of that dataset, which the Motley backend opens read-only. Trials SHALL run concurrently up to a configurable
limit (default 3).

#### Scenario: Agent-created model does not leak
- **WHEN** a trial creates a model and a later trial of another task lists models
- **THEN** the later trial does not see it

#### Scenario: Trial gets its task's dataset
- **WHEN** a run holds a `bench` task and a `jaffle` task
- **THEN** each trial's database and store copies are those of its own task's dataset

#### Scenario: Motley trials get their own organization
- **WHEN** two Motley trials run
- **THEN** each is seeded under its own user id, and their agents send different user ids

### Requirement: Motley under test
A run that selects a Motley profile SHALL take the Motley MCP URL (default `http://localhost:8000/api/v1/mcp/`) and a
seed command, and MUST refuse to start, naming the missing option, when no seed command is given. Before each Motley
trial it SHALL run the seed command with `--user-id <id> --store <the trial's store copy> --db <the run's database
file of the trial's dataset, as an absolute path>`, with the run's environment minus the Claude and Anthropic
credentials, within the trial's concurrency slot, under a timeout, and SHALL stop the command and every process it
started when the timeout passes or the run is interrupted. The user id SHALL match `[A-Za-z0-9_-]{1,64}`, SHALL be
derived from the run directory and the trial, and SHALL differ between any two trials and between any two runs. A seed
that fails or times out SHALL end that trial with end reason `error` and an error carrying the end of the seed's error
output, without starting an agent. Before the first trial the run SHALL, for each dataset that the run's Motley trials
use, seed one warm-up organization from that dataset's store and database under a user id of its own, and SHALL
complete an MCP `initialize` with a warm-up user's id; any failure of either MUST stop the run before any trial,
naming the cause. The run metadata SHALL record the Motley URL and the server name and version that `initialize`
reports, and SHALL record neither when no Motley profile is selected.

#### Scenario: Motley profile without a seed command
- **WHEN** a run selects `motley` and gives no seed command
- **THEN** it refuses to start and names the missing option

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

### Requirement: Run output
A run SHALL write, under a timestamped run directory: one results line per trial (task, dataset, covers, profile,
model, trial index, verdict with reasons, end reason, usage, cost, duration), the normalized trace and the raw
transcript per trial, the run metadata, and the report. Results SHALL be written as each trial completes, so an
interrupted run keeps completed trials. A results line without a dataset SHALL read as dataset `bench`. A trial whose
task is marked `xfail` for the trial's profile SHALL run and be reported separately from the pass rate; a trial in a
profile the task's `xfail` does not name SHALL count normally.

#### Scenario: Interrupted run keeps results
- **WHEN** a run is interrupted after some trials completed
- **THEN** the results file holds a line for each completed trial

#### Scenario: Results carry the dataset
- **WHEN** a `jaffle` task's trial completes
- **THEN** its results line records dataset `jaffle`

#### Scenario: Profile-scoped xfail
- **WHEN** a task's `xfail` names only `motley` and `motley+python`, and the task runs in `slayer` and `motley`
- **THEN** the `motley` trial's results line carries the xfail issue and the `slayer` trial's does not

## ADDED Requirements

### Requirement: Datasets of a run
A run SHALL build, or load from a given build directory, only the datasets its selected tasks use. A given build
directory SHALL be the build root holding one subdirectory per dataset; a run MUST refuse to start when the
subdirectory of any dataset it needs is missing or incomplete, naming every such dataset. Truth for each task SHALL be
computed on its own dataset.

#### Scenario: Only needed datasets built
- **WHEN** a run selects only `bench` tasks and no build directory is given
- **THEN** the Jaffle dataset is not built

#### Scenario: Missing dataset reported
- **WHEN** a run selects `bench` and `jaffle` tasks with a build directory that holds neither subdirectory
- **THEN** it refuses to start naming both `bench` and `jaffle`
