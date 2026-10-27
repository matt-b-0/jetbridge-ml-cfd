# Reproducible experimental interpolation benchmark

## Scope and source
The first benchmark reads replicate air-speed means from FAA/NRC JetBridge_2026/03-Averages, default pattern V-S01-A-*-HN-*.txt. It does not use 04-Summary files, CFD, HVAC flow constraints, or ML. Preserve the extracted dataset outside the repository.

The data dictionary specifies: -9999 is missing (ID 1); air-speed averages use entire recordings (ID 5); averaged coordinates are absolute metres (ID 55); speeds are m/s (ID 79). Thus no feet conversion or bridge-floor offset is added to these coordinates. Filename station labels remain feet metadata; source z is retained. Periods.csv defines stable intervals but is only hashed for provenance here, not applied to published averages or used to recalibrate CFD flow. Recomputing stable-window raw statistics is separate work.

## Design
- Separate 2D x/y fit per replicate and station. No replicate, station or scenario is pooled.
- Leave one exact coordinate location out, in sorted coordinate order. All observations at a location are grouped by the splitter. Missing speed observations are excluded from training and scoring, but counted in the manifest.
- All three methods use identical training/test rows. Source row indices and train rows are saved in predictions.csv, with run IDs, coordinates, predictions, missing-target and convex-hull flags.
- Methods: nearest in metre Euclidean distance; piecewise linear triangulation; thin-plate-spline RBF with degree 1 and zero smoothing. No hyperparameter tuning, clipping or coordinate standardisation.
- Linear returns missing predictions outside its training hull. There is no hidden nearest fallback. Report coverage, common-hull errors and extrapolation errors separately. Do not rank methods by their differently covered all-point metrics.
- Replicates reuse the same coordinate folds where layouts match. Each fit sees only the other locations from that replicate, so no replicate measurement at a test location enters that fit.
- This is exploratory spatial cross-validation, not an untouched final test. It assesses withheld locations within observed planes, not generalisation to new configurations or simultaneous 3D flow.
- Scalar speeds are never integrated as exact signed volume flux. CFD virtual-sensor tests and GPR remain separate subsequent stages.

## Reproduce on Ubuntu / WSL
Prefer a Linux filesystem checkout rather than a OneDrive-mounted editable installation. On this machine pip editable installation on OneDrive failed with Operation not permitted; a Linux working copy succeeded.

In a Linux checkout:
```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-benchmark.txt
python -m pip install --no-deps -e .
python -m pytest -q
python -m jetbridge_ml.benchmark \
  --dataset /mnt/c/Users/mattb_ar68ij9/Downloads/dot_92577_DS3/JetBridge_2026 \
  --output data/processed/interpolation_run_001
```
Substitute your own dataset path. Choose a new output directory on each run; the CLI refuses to overwrite an existing directory. To limit to the starter replicate, add:
```bash
--pattern 'V-S01-A-10-HN-1.txt'
```
No random split or random seed is needed. Prediction results are deterministic with the tested environment; runtime, creation time, absolute paths, Git status and rendered images may vary across machines.

## Outputs
- observations.csv: parsed replicate observations, never silently averaged across runs.
- predictions.csv: held-out predictions, exact training source rows, hull membership and combined fit/prediction seconds.
- metrics.csv: per-run RMSE, MAE, signed bias, coverage and negative-prediction count for common_hull, outside_hull and all.
- station_metrics.csv: mean per-run errors and run counts, separated by station, layout size, method and subset.
- manifest.json: input SHA-256 including dictionary/period/boundary files, source-code SHA-256, selection and settings, Python/package versions, Git commit and dirty state when available. Git fields are null outside a Git checkout; code hashes still identify the implementation.
- environment.txt: full pip freeze from the run; requirements-benchmark.txt pins the tested dependency environment without machine-specific editable paths.
- common_hull_rmse.png and station_rmse.png: aggregate and station-separated diagnostic plots.

Outputs live under ignored data/processed or an external folder. Raw datasets are not copied, modified, committed or pushed. See the initial results note for measured results and limitations.

## Current demo and quality workflow on 27 October 2026
The repository now includes the attributed study input subset and compact archived numerical evidence. Use the root run_all.py driver and docs/LIVE_DEMO.md for one-clone execution; older commands above describe the original research runs. Static checking uses python -m ruff check src tests run_all.py; numerical tests use python -m pytest -q; API documentation uses python -m pdoc jetbridge_ml -o docs/html. See docs/DEVELOPMENT.md for scope and limitations. Live/full execute fresh isothermal CFD in new output folders; archived unconverged thermal evidence remains explicitly separate.
