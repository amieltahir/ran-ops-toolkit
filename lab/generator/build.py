"""Generate PM measurements for a network and scenario, plus ground truth."""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from ranops.core import Measurement, load_counters

from lab.generator.network import Network, build_network, prb_available
from lab.generator.scenarios import Scenario, load_scenario

GRANULARITY_S = 900
DEFAULT_START = datetime(2026, 1, 1, tzinfo=UTC)

RRC_ATT = "RRC.ConnEstabAtt.Sum"
RRC_SUCC = "RRC.ConnEstabSucc.Sum"
ERAB_ATT = "E-RAB.EstabInitAttNbr.Sum"
ERAB_SUCC = "E-RAB.EstabInitSuccNbr.Sum"
PRB_USED = "RRU.PrbUsedDl"
PRB_AVAIL = "RRU.PrbAvailDl"


@dataclass(frozen=True)
class Dataset:
    seed: int
    scenario: Scenario
    network: Network
    start: datetime
    periods: int
    measurements: tuple[Measurement, ...]
    truth: dict[str, Any]


def _diurnal(period_start: datetime) -> float:
    """Traffic factor between 0.3 and 1.0, peaking in the evening."""
    hour = period_start.hour + period_start.minute / 60
    return 0.65 + 0.35 * math.sin((hour - 13) / 24 * 2 * math.pi)


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def generate(
    seed: int,
    scenario_name: str,
    n_cells: int = 60,
    periods: int = 96,
    start: datetime = DEFAULT_START,
) -> Dataset:
    """Build a network and ``periods`` 15-minute periods of PM data.

    The result depends only on the arguments, so identical inputs always give
    identical output.
    """
    if periods < 1:
        raise ValueError("periods must be at least 1")
    if start.tzinfo is None:
        raise ValueError("start must be timezone-aware")
    scenario = load_scenario(scenario_name)
    network = build_network(seed, n_cells)
    cell_ids = sorted(c.id for c in network.cells)

    injected: list[dict[str, Any]] = []
    rrc_rate_override: dict[str, float] = {}
    inject_rng = random.Random(f"inject:{seed}:{scenario.name}")
    for injection in scenario.injections:
        free = [c for c in cell_ids if c not in rrc_rate_override]
        for cell_id in sorted(
            inject_rng.sample(free, min(injection.cell_count, len(free)))
        ):
            rrc_rate_override[cell_id] = injection.rrc_success_rate
            injected.append(
                {
                    "type": injection.type,
                    "cell_id": cell_id,
                    "rrc_success_rate": injection.rrc_success_rate,
                }
            )

    counters = load_counters()
    for name in (RRC_ATT, RRC_SUCC, ERAB_ATT, ERAB_SUCC, PRB_USED, PRB_AVAIL):
        if name not in counters:
            raise ValueError(f"counter {name} missing from the catalogue")

    traffic_rng = random.Random(f"traffic:{seed}")
    cells = sorted(network.cells, key=lambda c: c.id)
    base_load = {c.id: traffic_rng.randint(3000, 9000) for c in cells}
    measurements: list[Measurement] = []
    for index in range(periods):
        period_start = start + timedelta(seconds=GRANULARITY_S * index)
        load = _diurnal(period_start)
        for cell in cells:
            att = round(base_load[cell.id] * load * traffic_rng.uniform(0.9, 1.1))
            if cell.id in rrc_rate_override:
                rate = rrc_rate_override[cell.id] + traffic_rng.gauss(0, 0.01)
            else:
                rate = 0.995 + traffic_rng.gauss(0, 0.002)
            succ = min(att, round(att * _clamp(rate, 0.0, 1.0)))
            erab_att = succ
            erab_succ = min(
                erab_att,
                round(erab_att * _clamp(0.997 + traffic_rng.gauss(0, 0.002), 0, 1)),
            )
            avail = prb_available(cell)
            used = round(
                avail * _clamp(0.55 * load * traffic_rng.uniform(0.9, 1.1), 0, 1), 1
            )
            values = {
                RRC_ATT: att,
                RRC_SUCC: succ,
                ERAB_ATT: erab_att,
                ERAB_SUCC: erab_succ,
                PRB_USED: used,
                PRB_AVAIL: avail,
            }
            measurements.extend(
                Measurement(
                    object_id=cell.id,
                    counter=counter,
                    period_start=period_start,
                    granularity_s=GRANULARITY_S,
                    value=float(value),
                )
                for counter, value in values.items()
            )

    truth = {
        "seed": seed,
        "scenario": scenario.name,
        "cells": len(network.cells),
        "start": start.isoformat(),
        "periods": periods,
        "granularity_s": GRANULARITY_S,
        "injected": injected,
    }
    return Dataset(seed, scenario, network, start, periods, tuple(measurements), truth)
