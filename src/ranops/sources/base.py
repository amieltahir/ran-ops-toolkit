"""Source interfaces. Sources are separate from adapters: a source says where
data comes from (lab, CSV, NetBox, a PM file directory); an adapter talks to a
vendor's node."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Protocol, runtime_checkable

from pydantic import AwareDatetime

from ranops.core.models import CoreModel, Measurement, Node


class Period(CoreModel):
    """Half-open time window [start, end)."""

    start: AwareDatetime
    end: AwareDatetime

    def contains(self, t: AwareDatetime) -> bool:
        return self.start <= t < self.end


@runtime_checkable
class InventorySource(Protocol):
    def get_inventory(self) -> list[Node]: ...


@runtime_checkable
class PmSource(Protocol):
    """Yields canonical measurements for a period. Parsing a standard format
    (TS 32.435 XML) belongs in a vendor-neutral PmSource, not in an adapter."""

    def read_pm(self, period: Period) -> Iterable[Measurement]: ...
