## Why

A profile already means "what the agent is connected to". Adding Motley's MCP server as a profile lets one run compare
SLayer, Motley and raw SQL side by side, so failures can be traced to Motley's MCP surface. Each Motley trial needs its
own org, seeded from the benchmark's store by storyline's seed script (DEV-2258).

## What Changes

- Two opt-in profiles, `motley` and `motley+python`: Motley's MCP server over HTTP, verbatim, plus `submit_answer`, plus
  the Python tool in `motley+python`. The default profiles stay `slayer`, `slayer+python` and `sql+python`.
- New run flags `--motley-url` (default `http://localhost:8000/api/v1/mcp/`) and `--motley-seed-cmd`. Before each
  Motley trial the runner seeds a fresh org for a user id derived from the run and the trial, and the agent sends that
  id as `X-Storyline-Dev-User-Id`. A warm-up seed and an MCP `initialize` at run start fill the embedding cache, record
  the server info and fail fast on a misconfigured backend.
- A session aborts with `error` unless every MCP server its profile declares is connected, in every profile.
- Grading parses Motley's `query` results (JSON with column objects and record rows, and its markdown), reads the bare
  `ClassName: message` error form, and counts only Motley's semantic-layer tools towards `query_errors`.
- A task's `xfail` can name the profiles it applies to; q9 is an expected failure in the Motley profiles until Motley
  returns result warnings.
- The report shows the Motley URL and MCP server info, and notes in each Motley section that Motley's `query` cannot run
  a saved query by name with `refine` yet.
- Profile semantics move into one table in `core`, and the error-kind parser moves to `core` so grading and the report
  share it.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `agent-harness`: Motley profiles, the Motley HTTP server with the identity header, the connected-servers check, and
  the trial environment carrying the Motley URL and user id.
- `benchmark-runs`: profile defaults and opt-in Motley profiles, per-trial org seeding, the warm-up, Motley isolation,
  and Motley run metadata.
- `benchmark-tasks`: profile-scoped `xfail`.
- `grading`: Motley result shapes, the bare error form, Motley profiles in the correctness and single-query criteria,
  and per-surface `query_errors`.
- `benchmark-report`: Motley metadata rows and the Motley section note.

## Impact

- Code: `core` (profile table, trace env, run metadata, result parsing, error kinds, xfail), `agents/claude.py`,
  `grading`, `runner`, `report/render.py`, `cli.py`.
- Tasks: `tasks/capability/q09/q9-credit-by-status.yaml` gains a profile-scoped `xfail`.
- Docs: README gains a "Motley profiles" section.
- External: needs a dev Motley backend with `development.allow_identity_headers: true` and storyline's
  `scripts/seed_eval_org.py` (DEV-2258) to run the Motley profiles; nothing else depends on it.
- No architecture model change: no new import edges, no new capability.
