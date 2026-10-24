# Initial experimental interpolation results — 24 October 2026

Exploratory spatial cross-validation of 36 S01-A / HN replicate planes from the external FAA/NRC dataset. There are 504 observations with no missing speed targets: six 24-point runs at 58 ft, and thirty 12-point runs elsewhere. Planes were measured separately; these are not a simultaneous 3D field.

Each replicate is fitted separately with one complete coordinate location withheld. Nearest, linear and fixed thin-plate-spline RBF use identical training/test rows. There is no tuning, cross-replicate pooling, CFD-assisted correction or imposed flow constraint.

## Coverage and fair comparison
360 held-out observations lie in their remaining training convex hull; 144 lie outside. Linear predicts 360/504 (71.43%) overall, versus 504/504 for nearest and RBF. All three predict the same 360 supported observations. RBF/nearest outside-hull errors are reported separately; they must not be compared with linear's differently covered all-point score.

Mean per-run common-hull RMSE: nearest 0.078597 m/s; linear 0.059768 m/s; RBF 0.051682 m/s. These macro scores give each replicate equal weight, so stations with six replicates contribute more than stations with three. They mix 12- and 24-point layouts and are not a definitive model ranking.

| Station (ft) | Points per run | Nearest RMSE | Linear RMSE | RBF RMSE |
|---:|---:|---:|---:|---:|
| 10 | 12 | 0.021688 | 0.014108 | 0.013995 |
| 16 | 12 | 0.016523 | 0.018603 | 0.016981 |
| 22 | 12 | 0.019976 | 0.017015 | 0.014580 |
| 28 | 12 | 0.018510 | 0.012402 | 0.011149 |
| 34 | 12 | 0.041043 | 0.029482 | 0.030733 |
| 40 | 12 | 0.020768 | 0.011387 | 0.011378 |
| 46 | 12 | 0.037202 | 0.020177 | 0.020691 |
| 52 | 12 | 0.130503 | 0.075765 | 0.052204 |
| 58 | 24 | 0.297246 | 0.246392 | 0.211551 |

Units are m/s; each entry is mean per-run RMSE on common supported points at that station. The large 52/58 ft errors materially affect the aggregate. This table does not isolate layout-density effects because station and layout change together. No cause is established by these errors alone.

## Verification and reproducibility
- All 13 tests passed, including source units/missing values, affine-field reproduction, explicit linear extrapolation, grouped-location isolation, repeatability, and a held-out-target perturbation check.
- Two executions gave byte-identical observations/metrics and identical prediction records after excluding timings.
- The verified run records 39 input SHA-256 hashes (36 average files plus dictionary, periods and boundary), code hashes, fixed method/split settings, package versions and Git provenance.
- No dependencies or settings were tuned using these errors. These exploratory folds must not become an unacknowledged final test if later used to select ML settings.
- Raw records and the CFD case remain unchanged. Stable-window recomputation and matching HVAC periods remain separate tasks. This is not experimental validation of CFD.

Full outputs are in ignored data/processed/interpolation_initial/ and /home/mattb/projects/jetbridge-results-20261024-verified in WSL. See interpolation_workflow.md for reproduction commands. Requirements are pinned in requirements-benchmark.txt. Source files remain external and were not uploaded.
