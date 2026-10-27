# Reproducibility, baselines and numerical checks

This workflow adds a retained-sensor mean baseline, paired model comparisons, a portable results gallery, automated Python tests, and bounded isothermal mesh/coordinate/flow-transfer checks. Experimental measurements, numerical fields and fitted predictions remain separate.

## One-command analysis

Install the package from the repository root. Raw FAA data stays external:

```bash
python -m pip install -e '.[dev]'
python -m jetbridge_ml.run_analysis \
  --dataset /path/to/JetBridge_2026 \
  --output /path/to/new-analysis \
  --gallery /path/to/new-gallery
```

This default needs Python and the dataset, not OpenFOAM. It runs nested experimental prediction, paired errors and the reduced numerical-stability study. Each subprocess log is saved at the output root; a failed step exits visibly instead of publishing a success summary. The output and gallery must be new directories so previous results are preserved. SUMMARY.md gives the core findings, and pipeline_manifest.json records commands, package versions and source hashes.

Optional sections require explicit inputs:

```bash
python -m jetbridge_ml.run_analysis \
  --dataset /path/to/JetBridge_2026 --output /path/to/new-full-analysis \
  --baseline-case /path/to/converged-isothermal-case \
  --cfd-candidates /path/to/report_figures/sampled_iso.csv \
  --cfd-reference /path/to/virtual_samples/dense_test.csv \
  --thermal-restart /path/to/original-buoyant-restart \
  --thermal-continuation /path/to/completed-buoyant-continuation \
  --verification-results /path/to/completed-isothermal-verification \
  --gallery /path/to/new-gallery
```

The matched-case step invokes OpenFOAM postprocessing. The other optional sections analyse existing sampled tables or logs. The runner never silently starts a new CFD solve. The workflows producing candidate/reference data are documented in report_figures.md and cfd_svr_benchmark.md.

## Mean baseline and paired comparisons

The mean baseline predicts each withheld sensor using the arithmetic mean of only its retained sensors. It has no tuning, flow-rate constraint or access to the held-out speed. Nearest, linear, RBF and SVR predictions use the same outer locations; SVR selection remains nested within training folds. Five-method summaries replace the earlier four-method results for this run, while earlier dated results are preserved.

Paired RBF-minus-SVR RMSE is recorded for every run and summarized by station. Negative values favour RBF. Complete coverage and matched run entries are required. The report includes wins, ties, mean/median paired differences, and performance relative to the mean baseline. Runs share an apparatus and stations/replicates can be dependent; no IID-sensor confidence interval or significance test is used. The mean baseline is an informative benchmark even if it outperforms a more complex method.

## Bounded CFD verification

Run this separately in WSL/Linux with OpenFOAM available, using a new Linux output directory:

```bash
python -m jetbridge_ml.cfd_interface.verification_study \
  --baseline /path/to/verified-isothermal-case \
  --dataset /path/to/JetBridge_2026 \
  --output /path/to/new-isothermal-verification
python -m jetbridge_ml.cfd_interface.verification_results \
  --study /path/to/new-isothermal-verification \
  --output /path/to/new-verification-summary
```

The prepared cold-start cases are:

| Case | Mesh cells | Supply factor | Intended check |
| --- | ---: | ---: | --- |
| Coarse | 17,664 | 1.0 | Mesh sensitivity |
| Existing baseline | 141,312 | 1.0 | Original comparison |
| Fine | 476,928 | 1.0 | Mesh sensitivity |
| Flow80 | 141,312 | 0.8 | Fixed-layout transfer |

Each new case runs blockMesh, checkMesh and simpleFoam with a 600-iteration cap. Geometry, viscosity, turbulence model, convection schemes and solver relaxation are retained. Flow80 scales initial/inlet U by 0.8, k by 0.8² and epsilon by 0.8³ to preserve the existing turbulence-intensity and length-scale assumptions. It is a controlled synthetic flow perturbation, not a newly matched experimental case. Source input hashes are checked afterwards.

Identical cellPoint sampling coordinates are used across meshes. Compare sensor speeds, dense section profiles and area-mean inlet-minus-outlet kinematic pressure (m²/s², not Pa). The fine mesh is a numerical comparison, not exact truth. Refinement factors are unequal; three meshes alone do not establish asymptotic behaviour or justify a GCI/observed-order claim. Solver convergence and wall treatment must be considered before interpreting differences.

Coordinate sensitivity compares published absolute-metre sensor positions against nominal local-inch coordinates converted to metres and offset using the floor at their nominal z. This is an alternative coordinate interpretation, not an automatic correction. Published coordinates remain the authority for experimental comparisons.

The transfer test fixes the 24-sensor interior and hybrid layouts before examining Flow80. Models are refitted on the new retained sensor values and tuned using training-only folds. Thus it tests whether the layout comparison transfers, not whether a frozen velocity surrogate generalizes across flow rates. Full-section linear scores retain incomplete-coverage flags and are not ranked against fully covered predictions.

## Repository gallery and CI

Selected derived figures and small aggregate tables are committed under docs/results/current. Raw inputs, all point predictions, solver logs, fields and models remain excluded. The gallery includes enough evidence to read the repository without running OpenFOAM or accessing a local drive.

The GitHub Actions workflow tests Python 3.10 and 3.12 using package installation and pytest, and uploads JUnit results. It does not download the FAA dataset or install OpenFOAM. Hosted status is recorded in GitHub Actions; local test results alone do not imply hosted CI success. Action configuration follows the official [checkout](https://github.com/actions/checkout), [setup-python](https://github.com/actions/setup-python) and [upload-artifact](https://github.com/actions/upload-artifact) documentation.

Thermal fields remain excluded from reconstruction reference data. Their bounded continuation and unresolved convergence are documented separately rather than extending the thermal scope here.

## Results from this implementation
The complete seven-section analysis command ran successfully. All three new CFD cases passed checkMesh and converged: coarse 115, fine 380, and Flow80 237 iterations. The existing baseline remains at 237. New selected plots/tables are in docs/results/current.

The experimental mean baseline has common-region mean per-run RMSE 0.067648 m/s. RBF beats the mean in 29/36 runs; SVR in 24/36. Paired RBF-minus-SVR RMSE averages -0.008151 m/s across runs, with a median of only -0.000575 m/s. RBF wins 21 runs and SVR 15. The 12-point layouts slightly favour SVR on average (+0.001385 m/s RBF-minus-SVR); the 24-point inlet layouts favour RBF strongly. Those layouts occur only at 58 ft, so density and station effects cannot be separated.

Baseline-to-fine speed differences are 0.001423 m/s RMSE at the 12 experimental positions and 0.007135 m/s across the 9,600 section samples (relative L2 approximately 4.54%). Kinematic pressure drops are 0.003960, 0.004284 and 0.004462 m²/s² on coarse/baseline/fine meshes. This does not establish mesh independence.

On the baseline mesh, nominal-inch versus published-metre positions change sampled speeds by 0.000293 m/s RMSE (maximum 0.000769 m/s), small relative to the approximately 0.04 m/s matched CFD/measurement error. This does not prove that every geometry or coordinate assumption is correct.

For RBF, full-section mean plane RMSE changes from 0.033883 (interior) to 0.026579 m/s (hybrid) at baseline flow, and 0.027537 to 0.021193 m/s at 80% flow. For SVR, the corresponding pairs are 0.033648/0.028435 and 0.027427/0.023186 m/s. This supports transfer of this fixed layout comparison across this controlled flow perturbation; it is not broad operating-condition validation.

The tracked starter case now includes the two writeFields false compatibility entries. Its controlDict matches the already-solved baseline runtime copy exactly. Geometry and physical boundaries were not changed. Local tests pass. Both hosted Python jobs passed after publication; see [run 40091944317](https://github.com/matt-b-0/jetbridge-ml-cfd/actions/runs/40091944317).

## Additional report visuals
Nine captioned figure pairs are included under docs/results/additional_figures. Regenerate them with python -m jetbridge_ml.report_synthesis --analysis /path/to/completed-analysis --verification-samples /path/to/verification-study --output /path/to/new-figures. The local ZIP is under data/processed/report_synthesis; large original fields remain excluded. These figures add descriptive views of existing results, not new validation.

## Current demo and quality workflow on 27 October 2026
The repository now includes the attributed study input subset and compact archived numerical evidence. Use the root run_all.py driver and docs/LIVE_DEMO.md for one-clone execution; older commands above describe the original research runs. Static checking uses python -m ruff check src tests run_all.py; numerical tests use python -m pytest -q; API documentation uses python -m pdoc jetbridge_ml -o docs/html. See docs/DEVELOPMENT.md for scope and limitations. Live/full execute fresh isothermal CFD in new output folders; archived unconverged thermal evidence remains explicitly separate.
