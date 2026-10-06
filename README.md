# slayer-evals

**Do agents actually reach for SLayer's DSL?**

[SLayer](https://github.com/MotleyAI/slayer) is a semantic layer whose query language can express partitioned
aggregates, re-aggregation, time shifts and running totals, rolling windows, ranking, multi-stage queries, inline
model extensions and more. An agent that talks to SLayer through its MCP server *could* answer an analytics question
with one well-formed query — or it could pull raw rows and do the work by hand. This benchmark measures which one
happens, so that every miss can be traced to SLayer's MCP surface (tool descriptions, help, error messages) and fixed
there.

It is a standalone, agent-agnostic harness: the built-in agent is a hermetic [Claude Agent
SDK](https://pypi.org/project/claude-agent-sdk/) agent, and any other agent can be plugged in by writing one adapter.

## What a trial is scored on

Each task is a business question about one seeded demo database, worded so that a single SLayer query using the
row's capability answers it, with its truth computed by hand-written SQL. Every trial gets two verdicts:

| Verdict | True when |
| --- | --- |
| **correct** | the submitted table matches the truth (for a refusal task: the answer surfaces SLayer's error or warning) |
| **single query** | one successful SLayer `query` call's own result matches the truth — no combining queries, no post-processing |

A trial passes when both hold. The report also counts informational flags per trial — used Python, handed SLayer raw
SQL, edited models, hit SLayer errors, ran several queries — which do not affect passing; every trace and full session
transcript is kept for finer diagnosis. The grader is pure and deterministic, and matches columns by name first and
by values second, so agents may name their columns freely.

## Covered rows

The rows come from the feature matrix behind [Four open-source semantic layers, 54
capabilities](https://motley.ai/blog-posts/four-open-source-semantic-layers-54-capabilities/).

| Row | Capability | Task(s) |
| --- | --- | --- |
| Q1 | Coarser grain in the same query | `q1-region-total` |
| Q2 | Arithmetic across grains | `q2-city-share` |
| Q3 | Re-aggregation | `q3-avg-city-revenue` |
| Q4 | Transforms / time shift | `q4-running-total`, `q4-prior-year` |
| Q5 | Calculated dimensions | `q5-spend-band` |
| Q6 | Fields from many models, fan-out safe | `q6-region-credit` |
| Q7 | Deep composition | `q7-cumulative-change` |
| Q8 | Population inference | `q8-tier-customers` |
| Q9 | No silently wrong numbers (warning surfaced) | `q9-credit-by-status` |
| Q10 | Filters across one-to-many joins | `q10-bronze-or-ok` |
| Q11 | Rolling time windows | `q11-rolling-customers` |
| Q12 | Aggregates as arguments | `q12-net-revenue` |
| Q13 | Order by what you don't show | `q13-top-cities-count` |
| Q14 | Ranking | `q14-top-customer-per-region` |
| Q15 | Multi-stage queries | `q15-revenue-bands` |
| Q16 | Inline model extension | `q16-order-size` |
| Q17 | Saved measures that compose | `q17-running-aov` |
| Q18 | Time-bucket safety (error surfaced) | `q18-day-of-monthly` |
| Q20 | Relative & typed filters | `q20-quarter-region`, `q20-last-three-months` (xfail) |
| Q21 | Calendar expressions | `q21-weekday-revenue` |
| Q23 | Saved queries & refinement | `q23-monthly-by-region` |
| Q24 | Nested results (flattened) | `q24-top-two-per-region` |
| Q25 | Explicit aggregate locality | `q25-credit-per-order` |

Two rows are deliberately left out: **Q19** (the agent and API surface — every task already exercises it) and **Q22**
(nested source data — SLayer does not support it). Tasks marked `xfail` run but are reported separately until the
linked issue is fixed: relative dates ("last three months") need SLayer's MCP server to pin "now".

## Five-minute quickstart

You need Python 3.12, [Poetry](https://python-poetry.org/) and a Claude subscription or API key.

```bash
git clone https://github.com/MotleyAI/slayer-evals.git
cd slayer-evals
poetry install
```

Put a credential into an env file. With a Claude subscription, create a long-lived token with Claude Code's
`claude setup-token` and save it:

```bash
echo "CLAUDE_CODE_OAUTH_TOKEN=<the token>" > .env.agents
```

(or `ANTHROPIC_API_KEY=<key>` for an API key). Then run one row in both profiles:

```bash
poetry run slayer-evals run --subscription-auth --env-file .env.agents --rows Q1
```

Use `--api-key-auth` with an API key. The auth mode is never guessed from whichever credential happens to be set.
The run writes `runs/<timestamp>/` with `report.md`, `results.jsonl`, `metadata.json`, one normalized trace per trial
in `traces/` and the full session transcript (every message and tool call) in `transcripts/`.

Useful flags: `--tasks q1-region-total,q4-running-total`, `--profiles slayer`, `--models claude-opus-5-5`,
`--trials 3` with `--mode repeat` (N trials each) or `--mode until-pass` (stop at the first pass),
`--concurrency 3`, `--max-turns 60`, `--timeout 900`, and `--slayer-command "/path/to/your/slayer"` to test a local
SLayer checkout.

## Profiles

* **`slayer`** — the SLayer MCP server, verbatim, plus `submit_answer`.
* **`slayer+python`** — the same plus a Python tool (pandas, numpy) running in a fresh subprocess with a sandboxed
  working directory, a clean environment, CPU and memory limits, and an audit log of file opens.

Every session is hermetic: an empty Claude config directory, no built-in tools, no settings, only the profile's MCP
servers (the trial aborts if any other server appears), and SLayer runs on its own copy of the database and store
with an allow-listed environment. The system prompt is short and generic; it never mentions SLayer features.

## Reading the report

`report.md` starts with the run's metadata, then one section per profile and model: a table of rows Q1–Q25 with
trial counts for each criterion, and a per-task table (pass rate k/N and pass^N for `repeat`; first-try pass, eventual
pass and attempts for `until-pass`). Expected failures, totals (tokens, cost, time) and a digest of every failed
trial follow: which criteria failed, why, and one line per SLayer call the agent made. Regenerate a report offline
with `poetry run slayer-evals report runs/<timestamp>`.

## Baseline

`results/baseline/` holds a committed run of every task in both profiles with Claude Opus 5.5 — its
[report](results/baseline/report.md), results and normalized traces. It is a **single-trial snapshot**: each task ran
once per profile, so individual rates are noisy; use `--trials` for stable numbers.

| Profile | Tasks scored | Correct | Single query | Passed |
| --- | --- | --- | --- | --- |
| `slayer` | 24 | 23 | 19 | 19 |
| `slayer+python` | 24 | 23 | 18 | 17 |

(The relative-date task is xfail and not counted.) The agent got almost every answer right, but in about one task in
five it reached the answer by combining queries, hand-written SQL or Python instead of one SLayer query — most
often on rolling windows (Q11), ordering by an unshown measure (Q13), deep composition (Q7) and fan-out-safe
cross-model aggregates (Q6). Each failure is listed with its SLayer calls in the report.

## Plugging in your own agent

An agent is a class constructed with `model=` whose `async run(inp: AgentInput) -> AgentOutcome` gets only the prompt,
the profile name and the trial environment (store and database copies, the SLayer command, credentials, budgets). It
returns the submission (columns, rows, message) and a normalized `Trace`: the ordered tool calls with their arguments
and raw result text, usage, cost, turns and end reason. Grading never sees your SDK's objects, so any agent works:

```bash
poetry run slayer-evals run --api-key-auth --env-file .env.agents --agent my_package.my_module:MyAgent
```

`slayer_evals.agents.claude.ClaudeAgent` is the reference implementation; `slayer_evals.core.ParsedResult.from_text`
parses SLayer's `query` output for your trace.

## Adding a task

A task is one YAML file under `tasks/`:

```yaml
id: q1-region-total
row: Q1
prompt: >-
  For every region and city, show the city's revenue (the sum of order amounts) and, on the same row, the total
  revenue of the region the city belongs to.
truth_sql: |
  select region, city, sum(amount) as revenue, sum(sum(amount)) over (partition by region) as region_total
  from orders_flat group by 1, 2
compare: {keys: [region, city], values: [revenue, region_total]}
```

Prompts must stay capability-neutral (no DSL names — a test enforces a deny-list), yet worded so that one query
using the row's capability answers them. `expect` turns the task into a refusal or warning task (one kind or a list),
and `xfail` links an issue. Then regenerate and commit the truth snapshot:

```bash
poetry run slayer-evals truth --write
```

`poetry run slayer-evals build --out data` builds the database and store template on their own if you want to
explore them.

## Development

```bash
poetry run ruff check .
poetry run basedpyright
poetry run pytest -m "not integration"
```

## Licence

MIT — see [LICENSE](LICENSE).
