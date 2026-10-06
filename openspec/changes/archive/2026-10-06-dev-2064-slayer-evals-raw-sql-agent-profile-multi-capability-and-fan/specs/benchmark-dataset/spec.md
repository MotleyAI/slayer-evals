## MODIFIED Requirements

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

## ADDED Requirements

### Requirement: Existing tables fixed
Extending the dataset MUST NOT change the content of the tables `regions`, `customers`, `orders`, `returns`, `events`
or the view `orders_flat` for the default seed; their canonical content hashes SHALL be committed and checked.

#### Scenario: Probe tables unchanged
- **WHEN** the dataset is built with the default seed
- **THEN** the canonical content hash of each probe table and of `orders_flat` equals its committed value
