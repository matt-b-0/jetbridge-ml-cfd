# Four-workstream results — 24 October 2026

This first completed analysis pass connects experimental prediction, CFD reconstruction, source-data auditing and thermal numerical diagnostics. Results remain separate: agreement with a CFD field is not agreement with physical measurements.

## 1. Experimental interpolation versus SVR

Thirty-six S01-A-HN replicate files provide 504 sensor means. Each replicate is fitted separately. An outer leave-one-location-out evaluation withholds a sensor before any scaling or hyperparameter selection. Inner three-fold grouped-location CV selects RBF-kernel SVR from 12 fixed combinations: C=[0.1,1,10], gamma=[0.1,1], epsilon=[0.002,0.01] m/s. The outer training-only StandardScaler is shared by nearest, linear and thin-plate RBF interpolation. No CFD targets, supplied-flow constraint or other replicate readings enter these fits.

| Method | Common supported mean per-run RMSE (m/s) | Outside-hull mean per-run RMSE (m/s) |
| --- | ---: | ---: |
| Nearest | 0.071293 | 0.090410 |
| Linear | 0.055241 | Unsupported |
| RBF | 0.049590 | 0.067264 |
| SVR | 0.057741 | 0.079988 |

There are 360 common supported and 144 outside-hull targets. RBF outperforms the selected SVR procedure in this evaluation; ML complexity does not automatically improve sparse experimental reconstruction. The earlier CFD SVR/RBF near tie therefore does not transfer directly to the measurements. This is a result worth reporting, not a reason to tune on test errors.

The inner grid is bounded, not an exhaustive search. No claim is made that every possible SVR configuration is inferior. Results are nested cross-validation estimates of this tuning procedure, not a new external test. Replicates/stations share a physical apparatus and are not independent physical systems. Pearson r and R² are recorded per run alongside RMSE/MAE/bias; undefined correlations remain missing. The original exploratory benchmark used unscaled metre distances, so its values are not directly interchangeable with these standardized baselines.

The source air-speed means describe whole records, including sequential measurement layouts. Keeping fits independent prevents replicate leakage, but does not make the 24-point inlet layout simultaneous. The 58 ft means combine A/B half-layout measurements.

Outputs: `data/processed/four_workstreams/experimental_nested/`. Figures: experimental_nested_errors, experimental_parity and experimental_spatial_errors. The search and nested_split_audit CSVs retain inner indices, outer training source rows and scaler means. Repeated full runs reproduced prediction and metric tables exactly.

## 2. CFD sensor density and placement

Four isothermal sections (16,28,40,52 ft) are reconstructed using 6,12,24 or 48 virtual sensors. Candidate labels come from the existing 32×48 section grids; evaluation uses disjoint 40×60 grids. Both use cellPoint sampling from the same converged iteration-237 numerical solution. This is a within-plane 2D study, separate from the earlier 3D station-held-out surrogate.

Three geometric layout families are compared: interior rectangles, boundary-heavy rectangles, and hybrid interior-plus-perimeter designs. Selection uses coordinates only, with deterministic handling of equidistant candidate points. SVR is tuned within the retained virtual sensors only. Evaluation points do not enter scaling or hyperparameter selection. All layouts are scored on the same fixed core (intersection of training hulls), as well as their own supported region, outside region and full section. Linear full-section rows have incomplete coverage and must not be ranked against fully covered methods without restriction.

Example full-section mean plane RMSE:

| Layout | Sensors | RBF (m/s) | SVR (m/s) |
| --- | ---: | ---: | ---: |
| Interior | 24 | 0.033883 | 0.033648 |
| Boundary-heavy | 24 | 0.048397 | 0.056783 |
| Hybrid | 24 | 0.026579 | 0.028435 |
| Boundary-heavy | 48 | 0.028697 | 0.031310 |
| Hybrid | 48 | 0.035615 | 0.038065 |

Boundary coverage can help, but merely moving a sparse array to the walls loses interior information. The 24-point hybrid improves full-section errors relative to 24 interior points; the 48-point hybrid is worse than the 24-point hybrid. The arrays are independently placed, not nested additions, so count and spatial arrangement both change. These results do not establish monotonic improvement with sensor count or an optimal layout.

The study is exploratory: prior wall errors motivated the designs, and hybrid layouts were added after the boundary-heavy arrays performed poorly. The evaluation field is reused, so none of these results is a new untouched final test. A future predeclared layout comparison on another numerical operating case would test transferability.

Outputs: `data/processed/four_workstreams/sensor_design/`, including sensor_count_errors, sensor_placement_examples, selected coordinates, search tables, coverage-aware metrics and compressed point predictions.

## 3. Matched CFD–raw-data audit

For S01-A-10-HN-1, the entire and stable intervals are identical: 1744997159–1744997453 s. All 12 raw sensor means reproduce the published three-decimal means within rounding (largest difference 0.000494331 m/s). Per-sensor timestamps are retained rather than treating asynchronous channels as simultaneous. Raw temporal standard deviations are not uncertainties of the mean.

The 58 valid HVAC supply readings give 0.533865517241 m³/s, matching the prescribed 0.533865517 m³/s to input rounding. Supply/lab means are 23.400/23.288 °C; the baseline is approximately isothermal. Source pressure difference is recorded, not treated as an exactly reproduced CFD boundary.

| Sampling at published coordinates | Speed RMSE (m/s) | Bias (m/s) | Pearson r |
| --- | ---: | ---: | ---: |
| Cell | 0.040473 | +0.037527 | 0.506640 |
| CellPoint | 0.039769 | +0.036674 | 0.488590 |

The small sampling change does not remove the positive bias. Error-height Pearson r is approximately 0.618 for cellPoint, a descriptive pattern over just 12 positions, not a demonstrated mechanism. Correlation does not establish agreement or explain the bias.

The raw CSV headers use nominal local inches, whereas published average files contain absolute metre coordinates. Differences are up to 2.85 mm in x, 2.00 mm in z and 3.65 mm in local height relative to the actual CFD floor. These are documented; published absolute coordinates remain the sampling authority. No floor offset is added twice and no raw/source coordinates are altered.

The inventory contains 42 HVAC period records for the 36 averages: the six 58 ft files each have separate A/B records. All 42 have equal entire/stable windows. Their measured supply means range approximately 433.3–535.4 L/s, while the CFD uses 533.9 L/s. Thus one solution should not be presented as a matched simulation of every station run. No root cause of the CFD–experiment discrepancy has been established.

Outputs: `data/processed/four_workstreams/matched_audit/`. Figures: matched_sampling_and_height, raw_measurements_and_cfd, boundary_and_raw_average_audit. Tables preserve raw mean checks, nominal-vs-published coordinates, valid counts and independent HVAC windows.

## 4. Bounded thermal convergence investigation

An isolated continuation copied saved buoyant field 967 into `/home/mattb/projects/jetbridge-thermal-continuation-20261024`. Physical boundaries, geometry, schemes and relaxation are byte-identical to the restart source. Only the start/end iteration controls and speed-bound diagnostics changed. checkMesh again reported Mesh OK. The original source hashes were checked after the run and remain unchanged.

The run advanced 1,000 additional SIMPLE iterations to saved field 1967 (about 342 s wall time). It did not converge:

- Final first pressure residual: 0.030011; temperature residual: 0.000259, versus criteria 1e-5 and 1e-6.
- Maximum per-probe temperature range over [1867,1967]: 0.135002 K; fails the predeclared 0.01 K screening threshold.
- Temperature remains within 294.439286–297.525 K, but maximum speed increased to 5.099652 m/s.
- Relative inlet/outlet imbalance is 1.23213e-6 (0.0001232%), yet residual and stationarity checks fail.

This demonstrates why flux balance and bounded temperature alone do not establish convergence. No experimentally fitted settings or ML training use this continuation. The initial divergent run, snapshot 967 and continuation 1967 remain unsuitable as trusted numerical reference fields. The earlier report figures deliberately remain labelled with their original snapshot 967; they were not silently replaced by the continuation.

The earlier log extends to iteration 1000, whereas the restart begins from saved 967. Histories overlap over 967–1000 and are displayed separately, not merged into one exact trajectory. SIMPLE iteration is not physical time. The 0.01 K screen is a numerical diagnostic choice, not a measured tolerance or physical validation criterion.

The next thermal task would require a separate controlled numerical investigation, not simply more identical steady iterations. Keep it bounded so experimental/CFD reconstruction remains the main project contribution.

Outputs: `data/processed/four_workstreams/thermal_continuation/`, with thermal_continuation_diagnostics and audit.json. Source case and zero-gravity control remain unchanged.

## Reproduce

Use the pinned WSL Python environment in requirements-benchmark.txt. Set REPO and export PYTHONPATH as in report_figures.md. Let DATA point to JetBridge_2026. Every --output path must be new. The input candidate/reference tables come from the already documented report_figures and virtual_sensors workflows.

```bash
python -m jetbridge_ml.experimental_svr --dataset "$DATA" \
  --mesh "$REPO/cfd/cases/empty_bridge_s01_a_10_hn_1/system/blockMeshDict" \
  --output /home/mattb/projects/new-experimental-nested
python -m jetbridge_ml.sensor_design_study \
  --candidates "$REPO/data/processed/report_figures/sampled_iso.csv" \
  --reference /home/mattb/projects/jetbridge-virtual-samples-20261024/dense_test.csv \
  --output /home/mattb/projects/new-sensor-design
python -m jetbridge_ml.cfd_interface.matched_audit --dataset "$DATA" \
  --case /home/mattb/projects/jetbridge-baseline-20261024 \
  --output /home/mattb/projects/new-matched-audit
python "$REPO/cfd/cases/thermal_bridge_s01_ac_10_hn_1/scripts/continue_saved.py" \
  --case /home/mattb/projects/jetbridge-thermal-stabilized-s01-ac-10-hn-1 \
  --time 967 --iterations 1000 --output /home/mattb/projects/new-thermal-continuation
# Source OpenFOAM, then run checkMesh and buoyantBoussinesqSimpleFoam in
# the new continuation directory, saving log.checkMesh and log.solver.
python -m jetbridge_ml.cfd_interface.thermal_audit \
  --restart-source /home/mattb/projects/jetbridge-thermal-stabilized-s01-ac-10-hn-1 \
  --continuation /home/mattb/projects/new-thermal-continuation \
  --output /home/mattb/projects/new-thermal-audit
```

## Checks and report direction

All 62 tests pass. New checks cover nested outer-target exclusion, inner scaler isolation, identical-location grouping, independent replicate rejection, all twelve density/placement designs, translation-stable geometric tie-breaking, raw units/sentinels/asynchronous timestamps, and restart probe handling. Experimental repeated runs agree exactly; final density numerical tables also agree on repeat after figure-only changes. Manifests record source hashes and model selection details. No raw data or generated fields are committed; no GitHub push was performed.

A defensible report conclusion is that reconstruction quality depends on spatial coverage and the reference data: RBF is a competitive baseline and outperforms the tested experimental SVR procedure, while near-wall extrapolation and unmatched operating conditions limit direct CFD comparisons. Thermal convergence remains an explicit limitation rather than evidence of improved physical agreement.