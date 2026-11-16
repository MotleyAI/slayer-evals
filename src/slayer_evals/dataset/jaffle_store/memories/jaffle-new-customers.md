---
created_at: '2026-11-06T10:40:13.705324Z'
description: 'Definition and recipe: new vs returning customers in a period'
entities:
- demo_database.orders.customer
- demo_database.orders.ordered_at
- demo_database.orders.unique_customers
- demo_database.customers
version: 2
---
A new customer in period P is a customer whose first-ever order (ordered_at:min per orders.customer) falls in P. This takes a two-stage query. Stage 1 (name it first_orders): source orders, dimensions [customer], measures [{name: first_order_at, formula: ordered_at:min}]. Stage 2: source first_orders, measures [*:count], filters first_order_at >= start of P and < end of P. Returning customers in P = unique_customers in P minus new customers in P. To count distinct buyers, always use the unique_customers measure (customer:count_distinct), not order rows.