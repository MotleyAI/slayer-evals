import pytest

from slayer_evals.dataset import DEFAULT_SEED, BuiltDataset, build_dataset


@pytest.fixture(scope="session")
def built(tmp_path_factory: pytest.TempPathFactory) -> BuiltDataset:
    """The dataset and store template built once with the default seed."""
    return build_dataset(tmp_path_factory.mktemp("built"), seed=DEFAULT_SEED)
