# Codex repository instructions — Jet Bridge CFD + ML

## Purpose and reading order
This repository supports an MMA3001 numerical-methods / ML investigation of sparse, planar jet-bridge ventilation measurements and OpenFOAM results.
Before substantive changes, read `PROJECT_CONTEXT.md`, `README.md`, and the README in any `cfd/cases/` directory being modified. Treat `docs/assumptions.md` and `docs/ai_usage_log.md` as living records.

## Scientific invariants
- Keep **experimental measurements**, **OpenFOAM output**, and **ML predictions** separate. Never present CFD as experimental ground truth.
- The FAA SWEMA hot-sphere observations are **air-speed magnitudes**, not three signed components. Do not integrate them as an exact normal-volume flux without an explicit, qualified flow-direction assumption.
- `Q.FS` is the HVAC **supplied volumetric flow**, not necessarily the flow through every plane of a potentially leaky physical bridge.
- Use SI units in software; document source units and conversions. Preserve the original x/y/z coordinate frame (x width, y height above laboratory floor, z bridge length).
- Never use test data to tune hyperparameters or calibrate a flow constraint. For multiple observations at a location, withhold entire sensor locations (and keep replicate leakage out of validation).
- For metrics, report local error at held-out observations separately from CFD-field reconstruction error and global flow-rate discrepancy.
- Report changes to model physics, turbulence treatment, inlet/outlet assumptions, mesh, or sensor mapping. A numerically conserved CFD solution is not by itself experimentally validated.
- Preserve original raw files unchanged. Treat missing-value sentinels (e.g. -9999) as missing, never as valid physical readings.

## Source tree and ownership
- `cfd/cases/`: OpenFOAM `0`, `constant`, `system`, solver scripts, and case-specific documentation. Do not reorganize without preserving runnable cases.
- `src/jetbridge_ml/data_processing/`: dataset readers and coordinate/units checks.
- `src/jetbridge_ml/interpolation/`: classic interpolation methods.
- `src/jetbridge_ml/machine_learning/`: fitted statistical / ML models.
- `src/jetbridge_ml/validation/`: statistics and reproducible validation splits.
- `src/jetbridge_ml/cfd_interface/`: exported CFD fields, sampling/parsing (not OpenFOAM setup itself).
- `tests/`: independent numerical unit tests and regression tests.
- `docs/`: research rationale, open questions, limitations, attribution and AI-use reflection.

## Engineering workflow
1. State scope and planned files for each meaningful change; keep changes modular.
2. Validate Python edits with `python -m pytest -q`; run examples when modifying I/O or models.
3. For CFD edits, run `blockMesh`, `checkMesh`, solver and flux/probe checks **when OpenFOAM is available**. Otherwise mark the case **untested**: don't invent results.
4. Use NumPy-style docstrings for public Python functions. Comment assumptions, not obvious syntax.
5. Keep README/reproducibility commands current; add tests for fixes and features.
6. Don't commit generated meshes, time folders, `.venv`, logs, or large raw datasets to Git.
7. Do not push to GitHub, remove data, or modify the approved research scope without explicit user permission.
8. Record substantive AI assistance, checks and rejected suggestions in `docs/ai_usage_log.md`; the student owns the scientific choices and validation.

## Current goals
- Reproduce the starter OpenFOAM case for `S01-A-10-HN-1` with matched supplied `Q.FS` and 12 experimental sensor locations.
- Build a reliable parser and quantitative comparison pipeline.
- Compare nearest/linear/RBF-style methods with a suitable ML baseline such as GPR under spatially held-out validation.
- Investigate the reported upstream/high vs downstream/low discrepancy without assuming its cause.
