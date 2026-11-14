"""Command line: ``python -m lab.generator --scenario healthy --seed 42 --out lab_out``."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from lab.generator.build import generate
from lab.generator.network import validate_network
from lab.generator.pm_validator import DEFAULT_XSD, validate_files
from lab.generator.pm_writer import write_pm_files
from lab.generator.scenarios import available_scenarios


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="lab.generator", description=__doc__)
    parser.add_argument("--scenario", default="healthy", choices=available_scenarios())
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--cells", type=int, default=60)
    parser.add_argument("--periods", type=int, default=96, help="15-minute periods")
    parser.add_argument("--out", type=Path, default=Path("lab_out"))
    parser.add_argument(
        "--xsd",
        type=Path,
        default=None,
        help=f"validate PM files against this XSD (default {DEFAULT_XSD} if present)",
    )
    args = parser.parse_args(argv)

    dataset = generate(args.seed, args.scenario, args.cells, args.periods)
    errors = validate_network(dataset.network)
    if errors:
        print("network invalid:", *errors, sep="\n  ", file=sys.stderr)
        return 1

    out: Path = args.out
    out.mkdir(parents=True, exist_ok=True)
    network = {
        "sites": [s.model_dump(mode="json") for s in dataset.network.sites],
        "nodes": [n.model_dump(mode="json") for n in dataset.network.nodes],
        "cells": [c.model_dump(mode="json") for c in dataset.network.cells],
    }
    (out / "network.json").write_text(json.dumps(network, indent=2) + "\n", "utf-8")
    state = {
        "cell_states": [s.model_dump(mode="json") for s in dataset.cell_states],
        "alarms": [a.model_dump(mode="json") for a in dataset.alarms],
    }
    (out / "state.json").write_text(json.dumps(state, indent=2) + "\n", "utf-8")
    (out / "truth.json").write_text(json.dumps(dataset.truth, indent=2) + "\n", "utf-8")
    paths = write_pm_files(dataset.network, dataset.measurements, out / "pm")
    print(f"wrote {len(paths)} PM files and network/state/truth JSON to {out}")

    xsd = args.xsd or (DEFAULT_XSD if DEFAULT_XSD.is_file() else None)
    if xsd is None:
        print("XSD not found: PM files NOT schema-validated (run scripts/fetch_xsd.py)")
        return 0
    failures = validate_files(paths, xsd)
    for name, file_errors in failures.items():
        print(f"INVALID {name}", *file_errors, sep="\n  ", file=sys.stderr)
    print(f"schema validation: {len(paths) - len(failures)}/{len(paths)} files valid")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
