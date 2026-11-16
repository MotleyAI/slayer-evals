"""The committed Jaffle sub-suite: Yann's 24 questions, their answer shapes and truth on the Jaffle dataset."""

import re

import pytest
import yaml

from slayer_evals.core import Table, Task
from slayer_evals.dataset import BuiltDataset
from slayer_evals.tasks import compute_truths, load_tasks
from tests.helpers import REPO

TASKS_DIR = REPO / "tasks"
QUESTIONS = yaml.safe_load((REPO / "tests" / "fixtures" / "jaffle_questions.yaml").read_text())
# id → (truth rows, compare keys, compare values), as design.md's task-shape table fixes them.
SHAPES: dict[str, tuple[int, list[str], list[str]]] = {
    "j-q01-stores": (6, ["store"], ["opened_on"]),
    "j-q02-orders-2025": (1, [], ["orders"]),
    "j-q03-revenue-by-store-2025": (6, ["store"], ["revenue"]),
    "j-q04-monthly-orders-2026": (10, ["month"], ["orders"]),
    "j-q05-top-products-2025": (5, ["product"], ["type", "units_sold"]),
    "j-q06-type-share-2025": (2, ["type"], ["sales", "share"]),
    "j-q07-aov-by-store": (6, ["store"], ["aov"]),
    "j-q08-tax-rate-check": (6, ["store"], ["stated_rate", "collected_rate"]),
    "j-q09-store-growth-2024-2025": (4, ["store"], ["sales_2024", "sales_2025", "growth"]),
    "j-q10-new-customers-by-year": (5, ["year"], ["new_customers"]),
    "j-q11-ytd-growth-same-store": (
        1,
        [],
        ["ytd_2025", "ytd_2026", "headline_growth", "ss_2025", "ss_2026", "same_store_growth"],
    ),
    "j-q12-best-unit-margin": (10, ["product"], ["unit_margin", "margin_pct"]),
    "j-c01-peak-weekday-hour": (1, [], ["weekday", "hour", "net_sales", "share"]),
    "j-c02-order-value-bands": (4, ["band"], ["orders", "net_sales", "share_of_sales"]),
    "j-c03-basket-mix": (3, ["mix"], ["orders", "share"]),
    "j-c04-ltv-by-first-store": (6, ["store"], ["customers", "avg_lifetime_spend"]),
    "j-c05-median-orders-per-customer": (6, ["store"], ["customers", "median_orders"]),
    "j-c06-top-decile-share": (1, [], ["top_decile_share", "top_decile_customers"]),
    "j-c07-best-month-vs-avg": (6, ["store"], ["best_month", "sales", "avg_month", "above_avg"]),
    "j-c08-growth-streak": (1, [], ["streak_months", "streak_start", "streak_end"]),
    "j-c09-brooklyn-cogs-margin": (1, [], ["cogs", "product_sales", "gross_margin"]),
    "j-c10-top-supply-component": (1, [], ["supply", "total_cost"]),
    "j-c11-tweeters-aov": (2, ["segment"], ["customers", "orders", "net_aov"]),
    "j-c12-jaffle-beverage-attach": (6, ["store"], ["jaffle_orders", "attach_rate"]),
}
# Wording that would state a business rule in the answer-shape sentence.
RULE_HINTS = (
    "pre-tax",
    "pretax",
    "before tax",
    "excluding tax",
    "excl. tax",
    "net of tax",
    "tax-inclusive",
    "cents",
    "cut-off",
    "cutoff",
    "last order",
    "first order",
    "first-ever",
    "same-store",
    "same store",
    "open for both",
    "subtotal",
    "order_total",
)


@pytest.fixture(scope="module")
def jaffle() -> dict[str, Task]:
    return {t.id: t for t in load_tasks(TASKS_DIR) if t.dataset == "jaffle"}


def question_of(task_id: str) -> str:
    return QUESTIONS[task_id.split("-")[1]]


def test_fixture_holds_the_24_questions():
    assert list(QUESTIONS) == [f"q{i:02d}" for i in range(1, 13)] + [f"c{i:02d}" for i in range(1, 13)]


def test_all_24_questions_present(jaffle: dict[str, Task]):
    assert sorted(jaffle) == sorted(SHAPES)
    assert sorted(t.split("-")[1] for t in jaffle) == sorted(QUESTIONS)


def test_ids_follow_the_question_ids(jaffle: dict[str, Task]):
    for tid in jaffle:
        assert re.fullmatch(r"j-[qc]\d{2}-[a-z0-9-]+", tid), tid


def test_jaffle_tasks_are_their_own_suite(jaffle: dict[str, Task]):
    for t in jaffle.values():
        assert t.suite == "jaffle", t.id
        assert t.covers == [], t.id
        assert t.naive_sql is None, t.id
        assert t.expect == "match", t.id


def test_jaffle_task_files_live_under_tasks_jaffle():
    files = sorted((TASKS_DIR / "jaffle").rglob("*.yaml"))
    assert len(files) == len(SHAPES)


def test_prompt_starts_with_the_verbatim_question(jaffle: dict[str, Task]):
    for tid, t in jaffle.items():
        assert t.prompt.startswith(question_of(tid)), tid


def test_prompt_adds_an_answer_shape_sentence(jaffle: dict[str, Task]):
    for tid, t in jaffle.items():
        assert t.prompt[len(question_of(tid)) :].strip(), tid


def test_shape_sentence_states_no_business_rule(jaffle: dict[str, Task]):
    problems = []
    for tid, t in jaffle.items():
        shape = t.prompt[len(question_of(tid)) :].lower()
        problems += [f"{tid}: {hint!r}" for hint in RULE_HINTS if hint in shape]
    assert problems == []


def test_compare_follows_the_task_shape(jaffle: dict[str, Task]):
    for tid, (_, keys, values) in SHAPES.items():
        assert (jaffle[tid].compare.keys, jaffle[tid].compare.values) == (keys, values), tid


@pytest.fixture(scope="module")
def truths(jaffle: dict[str, Task], built_jaffle: BuiltDataset) -> dict[str, Table]:
    return compute_truths(list(jaffle.values()), built_jaffle.db_path)


def shape_sentence(task: Task) -> str:
    return task.prompt[len(question_of(task.id)) :].lower()


def test_truth_has_the_task_shape(truths: dict[str, Table]):
    for tid, (rows, keys, values) in SHAPES.items():
        assert len(truths[tid].rows) == rows, tid
        assert sorted(truths[tid].columns) == sorted(keys + values), tid


def test_decided_shapes_are_stated(jaffle: dict[str, Task]):
    assert "october" in shape_sentence(jaffle["j-q04-monthly-orders-2026"])
    assert "round" in shape_sentence(jaffle["j-c06-top-decile-share"])


def test_peak_weekday_is_a_name(truths: dict[str, Table]):
    truth = truths["j-c01-peak-weekday-hour"]
    (weekday,) = [row[truth.columns.index("weekday")] for row in truth.rows]
    assert isinstance(weekday, str)
    assert weekday.isalpha()


@pytest.mark.parametrize("task_id", ["j-c02-order-value-bands", "j-c03-basket-mix", "j-c11-tweeters-aov"])
def test_fixed_labels_are_in_the_prompt(task_id: str, jaffle: dict[str, Task], truths: dict[str, Table]):
    truth = truths[task_id]
    (key,) = SHAPES[task_id][1]
    labels = [row[truth.columns.index(key)] for row in truth.rows]
    assert all(isinstance(label, str) for label in labels)
    for label in labels:
        assert label in jaffle[task_id].prompt, label
