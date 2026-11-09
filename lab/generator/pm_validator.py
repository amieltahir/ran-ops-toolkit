"""Validate PM XML files against an XSD (for example 3GPP ``measCollec.xsd``)."""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

from lxml import etree

DEFAULT_XSD = Path(__file__).resolve().parents[2] / "third_party" / "measCollec.xsd"


def load_schema(xsd_path: Path) -> etree.XMLSchema:
    return etree.XMLSchema(etree.parse(str(xsd_path)))


def validate_file(path: Path, schema: etree.XMLSchema) -> list[str]:
    """Return schema errors for ``path`` (empty if valid)."""
    try:
        document = etree.parse(str(path))
    except etree.XMLSyntaxError as exc:
        return [f"{path.name}: not well-formed: {exc}"]
    if schema.validate(document):
        return []
    return [f"{path.name}: line {e.line}: {e.message}" for e in schema.error_log]


def validate_files(paths: Iterable[Path], xsd_path: Path) -> dict[str, list[str]]:
    """Validate every file; return only the files that have errors."""
    schema = load_schema(xsd_path)
    results = {p.name: validate_file(p, schema) for p in paths}
    return {name: errors for name, errors in results.items() if errors}
