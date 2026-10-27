# Codex Handoff — MMA3001 Jet Bridge CFD, Interpolation and Machine Learning

**Prepared:** 24 October 2026  
**Status:** Research direction agreed in discussion; initial repository and OpenFOAM case scaffolded; CFD results and final experimental methodology **not yet verified**.  
**Audience:** Codex agent working in VS Code or Codex desktop against the local `jetbridge-ml-cfd` repository.

> **First instruction to Codex:** Read this file together with `AGENTS.md`, `PROJECT_CONTEXT.md`, the repository README and the CFD case README before making changes. Treat any conclusions below that lack a completed test as hypotheses. The research scope is a proposal and requires teaching-team approval under the MMA3001 brief.

## 1. Why the project exists

This is an individual project for **MMA3001 — Numerical Methods and Machine Learning**, worth **25%** of the unit. The supplied brief calls for a clearly defined mechanical/aerospace engineering problem; at least one numerical method and/or machine-learning method; credible alternative/baseline; verification and validation; appropriate sensitivity, optimisation or performance evaluation; reproducible GitHub code; and transparent AI-use reflection. The brief emphasises sound justification, validation and communication over complexity.

The deliverables include:
- A functional GitHub repository (README, appropriate licence, source code with docstrings/comments, generated HTML/API documentation, automated tests and test report, meaningful commits); a link plus zipped clone submitted via Moodle.
- An individual **5–10 page written project report**, excluding references/appendices.
- A **5-minute presentation plus 3 minutes of questions**, during Week 14 / examination period.
- Explicit disclosure of AI contributions and independent verification.

The **self-selected project must be approved by the unit coordinator/teaching team** before substantial work. Dates should be checked in current unit materials rather than assumed.

## 2. Agreed project direction

**Working title:** *Evaluation of Numerical Interpolation and Machine Learning for Sparse Jet Bridge Flow Reconstruction with OpenFOAM-Based Validation.*

**Primary research question:**

> How accurately can traditional interpolation and machine learning reconstruct air-speed distributions from sparse experimental jet bridge sensors, how does their performance depend on sensor density/placement, and how do the resulting predictions compare with OpenFOAM fields and independently measured HVAC flow rates?

**Main objective:** Fairly compare traditional interpolation versus ML, with OpenFOAM playing a **supporting role** in physics-based benchmarking and exploring uncertainty caused by sparse sensors. The project should **not** turn into an unbounded full CFD-validation exercise at the expense of the numerical-methods comparison.

**Core tasks:**
1. Parse and audit relevant FAA/NRC experimental data, including units and coordinate mappings.
2. Reproduce a single relatively simple empty-bridge, approximately isothermal OpenFOAM case.
3. Implement simple baselines: nearest neighbour, linear interpolation and radial basis function (RBF) interpolation.
4. Implement at least one learned model, initially **Gaussian process regression (GPR)**, with hyperparameters tuned using proper training/validation separation.
5. Evaluate held-out **entire sensor locations** from experiments, not individual time points from the same sensor scattered across train and test; prevent replicate or configuration leakage.
6. For a CFD field, extract **virtual sensors** at experimental layouts and compare reconstructions to the dense original CFD field; report separately from experimental truth.
7. Measure RMSE, MAE, bias, accuracy versus sensor density, runtime and (where meaningful) uncertainty/calibration.
8. Assess apparent flow-rate consistency with the HVAC reading, carefully distinguishing measured scalar air speed from signed normal velocity.

**Potential extensions (not required for core delivery):** particle concentration or temperature reconstruction; CFD-assisted residual/bias modelling; conservation-constrained interpolation; comparison across HVAC operating cases; sensor-location optimisation; detailed inlet diffuser and leak/buoyancy modelling; a 3D surrogate model.

## 3. Sources supplied in the ChatGPT conversation

1. `MMA3001_2026_Project_Brief.pdf` — unit requirements, deliverables, grading rubric.
2. `dot_92576_DS1.pdf` — 261-page FAA/NRC technical report, *Communicable Disease Transmission in Air Travel: Jet Bridge Ventilation*, dated July 2026 (DOT/FAA/AM-25/28).
3. `dot_92577_DS3.zip` — raw/processed open-publication experimental dataset; extracted root `JetBridge_2026/`.
4. Starter case previously created: `JetBridge_S01_A_10_HN_1_OpenFOAM.zip`.
5. Starter repository previously created: `jetbridge-ml-cfd-starter.zip`, with `AGENTS.md` and `PROJECT_CONTEXT.md`, modular Python package, tests and included CFD case.
6. Geometry evidence: in the dataset's `00-Templates/Boundary - Summary - SWEMA.txt`; not just a stylised figure. Plots / CSV were previously generated (`jetbridge_side_profile.png`, `jetbridge_cross_section.png`, `jetbridge_critical_coordinates.csv`).

The report names dataset DOI `https://doi.org/10.21949/qqdx-gh59`. **Public accessibility does not by itself establish permission to redistribute every file**; check the data's licence before pushing raw datasets to a public GitHub repo.

## 4. Experimental system and dataset

The data covers a **laboratory mock-up passenger boarding bridge**, along with operational jet-bridge observations. The laboratory setup is appropriate for a CFD comparison because it provides controlled operating conditions and measured ventilation flow rates.

Main variables:
- **Air-speed magnitude** from SWEMA hot-sphere probes (m/s), generally **not** the three signed components of velocity.
- Air temperature (°C), pressure/differential pressure and HVAC variables.
- Particle size-bin concentrations (UPAS; units depend on the exported variable/file, often counts per cm³).
- Tracer-gas CO₂ for relevant experiments.
- Coordinates of measurement points and experiment identifiers / replicates.
- HVAC supply flow readings: `Q.FS1`, `Q.FS2`, `Q.FS3`, and combined `Q.FS`, commonly in **L/s**.

Useful archive folder groups include `00-Templates`, `01-CSV`, `02-TXT`, `03-Averages`, `04-Summary`, `05-HVAC`, `06-Periods`, and `Data Dictionary.csv`.

Spatial layouts documented in the report:
- Typical air-speed measurement plane: **2 columns × 6 rows = 12 sensors**.
- Selected finer inlet air-speed layout: **4 × 6 = 24 sensor positions** (sometimes collected by repositioning a smaller physical array).
- Particle concentration: typical **2 × 4 = 8**, with selected **4 × 7 = 28** per plane; selected tests include multiple streamwise planes.
- Nominal stations along the bridge **z** axis: **10, 16, 22, 28, 34, 40, 46, 52, 58 ft**.

**Do not treat all these measurements as a simultaneous full 3D velocity field.** Some sensor planes and fine-grid positions were sampled sequentially, and sensor probes measure air-speed magnitude rather than vector velocity.

The FAA report's grid-resolution research topics (hypotheses 5.a–5.d) explicitly motivate studying sensor density and comparisons of air-speed / particle distributions with CFD.

## 5. Existing physical discrepancy motivating the investigation

The user has **already worked with this dataset in OpenFOAM** and used the **measured HVAC supply volumetric flow rate in L/s** as the prescribed inlet boundary condition. In a steady incompressible CFD case with sealed walls, calculated inlet and outlet flows agree by conservation. But the spatial experimental air-speed measurements do not correspond straightforwardly to the same inferred net flow; the user reported **higher upstream** and **lower downstream** measured velocities / inferred velocity distributions.

**No cause has been established and no quantitative station-by-station discrepancy analysis is yet completed.** Do not declare CFD, HVAC, or sensor measurements wrong based on the qualitative comparison alone.

Possible reasons to test (hypotheses only):
- Scalar speed magnitude vs signed normal velocity and uncertainty in flow direction.
- Very sparse cross-sectional sampling / missed jets or high-speed near-wall regions.
- Inlet diffuser / perforated door producing a nonuniform inflow not represented by a uniform full-face CFD boundary.
- Measurement-time mismatch, air-speed time averaging, sequential stations, sensor calibration and instrument uncertainty.
- Leakage / infiltration (the HVAC `Q.FS` is upstream supplied flow, not guaranteed net flux at every cross-section).
- Bridge-to-lab pressure, thermal effects/buoyancy, turbulence model and geometry errors.
- Inconsistent experiment ID, operating condition, pressure mode or flow direction between measurement and CFD case.

A useful equation for the **CFD vector field** is the sectional volumetric flux:

`Q(z) = integral_A U(x,y,z) · n dA`  (m³/s)

For a nominal constant-height duct, `A = width × height`, but a reconstruction using only measured **speed** `|U|` does **not** give exact signed flux without an additional justified unidirectional-flow assumption. Avoid silently converting local scalar magnitudes into the axial component.

Possible reported flow discrepancy metric (if physically meaningful):

`epsilon_Q = abs(Q_estimate - Q_FS) / Q_FS × 100%`

A model forced to match `Q_FS` has used that observation as a constraint: its agreement with `Q_FS` is **not independent validation**. Continue evaluating against withheld experimental sensor locations.

## 6. OpenFOAM baseline case already prepared

**Case ID:** `S01-A-10-HN-1` — empty bridge, approximately isothermal, neutral bridge pressure, with experimental air-speed sensors nominally at the 10 ft plane.

The case-specific HVAC file yielded an **unfiltered arithmetic mean of 58 valid `Q.FS` readings**:

- **533.866 L/s** (rounded: 533.87 L/s)
- **0.533866 m³/s**, imposed as inlet volumetric flow rate
- Nominal duct area approx **3.39 m²** (1.388618 × 2.441448)
- Bulk velocity approx **0.1575 m/s**

This average is specific to the chosen file and **not** automatically the mean of every run in its scenario. If quasi-steady periods are specified in `06-Periods`, examine using them rather than the unfiltered mean.

Existing case uses:
- `simpleFoam` (steady incompressible RANS); k-ε turbulence model (initial engineering assumption, not validated).
- `blockMesh` with 3 adjoining blocks representing sloped-flat-sloped bridge, nominal **141,312 hex cells**.
- `flowRateInletVelocity` at **z = 18.10512 m** (upper end) with Q given in m³/s.
- Pressure outlet at **z = 0 m** (lower end), no-slip walls, simplified full-face inlet/outlet.
- Probe coordinates at 12 experimental sensor locations, post-processing scripts and README.

**Status:** Input files were created and inspected statically. **`blockMesh`, `checkMesh`, and the CFD solver were not run in the previous ChatGPT environment**, so geometry conformity, convergence, mass balance and sensor agreement remain to be established on the user's installed OpenFOAM version. The high-fidelity diffuser, leakage paths, fan details, particle physics and buoyancy are *not* included in the baseline.

Suggested first commands in a sourced OpenFOAM shell:

```bash
cd cfd/cases/empty_bridge_s01_a_10_hn_1
python3 scripts/verify_setup.py
blockMesh
checkMesh
simpleFoam
python3 scripts/compare_probe_speeds.py
```

Check case compatibility with the installed OpenFOAM version, especially solver naming / boundary-condition dictionaries. Run a mesh-independence check and inspect flow fluxes across intermediate planes before interpreting physical results.

## 7. Critical geometry and coordinate mapping — highest-priority correction

The user reported that **Codex detected a height/coordinate issue**, including needing correct conversion for OpenFOAM. The full laboratory bridge geometry is defined in the supplied dataset's `00-Templates/Boundary - Summary - SWEMA.txt`, **already using metres**, and should be treated as the reference for the baseline model.

### Axis convention (source and OpenFOAM)

- `x` is the **bridge width** (from left wall): `0` to **1.388618 m**.
- `y` is the **absolute vertical elevation above the lab floor** (not height above the local bridge floor).
- `z` is the **longitudinal position**: `0` at downhill/exhaust end to **18.10512 m** at uphill/supply end.
- Air flows approximately toward **negative z**, from supply at 18.10512 m to exhaust at 0 m.
- `convertToMeters 1;` is appropriate for the existing SI-valued `blockMeshDict`; **do not divide or multiply these template coordinates again**.
- Dataset **station labels in feet** do require conversion: `z_m = station_ft × 0.3048` (unless the underlying file provides a more precise actual measurement coordinate; use that when available).
- Dataset **local sensor height** `y'` must be converted to global `y` by adding the bridge-floor elevation at the relevant streamwise station. Prefer actual source-file coordinates and documented station elevations rather than inferred rounded geometry.

### Four critical cross-sectional stations — exact template values

| Plane | z (m) | Floor y (m) | Ceiling y (m) |
|---|---:|---:|---:|
| P0 lower end | 0.000000 | 0.000000 | 2.441448 |
| P1 first slope end | 8.293100 | 0.673100 | 3.114548 |
| P2 flat section end | 10.096500 | 0.673100 | 3.114548 |
| P3 upper end | 18.105120 | 1.343025 | **3.784600** |

At **each** plane, the left and right corners occur at `x = 0` and `x = 1.388618`; hence the nominal 16 3D corner vertices are `(x, floor/ceiling y, z)` with the two x-values at each of the four planes.

Segment geometry:

| Section | z range (m) | Horizontal length (m) | Floor rise (m) | Floor slope |
|---|---|---:|---:|---:|
| A | 0 → 8.29310 | 8.29310 | +0.67310 | ≈ 4.640° |
| B | 8.29310 → 10.09650 | 1.80340 | 0.00000 | 0° |
| C | 10.09650 → 18.10512 | 8.00862 | +0.669925 | ≈ 4.782° |

Nominal internal clear height approximately **2.441448 m**, width **1.388618 m**, length **18.10512 m**. The published final template ceiling **3.784600 m** minus final floor **1.343025 m** equals **2.441575 m**, a **0.000127 m (0.127 mm)** difference from 2.441448 m. In the previously generated `blockMeshDict`, the upper-end ceiling was set instead to **3.784473 m**, maintaining *exactly constant internal clear height* but not matching the source template's final top coordinate. **Codex must explicitly inspect and reconcile this tiny source/template-versus-constant-height difference, document the decision, then rerun mesh checks.** Do not silently change it. The more consequential errors may be axis or feet-to-metres mapping, which should be checked first.

### Nominal station positions in metres

| Station (ft) | z (m) |
|---:|---:|
| 10 | 3.0480 |
| 16 | 4.8768 |
| 22 | 6.7056 |
| 28 | 8.5344 |
| 34 | 10.3632 |
| 40 | 12.1920 |
| 46 | 14.0208 |
| 52 | 15.8496 |
| 58 | 17.6784 |

The first bridge section rises, then floor is flat in B, and rises again through C. **`y` cannot simply be treated as a uniform local height from zero at all z locations.** Probe locations should be overlaid on the corrected cross-section and side-view to check for points in walls/outside the volume.

## 8. Comparison / validation design

Keep **three reference concepts** distinct:

1. **Experimental measurements:** physical but sparse, uncertain, scalar-speed observations; independently measured HVAC supply flow. Use complete withheld sensor locations for experimental prediction evaluation. Avoid using held-out data for tuning.
2. **OpenFOAM solution:** a full numerical field which, after checking mesh quality / solver convergence / boundary conditions, can serve as a **dense numerical reference** for virtual sensor experiments. **Not automatically experimental ground truth.**
3. **Interpolation/ML reconstructions:** predictions generated from identical retained experimental or virtual sensor inputs. Benchmark each method with consistent splits, metrics and computation settings.

Proposed experiment series:
- **A. Analytical smoke tests:** exact 2D functions, constant/linear fields, unit and coordinate checks; make numerical code verifiably correct before using uncertain engineering data.
- **B. CFD virtual sensor test:** sample the dense numerical field at actual 12/24 layouts and reduced sensor subsets, reconstruct a plane, compare at *unseen CFD grid points*; quantify RMSE/MAE and integral / peak errors. Repeat at multiple z planes and mesh levels where useful.
- **C. Experimental withheld-sensor test:** on one operating configuration, train on some complete locations and predict held-out points; compare traditional interpolation, GPR and baseline physics where supported.
- **D. Integrated-flow analysis:** calculate `Q(z)` directly from CFD *signed axial flux*; compare with any apparent experimental reconstruction **only under stated assumptions**; do not equate speed-magnitude integrals with measured net volumetric flux as a matter of fact.
- **E. Optional physics-informed constraint / correction:** impose supplied flow or learn CFD–experiment residual, but identify training inputs and retain independent test data.

Evaluation: RMSE, MAE, mean bias, spatial error maps, relative errors only where well-conditioned, runtime/training and prediction cost, sensitivity to number/location of sensors, wall extrapolation and uncertainty. Report failure modes and unsupported extrapolation.

## 9. Repository, Codex, WSL and modularity

Recommended repository: **one Git root**, in e.g. WSL at `/home/<linux-user>/projects/jetbridge-ml-cfd/` when OpenFOAM is on WSL, or Windows at `C:\Users\<user>\Documents\GitHub\jetbridge-ml-cfd\` when developing mainly with Windows-native tools. If using OpenFOAM under WSL, keep its simulation files in the WSL filesystem for more reliable Linux filesystem performance.

Recommended structure (the prior starter already uses this architecture):

```text
jetbridge-ml-cfd/                 <-- Open this root in VS Code; single .git here
├── AGENTS.md                     <-- Agent working rules
├── PROJECT_CONTEXT.md            <-- Existing concise context
├── CODEX_HANDOFF.md              <-- This expanded history/handoff
├── README.md
├── pyproject.toml
├── cfd/
│   └── cases/
│       └── empty_bridge_s01_a_10_hn_1/
│           ├── 0/
│           ├── constant/
│           ├── system/
│           ├── scripts/
│           └── data/
├── src/jetbridge_ml/
│   ├── data_processing/
│   ├── interpolation/
│   ├── machine_learning/
│   ├── validation/
│   └── cfd_interface/
├── data/raw/                   <-- large data ignored by Git
├── data/processed/             <-- generated datasets ignored by Git
├── docs/
├── examples/
├── scripts/
└── tests/
```

A **Python module** is a Python file / package under `src/jetbridge_ml` separated by responsibility; `cfd/` is a separate functional area with OpenFOAM cases. They are **not separate Git repositories or Git submodules**. Install the Python package in editable mode, e.g. `python -m pip install -e '.[dev]'`, then run `python -m pytest -q`.

VS Code + the Codex extension was recommended as the main development environment, with Codex desktop for broader work planning / delegation. The same local repo can be opened from either, but avoid simultaneous agents changing the same files without branch/worktree isolation.

The starter repository was reported to pass **five initial Python unit tests** and static CFD checks, but this does not establish valid CFD or ML outcomes. Record local environment versions and rerun the tests; do not rely on a summary of earlier test execution without checking.

`AGENTS.md` should direct Codex to read this file and `PROJECT_CONTEXT.md`. Scientific decisions, mesh/boundary changes and AI assistance should be documented in `docs/`.

## 10. Requested diagrams, visuals and previous outputs

Previously created visual references:
- `jet_bridge_cfd_and_machine_learning_workflow.png`: seven-stage high-level dataset → processing → OpenFOAM → interpolation → ML → validation → outputs schematic.
- `jet_bridge_geometry_and_cfd_setup.png`: conceptual geometry and mesh sketch, **illustrative** rather than machine-readable boundary data; use the extracted template for exact coordinates.
- `jetbridge_outputs/jetbridge_side_profile.png`: source-based z/y floor and ceiling plot.
- `jetbridge_outputs/jetbridge_cross_section.png`: x/y cross-section plot.
- `jetbridge_outputs/jetbridge_critical_coordinates.csv`: critical profile breakpoints.

The source-based plots are better geometry evidence than the stylised infographic.

## 11. Priority actions for Codex — in order

**Immediate priority: geometry verification, not expanding model complexity.**

1. Read `AGENTS.md`, `PROJECT_CONTEXT.md`, this file, the experimental data dictionary, source boundary template, case README and `system/blockMeshDict`.
2. Build a **geometry audit script** which extracts x/y/z edge coordinates from the original template and compares each of the 16 case vertices; report deltas and identify the 0.127 mm final-ceiling discrepancy explicitly.
3. Verify sensor coordinate frames and units, especially `y'` (height above bridge floor) vs `y` (absolute height above lab floor), and 10–58 ft labels vs metre positions. Make a 3D wireframe + side view + section plots overlaying all sensor points and flags for outside-domain points.
4. Fix only confirmed errors; document the before/after vertex table, changes and the reasons. Keep source-unit and converted values side by side if helpful.
5. On user's OpenFOAM installation, run `blockMesh`, `checkMesh`, `simpleFoam`; capture versions and results, check mass balance and flux across every sensor plane, check convergence and probe extraction.
6. Confirm case-specific `Q.FS` from appropriate quasi-steady HVAC periods and create a repeatable inlet-flow generator rather than hard-coded one-off numbers.
7. Build the parser with robust missing value handling, independent sensor IDs/coordinates, replications, units and scenario metadata.
8. Then implement fair interpolation vs GPR benchmark, baseline and statistical/physical validation; only after this consider more complex CFD or physics-informed methods.

**Do not:** claim the source data are internally inconsistent without a demonstrated calculation; use interpolated scalar speed as exact net mass flux; mix experiment cases silently; calibrate models using held-out validation sensors; assume a conserved CFD field is experimental truth; publish huge data/mesh outputs into Git; or silently alter the scope without approval.

## 12. Copy/paste first Codex prompt

> Read `AGENTS.md`, `PROJECT_CONTEXT.md`, `CODEX_HANDOFF.md`, the source FAA/NRC boundary template and the existing OpenFOAM case, without modifying files yet. Prioritise a numerical audit of the geometry and coordinate conversions. Verify bridge width/height/slope breakpoints, metres versus feet, global `y` versus local `y'`, and every blockMesh vertex against the template. Specifically investigate the final upper-ceiling coordinate (`3.784600 m` in source versus `3.784473 m` in the starter model). Summarise exact mismatches with source line/file references and propose a minimal patch and a plot-based validation plan. Only modify code after I review that plan. Avoid claiming CFD is validated until the local `blockMesh`, `checkMesh`, solver, and flux checks have run.

## Current demo and quality workflow on 27 October 2026
The repository now includes the attributed study input subset and compact archived numerical evidence. Use the root run_all.py driver and docs/LIVE_DEMO.md for one-clone execution; older commands above describe the original research runs. Static checking uses python -m ruff check src tests run_all.py; numerical tests use python -m pytest -q; API documentation uses python -m pdoc jetbridge_ml -o docs/html. See docs/DEVELOPMENT.md for scope and limitations. Live/full execute fresh isothermal CFD in new output folders; archived unconverged thermal evidence remains explicitly separate.
