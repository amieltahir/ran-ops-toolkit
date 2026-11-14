# Runbook: set up and run ranops locally

Current scope: the core library and the lab data generator. There is no server, mock node or CLI to start yet (M2 and M3).

## 1. Get the code

```bash
git clone https://github.com/amieltahir/ran-ops-toolkit.git   # first time
cd ran-ops-toolkit
git checkout main && git pull                                  # later
```

## 2. Create the environment

Requires Python 3.11+.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

If `python3 -m venv` fails with an `ensurepip` error, or Python crashes on `import ctypes`, use `uv` instead and point it at a working interpreter (for example `/usr/bin/python3.13`):

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
uv venv --seed --python /usr/bin/python3.13 .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
```

## 3. Check the environment

```bash
make check
```

Expect ruff, mypy and pytest to pass (69 passed, 1 skipped; the skip is the XSD test until you fetch the schema).

## 4. Generate lab data

```bash
python -m lab.generator --scenario healthy --seed 42 --cells 60 --out lab_out
python -m lab.generator --scenario degraded_rrc --seed 42 --out lab_out_rrc
python -m lab.generator --scenario cell_down --seed 42 --out lab_out_down
```

Each run writes to the `--out` directory:

| File | Content |
|---|---|
| `network.json` | sites, nodes, cells |
| `state.json` | cell admin/operational states and alarms |
| `truth.json` | exactly what was injected |
| `pm/*.xml` | 15-minute PM files, one per node and period |

Same seed and arguments always give identical output. `lab_out*` is gitignored.

## 5. Validate PM files against the 3GPP schema (optional)

The PM XML layout is not yet verified against the real schema. Get `measCollec.xsd` from TS 32.435 (public 3GPP material), then:

```bash
python scripts/fetch_xsd.py --file <path-to-xsd-or-zip>     # or --url <url>
python -m lab.generator --scenario healthy --out lab_out
```

The generator then reports `schema validation: N/N files valid`. Send any errors back so the writer can be fixed.

## 6. Day-to-day

```bash
make check   # same steps as CI
make fix     # auto-format and apply safe lint fixes
```
