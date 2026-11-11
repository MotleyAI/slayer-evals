"""The profile table, profile-scoped xfail, and the Motley fields of the trial environment and run metadata."""

import datetime as dt
import json
from pathlib import Path

import pytest
from pydantic import BaseModel, ValidationError

from slayer_evals.core import (
    DEFAULT_PROFILES,
    PROFILE_SPECS,
    PROFILES,
    AgentInput,
    ProfileSpec,
    RunMetadata,
    TrialEnv,
    XFail,
)
from slayer_evals.tasks import TaskFormatError, load_task
from tests.helpers import REPO, make_task, write_task

MOTLEY_URL = "http://localhost:8000/api/v1/mcp/"
METADATA = {
    "slayer_version": "1.0.2",
    "sdk_version": "0.2.163",
    "models": ["claude-opus-5-5"],
    "profiles": ["slayer", "motley"],
    "mode": "repeat",
    "n": 1,
    "max_turns": 60,
    "timeout_s": 900.0,
    "auth_mode": "subscription",
    "started_at": "2026-11-11T14:30:00Z",
}


def test_every_profile_has_a_spec():
    assert set(PROFILES) == {"slayer", "slayer+python", "sql+python", "motley", "motley+python"}
    assert len(PROFILES) == 5
    assert tuple(PROFILE_SPECS) == tuple(PROFILES)
    assert all(isinstance(s, ProfileSpec) and isinstance(s, BaseModel) for s in PROFILE_SPECS.values())


@pytest.mark.parametrize(
    ("profile", "surface", "python"),
    [
        ("slayer", "slayer", False),
        ("slayer+python", "slayer", True),
        ("sql+python", "sql", True),
        ("motley", "motley", False),
        ("motley+python", "motley", True),
    ],
)
def test_profile_spec(profile: str, surface: str, python: bool):
    spec = PROFILE_SPECS[profile]  # pyright: ignore[reportArgumentType]
    assert (spec.surface, spec.python) == (surface, python)


def test_default_profiles_are_the_three():
    assert tuple(DEFAULT_PROFILES) == ("slayer", "slayer+python", "sql+python")


def test_profile_spec_rejects_unknown_surface():
    with pytest.raises(ValidationError):
        ProfileSpec(surface="cube", python=False)  # pyright: ignore[reportArgumentType]


def env(tmp: Path, **kw) -> TrialEnv:
    return TrialEnv(
        trial_dir=tmp,
        store_dir=tmp / "store",
        db_path=tmp / "bench.duckdb",
        slayer_command=["slayer"],
        transcript_path=tmp / "transcript.jsonl",
        **kw,
    )


def test_trial_env_motley_fields_default_to_none(tmp_path: Path):
    e = env(tmp_path)
    assert e.motley_url is None
    assert e.motley_user_id is None


def test_motley_trial_env_round_trip(tmp_path: Path):
    e = env(tmp_path, motley_url=MOTLEY_URL, motley_user_id="se-20261111-143000-0123456789ab")
    inp = AgentInput(prompt="p", profile="motley", env=e)
    back = AgentInput.model_validate_json(inp.model_dump_json())
    assert back == inp
    assert back.env.motley_url == MOTLEY_URL
    assert back.env.motley_user_id == "se-20261111-143000-0123456789ab"


def test_run_metadata_motley_fields_default_to_none():
    md = RunMetadata.model_validate(METADATA)
    assert md.motley_url is None
    assert md.motley_server_info is None


def test_run_metadata_motley_round_trip():
    md = RunMetadata.model_validate({**METADATA, "motley_url": MOTLEY_URL, "motley_server_info": "motley 1.30.0"})
    back = RunMetadata.model_validate_json(md.model_dump_json())
    assert back == md
    assert (back.motley_url, back.motley_server_info) == (MOTLEY_URL, "motley 1.30.0")
    assert back.started_at == dt.datetime(2026, 11, 11, 14, 30, tzinfo=dt.UTC)


def test_committed_metadata_without_motley_fields_loads():
    for path in (
        REPO / "results" / "baseline" / "metadata.json",
        REPO / "tests" / "fixtures" / "run_repeat" / "metadata.json",
    ):
        raw = json.loads(path.read_text())
        assert "motley_url" not in raw
        md = RunMetadata.model_validate(raw)
        assert md.motley_url is None
        assert md.motley_server_info is None


def test_xfail_without_profiles_applies_to_every_profile():
    xf = XFail(issue="DEV-2058", reason="clock")
    assert xf.profiles == []
    assert all(xf.applies_to(p) for p in PROFILES)


def test_profile_scoped_xfail():
    xf = XFail(issue="DEV-1951", reason="no warnings", profiles=["motley", "motley+python"])
    assert [p for p in PROFILES if xf.applies_to(p)] == [p for p in PROFILES if p.startswith("motley")]


def test_xfail_rejects_unknown_profile():
    with pytest.raises(ValidationError):
        XFail(issue="DEV-1951", reason="r", profiles=["cube"])  # pyright: ignore[reportArgumentType]


def test_profile_scoped_xfail_round_trip():
    task = make_task(xfail={"issue": "DEV-1951", "reason": "r", "profiles": ["motley", "motley+python"]})
    assert type(task).model_validate_json(task.model_dump_json()) == task


def _xfail_doc(**xfail) -> dict:
    return {
        "id": "q9-x",
        "covers": ["Q9"],
        "prompt": "Total credit limit per order status.",
        "truth_sql": "select 1 as v",
        "slayer_query": {"query": {"source_model": "orders"}},
        "xfail": {"issue": "DEV-1951", "reason": "Motley's query drops result warnings", **xfail},
    }


def test_profile_scoped_xfail_loads(tmp_path: Path):
    task = load_task(write_task(tmp_path, _xfail_doc(profiles=["motley", "motley+python"])))
    assert task.xfail is not None
    assert task.xfail.profiles == ["motley", "motley+python"]
    assert task.xfail.applies_to("motley")
    assert task.xfail.applies_to("motley+python")
    assert not task.xfail.applies_to("slayer")
    assert not task.xfail.applies_to("sql+python")


def test_xfail_naming_an_unknown_profile_rejected(tmp_path: Path):
    path = write_task(tmp_path, _xfail_doc(profiles=["motley", "cube"]), name="bad")
    with pytest.raises(TaskFormatError) as exc:
        load_task(path)
    assert "bad.yaml" in str(exc.value)
    assert "cube" in str(exc.value)
