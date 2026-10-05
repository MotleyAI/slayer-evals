"""Store template: datasource, models, saved measures and queries, help memories, manifest."""

import json
import shutil
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from slayer.core.query import SlayerQuery
from slayer.storage.yaml_storage import YAMLStorage

from slayer_evals.core import StoreManifest
from slayer_evals.dataset import DB_FILE, MANIFEST_FILE, STORE_DIR, BuiltDataset

SLAYER = str(Path(sys.executable).parent / "slayer")
MODELS = {"regions", "customers", "orders", "returns", "events", "orders_flat"}


def test_layout(built: BuiltDataset):
    assert built.db_path == built.dir / DB_FILE
    assert built.store_dir == built.dir / STORE_DIR
    on_disk = StoreManifest.model_validate_json((built.dir / MANIFEST_FILE).read_text())
    assert on_disk == built.manifest


async def test_datasource_and_granularities(built: BuiltDataset):
    storage = YAMLStorage(base_dir=str(built.store_dir))
    assert await storage.list_datasources() == ["bench"]
    ds = await storage.get_datasource("bench")
    assert ds is not None and ds.type == "duckdb"
    assert not Path(ds.database).is_absolute()
    grans = {g.name: g for g in ds.granularities}
    assert grans["fiscal_year"].base == "month" and grans["fiscal_year"].multiple == 12
    assert grans["fiscal_year"].origin.month == 4
    assert grans["quarter_hour"].base == "minute" and grans["quarter_hour"].multiple == 15


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


async def test_manifest_matches_store(built: BuiltDataset):
    storage = YAMLStorage(base_dir=str(built.store_dir))
    measures: set[tuple[str, str, str]] = set()
    queries: dict[str, object] = {}
    for name in await storage.list_models(data_source="bench"):
        model = await storage.get_model(name, data_source="bench")
        assert model is not None
        measures |= {(model.name, m.name, m.formula) for m in model.measures}
        if model.source_queries:
            queries[model.name] = [q.model_dump(mode="json", exclude_none=True) for q in model.source_queries]
    m = built.manifest
    assert m.datasource == "bench"
    assert {(s.model, s.name, s.formula) for s in m.measures} == measures
    assert {q.name for q in m.queries} == set(queries)
    for q in m.queries:
        stages = q.query if isinstance(q.query, list) else [q.query]
        normalized = [SlayerQuery.model_validate(s).model_dump(mode="json", exclude_none=True) for s in stages]
        assert normalized == queries[q.name], q.name
    assert set(m.models) >= MODELS | set(queries)
    assert ("orders", "aov") in {(s.model, s.name) for s in m.measures}
    assert "monthly_rev" in {q.name for q in m.queries}


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
        assert "bench" in ds.content[0].text
        summary = await session.call_tool("models_summary", {"datasource_name": "bench"})
        assert not summary.isError
        for model in MODELS:
            assert f"`{model}`" in summary.content[0].text
        res = await session.call_tool(
            "query",
            {
                "query": {"source_model": "orders", "measures": [{"formula": "count(*)", "name": "n"}]},
                "format": "json",
            },
        )
        assert not res.isError, res.content[0].text
        payload = json.loads(res.content[0].text)
        data = payload["data"] if isinstance(payload, dict) else payload
        assert data and next(iter(data[0].values())) > 0
