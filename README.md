# ranops: 4G RAN Ops Toolkit

A vendor-neutral LTE RAN operations toolkit, Ericsson first. The v0.1 goal is
to produce daily health and KPI reports and parameter drift audits against a
simulated network, using a Python library and CLI, then Ansible and AWX.

The project is in **M1 (model and lab)**: the core model, KPI evaluator and a
seeded lab generator exist. Adapters, the mock node, reports, CLI, Ansible
collection and AWX integration are planned. See the [master plan](docs/master-plan.md) for scope and
milestones, and the [architecture](docs/architecture.md) for boundaries.

## Development setup

Requires Python 3.11+ and Git.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

Run the same checks as CI with `make check` (or `make fix` to auto-format).
Generate lab data with `python -m lab.generator --scenario degraded_rrc`.

The repository is private initially. A licence and any public/private split
will be chosen deliberately before publishing. Do not commit credentials,
licensed vendor documentation or proprietary software.
