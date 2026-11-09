"""Counter catalogue and KPI definitions, loaded from packaged YAML.

Counter names are 3GPP names (TS 32.425). KPI formulas use short aliases that
map to catalogue counters, because 3GPP counter names are not valid identifiers.
"""

from __future__ import annotations

from collections.abc import Mapping
from functools import cache
from importlib import resources
from typing import Any

import yaml
from pydantic import Field, model_validator

from ranops.core.formula import formula_names
from ranops.core.models import CoreModel


class CounterDef(CoreModel):
    name: str = Field(min_length=1)
    description: str = Field(min_length=1)
    unit: str = Field(min_length=1)
    reference: str = Field(min_length=1)


class KpiDef(CoreModel):
    name: str = Field(min_length=1)
    description: str = Field(min_length=1)
    unit: str = Field(min_length=1)
    formula: str = Field(min_length=1)
    inputs: Mapping[str, str]
    reference: str = Field(min_length=1)

    @model_validator(mode="after")
    def _formula_uses_declared_inputs(self) -> KpiDef:
        unknown = formula_names(self.formula) - set(self.inputs)
        if unknown:
            raise ValueError(f"formula uses undeclared inputs: {sorted(unknown)}")
        return self


def _read_yaml(filename: str) -> dict[str, Any]:
    text = resources.files("ranops.core").joinpath(filename).read_text("utf-8")
    data = yaml.safe_load(text)
    if not isinstance(data, dict):
        raise ValueError(f"{filename}: expected a mapping at the top level")
    return data


@cache
def load_counters() -> Mapping[str, CounterDef]:
    entries = _read_yaml("counters.yaml").get("counters", [])
    counters = [CounterDef.model_validate(e) for e in entries]
    by_name = {c.name: c for c in counters}
    if len(by_name) != len(counters):
        raise ValueError("counters.yaml: duplicate counter names")
    return by_name


@cache
def load_kpis() -> Mapping[str, KpiDef]:
    entries = _read_yaml("kpis.yaml").get("kpis", [])
    kpis = [KpiDef.model_validate(e) for e in entries]
    by_name = {k.name: k for k in kpis}
    if len(by_name) != len(kpis):
        raise ValueError("kpis.yaml: duplicate KPI names")
    counters = load_counters()
    for kpi in kpis:
        missing = set(kpi.inputs.values()) - set(counters)
        if missing:
            raise ValueError(f"KPI {kpi.name}: unknown counters {sorted(missing)}")
    return by_name
