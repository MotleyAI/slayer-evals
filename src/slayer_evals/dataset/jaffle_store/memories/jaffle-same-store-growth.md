---
created_at: '2026-11-06T10:40:49.593894Z'
description: 'Growth / YoY: always report headline AND same-store growth (stores open
  for both full periods)'
entities:
- demo_database.orders
- demo_database.orders.ordered_at
- demo_database.orders.net_sales
- demo_database.stores.opened_at
query:
  dimensions: null
  distinct_dimension_values: true
  filters:
  - stores.opened_at < '2024-01-01'
  - ordered_at >= '2024-01-01'
  - ordered_at < '2026-01-01'
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
    granularity: year
    label: null
  to_many_handling: broadcast
  variables: null
  version: 4
  whole_periods_only: false
version: 2
---
For any growth or year-over-year question at company level, report two numbers: the headline growth, and same-store growth. Same-store growth counts only stores open for the whole of both periods: filter stores.opened_at < the start of the earlier period. Store openings: Philadelphia Sep 2022, Brooklyn Apr 2023, Chicago May 2024, San Francisco Jun 2024, New Orleans Apr 2025, Los Angeles Oct 2025. Headline growth is driven mostly by new stores; same-store growth is the underlying health of the business. Example: 2025 vs 2024 net sales grew +69% headline but only about +4% same-store (Philadelphia + Brooklyn). Explain the gap by naming which stores opened or had their first full year.