## jaffle-data-coverage

Order data starts on 2022-09-19 (Philadelphia opened 2022-09-26), so 2022 is a partial year. The latest data is usually
mid-month: check MAX(orders.ordered_at) before any "this month / this year / YTD" question. Treat the current month as
incomplete and leave it out. Compare year-to-date against the same calendar cut-off in the prior year, never against
the full prior year. Stores that opened mid-period (e.g. Los Angeles, Oct 2025) have small samples; flag this when they
top a ranking.

## jaffle-money-in-cents

Money is stored as **integer cents**. On `orders` the columns `subtotal`, `tax_paid`, and `order_total` are cents; so
are `products.price` and `supplies.cost`. Do not sum these raw columns for a dollar figure: divide by 100 to get
dollars (for example `SUM(order_total) / 100.0`).

## jaffle-monthly-store-revenue

Monthly sales by store: pre-tax sales in dollars, `SUM(orders.subtotal) / 100.0`, by `stores.name` (through
`orders.store_id = stores.id`) over the month of `orders.ordered_at`. Use `subtotal` rather than `order_total` so
stores with different tax rates compare fairly (see jaffle-revenue-definition). Drop the current incomplete month (see
jaffle-data-coverage).

## jaffle-new-customers

A new customer in period P is a customer whose first-ever order (MIN(orders.ordered_at) per orders.customer) falls in
P. First compute each customer's first order (`orders` grouped by `customer`, MIN(ordered_at) as first_order_at), then
count those customers whose first_order_at >= start of P and < end of P. Returning customers in P = distinct customers
ordering in P minus new customers in P. To count distinct buyers, always use COUNT(DISTINCT orders.customer), not
order rows.

## jaffle-product-margin

`supplies` is the bill of materials: each row is one component consumed per unit of the product (`sku`). Unit COGS =
sum of `supplies.cost` per `sku` (cents; divide by 100 for dollars). Gross margin per unit = `products.price` - unit
COGS. For total COGS in a period, multiply each product's units sold (one `items` row per unit sold) by its unit COGS.
Current unit margins range from 89% (nutellaphone who dis?, $11.00 price, $1.21 COGS) to 65% (chai and mighty, $5.00
price, $1.75 COGS). chai and mighty is the #1 product by units in 2025 and the lowest-margin item on the menu.

## jaffle-revenue-definition

When a user says "revenue", "sales" or "AOV" without qualification, use pre-tax figures: `orders.subtotal`, and net
AOV = SUM(subtotal) / COUNT(*) over orders. `orders.order_total` includes sales tax, which is collected for the state,
not earned. Store tax rates run from 4% (Brooklyn, New Orleans) to 8% (Los Angeles), so tax-inclusive figures distort
store comparisons (e.g. in 2025 Brooklyn ranks 5th of 6 on tax-inclusive AOV but 2nd on pre-tax AOV). Use
`order_total` only when asked for gross or tax-inclusive numbers, and always state which basis you used.

## jaffle-sales-by-product

For sales by product, SKU or product type (product mix, category share), sum the price of every item sold: `items`
joined to `products` on `sku`, `SUM(products.price) / 100.0` (dollars, pre-tax). It reconciles exactly to
SUM(orders.subtotal) for every year. Do NOT sum each distinct product's price once (e.g. $28 for all beverages in 2025)
instead of once per item sold. Share of total: a group's item sales divided by the item sales of all groups.

## jaffle-same-store-growth

For any growth or year-over-year question at company level, report two numbers: the headline growth, and same-store
growth. Same-store growth counts only stores open for the whole of both periods: filter `stores.opened_at` < the start
of the earlier period. Store openings: Philadelphia Sep 2022, Brooklyn Apr 2023, Chicago May 2024, San Francisco Jun
2024, New Orleans Apr 2025, Los Angeles Oct 2025. Headline growth is driven mostly by new stores; same-store growth is
the underlying health of the business. Example: 2025 vs 2024 pre-tax sales grew +69% headline but only about +4%
same-store (Philadelphia + Brooklyn). Explain the gap by naming which stores opened or had their first full year.

## jaffle-tweets-limits

`tweets.content` is templated and uniformly positive ("Jaffles from the Jaffle Shop are {amazing|awesome|...}! Ordered
a {product}."). It cannot support sentiment, complaint or satisfaction analysis: if asked, say the data cannot answer
that rather than reporting 100% positive sentiment. It is valid for mention volume over time, the share of customers
who post, and which products are named in posts.
