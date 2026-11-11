# Jet Bridge desktop GUI

The GUI launches the same scientific components used by the project, with explicit separation between experiments, fresh CFD and archived diagnostics. It changes no original case dictionaries or published research scores.

## Open on Windows

Double-click `Launch_Jet_Bridge_GUI.cmd` in the repository, or run:

```powershell
python launch_gui.py
```

The frontend needs Python with Tk (included in ordinary Windows Python installations). The launcher can use the installed Codex bundled Python, a `JETBRIDGE_GUI_PYTHON` override, or the `py -3` launcher. The scientific worker needs the project's existing Python dependencies. No new pip package is required by the GUI itself.

On this workstation the defaults are WSL distribution `Ubuntu-24.04` and `/home/mattb/projects/jetbridge-python-env/bin/python`. These fields are editable for another installation. **Check runtime** checks Python scientific dependencies and reports whether the supported OpenCFD v2412 tools are available. A Python-only runtime can still run reconstruction and archived views. Fresh CFD requires the OpenFOAM runtime at `/usr/lib/openfoam/openfoam2412/etc/bashrc`.

For a new WSL environment, install the project as described in LIVE_DEMO.md and point the GUI at that environment's Python executable. Default Windows drive mounts under `/mnt/<drive>` are assumed. UNC/network paths are deliberately unsupported in this first version. Source paths and reconstruction/archived result folders can contain spaces. Fresh CFD case output folders must not contain spaces because OpenFOAM rejects those paths; the GUI checks this before starting. Outputs default to ignored `gui_runs/` in the checkout. Windows-to-WSL launches use literal argument arrays, not user-composed shell commands.

On a Linux desktop with Tk and the scientific environment active, `python launch_gui.py` uses that Python directly. A headless Linux worker can use the CLI below.

## Laptop screens and resizing

The window now starts within the available display size and can shrink to 640 × 420 on typical screens. It preserves the operating system's font/DPI scaling. The left settings panel scrolls, including by mouse wheel or keyboard focus, while Run and Cancel stay pinned at the bottom. Drag the divider to change the panel widths.

Figure previews resize automatically when the window or divider changes, preserving aspect ratio. Pillow gives smooth resizing when available (including the bundled Python); the standard-library fallback also fits the image inside the viewport. In short/narrow windows, result actions collapse into **Open results…**. Very short windows put the full text summary under **Open results… → Run summary** to leave space for the preview. Full-size figures remain accessible from that menu.

Close and reopen the GUI after updating its code; an already-running Python window keeps its old layout. Native Tk layout checks cover several window sizes and Tk font-scaling factors. These are component layout checks, not a claim to have tested every laptop/monitor DPI configuration.

## Help and physical validation

The GUI opens on Help, a scrollable explanation of the selected workflow, plots, metrics and evidence. The results summary distinguishes reconstruction-only runs, archived thermal diagnostics and actual CFD-to-experiment comparisons.

Physical validation means demonstrating that the flow model represents the real apparatus accurately enough for a specified engineering decision. The GUI provides relevant comparison evidence, but it does not implement a physical-validation certification test or an automatic acceptable-error threshold. Even a converged numerical solve with small flux imbalance needs suitable independent measurements, measurement-uncertainty context and an application-specific acceptance criterion. Held-location reconstruction error and CFD-versus-measurement error answer different questions.

## Residual progression plot

Select Residuals during a fresh run to follow the first reported initial residual for each field and SIMPLE iteration. The vertical axis is logarithmic. Select a field or All active fields. Exact all-zero series are omitted from the log plot; isolated zeros use its lower edge, while CSV files preserve the actual values. The source is labelled live, saved or archived.

The worker flushes residual_history.csv as solver lines arrive. It also saves residual_progress.png and .pdf after a successful, failed or cancelled solve when samples exist. The complete solver log retains any additional pressure-correction solves; the plotted record uses the first initial residual per field per iteration. Initial residuals and final linear-solver residuals are distinct columns in fresh histories. SIMPLE iterations are not physical seconds or ML epochs.

Archived isothermal and thermal views replay their recorded histories, clearly labelled. Reconstruction-only mode has no CFD residuals. Load CSV opens a compatible saved history. Falling curves indicate numerical settling; convergence status still comes from the configured solver criteria, with mesh and flux checks separate. Residuals do not establish physical accuracy.

## Controls and scope

| Control | Behaviour |
| --- | --- |
| Experimental setup | The 36 bundled S01-A-HN replicate files for reconstruction; 30 single-window files for fresh CFD |
| Run type | Experimental reconstruction, fresh isothermal CFD, archived matched isothermal comparison, or archived unconverged thermal diagnostics |
| Interpolation / regression | Thin-plate RBF, linear, nearest neighbour, or SVR |
| Mesh resolution | Coarse 17,664 cells, Standard 141,312 cells, Fine 476,928 cells |

Resolution is not an accuracy or mesh-independence grade. All meshes retain uniform block grading without near-wall inflation. The mesh control applies only to fresh CFD. Other modes disable it and retain the correct archived mesh provenance. Thermal diagnostics disable interpolation/ML fitting and never become reference/training data.

The 58 ft averages assemble sequential A/B measurements. They are available for reconstruction but excluded from fresh CFD because a single matched inlet cannot be assigned without a new research decision. The archived isothermal comparison is fixed to its actual source, S01-A-10-HN-1 at iteration 237. The thermal viewer is fixed to S01-AC-10-HN-1 and labels it unconverged. This GUI does not launch new thermal solves or accept arbitrary geometry, passenger configurations or imported CSV setups.

Select a workflow, experiment and reconstruction method, then click **Run selected setup**. The interpolation dropdown changes the reconstructed experimental surface and withheld-location score. It does not change the CFD solver discretisation or turbulence model.

## Fresh CFD protocol

1. Validate the selection and require a new, unprotected output folder.
2. Verify hashes of all bundled sources actually read by the job. Record their individual hashes and the bundle manifest hash. The full run_all.py demonstration retains its all-input check; this targeted GUI job checks its own declared inputs.
3. Fit the selected experimental reconstruction and evaluate held locations using the existing nested training-only machinery. Full-array refit plots are separate from predictive scores. For consistency the audited all-method evaluator is reused internally, although only the selected method is shown.
4. Read Q.FS only in the selected run's recorded **Entire Set** window, remove invalid sentinels/negative flows and convert L/s to m³/s. Record whether stable and entire windows differ. Measured speed targets do not calibrate Q.
5. Copy only the baseline `0/`, `constant/` and `system/` inputs to a new case. Set exact mesh counts, measured inlet Q and probes for the selected source coordinates. Recompute bulk initial U and k/epsilon consistently with the original 5% intensity and 7%-hydraulic-diameter length scale assumptions. Retain p, viscosity, turbulence model, sealed walls and idealised inlet/outlet assumptions. The documented 0.127 mm source-ceiling discrepancy remains unchanged.
6. Run blockMesh, checkMesh and simpleFoam. Require `Mesh OK`, explicit SIMPLE convergence within 600 iterations, and a saved converged U field. Iterations are not physical seconds.
7. Sample the exact sensor positions and a separate display grid with cellPoint interpolation. Reject invalid/nonfinite or mismatched coordinates. Check final inlet/outlet flux with a declared relative imbalance screen of 1e-5 before accepting comparison exports.
8. Save comparisons, refit maps, withheld errors, mesh plots, CSVs, PDF/PNG figures and a manifest. Recheck original case hashes.

Passing these numerical screens does not establish physical agreement, mesh independence or ventilation compliance. The chosen case remains an idealised isothermal k-epsilon RANS model. The supplied flow is not assumed equal to an experimental scalar-speed integral. CFD-to-measurement metrics are separate from interpolation held-location metrics.

## Logs results and cancellation

The GUI remains responsive while a separate worker runs. The Log tab shows stages and selected solver iterations. Complete OpenFOAM logs remain in `log.*` files. Results shows selected prediction metrics and a PNG preview, with buttons for the full-size figure, local HTML gallery and output folder. CSVs and manifest.json retain the complete numerical evidence, package versions, source-code hashes, Git revision and dirty-working-tree status.

Every click starts a new timestamped directory. Existing outputs and original source/data/case folders are protected. Failed and cancelled jobs retain their files and status; they are not labelled successful. Some experimental plots may exist even if the later CFD solve fails. The Cancel button writes a job-specific request, which the worker polls and uses to terminate only that subprocess group. Closing during a run requests cancellation; close again after it stops. The Python-only runtime check must finish before closing. The GUI does not clean previous runs.

## Reproducible CLI

Use the same scientific Python executable on Linux/WSL:

```bash
python -m jetbridge_ml.gui.workflow --root /path/to/jetbridge-ml-cfd --check
python -m jetbridge_ml.gui.workflow --root /path/to/jetbridge-ml-cfd \
  --output /home/user/new-gui-run --kind fresh \
  --run-id S01-A-10-HN-1 --method rbf --mesh coarse
```

Kinds: experimental, fresh, archive, thermal. Methods: rbf, linear, nearest, svr. Non-fresh requests require mesh standard. Thermal requests require the fixed thermal run and the unused method placeholder rbf. The original baseline Q uses the same mean as before; other single-window experiments generate new case-specific numerical studies.

## Quality checks

```bash
python -m ruff check src tests run_all.py launch_gui.py
python -m pytest -q
```

Tests check flow conversion, temporal selection, output protection, unsupported combinations, exact mesh counts, changed probes/initial turbulence, original-case preservation and cancellation of a silent child. Functional checks include a fresh coarse CFD solve, 58 ft SVR reconstruction, the archived thermal view, and the native Windows Tk-to-WSL result/preview path. These checks exercise the GUI implementation; they do not make physical-validation claims. See gui_verification.json for the recorded smoke-run results.


Residual-monitor verification on 5 November 2026: a fresh coarse case streamed 690 samples across 115 iterations to the native GUI, passed the existing numerical screens and exported the history figures. Archived isothermal replay, saved-history field filtering and normal window shutdown were checked separately. The full headless project suite passed 107 tests with one native-display module skipped; native layout checks ran on Windows. This verifies the plotting workflow, not physical validation of the model.


## MPI acceleration for fresh CFD

Select **Solver processes** in the GUI: 1 is serial; 2, 4 and 8 use Open MPI.
This applies to fresh isothermal CFD only. Archived and experimental modes do not
run a solver. Start with 2 or 4 on the tested four-core laptop; benchmark your own
mesh before assuming a speed gain. The worker refuses counts beyond available
WSL CPUs and does not oversubscribe or silently fall back to serial.

The copied case uses Scotch partitioning, parallel checkMesh, parallel simpleFoam
and reconstructPar at the converged saved iteration. Sampling and the existing
flux/convergence screens then run on reconstructed fields. Original cases,
physics, coordinates and stopping criteria are unchanged. Each manifest records
process count, available CPUs, commands and stage timings. Residuals come from
the actual parallel solver; cancellation uses the worker's subprocess group.
Generated processor directories and fields stay in the ignored job output.

Reproduce from Linux/WSL with the existing scientific Python environment:

```bash
PYTHONPATH=src python -m jetbridge_ml.gui.workflow --root "$PWD" \
  --output /home/mattb/jetbridge-demo-mpi4 --kind fresh \
  --mesh standard --processes 4
```

Use a new output directory without whitespace. OpenFOAM v2412, Open MPI,
`decomposePar`, `reconstructPar` and Scotch support must be installed in WSL.
The implementation follows the [OpenFOAM parallel workflow](https://www.openfoam.com/documentation/user-guide/3-running-applications/3.2-running-applications-in-parallel).
This option currently covers the GUI worker; other project orchestration scripts
retain their existing execution settings. Numerical serial/parallel agreement
is distinct from experimental validation.


### Measured MPI performance (5 November 2026)

Sequential single runs on the standard 141,312-cell mesh, S01-A-10-HN-1,
Ubuntu 24.04 / OpenFOAM v2412 / Open MPI 4.1.6, Intel i7-1165G7
(4 physical cores, 8 logical CPUs), with Linux-native case output:

| Processes | Solver (s) | All CFD stages (s) | CFD-stage speedup |
|---|---:|---:|---:|
| 1 | 57.003 | 61.821 | 1.00 |
| 2 | 37.937 | 47.704 | 1.30 |
| 4 | 32.743 | 42.300 | 1.46 |

All CFD stages includes mesh creation/checks, MPI setup, partition checks,
reconstruction and sampling. It excludes Python interpolation and plotting.
These are single trials, not repeated statistical benchmarks; output on the
Windows/OneDrive drive may perform differently. Four processes is the measured
starting recommendation for this standard mesh. Eight processes was not tested.

Serial converged at iteration 237; both MPI runs converged at 238. All passed
serial and partition mesh checks and the 1e-5 relative flux screen (imbalance
zero at logged precision). Relative L2 velocity differences across the same
2,412 sampled sensor/plane coordinates were 4.04e-8 (2 processes) and 2.31e-7
(4), below the declared 1% numerical-equivalence screen. Maximum speed
change was 8.51e-8 m/s. This is sampled-field agreement, not a whole-volume
error norm, mesh-independence result or physical validation. Original case
files were unchanged. Live residuals recorded 1,428 samples for each MPI run.
A separate test cancelled a real two-rank MPI job and checked that ranks stopped.

See [machine-readable evidence](mpi_verification.json) for stage timings and
local output paths. Reproduce the CLI above with processes 1, 2 and 4, unique
outputs and identical standard mesh/experiment inputs. Align sampled points by
coordinates before comparing vectors; do not compare raw export row order.


## Reconstruction Lab — interpolation first

The GUI now opens in **Reconstruction Lab - experimental comparison**. Select
one of the 36 supported S01-A-HN replicates and run. All four methods are
compared automatically; single-method, mesh and MPI controls are disabled in
lab modes. The existing experimental/fresh-CFD/archived workflows remain
available. Restart an already-open GUI to load the new workflow.

After completion, choose **Results → Open result gallery**. This opens the
interactive **Reconstruction Lab** in your browser. It runs locally and offline,
with no new frontend dependencies, server, account or cloud upload. Its five
views are:

1. **Compare fields**: four matching nearest/linear/RBF/SVR maps on one colour
   scale. Toggle sensor and hull overlays, focus on a method, and hover to read
   scalar speeds and floor-relative coordinates. Full-array maps are fits,
   not prediction tests; linear outside-hull cells stay missing.
2. **Unseen sensors**: parity plots, signed local residuals and common-support
   RMSE/MAE. Experimental scores reuse the existing nested leave-location-out
   evaluation. Each SVR inner search excludes the outer target. Outside-hull
   metrics/coverage remain separate in the CSV.
3. **Sensor count**: error versus nested retained-sensor count with three
   deterministic layouts. Hull vertices remain in every training subset, and
   test locations/support stay fixed. The band is trial range, not a confidence
   interval. This deliberately favourable coverage-preserving design is not a
   universal sensor-count recommendation.
4. **Input noise**: paired Gaussian perturbations at 0/2/5/10% of training-speed
   RMS, using the largest tested retained count (see sensitivity CSV). Only
   training targets change; held-out values stay unchanged. SVR is selected
   again inside noisy training data. No instrument-uncertainty claim is made.
5. **Accuracy & cost**: separately evaluated held-out RMSE versus median full
   fit plus 2,400 grid predictions over three calls, including SVR selection.
   Times exclude loading, plotting and CFD and depend on your machine.

**Reconstruction Lab - archived CFD virtual sensors** instead uses the bundled
converged isothermal 16 ft reference plane. It does not launch a solver or use
thermal fields. A 40×60 grid is split into 150 candidate training locations
(row/column indices congruent to 1 modulo 4) and 2,250 disjoint test locations.
A fixed 24-sensor design supplies the displayed full fits and primary scores;
separate learning studies use 6/8/12/24/48 sensors. Common-hull support is
reported explicitly. Numerical field error maps show the CFD reference and
method-minus-reference differences, including extrapolation for inspection.
These are same-plane numerical reconstruction studies, not independent
physical experiments or cross-station generalisation tests. The source CFD
uses the baseline scenario; the 16 ft label does not imply matching another
replicate's HVAC window.

The experimental learning/noise study is separate from the primary nested
leave-location-out comparison: seed 3001 chooses held-out interior sensors;
three nested training designs retain the hull vertices. The maximum training
count is less than the complete array because test sensors remain withheld.
The 58 ft A/B layout remains sequential, not a simultaneous 3D observation.
Negative predictions are never clipped. Fixed interpolation settings and the
existing training-only SVR grid are reused.

Every successful run saves six PNG/PDF figure pairs (seven for virtual CFD),
fields/predictions/metrics/sensitivity/timing CSVs, deterministic split records,
SVR search and scaler audits, a dashboard data JSON and the standard source-hash
manifest. The overall gallery links the interactive page. Outputs stay under
ignored gui_runs; no original measurements or case inputs are edited.

Reproduce without the GUI from the project root in the scientific environment:

```bash
PYTHONPATH=src python -m jetbridge_ml.gui.workflow --root "$PWD" \
  --kind lab --run-id S01-A-10-HN-1 --output ~/jetbridge-lab/experimental-01
PYTHONPATH=src python -m jetbridge_ml.gui.workflow --root "$PWD" \
  --kind lab_cfd --run-id S01-A-16-HN-1 --output ~/jetbridge-lab/virtual-01
```

Choose new output paths each time. Open reconstruction_lab.html after the run.
The experimental and virtual baseline examples generated on 5 November 2026
are recorded in reconstruction_lab_verification.json. Browser tests cover
1280/800/390-pixel widths, navigation, real canvas rendering, method focus,
local image loading and JavaScript exceptions. Native Tk checks cover default
mode, inactive controls, both completed result previews and dashboard opening.
