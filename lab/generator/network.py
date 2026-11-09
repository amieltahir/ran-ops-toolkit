"""Deterministic synthetic LTE network builder."""

from __future__ import annotations

import math
import random
from dataclasses import dataclass

from ranops.core import Cell, Node, Site

MAX_CELLS = 200
CELLS_PER_SITE = 3
# (band, DL EARFCN, DL PRBs) per sector. Lab values only.
_SECTOR_LAYERS = ((3, 1300, 100), (7, 3100, 100), (20, 6300, 50))


@dataclass(frozen=True)
class Network:
    sites: tuple[Site, ...]
    nodes: tuple[Node, ...]
    cells: tuple[Cell, ...]


def prb_available(cell: Cell) -> int:
    """Downlink PRBs for the cell's layer."""
    for band, _earfcn, prbs in _SECTOR_LAYERS:
        if band == cell.band:
            return prbs
    raise ValueError(f"unknown band {cell.band}")


def build_network(seed: int, n_cells: int) -> Network:
    """Build a network of ``n_cells`` cells, three per site, deterministic per seed."""
    if not 1 <= n_cells <= MAX_CELLS:
        raise ValueError(f"n_cells must be between 1 and {MAX_CELLS}")
    rng = random.Random(f"network:{seed}")
    n_sites = math.ceil(n_cells / CELLS_PER_SITE)
    pcis = rng.sample(range(504), n_cells)  # unique PCIs avoid accidental conflicts

    sites: list[Site] = []
    nodes: list[Node] = []
    cells: list[Cell] = []
    for i in range(1, n_sites + 1):
        site_id, node_id = f"SITE{i:03d}", f"ENB{i:03d}"
        sites.append(
            Site(
                id=site_id,
                name=f"Lab site {i}",
                latitude=round(rng.uniform(51.0, 52.0), 5),
                longitude=round(rng.uniform(-1.0, 0.0), 5),
            )
        )
        nodes.append(
            Node.model_validate(
                {
                    "id": node_id,
                    "site_id": site_id,
                    "vendor": "ericsson",
                    "sw_version": "LAB-21.Q4",
                    "ip": f"10.20.{(i - 1) // 250}.{(i - 1) % 250 + 1}",
                }
            )
        )
        for sector, (band, earfcn, _prbs) in enumerate(_SECTOR_LAYERS, start=1):
            if len(cells) == n_cells:
                break
            cells.append(
                Cell(
                    id=f"{node_id}-{sector}",
                    node_id=node_id,
                    band=band,
                    earfcn=earfcn,
                    pci=pcis[len(cells)],
                    tac=1001 + (i - 1) // 10,
                )
            )
    return Network(tuple(sites), tuple(nodes), tuple(cells))


def validate_network(network: Network) -> list[str]:
    """Return a list of consistency errors (empty if the network is valid)."""
    errors: list[str] = []
    site_ids = [s.id for s in network.sites]
    node_ids = [n.id for n in network.nodes]
    cell_ids = [c.id for c in network.cells]
    for label, ids in (("site", site_ids), ("node", node_ids), ("cell", cell_ids)):
        if len(set(ids)) != len(ids):
            errors.append(f"duplicate {label} ids")
    errors += [
        f"node {n.id}: unknown site {n.site_id}"
        for n in network.nodes
        if n.site_id not in site_ids
    ]
    errors += [
        f"cell {c.id}: unknown node {c.node_id}"
        for c in network.cells
        if c.node_id not in node_ids
    ]
    pcis = [c.pci for c in network.cells]
    if len(set(pcis)) != len(pcis):
        errors.append("duplicate PCIs")
    if not 1 <= len(network.cells) <= MAX_CELLS:
        errors.append(f"cell count outside 1..{MAX_CELLS}")
    return errors
