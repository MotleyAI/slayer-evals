"""Seeded generator for the benchmark database: the probe dataset's schema at realistic size, plus planted edge cases."""

import datetime as dt
import random
from pathlib import Path
from typing import Any

import duckdb


def _naive(year: int, month: int, day: int, hour: int = 0, minute: int = 0, second: int = 0) -> dt.datetime:
    """A naive timestamp, as DuckDB `TIMESTAMP` stores it."""
    return dt.datetime(year, month, day, hour, minute, second)  # noqa: DTZ001


DEFAULT_SEED = 2055
START = dt.date(2023, 1, 1)
END = dt.date(2025, 12, 31)
# No orders in this month; returns still fall into it.
GAP_MONTH = (2024, 8)
N_CUSTOMERS = 200
N_ORDERS = 5000
N_RETURNS = 250
N_EVENTS = 600

REGIONS = [(1, "North"), (2, "South"), (3, "East"), (4, "West"), (5, "Arctic")]
# Oslo is in two regions; Arctic (5) has no customers.
CITIES = {
    1: ["Oslo", "Bergen", "Trondheim"],
    2: ["Rome", "Naples", "Oslo"],
    3: ["Vienna", "Prague"],
    4: ["Lisbon", "Porto"],
}
REGION_WEIGHTS = [0.3, 0.3, 0.2, 0.2]
TIERS = (["gold", "silver", "bronze"], [0.2, 0.35, 0.45])
FIRST = ["Ada", "Ben", "Cleo", "Dan", "Ella", "Finn", "Gia", "Hugo", "Ines", "Jon", "Kai", "Lena", "Milo", "Nora"]
LAST = ["Berg", "Costa", "Dahl", "Ek", "Fischer", "Greco", "Holm", "Ito", "Jansen", "Kovac", "Lund", "Moreau"]

SCHEMA = """
CREATE TABLE regions (id INTEGER PRIMARY KEY, name VARCHAR);
CREATE TABLE customers (
  id INTEGER PRIMARY KEY, name VARCHAR, region_id INTEGER REFERENCES regions (id), city VARCHAR,
  tier VARCHAR, credit DOUBLE, discount DOUBLE
);
CREATE TABLE orders (
  id INTEGER PRIMARY KEY, customer_id INTEGER REFERENCES customers (id), amount DOUBLE, status VARCHAR,
  order_date DATE
);
CREATE TABLE returns (
  id INTEGER PRIMARY KEY, customer_id INTEGER REFERENCES customers (id), amount DOUBLE, return_date DATE
);
CREATE TABLE events (id INTEGER PRIMARY KEY, amount DOUBLE, event_ts TIMESTAMP);
CREATE VIEW orders_flat AS
SELECT o.id, o.customer_id, o.amount, o.status, o.order_date,
       r.name AS region, c.city, c.tier, c.credit, c.discount
FROM orders o
LEFT JOIN customers c ON o.customer_id = c.id
LEFT JOIN regions r ON c.region_id = r.id;
"""

# Planted rows use ids from 9001 up, so generated ids never collide with them.
NO_ORDERS_CUSTOMER = 9001
NULL_REGION_CUSTOMER = 9002
PLANTED_CUSTOMERS = [
    (NO_ORDERS_CUSTOMER, "Frank Moreau", 1, "Oslo", "gold", 600.0, 0.0),
    (NULL_REGION_CUSTOMER, "Eve Lund", None, "Paris", "silver", 500.0, 5.0),
]
PLANTED_EVENTS = [
    (9001, 1.0, _naive(2025, 3, 1, 9, 2, 0)),
    (9002, 2.0, _naive(2025, 3, 1, 9, 14, 59)),
    (9003, 4.0, _naive(2025, 3, 1, 9, 15, 0)),
    (9004, 8.0, _naive(2025, 3, 1, 9, 47, 30)),
    (9005, 16.0, _naive(2025, 3, 1, 10, 0, 0)),
]


def _rng(seed: int, table: str) -> random.Random:
    return random.Random(f"{seed}:{table}")


def _order_days() -> list[dt.date]:
    days = [START + dt.timedelta(days=i) for i in range((END - START).days + 1)]
    return [d for d in days if (d.year, d.month) != GAP_MONTH]


def _customers(seed: int) -> list[tuple[Any, ...]]:
    rng = _rng(seed, "customers")
    rows = []
    for cid in range(1, N_CUSTOMERS + 1):
        region = rng.choices([1, 2, 3, 4], weights=REGION_WEIGHTS)[0]
        name = f"{rng.choice(FIRST)} {rng.choice(LAST)}"
        tier = rng.choices(TIERS[0], weights=TIERS[1])[0]
        credit = float(rng.randrange(100, 1001, 10))
        discount = float(rng.choice([0, 0, 1, 2, 3, 5, 10]))
        rows.append((cid, name, region, rng.choice(CITIES[region]), tier, credit, discount))
    return rows + PLANTED_CUSTOMERS


def _orders(seed: int) -> list[tuple[Any, ...]]:
    rng = _rng(seed, "orders")
    days = _order_days()
    weights = [rng.uniform(0.2, 3.0) for _ in range(N_CUSTOMERS)]
    drafts = []
    for _ in range(N_ORDERS):
        day = rng.choice(days)
        customer = rng.choices(range(1, N_CUSTOMERS + 1), weights=weights)[0]
        amount = round(rng.lognormvariate(4.0, 0.6), 2)
        status = "ok" if rng.random() < 0.88 else "bad"
        drafts.append((day, customer, amount, status))
    drafts.sort(key=lambda d: (d[0], d[1], d[2], d[3]))
    rows = [(i, c, a, s, d) for i, (d, c, a, s) in enumerate(drafts, start=1)]
    planted_days = [rng.choice(days) for _ in range(16)]
    for k, day in enumerate(sorted(planted_days[:6])):
        rows.append((9001 + k, None, round(rng.lognormvariate(4.0, 0.6), 2), "ok", day))
    for k, day in enumerate(sorted(planted_days[6:])):
        rows.append((9101 + k, NULL_REGION_CUSTOMER, round(rng.lognormvariate(4.0, 0.6), 2), "ok", day))
    return rows


def _returns(seed: int, orders: list[tuple[Any, ...]]) -> list[tuple[Any, ...]]:
    rng = _rng(seed, "returns")
    returnable = [o for o in orders if o[1] is not None and o[3] == "ok" and o[0] < 9001]
    drafts = []
    for _ in range(N_RETURNS):
        _, customer, amount, _, day = rng.choice(returnable)
        when = min(day + dt.timedelta(days=rng.randint(3, 40)), END)
        drafts.append((when, customer, round(amount * rng.choice([1.0, 0.5, 0.25]), 2)))
    drafts.sort(key=lambda d: (d[0], d[1], d[2]))
    rows: list[tuple[Any, ...]] = [(i, c, a, d) for i, (d, c, a) in enumerate(drafts, start=1)]
    rows.append((9001, None, 15.0, dt.date(2025, 2, 20)))
    rows.append((9002, NULL_REGION_CUSTOMER, 10.0, dt.date(2025, 1, 15)))
    rows.append((9003, 1, 40.0, dt.date(GAP_MONTH[0], GAP_MONTH[1], 12)))
    return rows


def _events(seed: int) -> list[tuple[Any, ...]]:
    rng = _rng(seed, "events")
    start = _naive(2025, 1, 1)
    span = int((_naive(2025, 7, 1) - start).total_seconds())
    stamps = sorted(start + dt.timedelta(seconds=rng.randrange(span)) for _ in range(N_EVENTS))
    rows = [(i, round(rng.uniform(1, 50), 2), ts) for i, ts in enumerate(stamps, start=1)]
    return rows + PLANTED_EVENTS


def build_database(path: Path, seed: int = DEFAULT_SEED) -> Path:
    """Write the benchmark database to `path` (replacing it) and return the path."""
    path.unlink(missing_ok=True)
    orders = _orders(seed)
    con = duckdb.connect(str(path))
    try:
        for stmt in (s.strip() for s in SCHEMA.split(";")):
            if stmt:
                con.execute(stmt)
        con.executemany("INSERT INTO regions VALUES (?, ?)", REGIONS)
        con.executemany("INSERT INTO customers VALUES (?, ?, ?, ?, ?, ?, ?)", _customers(seed))
        con.executemany("INSERT INTO orders VALUES (?, ?, ?, ?, ?)", orders)
        con.executemany("INSERT INTO returns VALUES (?, ?, ?, ?)", _returns(seed, orders))
        con.executemany("INSERT INTO events VALUES (?, ?, ?)", _events(seed))
        con.execute("CHECKPOINT")
    finally:
        con.close()
    return path
