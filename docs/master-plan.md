# ranops: 4G RAN Ops Toolkit, Master Plan (v0.1)

This document replaces `ran_ops_toolkit_blueprint.md`. It is the single source of truth for scope, structure and milestones.

## 1. Goal and scope

**Goal:** a vendor-neutral 4G (LTE) RAN operations toolkit, Ericsson first, that produces a daily health and KPI report and a parameter drift audit, run through Ansible and AWX against a simulated network.

**In scope (v0.1)**
- Synthetic LTE network, 50-200 cells, seeded and deterministic
- Ericsson-style CLI mock (single multiplexed SSH server), 3GPP-style PM files, alarm feed
- Health check, KPI report, parameter audit: all read-only
- Python library and CLI first, then Ansible collection, Execution Environment, AWX

**Out of scope (v0.1):** 3G, 5G, Huawei (deferred behind adapter contract tests), config push and rollback (the mock parses `set` and rejects it), web UI, NetBox, Kubernetes, Open5GS/UERANSIM, Cython/PyArmor obfuscation, licence enforcement.

## 2. Decisions carried over from the blueprint review

| Blueprint item | Decision |
|---|---|
| 5G NR, Open5GS, UERANSIM, k3s | Dropped. They do not exercise Ericsson RAN ops work. Revisit only if a client asks. |
| Cython + PyArmor | Dropped. Premature, and unreadable code hurts a portfolio. Decide licensing and a public/private repo split later. |
| NETCONF/cmedit push | Deferred to v0.2 (safe change: pre-check, backup, apply, post-check, rollback). |
| FastAPI REST mock | Replaced by an SSH CLI mock, closer to real AMOS usage. |
| `$500k` product value | Removed. It was an assumption. |
| Flat `src/parser.py` | Replaced by the `ranops` package layout below. |
| Ansible `command:` calling Python | Replaced by an Ansible collection with real modules. |
| Hardcoded token | Secrets come from AWX credentials or environment only. |
| `apt-get` in EE | EE built with `ansible-builder` (base image is RPM-based). |

## 3. Architecture

```text
        AWX job templates / workflows
                    |
      Ansible collection (modules + roles)
                    |
            Python library  <-- CLI
    +---------------+---------------+
 core model        tools          adapters
 (canonical)   (health, KPI,    (ericsson now,
               param audit)      huawei later)
                    |
   Lab: synthetic network + mock node
   (SSH CLI mock, PM files, alarm feed)
```

Rules: tools call only the adapter interface. Vendor-specific names live only in `adapters/`. Every tool returns structured JSON first; HTML/CSV are rendered from it.

### Boundary rules (M2 and later)

- Generic 3GPP formats (for example TS 32.435 PM XML) are parsed in the vendor-neutral `sources/` layer (`sources/pm_3gpp_xml.py`, implementing `PmSource`). Adapters only map vendor-specific counter names and DNs to canonical types.
- Dependencies point one way: `lab/` may import `core`. `adapters/` and `tools/` never import `lab/`, and the mock node never imports adapter code, so adapter tests are not circular.
- The only contracts between the lab and the toolkit are the SSH dialect in `docs/mock-dialect.md`, the PM files, and the generator's `truth.json`.
- `cell_down` (disabled cell plus alarm) is required before M2 closes, so state and alarm parsing are exercised. `param_drift` follows in M3.
- The CLI calls tools like any other client.

## 4. Repository layout

```text
ran-ops-toolkit/
  README.md
  pyproject.toml
  .gitignore
  .github/workflows/ci.yml
  src/ranops/
    core/            # models, counter catalogue, KPI definitions, KPI evaluator
    sources/         # InventorySource, PmSource interfaces + lab/file implementations
    adapters/
      base.py        # RanAdapter interface
      ericsson/      # cli parser, MO mapper, PM reader
    tools/           # health_check.py, kpi_report.py, param_audit.py
    cli.py
  lab/
    generator/       # seeded network builder, scenarios (YAML), truth.json
    mock_node/       # asyncssh server (multiplexed node identities), PM + alarm writers
  baselines/         # versioned parameter baselines (YAML)
  collections/ranops/      # Ansible collection (M4)
  execution-environment/   # ansible-builder definition (M4)
  tests/
  docs/              # this plan, architecture, mock-dialect notes
```

## 5. Core model (pydantic)

- `Site`, `Node` (eNodeB: id, vendor, sw version, IP), `Unit`, `Cell` (id, band, EARFCN, PCI, TAC)
- `CellState`: admin state and operational state kept separate
- `Parameter` (scope: node or cell, name, value), `Baseline` (expected values with scope)
- `Alarm` (id, object, severity, type, probable cause, raised/cleared times)
- `Measurement` and `KpiSample` (cell, period, KPI, value, inputs)
- Counter catalogue in YAML (3GPP names); KPI definitions as formulas over counters, evaluated by a restricted evaluator (no `eval`)

## 6. Adapter interface

```python
class RanAdapter(Protocol):
    def get_inventory(self) -> list[Node]: ...
    def get_cell_states(self, node: Node) -> list[CellState]: ...
    def get_parameters(self, node: Node, names: list[str]) -> list[Parameter]: ...
    def list_alarms(self, node: Node) -> list[Alarm]: ...
    def read_pm(self, source: PmSource, period: Period) -> list[Measurement]: ...
```

`InventorySource` (lab, CSV, later NetBox or vendor export) and `PmSource` are separate from the adapter. A shared contract test suite runs against every adapter, which is what makes the later Huawei adapter cheap.

## 7. Lab design

- **Generator:** seeded builder. Scenarios as YAML: `healthy`, `cell_down`, `pci_conflict`, `degraded_rrc`, `param_drift`. Emits `truth.json` listing exactly what was injected, so tests assert detection against ground truth.
- **Mock node:** one asyncssh server multiplexing node identities. Small command set only (e.g. cell state listing, `get` for parameters, alarm listing). `set` is parsed and rejected as read-only. Output styled from your own knowledge and public material only.
- **PM writer:** 15-minute files in a 3GPP-style structure, values shaped by the scenario.
- **Alarm feed:** new, changed, cleared lifecycle.
- **Mock fidelity:** the mock is only as good as recollection of real output. Keep a `docs/mock-dialect.md` listing each command and its assumed format so it can be reviewed by someone who works with the real systems.

## 8. Tools (v0.1)

| Tool | Input | Output |
|---|---|---|
| Health check | adapter, nodes | cell state, active alarms, summary (JSON + HTML) |
| KPI report | PM source, period | KPIs per cell, thresholds, worst-cell list |
| Param audit | adapter, baseline | drift list: cell, parameter, expected, actual |

## 9. Milestones

| # | Milestone | Done when |
|---|---|---|
| M0 | Repo and tooling | Repo created, CI green on an empty test |
| M1 | Model and lab | Generator produces a valid network and PM files for `healthy` and `degraded_rrc`; validator passes; output is deterministic per seed |
| M2 | Ericsson adapter and mock CLI | `get_cell_states` and `get_parameters` work end to end against the mock |
| M3 | Tools and CLI | Each scenario is correctly detected, checked against `truth.json` |
| M4 | Ansible | Collection with modules and roles, EE image built with `ansible-builder`, inventory from the lab |
| M5 | AWX | Scheduled daily workflow produces the day's report |
| M6 | Demo packaging | README, architecture diagram, recorded demo, one-page case study |

## 10. Engineering ground rules

- Python 3.11+, pydantic, pytest, ruff, mypy (strict on `core/`)
- CI on every push: lint, type check, tests
- Public material only for mock dialects. Nothing from licensed vendor documentation (CPI, real MO models, ENM/AMOS software)
- Secrets never in the repo; AWX credentials or environment variables
- Private GitHub repo to start; choose a licence and any public/private split deliberately before publishing
- Hold the v0.1 list: every extra command, counter or vendor is about a week

## 11. Dev machine setup (M0-M1)

```bash
# prerequisites: Python 3.11+, git
git init ran-ops-toolkit && cd ran-ops-toolkit
python3 -m venv .venv && source .venv/bin/activate
pip install --upgrade pip
pip install pydantic pyyaml pytest ruff mypy
pip install asyncssh jinja2   # needed from M2/M3
```

Skip for now: Docker, minikube, Cython. Add `ansible-core` and `ansible-builder` at M4.

## 12. Risks

- **Mock fidelity:** validate against someone with real-system experience.
- **Real-data gap:** test parsers on a small anonymised real sample as early as possible.
- **Scope creep:** the out-of-scope list in section 1 is binding for v0.1.

## 13. Next actions

1. M0: create the private repo, add README, `pyproject.toml`, `.gitignore` and CI.
2. M1: write the core pydantic models and counter catalogue.
3. M1: build the seeded generator with `healthy` and `degraded_rrc`, plus `truth.json`.
4. M1: PM writer and validator.
