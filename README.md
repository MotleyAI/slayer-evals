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

Each task is a business question about one of two seeded demo databases, answerable by a single SLayer query,
with its truth computed by hand-written SQL. Every task also carries that reference SLayer query, and a test runs it
to prove the task fair; every trap carries the naive SQL that falls into it, and the same test proves that SQL wrong.
Every trial gets two verdicts:

| Verdict | True when |
| --- | --- |
| **correct** | the submitted table matches the truth (for a refusal task: the answer surfaces SLayer's error or warning; for an expected error, an empty answer whose message names the problem also counts, and in `sql+python`, for an expected warning, a message naming the problem counts whatever the answer) |
| **single query** | the own result of one successful SLayer `query` call or one `sql` statement matches the truth — no combining queries, no post-processing |

A trial passes when both hold. **Correct is the comparison across profiles**: one raw SQL statement can express
almost any answer, so single query is easier for the SQL agent than for the SLayer agents, which need the DSL to do
the same in one query. The report also counts informational flags per trial — used Python, used raw SQL (the `sql`
tool, or SQL handed to SLayer), edited models, hit query errors, ran several queries — which do not affect passing;
every trace and full session transcript is kept for finer diagnosis. The grader is pure and deterministic, and matches
columns by name first and by values second, so agents may name their columns freely.

## Suites

Tasks fall into four suites. Three run on the benchmark's own database and follow from what they cover:

* **capability** — one row of the feature matrix below each (`tasks/capability/`, 34 tasks).
* **combo** — two or three rows at once, with a simple SLayer query still answering them (`tasks/combo/`, 15 tasks).
* **trap** — a row plus a *pitfall*: a question whose straightforward SQL silently returns wrong numbers
  (`tasks/traps/`, 21 tasks).

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
| `count_after_unnest` | unnests a list, then counts rows, so an entity counts once per matching element | `t-vip-per-tier` |
| `unnest_fan_out` | sums an entity-level amount after unnesting its list | `t-tagged-credit` |
| `null_element` | uses `<> ALL` / `NOT IN` over a list holding a NULL element, which drops the row | `t-without-vip` |
| `same_element_and` | requires two values of one unnested element (`tag = 'x' AND tag = 'y'`), which matches nothing | `t-vip-and-eu-region` |

Prompts state what the answer should contain but never the pitfall's mechanism.

The fourth suite, **jaffle**, runs on a second database (`tasks/jaffle/`, 24 tasks): see [Jaffle Shop
sub-suite](#jaffle-shop-sub-suite).

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
| Q26 | Metrics without a join path | `q26-events-per-customer` |
| Q27 | List columns | `q27-vip-customers`, `q27-vip-and-eu`, `q27-vip-or-partner`, `q27-customers-per-tag`, `q27-region-distinct-tags`, `q27-region-tag-set`, `q27-tag-count-groups`, `q27-category-ratings` |

Most rows are also covered by combo and trap tasks; the report counts a task under every row it covers. Two rows
are deliberately left out: **Q19** (the agent and API surface — every task already exercises it) and **Q22**
(nested source data — SLayer does not support it). Tasks marked `xfail` run but are reported separately until the
linked issue is fixed: relative dates ("last three months") need SLayer's MCP server to pin "now".

## Jaffle Shop sub-suite

The `jaffle` suite holds the 24 business questions of Yann's nao-vs-Motley experiment (6 Nov 2026): twelve simple
ones (`j-q01-stores` … `j-q12-best-unit-margin`) and twelve complex ones (`j-c01-peak-weekday-hour` …
`j-c12-jaffle-beverage-attach`). Each prompt is the question verbatim, followed by one sentence fixing the answer's
rows, columns and units; the truth is his reference SQL adapted to that shape, and every task has a proven single
SLayer query like any other.

They run on the Jaffle Shop database: jafgen's seven raw tables (`customers`, `stores`, `products`, `orders`,
`items`, `supplies`, `tweets`) over four years, money in integer cents, built from a fixed seed so every build is
identical, with dates shifted so the last order falls on 2026-10-29. It is not Yann's exact file, so its numbers
differ from his. Its SLayer store holds the seven models and nine `jaffle-*` memories of `MotleyAI/my_model_repo`
(commit `2221871`), with the datasource named `demo_database` as the memories expect.

Several questions depend on a business rule — revenue is pre-tax, where the data ends, what a new customer is, what
counts as same-store growth. The rules reach the profiles as in Yann's run:

* **SLayer and Motley** — the rules are memories in the store; the agent sees one only if it finds it through
  `search` (keyword search: trials have no embeddings index).
* **`sql+python`** — a plain-SQL rendering of the same nine business rules is appended to the system prompt on
  `jaffle` tasks (`src/slayer_evals/dataset/jaffle_rules.md`).

The memories are kept as Yann ran them, stale figures included. Run the suite on its own with:

```bash
poetry run slayer-evals run --subscription-auth --env-file .env.agents --suites jaffle
```

The report adds a `jaffle` row to the headline table and a per-task Jaffle section; the row and pitfall tables
count the other three suites only.

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

Useful flags: `--tasks q1-region-total,q4-running-total`, `--suites jaffle,trap`, `--profiles slayer`, `--models claude-opus-5-5`,
`--trials 3` with `--mode repeat` (N trials each) or `--mode until-pass` (stop at the first pass),
`--concurrency 3`, `--max-turns 60`, `--timeout 900`, and `--slayer-command "/path/to/your/slayer"` to test a local
SLayer checkout.

A run builds the datasets its tasks need (about a minute for the Jaffle Shop). To build them once and reuse them, run
`poetry run slayer-evals build --out data`, which writes one directory per dataset, `data/bench/` and `data/jaffle/`
(each a database file and a `store/`), and pass `--dataset-dir data` to `run` and `truth`.

## Profiles

* **`slayer`** — the SLayer MCP server, verbatim, plus `submit_answer`.
* **`slayer+python`** — the same plus a Python tool (pandas, numpy, duckdb) running in a fresh subprocess with a
  sandboxed working directory, a clean environment, CPU and memory limits, and an audit log of file opens.
* **`sql+python`** — no SLayer at all: a `sql` tool that runs one DuckDB statement per call on a read-only connection
  to the trial's copy of the database (external access off and locked, 60 s timeout, at most 1,000 rows), plus
  `submit_answer` and the same Python tool, which is not given the database. Tasks that name a saved SLayer definition
  (such as the saved query `monthly_rev`) cannot be done without SLayer, so they fail in this profile without running
  an agent (end reason `auto_fail`).
* **`motley`** and **`motley+python`** — Motley's MCP server, verbatim, plus `submit_answer` (and the Python tool).
  Opt-in: see [Motley profiles](#motley-profiles).

A run uses `slayer`, `slayer+python` and `sql+python` unless `--profiles` says otherwise.

Every session is hermetic: an empty Claude config directory, no built-in tools, no settings, and exactly the profile's
MCP servers, each connected (the trial aborts if any other server appears, or a declared one is missing or not
connected). SLayer runs on its own copy of the database and store with an allow-listed environment. The system prompt
is short and generic and identical across profiles, except that the SLayer and Motley profiles are asked to request
`query` results as JSON, and that on `jaffle` tasks the `sql+python` system prompt ends with the business rules; it
never mentions SLayer or Motley features.

## Motley profiles

`motley` and `motley+python` connect the agent to a running Motley backend over HTTP, so one run can compare SLayer,
Motley and raw SQL side by side:

```bash
poetry run slayer-evals run --subscription-auth --env-file .env.agents --dataset-dir data \
  --profiles slayer,motley,motley+python \
  --motley-seed-cmd "/path/to/storyline/backend/scripts/eval_backend.sh seed" --motley-slayer-version 1.8.2
```

* `--motley-seed-cmd` seeds one Motley org; it is required with a Motley profile. Storyline's `eval_backend.sh seed`
  first brings up a local eval backend on `127.0.0.1:8100` if it is down. Before each Motley trial the runner calls it
  with `--user-id <id> --store <the trial's store copy> --db <the build's database file of the task's dataset>`, so
  every trial gets its own org, and the agent sends that id as `X-Storyline-Dev-User-Id`. A seed that fails or times
  out (600 s) ends that trial with `error`.
* `--motley-slayer-version` is the SLayer version the Motley backend runs (storyline's `motley-slayer` pin); it is
  required with a Motley profile, and each Motley trial's results line records it, while the other profiles record the
  local SLayer's version.
* `--motley-url` is the backend's MCP endpoint (default `http://localhost:8100/api/v1/mcp/`, the eval backend's). Its
  host must match the backend's `public_base_url`, or the backend answers 421.
* Storyline's `docs/eval_org_seed.md` describes the eval backend and the seed.

At start the run seeds one warm-up org per dataset its Motley trials use, which fills the embedding cache, and runs an
MCP `initialize` as a warm-up user; the run stops if any of these fails. The report records the Motley URL and the
server name and version `initialize` reports.
Two gaps on Motley's side show in its results: `q9-credit-by-status` is an expected failure in the Motley profiles
until Motley's `query` returns result warnings, and Motley's `query` cannot yet run a saved query by name with
`refine`, so saved-query tasks are answered with one inline query.

## Reading the report

`report.md` starts with the run's metadata and a headline table of suite by profile and model, then a table of trap
pitfall by profile, then one section per profile and model: a table of rows Q1–Q27 with trial counts for each
criterion (a multi-row task counts under each of its rows), and a per-task table (pass rate k/N and pass^N for `repeat`; first-try pass, eventual
pass and attempts for `until-pass`). Expected failures, totals (tokens, cost, time) and a digest of every failed
trial follow: which criteria failed, why, and one line per SLayer or `sql` call the agent made. Regenerate a report offline
with `poetry run slayer-evals report runs/<timestamp>`.

## Baseline

`results/baseline/` holds a committed run of every task of every suite in all five profiles with Claude Opus 5.5,
run on 17 Nov 2026: its [report](results/baseline/report.md), results and normalized traces. It is a **single-trial
snapshot**: each task ran once per profile, so individual rates are noisy; use `--trials` for stable numbers. The SLayer
and SQL profiles ran on SLayer 1.8.5, the version the benchmark pins; the Motley profiles ran against a local Motley
backend (`motley 1.30.0`, from storyline's `main`) whose SLayer is 1.8.2. Each results line records the SLayer
version that answered it.

| Suite | Profile | Trials | Correct | Single query | Passed |
| --- | --- | --- | --- | --- | --- |
| capability | `slayer` | 32 | 31 | 30 | 30 |
| capability | `slayer+python` | 32 | 31 | 30 | 30 |
| capability | `motley` | 31 | 30 | 27 | 27 |
| capability | `motley+python` | 31 | 30 | 26 | 26 |
| capability | `sql+python` | 33 (2 auto-failed) | 29 | 25 | 25 |
| combo | `slayer` | 15 | 15 | 14 | 14 |
| combo | `slayer+python` | 15 | 15 | 13 | 13 |
| combo | `motley` | 15 | 15 | 12 | 12 |
| combo | `motley+python` | 15 | 15 | 10 | 10 |
| combo | `sql+python` | 15 (1 auto-failed) | 13 | 7 | 7 |
| trap | `slayer` | 21 | 21 | 21 | 21 |
| trap | `slayer+python` | 21 | 21 | 21 | 21 |
| trap | `motley` | 21 | 21 | 19 | 19 |
| trap | `motley+python` | 21 | 21 | 18 | 18 |
| trap | `sql+python` | 21 | 21 | 20 | 20 |
| jaffle | `slayer` | 24 | 23 | 19 | 18 |
| jaffle | `slayer+python` | 24 | 22 | 17 | 16 |
| jaffle | `motley` | 24 | 23 | 14 | 14 |
| jaffle | `motley+python` | 24 | 23 | 12 | 12 |
| jaffle | `sql+python` | 24 | 23 | 17 | 17 |

Expected failures are not counted: the relative-date task in every profile, `q9-credit-by-status` in the Motley
profiles (their `query` drops result warnings) and `q27-tag-count-groups` in the four SLayer-backed profiles (SLayer's
`length` counts repeated list elements). **Correct** is the comparison: the four semantic-layer profiles miss at most
one task per bench suite, and every profile answered every trap correctly. The profiles separate on single query: of
the bench tasks, `slayer` and `slayer+python` lack a single-query answer on 3 and 4, `motley` and `motley+python` on 9
and 13, and `sql+python` on 17, 8 of them combos.

On the **jaffle** suite every profile but `slayer+python` was correct on 23 of 24 questions. The SLayer and Motley
agents now `search` the business-rule memories on nearly every question, so the pre-tax revenue rule is found and
used. Single query separates the profiles: 18 and 16 passes for SLayer, 17 for SQL, 14 and 12 for Motley.
[docs/baseline-failures.md](docs/baseline-failures.md) breaks every failure down by profile and pitfall, and the
Jaffle suite by business rule; the report lists each one with its SLayer, Motley and `sql` calls.

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

A task is one YAML file under the folder of its suite (`tasks/capability/`, `tasks/combo/`, `tasks/traps/` or
`tasks/jaffle/`):

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

`covers` lists the rows (Q1–Q27 except Q19 and Q22) and pitfall kinds the task exercises; the suite follows from it.
A Jaffle Shop task instead says `dataset: jaffle` and has no `covers`.
`slayer_query` is the intended SLayer query, in the arguments of SLayer's MCP `query` tool; `naive_sql` (one statement
or a list) is required on traps and forbidden elsewhere. `compare` sets the key and value columns, `tolerance`,
`ordered`, `columns_exact`, `null_as_zero` (NULL equals 0 in value columns) and `extra_zero_rows` (an extra row for an
empty group, all 0 or NULL, is ignored, for a question that asks after every group). `expect` turns the task into a refusal
or warning task (one kind or a list), `uses_saved` names the saved SLayer definitions the prompt relies on, and `xfail`
links an issue. Prompts must stay capability-neutral and must not hint at a pitfall (a test enforces a whole-word
deny-list). `tests/test_task_proofs.py` runs every `slayer_query` and `naive_sql` on the built dataset. Then
regenerate and commit the truth snapshot:

```bash
poetry run slayer-evals truth --write
```

`poetry run slayer-evals build --out data` builds every dataset's database and store template into `data/bench/` and
`data/jaffle/` if you want to explore them.

## Development

```bash
poetry run ruff check .
poetry run basedpyright
poetry run pytest -m "not integration"
```

## Licence

MIT — see [LICENSE](LICENSE).
