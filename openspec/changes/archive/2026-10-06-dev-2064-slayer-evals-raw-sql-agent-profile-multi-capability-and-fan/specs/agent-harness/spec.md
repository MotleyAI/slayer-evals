## MODIFIED Requirements

### Requirement: Agent contract
An agent SHALL receive only the task prompt text, the profile name, and the trial environment (store path, database
path, credentials, budgets). It MUST NOT receive the task's covers, comparison rules, expectations, reference SLayer
query, naive SQL or truth. It SHALL return a submission (`columns`, `rows`, `message`, or none) and a normalized trace:
the profile; an ordered list of tool calls, each with tool name, arguments, raw result text, parsed result (columns and
rows, warnings) when the tool is a SLayer `query` or the `sql` tool, an error flag, and for the Python tool its audit
log; plus usage (input, output, cache read and cache write tokens), cost, duration, turn count and end reason
(`submitted`, `max_turns`, `timeout`, `error`, `auto_fail`).

#### Scenario: Agent sees only the prompt
- **WHEN** a trial is started for a task
- **THEN** the agent-facing inputs contain the prompt text and none of the task's other fields

#### Scenario: Trace round-trip
- **WHEN** a normalized trace is serialized to JSON and read back
- **THEN** it equals the original

### Requirement: Hermetic Claude session
The Claude Agent SDK agent SHALL run each trial in an empty Claude configuration directory, with no built-in tools,
no settings sources, and only the MCP servers its profile declares: the SLayer server and the in-process `bench`
server in the SLayer profiles, and only the `bench` server in `sql+python`. After connecting it MUST verify that no
other MCP server is loaded and abort the trial otherwise. The SLayer MCP server SHALL run as `slayer mcp` over stdio on
the trial's store copy with a sanitized environment (an allow-list; no Claude or Anthropic credentials). Telemetry and
non-essential traffic SHALL be disabled and the prompt-caching mode pinned. The system prompt SHALL be minimal,
generic and identical across tasks and profiles, except that the SLayer profiles alone carry one sentence telling the
agent to request `query` results as JSON so numbers are exact; it SHALL ask every agent to submit exact, unrounded
values with null as the label of a group whose key is unknown; it MUST NOT mention SLayer features or tasks.

#### Scenario: Leaked server aborts
- **WHEN** after connecting the session reports an MCP server the profile did not declare
- **THEN** the trial ends with end reason `error` and a message naming the server

#### Scenario: SLayer subprocess has no credentials
- **WHEN** the SLayer server is launched
- **THEN** its environment contains no `CLAUDE_CODE_OAUTH_TOKEN`, `ANTHROPIC_API_KEY` or `ANTHROPIC_AUTH_TOKEN`

#### Scenario: No SLayer in the raw-SQL profile
- **WHEN** a session starts in `sql+python`
- **THEN** no SLayer server is configured or launched, and a SLayer server reported after connecting aborts the trial

#### Scenario: System prompt per profile
- **WHEN** the system prompts of the three profiles are compared
- **THEN** they are equal apart from the JSON-results sentence, which appears in `slayer` and `slayer+python` only

### Requirement: Profiles
Profile `slayer` SHALL expose every tool the SLayer MCP server advertises plus `submit_answer`. Profile
`slayer+python` SHALL additionally expose a Python tool that runs code in a subprocess with a fresh sandbox working
directory, a sanitized environment, CPU-time and memory limits, a per-call timeout, pandas, numpy and duckdb
installed, and an audit hook recording file opens and subprocess launches. Profile `sql+python` SHALL expose
`submit_answer`, the same Python tool, and the `sql` tool, and no SLayer tool; its Python tool MUST NOT be given the
database path.

#### Scenario: Profile tool sets
- **WHEN** a session starts in each profile
- **THEN** the model is offered exactly the SLayer tools plus `submit_answer` in `slayer`, those plus the Python tool in `slayer+python`, and exactly `submit_answer`, the Python tool and `sql` in `sql+python`

#### Scenario: Python audit log
- **WHEN** code in the Python tool opens a file outside its sandbox directory
- **THEN** the call's audit log in the trace records the path

#### Scenario: Python timeout
- **WHEN** code in the Python tool runs past its timeout
- **THEN** the call returns an error result and the session continues

## ADDED Requirements

### Requirement: SQL tool
The `sql` tool SHALL take one DuckDB SQL statement and run it on a read-only connection to the trial's database copy
with external access disabled and configuration locked, so that it cannot modify the database, read or write any other
file, attach a database, install or load extensions, reach the network, or re-enable any of these. Each call SHALL use
its own connection, closed when the call ends. Input with zero or more than one statement MUST be rejected as a tool
error. A call SHALL time out after 60 seconds: the statement is interrupted, the call returns an error result, and the
session continues; no work of a timed-out call MAY overlap a later call. The result SHALL be a JSON object with
`columns`, `rows` (at most 1,000, fetched without materializing more than 1,001) and `truncated`, with dates and
timestamps as ISO strings and decimals as numbers; a database error SHALL be returned as a tool error carrying the
database's message. The tool description SHALL name the dialect and read-only access and MUST NOT name tables or
SLayer.

#### Scenario: Query result
- **WHEN** the agent runs `select region, sum(amount) as revenue from orders_flat group by 1`
- **THEN** the tool returns the columns and rows as JSON with `truncated` false

#### Scenario: Batch rejected
- **WHEN** the input holds two statements separated by a semicolon
- **THEN** the tool returns an error and runs neither

#### Scenario: Escape attempts fail
- **WHEN** the agent tries to read a host file, `ATTACH` another database, `COPY` to a file, `INSTALL` or `LOAD` an extension, re-enable external access, or insert into a table
- **THEN** each call returns an error and the database file is unchanged

#### Scenario: Timeout does not leak into the next call
- **WHEN** a long-running statement exceeds the timeout and the agent then runs a short query
- **THEN** the first call returns a timeout error and the second returns its own correct result

#### Scenario: Row cap
- **WHEN** a statement returns 1,500 rows
- **THEN** the tool returns 1,000 rows with `truncated` true
