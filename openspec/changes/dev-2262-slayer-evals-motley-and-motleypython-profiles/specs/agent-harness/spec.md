## MODIFIED Requirements

### Requirement: Agent contract
An agent SHALL receive only the task prompt text, the profile name, and the trial environment (store path, database
path, credentials, budgets, and in the Motley profiles the Motley MCP URL and the trial's Motley user id). It MUST NOT
receive the task's covers, comparison rules, expectations, reference SLayer query, naive SQL or truth. It SHALL return a
submission (`columns`, `rows`, `message`, or none) and a normalized trace: the profile; an ordered list of tool calls,
each with tool name, arguments, raw result text, parsed result (columns and rows, warnings) when the tool is a SLayer or
Motley `query` or the `sql` tool, an error flag, and for the Python tool its audit log; plus usage (input, output, cache
read and cache write tokens), cost, duration, turn count and end reason (`submitted`, `max_turns`, `timeout`, `error`,
`auto_fail`).

#### Scenario: Agent sees only the prompt
- **WHEN** a trial is started for a task
- **THEN** the agent-facing inputs contain the prompt text and none of the task's other fields

#### Scenario: Motley trial environment
- **WHEN** a trial is started in `motley`
- **THEN** the agent's trial environment carries the Motley MCP URL and the trial's Motley user id, and still none of the task's other fields

#### Scenario: Trace round-trip
- **WHEN** a normalized trace is serialized to JSON and read back
- **THEN** it equals the original

### Requirement: Hermetic Claude session
The Claude Agent SDK agent SHALL run each trial in an empty Claude configuration directory, with no built-in tools,
no settings sources, and only the MCP servers its profile declares: the SLayer server and the in-process `bench`
server in the SLayer profiles, the Motley server and the `bench` server in the Motley profiles, and only the `bench`
server in `sql+python`. After connecting it MUST verify that the loaded MCP servers are exactly the declared ones and
that each is connected, and otherwise abort the trial with end reason `error` and a message naming the server and its
status. The SLayer MCP server SHALL run as `slayer mcp` over stdio on the trial's store copy with a sanitized
environment (an allow-list; no Claude or Anthropic credentials). The Motley MCP server SHALL be reached over HTTP at the
run's Motley URL, with the trial's Motley user id sent as the `X-Storyline-Dev-User-Id` header on every request and no
credentials. Telemetry and non-essential traffic SHALL be disabled and the prompt-caching mode pinned. The system
prompt SHALL be minimal, generic and identical across tasks and profiles, except that the SLayer and Motley profiles
alone carry one sentence telling the agent to request `query` results as JSON so numbers are exact; it SHALL ask every
agent to submit exact, unrounded values with null as the label of a group whose key is unknown; it MUST NOT mention
SLayer or Motley features or tasks.

#### Scenario: Leaked server aborts
- **WHEN** after connecting the session reports an MCP server the profile did not declare
- **THEN** the trial ends with end reason `error` and a message naming the server

#### Scenario: Missing or failed server aborts
- **WHEN** after connecting a declared MCP server is not reported, or is reported with a status other than connected
- **THEN** the trial ends with end reason `error` and a message naming the server and its status, and no prompt is sent

#### Scenario: SLayer subprocess has no credentials
- **WHEN** the SLayer server is launched
- **THEN** its environment contains no `CLAUDE_CODE_OAUTH_TOKEN`, `ANTHROPIC_API_KEY` or `ANTHROPIC_AUTH_TOKEN`

#### Scenario: No SLayer in the raw-SQL profile
- **WHEN** a session starts in `sql+python`
- **THEN** no SLayer server is configured or launched, and a SLayer server reported after connecting aborts the trial

#### Scenario: Motley server carries the trial identity
- **WHEN** a session starts in `motley` or `motley+python`
- **THEN** the only data server configured is the Motley server at the run's Motley URL, every request to it carries `X-Storyline-Dev-User-Id` with the trial's user id, and a SLayer server reported after connecting aborts the trial

#### Scenario: System prompt per profile
- **WHEN** the system prompts of the five profiles are compared
- **THEN** they are equal apart from the JSON-results sentence, which appears in `slayer`, `slayer+python`, `motley` and `motley+python` only

### Requirement: Profiles
Profile `slayer` SHALL expose every tool the SLayer MCP server advertises plus `submit_answer`. Profile
`slayer+python` SHALL additionally expose a Python tool that runs code in a subprocess with a fresh sandbox working
directory, a sanitized environment, CPU-time and memory limits, a per-call timeout, pandas, numpy and duckdb
installed, and an audit hook recording file opens and subprocess launches. Profile `motley` SHALL expose every tool the
Motley MCP server advertises plus `submit_answer`, and profile `motley+python` those plus the same Python tool. Profile
`sql+python` SHALL expose `submit_answer`, the same Python tool, and the `sql` tool, and no SLayer or Motley tool; its
Python tool MUST NOT be given the database path.

#### Scenario: Profile tool sets
- **WHEN** a session starts in each profile
- **THEN** the model is offered exactly the SLayer tools plus `submit_answer` in `slayer`, those plus the Python tool in `slayer+python`, the Motley tools plus `submit_answer` in `motley`, those plus the Python tool in `motley+python`, and exactly `submit_answer`, the Python tool and `sql` in `sql+python`

#### Scenario: Python audit log
- **WHEN** code in the Python tool opens a file outside its sandbox directory
- **THEN** the call's audit log in the trace records the path

#### Scenario: Python timeout
- **WHEN** code in the Python tool runs past its timeout
- **THEN** the call returns an error result and the session continues
