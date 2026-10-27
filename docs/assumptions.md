# Assumptions and uncertainties (living log)

- **Scalar air speed vs vector flux:** SWEMA measurements provide magnitudes; signed cross-sectional flux requires axial component or a stated approximation.
- **Nominal inlet flux:** the CFD inlet uses the replicate-specific mean HVAC supply flow (`Q.FS`), not a measured net flux at a downstream cross section.
- **Sealed CFD, potentially leaky experiment:** CFD conservation does not establish identical physical flux at all lab planes.
- **Steady RANS:** the baseline `simpleFoam` k-epsilon model assumes steady incompressible isothermal flow, with idealised inlet/outlet faces and no explicitly modelled gaps or diffuser holes.
- **Sparse and asynchronous measurements:** not a synchronized 3D velocity field; group data by experiments and stations.
- **Interpolation and extrapolation:** do not claim reconstructed values in unsampled regions are validated solely because maps look smooth.
- **Data licences:** the official released dataset record was checked on 27 October 2026 and identifies CC BY 4.0. Selected original records are included unchanged under data/demo with attribution and hashes. This does not assign the still-undecided project-code licence.
- Experimental interpolation baseline: use published entire-record replicate means and absolute x/y metre coordinates, with a separate fit per replicate and no pooled repeats. Fixed nearest/linear/thin-plate-spline RBF settings are exploratory. Linear unsupported predictions remain missing; report common-hull and extrapolation scores separately. No CFD or supplied-flow constraint is used.
- Thermal extension S01-AC-10-HN-1: inlet and ambient temperatures/flow from matched HVAC windows; fixed walls at lab temperature are a surrogate, not measured wall temperatures or an exact adiabatic reconstruction. Steady Boussinesq with vertical gravity and unchanged baseline geometry. Initial trial diverged; stronger-relaxation restart is bounded but unconverged. Do not use either as validated CFD truth. See thermal_case_results.md.
- Numerical stability study: synthetic diffusion and weighted-Jacobi examples verify numerical mechanisms only; they do not diagnose the nonlinear CFD failure. Actual-layout interpolation noise gains are worst-case sensitivity bounds, not accuracy or instrument-uncertainty estimates. Steady SIMPLE has no physical time-step CFL interpretation. Prior thermal relaxation comparison is confounded by changed initialization.

## CFD virtual-sensor SVR (2026-10-24)
The model uses scalar speed from the converged isothermal field only. Training stations and final withheld planes are disjoint; both are sampled with cellPoint. Baselines share training-only standardized 3D coordinates. Full-plane wall extrapolation is reported separately from the common sensor hull. SVR solver-iteration diagnostics are not neural-network epochs or PDE stability evidence. See cfd_svr_benchmark.md.

## Report visualisation (2026-10-24)
The report collection uses common physical coordinates and cellPoint field sampling; sensor comparison panels retain the earlier cell-sampling convention. Uniform plane-sample statistics do not replace mesh-integrated flux or physical validation. Buoyant iteration 967 remains provisional and is labelled NOT CONVERGED. See report_figures.md for numerical status, rendering details and captions.

## Four-workstream evaluation (2026-10-24)
Experimental SVR tuning is nested inside held-location folds with separate fits per replicate and shared training-only standardized coordinates. CFD density designs are exploratory and non-nested; hybrid designs were added after boundary-heavy results, and evaluation uses disjoint spatial sample grids from one numerical field. The 58 ft A/B HVAC windows remain separate. Raw inch coordinates are nominal local values, not replacements for published absolute metre coordinates. Thermal continuation preserves physics/relaxation and fails residual/probe stationarity checks at 1967; low flux imbalance alone is insufficient. See four_workstreams_results.md.

## Submission workflow and extra checks (2026-10-24)
The arithmetic-mean baseline uses only retained sensors. Paired results remain descriptive at run/station/layout level; station and density are confounded at 58 ft. Three isothermal meshes and an 80%-flow synthetic case quantify sensitivity/transfer without a mesh-independence or physical-validation claim. Nominal-inch positions are an alternative mapping only. Flow transfer refits models on retained values while keeping layouts fixed. The curated gallery contains derived summaries, not raw data or dense predictions. See project_improvements.md.

## Final report review on 26 October 2026
The expanded C = 0.01 nested search is a post-hoc exploratory sensitivity, not a replacement for the primary predeclared comparison or an untouched test. No outer sensor target enters its own tuning. The first 58 ft replicate shows unphysical negative RBF extrapolation; maps show it without clipping. Full-array fields are illustrative fits and held-location errors are separate. Independent Gaussian perturbations are a scenario; correlated physical variations could change the comparison. The student explicitly left the licence undecided and the AI statement unchanged.

## Portable demo inputs on 27 October 2026
The FAA/NRC official release record identifies CC BY 4.0. Selected original inputs are bundled unchanged with attribution and hashes; this does not select a project-code licence. Demo replay and archived thermal diagnostics are not new CFD simulations. Live solves the baseline; full also solves mesh/flow cases. Both retain the original physical assumptions and reject failed new CFD before reference fitting. No historical comparison is relabelled as a newly validated experiment.

