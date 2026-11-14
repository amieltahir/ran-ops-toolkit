"""Adapter interface. Tools call only this; they never import a vendor package.

PM data is read through ``ranops.sources.PmSource``, not through the adapter.
If a vendor needs counter-name mapping, add an explicit hook in M3 rather than
widening this interface now.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol, runtime_checkable

from ranops.core.models import Alarm, CellState, Node, Parameter


@runtime_checkable
class RanAdapter(Protocol):
    def get_inventory(self) -> list[Node]: ...

    def get_cell_states(self, node: Node) -> list[CellState]: ...

    def get_parameters(self, node: Node, names: Sequence[str]) -> list[Parameter]: ...

    def list_alarms(self, node: Node) -> list[Alarm]: ...
