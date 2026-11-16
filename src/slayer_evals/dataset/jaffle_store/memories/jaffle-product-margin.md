---
created_at: '2026-11-06T10:40:44.974086Z'
description: Unit COGS and gross margin per product come from supplies (bill of materials
  per sku)
entities:
- demo_database.supplies
- demo_database.supplies.sku
- demo_database.products.name
- demo_database.products.price
- demo_database.supplies.total_supply_cost
query:
  dimensions:
  - label: null
    model: null
    name: sku
  - label: null
    model: products
    name: name
  - label: null
    model: products
    name: price
  distinct_dimension_values: true
  filters: null
  limit: null
  main_time_dimension: null
  measures:
  - description: null
    formula: total_supply_cost
    label: null
    meta: null
    name: null
    type: null
  name: null
  offset: null
  order: null
  source_model: supplies
  time_dimensions: null
  to_many_handling: broadcast
  variables: null
  version: 4
  whole_periods_only: false
version: 2
---
supplies is the bill of materials: each row is one component consumed per unit of the product (sku). Unit COGS = sum of supplies.cost per sku (cents; total_supply_cost gives dollars). Gross margin per unit = products.price - unit COGS. For total COGS in a period, multiply each product's items.units_sold by its unit COGS. Current unit margins range from 89% (nutellaphone who dis?, $11.00 price, $1.21 COGS) to 65% (chai and mighty, $5.00 price, $1.75 COGS). chai and mighty is the #1 product by units in 2025 and the lowest-margin item on the menu.