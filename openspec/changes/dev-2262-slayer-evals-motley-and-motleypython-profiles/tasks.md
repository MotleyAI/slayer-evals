## 1. Core

- [x] 1.1 `ProfileSpec(BaseModel)` (`surface`, `python`) and `PROFILE_SPECS` for all five profiles; `Profile` / `PROFILES` from it; `DEFAULT_PROFILES` = `slayer`, `slayer+python`, `sql+python` (design decisions 3, 10). Verify a core test that every profile has a spec and the defaults are the three.
- [x] 1.2 `TrialEnv` gains `motley_url` and `motley_user_id` (optional); `RunMetadata` gains `motley_url` and `motley_server_info` (default `None`). Verify trace and metadata round-trip tests, and that the committed baseline `metadata.json` still loads.
- [x] 1.3 `XFail.profiles: list[Profile]` (empty = every profile) with a method answering whether it applies to a profile. Verify the benchmark-tasks xfail scenarios (loads; unknown profile rejected).
- [x] 1.4 Move `error_kind` into `core`: the prefixed form, plus a bare `<Name>(Error|Exception): ` at the start of the text (design decision 11). Delete `grading/errors.py`. Verify tests: prefixed, bare `TimeDimensionColumnError: …`, and `SQL: …`, `Note: …`, `Invalid arguments: …` giving `None`.
- [x] 1.5 `ParsedResult.from_text`: dispatch JSON `columns` on the entry type; parse Motley's column objects plus records strictly; turn `truncated: true` into a `truncated` warning; scan the markdown trailer for Motley's `_(truncated to N rows …)_` footer (design decision 12). Verify the grading parsing scenarios: both JSON `columns` shapes, a malformed column object, a duplicate name, a missing key, an empty result, and markdown with footer / SQL block + footer / footer + reminder / all three, truncated and not.

## 2. Tasks

- [x] 2.1 q9 gains `xfail: {issue: DEV-1951, reason: "Motley's query drops result warnings", profiles: [motley, motley+python]}`. Verify `slayer-evals truth` passes and the task loads with the scoped xfail.

## 3. Agents

- [x] 3.1 `agents/claude.py` reads `PROFILE_SPECS` instead of `SLAYER_PROFILES` / `PYTHON_PROFILES`. Motley profiles configure the HTTP server `motley` with the URL and the `X-Storyline-Dev-User-Id` header; `bench` gets `submit_answer` plus `python` when `python`; no `sql` tool and no SLayer server; the JSON sentence for the SLayer and Motley surfaces; `motley_server {url, user_id}` in the transcript's `Session` line. Verify the agent-options tests per Motley profile (servers, HTTP config, allowed tools, bench tools, system prompt equal to SLayer's).
- [x] 3.2 Connected-servers check: after connecting, the reported servers must be exactly the declared ones, each `connected`; otherwise `error` naming the server and its status, with no prompt sent (design decision 13). Verify fake-SDK tests: an extra `slayer` in `motley`, a missing `motley`, a missing `bench`, a `motley` reported `failed`, and exact success; the existing leak tests still pass.
- [x] 3.3 `integration`-marked test: the real Claude SDK client against a local streamable-HTTP MCP server that records request headers; connect, `get_mcp_status`, then assert `X-Storyline-Dev-User-Id` reached `initialize` and `tools/list` (design decision 14). Verify it passes when run explicitly with `-m integration`.

## 4. Grading

- [x] 4.1 `grading/verdict.py` uses `core.error_kind` and decides the raw-SQL refusal on surface `sql`. Verify verdict tests: a Motley error task passes through the bare form; a Motley warning task is graded as in SLayer; a `uses_saved` task is not auto-failed in `motley`.
- [x] 4.2 `grading/flags.py`: `trace_flags` takes the profile; `query_errors` uses the surface's data tools (SLayer: every non-bench tool; `sql`: `sql`; Motley: the 8-tool allow-list). Verify the grading flag scenarios, including the Motley product-tool one; the SLayer and SQL flag tests are unchanged.

## 5. Runner and CLI

- [x] 5.1 Motley user id `se-<run dir name>-<hash12>` from the absolute run directory and the label (design decision 7). Verify tests: a full match of `[A-Za-z0-9_-]{1,64}` at maximum length, deterministic, distinct across profiles, models, trials, `-k` run-directory suffixes and `warm-up`.
- [x] 5.2 `RunConfig` gains `motley_url` (default `http://localhost:8000/api/v1/mcp/`) and `motley_seed_command`; `profiles` defaults to `DEFAULT_PROFILES`; a Motley profile without a seed command refuses to start. `Combo.auto_fails` reads the surface. Verify runner tests: the default profiles are the three; refusal names `--motley-seed-cmd`.
- [x] 5.3 Per-trial seed (design decision 8): argv `--user-id`, `--store <trial store copy>`, `--db <absolute built database>`; `_child_env()`; inside the semaphore before the agent; own process group, killed and reaped in `finally`; 600 s timeout; failure → `error` trial with `motley seed failed (exit N): <stderr tail>` and no agent; `TrialEnv` carries the URL and the user id. Verify runner tests with a fake seed script: recorded argv and env (no Claude credentials), seed before agent, the agent's env carries the id and URL, a failing seed gives an `error` trial carrying the stderr tail with no agent run, and a timed-out seed whose spawned sleeper does not survive.
- [x] 5.4 Warm-up (design decisions 2, 9): seed `warm-up`, then streamable-HTTP `initialize` with its header (60 s timeout); record `motley_url` and `motley_server_info` (`<name> <version>`); every failure → `MotleyWarmUpError` (421 hint), caught by the CLI with exit 2; the warm-up's stderr goes to the user's stderr. Verify runner tests against a fake Motley FastMCP streamable-HTTP server subprocess reporting a known version (metadata recorded), and refusals with no trials for: a missing seed executable, a failing seed, a refused connection, an `initialize` timeout and a 421.
- [x] 5.5 Profile-scoped xfail in `TrialResult.xfail`. Verify the benchmark-runs profile-scoped xfail scenario.
- [x] 5.6 CLI: `--motley-url`, `--motley-seed-cmd` (shlex), `--profiles` help listing all five while the default stays the three. Verify CLI tests for parsing, the defaults and the help text.

## 6. Report

- [x] 6.1 `report/render.py`: `core.error_kind` in the digest; `Motley MCP` and `MCP server info` metadata rows only when set; the approved DEV-2260 sentence (design decision 4) at the top of each Motley profile's section. Verify the report scenarios (Motley run report, run without Motley) and the existing byte-identical baseline test.

## 7. Docs and finish

- [x] 7.1 README "Motley profiles" section (design decision 19). Verify it names both flags, the backend config and the seed docs.
- [x] 7.2 Run the full non-integration suite, `ruff`, the type-check against its baseline, `la-arch-check` and `npx likec4 validate`. All must pass.
