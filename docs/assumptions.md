# Assumptions and uncertainties (living log)

- **Scalar air speed vs vector flux:** SWEMA measurements provide magnitudes; signed cross-sectional flux requires axial component or a stated approximation.
- **Nominal inlet flux:** the CFD inlet uses the replicate-specific mean HVAC supply flow (`Q.FS`), not a measured net flux at a downstream cross section.
- **Sealed CFD, potentially leaky experiment:** CFD conservation does not establish identical physical flux at all lab planes.
- **Steady RANS:** the baseline `simpleFoam` k-epsilon model assumes steady incompressible isothermal flow, with idealised inlet/outlet faces and no explicitly modelled gaps or diffuser holes.
- **Sparse and asynchronous measurements:** not a synchronized 3D velocity field; group data by experiments and stations.
- **Interpolation and extrapolation:** do not claim reconstructed values in unsampled regions are validated solely because maps look smooth.
- **Data licences:** confirm the released dataset terms before publicly copying raw inputs into the GitHub repo.
