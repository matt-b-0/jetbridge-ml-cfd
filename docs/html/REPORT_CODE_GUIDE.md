# Code behind the submitted report

This is the GitHub-readable version of the short HTML source documentation. The exact [submitted PDF](../report/MMA3001_Jet_Bridge_FinalSubmission.pdf) is retained unchanged.

**Question:** can sparse measurements reconstruct jet-bridge speed, and does SVR improve on conventional interpolation?

**Workflow:** read measurements → hide one sensor → fit retained sensors → predict the hidden speed → compare errors.

RBF has the lowest mean per-run common-support RMSE (0.04959 m/s), compared with SVR (0.05774 m/s). Its advantage concentrates at 58 ft; station and layout density are confounded. The 360 common supported targets are distinct from the physical hull area. CFD reconstruction and experimental prediction remain separate comparisons.

## Six functions to understand

### Read the measurements: `read_speed_average`

- **Input:** One FAA averaged-data text file.
- **Output:** A table of x, y, z in metres, speed in m/s and run identifiers.
- **Purpose:** Checks the file structure, units and coordinates. Converts the -9999 missing-speed marker to NaN; invalid negative/infinite speeds are rejected.

Report p. 2. [Open actual source](../../src/jetbridge_ml/data_processing/faa.py#L9).

### Apply an interpolation method: `predict_plane`

- **Input:** A method name, retained sensor coordinates and speeds, and query coordinates.
- **Output:** One predicted speed per query; linear gives NaN outside the sensor hull.
- **Purpose:** Chooses nearest neighbour, linear or thin-plate RBF. It uses the coordinates supplied by the caller; the report workflow supplies training-only standardised coordinates.

Report p. 3. [Open actual source](../../src/jetbridge_ml/interpolation/plane.py#L8).

### Choose SVR settings: `select_plane_svr`

- **Input:** Training coordinates and speeds, with optional location groups and parameter grid.
- **Output:** A fitted SVR, selected settings, search results and split/scaler audit.
- **Purpose:** Uses three inner folds. Scaling is fitted inside each training fold. The outer hidden sensor must already have been excluded by the caller.

Report p. 3. [Open actual source](../../src/jetbridge_ml/machine_learning/selection.py#L11).

### Predict sensors that were hidden: `evaluate_experimental_plane`

- **Input:** One experimental run; an optional SVR search grid.
- **Output:** Held-location predictions, parameter-search records and split/scaler audits.
- **Purpose:** Removes one location before tuning, predicts it with all five methods, and repeats for every location. Each experimental run is fitted separately.

Report p. 3. [Open actual source](../../src/jetbridge_ml/experimental_svr.py#L23).

### Calculate prediction error: `regression_metrics`

- **Input:** Reference speeds and predictions at the same supported locations.
- **Output:** RMSE, MAE and signed bias, all in m/s when the inputs are m/s.
- **Purpose:** Computes prediction minus observation. Rejects empty, mismatched or non-finite arrays. Positive bias means overprediction.

Report p. 4. [Open actual source](../../src/jetbridge_ml/validation/metrics.py#L5).

### Compare methods fairly: `summarize`

- **Input:** The table of held-location predictions and hull flags.
- **Output:** Per-run method errors and coverage for inside, outside and all targets.
- **Purpose:** Keeps unsupported queries visible in coverage counts. The report then averages the per-run errors equally over runs; it does not pool every error into one RMSE.

Report p. 4. [Open actual source](../../src/jetbridge_ml/benchmark.py#L60).

## Six core checks

Open [test_core.py](../../tests/test_core.py) and run `PYTHONPATH=src python -m pytest -v` from the repository root. For the talk, explain the test showing that opposite signed errors cancel in bias while RMSE and MAE remain positive. [Test instructions](../../tests/README.md) cover all six cases.

Report pp. 6–9 support the main comparison with separate CFD, sensitivity and timing evidence. Convergence does not establish physical agreement; the thermal extension remains unconverged.

The submitted report's 82-test count is its original development snapshot. The current default is six core cases, with the wider regression collection retained for development. Scientific results are unchanged.
