"""The SLayer store templates an agent starts from, one per dataset, and the build layout `<root>/<dataset>/`."""

import asyncio
import datetime as dt
import shutil
from collections.abc import Iterable
from pathlib import Path

import yaml
from pydantic import BaseModel
from slayer.core.granularity import CustomGranularity
from slayer.core.models import DatasourceConfig, SlayerModel
from slayer.engine.query_engine import SlayerQueryEngine
from slayer.memories.help_seed import seed_help_memories
from slayer.memories.service import MemoryService
from slayer.storage.yaml_storage import YAMLStorage

from slayer_evals.core import DATASET_SPECS, DATASETS, Dataset
from slayer_evals.dataset.generator import DEFAULT_SEED, build_database
from slayer_evals.dataset.jaffle import build_jaffle_database

DATASOURCE = DATASET_SPECS["bench"].datasource
DB_FILE = DATASET_SPECS["bench"].db_file
STORE_DIR = "store"
MODELS_DIR = Path(__file__).resolve().parent / "models"
JAFFLE_DIR = Path(__file__).resolve().parent / "jaffle_store"
JAFFLE_RULES = Path(__file__).resolve().parent / "jaffle_rules.md"
GRANULARITIES = [
    CustomGranularity(name="fiscal_year", base="month", multiple=12, origin=dt.datetime(2023, 4, 1)),  # noqa: DTZ001 - SLayer origins are naive
    CustomGranularity(name="quarter_hour", base="minute", multiple=15),
]


class BuiltDataset(BaseModel):
    dir: Path
    db_path: Path
    store_dir: Path


def _datasource(dataset: Dataset, database: str) -> DatasourceConfig:
    name = DATASET_SPECS[dataset].datasource
    if dataset == "bench":
        return DatasourceConfig(name=name, type="duckdb", database=database, granularities=GRANULARITIES)
    return DatasourceConfig(name=name, type="duckdb", database=database)


def _model_docs(models_dir: Path) -> list[dict]:
    docs = [yaml.safe_load(f.read_text()) for f in sorted(models_dir.glob("*.yaml"))]
    return sorted(docs, key=lambda d: bool(d.get("source_queries")))


async def _save_memories(storage: YAMLStorage, memories_dir: Path) -> None:
    """Save each memory with its query (links derived from it) or else its authored entities."""
    service = MemoryService(storage)
    for path in sorted(memories_dir.glob("*.md")):
        _, front, body = path.read_text().split("---", 2)
        meta = yaml.safe_load(front)
        query = meta.get("query")
        links = {k: v for k, v in query.items() if v is not None} if query else meta["entities"]
        await service.save_memory(
            id=path.stem, learning=body.strip(), description=meta["description"], linked_entities=links
        )


async def _fill_store(dataset: Dataset, store_dir: Path, db_path: Path) -> None:
    storage = YAMLStorage(base_dir=str(store_dir))
    # Query-backed models validate by dry-run, so build against the absolute path, then make it trial-relative.
    await storage.save_datasource(_datasource(dataset, str(db_path.resolve())))
    models_dir = MODELS_DIR if dataset == "bench" else JAFFLE_DIR / "models"
    datasource = DATASET_SPECS[dataset].datasource
    engine = SlayerQueryEngine(storage=storage)
    try:
        for doc in _model_docs(models_dir):
            await engine.save_model(SlayerModel.model_validate({**doc, "data_source": datasource}))
    finally:
        await engine.aclose()
    if dataset == "jaffle":
        await _save_memories(storage, JAFFLE_DIR / "memories")
    await storage.save_datasource(_datasource(dataset, DATASET_SPECS[dataset].db_file))
    await seed_help_memories(storage=storage)


def _build_database(dataset: Dataset, path: Path, seed: int | None) -> Path:
    if dataset == "bench":
        return build_database(path, seed=DEFAULT_SEED if seed is None else seed)
    return build_jaffle_database(path, seed=seed)


def build_dataset(out_dir: Path, seed: int | None = None, dataset: Dataset = "bench") -> BuiltDataset:
    """Build one dataset's database and store template under `out_dir` (seed: the dataset's default if None)."""
    out_dir.mkdir(parents=True, exist_ok=True)
    db_path = _build_database(dataset, out_dir / DATASET_SPECS[dataset].db_file, seed)
    store_dir = out_dir / STORE_DIR
    if store_dir.exists():
        shutil.rmtree(store_dir)
    asyncio.run(_fill_store(dataset, store_dir, db_path))
    return BuiltDataset(dir=out_dir, db_path=db_path, store_dir=store_dir)


def build_datasets(
    root: Path, datasets: Iterable[Dataset] = DATASETS, seed: int | None = None
) -> dict[Dataset, BuiltDataset]:
    """Build each named dataset into `<root>/<dataset>/`."""
    return {d: build_dataset(root / d, seed=seed, dataset=d) for d in _in_order(datasets)}


def _in_order(datasets: Iterable[Dataset]) -> list[Dataset]:
    named = set(datasets)
    return [d for d in DATASETS if d in named]


def _built(out_dir: Path, dataset: Dataset) -> BuiltDataset:
    return BuiltDataset(dir=out_dir, db_path=out_dir / DATASET_SPECS[dataset].db_file, store_dir=out_dir / STORE_DIR)


def _complete(built: BuiltDataset) -> bool:
    return built.db_path.is_file() and built.store_dir.is_dir()


def load_built(out_dir: Path, dataset: Dataset = "bench") -> BuiltDataset:
    """One dataset previously built into `out_dir`."""
    built = _built(out_dir, dataset)
    if not _complete(built):
        raise ValueError(f"{out_dir} is not a built dataset ({dataset}; run `slayer-evals build`)")
    return built


def load_datasets(root: Path, datasets: Iterable[Dataset]) -> dict[Dataset, BuiltDataset]:
    """The named datasets of the build root `root`; fails naming every one that is missing or incomplete."""
    built: dict[Dataset, BuiltDataset] = {d: _built(root / d, d) for d in _in_order(datasets)}
    missing = [d for d, b in built.items() if not _complete(b)]
    if missing:
        raise ValueError(
            f"{root} lacks the built dataset(s) {', '.join(missing)} "
            f"(expected {', '.join(f'{d}/' for d in missing)}; run `slayer-evals build --out {root}`)"
        )
    return built


def jaffle_rules() -> str:
    """The Jaffle business rules in plain table and column terms, for the raw-SQL profile."""
    return JAFFLE_RULES.read_text()
