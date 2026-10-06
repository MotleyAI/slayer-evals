"""Truth computation and snapshots."""

import datetime as dt
from pathlib import Path

import duckdb
import pytest

from slayer_evals.core import Table
from slayer_evals.tasks import (
    SnapshotDriftError,
    TruthError,
    check_snapshots,
    compute_truth,
    compute_truths,
    write_snapshots,
)
from tests.helpers import make_task


@pytest.fixture
def db(tmp_path: Path) -> Path:
    path = tmp_path / "t.duckdb"
    con = duckdb.connect(str(path))
    con.execute("create table t (k varchar, d date, v double)")
    con.execute("insert into t values ('a', date '2025-01-01', 1.5), ('b', date '2025-02-01', null)")
    con.close()
    return path


def test_truth_from_sql(db: Path):
    task = make_task(id="t1", truth_sql="select k, d, v from t order by k")
    truth = compute_truth(task, db)
    assert truth.columns == ["k", "d", "v"]
    assert [r[0] for r in truth.rows] == ["a", "b"]
    assert truth.rows[0][1] in (dt.date(2025, 1, 1), "2025-01-01")
    assert truth.rows[1][2] is None


def test_truth_sql_error_names_task(db: Path):
    task = make_task(id="broken-task", truth_sql="select nope from t")
    with pytest.raises(TruthError) as exc:
        compute_truth(task, db)
    assert "broken-task" in str(exc.value)
    assert "nope" in str(exc.value)


def test_compute_truths_keyed_by_id(db: Path):
    tasks = [make_task(id="a", truth_sql="select 1 as x"), make_task(id="b", truth_sql="select 2 as x")]
    truths = compute_truths(tasks, db)
    assert set(truths) == {"a", "b"}
    assert truths["b"] == Table(columns=["x"], rows=[[2]])


def test_snapshot_round_trip(db: Path, tmp_path: Path):
    truths = compute_truths([make_task(id="t1", truth_sql="select k, d, v from t order by k")], db)
    snap = tmp_path / "truth"
    write_snapshots(truths, snap)
    assert (snap / "t1.json").exists()
    check_snapshots(truths, snap)


def test_snapshot_drift_detected(db: Path, tmp_path: Path):
    snap = tmp_path / "truth"
    write_snapshots(compute_truths([make_task(id="t1", truth_sql="select v from t order by k")], db), snap)
    changed = compute_truths([make_task(id="t1", truth_sql="select v * 2 as v from t order by k")], db)
    with pytest.raises(SnapshotDriftError) as exc:
        check_snapshots(changed, snap)
    assert "t1" in str(exc.value)


def test_missing_snapshot_is_drift(db: Path, tmp_path: Path):
    snap = tmp_path / "truth"
    snap.mkdir()
    truths = compute_truths([make_task(id="new-task", truth_sql="select 1 as x")], db)
    with pytest.raises(SnapshotDriftError) as exc:
        check_snapshots(truths, snap)
    assert "new-task" in str(exc.value)


def test_stale_snapshot_is_drift(db: Path, tmp_path: Path):
    snap = tmp_path / "truth"
    write_snapshots(compute_truths([make_task(id="gone", truth_sql="select 1 as x")], db), snap)
    with pytest.raises(SnapshotDriftError) as exc:
        check_snapshots({}, snap)
    assert "gone" in str(exc.value)


def test_unordered_truth_rows_are_sorted(db: Path):
    truth = compute_truth(make_task(id="t", truth_sql="select k, v from t order by k desc"), db)
    assert [r[0] for r in truth.rows] == ["a", "b"]


def test_ordered_truth_keeps_sql_order(db: Path):
    task = make_task(id="t", truth_sql="select k from t order by k desc", compare={"keys": ["k"], "ordered": True})
    assert [r[0] for r in compute_truth(task, db).rows] == ["b", "a"]


def test_snapshot_tolerates_last_bit_float_noise(tmp_path: Path):
    snap = tmp_path / "truth"
    write_snapshots({"t": Table(columns=["v"], rows=[[0.1 + 0.2]])}, snap)
    check_snapshots({"t": Table(columns=["v"], rows=[[0.3]])}, snap)
    drifted = {"t": Table(columns=["v"], rows=[[0.31]])}
    with pytest.raises(SnapshotDriftError):
        check_snapshots(drifted, snap)
