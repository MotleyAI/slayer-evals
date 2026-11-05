## Context

See proposal.md for the motivation. SLayer 1.7.0 (PyPI), the first release with list columns, is the reference for
every truth. Each semantic below was verified on 1.7.0 by calling the MCP `query` tool in process over a small
database holding the planned edge cases:
- a list's elements are its non-NULL elements;
- `contains`, `contains_any` and `contains_all` are NULL on a NULL list, and `length` is NULL on a NULL list and 0 on
  an empty one;
- `L.value` is a keyless one-to-many child, so filters restrict the parent by existence;
- `to_many_handling: associate` (a field inside the query object) counts each parent once per element value; the
  default broadcasts the parent total onto every element with a broadcast warning;
- `count(L.*)` counts element occurrences, repeats included;
- `NOT (L.value = x)` keeps parents having some element other than `x`;
- `collect` returns the distinct, sorted, non-NULL values, and `[]` for an empty cell (for example a region without
  customers, queried from `regions`);
- `contains` on a TEXT column is a plan-time error pointing to `LIKE`;
- a model declares a list column as uppercase `type: ARRAY` with `element_type: TEXT|INT`; lowercase spellings are
  rejected.

DuckDB's own list functions differ from these. `len()` counts NULL elements, and `'x' <> ALL(tags)` / `NOT IN
(unnest)` drops a list holding a NULL element and keeps a NULL list (checked on DuckDB 1.5.6). So hand-written truths
must spell out the SLayer semantics explicitly, for example `list_filter(tags, x -> x IS NOT NULL)`.

Architecture principles that apply (`architecture/system.arc42.md`):
- P1 pure grading: list-cell comparison lives in `grading`, imports only `core` and does no I/O.
- P5 reproducible data: the new columns come from seeded streams of their own, and truth comes from the built
  database.
- P6 capability-neutral prompts: the deny-list gains the list DSL.
- P7 proven tasks: the fairness test covers every new task and trap.

No c4 change: all work stays inside the existing nodes `dataset`, `core`, `tasks`, `grading`, `runner` and `report`.
No arc42 change.

## Goals / Non-Goals

**Goals:**
- Q27 list-column coverage as the issue lists it, plus the typed brief's two questions: "how many have value x" is
  task 1, plus the `count_after_unnest` trap; "has both x and y" is task 2, plus the `same_element_and` trap.
- Q26 coverage.
- Honest per-trial SLayer provenance in results and the baseline.

**Non-Goals:**
- A full baseline rerun.
- Tasks for list functions beyond the issue's list, such as list-to-list `contains_any(tags, other_list)` or list
  variables.
- An element-occurrence task ("how many times is tag x assigned"): the typed brief's example asks for rows holding the
  value.
- Changing DEV-2065's worktree. Its duplicate Q26 task is resolved when it merges main.
- A one-stage per-element `rank`. 1.7.0 refuses `partition_by` an element (`PartitionKeyError` in every mode,
  DEV-1932 Case 1b), so the rank combo uses two stages.

## The tasks

Exact prompts, truths and `compare` specs are written in the pr-tests stage. Any population ambiguity is stated in the
prompt without deny-listed words, for example whether a customer whose tags are not on record counts.

| # | id | covers | question (gist) | reference construct |
| --- | --- | --- | --- | --- |
| 1 | `q27-vip-customers` | Q27 | how many customers have tag `vip` | `contains(tags, 'vip')`, `count(*)` |
| 2 | `q27-vip-and-eu` | Q27 | how many customers have both `vip` and `eu` | `contains_all(tags, ['vip', 'eu'])` |
| 3 | `q27-vip-or-partner` | Q27 | per region, customers with `vip` or `partner` | `contains_any` / `tags.value IN (…)` |
| 4 | `q27-customers-per-tag` | Q27 | customers per tag | `count(*)` by `tags.value`, `associate` |
| 5 | `q27-region-distinct-tags` | Q27 | distinct tags per region | `count_distinct(tags.value)` |
| 6 | `q27-region-tag-set` | Q27 | every region's set of tags, `[]` for Arctic (no customers) | `collect(customers.tags.value)` from `regions` |
| 7 | `q27-tag-count-groups` | Q27 | customers by number of tags | `length(tags)` as a dimension |
| 8 | `q27-category-ratings` | Q27 | average rating and number of ratings per category | `avg(ratings.value)`, `count(ratings.*)` |
| 9 | `q26-events-per-customer` | Q26 | events, customers, events per customer | cross-model count across a product hop |
| 10 | `c-vip-region-share` | Q27, Q2 | `vip` customers' revenue per region and share of their total | list filter + `partition_by` |
| 11 | `c-vip-monthly-change` | Q27, Q4 | `vip` customers' monthly 2025 revenue and change from the prior month | list filter + `change` |
| 12 | `c-top-customers-per-tag` | Q27, Q14, Q15 | per tag, the two customers with the highest revenue | two stages: revenue per (tag, customer) under `associate`, then `rank` partitioned by the tag |
| 13 | `c-tier-credit-tags` | Q27, Q6 | per tier: customers, total credit, distinct tags | parent measures + element aggregate |
| 14 | `t-vip-per-tier` | Q27, `count_after_unnest` | customers per tier holding `vip` | naive: unnest, `count(*)` |
| 15 | `t-tagged-credit` | Q27, `unnest_fan_out` | total credit of customers tagged `vip` or `partner` | naive: unnest, `sum(credit)` |
| 16 | `t-without-vip` | Q27, `null_element` | per region, customers (tags on record) without `vip` | naive: `'vip' <> ALL(tags)` |
| 17 | `t-vip-and-eu-region` | Q27, `same_element_and` | per region, customers holding both `vip` and `eu` | naive: `tag = 'vip' AND tag = 'eu'` after unnest |

## Decisions

- **Row ids.** The list tasks cover Q27, DEV-2137's matrix row. Q26 is also covered in this change.
  - Options: Q27 with Q26 "not yet covered"; Q27 plus Q26 tasks.
  - Taken: plus Q26, which keeps every row SLayer supports covered. (user)
- **The Q26 task.** Own `q26-events-per-customer` here, mirroring DEV-2065's uncommitted `q6-events-per-customer`.
  - Options: own it; write a different Q26 question; leave Q26 to DEV-2065.
  - Taken: own it, for a clean end state whichever change lands first. (user)
- **List-cell grading.** A cell compares as the set of its normalized non-NULL elements. JSON-list or comma text also
  matches when the truth column holds lists.
  - Options: that; real lists only; ordered exact.
  - Taken: the lenient set form. It is consistent with the grader's existing leniency and judges the set, not its
    spelling. (user)
- **Numeric list.** `products.ratings INTEGER[]` with one task.
  - Options: `products.ratings`; `orders.line_prices`; none.
  - Taken: `products.ratings`. Its data is independent and the question is natural; line prices would duplicate
    `order_items`. (user)
- **Baseline scope.** Run the new tasks only, in all three profiles, on the new pin.
  - Options: new tasks only; full rerun; no baseline change.
  - Taken: new tasks only. Every task gets a baseline result without colliding with DEV-2065's full-baseline
    rewrite. (user)
- **Probe freeze.** Add `customers.tags`, freeze the probe columns via a projected hash, and allow the benchmark's added
  columns in the layout check.
  - Options: that; a one-to-one side table.
  - Taken: that. The tags live where the questions put them, and the freeze keeps protecting existing data. (user)
- **SLayer pin.** Pin the PyPI release `motley-slayer = "1.7.0"`, replacing the git rev. This supersedes the earlier
  entry "DEV-2137 assumed merged; pin its merged main commit".
  - Options: PyPI 1.7.0; git rev `f85c8da` (the v1.7.0 tag).
  - Taken: PyPI. It is a published, immutable release that installs from a wheel and reports the version plainly.
    (user)
- **Rank combo.** `c-top-customers-per-tag` keeps its question with a two-stage reference (revenue per tag and
  customer under `associate`, then `rank` partitioned by the tag), so it covers Q27, Q14 and Q15.
  - Options: two-stage reference plus Q15; xfail against DEV-1932; make the one-stage form work in SLayer.
  - Taken: two-stage. It is still one `query` call and works on 1.7.0, and an agent's `PartitionKeyError` on the
    one-stage form is MCP-surface evidence in the trace. (user)
- **Two element filters.** On 1.7.0, separate filters `tags.value = 'vip'` and `tags.value = 'eu'` return 0 as one
  same-element conjunction, with only a `semi_join_pushed` warning.
  - Options: record it as observed with no plan change; add a SLayer warning task.
  - Taken: record it. The benchmark measures the surface as shipped (principle 6). (user)
- **Empty collected set.** `q27-region-tag-set` asks for every region, so Arctic (no customers) has `[]`. Its
  reference sources `regions` with `collect(customers.tags.value)`.
  - Options: every region with Arctic `[]`; a tagless group made from witnesses.
  - Taken: every region. It exercises `collect`'s empty-cell rule using an existing planted edge case. (user, codex)
- **Pin compatibility gate.** Right after the pin, run the full existing non-integration suite and task proofs on
  1.7.0 before any other change, so a 1.1.0 → 1.7.0 regression is never confused with this work. (codex)
- **Stage-output column naming** (rejected, codex). Codex asked for truth names that resolve structurally against the
  stage outputs `s.customers__tags__value` and `s.customers__name`. Rejected: `resolve_column`'s `…__<name>` rule
  already resolves `value` and `name`; other names fall back to the grader's designed value matching; and the
  fairness test fails any reference that doesn't match its truth under `compare`.
- **List type spelling.** Model YAML spells list types in uppercase (`ARRAY`, `TEXT`, `INT`) because 1.7.0 rejects
  lowercase (Backlog DEV-2174). (default)
- **Forward pointer.** The rank task's file carries a one-line comment naming DEV-1932 as the future single-stage fix.
  (default)
- **Baseline provenance.** A baseline assembled from several runs mixes SLayer versions while only `metadata.json`
  records one.
  - Options: per-trial `slayer_version` on every results line, with the report showing each version and its trial
    count when they differ, the baseline spec allowing several runs, and old baseline lines backfilled with `1.1.0`;
    a full rerun on the new pin; no baseline change.
  - Taken: per-trial version. Provenance becomes honest, also for the existing reruns and future partial ones, without
    colliding with DEV-2065. (user, codex)
- **Deny-list syntax entries.** The deny-list also gains `contains(` and `length(`, the overloaded list functions;
  ordinary prose ("contains", "length") stays allowed. (codex)
- **Numeric list elements.** They match order-insensitively within the task's `tolerance`, recursively, ignoring
  duplicates and NULL elements. (codex)
- **Column name.** The tag column is named `tags`, not `skills`, per the issue and SLayer's Q27 probes. The typed brief's
  "skills" questions map to tasks 1, 2, 14 and 17. (default)
- **Reading the typed brief.** "Count of instances of a value across the rows (e.g. how many users have skill x)" is
  read as rows holding the value (task 1), per its example. There is no separate element-occurrence task. (default)
- **Where the witnesses go.** List witnesses are set on existing customer and product ids, not new rows, so the probe
  hashes stay valid. (default)
- **Row markers.** Q27's markers are `contains`, `.value`, `length(` and `collect(`; Q26 has none. (default)
- **Deny-list additions.** `contains_any`, `contains_all`, `collect(` and `unnest`. (default)
- **Report row names.** They follow the upstream matrix: Q26 "Metrics without a join path", Q27 "List columns".
  (default)
- **NULL vs empty list.** In grading, NULL never equals an empty list. (default)
- **The version field.** `TrialResult.slayer_version` is required rather than optional: every committed results file
  is backfilled, and an optional field would let unversioned lines through silently. (default)

## Risks / Trade-offs

- [A reference query fails on 1.7.0 although the probe passed] → it is a gap to raise with the user, never something to
  route around.
- [1.7.0 treats two separate element filters as one same-element conjunction (a silent 0)] → the `same_element_and`
  trap and the `q27-vip-and-eu` traces show whether agents hit it.
- [Existing references behave differently going from 1.1.0 to 1.7.0, including transitive dependency moves] → the pin
  compatibility gate (task 1.2) runs before any other change, and a failing pre-existing test or reference is a
  suspected gap: STOP and ask.
- [Random list streams make a trap's witness vanish for the default seed] → the witnesses are set deterministically on
  fixed ids, and `test_every_trap_is_live` proves each naive SQL wrong.
- [Comma-text leniency splits a tag that contains a comma] → none of the vocabulary does; documented here.
- [Mixed SLayer versions in the baseline confuse readers] → the report lists versions with trial counts, and the README
  names both pins.
- [DEV-2065 lands with its `q6-events-per-customer`] → the duplicate task id makes loading fail on merge, forcing one
  copy to be dropped.
- [Requiring `slayer_version` breaks old local run directories] → only committed results files matter; they are
  backfilled.

## Migration Plan

- Backfill `"slayer_version": "1.1.0"` into every existing line of `results/baseline/results.jsonl`, and the test
  fixtures' results files with `1.0.2`, the version their metadata records.
- Regenerate the truth snapshots for the new tasks only. Existing snapshots must stay byte-identical.
