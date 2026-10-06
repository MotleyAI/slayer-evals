## Context

The repository is empty (licence, `living-architecture.yaml`, OpenSpec). Inputs come from the `slayer` repository:
the feature matrix and probe suite in `slayer/examples/comparisons/` (`matrix.yaml`, `probes.yaml`, `dataset.sql`,
`slayer/models/`, `slayer/run_slayer.py`) and the MCP server `slayer/mcp/server.py` (21 tools, no raw-SQL query tool;
`query` caps output at 20 rows without an explicit `limit`; results as markdown by default, JSON on request). The
hermetic Claude Agent SDK precedent is `bird-agents` (`src/bird_interact_agents/agents/claude_sdk/sdk_env.py`,
`agent.py`): empty `CLAUDE_CONFIG_DIR`, `tools=[]`, `setting_sources=[]`, `disallowed_tools`, post-connect MCP leak
check, telemetry env, pinned prompt caching, explicit auth mode, one spawned process per task.

`slayer mcp` has no way to pin "now" (the engine `create_mcp_server` builds has no clock), tracked as DEV-2058.

## Goals / Non-Goals

**Goals:**
- Credible, reproducible verdicts that separate "right answer" from "right answer via the DSL".
- Any agent can be benchmarked by writing one adapter.
- Failures are diagnosable from the report alone, to drive MCP-surface fixes in `slayer`.

**Non-Goals:**
- Changing SLayer (MCP-surface fixes and DEV-2058 are separate `slayer` PRs).
- Rows Q19 (agent and API surface; every task already exercises it) and Q22 (nested source data; unsupported).
- A cloud runner, an LLM judge, or an OS-level container sandbox.

## Decisions

### Architecture: eight precise nodes under `python` (root package `slayer_evals`, source root `src`)
| Node | Owns | Imports |
|---|---|---|
| `core` | pydantic schemas: task, store manifest, submission, trace, verdict, trial result | — |
| `dataset` | seeded generator, DuckDB build, store template, manifest | core |
| `tasks` | task YAML loading and validation, truth computation, truth snapshots | core |
| `grading` | table comparison, verdict, trace flags | core |
| `agents` | adapter protocol, Claude SDK adapter, `submit_answer`, Python sandbox, trace normalization | core |
| `runner` | trial isolation, run modes, concurrency, auth, result files | core, dataset, tasks, agents, grading, report |
| `report` | markdown report from a run directory | core |
| `cli` | entry point | runner, report, dataset, tasks |

`grading`, `agents` and `report` never import one another: the only seam between an agent and its score is
`core`'s `Submission` and `Trace`. Alternative considered: four coarse nodes (`benchmark`, `grading`, `agents`,
`app`); rejected because `agents` would then import task metadata, losing the import-level guarantee of blind agents.

Spec ownership (`specs:` metadata): `benchmark-dataset`→dataset, `benchmark-tasks`→tasks, `grading`→grading,
`agent-harness`→agents, `benchmark-runs`→runner, `benchmark-report`→report. `core` and `cli` own no behaviour.

`system.arc42.md` principles (exact wording is approved when it lands):
1. Pure grading: a verdict is a function of (task, truth, submission, trace); grading does no I/O and imports only
   `core`. [enforced: arch_check:model-truth] plus a test.
2. Blind agents: an agent receives only the prompt text, its profile and the trial environment. [enforced: test]
3. Agent-agnostic: nothing outside `agents` reads SDK objects. [enforced: arch_check:model-truth]
4. Hermetic sessions: a session loads exactly its profile's MCP servers, with sanitized subprocess environments.
   [enforced: test]
5. Reproducible data: same seed, same tables; truth comes from the built database, never hand-typed.
   [enforced: test]
6. Fix the surface, not the eval: prompts stay generic and capability-neutral. [review] plus the prompt deny-list test.

### Verdict: correct, and answered by a single query
A trial passes when the answer is correct and some successful `query` call's own result matches the truth: the answer
needed no combining of queries and no post-processing. Which DSL features that query uses is not graded — a task's
wording forces its intended feature, and a task that turns out to be solvable another way is refined, not graded
harder. Results are parsed at capture time from markdown and both JSON shapes; the system prompt asks for JSON results,
since SLayer's markdown rounds formatted measures for display. A truncated result fails on row count. Agents name
measures freely and reach dimensions by different paths, so columns resolve by name first and by values second; the
mapping used is recorded in the verdict.

### Trace flags, not hack rules
The verdict carries informational flags read straight off the trace (Python used, raw SQL handed to SLayer, models
edited, SLayer errors, several queries); they do not affect `passed`. Finer failure categories are left to analysis of
the recorded traces and transcripts once real failure modes are known. The Python sandbox (temp cwd, env allow-list,
rlimits, timeout, audit log of file opens) exists for host hygiene and diagnosis.

### Dataset: probe schema at realistic size
A generator with one dedicated `random.Random(seed)` per table, stable iteration order and fixed dates, then planted
edge-case rows appended with reserved ids. Truth snapshots (`tasks/truth/<id>.json`) are generated by the build and
committed; a test re-derives and compares them. Store template models are adapted from the probe suite's
`slayer/models/` (plus saved measures such as `aov` and saved queries such as `monthly_rev`), with the datasource
renamed `bench` and paths made relative to the trial directory.

### Run modes and isolation
`repeat` (N trials each) and `until-pass` (stop at first pass, at most N). One spawned process per trial with fresh
copies of the database and store (bird-agents found a shared event loop hangs SLayer at concurrency ≥3). Auth mode is
an explicit flag; credentials come from `--env-file` (for the baseline, `/home/james/GitHub/SLayer/.env.agents`, a
subscription OAuth token, never copied into the repository).

### Task catalogue (guidance for authoring; each task adapts that row's probes in `probes.yaml`)
| Row | Task sketch | Intended feature |
|---|---|---|
| Q1 | revenue per region and city with the region's total alongside | `sum` + `partition_by` |
| Q2 | each city's share of its region's and of all revenue | ratio with `partition_by` (incl. `[]`) |
| Q3 | per region, the unweighted average of its cities' revenue | nested aggregate over `partition_by` |
| Q4 | same months of the prior year (absolute months); running total; month-over-month % | `time_shift`; `cumsum`; `change_pct` |
| Q5 | revenue split by high/low lifetime-spend customers | calculated dimension over a partitioned aggregate |
| Q6 | revenue per region with average customer credit, fan-out safe | cross-model aggregate `avg(customers.credit)` |
| Q7 | cumulative sum of month-over-month revenue change | nested transform `cumsum(change(...))` |
| Q8 | per-tier customers and revenue without naming the root | root omitted, population inferred |
| Q9 | a fan-out question that triggers SLayer's warning or error | expected warning/error kind surfaced |
| Q10 | customers that are bronze or have any OK order, counted once | filter across a one-to-many join with OR |
| Q11 | trailing-90-day distinct customers per month | `window=` on `count_distinct` |
| Q12 | revenue net of customer discount; weighting by a coarser aggregate | aggregate over cross-model arithmetic; `weighted_avg` weight |
| Q13 | top statuses by revenue showing only the order count | order by an unselected measure |
| Q14 | top customers per region; customers with 3+ consecutive order months | `rank` filter; `consecutive_periods` |
| Q15 | a question needing a query over a query result | multi-stage list or query-backed model then query |
| Q16 | a one-off derived column for one question | inline `source_model` extension |
| Q17 | running total of average order value | transform over saved measure `aov` |
| Q18 | a day-level breakdown of a month-truncated column | expected granularity error surfaced |
| Q20 | revenue in a typed period (`2025-Q1`); last 3 months (xfail DEV-2058) | typed / relative time filter |
| Q21 | revenue by day of week; days between first and last order | `date_part`; `date_diff` |
| Q23 | the saved monthly revenue query refined by region | saved query + `refine` |
| Q24 | top two customers per region (flat output) | `partition_by` + `rank` |
| Q25 | average customer credit per customer vs per order | aggregate locality |

## Risks / Trade-offs

- [A task is solvable without its intended feature] → it still passes; failures and traces show it, and the task's
  wording is refined.
- [Single-trial baseline is noisy] → labelled as a snapshot in the report and README; `--trials` and both run modes
  make repeats cheap.
- [Subscription rate limits stall long runs] → results are written per trial; selection flags allow resuming by
  task subset.
- [Relative-date tasks cannot pass until DEV-2058 ships] → marked xfail with the issue key, reported separately.
