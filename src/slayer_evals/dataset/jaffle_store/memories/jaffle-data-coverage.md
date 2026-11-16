---
created_at: '2026-11-06T10:40:09.102966Z'
description: 'Partial periods: 2022 and the current month/year are incomplete; compare
  YTD like-for-like'
entities:
- demo_database.orders.ordered_at
- demo_database.stores.opened_at
- demo_database.stores.name
version: 2
---
Order data starts on 2022-09-19 (Philadelphia opened 2022-09-26), so 2022 is a partial year. The latest data is usually mid-month: check ordered_at:max before any "this month / this year / YTD" question. Treat the current month as incomplete (whole_periods_only: true). Compare year-to-date against the same calendar cut-off in the prior year, never against the full prior year. Stores that opened mid-period (e.g. Los Angeles, Oct 2025) have small samples; flag this when they top a ranking.