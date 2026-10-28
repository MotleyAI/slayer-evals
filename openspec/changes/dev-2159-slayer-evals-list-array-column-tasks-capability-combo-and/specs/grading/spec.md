## MODIFIED Requirements

### Requirement: Table comparison
Two tables SHALL match when, after column resolution, the key and value columns' rows are equal as multisets
(or as sequences when `ordered`), with numeric values equal within `tolerance`, NULL equal only to NULL (or, when the
task sets `null_as_zero`, NULL also equal to 0 in value columns), NaN treated as NULL, and dates and timestamps compared
after normalization to ISO form. A list-valued cell SHALL compare as the set of its normalized non-NULL elements,
ignoring element order and repeats, with numeric elements equal within `tolerance`; in a column whose truth cells are
lists, a result cell holding JSON list text or comma-separated text SHALL compare as the set of its elements the same
way, while text in any other column is compared as text. NULL SHALL NOT equal an empty list. Column resolution SHALL
map each truth column to a result column by exact name, else by `.name` suffix, else by a flattened `a__b` form; a
truth column that resolves by name to more than one column MUST make the match fail with a reason naming it. Truth
columns that resolve by name to no column SHALL be matched by values: the tables match if some one-to-one assignment
of those truth columns to the result columns not already used makes the rows match, preferring, when several do, the
assignment whose result column names are closest to the truth names; if none does, the match fails with a reason
naming those columns. A successful match SHALL record the column mapping it used, and the verdict SHALL carry the
mappings of its correctness and single-query matches. Extra result columns SHALL be ignored unless `columns_exact`.
The row counts MUST be equal.

#### Scenario: Order-insensitive match with tolerance
- **WHEN** a result has the truth rows in a different order and a value off by 1e-9
- **THEN** the tables match

#### Scenario: Ambiguous column fails
- **WHEN** truth column `name` matches both `customers.name` and `regions.name` in the result
- **THEN** the match fails with a reason naming `name` as ambiguous

#### Scenario: Columns matched by values
- **WHEN** a result names its columns `orders.customers.regions.name` and `orders.rev` for truth columns `region` and `revenue`, with matching rows
- **THEN** the tables match and the recorded mapping is `region` → `orders.customers.regions.name`, `revenue` → `orders.rev`

#### Scenario: Truncated result fails
- **WHEN** a result holds 20 of the truth's 25 rows
- **THEN** the tables do not match and the reason gives both row counts

#### Scenario: Ordered task
- **WHEN** a task sets `ordered` and the result has the right rows in the wrong order
- **THEN** the tables do not match

#### Scenario: NULL as zero
- **WHEN** the truth has NULL revenue for a month and the result has 0
- **THEN** the tables match if the task sets `null_as_zero`, and do not match otherwise

#### Scenario: List cells compare as sets
- **WHEN** a truth cell is `['eu', 'vip']` and the result cell is `['vip', 'eu', 'vip']`, `['vip', 'eu', NULL]`, `'["vip","eu"]'` or `'vip, eu'`
- **THEN** the cells are equal; and a result cell `['vip']` or NULL is not equal

#### Scenario: Numeric list elements within tolerance
- **WHEN** a truth cell is `[1.5, 2.0]` and the result cell is `[2.0000000001, 1.5]`, or `[1.5, 2.1]`
- **THEN** the first is equal and the second is not

#### Scenario: Text outside list columns stays text
- **WHEN** a truth column holds the text `'vip, eu'` and the result holds `['vip', 'eu']`
- **THEN** the cells are not equal
