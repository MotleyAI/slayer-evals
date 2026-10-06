"""The `sql+python` profile's SQL tool: read-only, hermetic, one statement per call, timeout, row cap."""

import asyncio
import datetime as dt
import hashlib
import json
import re
import shutil
import threading
import time
from pathlib import Path
from typing import Any

import duckdb
import pytest

from slayer_evals.agents import sql as sql_tool
from slayer_evals.agents.sql import MAX_ROWS, SQL_DESCRIPTION, SQL_TIMEOUT_S, run_sql
from slayer_evals.dataset import BuiltDataset

TABLES = (
    "regions",
    "customers",
    "orders",
    "returns",
    "events",
    "orders_flat",
    "products",
    "order_items",
    "campaigns",
    "campaign_members",
    "cities",
)
LONG_SQL = "select count(*) from range(1000000000000) a"


@pytest.fixture
def db(built: BuiltDataset, tmp_path: Path) -> Path:
    path = tmp_path / "bench.duckdb"
    shutil.copy2(built.db_path, path)
    return path


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def payload(text: str) -> dict:
    out = json.loads(text)
    assert set(out) == {"columns", "rows", "truncated"}
    return out


def test_limits():
    assert MAX_ROWS == 1000
    assert SQL_TIMEOUT_S == 60


async def test_query_result(db: Path):
    r = await run_sql("select region, sum(amount) as revenue from orders_flat group by 1", db_path=db)
    assert r.ok, r.text
    out = payload(r.text)
    assert out["columns"] == ["region", "revenue"]
    assert out["truncated"] is False
    con = duckdb.connect(str(db), read_only=True)
    try:
        want = con.execute("select region, sum(amount) from orders_flat group by 1").fetchall()
    finally:
        con.close()
    assert sorted(map(tuple, out["rows"]), key=str) == sorted(want, key=str)


async def test_values_are_json_friendly(db: Path):
    sql = "select date '2025-01-31' as d, timestamp '2025-03-01 09:15:00' as ts, 1.25::decimal(10, 2) as x, null as n"
    r = await run_sql(sql, db_path=db)
    assert r.ok, r.text
    ((d, ts, x, n),) = payload(r.text)["rows"]
    assert d == "2025-01-31"
    assert dt.datetime.fromisoformat(ts) == dt.datetime(2025, 3, 1, 9, 15)  # noqa: DTZ001 - naive like DuckDB TIMESTAMP
    assert isinstance(x, (int, float))
    assert x == 1.25
    assert n is None


@pytest.mark.parametrize(
    "sql",
    ["select 1; select 2", "select 1 as a; select * from no_such_table", "select 1;select 2;"],
)
async def test_batch_rejected(db: Path, sql: str):
    r = await run_sql(sql, db_path=db)
    assert not r.ok
    assert "no_such_table" not in r.text
    assert "statement" in r.text.lower()


@pytest.mark.parametrize("sql", ["", "   ", ";", "-- just a comment"])
async def test_no_statement_rejected(db: Path, sql: str):
    r = await run_sql(sql, db_path=db)
    assert not r.ok
    assert "statement" in r.text.lower()


async def test_trailing_semicolon_is_one_statement(db: Path):
    r = await run_sql("select 1 as x;", db_path=db)
    assert r.ok, r.text
    assert payload(r.text)["rows"] == [[1]]


def escape_attempts(tmp: Path) -> list[str]:
    secret = tmp / "secret.csv"
    secret.write_text("a,b\n1,2\n")
    return [
        f"select * from read_csv('{secret}')",
        "select * from read_text('/etc/hostname')",
        "select * from glob('/etc/*')",
        f"attach '{tmp / 'other.duckdb'}' as other",
        f"copy (select 1 as x) to '{tmp / 'out.csv'}'",
        f"export database '{tmp / 'exported'}'",
        "install httpfs",
        "load httpfs",
        "set enable_external_access = true",
        "set lock_configuration = false",
        "select * from read_csv('https://example.com/data.csv')",
        "insert into regions values (99, 'Atlantis')",
        "update orders set amount = 0",
        "delete from returns",
        "create table stolen as select * from customers",
        "drop table events",
    ]


async def test_escape_attempts_fail(db: Path, tmp_path: Path):
    before = digest(db)
    for sql in escape_attempts(tmp_path):
        r = await run_sql(sql, db_path=db)
        assert not r.ok, sql
    assert digest(db) == before
    for leftover in ("other.duckdb", "out.csv", "exported"):
        assert not (tmp_path / leftover).exists(), leftover
    r = await run_sql("select count(*) as n from regions", db_path=db)
    assert payload(r.text)["rows"] == [[5]]


async def test_database_error_is_a_tool_error_with_its_message(db: Path):
    r = await run_sql("select nope from orders", db_path=db)
    assert not r.ok
    assert "nope" in r.text


async def test_connection_closed_after_each_call(db: Path):
    await run_sql("select 1", db_path=db)
    await run_sql("select nope from orders", db_path=db)
    con = duckdb.connect(str(db))
    con.close()


async def test_timeout_does_not_leak_into_the_next_call(db: Path):
    threads_before = set(threading.enumerate())
    start = time.monotonic()
    slow = await run_sql(LONG_SQL, db_path=db, timeout_s=1.0)
    assert time.monotonic() - start < 15
    assert not slow.ok
    assert slow.timed_out
    assert "time" in slow.text.lower()
    # Released on return: a read-write open fails while any connection (and so any statement) is still live.
    duckdb.connect(str(db)).close()
    leftover = [t for t in threading.enumerate() if t not in threads_before and not t.name.startswith("asyncio_")]
    assert not [t for t in leftover if t.is_alive()]
    fast = await run_sql("select count(*) as n from regions", db_path=db)
    assert fast.ok, fast.text
    assert payload(fast.text)["rows"] == [[5]]


async def test_unstoppable_statement_keeps_its_connection_until_it_ends(db: Path, monkeypatch: pytest.MonkeyPatch):
    release, finished = threading.Event(), threading.Event()
    seen: list[object] = []

    def stuck(con: duckdb.DuckDBPyConnection, sql: str) -> tuple[list[str], list[tuple]]:
        release.wait(30)
        try:
            seen.append(con.execute("select 42").fetchall())
        except duckdb.Error as exc:
            seen.append(exc)
        finished.set()
        return ["x"], [(1,)]

    monkeypatch.setattr(sql_tool, "_execute", stuck)
    monkeypatch.setattr(sql_tool, "JOIN_TIMEOUT_S", 0.1)
    r = await run_sql("select 1", db_path=db, timeout_s=0.1)
    assert r.timed_out
    release.set()
    assert finished.wait(10)
    assert seen == [[(42,)]]
    for t in threading.enumerate():
        if t.name == "slayer-evals-sql":
            t.join(10)
    duckdb.connect(str(db)).close()


async def test_unstoppable_statement_blocks_only_its_own_database(
    db: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    release = threading.Event()
    real = sql_tool._execute

    def maybe_stuck(con: duckdb.DuckDBPyConnection, sql: str) -> tuple[list[str], list[tuple]]:
        if "stuck" in sql:
            release.wait(30)
        return real(con, sql)

    monkeypatch.setattr(sql_tool, "_execute", maybe_stuck)
    monkeypatch.setattr(sql_tool, "JOIN_TIMEOUT_S", 0.1)
    other = tmp_path / "other.duckdb"
    shutil.copy2(db, other)
    assert (await run_sql("select 'stuck'", db_path=db, timeout_s=0.1)).timed_out
    busy = await run_sql("select 1", db_path=db, timeout_s=0.3)
    assert not busy.ok
    assert busy.timed_out
    assert "still running" in busy.text
    elsewhere = await run_sql("select 1 as n", db_path=other, timeout_s=0.3)
    assert elsewhere.ok, elsewhere.text
    release.set()
    after = await run_sql("select 1 as n", db_path=db, timeout_s=10)
    assert after.ok, after.text
    assert payload(after.text)["rows"] == [[1]]


class FailingClose:
    error: Exception

    def __init__(self, con: duckdb.DuckDBPyConnection) -> None:
        self.con = con

    def __getattr__(self, name: str) -> object:
        return getattr(self.con, name)

    def close(self) -> None:
        self.con.close()
        raise self.error


@pytest.mark.parametrize("error", [duckdb.ConnectionException("close failed"), OSError("close failed")])
@pytest.mark.parametrize("sql", ["select 1 as n", "select 1; select 2"])
async def test_failed_close_still_frees_the_database(
    db: Path, monkeypatch: pytest.MonkeyPatch, sql: str, error: Exception
):
    real = duckdb.connect

    def connect(*a: Any, **kw: Any) -> FailingClose:
        wrapped = FailingClose(real(*a, **kw))
        wrapped.error = error
        return wrapped

    monkeypatch.setattr(sql_tool.duckdb, "connect", connect)
    first = await run_sql(sql, db_path=db, timeout_s=1.0)
    assert not first.timed_out
    assert first.ok == (sql == "select 1 as n")
    again = await run_sql("select 1 as n", db_path=db, timeout_s=1.0)
    assert again.ok, again.text


async def test_failed_connect_frees_the_database(db: Path, monkeypatch: pytest.MonkeyPatch):
    real = duckdb.connect
    errors = iter([duckdb.IOException("cannot open"), OSError("no handles")])

    def connect(*a: Any, **kw: Any) -> duckdb.DuckDBPyConnection:
        error = next(errors, None)
        if error is not None:
            raise error
        return real(*a, **kw)

    monkeypatch.setattr(sql_tool.duckdb, "connect", connect)
    failed = await run_sql("select 1", db_path=db, timeout_s=1.0)
    assert not failed.ok
    assert "cannot open" in failed.text
    with pytest.raises(OSError, match="no handles"):
        await run_sql("select 1", db_path=db, timeout_s=1.0)
    again = await run_sql("select 1 as n", db_path=db, timeout_s=1.0)
    assert again.ok, again.text


async def test_cancelled_call_stops_its_statement_and_frees_the_database(db: Path):
    call = asyncio.create_task(run_sql(LONG_SQL, db_path=db))
    await asyncio.sleep(0.5)
    call.cancel()
    with pytest.raises(asyncio.CancelledError):
        await call
    after = await run_sql("select 1 as n", db_path=db, timeout_s=1.0)
    assert after.ok, after.text


@pytest.mark.parametrize(("n", "rows", "truncated"), [(1500, 1000, True), (1001, 1000, True), (1000, 1000, False)])
async def test_row_cap(db: Path, n: int, rows: int, truncated: bool):
    r = await run_sql(f"select * from range({n}) t(i)", db_path=db)
    assert r.ok, r.text
    out = payload(r.text)
    assert len(out["rows"]) == rows
    assert out["truncated"] is truncated
    assert out["rows"][0] == [0]


def test_description_names_dialect_and_access_only():
    low = SQL_DESCRIPTION.lower()
    assert "duckdb" in low
    assert "read-only" in low or "read only" in low
    assert "slayer" not in low
    for table in (t for t in TABLES if t != "returns"):  # "returns" is also a verb
        assert not re.search(rf"\b{table}\b", low), table
