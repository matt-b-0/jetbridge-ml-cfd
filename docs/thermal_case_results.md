# Thermal CFD trial — 24 October 2026

## Outcome
A separate cold-supply thermal case and zero-gravity control were run for S01-AC-10-HN-1. The original thermal steady solve FAILED NUMERICALLY. A stronger-relaxation restart remained bounded but did not converge. Neither buoyant result is experimentally validated or suitable as a trusted dense reference for interpolation/ML.

All 19 Python tests passed. The tests verify source parsing, units, averaging-window matching and setup logic, not CFD physics.

## Matched source inputs
From 56 valid observations per HVAC variable in 05-HVAC/S01-AC-10-HN-1.csv, using the matching Periods.csv interval 1744666320–1744666600 inclusive:
- Supply: 21.2892857°C = 294.4392857 K.
- Lab: 24.375°C = 297.525 K.
- Differential: supply minus lab = -3.0857143 K.
- Supply flow: 531.7607143 L/s = 0.5317607143 m3/s.

The stable interval equals the entire-set interval for this run. The speed/temperature means in 03-Averages are whole-record statistics at identical absolute metre coordinates. These are scalar air speeds and Celsius temperatures. No source files were modified.

## Model and assumptions
OpenCFD v2412 patch 260127, buoyantBoussinesqSimpleFoam, steady incompressible Boussinesq k-epsilon, gravity in negative y. The 141,312-cell geometry is unchanged, including the known upper-ceiling discrepancy. beta=1/Tlab_K gives beta*abs(deltaT)=0.0103713, approximately 1.04% relative density variation over imposed boundary temperatures.

Walls are fixed at LAB temperature as an explicit surrogate, NOT measured wall temperature. This is not an exact reconstruction of A/AC adiabatic wall conditions. Initial/backflow temperature is lab temperature. Full-face supply, sealed walls, simplified reduced-pressure outlet and first-order upwind schemes are retained. No explicit buoyancy turbulence-production correction or conjugate wall heat conduction is included. See the case README for all dictionaries and reproducibility commands.

The zero-gravity control has identical flow, temperatures, thermal boundaries, mesh and turbulence treatment; only gravity is disabled. No wall temperatures, physical coefficients or inlet values were fitted to the experimental sensor errors.

## Numerical outcomes
| Run | Iterations | Saved field compared | Status |
|---|---:|---:|---|
| Initial buoyant case | 3000 | 3000 | Numerical failure |
| Zero-gravity control | 733 | 733 | Met configured residual criteria |
| Stronger-relaxation buoyant restart | 1000 | 967 | Bounded but NOT CONVERGED |

The initial run reached maximum speed approximately 62,288 m/s and temperature maximum 297.727519 K, exceeding its fixed boundary range. Final outlet flow approximately 0.541184 m3/s versus inlet 0.531761 m3/s gives roughly 1.77% imbalance. This is a numerical failure; its sensor errors are not meaningful physical accuracy statistics. Close net flow earlier in the run did not establish stability.

The stabilization attempt starts from the control's converged field and reduces pressure/U/T/turbulence relaxation to 0.1/0.1/0.2/0.3, with unchanged physical boundaries and a 1000-iteration cap. At the last saved field:
- Maximum speed 1.427448 m/s; temperatures 294.4392857–297.525 K, with no boundary overshoot detected.
- Signed inlet/outlet flow -0.5317607143 / +0.5317616106 m3/s; relative imbalance approximately 0.000169%.
- Corrected probe-temperature range in snapshot-967 window [867,967] is 0.1324055 K, so stationarity is not established. The former 0.1723 K report incorrectly included later probe records; the final-iteration-1000 audit gives 0.1187674 K over [900,1000]. See numerical_stability_study.md.
- Final solver residuals at iteration 1000 remain above requested criteria: Ux 0.00134348, Uy 0.00049360, Uz 0.00052115, T 0.000293997, first p_rgh 0.0341527, epsilon 0.00086272, k 0.00086320.

The copied warm-start field retained its previous output time index, shifting saved time folders to 67,167,...,967. The run ended at 1000, but field comparisons explicitly use saved iteration 967, not an invented final-1000 field. SIMPLE iteration is not physical time.

## Provisional sensor comparison
These numbers describe saved iterates; the buoyant case has not passed convergence/stationarity checks.
| Quantity | Zero-gravity control (733) | Buoyant restart snapshot (967) |
|---|---:|---:|
| Speed RMSE (m/s) | 0.132615 | 0.156200 |
| Speed bias (m/s) | +0.012785 | +0.142401 |
| Temperature RMSE (K) | 1.512919 | 0.641174 |
| Temperature bias (K) | -1.406683 | +0.197005 |

The buoyant snapshot shows a cold lower layer and warmer upper region, but the velocity agreement is worse than the control and the temperature/probe field still evolves. This cannot establish a successful thermal validation or a root cause of the project discrepancy.

## Reproducibility and files
Tracked input case: cfd/cases/thermal_bridge_s01_ac_10_hn_1/. Its prepare.py regenerates the source-derived inputs in a new output folder. stabilize.py documents the warm-start and relaxation procedure. Export/plots: python -m jetbridge_ml.cfd_interface.plot_thermal.

Runtime cases in WSL:
- /home/mattb/projects/jetbridge-thermal-s01-ac-10-hn-1
- /home/mattb/projects/jetbridge-thermal-control-s01-ac-10-hn-1
- /home/mattb/projects/jetbridge-thermal-stabilized-s01-ac-10-hn-1

Local provisional figures/data: ignored data/processed/thermal_visuals/. Source records, generated meshes, time fields and figures are not committed. Failed-run diagnostics remain separately in /home/mattb/projects/jetbridge-thermal-failed-diagnostics-20261024.

Figures include speed/temperature cross-sections and point deltas, height profiles against control, longitudinal slices, and residual/probe histories. PNG and PDF versions are generated. The longitudinal contour rendering is clipped to the actual piecewise bridge outline to avoid filling outside the concave domain. Input/run/script hashes and exact sampling time are saved with exported metrics. Sample coordinates are checked; speed magnitude is compared to speed magnitude.

## Next scientific checks
Do not use these buoyant fields as validated training/benchmark truth. Investigate numerical robustness, a transient buoyant formulation with appropriate time-step/time-convergence checks, wall thermal boundary evidence or conjugate heat transfer, buoyant turbulence treatment, wall resolution/y+, energy balance, mesh sensitivity, pressure/backflow assumptions and diffuser representation. No parameters should be tuned on final test sensors. Keep this thermal extension bounded so the interpolation-versus-ML comparison remains the main project objective.
