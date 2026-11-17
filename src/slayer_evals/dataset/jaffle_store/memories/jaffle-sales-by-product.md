---
created_at: '2026-11-06T10:40:48.054036Z'
description: 'Sales by product/type: use items.line_sales, never products.price:sum
  from items'
entities:
- demo_database.items
- demo_database.products.type
- demo_database.items.line_sales
- demo_database.items.unit_price
- demo_database.orders.ordered_at
query:
  dimensions:
  - label: null
    model: products
    name: type
  distinct_dimension_values: true
  filters:
  - orders.ordered_at >= '2025-01-01'
  - orders.ordered_at < '2026-01-01'
  limit: null
  main_time_dimension: null
  measures:
  - description: null
    formula: line_sales
    label: null
    meta: null
    name: null
    type: null
  - description: null
    formula: line_sales / unit_price:sum(partition_by=[])
    label: null
    meta: null
    name: share
    type: null
  name: null
  offset: null
  order: null
  source_model: items
  time_dimensions: null
  to_many_handling: broadcast
  variables: null
  version: 4
  whole_periods_only: false
version: 2
---
For sales by product, SKU or product type (product mix, category share), query the items model with the line_sales measure (dollars, pre-tax). It reconciles exactly to orders.net_sales for every year. Do NOT write products.price:sum from items: SLayer aggregates a joined one-side column at its own grain, so it sums each distinct product's price once (e.g. $28 for all beverages in 2025) instead of once per item sold. Share of total: line_sales / unit_price:sum(partition_by=[]).