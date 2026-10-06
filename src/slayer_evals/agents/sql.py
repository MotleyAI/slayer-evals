"""The `sql+python` profile's SQL tool: one statement on a read-only, hermetic DuckDB connection per call."""

import asyncio
import contextlib
import datetime as dt
import decimal
import json
import math
import threading
import uuid
from pathlib import Path
from typing import Any

import duckdb
from pydantic import BaseModel

SQL_TOOL = "sql"
SQL_TIMEOUT_S = 60
MAX_ROWS = 1000
# How long a timed-out statement may take to stop after it is interrupted.
JOIN_TIMEOUT_S = 10.0
GUARD_POLL_S = 0.05
_GUARDS: dict[Path, threading.Lock] = {}
_GUARDS_LOCK = threading.Lock()
SQL_CONFIG: dict[str, str | bool | int | float | list[str]] = {
    "enable_external_access": False,
    "lock_configuration": True,
}
SQL_DESCRIPTION = (
    "Run one DuckDB SQL statement against the analytics database (read-only access) and return the result as JSON "
    f"with columns, rows (at most {MAX_ROWS}) and whether the rows were truncated. "
    "The database's own catalog (information_schema, duckdb_tables(), DESCRIBE) lists what is available."
)


class SqlRun(BaseModel):
    ok: bool
    timed_out: bool = False
    text: str


def _jsonable(v: Any) -> Any:
    if isinstance(v, float) and math.isnan(v):
        return None
    if isinstance(v, decimal.Decimal):
        return float(v)
    if isinstance(v, (dt.date, dt.time)):
        return v.isoformat()
    if isinstance(v, (uuid.UUID, dt.timedelta, bytes)):
        return str(v)
    if isinstance(v, (list, tuple)):
        return [_jsonable(x) for x in v]
    if isinstance(v, dict):
        return {str(k): _jsonable(x) for k, x in v.items()}
    return v


def _payload(columns: list[str], rows: list[tuple[Any, ...]]) -> str:
    truncated = len(rows) > MAX_ROWS
    out = [[_jsonable(v) for v in r] for r in rows[:MAX_ROWS]]
    return json.dumps({"columns": columns, "rows": out, "truncated": truncated}, default=str)


def _execute(con: duckdb.DuckDBPyConnection, sql: str) -> tuple[list[str], list[tuple[Any, ...]]]:
    cur = con.execute(sql)
    columns = [d[0] for d in cur.description or []]
    return columns, cur.fetchmany(MAX_ROWS + 1) if cur.description else []


def _guard(db_path: Path) -> threading.Lock:
    """The database's guard, held from a call's start until its worker exits."""
    with _GUARDS_LOCK:
        return _GUARDS.setdefault(db_path.resolve(), threading.Lock())


def _close_and_release(con: duckdb.DuckDBPyConnection, guard: threading.Lock) -> None:
    try:
        with contextlib.suppress(Exception):  # the outcome is already known; a failed close must not mask it
            con.close()
    finally:
        guard.release()


async def _acquire(guard: threading.Lock, timeout_s: float) -> bool:
    loop = asyncio.get_running_loop()
    deadline = loop.time() + timeout_s
    while not guard.acquire(blocking=False):
        if loop.time() >= deadline:
            return False
        await asyncio.sleep(GUARD_POLL_S)
    return True


async def run_sql(sql: str, db_path: Path, timeout_s: float = SQL_TIMEOUT_S) -> SqlRun:
    """Run exactly one statement on its own read-only connection, interrupting it after `timeout_s`."""
    guard = _guard(db_path)
    if not await _acquire(guard, timeout_s):
        return SqlRun(ok=False, timed_out=True, text=f"A previous statement is still running after {timeout_s:g} s.")
    try:
        con = duckdb.connect(str(db_path), read_only=True, config=SQL_CONFIG)
    except duckdb.Error as exc:
        guard.release()
        return SqlRun(ok=False, text=str(exc))
    except BaseException:
        guard.release()
        raise
    loop = asyncio.get_running_loop()
    done: asyncio.Future[Any] = loop.create_future()

    def settle(outcome: Any) -> None:
        if not done.done():
            done.set_result(outcome)

    def work() -> None:
        # The worker closes its own connection (closing it from another thread mid-statement is unsafe) and frees the guard.
        try:
            outcome: Any = _execute(con, sql)
        except Exception as exc:  # noqa: BLE001 - handed back to the coroutine as the call's error
            outcome = exc
        finally:
            _close_and_release(con, guard)
        with contextlib.suppress(RuntimeError):  # the loop may be gone if the caller was cancelled
            loop.call_soon_threadsafe(settle, outcome)

    worker = threading.Thread(target=work, name="slayer-evals-sql", daemon=True)
    try:
        n = len(con.extract_statements(sql))
        if n != 1:
            return SqlRun(ok=False, text=f"Send exactly one SQL statement per call (got {n} statements).")
        worker.start()
        try:
            outcome = await asyncio.wait_for(asyncio.shield(done), timeout=timeout_s)
        except TimeoutError:
            return SqlRun(ok=False, timed_out=True, text=f"The statement timed out after {timeout_s:g} s.")
    except duckdb.Error as exc:
        return SqlRun(ok=False, text=str(exc))
    finally:
        # A timed-out (or cancelled) statement is interrupted and awaited; one that outlives the join keeps the guard,
        # so it never overlaps a later call.
        if worker.is_alive():
            with contextlib.suppress(duckdb.Error):  # the worker may have just finished and closed it
                con.interrupt()
            await asyncio.to_thread(worker.join, JOIN_TIMEOUT_S)
        elif worker.ident is None:
            _close_and_release(con, guard)
    if isinstance(outcome, BaseException):
        return SqlRun(ok=False, text=str(outcome))
    return SqlRun(ok=True, text=_payload(*outcome))
