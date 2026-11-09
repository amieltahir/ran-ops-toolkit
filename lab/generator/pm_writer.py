"""Write 3GPP-style (TS 32.435) PM measurement collection XML files.

The element layout follows the author's recollection of ``measCollec.xsd`` and
must be confirmed by validating the output against the real schema (see
``pm_validator`` and ``scripts/fetch_xsd.py``).
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

from lxml import etree
from ranops.core import Measurement, load_counters

from lab.generator.network import Network

NAMESPACE = "http://www.3gpp.org/ftp/specs/archive/32_series/32.435#measCollec"
FILE_FORMAT_VERSION = "32.435 V10.0"
DN_PREFIX = "SubNetwork=LAB"


def _ts(value: datetime) -> str:
    return value.isoformat()


def pm_filename(node_id: str, period_start: datetime, granularity_s: int) -> str:
    """3GPP-style file name: ``A<begin>-<end>_<node>.xml`` (UTC)."""
    end = period_start + timedelta(seconds=granularity_s)
    return f"A{period_start:%Y%m%d.%H%M}+0000-{end:%H%M}+0000_{node_id}.xml"


def render_pm_file(
    network: Network,
    node_id: str,
    period_start: datetime,
    granularity_s: int,
    measurements: list[Measurement],
) -> bytes:
    """Render one node's measurements for one period as XML bytes."""
    node = next(n for n in network.nodes if n.id == node_id)
    end = period_start + timedelta(seconds=granularity_s)
    order = list(load_counters())
    position = {name: i for i, name in enumerate(order, start=1)}

    def q(tag: str) -> str:
        return f"{{{NAMESPACE}}}{tag}"

    root = etree.Element(q("measCollecFile"), nsmap={None: NAMESPACE})
    header = etree.SubElement(
        root,
        q("fileHeader"),
        fileFormatVersion=FILE_FORMAT_VERSION,
        vendorName=node.vendor,
        dnPrefix=DN_PREFIX,
    )
    etree.SubElement(header, q("fileSender"), localDn=f"ManagedElement={node.id}")
    etree.SubElement(header, q("measCollec"), beginTime=_ts(period_start))

    data = etree.SubElement(root, q("measData"))
    etree.SubElement(
        data,
        q("managedElement"),
        localDn=f"ManagedElement={node.id}",
        swVersion=node.sw_version,
    )
    info = etree.SubElement(data, q("measInfo"), measInfoId="LTE_CELL")
    etree.SubElement(info, q("job"), jobId="lab-pm-15min")
    etree.SubElement(
        info, q("granPeriod"), duration=f"PT{granularity_s}S", endTime=_ts(end)
    )
    etree.SubElement(info, q("repPeriod"), duration=f"PT{granularity_s}S")
    for name in order:
        etree.SubElement(info, q("measType"), p=str(position[name])).text = name

    by_cell: dict[str, list[Measurement]] = defaultdict(list)
    for m in measurements:
        by_cell[m.object_id].append(m)
    for cell_id in sorted(by_cell):
        value = etree.SubElement(
            info, q("measValue"), measObjLdn=f"EUtranCellFDD={cell_id}"
        )
        for m in sorted(by_cell[cell_id], key=lambda m: position[m.counter]):
            etree.SubElement(value, q("r"), p=str(position[m.counter])).text = repr(
                m.value
            )

    footer = etree.SubElement(root, q("fileFooter"))
    etree.SubElement(footer, q("measCollec"), endTime=_ts(end))
    return etree.tostring(
        root, xml_declaration=True, encoding="UTF-8", pretty_print=True
    )


def write_pm_files(
    network: Network, measurements: tuple[Measurement, ...], out_dir: Path
) -> list[Path]:
    """Write one XML file per node and period under ``out_dir``; return the paths."""
    cell_node = {c.id: c.node_id for c in network.cells}
    groups: dict[tuple[str, datetime, int], list[Measurement]] = defaultdict(list)
    for m in measurements:
        groups[(cell_node[m.object_id], m.period_start, m.granularity_s)].append(m)

    out_dir.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    for (node_id, period_start, granularity_s), items in sorted(groups.items()):
        path = out_dir / pm_filename(node_id, period_start, granularity_s)
        path.write_bytes(
            render_pm_file(network, node_id, period_start, granularity_s, items)
        )
        paths.append(path)
    return paths
