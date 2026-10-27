# Cold-supply thermal baseline: S01-AC-10-HN-1

This is a separate exploratory thermal model using buoyantBoussinesqSimpleFoam (OpenCFD v2412). It preserves the existing baseline geometry, including the known 0.127 mm upper-ceiling discrepancy, and the published absolute metre sensor coordinates. It does not modify the isothermal case.

## Source and thermal assumptions
HVAC readings are selected using the matching Periods.csv stable interval, 1744666320–1744666600 inclusive. In this run the stable and entire-set intervals match, so published whole-record speed and temperature means have the same nominal time window.

56 valid readings yield supply temperature 21.2892857°C = 294.4392857 K, lab temperature 24.375°C = 297.525 K, and Q=531.7607143 L/s = 0.5317607143 m3/s. Sentinels -9999 are excluded separately per variable.

- Cold inlet: fixed measured mean supply temperature.
- Initial interior: lab temperature.
- Walls: fixed lab mean temperature, a deliberately idealised heat-transfer surrogate. LAB TEMPERATURE IS NOT MEASURED WALL TEMPERATURE. This is not an exact reconstruction of the dataset's A/AC thermal boundary conditions.
- Outlet: pressureInletOutletVelocity and fixed reduced hydrostatic p_rgh=0; T inletOutlet uses lab temperature for any backflow. Experimental pressure mode is not fully reproduced by this simplification.
- Gravity (0,-9.81,0) respects y vertical and z along the sloping bridge.
- Boussinesq beta=1/Tlab_K and TRef=Tlab_K; maximum imposed beta*deltaT approximately 0.01037. Constant viscosity 1.5e-5 m2/s, Pr=0.71, Prt=0.85 are air-property/turbulence assumptions.
- k-epsilon with 5% inlet turbulence intensity and length scale 7% hydraulic diameter. No explicit buoyancy-production turbulence correction, conjugate wall conduction, diffuser detail or leaks.
- Steady, first-order upwind thermal/momentum convection; this is a baseline requiring mesh/physics sensitivity checks.
- Temperatures stored in OpenFOAM are Kelvin; plots and experimental comparisons use Celsius, and temperature differences have the same numerical value in K and °C.

A perfectly adiabatic steady duct without internal heat sources would approach the inlet temperature throughout; a sustained steady temperature differential requires explicit heat exchange. A zero-gravity CONTROL uses identical thermal inputs/BCs, differing only in gravity, to isolate modelled buoyancy effects.

## Reproduce
Install the project Python environment and source OpenFOAM. Generate a NEW Linux case directory:
```bash
python cfd/cases/thermal_bridge_s01_ac_10_hn_1/scripts/prepare.py \
 --dataset /path/to/JetBridge_2026 \
 --template cfd/cases/empty_bridge_s01_a_10_hn_1 \
 --output /home/mattb/projects/new-thermal-case
source /usr/lib/openfoam/openfoam2412/etc/bashrc
cd /home/mattb/projects/new-thermal-case
bash Allrun
```
For the control, generate another new directory with --no-buoyancy. The generator refuses to overwrite existing cases and refuses inconsistent sensor/HVAC averaging windows. It records source hashes, units, valid counts, thermal assumptions and parameters in data/processed/setup.json.

Numerical settings: three blocks / 141,312 cells, maximum 3000 SIMPLE iterations, relaxation U=0.3/T=0.5/p_rgh=0.3, residual criteria p_rgh/U/k/epsilon=1e-5 and T=1e-6. Check solver logs and recorded field bounds; reaching the iteration cap is not convergence.

Comparison command after both runs:
```bash
python -m jetbridge_ml.cfd_interface.plot_thermal \
 --case /home/mattb/projects/jetbridge-thermal-s01-ac-10-hn-1 \
 --control /home/mattb/projects/jetbridge-thermal-control-s01-ac-10-hn-1 \
 --output /home/mattb/projects/new-thermal-figures
```
This exports final saved speed/temperature planes and sensor values with source coordinates checked. It labels convergence status rather than assuming it.

Selected experimental records and archived diagnostic exports are now included under data/demo; full raw archives and large solved fields remain external. The runtime Linux case holds logs, fields and processed experiment data. Consult docs/thermal_case_results.md for actual run status and scientific limitations.

## Recorded run status

Initial buoyant run failed numerically by iteration 3000. Zero-gravity control met residual criteria at 733. A separate lower-relaxation warm start reached 1000 without convergence; last saved field 967. These are not validated thermal predictions. See ../../../docs/thermal_case_results.md (repository docs/thermal_case_results.md).

To reproduce the warm start, run scripts/stabilize.py with --thermal, --control, --control-time 733 and a new --output directory. It copies the converged control field, changes numerical relaxation only, and preserves the source thermal boundaries. The retained output time index means the first saved checkpoint may be at iteration 67 rather than 100; the exporter records the actual saved time.


## Bounded continuation audit
The new scripts/continue_saved.py copies a selected saved field into a fresh case, preserves physical and numerical settings, and extends the iteration cap. The recorded continuation from 967 to 1967 still failed residual and probe-stationarity checks; it is not a reference field or a validated thermal result. See docs/four_workstreams_results.md in the repository root for commands and diagnostics. Original case dictionaries and prior result figures are unchanged.

## Current one-clone demonstration
The root run_all.py driver regenerates thermal graphics from explicitly archived unconverged evidence; it does not claim a new successful thermal solve. See docs/LIVE_DEMO.md and docs/DEVELOPMENT.md in the repository root for profiles, python -m ruff check src tests run_all.py, pytest and API documentation. Existing physical assumptions and failed status remain unchanged.

