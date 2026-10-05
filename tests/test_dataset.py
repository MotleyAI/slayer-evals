"""Deterministic dataset build, probe schema and planted edge cases."""

import datetime as dt
import hashlib
from pathlib import Path

import duckdb
import pytest

from slayer_evals.dataset import DEFAULT_SEED, BuiltDataset, build_database

TABLES = ("regions", "customers", "orders", "returns", "events", "orders_flat")

SCHEMA = {
    "regions": [("id", "INTEGER"), ("name", "VARCHAR")],
    "customers": [
        ("id", "INTEGER"),
        ("name", "VARCHAR"),
        ("region_id", "INTEGER"),
        ("city", "VARCHAR"),
        ("tier", "VARCHAR"),
        ("credit", "DOUBLE"),
        ("discount", "DOUBLE"),
    ],
    "orders": [
        ("id", "INTEGER"),
        ("customer_id", "INTEGER"),
        ("amount", "DOUBLE"),
        ("status", "VARCHAR"),
        ("order_date", "DATE"),
    ],
    "returns": [("id", "INTEGER"), ("customer_id", "INTEGER"), ("amount", "DOUBLE"), ("return_date", "DATE")],
    "events": [("id", "INTEGER"), ("amount", "DOUBLE"), ("event_ts", "TIMESTAMP")],
    "orders_flat": [
        ("id", "INTEGER"),
        ("customer_id", "INTEGER"),
        ("amount", "DOUBLE"),
        ("status", "VARCHAR"),
        ("order_date", "DATE"),
        ("region", "VARCHAR"),
        ("city", "VARCHAR"),
        ("tier", "VARCHAR"),
        ("credit", "DOUBLE"),
        ("discount", "DOUBLE"),
    ],
}


def table_hash(db: Path, table: str) -> str:
    con = duckdb.connect(str(db), read_only=True)
    try:
        rows = con.execute(f"select * from {table} order by all").fetchall()
    finally:
        con.close()
    return hashlib.sha256(repr(rows).encode()).hexdigest()


def scalar(db: Path, sql: str):
    con = duckdb.connect(str(db), read_only=True)
    try:
        return con.execute(sql).fetchone()[0]
    finally:
        con.close()


def test_same_seed_same_tables(tmp_path: Path):
    a = build_database(tmp_path / "a.duckdb", seed=DEFAULT_SEED)
    b = build_database(tmp_path / "b.duckdb", seed=DEFAULT_SEED)
    for t in TABLES:
        assert table_hash(a, t) == table_hash(b, t), t


def test_different_seed_different_orders(tmp_path: Path):
    a = build_database(tmp_path / "a.duckdb", seed=DEFAULT_SEED)
    b = build_database(tmp_path / "b.duckdb", seed=DEFAULT_SEED + 1)
    assert table_hash(a, "orders") != table_hash(b, "orders")


def test_schema_matches_probe_layout(built: BuiltDataset):
    con = duckdb.connect(str(built.db_path), read_only=True)
    try:
        for table, cols in SCHEMA.items():
            got = con.execute(
                "select column_name, data_type from information_schema.columns "
                "where table_name = ? order by ordinal_position",
                [table],
            ).fetchall()
            assert [tuple(r) for r in got] == cols, table
        fks = con.execute(
            "select table_name, constraint_column_names from duckdb_constraints() where constraint_type = 'FOREIGN KEY'"
        ).fetchall()
    finally:
        con.close()
    declared = {(t, tuple(c)) for t, c in fks}
    assert declared == {
        ("customers", ("region_id",)),
        ("orders", ("customer_id",)),
        ("returns", ("customer_id",)),
    }


def test_orders_flat_left_joins(built: BuiltDataset):
    db = built.db_path
    assert scalar(db, "select count(*) from orders_flat") == scalar(db, "select count(*) from orders")
    assert scalar(db, "select count(*) from orders_flat where customer_id is null and region is null") >= 1


def test_realistic_size(built: BuiltDataset):
    db = built.db_path
    assert 100 <= scalar(db, "select count(*) from customers") <= 400
    assert 2500 <= scalar(db, "select count(*) from orders") <= 10000
    assert scalar(db, "select min(order_date) from orders") >= dt.date(2023, 1, 1)
    assert scalar(db, "select max(order_date) from orders") <= dt.date(2025, 12, 31)


EDGE_CASES = {
    "customer with no orders": (
        "select count(*) from customers c where not exists (select 1 from orders o where o.customer_id = c.id)"
    ),
    "customer with NULL region": "select count(*) from customers where region_id is null",
    "city in two regions": (
        "select count(*) from (select city from customers where region_id is not null "
        "group by city having count(distinct region_id) >= 2)"
    ),
    "region with no customers": (
        "select count(*) from regions r where not exists (select 1 from customers c where c.region_id = r.id)"
    ),
    "order with NULL customer_id": "select count(*) from orders where customer_id is null",
    "month with returns but no orders": (
        "select count(*) from (select distinct date_trunc('month', return_date) m from returns) r "
        "where not exists (select 1 from orders o where date_trunc('month', o.order_date) = r.m)"
    ),
    "return with NULL customer_id": "select count(*) from returns where customer_id is null",
    "events in different quarter-hour buckets within one hour": (
        "select count(*) from (select date_trunc('hour', event_ts) h from events "
        "where minute(event_ts) % 15 <> 0 or second(event_ts) <> 0 "
        "group by h having count(distinct floor(minute(event_ts) / 15)) >= 2)"
    ),
}


@pytest.mark.parametrize("name", sorted(EDGE_CASES))
def test_planted_edge_case_present(built: BuiltDataset, name: str):
    assert scalar(built.db_path, EDGE_CASES[name]) >= 1, name


def test_month_gap_inside_order_range(built: BuiltDataset):
    gaps = scalar(
        built.db_path,
        "select count(*) from (select unnest(generate_series(date_trunc('month', min(order_date)), "
        "date_trunc('month', max(order_date)), interval 1 month)) m from orders) s "
        "where not exists (select 1 from orders o where date_trunc('month', o.order_date) = s.m)",
    )
    assert gaps >= 1
