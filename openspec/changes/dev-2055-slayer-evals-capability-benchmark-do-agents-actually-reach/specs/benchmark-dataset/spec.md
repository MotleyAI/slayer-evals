## Purpose

Provides the one demo database every benchmark task runs against, and the SLayer store an agent starts from, both
built reproducibly from a seed.

## ADDED Requirements

### Requirement: Deterministic dataset build
The build SHALL generate a DuckDB database with tables `regions`, `customers`, `orders`, `returns`, `events` and a view
`orders_flat`, in the column layout of SLayer's comparison probe dataset, at realistic size (on the order of 200
customers and 5,000 orders over 2023–2025). Building twice with the same seed MUST yield identical table contents.
Different seeds MUST yield different contents.

#### Scenario: Same seed, same tables
- **WHEN** the dataset is built twice with the default seed into two directories
- **THEN** every table's canonical content hash (rows sorted by all columns) is equal across the two builds

#### Scenario: Different seed, different tables
- **WHEN** the dataset is built with two different seeds
- **THEN** the `orders` content hashes differ

#### Scenario: Schema matches the probe layout
- **WHEN** the dataset is built
- **THEN** each table has exactly the probe dataset's columns and types, foreign keys are declared, and `orders_flat` joins orders to customers and regions with left joins

### Requirement: Planted edge cases
The built dataset SHALL contain each of these edge cases, each verifiable by a query: a customer with no orders; a
customer with a NULL region; a city that appears in two regions; a region with no customers; orders with a NULL
`customer_id`; at least one calendar month inside the order date range with no orders; a month with returns but no
orders; a return with a NULL `customer_id`; events with sub-hour timestamps falling into different quarter-hour
buckets.

#### Scenario: Every planted case is present
- **WHEN** the dataset is built with the default seed
- **THEN** each edge-case invariant query returns the expected non-empty (or, for gaps, empty) result

### Requirement: Store template
The build SHALL produce a SLayer store containing a DuckDB datasource named `bench` pointing at the built database,
with custom granularities `fiscal_year` (12 months starting April) and `quarter_hour` (15 minutes); a model per table
and for `orders_flat`, with joins along the foreign keys; the saved measures, query-backed models and saved queries the
tasks rely on; and SLayer's help memories as `slayer mcp` seeds them. The build SHALL also emit a manifest of the
store's models, saved measures (name → formula) and saved queries for the grader.

#### Scenario: Store loads and answers
- **WHEN** a SLayer MCP server is started on a copy of the store template
- **THEN** `list_datasources` lists `bench`, `models_summary` lists every model, and a `query` on `orders` returns rows

#### Scenario: Manifest matches the store
- **WHEN** the store template is built
- **THEN** every saved measure and saved query in the manifest exists in the store with the same definition, and vice versa
