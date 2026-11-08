"""Unit tests for the canonical model."""

from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from ranops.core import (
    AdminState,
    Alarm,
    Baseline,
    BaselineEntry,
    Cell,
    CellState,
    KpiSample,
    Measurement,
    Node,
    OperationalState,
    Parameter,
    ParameterScope,
    Severity,
    Site,
)

T0 = datetime(2026, 1, 1, 0, 0, tzinfo=UTC)


def make_cell(**overrides: object) -> Cell:
    data: dict[str, object] = {
        "id": "C1",
        "node_id": "N1",
        "band": 3,
        "earfcn": 1300,
        "pci": 100,
        "tac": 1001,
    }
    data.update(overrides)
    return Cell.model_validate(data)


def test_site_rejects_bad_coordinates() -> None:
    with pytest.raises(ValidationError):
        Site(id="S1", name="Site 1", latitude=95.0)


def test_node_parses_ip() -> None:
    node = Node.model_validate(
        {
            "id": "N1",
            "site_id": "S1",
            "vendor": "x",
            "sw_version": "1.0",
            "ip": "10.0.0.1",
        }
    )
    assert str(node.ip) == "10.0.0.1"


def test_node_rejects_invalid_ip() -> None:
    with pytest.raises(ValidationError):
        Node.model_validate(
            {
                "id": "N1",
                "site_id": "S1",
                "vendor": "x",
                "sw_version": "1.0",
                "ip": "10.244.08.40",
            }
        )


@pytest.mark.parametrize("pci", [-1, 504])
def test_cell_rejects_out_of_range_pci(pci: int) -> None:
    with pytest.raises(ValidationError):
        make_cell(pci=pci)


def test_cell_accepts_pci_bounds() -> None:
    assert make_cell(pci=0).pci == 0
    assert make_cell(pci=503).pci == 503


def test_models_are_frozen() -> None:
    cell = make_cell()
    with pytest.raises(ValidationError):
        cell.pci = 5


def test_extra_fields_forbidden() -> None:
    with pytest.raises(ValidationError):
        make_cell(unknown="x")


@pytest.mark.parametrize(
    ("admin", "oper", "expected"),
    [
        (AdminState.UNLOCKED, OperationalState.ENABLED, True),
        (AdminState.UNLOCKED, OperationalState.DISABLED, False),
        (AdminState.LOCKED, OperationalState.ENABLED, False),
        (AdminState.SHUTTING_DOWN, OperationalState.ENABLED, False),
    ],
)
def test_cell_state_in_service(
    admin: AdminState, oper: OperationalState, expected: bool
) -> None:
    state = CellState(cell_id="C1", admin_state=admin, operational_state=oper)
    assert state.in_service is expected


def test_parameter_and_baseline_entry() -> None:
    param = Parameter(scope=ParameterScope.CELL, object_id="C1", name="p", value=-114)
    entry = BaselineEntry(scope=ParameterScope.CELL, name="p", expected=-114)
    assert param.value == entry.expected
    assert entry.object_ids is None


def test_baseline_holds_entries() -> None:
    entry = BaselineEntry(
        scope=ParameterScope.CELL, name="p", expected=1, object_ids=frozenset({"C1"})
    )
    baseline = Baseline(name="b", version="1", entries=(entry,))
    assert baseline.entries[0].object_ids == frozenset({"C1"})


def make_alarm(**overrides: object) -> Alarm:
    data: dict[str, object] = {
        "id": "A1",
        "object_id": "C1",
        "severity": Severity.MAJOR,
        "alarm_type": "communications",
        "probable_cause": "cell unavailable",
        "raised_at": T0,
    }
    data.update(overrides)
    return Alarm.model_validate(data)


def test_alarm_active_until_cleared() -> None:
    assert make_alarm().is_active is True
    assert make_alarm(cleared_at=T0 + timedelta(minutes=5)).is_active is False


def test_alarm_with_cleared_severity_is_not_active() -> None:
    assert make_alarm(severity=Severity.CLEARED).is_active is False


def test_alarm_rejects_clear_before_raise() -> None:
    with pytest.raises(ValidationError):
        make_alarm(cleared_at=T0 - timedelta(minutes=1))


def test_alarm_requires_timezone_aware_times() -> None:
    with pytest.raises(ValidationError):
        make_alarm(raised_at=datetime(2026, 1, 1))


def test_measurement_default_granularity() -> None:
    m = Measurement(
        object_id="C1", counter="RRC.ConnEstabAtt", period_start=T0, value=10
    )
    assert m.granularity_s == 900


def test_measurement_rejects_zero_granularity() -> None:
    with pytest.raises(ValidationError):
        Measurement(
            object_id="C1", counter="c", period_start=T0, granularity_s=0, value=1
        )


def test_kpi_sample_allows_missing_value() -> None:
    sample = KpiSample(
        cell_id="C1", kpi="rrc_setup_success_rate", period_start=T0, value=None
    )
    assert sample.value is None
    assert sample.inputs == {}
