"""The SLayer store template an agent starts from."""

import asyncio
import datetime as dt
from pathlib import Path

import yaml
from pydantic import BaseModel
from slayer.core.granularity import CustomGranularity
from slayer.core.models import DatasourceConfig, SlayerModel
from slayer.engine.query_engine import SlayerQueryEngine
from slayer.memories.help_seed import seed_help_memories
from slayer.storage.yaml_storage import YAMLStorage

from slayer_evals.dataset.generator import DEFAULT_SEED, build_database

DATASOURCE = "bench"
DB_FILE = "bench.duckdb"
STORE_DIR = "store"
MODELS_DIR = Path(__file__).resolve().parent / "models"
GRANULARITIES = [
    CustomGranularity(name="fiscal_year", base="month", multiple=12, origin=dt.datetime(2023, 4, 1)),  # noqa: DTZ001 - SLayer origins are naive
    CustomGranularity(name="quarter_hour", base="minute", multiple=15),
]


class BuiltDataset(BaseModel):
    dir: Path
    db_path: Path
    store_dir: Path


def _datasource(database: str) -> DatasourceConfig:
    return DatasourceConfig(name=DATASOURCE, type="duckdb", database=database, granularities=GRANULARITIES)


async def _fill_store(store_dir: Path, db_path: Path) -> None:
    storage = YAMLStorage(base_dir=str(store_dir))
    # Query-backed models validate by dry-run, so build against the absolute path, then make it trial-relative.
    await storage.save_datasource(_datasource(str(db_path.resolve())))
    engine = SlayerQueryEngine(storage=storage)
    try:
        docs = [yaml.safe_load(f.read_text()) for f in sorted(MODELS_DIR.glob("*.yaml"))]
        for doc in sorted(docs, key=lambda d: bool(d.get("source_queries"))):
            await engine.save_model(SlayerModel.model_validate({"data_source": DATASOURCE, **doc}))
    finally:
        await engine.aclose()
    await storage.save_datasource(_datasource(DB_FILE))
    await seed_help_memories(storage=storage)


def build_dataset(out_dir: Path, seed: int = DEFAULT_SEED) -> BuiltDataset:
    """Build the database and the store template under `out_dir`."""
    out_dir.mkdir(parents=True, exist_ok=True)
    db_path = build_database(out_dir / DB_FILE, seed=seed)
    store_dir = out_dir / STORE_DIR
    asyncio.run(_fill_store(store_dir, db_path))
    return BuiltDataset(dir=out_dir, db_path=db_path, store_dir=store_dir)


def load_built(out_dir: Path) -> BuiltDataset:
    """A dataset previously built into `out_dir`."""
    built = BuiltDataset(dir=out_dir, db_path=out_dir / DB_FILE, store_dir=out_dir / STORE_DIR)
    if not built.db_path.is_file() or not built.store_dir.is_dir():
        raise ValueError(f"{out_dir} is not a built dataset (run `slayer-evals build --out {out_dir}`)")
    return built
