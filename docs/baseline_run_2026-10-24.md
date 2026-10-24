# Baseline simulation — 24 October 2026

## Status
OpenFOAM v2412 patch 260127 completed the baseline under Ubuntu 24.04 / WSL 2 as user mattb, using one process. SIMPLE reported convergence in 237 iterations (55 seconds wall time). This is numerical convergence to the configured residual criteria, not experimental validation or mesh independence.

Linux case: `/home/mattb/projects/jetbridge-baseline-20261024`.
Original Windows case inputs were not modified. The run copy adds `writeFields false;` to inletFlux and outletFlux for OpenFOAM v2412 compatibility. Geometry retains upper ceiling y=3.784473 m, including the known 0.127 mm difference from the included source template. Published rounded sensor positions are retained.

## Checks and results
- Existing static checker passed; it assumes constant height and is not an independent source geometry audit.
- blockMesh completed: 141,312 cells.
- checkMesh: Mesh OK; maximum non-orthogonality 4.7816886 degrees; maximum skewness 0.10708159; total volume 61.380677 m3.
- Final initial residuals: Ux 9.3580874e-6, Uy 2.3787993e-6, Uz 5.3345327e-7, p 3.2183807e-6 (first pressure solve), epsilon 6.3290581e-8, k 6.9755718e-7. These satisfy the configured residualControl values.
- Final reported global continuity error: 4.002308e-11 (solver diagnostic; not a physical volumetric flux).
- At iteration 200, signed inlet/outlet phi sums were -0.533865517 / +0.533865509 m3/s, a relative imbalance of approximately 1.50e-6 percent.
- Final field 237 postprocessing reports signed inlet/outlet flow as -0.53386552 / +0.53386552 m3/s at displayed precision. Do not interpret rounded equality as exact zero imbalance.
- Verified all 12 output probe-header coordinates against the source/processed layout. Final comparison uses iteration 237, explicitly postprocessed after solver completion; scheduled outputs alone ended at 200.
- Sensor speed RMSE 0.040473 m/s; MAE 0.037527 m/s; mean bias +0.037527 m/s. CFD speed exceeds measured mean at every sensor. Compare magnitudes, not signed Uz.
- No fatal errors, warnings or turbulence bounding messages were found by the run-log scan.

## Reproduction in the Linux run copy
```bash
source /usr/lib/openfoam/openfoam2412/etc/bashrc
cd /home/mattb/projects/jetbridge-baseline-20261024
# Mesh and solver have already run. To extract the saved final field again:
simpleFoam -postProcess -latestTime > log.postProcess-final 2>&1
python3 scripts/compare_probe_speeds.py
```

Full logs and fields remain in the Linux case. The small final sensor comparison CSV is saved beside this report. No meshes or fields are committed.

## Outstanding checks
Source-ceiling reconciliation, finer mesh sensitivity, wall y+, intermediate sectional fluxes, sensitivity to inlet/turbulence assumptions, experimental averaging windows, and physical validation remain outstanding. The full-face inlet, sealed walls and steady isothermal k-epsilon model remain baseline assumptions. The current single-station comparison cannot establish the cause of the reported upstream/downstream discrepancy.