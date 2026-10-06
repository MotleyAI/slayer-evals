## Purpose

Defines the contract any agent implements to be benchmarked, and the hermetic Claude Agent SDK agent that runs the
SLayer MCP server verbatim in two tool profiles.

## ADDED Requirements

### Requirement: Agent contract
An agent SHALL receive only the task prompt text, the profile name, and the trial environment (store path, database
path, credentials, budgets). It MUST NOT receive the task's row, capability predicates, allowances, expectations or
truth. It SHALL return a submission (`columns`, `rows`, `message`, or none) and a normalized trace: an ordered list of
tool calls, each with tool name, arguments, raw result text, parsed result (columns and rows, warnings) when the tool
is a SLayer `query`, an error flag, and for the Python tool its audit log; plus usage (input, output, cache read and
cache write tokens), cost, duration, turn count and end reason (`submitted`, `max_turns`, `timeout`, `error`).

#### Scenario: Agent sees only the prompt
- **WHEN** a trial is started for a task
- **THEN** the agent-facing inputs contain the prompt text and none of the task's other fields

#### Scenario: Trace round-trip
- **WHEN** a normalized trace is serialized to JSON and read back
- **THEN** it equals the original

### Requirement: Hermetic Claude session
The Claude Agent SDK agent SHALL run each trial in an empty Claude configuration directory, with no built-in tools,
no settings sources, and only the MCP servers its profile declares; after connecting it MUST verify that no other MCP
server is loaded and abort the trial otherwise. The SLayer MCP server SHALL run as `slayer mcp` over stdio on the
trial's store copy with a sanitized environment (an allow-list; no Claude or Anthropic credentials). Telemetry and
non-essential traffic SHALL be disabled and the prompt-caching mode pinned. The system prompt SHALL be minimal,
generic and identical across tasks: it MUST NOT mention SLayer features or tasks; it SHALL tell the agent to request
`query` results as JSON so numbers are exact.

#### Scenario: Leaked server aborts
- **WHEN** after connecting the session reports an MCP server the profile did not declare
- **THEN** the trial ends with end reason `error` and a message naming the server

#### Scenario: SLayer subprocess has no credentials
- **WHEN** the SLayer server is launched
- **THEN** its environment contains no `CLAUDE_CODE_OAUTH_TOKEN`, `ANTHROPIC_API_KEY` or `ANTHROPIC_AUTH_TOKEN`

### Requirement: Profiles
Profile `slayer` SHALL expose every tool the SLayer MCP server advertises plus `submit_answer`. Profile
`slayer+python` SHALL additionally expose a Python tool that runs code in a subprocess with a fresh sandbox working
directory, a sanitized environment, CPU-time and memory limits, a per-call timeout, pandas, numpy and duckdb
installed, and an audit hook recording file opens and subprocess launches.

#### Scenario: Profile tool sets
- **WHEN** a session starts in each profile
- **THEN** the model is offered exactly the SLayer tools plus `submit_answer`, and in `slayer+python` also the Python tool

#### Scenario: Python audit log
- **WHEN** code in the Python tool opens a file outside its sandbox directory
- **THEN** the call's audit log in the trace records the path

#### Scenario: Python timeout
- **WHEN** code in the Python tool runs past its timeout
- **THEN** the call returns an error result and the session continues

### Requirement: Answer submission
`submit_answer` SHALL accept `columns` (list of names), `rows` (list of lists) and `message` (text). The first
submission ends the trial. A submission whose rows do not all have `len(columns)` values MUST be rejected back to the
agent as a tool error without ending the trial.

#### Scenario: Ragged submission rejected
- **WHEN** the agent submits a row with fewer values than columns
- **THEN** the tool returns an error and the trial continues

### Requirement: Budgets and end reasons
A trial SHALL end at the first of: a valid submission, the turn budget (default 60), or the wall-clock budget
(default 15 minutes); the end reason SHALL be recorded and a partially streamed transcript kept on disk. Usage SHALL be
taken from the session's final result message, falling back to de-duplicated per-turn usage marked `partial` when
the session ends abnormally.

#### Scenario: Timeout keeps the transcript
- **WHEN** a trial exceeds its wall-clock budget
- **THEN** its end reason is `timeout` and the transcript written so far is on disk
