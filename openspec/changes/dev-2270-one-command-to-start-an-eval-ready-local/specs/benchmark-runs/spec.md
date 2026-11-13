## MODIFIED Requirements

### Requirement: Motley under test
A run that selects a Motley profile SHALL take the Motley MCP URL (default `http://localhost:8100/api/v1/mcp/`) and a
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
