# Jet Bridge CFD + Numerical Interpolation + Machine Learning

Starter repository for MMA3001 work comparing reconstruction from sparse FAA/NRC jet-bridge measurements against OpenFOAM reference fields.

**Status:** working scaffold. Only the original CFD input case has been packaged; it has not been solver-validated. The Python modules contain small demonstrated utilities, *not* a finished analysis pipeline.

Read `PROJECT_CONTEXT.md` for experiment background and `AGENTS.md` for Codex rules. Always read the case README before attempting CFD.

## Layout

```
AGENTS.md                     Codex-specific working instructions
PROJECT_CONTEXT.md            research decisions / dataset caveats
cfd/cases/...                 executable OpenFOAM cases (separate from Python package)
src/jetbridge_ml/
  data_processing/            input readers, coordinate mapping
  interpolation/              traditional numerical methods
  machine_learning/           learned surrogates, hyperparameters
  validation/                 withheld-location splits, metrics, physics checks
  cfd_interface/              import/export/sampling CFD fields
examples/                     small runnable demonstration
scripts/                      orchestration scripts (future)
tests/                        unit tests
data/raw/                     user's large raw dataset (ignored by Git)
data/processed/               derived larger datasets (ignored by Git)
docs/                         AI reflection, assumptions and research notes
```

## Python setup (WSL/Linux)

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
python -m pytest -q
python examples/compare_nearest.py
```

`pip install -e` installs this package in **editable mode**, so imports such as `from jetbridge_ml.interpolation import nearest_neighbor` work across the repo without copying scripts between folders. VS Code should select `.venv/bin/python` for the interpreter.

## OpenFOAM CFD

The starter case is in `cfd/cases/empty_bridge_s01_a_10_hn_1/`.

```bash
cd cfd/cases/empty_bridge_s01_a_10_hn_1
python3 scripts/verify_setup.py
blockMesh
checkMesh
simpleFoam
python3 scripts/compare_probe_speeds.py
```

These are **instructions**, not evidence they ran; source your OpenFOAM environment and confirm solver/BC compatibility with your installed version. Never publish or use an unverified CFD result as experimental truth.

## GitHub

Keep **this folder** as the single Git repository. `cfd/` and `src/` are ordinary directories/modules, not separate Git repositories and not Git submodules. Commit source and small reproducibility artifacts; ignore meshed/time-series solver output and giant raw data files. Add an appropriately reviewed `LICENSE` before public release.

Suggested initial commands:

```bash
git init -b main
git add .
git commit -m 'Initial reproducible Jet Bridge project scaffold'
```

Then use VS Code Source Control > Publish to GitHub or use `git remote add origin ...` / `git push`. Publish only after reviewing original-data redistribution rights.

## First steps
1. Reconfirm `.venv` tests locally.
2. Confirm the CFD case runs on your OpenFOAM version; record `checkMesh`, convergence, fluxes and probe outputs.
3. Implement robust raw FAA parsers and validation splits.
4. Compare baseline interpolation methods and GPR on identical held-out locations.
5. Add virtual CFD-sensor experiments and report limitations.
