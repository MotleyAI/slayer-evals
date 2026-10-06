"""Table comparison: column resolution, multiset/ordered, tolerance, NULL/NaN, dates, row counts."""

import datetime as dt
import math

from slayer_evals.core import Compare, Table
from slayer_evals.grading import match_tables

TRUTH = Table(
    columns=["region", "city", "region_total"],
    rows=[["North", "Oslo", 705.0], ["North", "Bergen", 705.0], ["South", "Rome", 890.0], [None, "Paris", 280.0]],
)
CMP = Compare(keys=["region", "city"], values=["region_total"])


def res(columns: list[str], rows: list[list]) -> Table:
    return Table(columns=columns, rows=rows)


def test_exact_match():
    assert match_tables(TRUTH, TRUTH, CMP).ok


def test_order_insensitive_with_tolerance():
    rows = [list(r) for r in reversed(TRUTH.rows)]
    rows[0][2] += 1e-9
    assert match_tables(TRUTH, res(TRUTH.columns, rows), CMP).ok


def test_value_outside_tolerance():
    rows = [list(r) for r in TRUTH.rows]
    rows[0][2] = 706.0
    m = match_tables(TRUTH, res(TRUTH.columns, rows), CMP)
    assert not m.ok


def test_dotted_suffix_resolution():
    cols = ["orders_flat.region", "orders_flat.city", "orders_flat.region_total"]
    assert match_tables(TRUTH, res(cols, [list(r) for r in TRUTH.rows]), CMP).ok


def test_flattened_resolution():
    cols = ["agg.orders_flat__region", "agg.orders_flat__city", "agg.region_total"]
    assert match_tables(TRUTH, res(cols, [list(r) for r in TRUTH.rows]), CMP).ok


def test_ambiguous_column_fails():
    truth = Table(columns=["name", "n"], rows=[["Alice", 1]])
    result = res(["orders.customers.name", "orders.customers.regions.name", "orders.n"], [["Alice", "North", 1]])
    m = match_tables(truth, result, Compare(keys=["name"], values=["n"]))
    assert not m.ok
    assert "name" in m.reason
    assert "ambiguous" in m.reason


def test_missing_column_fails():
    m = match_tables(TRUTH, res(["region", "city"], [r[:2] for r in TRUTH.rows]), CMP)
    assert not m.ok
    assert "region_total" in m.reason


def test_extra_columns_ignored_unless_exact():
    cols = TRUTH.columns + ["extra"]
    rows = [list(r) + [1] for r in TRUTH.rows]
    assert match_tables(TRUTH, res(cols, rows), CMP).ok
    exact = CMP.model_copy(update={"columns_exact": True})
    assert not match_tables(TRUTH, res(cols, rows), exact).ok


def test_truncated_result_fails_with_counts():
    truth = Table(columns=["k", "v"], rows=[[i, float(i)] for i in range(25)])
    m = match_tables(truth, res(["k", "v"], truth.rows[:20]), Compare(keys=["k"], values=["v"]))
    assert not m.ok
    assert "20" in m.reason
    assert "25" in m.reason


def test_ordered_task_rejects_wrong_order():
    truth = Table(columns=["k", "v"], rows=[["a", 3], ["b", 2], ["c", 1]])
    cmp = Compare(keys=["k"], values=["v"], ordered=True)
    assert match_tables(truth, truth, cmp).ok
    assert not match_tables(truth, res(["k", "v"], list(reversed(truth.rows))), cmp).ok


def test_null_only_equals_null():
    truth = Table(columns=["k", "v"], rows=[["a", None]])
    cmp = Compare(keys=["k"], values=["v"])
    assert match_tables(truth, res(["k", "v"], [["a", None]]), cmp).ok
    assert not match_tables(truth, res(["k", "v"], [["a", 0]]), cmp).ok
    assert not match_tables(truth, res(["k", "v"], [["a", ""]]), cmp).ok


def test_nan_is_null():
    truth = Table(columns=["k", "v"], rows=[["a", None]])
    assert match_tables(truth, res(["k", "v"], [["a", math.nan]]), Compare(keys=["k"], values=["v"])).ok


def test_dates_normalized():
    truth = Table(columns=["month", "rev"], rows=[[dt.date(2025, 1, 1), 140.0], [dt.date(2025, 2, 1), 200.0]])
    cmp = Compare(keys=["month"], values=["rev"])
    for spelling in ("2025-01-01 00:00:00", "2025-01-01", "2025-01-01T00:00:00"):
        result = res(["orders.month", "orders.rev"], [[spelling, 140], ["2025-02-01", 200.0]])
        assert match_tables(truth, result, cmp).ok, spelling


def test_timestamps_normalized():
    truth = Table(columns=["ts", "n"], rows=[[dt.datetime(2025, 3, 1, 9, 15), 2]])  # noqa: DTZ001 - naive like DuckDB TIMESTAMP
    result = res(["ts", "n"], [["2025-03-01 09:15:00", 2]])
    assert match_tables(truth, result, Compare(keys=["ts"], values=["n"])).ok


def test_numeric_strings_compare_as_numbers():
    truth = Table(columns=["k", "v"], rows=[["a", 1.5]])
    assert match_tables(truth, res(["k", "v"], [["a", "1.5"]]), Compare(keys=["k"], values=["v"])).ok


def test_empty_compare_uses_all_truth_columns():
    truth = Table(columns=["k", "v"], rows=[["a", 1]])
    assert match_tables(truth, res(["x.k", "x.v"], [["a", 1]]), Compare()).ok
    assert not match_tables(truth, res(["x.k", "x.v"], [["a", 2]]), Compare()).ok


def test_columns_matched_by_values():
    truth = Table(columns=["region", "revenue"], rows=[["North", 10.0], ["South", 20.0], [None, 5.0]])
    result = res(["orders.customers.regions.name", "orders.rev"], [["South", 20.0], [None, 5.0], ["North", 10.0]])
    m = match_tables(truth, result, Compare(keys=["region"], values=["revenue"]))
    assert m.ok, m.reason
    assert m.columns == {"region": "orders.customers.regions.name", "revenue": "orders.rev"}
    assert "matched by values" in m.reason


def test_name_matches_are_recorded():
    m = match_tables(TRUTH, TRUTH, CMP)
    assert m.columns == {"region": "region", "city": "city", "region_total": "region_total"}


def test_value_match_prefers_closest_names():
    truth = Table(columns=["k", "revenue", "cost"], rows=[["a", 1.0, 1.0], ["b", 2.0, 2.0]])
    result = res(["k", "x.cost_total", "x.revenue_total"], [["a", 1.0, 1.0], ["b", 2.0, 2.0]])
    m = match_tables(truth, result, Compare(keys=["k"], values=["revenue", "cost"]))
    assert m.ok
    assert m.columns == {"k": "k", "revenue": "x.revenue_total", "cost": "x.cost_total"}


def test_value_match_respects_row_alignment():
    truth = Table(columns=["k", "v"], rows=[["a", 1.0], ["b", 2.0]])
    swapped = res(["key", "val"], [["a", 2.0], ["b", 1.0]])
    m = match_tables(truth, swapped, Compare(keys=["k"], values=["v"]))
    assert not m.ok


def test_value_match_failure_names_columns():
    truth = Table(columns=["k", "v"], rows=[["a", 1.0]])
    m = match_tables(truth, res(["k", "other"], [["a", 9.0]]), Compare(keys=["k"], values=["v"]))
    assert not m.ok
    assert "'v'" in m.reason
    assert m.columns == {}


def test_value_match_does_not_reuse_a_name_matched_column():
    truth = Table(columns=["v", "w"], rows=[["a", "a"]])
    m = match_tables(truth, res(["v"], [["a"]]), Compare(keys=["v", "w"]))
    assert not m.ok


def test_iso_month_equals_first_of_month():
    truth = Table(columns=["month", "rev"], rows=[[dt.date(2025, 1, 1), 1.0], ["2025-02-01T00:00:00", 2.0]])
    result = res(["month", "rev"], [["2025-01", 1.0], ["2025-02", 2.0]])
    assert match_tables(truth, result, Compare(keys=["month"], values=["rev"])).ok
    assert not match_tables(truth, res(["month", "rev"], [["2025-01", 1.0], ["2025-03", 2.0]]), Compare()).ok
