"""Scenario definitions, loaded from YAML in ``scenarios/``."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field

SCENARIO_DIR = Path(__file__).parent / "scenarios"


class DegradedRrc(BaseModel):
    """Lower the RRC setup success rate on a number of randomly chosen cells."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    type: Literal["degraded_rrc"]
    cell_count: int = Field(ge=1)
    rrc_success_rate: float = Field(gt=0, lt=1)


class CellDown(BaseModel):
    """Take cells out of service: operationally disabled, zero traffic, one
    active alarm each."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    type: Literal["cell_down"]
    cell_count: int = Field(ge=1)


Injection = Annotated[DegradedRrc | CellDown, Field(discriminator="type")]


class Scenario(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str = Field(min_length=1)
    description: str = Field(min_length=1)
    injections: tuple[Injection, ...] = ()


def available_scenarios() -> list[str]:
    return sorted(p.stem for p in SCENARIO_DIR.glob("*.yaml"))


def load_scenario(name: str) -> Scenario:
    path = SCENARIO_DIR / f"{name}.yaml"
    if not path.is_file():
        raise ValueError(
            f"unknown scenario {name!r}; available: {available_scenarios()}"
        )
    scenario = Scenario.model_validate(yaml.safe_load(path.read_text("utf-8")))
    if scenario.name != name:
        raise ValueError(
            f"{path.name}: scenario name {scenario.name!r} does not match file"
        )
    return scenario
