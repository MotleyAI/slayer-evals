## Context

See proposal.md (Why) and the delta specs for the behaviour.

- **Profile meaning is scattered.** `SLAYER_PROFILES` / `PYTHON_PROFILES` (`agents/claude.py`) and `RAW_SQL_PROFILE`
  (`runner/run.py`, `grading/verdict.py`) are hand-kept tuples. Two more profiles would multiply them.
- **The error-kind regex is duplicated.** `grading/errors.py` and `report/render.py` each hold a copy.
- **Motley's MCP surface** (storyline `origin/main`, `backend/storyline/api/mcp/`):
  - 28 tools. `query` is the data tool. `inspect` and `search` read the semantic layer. `create_model`, `edit_model`,
    `delete`, `save_memory` and `switch_branch` write it. The rest are documents, blocks, masters, feedback and
    identity. `list_resources` mixes datasources and branches with documents, masters and styles.
  - `query` JSON (the default format) is `{"columns": [{name, role, type, title, granularity, aggregation}], "rows":
    [{"<model>.<column>": value}], "row_count", "truncated", "hint"?, "sql"?, "history_url"?, "reminder"?}`, dumped with
    `indent=2`. It has no `warnings` key: Motley drops SLayer's result warnings (DEV-1951).
  - `query` markdown is a bare table with qualified headers and empty cells for nulls, then an optional fenced SQL
    block, then a footer `_(N rows)_` or `_(truncated to N rows — …)_`, then an optional reminder.
  - The default `limit` is 100. Every truth table has at most 50 rows.
  - A tool error is `str(exc)` with `isError`, with no tool prefix and no class name, except SLayer's `QueryTypeError`
    family, whose messages start with the class name (`TimeDimensionColumnError: …`).
  - `initialize` reports `{"name": "motley", "version": <the mcp package version>}`, because Motley passes no version.
  - Motley's `query`, `create_model` and `edit_model` take SLayer's argument shapes.
  - Identity: with `development.allow_identity_headers: true`, `X-Storyline-Dev-User-Id`
    (`[A-Za-z0-9_-]{1,64}`, full match) picks the user. The `Host` must match `public_base_url`'s netloc, else 421.
- **The seed (DEV-2258)** is `scripts/seed_eval_org.py --user-id --store --db`. It is dev-only, needs an absolute
  `--db`, opens DuckDB read-only, never writes the store, refuses an existing user id or org, runs in one transaction,
  copies embeddings from any org with a matching content hash and computes the rest inline, and warns about dropped
  custom granularities.

## Goals / Non-Goals

**Goals:**
- One table in `core` decides what each profile is. Adding a profile adds one entry.
- One error-kind parser, shared by grading and the report.
- An infrastructure failure (a seed, the backend, a declared server that is not connected) becomes an `error` trial or
  stops the run. It never reads as a wrong answer.

**Non-Goals:**
- A Motley baseline run and committed Motley results. The seed lands with DEV-2258.
- A live test against a real Motley backend.
- Run-by-name with `refine` (DEV-2260), result warnings (DEV-1951) and custom granularities (DEV-2261) on the Motley
  side.
- Cleaning up eval orgs. DEV-2258 says to recreate the local database instead.

## Decisions

1. **Motley metadata = URL plus `serverInfo` as reported**, labelled "MCP server info". It is the mcp package version,
   not a Motley build. Making Motley report a build version (a git describe) was weighed and dropped: the version only
   serves provenance, the user controls what is brought up, and DEV-2258 stays untouched. (user)
2. **Warm-up at run start.** When a Motley profile is selected, seed a `warm-up` org, then run MCP `initialize` over
   streamable HTTP with that user's header. It fills the embedding cache once, so concurrent first seeds do not each
   embed everything, and it fails fast on a misconfigured backend. The alternative was no warm-up, with a header-less
   `initialize`. (user)
3. **Default profiles stay `slayer`, `slayer+python`, `sql+python`; the Motley profiles are opt-in.** The alternatives
   were all five by default, or a default that depends on whether a seed command is given. (user)
4. **q9 under Motley is a profile-scoped xfail** (`XFail.profiles`, DEV-1951). A hard-coded note in the report was the
   alternative. The run-by-name gap (DEV-2260) is one sentence at the top of each Motley section, because the
   saved-query tasks can still pass. (user, approved wording) "Motley's `query` cannot run a saved query by name with
   `refine` yet (DEV-2260); saved-query tasks are answered with one inline query."
5. **Motley `query_errors` counts an allow-list of 8 semantic-layer tools**: `query`, `inspect`, `search`,
   `create_model`, `edit_model`, `delete`, `save_memory`, `switch_branch`. `list_resources` is excluded. A deny-list of
   product tools was the alternative; a new product tool would silently pollute it. (user)
6. **All Motley orgs read the run's one database file**, given as an absolute path: the built dataset's
   `bench.duckdb`, not the trial copy. DEV-2258 opens it read-only and tests concurrent orgs on one file. (default)
7. **User id = `se-<run dir name>-<first 12 hex of sha256("<absolute run dir>|<label>")>`.** The label is the trial
   stem, or `warm-up`. It is at most 35 characters, and it is unique across runs because the absolute run directory is
   unique, which matters because DEV-2258 refuses existing ids. (default)
8. **Seed lifecycle.** The seed runs inside the trial's concurrency slot, before the agent process, with a 600 s
   timeout. It gets `_child_env()` (the runner's environment without the Claude credentials). It runs in its own
   process group, which is killed and reaped in `finally` on timeout or cancellation. Its time is not counted in the
   trial's duration. A failure ends that trial with `error` and `motley seed failed (exit N): <stderr tail>`, and no
   agent starts. On success its output is discarded. The warm-up's stderr goes to the user's stderr, where the
   granularity warning appears once. (default; process-group cleanup (codex))
9. **Every warm-up failure becomes one exception type, `MotleyWarmUpError`, which the CLI catches (exit 2).** This
   covers a seed that cannot launch, fails or times out, a refused connection, an HTTP error, a timeout and an MCP
   protocol error. The cause is kept, and a 421 adds the hint that the `--motley-url` host must match the backend's
   `public_base_url`. (codex)
10. **`ProfileSpec(BaseModel)` in `core`**: `surface: Literal["slayer", "motley", "sql"]` and `python: bool`, in
    `PROFILE_SPECS: dict[Profile, ProfileSpec]`. `PROFILES` is its key tuple, and `DEFAULT_PROFILES` holds the three.
    The agent's servers, tools and system prompt, the runner's auto-fail and seeding, grading's raw-SQL refusal and
    `query_errors` set, and the report's Motley note all read it. (default, structural)
11. **`error_kind` moves to `core`.** Grading and the report's digest share it. The bare form needs a name ending in
    `Error` or `Exception` at the start of the text, directly followed by `: `, so labels such as `SQL:`, `Note:` and
    `Invalid arguments:` are not read as classes. (default, structural; bare-form constraint (codex))
12. **Result parsing dispatches on the column entries.** Strings with list rows are the `sql` tool's shape. Objects
    with a unique string `name`, plus records whose keys are exactly those names, are Motley's. Anything else is not a
    table, so a missing key never becomes a silent `None`. `truncated: true` becomes a `truncated` warning. The markdown
    trailer after the table is scanned for Motley's truncation footer wherever it sits, around a SQL block and a
    reminder. (codex)
13. **The session requires every declared server to be connected, in every profile.** A missing declared server, or
    one reported with any status other than `connected`, ends the trial with `error` before the prompt is sent, naming
    the server and its status. Extra servers still abort. Before this change only extras were checked, so a down
    Motley backend or a crashed `slayer mcp` would have read as the agent answering wrongly. (user; raised by codex)
14. **An `integration`-marked test proves the header reaches the server.** It starts the real Claude SDK client
    against a local streamable-HTTP MCP server that records request headers. It connects, reads `get_mcp_status`, and
    checks that `X-Storyline-Dev-User-Id` arrived on `initialize` and `tools/list`. It sits outside the unit suite,
    like the existing smoke test. (user; raised by codex)
15. **The JSON-results sentence applies to the Motley profiles verbatim**, as the tracker issue says. Its "the default
    markdown rounds some values" clause does not hold for Motley, whose default is JSON and whose markdown does not
    round. That is harmless, and changing the sentence would change the SLayer prompt the committed baseline was run
    with. (default)
16. **`edited_models` stays `create_model` / `edit_model`.** Motley's `delete` does not count, matching SLayer's
    `delete_model`. `raw_sql` and `several_queries` carry over unchanged, because Motley's argument shapes are SLayer's.
    (default)
17. **Tests also pin the user ids** across profiles, models, trials, `-k` run-directory suffixes and `warm-up`, plus a
    full match against the real pattern at maximum length. **`--profiles` help** is built from all five `PROFILES`,
    while the default stays `DEFAULT_PROFILES`. (codex)
18. **The committed baseline report stays byte-identical.** `RunMetadata`'s new Motley fields default to `None`, and
    their report rows appear only when set. (default)
19. **README** gains a "Motley profiles" section: the flags, the backend config (dev environment,
    `allow_identity_headers`, a URL host that matches `public_base_url`), the warm-up, and a pointer to storyline's
    `docs/eval_org_seed.md`. (default)

## Risks / Trade-offs

- **[Risk]** The Claude CLI might not send the configured headers on every HTTP MCP request. Without the header,
  Motley silently uses the configured identity, so every trial would land in one org. → The integration test in
  decision 14, and the connected-servers check.
- **[Risk]** Motley's result shapes could change on storyline `main`. → The parser rejects unknown shapes instead of
  guessing, and the report's digest shows the call.
- **[Risk]** The warm-up seed computes every embedding on a fresh database, which is slow. → It happens once per run,
  under the 600 s seed timeout. Later seeds copy.
- **[Trade-off]** "MCP server info" records the mcp package version, not Motley's. Runs are told apart by URL and
  date.
- **[Trade-off]** The connected-servers check also changes the SLayer profiles: a `slayer mcp` that fails at startup
  now gives `error` instead of a scored failure.
