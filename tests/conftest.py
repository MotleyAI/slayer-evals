import pytest

import slayer_evals.agents.claude as claude_module
from slayer_evals.dataset import DEFAULT_SEED, BuiltDataset, build_dataset


@pytest.fixture(autouse=True)
def short_server_settle(request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch) -> None:
    """Scripted clients report their final MCP status at once; only live sessions need the full settle time."""
    if request.node.get_closest_marker("integration") is None:
        monkeypatch.setattr(claude_module, "SERVER_SETTLE_S", 0.5)


@pytest.fixture(scope="session")
def built(tmp_path_factory: pytest.TempPathFactory) -> BuiltDataset:
    """The dataset and store template built once with the default seed."""
    return build_dataset(tmp_path_factory.mktemp("built"), seed=DEFAULT_SEED)
