"""System discovery via entry points (group `gw.systems`).

Nothing in gw_common imports a system package; systems announce themselves in their pyproject.
"""

from __future__ import annotations

from importlib.metadata import entry_points

from gw_common.interfaces import System

GROUP = "gw.systems"


def available() -> dict[str, str]:
    """name -> entry point target, for `gw-eval --list`."""
    return {ep.name: ep.value for ep in entry_points(group=GROUP)}


def load(name: str) -> System:
    for ep in entry_points(group=GROUP):
        if ep.name == name:
            system = ep.load()()
            if not isinstance(system, System):
                raise TypeError(f"{ep.value} does not satisfy the System protocol")
            return system
    known = ", ".join(sorted(available())) or "(none installed)"
    raise KeyError(f"unknown system {name!r}. Registered systems: {known}")
