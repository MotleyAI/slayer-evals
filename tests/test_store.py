"""Store template: datasource, models, saved measures and queries, help memories."""

import json
import shutil
import sys
from pathlib import Path

import pytest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.types import CallToolResult, TextContent
from slayer.storage.yaml_storage import YAMLStorage

from slayer_evals.dataset import DB_FILE, STORE_DIR, BuiltDataset, build_dataset, load_built

SLAYER = str(Path(sys.executable).parent / "slayer")
MODELS = {
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
}


def text_of(res: CallToolResult) -> str:
    content = res.content[0]
    assert isinstance(content, TextContent)
    return content.text


def test_layout(built: BuiltDataset):
    assert built.db_path == built.dir / DB_FILE
    assert built.store_dir == built.dir / STORE_DIR
    assert load_built(built.dir) == built


async def test_datasource_and_granularities(built: BuiltDataset):
    storage = YAMLStorage(base_dir=str(built.store_dir))
    assert await storage.list_datasources() == ["bench"]
    ds = await storage.get_datasource("bench")
    assert ds is not None
    assert ds.type == "duckdb"
    assert ds.database is not None
    assert not Path(ds.database).is_absolute()
    grans = {g.name: g for g in ds.granularities}
    assert grans["fiscal_year"].base == "month"
    assert grans["fiscal_year"].multiple == 12
    origin = grans["fiscal_year"].origin
    assert origin is not None
    assert origin.month == 4
    assert grans["quarter_hour"].base == "minute"
    assert grans["quarter_hour"].multiple == 15


async def test_models_and_joins(built: BuiltDataset):
    storage = YAMLStorage(base_dir=str(built.store_dir))
    names = set(await storage.list_models(data_source="bench"))
    assert MODELS <= names
    orders = await storage.get_model("orders", data_source="bench")
    assert orders is not None
    assert "customers" in {j.target_model for j in orders.joins}
    customers = await storage.get_model("customers", data_source="bench")
    assert customers is not None
    assert "regions" in {j.target_model for j in customers.joins}
    returns = await storage.get_model("returns", data_source="bench")
    assert returns is not None
    assert "customers" in {j.target_model for j in returns.joins}


async def test_new_models_join_along_their_keys(built: BuiltDataset):
    storage = YAMLStorage(base_dir=str(built.store_dir))

    async def targets(name: str) -> set[str]:
        model = await storage.get_model(name, data_source="bench")
        assert model is not None, name
        return {j.target_model for j in model.joins}

    assert {"orders", "products"} <= await targets("order_items")
    assert {"campaigns", "customers"} <= await targets("campaign_members")
    assert "regions" in await targets("cities")


async def test_customers_join_cities_on_city_and_region(built: BuiltDataset):
    storage = YAMLStorage(base_dir=str(built.store_dir))
    customers = await storage.get_model("customers", data_source="bench")
    assert customers is not None
    (join,) = [j for j in customers.joins if j.target_model == "cities"]
    assert sorted(map(tuple, join.join_pairs)) == [("city", "city"), ("region_id", "region_id")]
    assert join.cardinality is not None
    assert join.cardinality.value == "many_to_one"


async def test_every_join_declares_its_cardinality(built: BuiltDataset):
    storage = YAMLStorage(base_dir=str(built.store_dir))
    for name in sorted(MODELS):
        model = await storage.get_model(name, data_source="bench")
        assert model is not None, name
        for j in model.joins:
            assert j.cardinality is not None, (name, j.target_model)


async def test_saved_measure_and_query(built: BuiltDataset):
    storage = YAMLStorage(base_dir=str(built.store_dir))
    orders = await storage.get_model("orders", data_source="bench")
    assert orders is not None
    assert {m.name: m.formula for m in orders.measures}["aov"] == "sum(amount) / count(*)"
    monthly = await storage.get_model("monthly_rev", data_source="bench")
    assert monthly is not None
    assert monthly.source_queries


async def test_help_memories_seeded(built: BuiltDataset):
    storage = YAMLStorage(base_dir=str(built.store_dir))
    memory = await storage.get_memory_row("help.intro")
    assert memory is not None


async def test_store_copy_loads_and_answers(built: BuiltDataset, tmp_path: Path):
    trial = tmp_path / "trial"
    shutil.copytree(built.dir, trial)
    params = StdioServerParameters(command=SLAYER, args=["mcp", "--storage", str(trial / STORE_DIR)], cwd=str(trial))
    async with stdio_client(params) as (read, write), ClientSession(read, write) as session:
        await session.initialize()
        ds = await session.call_tool("list_datasources", {})
        assert "bench" in text_of(ds)
        summary = await session.call_tool("models_summary", {"datasource_name": "bench"})
        assert not summary.isError
        for model in MODELS:
            assert f"`{model}`" in text_of(summary)
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
        assert data
        assert next(iter(data[0].values())) > 0


def test_rebuild_drops_stale_store_files(tmp_path: Path):
    stale = tmp_path / STORE_DIR / "stale_model.yaml"
    stale.parent.mkdir()
    stale.write_text("name: stale\n")
    built = build_dataset(tmp_path)
    assert not stale.exists()
    assert (built.store_dir / "datasources").is_dir()


def test_load_built_rejects_a_non_dataset(tmp_path: Path):
    with pytest.raises(ValueError, match="not a built dataset"):
        load_built(tmp_path)
