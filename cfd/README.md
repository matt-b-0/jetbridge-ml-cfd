# CFD workspace

Each subdirectory inside `cases/` is an independent OpenFOAM case (its own `0/`, `constant/`, `system/`, and `Allrun`). Work from **the case directory**, not the repository root. Do not create a second `.git` here. Python postprocessing tools belong in `src/jetbridge_ml/cfd_interface/`; a case can still have one-off scripts under its own `scripts/`.

The included `empty_bridge_s01_a_10_hn_1` case is a simplified **unverified** initial baseline using the measured HVAC `Q.FS`. See its README for geometrical assumptions, probes, flux checks, and caveats. Store finished CFD outputs externally or in the ignored case folder; never commit large result/time directories.
