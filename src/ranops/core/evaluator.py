"""Evaluate catalogue KPIs from raw counter values."""

from __future__ import annotations

from collections.abc import Mapping

from pydantic import AwareDatetime

from ranops.core.catalogue import KpiDef
from ranops.core.formula import evaluate_formula
from ranops.core.models import KpiSample


def evaluate_kpi(
    kpi: KpiDef,
    cell_id: str,
    period_start: AwareDatetime,
    counters: Mapping[str, float],
    granularity_s: int = 900,
) -> KpiSample:
    """Compute ``kpi`` for one cell and period from ``counters`` keyed by counter
    name. The sample value is ``None`` if any input is missing or the formula
    cannot be evaluated (for example, a zero denominator)."""
    inputs = {
        alias: counters[counter]
        for alias, counter in kpi.inputs.items()
        if counter in counters
    }
    return KpiSample(
        cell_id=cell_id,
        kpi=kpi.name,
        period_start=period_start,
        granularity_s=granularity_s,
        value=evaluate_formula(kpi.formula, inputs),
        inputs={kpi.inputs[alias]: v for alias, v in inputs.items()},
    )
