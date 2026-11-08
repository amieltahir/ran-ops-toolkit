# ranops: 4G RAN Ops Toolkit

A vendor-neutral LTE RAN operations toolkit, Ericsson first. The v0.1 goal is
to produce daily health and KPI reports and parameter drift audits against a
simulated network, using a Python library and CLI, then Ansible and AWX.

The project is at **M0: repository and tooling**. The simulator, adapters,
reports, CLI, Ansible collection and AWX integration are planned, not yet
implemented. See the [master plan](docs/master-plan.md) for scope and
milestones, and the [architecture](docs/architecture.md) for boundaries.

## Development setup

Requires Python 3.11+ and Git.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
pre-commit install
```

Run the same checks as CI:

```bash
ruff check .
ruff format --check .
mypy src/ranops/core
pytest
pre-commit run --all-files
```

The repository is private initially. A licence and any public/private split
will be chosen deliberately before publishing. Do not commit credentials,
licensed vendor documentation or proprietary software.
