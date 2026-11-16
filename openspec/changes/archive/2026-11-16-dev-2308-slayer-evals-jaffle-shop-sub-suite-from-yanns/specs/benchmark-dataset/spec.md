## ADDED Requirements

### Requirement: Jaffle Shop dataset
The build SHALL generate a second DuckDB database, the Jaffle Shop dataset, with jafgen over 4 years, holding the
tables `customers`, `stores`, `products`, `orders`, `items`, `supplies` and `tweets` in the shape jafgen writes them:
money in integer cents, the ordering customer in `orders.customer`, and `ordered_at`, `opened_at` and `tweeted_at`
as timestamps, shifted by whole days so that the last order falls on 2026-10-29. It SHALL contain 6 stores, opened
on 2022-10-31 (Philadelphia), 2023-05-11 (Brooklyn), 2024-06-27 (Chicago), 2024-07-07 (San Francisco), 2025-05-08
(New Orleans) and 2025-11-11 (Los Angeles), and between 1.1 and 1.25 million orders from 2022-10-31 to 2026-10-29.
Every random draw of the generator, including generated ids, SHALL come from a fixed seed, so that building twice
yields identical table contents; the canonical content hash of each of the 7 tables (rows sorted by all columns)
SHALL be committed and checked. Generating the dataset MUST NOT change the random state, the id generator or the
working directory of the process that builds it.

#### Scenario: Same seed, same Jaffle tables
- **WHEN** the Jaffle dataset is built twice into two directories
- **THEN** every table's canonical content hash is equal across the two builds and equals its committed value

#### Scenario: Jaffle shape and range
- **WHEN** the Jaffle dataset is built
- **THEN** it has exactly the 7 tables, money columns are integers, the 6 stores carry the stated opening dates, and the orders span 2022-10-31 to 2026-10-29 with between 1.1 and 1.25 million rows

#### Scenario: Builder process left untouched
- **WHEN** the Jaffle dataset is built inside a process
- **THEN** that process's random state, id generation and working directory are the same afterwards as before

### Requirement: Jaffle store template
The build SHALL produce a SLayer store for the Jaffle dataset containing a DuckDB datasource named `demo_database`
pointing at the trial-relative Jaffle database file; the 7 models of `MotleyAI/my_model_repo` at commit `2221871`
(`customers`, `stores`, `products`, `orders`, `items`, `supplies`, `tweets`) with their joins, saved measures and
descriptions, without sampled values; the 9 `jaffle-*` memories of that repository (`jaffle-data-coverage`,
`jaffle-money-in-cents`, `jaffle-monthly-store-revenue`, `jaffle-new-customers`, `jaffle-product-margin`,
`jaffle-revenue-definition`, `jaffle-sales-by-product`, `jaffle-same-store-growth`, `jaffle-tweets-limits`) with their
learning text and description verbatim, linked to their authored entities or, for a memory with a saved query, to the
entities of that query; and SLayer's help memories as `slayer mcp` seeds them. It SHALL hold no semantic-search index.

#### Scenario: Jaffle store loads and answers
- **WHEN** a SLayer MCP server is started on a copy of the Jaffle store template
- **THEN** `list_datasources` lists `demo_database`, `models_summary` lists the 7 models, and a `query` on `orders` returns rows

#### Scenario: Business rules are searchable
- **WHEN** the SLayer `search` tool is called on the Jaffle store with the words "revenue pre-tax"
- **THEN** the results include the memory `jaffle-revenue-definition`

#### Scenario: Memories carry their links
- **WHEN** the Jaffle store template is built
- **THEN** each of the 9 memories has its committed learning text and description and a non-empty set of linked entities, equal to its committed expected set

### Requirement: Jaffle business rules text
The repository SHALL hold one plain-SQL text of the Jaffle business rules: one section per `jaffle-*` memory, in the
memory's order, stating the same rule in table and column terms instead of SLayer measures, aggregations and
query settings, without the memory's SLayer-specific mechanics, and otherwise verbatim, including its figures.

#### Scenario: One section per memory
- **WHEN** the rules text is checked against the Jaffle memories
- **THEN** it has exactly one section per memory, titled with the memory's id, in the same order

#### Scenario: No SLayer vocabulary
- **WHEN** the rules text is checked
- **THEN** it names no SLayer measure, aggregation suffix or query setting (for example `net_sales`, `:min`, `whole_periods_only`, `line_sales`, `partition_by`)

### Requirement: One build directory per dataset
The build SHALL write each dataset to its own subdirectory of the output directory, named after the dataset (`bench`,
`jaffle`), each holding that dataset's database file and store template.

#### Scenario: Build layout
- **WHEN** the build runs into an output directory
- **THEN** the output directory holds `bench/` and `jaffle/`, each with its database file and its `store/`
