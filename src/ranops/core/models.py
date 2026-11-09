"""Canonical, vendor-neutral data model.

Nothing in this module may reference a vendor. Vendor-specific names and
formats are translated into these types inside ``ranops.adapters``.

State and alarm semantics follow ITU-T X.731 (admin/operational state) and
X.733 (perceived severity).
"""

from __future__ import annotations

from collections.abc import Mapping
from enum import StrEnum
from ipaddress import IPv4Address
from types import MappingProxyType

from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    field_serializer,
    field_validator,
    model_validator,
)


class CoreModel(BaseModel):
    """Base for all canonical models: immutable, no unknown fields."""

    model_config = ConfigDict(frozen=True, extra="forbid")


class AdminState(StrEnum):
    LOCKED = "locked"
    UNLOCKED = "unlocked"
    SHUTTING_DOWN = "shutting_down"


class OperationalState(StrEnum):
    ENABLED = "enabled"
    DISABLED = "disabled"


class Severity(StrEnum):
    CRITICAL = "critical"
    MAJOR = "major"
    MINOR = "minor"
    WARNING = "warning"
    INDETERMINATE = "indeterminate"
    CLEARED = "cleared"


class UnitKind(StrEnum):
    BASEBAND = "baseband"
    RADIO = "radio"


class ParameterScope(StrEnum):
    NODE = "node"
    CELL = "cell"


ParamValue = str | int | float | bool


class Site(CoreModel):
    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)


class Node(CoreModel):
    """A radio node (an eNodeB in LTE)."""

    id: str = Field(min_length=1)
    site_id: str = Field(min_length=1)
    vendor: str = Field(min_length=1)
    sw_version: str = Field(min_length=1)
    ip: IPv4Address


class Unit(CoreModel):
    """A hardware unit of a radio node (baseband or radio)."""

    id: str = Field(min_length=1)
    node_id: str = Field(min_length=1)
    kind: UnitKind


class Cell(CoreModel):
    id: str = Field(min_length=1)
    node_id: str = Field(min_length=1)
    band: int = Field(ge=1, le=256)
    earfcn: int = Field(ge=0, le=262143)
    pci: int = Field(ge=0, le=503)
    tac: int = Field(ge=0, le=65535)


class CellState(CoreModel):
    cell_id: str = Field(min_length=1)
    admin_state: AdminState
    operational_state: OperationalState

    @property
    def in_service(self) -> bool:
        return (
            self.admin_state is AdminState.UNLOCKED
            and self.operational_state is OperationalState.ENABLED
        )


class Parameter(CoreModel):
    """An observed parameter value on a node or a cell."""

    scope: ParameterScope
    object_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    value: ParamValue


class BaselineEntry(CoreModel):
    """Expected value for one parameter.

    ``object_ids`` limits the entry to specific nodes/cells; ``None`` means it
    applies to every object of the given scope.
    """

    scope: ParameterScope
    name: str = Field(min_length=1)
    expected: ParamValue
    object_ids: frozenset[str] | None = None


class Baseline(CoreModel):
    name: str = Field(min_length=1)
    version: str = Field(min_length=1)
    entries: tuple[BaselineEntry, ...]


class Alarm(CoreModel):
    id: str = Field(min_length=1)
    object_id: str = Field(min_length=1)
    severity: Severity
    alarm_type: str = Field(min_length=1)
    probable_cause: str = Field(min_length=1)
    raised_at: AwareDatetime
    cleared_at: AwareDatetime | None = None

    @model_validator(mode="after")
    def _cleared_not_before_raised(self) -> Alarm:
        if self.cleared_at is not None and self.cleared_at < self.raised_at:
            raise ValueError("cleared_at must not be earlier than raised_at")
        return self

    @property
    def is_active(self) -> bool:
        return self.cleared_at is None and self.severity is not Severity.CLEARED


class Measurement(CoreModel):
    """One raw counter value for one object and one measurement period."""

    object_id: str = Field(min_length=1)
    counter: str = Field(min_length=1)
    period_start: AwareDatetime
    granularity_s: int = Field(default=900, gt=0)
    value: float


class KpiSample(CoreModel):
    """A computed KPI value. ``value`` is ``None`` when inputs were missing or the
    denominator was zero; ``inputs`` records the counter values used."""

    cell_id: str = Field(min_length=1)
    kpi: str = Field(min_length=1)
    period_start: AwareDatetime
    granularity_s: int = Field(default=900, gt=0)
    value: float | None
    inputs: Mapping[str, float] = Field(default_factory=dict)

    @field_validator("inputs")
    @classmethod
    def _freeze_inputs(cls, value: Mapping[str, float]) -> Mapping[str, float]:
        return MappingProxyType(dict(value))

    @field_serializer("inputs")
    def _serialise_inputs(self, value: Mapping[str, float]) -> dict[str, float]:
        return dict(value)
