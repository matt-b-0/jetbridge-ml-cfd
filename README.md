# Jet Bridge CFD, Interpolation and Machine Learning

An MMA3001 investigation of how accurately interpolation and support vector regression reconstruct sparse jet-bridge air-speed measurements, and what OpenFOAM virtual-sensor studies reveal about spatial sampling.

**Current status:** nested experimental comparisons, sensor-placement experiments and isothermal mesh/coordinate/flow checks have run. The buoyant thermal case remains unconverged. Numerical convergence is not experimental validation.

## Results you can inspect immediately

The [results gallery](docs/results/current/README.md) contains selected derived figures and small tables committed with the code. No OpenFOAM installation or local dataset is needed to read it. See the [run summary](docs/results/current/SUMMARY.md) and [methods/reproduction guide](docs/project_improvements.md).

For 36 experimental runs and 504 held-out sensor means, common supported locations give:

| Method | Mean per-run RMSE (m/s) |
| --- | ---: |
| Retained-sensor mean | 0.067648 |
| Nearest neighbour | 0.071293 |
| Linear interpolation | 0.055241 |
| Thin-plate RBF | 0.049590 |
| RBF-kernel SVR | 0.057741 |

Each experimental replicate is fitted separately. SVR hyperparameters are selected inside each outer training fold. Linear interpolation does not extrapolate; coverage and outside-hull errors are reported separately.

![Paired experimental errors](docs/results/current/paired/paired_model_errors.png)

RBF wins 21 of 36 paired runs, but its mean advantage is concentrated at the 58 ft, 24-sensor layout. The 12-sensor runs slightly favour SVR on average. Station and layout density are confounded, so this is not evidence that density alone causes the difference. No IID-sensor significance claim is made.

The CFD checks quantify mesh sensitivity and small coordinate-rounding effects. A fixed 24-sensor hybrid layout also improves RBF/SVR full-section reconstruction in a synthetic 80%-flow case. These are numerical studies, not independently matched experimental validations.

## Reproduce the Python analysis

The tested environment is Python 3.12 under Ubuntu 24.04/WSL. From a clone of this repository:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-benchmark.txt
python -m pip install --no-deps -e .
python -m pytest -q
python -m jetbridge_ml.run_analysis \
  --dataset /path/to/JetBridge_2026 \
  --output data/processed/new-analysis \
  --gallery data/processed/new-gallery
```

The default command runs the experimental mean/nearest/linear/RBF/SVR comparison, paired errors and reduced numerical-stability study. It needs the external FAA dataset but does not need OpenFOAM. Every output/gallery path must be new. Logs, package versions, source hashes and SUMMARY.md are saved automatically.

For a general development installation rather than the pinned research environment, use `python -m pip install -e '.[dev]'`. The automated workflow tests Python 3.10 and 3.12; hosted CI has not yet run for these local changes.

[Optional CFD analysis flags and complete commands](docs/project_improvements.md) add matched raw/HVAC audits, sensor-placement comparisons, thermal diagnostics and summaries of completed verification cases. They require explicit input paths; the analysis runner does not silently start CFD solves or download raw data.

## OpenFOAM cases

The isothermal starter is [cfd/cases/empty_bridge_s01_a_10_hn_1](cfd/cases/empty_bridge_s01_a_10_hn_1/README.md). It uses steady incompressible k-epsilon RANS, a full-face supply and sealed walls. The tested v2412 writeFields compatibility entries are included. Run cases in a separate Linux/WSL directory and retain their logs and fields outside Git.

```bash
source /usr/lib/openfoam/openfoam2412/etc/bashrc
# In a separate copy of the case:
blockMesh > log.blockMesh
checkMesh > log.checkMesh
simpleFoam > log.simpleFoam
```

The [verification workflow](docs/project_improvements.md) prepares isolated coarse/fine meshes and a reduced-flow case, with bounded iteration caps. Three meshes provide sensitivity evidence; they do not automatically establish mesh independence or a GCI. The known 0.127 mm source-ceiling discrepancy remains documented.

The [thermal extension](docs/thermal_case_results.md) uses a cold supply and laboratory-temperature walls as an unmeasured wall-temperature surrogate. Its continuation still fails residual and stationarity checks. Thermal fields are excluded from ML/reference training.

## Project structure and evidence

| Location | Responsibility |
| --- | --- |
| src/jetbridge_ml/data_processing | Experimental readers, units and source records |
| src/jetbridge_ml/interpolation | Traditional reconstruction methods |
| src/jetbridge_ml/machine_learning | SVR fitting and training-only selection |
| src/jetbridge_ml/cfd_interface | CFD sampling, numerical checks and comparisons |
| src/jetbridge_ml/validation | Error metrics, spatial splits and reduced stability checks |
| cfd/cases | OpenFOAM inputs and reproducible case preparation |
| tests | Numerical and data-handling checks |
| docs/results/current | Selected reproducible figures and small derived summaries |
| data/processed | Ignored complete local outputs |

The [.github workflow](.github/workflows/numerical-checks.yml) installs the Python package and runs tests without external measurements or OpenFOAM, then saves JUnit results. It is configured locally; GitHub execution requires a push.

Background and research assumptions: [PROJECT_CONTEXT.md](PROJECT_CONTEXT.md), [assumptions](docs/assumptions.md), [four-workstream results](docs/four_workstreams_results.md), [numerical stability](docs/numerical_stability_study.md), and [AI-use record](docs/ai_usage_log.md).

Raw FAA/NRC data, generated meshes, saved fields, full prediction tables and fitted model binaries remain outside Git. The public repository includes source, tests, documentation and selected derived results. Dataset provenance and source details are recorded in PROJECT_CONTEXT.md and the analysis manifests.
Nine [additional report figures with PNG/PDF downloads and captions](docs/results/additional_figures/README.md) show model skill, station/layout effects, mesh profiles, flow-transfer error maps and unresolved thermal convergence.
