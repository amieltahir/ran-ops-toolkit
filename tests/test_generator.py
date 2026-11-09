"""Tests for the seeded generator, PM writer and validator."""

import hashlib
from datetime import UTC, datetime
from pathlib import Path

import pytest
from lxml import etree
from ranops.core import evaluate_kpi, load_counters, load_kpis

from lab.generator.build import generate
from lab.generator.network import build_network, validate_network
from lab.generator.pm_validator import DEFAULT_XSD, validate_files
from lab.generator.pm_writer import NAMESPACE, write_pm_files
from lab.generator.scenarios import available_scenarios, load_scenario

NS = {"m": NAMESPACE}


def digest(directory: Path) -> str:
    h = hashlib.sha256()
    for path in sorted(directory.rglob("*.xml")):
        h.update(path.name.encode())
        h.update(path.read_bytes())
    return h.hexdigest()


@pytest.mark.parametrize("n_cells", [1, 50, 61, 200])
def test_network_is_valid(n_cells: int) -> None:
    network = build_network(1, n_cells)
    assert len(network.cells) == n_cells
    assert validate_network(network) == []


@pytest.mark.parametrize("n_cells", [0, 201])
def test_network_size_limits(n_cells: int) -> None:
    with pytest.raises(ValueError):
        build_network(1, n_cells)


def test_network_deterministic_per_seed() -> None:
    assert build_network(7, 60) == build_network(7, 60)
    assert build_network(7, 60) != build_network(8, 60)


def test_scenarios_available() -> None:
    assert {"healthy", "degraded_rrc"} <= set(available_scenarios())
    with pytest.raises(ValueError):
        load_scenario("nope")


def test_generated_counters_are_in_catalogue() -> None:
    dataset = generate(1, "healthy", n_cells=6, periods=2)
    assert {m.counter for m in dataset.measurements} <= set(load_counters())


def test_dataset_deterministic_per_seed() -> None:
    a = generate(3, "degraded_rrc", n_cells=30, periods=4)
    b = generate(3, "degraded_rrc", n_cells=30, periods=4)
    c = generate(4, "degraded_rrc", n_cells=30, periods=4)
    assert a.measurements == b.measurements
    assert a.truth == b.truth
    assert a.measurements != c.measurements


def test_healthy_truth_has_no_injections() -> None:
    assert generate(1, "healthy", n_cells=30, periods=1).truth["injected"] == []


def mean_rrc_rate(dataset_measurements: tuple, cell_id: str) -> float:  # type: ignore[type-arg]
    kpi = load_kpis()["rrc_setup_success_rate"]
    by_period: dict[datetime, dict[str, float]] = {}
    for m in dataset_measurements:
        if m.object_id == cell_id:
            by_period.setdefault(m.period_start, {})[m.counter] = m.value
    values = [evaluate_kpi(kpi, cell_id, p, c).value for p, c in by_period.items()]
    assert all(v is not None for v in values)
    return sum(values) / len(values)  # type: ignore[arg-type]


def test_degraded_rrc_detected_against_truth() -> None:
    dataset = generate(11, "degraded_rrc", n_cells=60, periods=8)
    injected = {i["cell_id"] for i in dataset.truth["injected"]}
    assert len(injected) == 3
    for cell in dataset.network.cells:
        rate = mean_rrc_rate(dataset.measurements, cell.id)
        assert (rate < 90) == (cell.id in injected), (cell.id, rate)


def test_healthy_has_no_degraded_cells() -> None:
    dataset = generate(11, "healthy", n_cells=60, periods=8)
    assert all(
        mean_rrc_rate(dataset.measurements, c.id) > 97 for c in dataset.network.cells
    )


def test_pm_files_written_and_round_trip(tmp_path: Path) -> None:
    dataset = generate(5, "healthy", n_cells=7, periods=2)
    paths = write_pm_files(dataset.network, dataset.measurements, tmp_path)
    assert len(paths) == 3 * 2  # 3 nodes x 2 periods
    assert paths[0].name.startswith("A20260101.0000+0000-0015+0000_ENB001")

    counters = list(load_counters())
    expected = {
        (m.object_id, m.counter, m.period_start): m.value for m in dataset.measurements
    }
    seen = {}
    for path in paths:
        root = etree.parse(str(path)).getroot()
        types = {t.get("p"): t.text for t in root.iterfind(".//m:measType", NS)}
        assert list(types.values()) == counters
        begin = datetime.fromisoformat(
            root.find(".//m:fileHeader/m:measCollec", NS).get("beginTime")
        )
        for value in root.iterfind(".//m:measValue", NS):
            cell_id = value.get("measObjLdn").removeprefix("EUtranCellFDD=")
            for r in value.iterfind("m:r", NS):
                seen[(cell_id, types[r.get("p")], begin)] = float(r.text)
    assert seen == expected


def test_pm_output_deterministic(tmp_path: Path) -> None:
    for name in ("a", "b"):
        ds = generate(9, "degraded_rrc", n_cells=12, periods=2)
        write_pm_files(ds.network, ds.measurements, tmp_path / name)
    assert digest(tmp_path / "a") == digest(tmp_path / "b")


def test_validator_with_simple_schema(tmp_path: Path) -> None:
    xsd = tmp_path / "t.xsd"
    xsd.write_text(
        '<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">'
        '<xs:element name="a" type="xs:int"/></xs:schema>'
    )
    good, bad, broken = (
        tmp_path / "good.xml",
        tmp_path / "bad.xml",
        tmp_path / "broken.xml",
    )
    good.write_text("<a>1</a>")
    bad.write_text("<a>x</a>")
    broken.write_text("<a>")
    failures = validate_files([good, bad, broken], xsd)
    assert set(failures) == {"bad.xml", "broken.xml"}


@pytest.mark.skipif(not DEFAULT_XSD.is_file(), reason="run scripts/fetch_xsd.py first")
def test_pm_files_validate_against_3gpp_xsd(tmp_path: Path) -> None:
    dataset = generate(2, "degraded_rrc", n_cells=12, periods=2)
    paths = write_pm_files(dataset.network, dataset.measurements, tmp_path)
    assert validate_files(paths, DEFAULT_XSD) == {}


def test_start_must_be_timezone_aware() -> None:
    with pytest.raises(ValueError):
        generate(1, "healthy", n_cells=3, periods=1, start=datetime(2026, 1, 1))


def test_default_start_is_utc() -> None:
    assert generate(1, "healthy", n_cells=3, periods=1).start == datetime(
        2026, 1, 1, tzinfo=UTC
    )
