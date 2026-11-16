"""The Jaffle Shop dataset: seeded build, store template, memories, business rules text, build layout."""

import datetime as dt
import hashlib
import json
import os
import random
import re
import shutil
import sqlite3
import sys
import uuid
from pathlib import Path
from typing import Any

import duckdb
import numpy as np
import pytest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.types import CallToolResult, TextContent
from slayer.storage.yaml_storage import YAMLStorage

import slayer_evals.dataset.store as store_module
from slayer_evals.agents import slayer_server_env
from slayer_evals.core import DATASET_SPECS, DATASETS
from slayer_evals.dataset import (
    STORE_DIR,
    BuiltDataset,
    build_datasets,
    build_jaffle_database,
    jaffle_rules,
    load_built,
    load_datasets,
)
from tests.helpers import REPO
from tests.test_dataset import table_hash

SLAYER = str(Path(sys.executable).parent / "slayer")
TABLES = ("customers", "stores", "products", "orders", "items", "supplies", "tweets")
HASHES = REPO / "tests" / "fixtures" / "jaffle_table_hashes.json"
MONEY_COLUMNS = (
    ("orders", "subtotal"),
    ("orders", "tax_paid"),
    ("orders", "order_total"),
    ("products", "price"),
    ("supplies", "cost"),
)
INTEGER_TYPES = {"TINYINT", "SMALLINT", "INTEGER", "BIGINT", "HUGEINT", "UTINYINT", "USMALLINT", "UINTEGER", "UBIGINT"}
STORES = {
    "Philadelphia": dt.date(2022, 10, 31),
    "Brooklyn": dt.date(2023, 5, 11),
    "Chicago": dt.date(2024, 6, 27),
    "San Francisco": dt.date(2024, 7, 7),
    "New Orleans": dt.date(2025, 5, 8),
    "Los Angeles": dt.date(2025, 11, 11),
}
MODELS = {"customers", "stores", "products", "orders", "items", "supplies", "tweets"}
# Per model of `MotleyAI/my_model_repo` (commit 2221871): (saved measures, join targets).
MODEL_SHAPES: dict[str, tuple[set[str], set[str]]] = {
    "customers": ({"customer_count"}, set()),
    "items": ({"units_sold", "line_sales"}, {"orders", "products"}),
    "orders": (
        {
            "total_revenue",
            "net_sales",
            "tax_collected",
            "order_count",
            "unique_customers",
            "avg_order_value",
            "effective_tax_rate",
            "sales_weighted_aov",
        },
        {"customers", "stores"},
    ),
    "products": ({"product_count", "avg_price"}, set()),
    "stores": ({"store_count"}, set()),
    "supplies": ({"total_supply_cost", "avg_unit_cost"}, {"products"}),
    "tweets": ({"tweet_count"}, {"customers"}),
}
# Dates, years, percentages, dollar amounts and ordinals: the figures a rule must keep.
FIGURE = re.compile(r"\d{4}-\d{2}-\d{2}|[+-]?\d+(?:\.\d+)?%|\$\d+(?:\.\d+)?|\b(?:19|20)\d{2}\b|\b\d+(?:st|nd|rd|th)\b")
# Per memory, as `MotleyAI/my_model_repo` (commit 2221871) holds it and the pinned SLayer links it:
# (description, sha256 of the stripped learning text, linked entities).
MEMORIES: dict[str, tuple[str, str, set[str]]] = {
    "jaffle-data-coverage": (
        "Partial periods: 2022 and the current month/year are incomplete; compare YTD like-for-like",
        "fe99b64a2c77220d7aa0bef9296d5e3d88b90572543e92bd9b213da0482d6eb1",
        {"demo_database.orders.ordered_at", "demo_database.stores.opened_at", "demo_database.stores.name"},
    ),
    "jaffle-money-in-cents": (
        "Money columns are integer cents; use the dollars aggregation / dollar measures.",
        "986ebda567095d84db25df0de647092c3992ebb6686abdfbca3a318cda060a6a",
        {
            "demo_database.orders.order_total",
            "demo_database.orders.subtotal",
            "demo_database.orders.tax_paid",
            "demo_database.products.price",
            "demo_database.supplies.cost",
        },
    ),
    "jaffle-monthly-store-revenue": (
        "Example query: monthly pre-tax net sales by store",
        "6148619ecde923038fbfd5cf5748d5b3c86e617df3d14a07431e482f6b930472",
        {
            "demo_database.orders",
            "demo_database.stores.name",
            "demo_database.orders.ordered_at",
            "demo_database.orders.net_sales",
        },
    ),
    "jaffle-new-customers": (
        "Definition and recipe: new vs returning customers in a period",
        "f6876999da9e816486f848bc12f4560363ecd0abcb3db7a0e2c941d62092a7fe",
        {
            "demo_database.orders.customer",
            "demo_database.orders.ordered_at",
            "demo_database.orders.unique_customers",
            "demo_database.customers",
        },
    ),
    "jaffle-product-margin": (
        "Unit COGS and gross margin per product come from supplies (bill of materials per sku)",
        "351fc9cdfd77dcb335968d6ac0afaff64bcb72dbd9e34faa70322df1d789e885",
        {
            "demo_database.supplies",
            "demo_database.supplies.sku",
            "demo_database.products.name",
            "demo_database.products.price",
            "demo_database.supplies.total_supply_cost",
        },
    ),
    "jaffle-revenue-definition": (
        '"Revenue", "sales" and "AOV" mean pre-tax (net_sales) unless the user asks for gross',
        "920ff719f57cb8a4d56b6ae7adc8a479b876fed6b46cdee82bdc66bf16941be9",
        {
            "demo_database.orders",
            "demo_database.stores.name",
            "demo_database.orders.net_sales",
            "demo_database.orders.order_count",
        },
    ),
    "jaffle-sales-by-product": (
        "Sales by product/type: use items.line_sales, never products.price:sum from items",
        "9c244cd30cff8726321e2074781d449cf7851ff6d763e8f49210653cda3516ab",
        {
            "demo_database.items",
            "demo_database.products.type",
            "demo_database.items.line_sales",
            "demo_database.items.unit_price",
            "demo_database.orders.ordered_at",
        },
    ),
    "jaffle-same-store-growth": (
        "Growth / YoY: always report headline AND same-store growth (stores open for both full periods)",
        "0a26ec429a2446bb5cee61e720820fed59ebb16f36619e36ffe5779f957ea8be",
        {
            "demo_database.orders",
            "demo_database.orders.ordered_at",
            "demo_database.orders.net_sales",
            "demo_database.stores.opened_at",
        },
    ),
    "jaffle-tweets-limits": (
        "tweets are templated and all positive: no sentiment analysis; use for volume and product mentions only",
        "f6aa7be1345ef8cca7e5f29db8d981f8e24089f3a7e755c0777134b0c74daf65",
        {"demo_database.tweets", "demo_database.tweets.content", "demo_database.tweets.tweet_count"},
    ),
}
WITH_QUERY = {
    "jaffle-monthly-store-revenue",
    "jaffle-product-margin",
    "jaffle-revenue-definition",
    "jaffle-sales-by-product",
    "jaffle-same-store-growth",
}
SAVED_MEASURES = (
    "customer_count",
    "units_sold",
    "line_sales",
    "total_revenue",
    "net_sales",
    "tax_collected",
    "order_count",
    "unique_customers",
    "avg_order_value",
    "effective_tax_rate",
    "sales_weighted_aov",
    "product_count",
    "avg_price",
    "store_count",
    "total_supply_cost",
    "avg_unit_cost",
    "tweet_count",
)
QUERY_SETTINGS = (
    "whole_periods_only",
    "partition_by",
    "to_many_handling",
    "time_dimensions",
    "main_time_dimension",
    "source_model",
    "source_queries",
)
AGGREGATION_SUFFIX = re.compile(r"\w:(sum|min|max|avg|count|count_distinct|dollars|weighted_avg)\b")


def scalar(db: Path, sql: str) -> Any:
    con = duckdb.connect(str(db), read_only=True)
    try:
        row = con.execute(sql).fetchone()
        assert row is not None
        return row[0]
    finally:
        con.close()


def text_of(res: CallToolResult) -> str:
    return "\n".join(c.text for c in res.content if isinstance(c, TextContent))


# Generation


class ProcessState:
    """What generating the dataset must leave unchanged in the building process."""

    def __init__(self) -> None:
        self.random = random.getstate()
        self.numpy = np.random.get_state()
        self.uuid4 = uuid.uuid4
        self.cwd = os.getcwd()

    def same_as(self, other: "ProcessState") -> bool:
        return (
            self.random == other.random
            and all(np.array_equal(a, b) for a, b in zip(self.numpy, other.numpy, strict=True))
            and self.uuid4 is other.uuid4
            and self.cwd == other.cwd
        )


@pytest.fixture(scope="module")
def second_build(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, ProcessState, ProcessState]:
    """A second Jaffle database built in this process, with the process state before and after."""
    random.seed(12345)
    np.random.seed(54321)
    before = ProcessState()
    db = build_jaffle_database(tmp_path_factory.mktemp("jaffle-again") / "jaffle.duckdb")
    return db, before, ProcessState()


def test_same_seed_same_jaffle_tables(
    built_jaffle: BuiltDataset, second_build: tuple[Path, ProcessState, ProcessState]
):
    db, _, _ = second_build
    committed = json.loads(HASHES.read_text())
    assert sorted(committed) == sorted(TABLES)
    for table in TABLES:
        first = table_hash(built_jaffle.db_path, table)
        assert first == table_hash(db, table), table
        assert first == committed[table], table


def test_builder_process_left_untouched(second_build: tuple[Path, ProcessState, ProcessState]):
    _, before, after = second_build
    assert after.same_as(before)


def test_jaffle_tables(built_jaffle: BuiltDataset):
    con = duckdb.connect(str(built_jaffle.db_path), read_only=True)
    try:
        tables = {r[0] for r in con.execute("select table_name from information_schema.tables").fetchall()}
        types = {
            (t, c): d
            for t, c, d in con.execute(
                "select table_name, column_name, data_type from information_schema.columns"
            ).fetchall()
        }
    finally:
        con.close()
    assert tables == set(TABLES)
    for table, column in MONEY_COLUMNS:
        assert types[(table, column)] in INTEGER_TYPES, (table, column)
    assert ("orders", "customer") in types
    for table, column in (("orders", "ordered_at"), ("stores", "opened_at"), ("tweets", "tweeted_at")):
        assert types[(table, column)].startswith("TIMESTAMP"), (table, column)


def test_jaffle_stores_and_order_range(built_jaffle: BuiltDataset):
    db = built_jaffle.db_path
    con = duckdb.connect(str(db), read_only=True)
    try:
        stores = dict(con.execute("select name, cast(opened_at as date) from stores").fetchall())
    finally:
        con.close()
    assert stores == STORES
    assert 1_100_000 <= scalar(db, "select count(*) from orders") <= 1_250_000
    assert scalar(db, "select cast(min(ordered_at) as date) from orders") == dt.date(2022, 10, 31)
    assert scalar(db, "select cast(max(ordered_at) as date) from orders") == dt.date(2026, 10, 29)


# Store template


def test_jaffle_layout(built_jaffle: BuiltDataset):
    assert built_jaffle.db_path == built_jaffle.dir / DATASET_SPECS["jaffle"].db_file
    assert built_jaffle.store_dir == built_jaffle.dir / STORE_DIR
    assert load_built(built_jaffle.dir, dataset="jaffle") == built_jaffle


async def test_jaffle_datasource_and_models(built_jaffle: BuiltDataset):
    storage = YAMLStorage(base_dir=str(built_jaffle.store_dir))
    assert await storage.list_datasources() == ["demo_database"]
    ds = await storage.get_datasource("demo_database")
    assert ds is not None
    assert ds.type == "duckdb"
    assert ds.database == DATASET_SPECS["jaffle"].db_file
    assert set(await storage.list_models(data_source="demo_database")) == MODELS
    for name, (measures, joins) in MODEL_SHAPES.items():
        model = await storage.get_model(name, data_source="demo_database")
        assert model is not None, name
        assert {m.name for m in model.measures} == measures, name
        assert {j.target_model for j in model.joins} == joins, name


def test_jaffle_models_carry_no_sampled_values(built_jaffle: BuiltDataset):
    for path in (built_jaffle.store_dir / "models").rglob("*.yaml"):
        text = path.read_text()
        for key in ("sampled_values", "distinct_count", "sampled:"):
            assert key not in text, (path.name, key)


async def test_memories_carry_their_links(built_jaffle: BuiltDataset):
    storage = YAMLStorage(base_dir=str(built_jaffle.store_dir))
    for memory_id, (description, learning_sha, entities) in MEMORIES.items():
        memory = await storage.get_memory_row(memory_id)
        assert memory is not None, memory_id
        assert memory.description == description, memory_id
        assert hashlib.sha256(memory.learning.strip().encode()).hexdigest() == learning_sha, memory_id
        assert set(memory.entities) == entities, memory_id
        assert (memory.query is not None) == (memory_id in WITH_QUERY), memory_id


async def test_jaffle_help_memories_seeded(built_jaffle: BuiltDataset):
    storage = YAMLStorage(base_dir=str(built_jaffle.store_dir))
    assert await storage.get_memory_row("help.intro") is not None


def test_jaffle_store_has_no_search_index(built_jaffle: BuiltDataset):
    for path in built_jaffle.store_dir.rglob("*.db"):
        con = sqlite3.connect(path)
        try:
            tables = [
                r[0]
                for r in con.execute("select name from sqlite_master where type = 'table'").fetchall()
                if "embedding" in r[0].lower()
            ]
            counts = {t: con.execute(f'select count(*) from "{t}"').fetchone()[0] for t in tables}
        finally:
            con.close()
        assert not any(counts.values()), (path.name, counts)


async def test_jaffle_store_loads_answers_and_searches(built_jaffle: BuiltDataset, tmp_path: Path):
    trial = tmp_path / "trial"
    shutil.copytree(built_jaffle.dir, trial)
    params = StdioServerParameters(
        command=SLAYER,
        args=["mcp", "--storage", str(trial / STORE_DIR)],
        env=slayer_server_env(os.environ),
        cwd=str(trial),
    )
    async with stdio_client(params) as (read, write), ClientSession(read, write) as session:
        await session.initialize()
        assert "demo_database" in text_of(await session.call_tool("list_datasources", {}))
        summary = await session.call_tool("models_summary", {"datasource_name": "demo_database"})
        assert not summary.isError, text_of(summary)
        for model in MODELS:
            assert f"`{model}`" in text_of(summary), model
        res = await session.call_tool(
            "query",
            {
                "query": {"source_model": "orders", "measures": [{"formula": "count(*)", "name": "n"}]},
                "format": "json",
            },
        )
        assert not res.isError, text_of(res)
        payload = json.loads(text_of(res))
        data = payload["data"] if isinstance(payload, dict) else payload
        assert next(iter(data[0].values())) > 1_000_000
        found = await session.call_tool("search", {"question": "revenue pre-tax"})
        assert not found.isError, text_of(found)
        assert "jaffle-revenue-definition" in text_of(found)


# Business rules text


def rule_sections(text: str) -> list[str]:
    return re.findall(r"^## (\S+)\s*$", text, re.MULTILINE)


def test_one_rules_section_per_memory():
    assert rule_sections(jaffle_rules()) == sorted(MEMORIES)


def test_every_rules_section_has_a_body():
    bodies = re.split(r"^## \S+\s*$", jaffle_rules(), flags=re.MULTILINE)[1:]
    assert len(bodies) == len(MEMORIES)
    assert all(b.strip() for b in bodies)


def rule_bodies(text: str) -> dict[str, str]:
    return dict(zip(rule_sections(text), re.split(r"^## \S+\s*$", text, flags=re.MULTILINE)[1:], strict=True))


async def test_rules_keep_each_memorys_figures(built_jaffle: BuiltDataset):
    storage = YAMLStorage(base_dir=str(built_jaffle.store_dir))
    bodies = rule_bodies(jaffle_rules())
    missing = []
    for memory_id in MEMORIES:
        memory = await storage.get_memory_row(memory_id)
        assert memory is not None, memory_id
        missing += [f"{memory_id}: {f}" for f in FIGURE.findall(memory.learning) if f not in bodies[memory_id]]
    assert missing == []


def test_rules_name_no_slayer_vocabulary():
    text = jaffle_rules()
    found = [w for w in (*SAVED_MEASURES, *QUERY_SETTINGS) if re.search(rf"\b{w}\b", text)]
    found += AGGREGATION_SUFFIX.findall(text)
    assert found == []


def test_rules_mention_no_slayer():
    assert "slayer" not in jaffle_rules().lower()


# Build layout


def test_build_layout(tmp_path: Path, built_jaffle: BuiltDataset, monkeypatch: pytest.MonkeyPatch):
    def reuse_jaffle(path: Path, seed: int | None = None) -> Path:
        shutil.copy2(built_jaffle.db_path, path)
        return path

    monkeypatch.setattr(store_module, "build_jaffle_database", reuse_jaffle)
    built = build_datasets(tmp_path)
    assert set(built) == set(DATASETS)
    for dataset in DATASETS:
        assert built[dataset].dir == tmp_path / dataset
        assert built[dataset].db_path == tmp_path / dataset / DATASET_SPECS[dataset].db_file
        assert built[dataset].db_path.is_file()
        assert (tmp_path / dataset / STORE_DIR).is_dir()
    assert load_datasets(tmp_path, DATASETS) == built


def test_build_only_the_named_datasets(tmp_path: Path):
    built = build_datasets(tmp_path, ["bench"])
    assert set(built) == {"bench"}
    assert not (tmp_path / "jaffle").exists()


def test_load_datasets_names_every_missing_one(tmp_path: Path):
    with pytest.raises(ValueError) as exc:
        load_datasets(tmp_path, ["bench", "jaffle"])
    assert "bench" in str(exc.value)
    assert "jaffle" in str(exc.value)


def test_load_datasets_takes_only_what_it_needs(tmp_path: Path, built: BuiltDataset):
    shutil.copytree(built.dir, tmp_path / "bench")
    assert set(load_datasets(tmp_path, ["bench"])) == {"bench"}
    with pytest.raises(ValueError, match="jaffle"):
        load_datasets(tmp_path, ["bench", "jaffle"])
