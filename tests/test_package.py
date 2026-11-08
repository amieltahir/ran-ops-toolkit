"""Smoke tests for the package scaffold."""

import ranops
import ranops.core


def test_package_imports() -> None:
    assert ranops.__name__ == "ranops"
    assert ranops.core.__name__ == "ranops.core"


def test_core_model_exports() -> None:
    from ranops.core import AdminState, CellState, OperationalState, Site

    site = Site(id="site-1", name="Test site")
    state = CellState(
        cell_id="cell-1",
        admin_state=AdminState.UNLOCKED,
        operational_state=OperationalState.ENABLED,
    )
    assert site.id == "site-1"
    assert state.in_service
