---
created_at: '2026-11-06T10:40:10.644884Z'
description: Money columns are integer cents; use the dollars aggregation / dollar
  measures.
entities:
- demo_database.orders.order_total
- demo_database.orders.subtotal
- demo_database.orders.tax_paid
- demo_database.products.price
- demo_database.supplies.cost
version: 2
---
Money is stored as **integer cents**. On `orders` the columns `subtotal`, `tax_paid`, and `order_total` are cents; so are `products.price` and `supplies.cost`. Do not `sum` these raw columns for a dollar figure. Use the `dollars` aggregation (`order_total:dollars`) or the pre-built dollar measures (`total_revenue`, `net_sales`, `tax_collected`, `avg_order_value`), which divide by 100.