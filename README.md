# Jet Bridge CFD + Numerical Interpolation + Machine Learning

Starter repository for MMA3001 work comparing reconstruction from sparse FAA/NRC jet-bridge measurements against OpenFOAM reference fields.

**Status:** first experimental interpolation benchmark implemented and tested. An isolated OpenFOAM baseline converged with a mesh passing checkMesh; physical validation and mesh sensitivity remain outstanding. See docs/baseline_run_2026-10-24.md and docs/interpolation_initial_results.md. The repository CFD inputs retain the documented compatibility/geometry issues.

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

## Experimental interpolation benchmark

The first reproducible benchmark compares nearest, linear and RBF interpolation with held-out sensor locations. See [the workflow](docs/interpolation_workflow.md) for environment setup, dataset-path commands, saved manifests, coverage reporting and limitations. Raw FAA data remains external to Git.


CFD comparison figures can be regenerated with the workflow in [docs/cfd_comparison_visuals.md](docs/cfd_comparison_visuals.md). It separates the matched 10 ft case from exploratory cross-station differences.


A separate cold-supply thermal trial and zero-gravity control are documented in [docs/thermal_case_results.md](docs/thermal_case_results.md). The buoyant runs have not passed convergence checks and are not validated reference fields.


The [course-aligned numerical stability study](docs/numerical_stability_study.md) compares FTCS, implicit Euler, Crank–Nicolson, relaxation, and actual sensor-layout noise amplification. It also audits existing CFD convergence without claiming a cause of the thermal failure.


The trained CFD virtual-sensor SVR, interpolation comparison, and optimization error graphs are documented in [docs/cfd_svr_benchmark.md](docs/cfd_svr_benchmark.md).

A collection of 16 report figures for the isothermal baseline, zero-gravity thermal control and provisional buoyant snapshot is described in [docs/report_figures.md](docs/report_figures.md), including PNG/PDF exports, captions and reproducibility commands.
