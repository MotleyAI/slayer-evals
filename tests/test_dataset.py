"""Deterministic dataset build, probe schema and planted edge cases."""

import datetime as dt
import hashlib
import json
from pathlib import Path

import duckdb
import pytest

from slayer_evals.dataset import DEFAULT_SEED, BuiltDataset, build_database
from tests.helpers import REPO

PROBE_TABLES = ("regions", "customers", "orders", "returns", "events", "orders_flat")
NEW_TABLES = ("products", "order_items", "campaigns", "campaign_members", "cities")
TABLES = PROBE_TABLES + NEW_TABLES
PROBE_HASHES = REPO / "tests" / "fixtures" / "probe_table_hashes.json"

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
        row = con.execute(sql).fetchone()
        assert row is not None
        return row[0]
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


def test_probe_tables_unchanged(built: BuiltDataset):
    committed = json.loads(PROBE_HASHES.read_text())
    assert sorted(committed) == sorted(PROBE_TABLES)
    for table in PROBE_TABLES:
        assert table_hash(built.db_path, table) == committed[table], table


def test_new_tables_are_deterministic_and_seeded(tmp_path: Path):
    a = build_database(tmp_path / "a.duckdb", seed=DEFAULT_SEED)
    b = build_database(tmp_path / "b.duckdb", seed=DEFAULT_SEED + 1)
    assert any(table_hash(a, t) != table_hash(b, t) for t in ("order_items", "campaign_members"))


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
    assert {(t, c) for t, c in declared if t in PROBE_TABLES} == {
        ("customers", ("region_id",)),
        ("orders", ("customer_id",)),
        ("returns", ("customer_id",)),
    }
    assert {
        ("order_items", ("order_id",)),
        ("order_items", ("product_id",)),
        ("campaign_members", ("campaign_id",)),
        ("campaign_members", ("customer_id",)),
        ("cities", ("region_id",)),
    } <= declared


def test_new_tables_have_keys(built: BuiltDataset):
    con = duckdb.connect(str(built.db_path), read_only=True)
    try:
        pks = con.execute(
            "select table_name, constraint_column_names from duckdb_constraints() where constraint_type = 'PRIMARY KEY'"
        ).fetchall()
        columns = {
            t: {
                r[0]
                for r in con.execute(
                    "select column_name from information_schema.columns where table_name = ?", [t]
                ).fetchall()
            }
            for t in NEW_TABLES
        }
    finally:
        con.close()
    keys = {t: set(c) for t, c in pks}
    for table in NEW_TABLES:
        assert table in keys, table
    assert keys["cities"] == {"city", "region_id"}
    assert {"order_id", "product_id", "line_amount"} <= columns["order_items"]
    assert {"campaign_id", "customer_id"} <= columns["campaign_members"]
    assert {"city", "region_id"} <= columns["cities"]


def test_orders_flat_left_joins(built: BuiltDataset):
    db = built.db_path
    assert scalar(db, "select count(*) from orders_flat") == scalar(db, "select count(*) from orders")
    assert scalar(db, "select count(*) from orders_flat where customer_id is null and region is null") >= 1


def test_items_add_up_to_orders(built: BuiltDataset):
    db = built.db_path
    off = scalar(
        db,
        "select count(*) from orders o left join (select order_id, sum(line_amount) s, count(*) n "
        "from order_items group by 1) i on i.order_id = o.id "
        "where i.s is null or abs(i.s - o.amount) > 0.005 or i.n not between 1 and 4",
    )
    assert off == 0
    assert scalar(db, "select count(*) from order_items where order_id not in (select id from orders)") == 0
    assert scalar(db, "select count(distinct order_id) from order_items") == scalar(db, "select count(*) from orders")
    assert scalar(db, "select count(*) from (select order_id from order_items group by 1 having count(*) > 1)") > 0


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
    "event on the last day of a month after midnight": (
        "select count(*) from events where event_ts::date = last_day(event_ts::date) "
        "and event_ts > event_ts::date::timestamp"
    ),
    "city in two regions in cities": (
        "select count(*) from (select city from cities group by city having count(distinct region_id) >= 2)"
    ),
    "city in two regions in customers and cities": (
        "select count(*) from (select c.city from customers c join cities ci "
        "on ci.city = c.city and ci.region_id = c.region_id "
        "group by c.city having count(distinct c.region_id) >= 2)"
    ),
    "two equal-amount multi-item orders in one region": (
        "with multi as (select order_id from order_items group by 1 having count(*) > 1) "
        "select count(*) from (select c.region_id, o.amount from orders o "
        "join customers c on c.id = o.customer_id join multi m on m.order_id = o.id "
        "where c.region_id is not null group by 1, 2 having count(*) >= 2)"
    ),
    "customer with orders in two or more campaigns": (
        "select count(*) from (select cm.customer_id from campaign_members cm "
        "where exists (select 1 from orders o where o.customer_id = cm.customer_id) "
        "group by 1 having count(distinct cm.campaign_id) >= 2)"
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
