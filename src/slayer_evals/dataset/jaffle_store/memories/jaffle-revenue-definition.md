---
created_at: '2026-11-06T10:40:46.506576Z'
description: '"Revenue", "sales" and "AOV" mean pre-tax (net_sales) unless the user
  asks for gross'
entities:
- demo_database.orders
- demo_database.stores.name
- demo_database.orders.net_sales
- demo_database.orders.order_count
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
  - description: null
    formula: net_sales / order_count
    label: null
    meta: null
    name: net_aov
    type: null
  - description: null
    formula: order_count
    label: null
    meta: null
    name: null
    type: null
  name: null
  offset: null
  order: null
  source_model: orders
  time_dimensions: null
  to_many_handling: broadcast
  variables: null
  version: 4
  whole_periods_only: false
version: 2
---
When a user says "revenue", "sales" or "AOV" without qualification, use pre-tax figures: orders.net_sales, and net AOV = net_sales / order_count. total_revenue and the saved avg_order_value include sales tax, which is collected for the state, not earned. Store tax rates run from 4% (Brooklyn, New Orleans) to 8% (Los Angeles), so tax-inclusive figures distort store comparisons (e.g. in 2025 Brooklyn ranks 5th of 6 on tax-inclusive AOV but 2nd on pre-tax AOV). Use total_revenue / avg_order_value only when asked for gross or tax-inclusive numbers, and always state which basis you used.