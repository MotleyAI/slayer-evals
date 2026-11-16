# benchmark-dataset Specification

## Purpose
Provides the one demo database every benchmark task runs against, and the SLayer store an agent starts from, both
built reproducibly from a seed.

## Requirements

### Requirement: Deterministic dataset build
The build SHALL generate a DuckDB database with tables `regions`, `customers`, `orders`, `returns`, `events` and a view
`orders_flat`, in the column layout of SLayer's comparison probe dataset, plus the benchmark's tables `products`,
`order_items`, `campaigns`, `campaign_members` and `cities`, at realistic size (on the order of 200 customers and 5,000
orders over 2023–2025). Each order's `order_items` lines SHALL sum, in `line_amount`, to the order's `amount` to the
cent. Building twice with the same seed MUST yield identical table contents. Different seeds MUST yield different
contents.

#### Scenario: Same seed, same tables
- **WHEN** the dataset is built twice with the default seed into two directories
- **THEN** every table's canonical content hash (rows sorted by all columns) is equal across the two builds

#### Scenario: Different seed, different tables
- **WHEN** the dataset is built with two different seeds
- **THEN** the `orders` content hashes differ

#### Scenario: Schema matches the probe layout
- **WHEN** the dataset is built
- **THEN** the probe tables have exactly the probe dataset's columns and types, every table's keys and foreign keys are declared, and `orders_flat` joins orders to customers and regions with left joins

#### Scenario: Items add up to orders
- **WHEN** the dataset is built
- **THEN** for every order, the sum of its items' `line_amount` equals its `amount` within 0.005

### Requirement: Planted edge cases
The built dataset SHALL contain each of these edge cases, each verifiable by a query: a customer with no orders; a
customer with a NULL region; a city that appears in two regions, in `customers` and in `cities`; a region with no
customers; orders with a NULL `customer_id`; at least one calendar month inside the order date range with no orders; a
month with returns but no orders; a return with a NULL `customer_id`; events with sub-hour timestamps falling into
different quarter-hour buckets; an event on the last day of a month after midnight; two orders of one region with equal
amounts and more than one item each; a customer with orders in two or more campaigns; and, for every trap task, a
witness that makes the trap's naive query differ from the truth.

#### Scenario: Every planted case is present
- **WHEN** the dataset is built with the default seed
- **THEN** each edge-case invariant query returns the expected non-empty (or, for gaps, empty) result

### Requirement: Store template
The build SHALL produce a SLayer store containing a DuckDB datasource named `bench` pointing at the built database,
with custom granularities `fiscal_year` (12 months starting April) and `quarter_hour` (15 minutes); a model per table
and for `orders_flat`, with joins along the foreign keys and declared cardinalities (`customers` to `cities` on both
city and region); the saved measures, query-backed models and saved queries the tasks rely on; and SLayer's help
memories as `slayer mcp` seeds them.

#### Scenario: Store loads and answers
- **WHEN** a SLayer MCP server is started on a copy of the store template
- **THEN** `list_datasources` lists `bench`, `models_summary` lists every model, and a `query` on `orders` returns rows

#### Scenario: Saved measure and saved query present
- **WHEN** the store template is built
- **THEN** model `orders` has the saved measure `aov` and the query-backed model `monthly_rev` exists

### Requirement: Existing tables fixed
Extending the dataset MUST NOT change the content of the tables `regions`, `customers`, `orders`, `returns`, `events`
or the view `orders_flat` for the default seed; their canonical content hashes SHALL be committed and checked.

#### Scenario: Probe tables unchanged
- **WHEN** the dataset is built with the default seed
- **THEN** the canonical content hash of each probe table and of `orders_flat` equals its committed value

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
