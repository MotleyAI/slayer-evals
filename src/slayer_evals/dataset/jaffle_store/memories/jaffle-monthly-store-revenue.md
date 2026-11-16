---
created_at: '2026-11-06T10:40:41.863318Z'
description: 'Example query: monthly pre-tax net sales by store'
entities:
- demo_database.orders
- demo_database.stores.name
- demo_database.orders.ordered_at
- demo_database.orders.net_sales
query:
  dimensions:
  - label: null
    model: stores
    name: name
  distinct_dimension_values: true
  filters: null
  limit: null
  main_time_dimension: null
  measures:
  - description: null
    formula: net_sales
    label: null
    meta: null
    name: null
    type: null
  name: null
  offset: null
  order: null
  source_model: orders
  time_dimensions:
  - date_range: null
    dimension:
      label: null
      model: null
      name: ordered_at
    granularity: month
    label: null
  to_many_handling: broadcast
  variables: null
  version: 4
  whole_periods_only: true
version: 2
---
Monthly sales by store: net_sales (pre-tax, dollars) by stores.name over month(ordered_at). Use net_sales rather than total_revenue so stores with different tax rates compare fairly (see jaffle-revenue-definition). Drop the current incomplete month (see jaffle-data-coverage).