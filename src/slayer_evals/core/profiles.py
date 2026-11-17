"""Profiles: what an agent is connected to, as one table every node reads."""

from typing import Literal

from pydantic import BaseModel

Profile = Literal["slayer", "slayer+python", "sql+python", "motley", "motley+python"]
Surface = Literal["slayer", "motley", "sql"]


class ProfileSpec(BaseModel):
    """The data surface a profile exposes, and whether it adds the Python tool."""

    surface: Surface
    python: bool


PROFILE_SPECS: dict[Profile, ProfileSpec] = {
    "slayer": ProfileSpec(surface="slayer", python=False),
    "slayer+python": ProfileSpec(surface="slayer", python=True),
    "sql+python": ProfileSpec(surface="sql", python=True),
    "motley": ProfileSpec(surface="motley", python=False),
    "motley+python": ProfileSpec(surface="motley", python=True),
}
PROFILES: tuple[Profile, ...] = tuple(PROFILE_SPECS)
DEFAULT_PROFILES: tuple[Profile, ...] = ("slayer", "slayer+python", "sql+python")
