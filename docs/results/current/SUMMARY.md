# Analysis summary

Experimental error is nested held-location prediction, not CFD agreement.

| Method | Mean per-run RMSE (m/s) | MAE (m/s) | Bias (m/s) |
| --- | ---: | ---: | ---: |
| linear | 0.055241 | 0.043424 | -0.009798 |
| mean | 0.067648 | 0.055683 | -0.009355 |
| nearest | 0.071293 | 0.059292 | +0.001263 |
| rbf | 0.049590 | 0.040388 | -0.001164 |
| svr | 0.057741 | 0.049735 | -0.007704 |

RBF wins 21 of 36 paired run comparisons; SVR wins 15. Negative paired error favours RBF.

Layout-stratified paired differences (descriptive; density and station are confounded):
- 12-point layouts: 30 runs; mean RBF-minus-SVR RMSE +0.001385 m/s
- 24-point layouts: 6 runs; mean RBF-minus-SVR RMSE -0.055829 m/s

Runs and stations are descriptive groups sharing one apparatus; no IID-sensor statistical significance is claimed.

## Completed sections

- experimental
- paired
- stability
- sensor_design
- matched
- thermal
- verification

Optional CFD sections are omitted unless their inputs are supplied. The runner does not silently solve CFD or download raw data. Thermal results remain separate from training/reference data.
