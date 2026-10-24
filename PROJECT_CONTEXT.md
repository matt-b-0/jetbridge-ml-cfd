# Project context — MMA3001 Jet Bridge CFD + Numerical Interpolation + ML

**Status:** working project proposal and starter code; research scope and any student-proposed dataset usage require teaching-team approval per the MMA3001 brief. This is a concise handoff summary from earlier discussion, not a verbatim chat export.

## Academic objective
The MMA3001 (Numerical Methods and Machine Learning) individual project requires an engineering problem, numerical/ML method, credible baseline, validation, performance/sensitivity analysis where appropriate, a functional reproducible GitHub repository, documentation, tests, transparent AI-use reflection, a 5–10 page written report, and a short individual presentation. Scientific understanding and justifying method choices matter more than choosing complex models.

## Working research question
> How accurately can conventional interpolation and machine learning reconstruct sparse experimental jet-bridge air-speed distributions, and what can CFD-assisted virtual sensor experiments reveal about spatial sampling bias and consistency with HVAC-supplied flow rates?

Possible title: **Numerical Interpolation and Machine Learning for Sparse Jet Bridge Flow Reconstruction with OpenFOAM-Based Evaluation**.

The key issue is comparing **local predictive performance** at sensor coordinates with **global flow-rate consistency**. These are different constraints; enforcing the known HVAC flow rate does not validate the reconstructed spatial field.

## Sources
1. `MMA3001_2026_Project_Brief.pdf` — user's assessment document (not bundled; keep/source locally in docs/references as permitted).
2. FAA/NRC DOT/FAA/AM-25/28, *Communicable Disease Transmission in Air Travel: Jet Bridge Ventilation* (July 2026). Dataset DOI: https://doi.org/10.21949/qqdx-gh59. Associated 261-page report supplied by user (not bundled).
3. Original dataset archive `dot_92577_DS3.zip` / `JetBridge_2026/` supplied by user (not bundled in this starter; archive ~80 MB). Check distribution rights/licence before posting original data files publicly.
4. CFD proof-of-concept case generated previously for `S01-A-10-HN-1`, included at `cfd/cases/empty_bridge_s01_a_10_hn_1/`. The included README is specific to the simulation case.

## Dataset and experimental method
- Categories include air speed (SWEMA hot-sphere probes), temperature, HVAC pressure/volumetric readings, tracer CO2 and particle size-bin concentrations (UPAS).
- 12-sensor (2x6) air-speed planar arrays are typical; 24-sensor (4x6) layouts were used at selected inlet tests. Particle layouts include 2x4 and a selected 4x7 arrangement. The report documents stations in feet along the z axis, e.g. 10, 16, 22, ... 58 ft.
- Cross-sectional arrays are sparse and some planes were measured sequentially. Do not interpret all sensor readings as a synchronized 3D vector field.
- Preserve replicate and scenario IDs in parsers and train/test splits. Always match sensor positions, case thermal conditions, direction, and experimental setting to CFD.
- The FAA work explicitly considers sensor count and comparison to CFD in its grid-resolution research themes (hypotheses 5.a–5.d).

## Important discovered discrepancy
The user's earlier OpenFOAM work imposed the volumetric flow rate **reported by the laboratory HVAC system**. Their CFD conserved inlet-to-outlet mass flux, but the experimental spatial air-speed samples appeared **high upstream and low downstream relative to CFD**. No root cause has been demonstrated. Candidates to test include sparse spatial sampling, scalar speed vs axial velocity, diffuser/inlet nonuniformity, wall leakage/infiltration, pressure conditions, turbulence and thermal effects, mismatched averaging/replicate windows.

## Selected CFD starter (baseline, not validated)
- Experimental case: `S01-A-10-HN-1`, empty bridge, approximately isothermal, neutral pressure, sensor plane at z = 3.05 m.
- In case-specific HVAC file, unfiltered mean of 58 valid `Q.FS` observations: **533.866 L/s = 0.533866 m³/s**. This is the *file-specific arithmetic mean*, not the full configuration-average reported elsewhere.
- Model: steady incompressible `simpleFoam`, k-epsilon RANS; this is an initial simplifying choice, not a vetted physics model.
- Source geometry from the archive boundary template: width 1.388618 m, internal clear height 2.441448 m, streamwise z 0 to 18.10512 m. Floor y(z) nodes: (0, 0), (8.29310, 0.67310), (10.09650, 0.67310), (18.10512, 1.343025).
- CFD domain uses full-face inlet (`flowRateInletVelocity` at upstream +z), pressure outlet at z=0, and no-slip walls. Real diffuser perforations, plenum, leakage and buoyancy omitted in baseline.
- Case has 12 experimental sensor coordinates at z=3.05 m and `probes` for U/p. Compare measured **speed magnitude** to `|U|`, not blindly to signed Uz. The original case report cautions it has not been run/solver-verified.
- `cfd/cases/empty_bridge_s01_a_10_hn_1/README.md` contains the exact solver configuration, caveats and commands.

## Planned computational comparison
1. Verify parsing, units, geometry and sensor coordinate mapping using the original source files.
2. Implement traditional baselines (nearest, linear, RBF), plus an ML model (initially Gaussian process regression), with the *same* train/test sensors.
3. For experimental validation, withhold complete sensor locations and keep experimental repeats/scenarios grouped to prevent leakage. Clearly separate hyperparameter selection from final testing.
4. For dense-field reconstruction, sample **virtual sensors** from OpenFOAM CFD planes and compare interpolated surfaces to the full CFD field. This measures agreement to the CFD numerical field, not experimental truth.
5. Quantify RMSE/MAE/bias at withheld locations; record computation and training time. Evaluate sample-resolution sensitivity and unsupported extrapolation.
6. Where physically justified, estimate apparent volumetric flux by integrating the **normal component**. For experimental scalar speed, report any unidirectional approximation explicitly. Compare with supplied `Q.FS` while acknowledging possible leakage and independent errors.
7. Optional: learn CFD discrepancy correction from training sensors or compare constrained vs unconstrained reconstruction. Neither should force outputs to match test values or be described as validation solely because Q matches.

## Desired outputs
- Professional Python package and a separate executable OpenFOAM case.
- Documented data handling, SI units, solver and interpolation assumptions.
- Matched CFD-vs-sensor plots at each station; virtual-sensor benchmarks and error vs sensor density.
- Quantitative local errors, integral consistency check, performance timings, convergence/sensitivity and limits.
- README, pdoc/HTML docs, tests, a licence selected by the user, project report and AI reflection.

## Open decisions
- Version of OpenFOAM on the user's workstation and whether CFD runs in WSL/Linux.
- Exact set of experiment configurations used for training/validation and whether simulation boundary conditions can reproduce them.
- Whether data licence allows public redistribution (DOI is public but a publication link alone does not establish blanket reuse permissions).
- Whether temperature and particle concentrations become extensions rather than core requirements.
- Exact presentation/submission dates; consult current unit materials rather than assuming.

## Work ownership and honesty
AI may assist with code planning, prototyping, tests, documentation and diagnostics, but the student must verify results, select assumptions and reflect on assistance. Do not describe a mesh, solver, or ML model as validated until the relevant checks have actually run.
