# slayer-evals

**Do agents actually reach for SLayer's DSL — and does it beat raw SQL on correctness?**

[SLayer](https://github.com/MotleyAI/slayer) is a semantic layer whose query language can express partitioned
aggregates, re-aggregation, time shifts and running totals, rolling windows, ranking, multi-stage queries, inline
model extensions and more. An agent that talks to SLayer through its MCP server *could* answer an analytics question
with one well-formed query — or it could pull raw rows and do the work by hand. This benchmark measures which one
happens, so that every miss can be traced to SLayer's MCP surface (tool descriptions, help, error messages) and fixed
there. It also runs the same questions through an agent that queries the database directly with SQL, including
**traps** where the straightforward SQL silently returns wrong numbers, so the two approaches can be compared on
correctness.

It is a standalone, agent-agnostic harness: the built-in agent is a hermetic [Claude Agent
SDK](https://pypi.org/project/claude-agent-sdk/) agent, and any other agent can be plugged in by writing one adapter.

## What a trial is scored on

Each task is a business question about one seeded demo database, worded so that a single SLayer query answers it,
with its truth computed by hand-written SQL. Every task also carries that reference SLayer query, and a test runs it
to prove the task fair; every trap carries the naive SQL that falls into it, and the same test proves that SQL wrong.
Every trial gets two verdicts:

| Verdict | True when |
| --- | --- |
| **correct** | the submitted table matches the truth (for a refusal task: the answer surfaces SLayer's error or warning; in `sql+python`, an empty answer whose message names the problem) |
| **single query** | the own result of one successful SLayer `query` call or one `sql` statement matches the truth — no combining queries, no post-processing |

A trial passes when both hold. **Correct is the comparison across profiles**: one raw SQL statement can express
almost any answer, so single query is easier for the SQL agent than for the SLayer agents, which need the DSL to do
the same in one query. The report also counts informational flags per trial — used Python, used raw SQL (the `sql`
tool, or SQL handed to SLayer), edited models, hit query errors, ran several queries — which do not affect passing;
every trace and full session transcript is kept for finer diagnosis. The grader is pure and deterministic, and matches
columns by name first and by values second, so agents may name their columns freely.

## Suites

Tasks fall into three suites, by what they cover:

* **capability** — one row of the feature matrix below each (`tasks/capability/`, 25 tasks).
* **combo** — two or three rows at once, with a simple SLayer query still answering them (`tasks/combo/`, 11 tasks).
* **trap** — a row plus a *pitfall*: a question whose straightforward SQL silently returns wrong numbers
  (`tasks/traps/`, 17 tasks).

| Pitfall | The naive SQL… | Task(s) |
| --- | --- | --- |
| `fan_out` | sums a one-side amount after joining a many side | `t-fan-out-items`, `t-fan-out-credit` |
| `count_after_join` | counts rows after a one-to-many join instead of entities | `t-count-after-join` |
| `chasm` | joins two independent facts through their shared parent | `t-chasm` |
| `bridge` | joins through a many-to-many membership table | `t-bridge-email` |
| `non_unique_key` | joins on a column that is only part of the key | `t-city-size` |
| `outer_join_filter` | filters the outer side of a left join in `WHERE` | `t-zero-regions` |
| `not_in_null` | uses `NOT IN` over a list containing NULL | `t-never-returned` |
| `count_outer_join` | counts `*` over a left join, so a missing child counts as one | `t-orders-per-customer` |
| `filtered_total` | filters the numerator of a share but not its denominator | `t-ok-share` |
| `distinct_reagg` | adds up distinct counts of overlapping groups | `t-orders-per-category` |
| `missing_periods` | groups by month and silently drops an empty month | `t-monthly-gaps` |
| `filter_before_window` | filters the dates before a running total or lag reads earlier months | `t-prev-month`, `t-all-time-running` |
| `rows_window_gap` | uses a row-count window over a series with a missing month | `t-rolling-gap` |
| `timestamp_bounds` | bounds a timestamp with `BETWEEN` two dates, losing the last day | `t-march-events` |
| `avg_of_avgs` | averages per-group averages instead of the rows | `t-overall-aov` |

Prompts state what the answer should contain but never the pitfall's mechanism.

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

Most rows are also covered by combo and trap tasks; the report counts a task under every row it covers. Two rows
are deliberately left out: **Q19** (the agent and API surface — every task already exercises it) and **Q22**
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

(or `ANTHROPIC_API_KEY=<key>` for an API key). Then run the tasks covering one row in all three profiles:

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
* **`slayer+python`** — the same plus a Python tool (pandas, numpy, duckdb) running in a fresh subprocess with a
  sandboxed working directory, a clean environment, CPU and memory limits, and an audit log of file opens.
* **`sql+python`** — no SLayer at all: a `sql` tool that runs one DuckDB statement per call on a read-only connection
  to the trial's copy of the database (external access off and locked, 60 s timeout, at most 1,000 rows), plus
  `submit_answer` and the same Python tool, which is not given the database. Tasks that name a saved SLayer definition
  (such as the saved query `monthly_rev`) cannot be done without SLayer, so they fail in this profile without running
  an agent (end reason `auto_fail`).

Every session is hermetic: an empty Claude config directory, no built-in tools, no settings, only the profile's MCP
servers (the trial aborts if any other server appears), and SLayer runs on its own copy of the database and store
with an allow-listed environment. The system prompt is short and generic and identical across profiles, except that
the SLayer profiles are asked to request `query` results as JSON; it never mentions SLayer features.

## Reading the report

`report.md` starts with the run's metadata and a headline table of suite by profile and model, then a table of trap
pitfall by profile, then one section per profile and model: a table of rows Q1–Q25 with trial counts for each
criterion (a multi-row task counts under each of its rows), and a per-task table (pass rate k/N and pass^N for `repeat`; first-try pass, eventual
pass and attempts for `until-pass`). Expected failures, totals (tokens, cost, time) and a digest of every failed
trial follow: which criteria failed, why, and one line per SLayer or `sql` call the agent made. Regenerate a report offline
with `poetry run slayer-evals report runs/<timestamp>`.

## Baseline

`results/baseline/` holds a committed run of every task in all three profiles with Claude Opus 5.5 — its
[report](results/baseline/report.md), results and normalized traces. It is a **single-trial snapshot**: each task ran
once per profile, so individual rates are noisy; use `--trials` for stable numbers. SLayer is pinned to commit
`1653a91` of its main branch (reported as 1.1.0). The `sql+python` trials were rerun after the system prompt gained
its exact-answers sentence; the SLayer profiles ran just before it.

| Suite | Profile | Trials | Correct | Single query | Passed |
| --- | --- | --- | --- | --- | --- |
| capability | `slayer` | 24 | 22 | 20 | 18 |
| capability | `slayer+python` | 24 | 22 | 15 | 15 |
| capability | `sql+python` | 24 (2 auto-failed) | 19 | 17 | 16 |
| combo | `slayer` | 11 | 11 | 4 | 4 |
| combo | `slayer+python` | 11 | 11 | 4 | 4 |
| combo | `sql+python` | 11 (1 auto-failed) | 10 | 6 | 6 |
| trap | `slayer` | 17 | 17 | 10 | 10 |
| trap | `slayer+python` | 17 | 16 | 9 | 8 |
| trap | `sql+python` | 17 | 16 | 16 | 15 |

(The relative-date task is xfail and not counted.) **Correct** is the comparison: the SLayer agent answered every
trap correctly, and so — on this set — did the raw-SQL agent, apart from one answer with an extra empty row; Opus 5.5
avoids these pitfalls in SQL too. The SLayer agents' gap is single query: on traps and combos they often assembled the
right answer from several queries instead of one, most persistently when ordering by an unshown measure (Q13), with
transforms over a date range (Q4, Q7, Q11) and on combos. [docs/baseline-failures.md](docs/baseline-failures.md)
breaks every failure down by profile and pitfall; the report lists each one with its SLayer and `sql` calls.

## Plugging in your own agent

An agent is a class constructed with `model=` whose `async run(inp: AgentInput) -> AgentOutcome` gets only the prompt,
the profile name and the trial environment (store and database copies, the SLayer command, credentials, budgets). It
returns the submission (columns, rows, message) and a normalized `Trace`: the ordered tool calls with their arguments
and raw result text, usage, cost, turns and end reason. Grading never sees your SDK's objects, so any agent works:

```bash
poetry run slayer-evals run --api-key-auth --env-file .env.agents --agent my_package.my_module:MyAgent
```

`slayer_evals.agents.claude.ClaudeAgent` is the reference implementation; `slayer_evals.core.ParsedResult.from_text`
parses SLayer's `query` output and the `sql` tool's output for your trace.

## Adding a task

A task is one YAML file under the folder of its suite (`tasks/capability/`, `tasks/combo/` or `tasks/traps/`):

```yaml
id: t-chasm
covers: [Q6, chasm]
prompt: >-
  For each region that has customers, show the total amount ordered (the sum of order amounts) and the total amount
  returned (the sum of return amounts) by its customers. ...
truth_sql: |
  with o as (...), rt as (...), g as (...)
  select g.region, o.ordered, rt.returned from g left join o ... left join rt ...
slayer_query: {"query": {"source_model": "customers", "dimensions": ["regions.name"],
               "measures": [{"formula": "sum(orders.amount)", "name": "ordered"},
                            {"formula": "sum(returns.amount)", "name": "returned"}]}}
naive_sql: |
  select r.name as region, sum(o.amount) as ordered, sum(rt.amount) as returned
  from customers c left join regions r on ... left join orders o on ... left join returns rt on ...
  group by 1
compare: {keys: [region], values: [ordered, returned]}
```

`covers` lists the rows (Q1–Q25 except Q19 and Q22) and pitfall kinds the task exercises; the suite follows from it.
`slayer_query` is the intended SLayer query, in the arguments of SLayer's MCP `query` tool; `naive_sql` (one statement
or a list) is required on traps and forbidden elsewhere. `compare` sets the key and value columns, `tolerance`,
`ordered`, `columns_exact` and `null_as_zero` (NULL equals 0 in value columns). `expect` turns the task into a refusal
or warning task (one kind or a list), `uses_saved` names the saved SLayer definitions the prompt relies on, and `xfail`
links an issue. Prompts must stay capability-neutral and must not hint at a pitfall (a test enforces a whole-word
deny-list). `tests/test_task_proofs.py` runs every `slayer_query` and `naive_sql` on the built dataset. Then
regenerate and commit the truth snapshot:

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
