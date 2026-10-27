# One-clone live demonstration

This is the current entry point for regenerating the project figures. Older dated notes describe the original research runs; this driver adds orchestration without replacing their scientific assumptions or scores.

## Setup once in Ubuntu or WSL

The live/full profiles need OpenCFD OpenFOAM v2412 at `/usr/lib/openfoam/openfoam2412/etc/bashrc`, providing `blockMesh`, `checkMesh` and `simpleFoam`. The existing Ubuntu 24.04 workstation installation is supported. The runner sources that runtime automatically. Git does not install a system CFD runtime. Replay works without OpenFOAM.

```bash
git clone https://github.com/matt-b-0/jetbridge-ml-cfd.git
cd jetbridge-ml-cfd
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-benchmark.txt
python -m pip install --no-deps -e .
```

All data required by the commands below is included in the ordinary Git clone: no LFS pull, private download path or manual CSV copying. The experimental subset has a separate CC BY 4.0 attribution notice in `data/demo/ATTRIBUTION.md`. This does not assign a licence to the student's code, which remains undecided.

## Demonstrate a real CFD run

```bash
python run_all.py --profile live --output ~/jetbridge-demo/live-01
```

The output directory must be new. Prefer the Linux filesystem for CFD performance. The script runs lint/tests, copies the tracked baseline inputs to that isolated directory, runs blockMesh, checkMesh and simpleFoam, verifies convergence within 600 SIMPLE iterations, calculates y-plus, samples the fresh field, and runs the interpolation/ML and plotting stages. It never cleans or solves inside the tracked original case.

Live regenerates baseline-based slices, matched comparisons, virtual sensor models and sensor-placement plots from the new baseline. Mesh-refinement/80%-flow comparison tables and all thermal inputs are replayed from included evidence and labelled in `demo_manifest.json`. It does not pretend that a single new baseline run reproduces a mesh study or the failed thermal history.

To run all four isothermal cases freshly as well:

```bash
python run_all.py --profile full --output ~/jetbridge-demo/full-01
```

Full runs the baseline, coarse, fine and synthetic 80%-flow cases and regenerates their mesh/flow comparison tables. Thermal diagnostics still use archived evidence because the buoyant case did not converge. Its figures retain NOT CONVERGED labels and its values never become ML training/reference data. Neither live nor full establishes physical experimental validation or mesh independence.

For a figure-generation rehearsal without any CFD execution:

```bash
python run_all.py --profile replay --output ~/jetbridge-demo/replay-01
python run_all.py --profile full --plan
```

Replay recomputes experimental fits, nested tuning, reduced stability, CFD-surrogate fits, perturbation experiments, timings and plot rendering using archived numerical tables. It is not a new simulation. The plan command executes nothing and creates no outputs.

## What to show during the assessment

Open the final `index.html` gallery. Every PNG is linked with its stage directory; corresponding PDF files remain alongside it. `figure_inventory.json` records the generated paths and hashes. `demo_manifest.json` records each command, data lineage, status, log and measured duration. Logs stream to files while stage names and completion times appear in the terminal.

The workflow includes the original interpolation benchmark, nested experimental comparison, paired station/layout comparison, reduced diffusion study, virtual-sensor SVR diagnostics, sensor designs, 16-panel collection, thermal comparisons, additional report figures, repeated timing study, compact figures, empirical perturbations, and the 10/58 ft coverage and lower-C diagnostics. API HTML docs are regenerated in the output folder. This is the maintained Python-generated scientific figure collection, not regeneration of third-party images in source reports or a fresh Word layout.

A full research regeneration can exceed the presentation slot. Rehearse on the demonstration computer and consult the measured stage durations; do not promise a fixed runtime across machines. Start full before presenting if necessary. Live is the smaller real-solve demonstration. After separately checking lint/tests, `--skip-quality` can omit those two stages during a timed rehearsal; the omission is recorded rather than hidden. It does not omit a failed physics check.

## Failures and interpretation

The runner refuses existing outputs, rejects output inside tracked source/data/case directories, verifies all included hashes and stops at the first failed subprocess. Logs and a failure manifest remain. A failed mesh or an unconverged new baseline prevents downstream use as a numerical reference. Do not present a partial directory as a completed demo.

The input geometry remains SI, with x across width, y above the laboratory floor and z along the bridge. Experimental hot-sphere values are scalar speed magnitudes, not signed axial flux. Cross-station data is asynchronous and the 58 ft layout is confounded with station. The lower-C extension remains post-hoc exploratory; timing results are newly measured on the demonstration hardware.

See [development and linting](DEVELOPMENT.md) for the quality commands and [data attribution](../data/demo/ATTRIBUTION.md) for provenance.

## Measured workstation check on 27 October 2026
The development full run regenerated 80 PNG figures in 27 logged stages. Stage execution totalled approximately 772 seconds (12.9 minutes), excluding initial input hashing. Its fresh solves converged at baseline 237, coarse 115, fine 380 and flow80 237, with all meshes passing checkMesh. These are numerical checks, not physical validation. The final live/replay clone checks and current test count are recorded under docs/demo_validation. Do not try to fit this full run into a five-minute presentation.
