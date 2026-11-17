"""Table comparison: column resolution, multiset/ordered, tolerance, NULL/NaN, dates, row counts."""

import datetime as dt
import math

import pytest

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


def test_null_as_zero_in_values():
    truth = Table(columns=["month", "rev"], rows=[["2024-08-01", None], ["2024-09-01", 5.0]])
    result = res(["month", "rev"], [["2024-08-01", 0], ["2024-09-01", 5.0]])
    assert not match_tables(truth, result, Compare(keys=["month"], values=["rev"])).ok
    assert match_tables(truth, result, Compare(keys=["month"], values=["rev"], null_as_zero=True)).ok


def test_null_as_zero_both_ways():
    truth = Table(columns=["month", "n"], rows=[["2024-08-01", 0]])
    result = res(["month", "n"], [["2024-08-01", None]])
    assert not match_tables(truth, result, Compare(keys=["month"], values=["n"])).ok
    assert match_tables(truth, result, Compare(keys=["month"], values=["n"], null_as_zero=True)).ok


def test_null_as_zero_leaves_keys_alone():
    truth = Table(columns=["k", "v"], rows=[[None, 1.0]])
    result = res(["k", "v"], [[0, 1.0]])
    assert not match_tables(truth, result, Compare(keys=["k"], values=["v"], null_as_zero=True)).ok


def test_null_as_zero_does_not_equate_other_values():
    truth = Table(columns=["k", "v"], rows=[["a", None]])
    result = res(["k", "v"], [["a", 1.0]])
    assert not match_tables(truth, result, Compare(keys=["k"], values=["v"], null_as_zero=True)).ok


# List-valued cells.

LIST_CMP = Compare(keys=["region"], values=["tags"])


def list_truth(cell: object) -> Table:
    return Table(columns=["region", "tags"], rows=[["North", cell]])


def list_result(cell: object) -> Table:
    return res(["region", "tags"], [["North", cell]])


@pytest.mark.parametrize(
    "cell",
    [
        ["vip", "eu", "vip"],
        ["vip", "eu", None],
        ["eu", "vip"],
        '["vip","eu"]',
        '["eu", "vip", null]',
        "vip, eu",
        "eu,vip",
    ],
)
def test_list_cells_compare_as_sets(cell: object):
    assert match_tables(list_truth(["eu", "vip"]), list_result(cell), LIST_CMP).ok


@pytest.mark.parametrize("cell", [["vip"], ["vip", "eu", "b2b"], None, [], "vip", '["vip"]', "vip, eu, b2b"])
def test_list_cells_with_other_elements_differ(cell: object):
    assert not match_tables(list_truth(["eu", "vip"]), list_result(cell), LIST_CMP).ok


def test_truth_list_repeats_and_nulls_ignored():
    assert match_tables(list_truth(["vip", None, "vip"]), list_result(["vip"]), LIST_CMP).ok


def test_one_element_text_matches_a_one_element_list():
    assert match_tables(list_truth(["vip"]), list_result("vip"), LIST_CMP).ok


def test_null_is_not_an_empty_list():
    assert not match_tables(list_truth([]), list_result(None), LIST_CMP).ok
    assert not match_tables(list_truth(None), list_result([]), LIST_CMP).ok
    assert match_tables(list_truth([]), list_result([]), LIST_CMP).ok
    assert match_tables(list_truth([]), list_result("[]"), LIST_CMP).ok
    assert match_tables(list_truth(None), list_result(None), LIST_CMP).ok


def test_numeric_list_elements_within_tolerance():
    assert match_tables(list_truth([1.5, 2.0]), list_result([2.0000000001, 1.5]), LIST_CMP).ok
    assert not match_tables(list_truth([1.5, 2.0]), list_result([1.5, 2.1]), LIST_CMP).ok
    assert match_tables(list_truth([1, 2]), list_result([2.0, 1.0, 2]), LIST_CMP).ok


def test_numeric_list_text_within_tolerance():
    assert match_tables(list_truth([1.5, 2.0]), list_result("[2.0000000001, 1.5]"), LIST_CMP).ok
    assert match_tables(list_truth([1.5, 2.0]), list_result("2, 1.5"), LIST_CMP).ok
    assert not match_tables(list_truth([1.5, 2.0]), list_result("1.5, 2.1"), LIST_CMP).ok


def test_list_tolerance_follows_the_task():
    loose = LIST_CMP.model_copy(update={"tolerance": 0.1})
    assert match_tables(list_truth([1.5, 2.0]), list_result([1.5, 2.05]), loose).ok


def test_text_outside_list_columns_stays_text():
    cmp = Compare(keys=["region"], values=["label"])
    truth = Table(columns=["region", "label"], rows=[["North", "vip, eu"]])
    assert not match_tables(truth, res(["region", "label"], [["North", ["vip", "eu"]]]), cmp).ok
    assert not match_tables(truth, res(["region", "label"], [["North", "eu, vip"]]), cmp).ok
    assert match_tables(truth, res(["region", "label"], [["North", "vip, eu"]]), cmp).ok


def test_list_column_with_null_cells_reads_text():
    truth = Table(columns=["region", "tags"], rows=[["North", ["vip"]], ["South", None]])
    result = res(["region", "tags"], [["South", None], ["North", "vip"]])
    assert match_tables(truth, result, LIST_CMP).ok


def test_list_key_column_unordered_rows():
    truth = Table(columns=["tags", "n"], rows=[[["a", "b"], 1.0], [["c"], 2.0]])
    result = res(["tags", "n"], [[["c"], 2.0], [["b", "a", "a"], 1.0]])
    assert match_tables(truth, result, Compare(keys=["tags"], values=["n"])).ok


def test_list_column_matched_by_values():
    truth = Table(columns=["region", "tag_set"], rows=[["North", ["eu", "vip"]], ["Arctic", []]])
    result = res(["regions.name", "regions.collected"], [["Arctic", []], ["North", ["vip", "eu"]]])
    m = match_tables(truth, result, Compare(keys=["region"], values=["tag_set"]))
    assert m.ok, m.reason
    assert m.columns == {"region": "regions.name", "tag_set": "regions.collected"}


def test_ordered_rows_with_list_cells():
    truth = Table(columns=["k", "tags"], rows=[["a", ["x", "y"]], ["b", ["z"]]])
    cmp = Compare(keys=["k"], values=["tags"], ordered=True)
    assert match_tables(truth, res(["k", "tags"], [["a", ["y", "x"]], ["b", "z"]]), cmp).ok
    assert not match_tables(truth, res(["k", "tags"], [["b", ["z"]], ["a", ["x", "y"]]]), cmp).ok


def test_second_assignment_tried_when_the_closest_names_fail():
    truth = Table(columns=["k", "a", "b"], rows=[[1, 5.0, 6.0], [2, 6.0, 5.0]])
    result = res(["k", "aa", "bb"], [[1, 6.0, 5.0], [2, 5.0, 6.0]])
    m = match_tables(truth, result, Compare(keys=["k"], values=["a", "b"]))
    assert m.ok, m.reason
    assert m.columns == {"k": "k", "a": "bb", "b": "aa"}


ZERO_OK = Compare(keys=["region"], values=["customers"], extra_zero_rows=True)
REGIONS = Table(columns=["region", "customers"], rows=[[None, 1], ["East", 10], ["North", 6]])


@pytest.mark.parametrize("extra", [["Arctic", 0], ["Arctic", None], [None, 0]], ids=["zero", "null", "null-key"])
def test_extra_zero_row_allowed_when_the_task_says_so(extra: list):
    truth = Table(columns=["region", "customers"], rows=[["East", 10], ["North", 6]])
    result = res(["region", "customers"], [["East", 10], extra, ["North", 6]])
    m = match_tables(truth, result, ZERO_OK)
    assert m.ok, m.reason
    assert not match_tables(truth, result, Compare(keys=["region"], values=["customers"])).ok


def test_extra_zero_row_with_renamed_columns():
    result = res(["region", "customers_vip_and_eu"], [["East", 10], ["North", 6], ["Arctic", 0], [None, 1]])
    m = match_tables(REGIONS, result, ZERO_OK)
    assert m.ok, m.reason
    assert m.columns == {"region": "region", "customers": "customers_vip_and_eu"}


def test_extra_nonzero_row_still_fails():
    result = res(["region", "customers"], [[None, 1], ["East", 10], ["North", 6], ["Arctic", 2]])
    assert not match_tables(REGIONS, result, ZERO_OK).ok


def test_zero_row_cannot_repeat_a_truth_key():
    result = res(["region", "customers"], [[None, 1], ["East", 10], ["North", 6], ["North", 0]])
    assert not match_tables(REGIONS, result, ZERO_OK).ok


def test_missing_row_still_fails_with_extra_zero_rows():
    result = res(["region", "customers"], [["East", 10], ["North", 6], ["Arctic", 0]])
    assert not match_tables(REGIONS, result, ZERO_OK).ok


def test_ordered_match_ignores_the_extra_zero_row():
    cmp = Compare(keys=["region"], values=["customers"], ordered=True, extra_zero_rows=True)
    truth = Table(columns=["region", "customers"], rows=[["East", 10], ["North", 6]])
    assert match_tables(truth, res(["region", "customers"], [["East", 10], ["North", 6], ["Arctic", 0]]), cmp).ok
    assert not match_tables(truth, res(["region", "customers"], [["North", 6], ["East", 10], ["Arctic", 0]]), cmp).ok
