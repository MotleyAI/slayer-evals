"""The Jaffle Shop database: jafgen's raw tables, seeded, with dates shifted so the last order is on `END_DATE`."""

import datetime as dt
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import duckdb

JAFFLE_SEED = 20261106
YEARS = 4
END_DATE = dt.date(2026, 10, 29)
TABLES = ("customers", "stores", "products", "orders", "items", "supplies", "tweets")
DATE_COLUMNS = {"stores": "opened_at", "orders": "ordered_at", "tweets": "tweeted_at"}
ERROR_TAIL = 2000


def _generate(out_dir: Path, seed: int) -> Path:
    """Run the seeded jafgen child in `out_dir`; returns the directory of its CSVs."""
    env = {**os.environ, "PYTHONHASHSEED": "0", "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"}
    proc = subprocess.run(
        [sys.executable, "-m", "slayer_evals.dataset.jafgen_child", str(seed), str(YEARS)],
        cwd=out_dir,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        check=False,
    )
    if proc.returncode != 0:
        tail = proc.stderr.decode(errors="replace")[-ERROR_TAIL:]
        raise RuntimeError(f"jafgen failed (exit {proc.returncode}): {tail}")
    return out_dir / "jaffle-data"


def build_jaffle_database(path: Path, seed: int | None = None) -> Path:
    """Write the Jaffle Shop database to `path` (replacing it) and return the path."""
    path.unlink(missing_ok=True)
    with tempfile.TemporaryDirectory(prefix="slayer-evals-jafgen-") as tmp:
        data_dir = _generate(Path(tmp), JAFFLE_SEED if seed is None else seed)
        con = duckdb.connect(str(path))
        try:
            for table in TABLES:
                csv = str(data_dir / f"raw_{table}.csv").replace("'", "''")
                con.execute(f"CREATE TABLE {table} AS SELECT * FROM read_csv_auto('{csv}')")
            last = con.execute("SELECT CAST(MAX(ordered_at) AS DATE) FROM orders").fetchone()
            assert last is not None
            delta = (END_DATE - last[0]).days
            for table, column in DATE_COLUMNS.items():
                con.execute(f"UPDATE {table} SET {column} = {column} + INTERVAL '{delta} days'")
            con.execute("CHECKPOINT")
        finally:
            con.close()
    return path
