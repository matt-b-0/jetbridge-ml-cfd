# Assumptions and uncertainties (living log)

- **Scalar air speed vs vector flux:** SWEMA measurements provide magnitudes; signed cross-sectional flux requires axial component or a stated approximation.
- **Nominal inlet flux:** the CFD inlet uses the replicate-specific mean HVAC supply flow (`Q.FS`), not a measured net flux at a downstream cross section.
- **Sealed CFD, potentially leaky experiment:** CFD conservation does not establish identical physical flux at all lab planes.
- **Steady RANS:** the baseline `simpleFoam` k-epsilon model assumes steady incompressible isothermal flow, with idealised inlet/outlet faces and no explicitly modelled gaps or diffuser holes.
- **Sparse and asynchronous measurements:** not a synchronized 3D velocity field; group data by experiments and stations.
- **Interpolation and extrapolation:** do not claim reconstructed values in unsampled regions are validated solely because maps look smooth.
- **Data licences:** confirm the released dataset terms before publicly copying raw inputs into the GitHub repo.
- Experimental interpolation baseline: use published entire-record replicate means and absolute x/y metre coordinates, with a separate fit per replicate and no pooled repeats. Fixed nearest/linear/thin-plate-spline RBF settings are exploratory. Linear unsupported predictions remain missing; report common-hull and extrapolation scores separately. No CFD or supplied-flow constraint is used.
- Thermal extension S01-AC-10-HN-1: inlet and ambient temperatures/flow from matched HVAC windows; fixed walls at lab temperature are a surrogate, not measured wall temperatures or an exact adiabatic reconstruction. Steady Boussinesq with vertical gravity and unchanged baseline geometry. Initial trial diverged; stronger-relaxation restart is bounded but unconverged. Do not use either as validated CFD truth. See thermal_case_results.md.
- Numerical stability study: synthetic diffusion and weighted-Jacobi examples verify numerical mechanisms only; they do not diagnose the nonlinear CFD failure. Actual-layout interpolation noise gains are worst-case sensitivity bounds, not accuracy or instrument-uncertainty estimates. Steady SIMPLE has no physical time-step CFL interpretation. Prior thermal relaxation comparison is confounded by changed initialization.
