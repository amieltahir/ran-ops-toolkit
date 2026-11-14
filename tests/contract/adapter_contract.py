"""Shared contract tests for every RanAdapter implementation.

Subclass ``AdapterContract`` in a test module and provide the fixtures
``adapter`` and ``truth`` (see below). The class has no ``Test`` prefix so
pytest does not collect it directly; the subclass must be named ``Test...``.

``truth`` is a small object built from the generator's truth.json with:
    nodes: list[Node]
    cell_states: dict[str, CellState]      # cell_id -> expected state
    active_alarm_objects: set[str]         # object ids with an active alarm
    parameters: dict[tuple[str, str], object]  # (object_id, name) -> value
"""

from __future__ import annotations

from typing import Any

from ranops.adapters import RanAdapter


class AdapterContract:
    def test_is_ran_adapter(self, adapter: Any) -> None:
        assert isinstance(adapter, RanAdapter)

    def test_inventory_matches_truth(self, adapter: Any, truth: Any) -> None:
        assert {n.id for n in adapter.get_inventory()} == {n.id for n in truth.nodes}

    def test_cell_states_match_truth(self, adapter: Any, truth: Any) -> None:
        seen = {}
        for node in adapter.get_inventory():
            for state in adapter.get_cell_states(node):
                seen[state.cell_id] = state
        assert seen == truth.cell_states

    def test_active_alarms_match_truth(self, adapter: Any, truth: Any) -> None:
        active = set()
        for node in adapter.get_inventory():
            active |= {a.object_id for a in adapter.list_alarms(node) if a.is_active}
        assert active == truth.active_alarm_objects

    def test_parameters_match_truth(self, adapter: Any, truth: Any) -> None:
        for node in adapter.get_inventory():
            names = sorted({name for (_, name) in truth.parameters})
            for p in adapter.get_parameters(node, names):
                key = (p.object_id, p.name)
                if key in truth.parameters:
                    assert p.value == truth.parameters[key]

    def test_unknown_parameter_is_omitted_not_fatal(self, adapter: Any) -> None:
        node = adapter.get_inventory()[0]
        assert adapter.get_parameters(node, ["noSuchParameter"]) == []
