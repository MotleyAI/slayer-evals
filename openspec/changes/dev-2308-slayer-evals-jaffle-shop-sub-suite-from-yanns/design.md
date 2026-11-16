## Context

See proposal.md for motivation. Source material is Yann's bundle (`nao-vs-motley-slim.zip`, unpacked to
`nao-vs-motley/`): questions `nao_project/tests/q*.yml` and `nao_project/tests/complex/c*.yml` (`name`, `prompt`,
reference `sql`), reference results `references.txt` and `complex/references.txt`, SLayer models
`slayer_data/models/demo_database/*.yaml`, memories `slayer_data/memories/jaffle-*.md`, DB builder
`scripts/build_db.py`, memory loader `scripts/load_memories.py`. The bundle is not in the repo; its models, memories
and questions are copied in as committed data.

Constraints:
- Architecture (`architecture/system.arc42.md`): principles 1–7 all apply. Rules text reaches the agent only through
  the trial environment (2); prompts stay capability-neutral and pass the deny list (6); every task has a proven
  single SLayer query (7); truth comes from the built database and the same seed yields the same tables (5).
- Import law (`architecture/model.c4`): `tasks`, `agents`, `grading` and `report` import only `core`; `runner` and
  `cli` reach `dataset`. The dataset registry that `tasks` (proofs, truth) and `report` need therefore lives in
  `core`. No new node or arrow.
- SLayer is pinned at git rev `1653a918` (reports 1.1.0). Its memory API takes either an entity list or a query,
  never both.

## Goals / Non-Goals

**Goals:**
- Score Yann's 24 questions automatically in every profile, with business rules delivered as in his run: found by
  search on the SLayer side, in the prompt on the SQL side.
- Keep the bench suites, their row and pitfall tables, and their proofs exactly as they are.

**Non-Goals:**
- No SLayer pin bump. The pinned SLayer has a SQL-generation bug (a multi-stage final stage with no dimensions whose
  measures read a joined model emits `SELECT` with an empty select list); it is fixed in 1.8.5 and on `main`. Agents
  may hit it; reference queries avoid it.
- No nao mode (DEV-2309).
- No semantic search or embeddings index: trials stay hermetic, so `search` is keyword-only.
- No business rules in the SLayer or Motley system prompts.
- Not Yann's exact database file: numbers differ from his `references.txt`; truth is recomputed from the seeded build.
- No correction of the memories' stale figures or of `jaffle-tweets-limits`' "uniformly positive" claim (jafgen does
  write neutral and negative tweets); the text stays as Yann ran it, identical for both profile families.

## Decisions

### Decisions log
1. The Jaffle database is rebuilt from a seed, not downloaded nor committed via LFS. (user)
2. Prompts are Yann's question verbatim plus an answer-shape sentence that states no business rule. (user)
3. Every Jaffle task carries a proven `slayer_query`; principle 7 is unchanged. Probes on a 4-year build showed C3,
   C5, C6, C8, Q11, C9, C10 and C12 each have a single (multi-stage where needed) SLayer query matching the reference
   exactly, on the pinned SLayer and on 1.8.5. (default, after probes the user asked for)
4. Business rules reach the SQL profiles through the system prompt; SLayer and Motley find them through `search`.
   Applies to the Jaffle sub-suite only. Alternatives rejected: same lookup for all via a `business_rules` table (A),
   rules in every prompt (C), no rules for SQL (D). (user, "for now")
5. The SQL rules text is a plain-SQL rendering of the 9 memories, not Yann's nao RULES.md (which carries SQL trap
   coaching the SLayer side never gets) and not the memories verbatim (SLayer vocabulary). (user)
6. A `dataset` field on tasks; `jaffle` is its own suite with no `covers`; row and pitfall tables stay bench-only.
   Alternative rejected: tagging Jaffle tasks with capability rows. (user)
7. The full baseline (all 77 tasks × 3 default profiles) is re-run in this change. (user)
8. Q4 includes the partial October, stated in the shape sentence. (user)
9. Q9 lists all 4 stores with sales in both years. (user)
10. Q12 lists all 10 products, margin in dollars and as a fraction. (user)
11. The remaining per-task shapes in the table below, including C6 "rounded up", C8 counting growth months only,
    C10 a single row, C1 the weekday name, fixed labels where the answer invents them. (default; the user delegated
    per-task calls)
12. The Jaffle datasource stays named `demo_database`, because the memories' entity tags name it. (default)
13. Build layout `<out>/<dataset>/`, a `--suites` flag, a Motley warm-up per dataset. (default)
14. Arc42 Purpose: "analytics questions over a seeded demo database:" → "analytics questions over seeded demo
    databases:". (user, approved wording)
15. The 5 memories with a saved query (`jaffle-monthly-store-revenue`, `jaffle-product-margin`,
    `jaffle-revenue-definition`, `jaffle-sales-by-product`, `jaffle-same-store-growth`) are saved with their query,
    so their links are derived from it, as Yann's loader did; the other 4 keep their authored entities. A test pins
    each memory's resulting entity set. (codex)
16. jafgen runs in a child process that seeds `random`, NumPy and jafgen's module-level Faker, patches `uuid.uuid4`
    to draw from the seeded generator, and works in a temporary directory; nothing in the builder process is touched.
    A test builds twice and compares hashes. (codex)
17. The 7 Jaffle tables use the bench dataset's existing canonical content hash (rows sorted by all columns). (codex)
18. Truth computation and `truth --write` always cover every loaded task across both datasets. (codex)
19. `--dataset-dir` is the build root; a run validates only its datasets' subdirectories and names every missing one
    together. No compatibility path for the old flat layout. (codex)
20. `TrialResult.dataset` is always written; the report derives the suite from it (`jaffle`) or from `covers`. (codex)
21. Baseline and report tests extended: `jaffle` headline row and section, row and pitfall totals exclude Jaffle
    trials. (codex)
22. Motley warm-up identities are dataset-qualified (`warm-up:bench`, `warm-up:jaffle`), and only datasets with
    Motley trials are warmed. (codex)
23. rejected (codex): regenerate or strip the memories' stale figures. Reason: both profile families see the same
    text, it is what Yann ran, no task's truth depends on those figures, and no question asks about sentiment.
24. rejected (codex): seed each Motley trial with a per-trial database copy. Reason: the `benchmark-runs` spec makes
    all Motley organizations read the run's one database file, opened read-only by the backend; the shared file is
    deliberate. Kept per dataset.
25. rejected (codex): validate result lines against task files in the report. Reason: the report regenerates offline
    from the run directory alone, and `report` imports only `core`.

### Dataset registry in `core`
`Dataset = Literal["bench", "jaffle"]` and a `DATASET_SPECS` table (datasource name, database file name), like
`PROFILE_SPECS`. `tasks` (proofs, truth), `runner` and `report` read it without new arrows. Alternative rejected:
dataset knowledge in `dataset` only — `tasks` cannot import it.

### Rules through `TrialEnv`
`TrialEnv.business_rules: str | None`, set by the runner only for a `jaffle` task on a `sql`-surface profile;
`system_prompt` appends it under a fixed heading. Agents never see the task or its dataset name, so principle 2
holds and `agents` stays blind to what is graded.

### Task shapes
Conventions: money in dollars, shares and growth as fractions, the row set always stated, labels fixed only where
the answer would invent them (C2 bands, C3 mixes, C11 segments).

| id | rows | keys → values |
|---|---|---|
| j-q01-stores | 6 | store → opened_on |
| j-q02-orders-2025 | 1 | orders |
| j-q03-revenue-by-store-2025 | 6 | store → revenue |
| j-q04-monthly-orders-2026 | 10 (partial Oct included, stated) | month → orders |
| j-q05-top-products-2025 | 5 | product → type, units_sold |
| j-q06-type-share-2025 | 2 | type → sales, share |
| j-q07-aov-by-store | 6 | store → aov |
| j-q08-tax-rate-check | 6 | store → stated_rate, collected_rate |
| j-q09-store-growth-2024-2025 | 4 (stores with sales in both years) | store → sales_2024, sales_2025, growth |
| j-q10-new-customers-by-year | 5 | year → new_customers |
| j-q11-ytd-growth-same-store | 1 | ytd_2025, ytd_2026, headline_growth, ss_2025, ss_2026, same_store_growth |
| j-q12-best-unit-margin | 10 | product → unit_margin, margin_pct |
| j-c01-peak-weekday-hour | 1 | weekday (name), hour, net_sales, share |
| j-c02-order-value-bands | 4 (fixed labels) | band → orders, net_sales, share_of_sales |
| j-c03-basket-mix | 3 (fixed labels) | mix → orders, share |
| j-c04-ltv-by-first-store | 6 | store → customers, avg_lifetime_spend |
| j-c05-median-orders-per-customer | 6 | store → customers, median_orders |
| j-c06-top-decile-share | 1 (top 10% rounded up, stated) | top_decile_share, top_decile_customers |
| j-c07-best-month-vs-avg | 6 | store → best_month, sales, avg_month, above_avg |
| j-c08-growth-streak | 1 (growth months only) | streak_months, streak_start, streak_end |
| j-c09-brooklyn-cogs-margin | 1 | cogs, product_sales, gross_margin |
| j-c10-top-supply-component | 1 | supply, total_cost |
| j-c11-tweeters-aov | 2 (fixed labels) | segment → customers, orders, net_aov |
| j-c12-jaffle-beverage-attach | 6 | store → jaffle_orders, attach_rate |

### Reference-query notes (from the planning probes, pinned SLayer)
- C9: stage 1 `unit_cogs` = `supplies` by `sku` with `sum(cost)`; stage 2 = `items` extended with a join to
  `unit_cogs` on `sku` and a row-level column `uc = unit_cogs.unit_cogs`, filtered to Brooklyn and 2025, **grouped by
  `orders.stores.name`** (no dimensions hits the pinned bug), measures `sum(uc) / 100.0`, `sum(unit_price)`,
  `1 - sum(uc) / 100.0 / sum(unit_price)`. `sum(unit_cogs.unit_cogs)` directly aggregates at the stage's grain (wrong).
- C10: stage 1 `sold` = `items` by `sku` with `count(*)` in 2025; stage 2 = `supplies` extended with a join to `sold`,
  by `name`, `sum(cost * sold.units) / 100.0`, ordered desc, limit 1. A `units` column there broadcasts (wrong).
- C3, C12: per-order stage on `items` extended with row-level flags `CASE WHEN products.type = '…' THEN 1 ELSE 0 END`,
  `max()` per order; C3 then groups by a computed `mix` with `count(*) / sum(count(*), partition_by=[])`; C12 filters
  `has_j = 1` and takes `avg(has_b)` by store.
- C5: stage by `stores.name`, `customer` with `count(*)`, then `median(n)` by store.
- C6: per-customer stage with `ntile(0 - sum(subtotal), n=10)` (SLayer's `ntile` is ascending), then conditional sums
  on `decile = 1`.
- C8: monthly stage with `consecutive_periods(change(sum(subtotal)) > 0)`, then max run with start
  `date_add(ordered_at, -(run - 1), 'month')`.
- Q11: one stage on `orders` extended with a row-level column `opened = stores.opened_at`, conditional sums.

### Store model YAMLs
Yann's model files carry `sampled`, `sampled_values` and `distinct_count` from his database; these are stripped from
the committed copies, and the models are saved through the engine so SLayer validates them on build.

## Risks / Trade-offs

- [jafgen or NumPy upgrade changes generated data] → the committed hashes and truth snapshots fail loudly; regenerate
  both deliberately in the upgrading change.
- [CI build time grows by a 1.2M-order build] → the Jaffle build is built once per test session, like the bench one.
- [Per-trial copy of a ~145 MB database] → acceptable at concurrency 3; Motley trials read the shared file anyway.
- [SQL profile finds the rules in its prompt while SLayer must search] → deliberate (decision 4); the report says so
  next to the Jaffle results.
- [Stale memory figures mislead agents] → identical for both profile families; see Non-Goals.
- [Pinned SLayer bug makes C9-like answers harder for SLayer agents] → a real surface gap the benchmark should show.

## Migration Plan

`build` output and `--dataset-dir` change layout (**BREAKING**, proposal): an existing flat build directory must be
rebuilt. Old results files without `dataset` read as `bench`. The baseline is re-run, so no old baseline stays.
