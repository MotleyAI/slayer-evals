"""Datasets: which database and SLayer datasource a task runs on, as one table every node reads."""

from typing import Literal

from pydantic import BaseModel

Dataset = Literal["bench", "jaffle"]


class DatasetSpec(BaseModel):
    """The datasource name in a dataset's store and its database file name."""

    datasource: str
    db_file: str


DATASET_SPECS: dict[Dataset, DatasetSpec] = {
    "bench": DatasetSpec(datasource="bench", db_file="bench.duckdb"),
    "jaffle": DatasetSpec(datasource="demo_database", db_file="jaffle.duckdb"),
}
DATASETS: tuple[Dataset, ...] = tuple(DATASET_SPECS)
