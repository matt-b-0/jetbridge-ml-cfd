# Jet bridge OpenFOAM baseline — S01-A-10-HN-1

**Status:** complete OpenFOAM input case and 3-block mesh definition; **not solved or checked with OpenFOAM in this environment** (OpenFOAM executables are unavailable here). Run `blockMesh`, `checkMesh` and `simpleFoam` on your system and inspect logs before treating results as credible.

## Experiment selected

- Dataset: NRC/FAA *Communicable Disease Transmission in Air Travel: Jet Bridge Ventilation* (DOT/FAA/AM-25/28; 2026), open data: https://doi.org/10.21949/qqdx-gh59
- Case: **S01-A-10-HN-1** — empty bridge, approximately isothermal, neutral pressure, flow towards decreasing z; air speed measured 10 ft from exhaust.
- HVAC source: `05-HVAC/S01-A-10-HN-1.csv`, column `Q.FS (lps)`. In this file, 58 valid (nonnegative) readings, unfiltered **arithmetic mean 533.866 L/s**, median 536.900 L/s. Input used: **0.53386552 m³/s**. No quasi-steady-state filtering was done; review `06-Periods` if you need to match the exact averaging period for a publication-quality comparison. This file-specific mean need not equal the configuration-wide value quoted in the report.
- Measured air speeds for this exact replicate: `03-Averages/V-S01-A-10-HN-1.txt` (12 points, 2 x 6). Probe positions and mean speeds are converted to `data/processed/experimental_sensor_speeds.csv`.
- Missing values in source files are **-9999** and must not be included in averages.

## Geometry and coordinates

Geometry comes from the uploaded `00-Templates/Boundary - Summary - SWEMA.txt`, not an estimated rectangular box. The bridge is modelled as a constant-width, constant-clear-height duct with piecewise linear sloped floor:

| z (m) | floor elevation y (m) | width x (m) | clear height (m) |
|--:|--:|--:|--:|
| 0.00000 | 0.000000 | 1.388618 | 2.441448 |
| 8.29310 | 0.673100 | 1.388618 | 2.441448 |
| 10.09650 | 0.673100 | 1.388618 | 2.441448 |
| 18.10512 | 1.343025 | 1.388618 | 2.441448 |

Coordinate convention: **x across width**, **y upward from laboratory floor**, **z along bridge**, inlet at z=18.10512 m, outlet at z=0. The supply-end inlet is a full rectangular face, **not** the real three-duct perforated inlet diffuser. The outlet is a full rectangular face, **not** an explicitly modelled exhaust plenum. This is intentionally a first-order validation baseline.

- Inlet/outlet nominal normal area: **3.390239 m²**
- Nominal bulk normal speed: **0.157471 m/s** (mean over cross-section)
- `blockMesh` resolution: 24 x 32 x (84 + 18 + 82) = **141,312 hexahedral cells**
- Uniform block grading; no near-wall inflation yet. Start here for workflow checks, then do grid-convergence tests and adjust y+ / near-wall mesh according to turbulence treatment.

## Physics and boundaries

- `simpleFoam`, steady incompressible RANS with `kEpsilon` (initial engineering baseline; not validated as a model of this experiment).
- Air kinematic viscosity assumed `1.5e-5 m²/s`. No thermal/buoyancy calculation or particle tracking.
- `0/U` **inlet**: `flowRateInletVelocity; volumetricFlowRate constant 0.533865517;` (m³/s). For this upstream face the normal points along +z; incoming velocity points roughly along -z.
- `0/U` **outlet**: `pressureInletOutletVelocity`; `0/p` outlet `fixedValue 0` (kinematic gauge pressure). Walls no-slip; `k`, `epsilon`, `nut` use standard inlet/outlet conditions and wall functions.
- Turbulence initialisation assumes 5% turbulence intensity and length scale 7% of hydraulic diameter: k=9.299e-05 m²/s², epsilon=1.189e-06 m²/s³. **Assumptions**, not measured inputs.
- Pressure difference and mass balance must be validated, **not assumed to match experimental conditions**. HVAC Q.FS measures supply, not necessarily net flux downstream if physical leakage exists.
- Hot-sphere probes measure **air-speed magnitude**; comparison script uses `sqrt(Ux²+Uy²+Uz²)`. Do not treat experimental air-speed magnitude as the signed axial velocity needed for exact net flux integration.

## Run

Install/source an OpenFOAM variant providing `simpleFoam`, e.g. an OpenFOAM.com release supporting the included solver files.

```bash
cd JetBridge_S01_A_10_HN_1_OpenFOAM
blockMesh | tee log.blockMesh
checkMesh | tee log.checkMesh
simpleFoam | tee log.simpleFoam
python3 scripts/compare_probe_speeds.py
```

Alternatively run `./Allrun` after sourcing the OpenFOAM environment. Solver output is in `postProcessing/` and time directories. The sampling function object `sensors` extracts `U` and `p` at 12 real probe coordinates; `inletFlux` and `outletFlux` integrate `phi` over the inlet and outlet patches (signed outward flux; inlet negative, outlet positive). Check `log.simpleFoam` convergence and the patch flux results for mass conservation.

To update the input based on the HVAC readings:

```bash
python3 scripts/set_hvac_flow.py --statistic mean
# or --statistic median
```

`set_hvac_flow.py` changes Q but does not recompute U/k/epsilon initial guesses; this is okay for modest changes, but for large changes update all fields consistently.

## Validation workflow

1. Confirm `checkMesh` is clean and residuals fall to acceptable tolerances; verify Q_in+Q_out approaches zero.
2. Compare **CFD speed magnitude** at the same 12 spatial points, *not* an unpaired cross-sectional average. Run `scripts/compare_probe_speeds.py` for error metrics and CSV.
3. Repeat for matched stations/replicates, then test mesh resolution, inlet diffuser/profile, turbulence and leakage assumptions. **Do not claim CFD is ground truth simply because mass is conserved.**
4. The `simpleFoam` domain omits detailed diffuser perforations, wall leaks, manikins and heat transfer. More complex effects require additional physics, geometry and matching boundary-condition data.

## Included material

```text
0/                     U, p, k, epsilon, nut
constant/              transportProperties, turbulenceProperties
system/                blockMeshDict, controlDict, fvSchemes, fvSolution
data/source/            selected original FAA files (including precise geometry)
data/processed/         sensor positions, measurements, HVAC summary
scripts/               comparison script and HVAC boundary updater
Allrun / Allclean       execution helpers
```

Report acknowledgement: National Research Council of Canada / FAA, *Communicable Disease Transmission in Air Travel: Jet Bridge Ventilation*, DOT/FAA/AM-25/28 (July 2026), linked above. Confirm associated dataset terms before redistributing selected source files.
