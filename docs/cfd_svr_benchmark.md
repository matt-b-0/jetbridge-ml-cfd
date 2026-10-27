# CFD virtual-sensor SVR benchmark

## Design and reproducibility

This study predicts scalar air speed from x, height above the sloped floor, and bridge distance z (metres). All targets are numerical samples from the converged isothermal baseline at time 237 in `/home/mattb/projects/jetbridge-baseline-20261024`. This is CFD reconstruction, not experimental validation. Failed or provisional thermal fields are excluded.

Training uses 72 virtual sensors at 10, 22, 34, 46 and 58 ft, placed at the FAA sensor coordinates. Four entirely withheld planes at 16, 28, 40 and 52 ft supply 9,600 reference points (40 by 60 per plane). Experimental speed labels are never used. Both sparse and dense CFD samples use OpenFOAM cellPoint interpolation; no CFD solve or geometry change is made.

An RBF-kernel SVR is tuned with leave-one-training-station-out cross-validation over 27 combinations: C = [0.1, 1, 10], gamma = [0.05, 0.2, 1], epsilon = [0.0005, 0.002, 0.005]. Scalers are fitted within each training fold; station weights prevent the denser 58 ft layout dominating. Dense test labels are loaded only after selection, final fitting and training diagnostics. The final training-only StandardScaler is shared with the three-dimensional nearest, linear and thin-plate RBF baselines. These differ from the earlier two-dimensional experimental interpolation benchmark.

Selected parameters: C = 0.1, gamma = 0.2, epsilon = 0.0005 m/s. Final SVR converged in 2,132 solver iterations (fit_status = 0). All 44 tests passed, including grouped splits, training-only scaling, affine interpolation, unsupported extrapolation, and model serialization. Reloading the actual saved model reproduced exported predictions exactly.

From WSL, activate the pinned Python environment described in requirements-benchmark.txt, export PYTHONPATH to the repository src directory, and source the OpenFOAM bashrc. Run the two modules with fresh output directories:

```bash
python -m jetbridge_ml.cfd_interface.virtual_sensors \
  --case /home/mattb/projects/jetbridge-baseline-20261024 \
  --dataset /mnt/c/Users/mattb_ar68ij9/Downloads/dot_92577_DS3/JetBridge_2026 \
  --output /home/mattb/projects/jetbridge-virtual-samples-20261024
python -m jetbridge_ml.virtual_benchmark \
  --samples /home/mattb/projects/jetbridge-virtual-samples-20261024 \
  --output /home/mattb/projects/jetbridge-virtual-svr-benchmark-20261024
```

Outputs include the joblib model, training sensors, dense predictions, per-station metrics and coverage, fold/scaler audit, search results, learning curves, source/input hashes and package versions. Copies of the benchmark outputs are under data/processed/virtual_svr (ignored by Git). Timing rows explicitly distinguish combined baseline fitting/prediction from SVR prediction alone; they must not be used as a fair end-to-end runtime ranking.

## Results and limits

Numbers below are arithmetic means of the four held-out plane RMSE values, in m/s. The shared supported region contains 4,400 of 9,600 points (45.8%). Outside-hull errors are reported separately rather than silently discarded.

| Method | Common supported region | Full planes |
| --- | ---: | ---: |
| Nearest | 0.004826 | 0.033509 |
| Linear | 0.003310 | Unsupported outside hull |
| Thin-plate RBF | 0.002927 | 0.032378 |
| SVR | 0.002914 | 0.032585 |

SVR and RBF are nearly tied inside the hull; RBF has slightly better full-plane RMSE and common-region MAE. No general superiority is established. Near-wall extrapolation dominates the full-plane errors: outside-hull mean RMSE is 0.044173 m/s for SVR. The model has no imposed wall condition or flux constraint. No negative predictions were observed in this test, and no clipping is applied.

All samples are correlated observations of one smooth numerical solution, not independent physical experiments or multiple operating conditions. Mesh uncertainty, boundary-condition mismatch, measurement uncertainty and physical validation remain unresolved. Station-grouped CV supports spatial reconstruction evaluation; it does not establish generalisation to another flow rate or thermal case.

## Error graphs and course connection

SVR is not trained in neural-network epochs. svr_solver_iteration_error.png/pdf shows independent fresh fits at increasing maximum solver iteration budgets, using only training-station folds. It is an optimization-budget diagnostic, not a warm-start training trace. The shaded band is station variability, not a confidence interval. Early-budget fits may be unconverged; convergence flags are saved in solver_iteration_curve.csv.

svr_learning_and_search.png/pdf shows hyperparameter-search error and error versus training sample count. These are descriptive curves conditional on parameters already selected using the training stations, not independent test estimates. Held-out station and delta-slice figures show the separate final test results.

This implements syllabus SVR (5.3), regression evaluation and training selection (5.5-5.6), spatial interpolation/extrapolation (3.x), and numerical error/reproducibility (2.2, 1.2, 1.5). Solver optimization convergence is distinct from the PDE stability study and from physical accuracy. The student should review the assumptions and interpretation before submission.
## Current demo and quality workflow on 27 October 2026
The repository now includes the attributed study input subset and compact archived numerical evidence. Use the root run_all.py driver and docs/LIVE_DEMO.md for one-clone execution; older commands above describe the original research runs. Static checking uses python -m ruff check src tests run_all.py; numerical tests use python -m pytest -q; API documentation uses python -m pdoc jetbridge_ml -o docs/html. See docs/DEVELOPMENT.md for scope and limitations. Live/full execute fresh isothermal CFD in new output folders; archived unconverged thermal evidence remains explicitly separate.
