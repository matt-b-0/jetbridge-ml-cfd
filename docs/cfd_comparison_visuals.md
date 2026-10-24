# CFD slice and sensor comparison figures

Generated from the saved iteration-237 field in /home/mattb/projects/jetbridge-baseline-20261024, with OpenCFD v2412, and FAA 03-Averages/V-S01-A-{station}-HN-1.txt at nine numeric stations.

## Interpretation
The baseline was selected using the HVAC flow for S01-A-10-HN-1. Only that run is treated as boundary-matched here; even its velocity averages and HVAC averaging window require further review. All other stations are exploratory comparisons to one unchanged CFD supply setting. They are not nine independently matched or validated simulations.

Delta is speed magnitude from CFD minus measured scalar mean, in m/s. Red indicates overprediction; blue underprediction. Dense differences are not plotted because the experiment provides sparse points, not a full measured plane.

At 10 ft: RMSE 0.040473 m/s, mean bias +0.037527 m/s. Across replicate 1 at other stations, mean differences change from positive at 10–40 ft to negative at 46–58 ft; 58 ft mean bias is -0.335888 m/s. The pattern is consistent with the earlier qualitative discrepancy, but neither the cause nor the adequacy of the simplified baseline is established.

## Export and coordinate checks
- Cutting planes use the published source z coordinates in metres, not nominal feet converted again.
- Dense slice vectors use OpenFOAM cellPoint interpolation for display. Sensor values use cell sampling, consistent with the existing default probes. Smooth slice colours and cell-sampled sensor values need not coincide exactly.
- Every sampled xyz is matched uniquely to its source sensor within 1e-7 m before differences are calculated. Sensor count, finite samples and the independent original 10 ft probe comparison are checked.
- The matched figure uses absolute y elevation. Galleries subtract the actual mesh floor for display only; source coordinates are unchanged.
- Gallery colour scales are shared across all nine planes. The matched three-panel figure shares one speed scale for measurements/CFD and a separate symmetric zero-centred delta scale.
- The 0.127 mm upper ceiling discrepancy is retained. Mesh sensitivity, wall treatment and experimental physical validation are outstanding.
- Sampling performs postprocessing only; the CFD solution and original dictionaries are unchanged. The export dictionary is stored in the results folder.
- The initial export failed because OpenFOAM rejected a working directory containing spaces; the workflow now launches postprocessing from the Linux case directory.

## Reproduce
Use the Python environment described in interpolation_workflow.md and a case with the saved final field:
```bash
python -m jetbridge_ml.cfd_interface.plot_comparison \
  --case /home/mattb/projects/jetbridge-baseline-20261024 \
  --dataset /mnt/c/Users/mattb_ar68ij9/Downloads/dot_92577_DS3/JetBridge_2026 \
  --output /home/mattb/projects/jetbridge-visuals-new
```
The output directory must be new. The default OpenFOAM bashrc path is /usr/lib/openfoam/openfoam2412/etc/bashrc; override with --foam-bashrc if required.

## Local deliverables
Results are under ignored data/processed/cfd_visuals/, each figure in PNG and PDF:
- matched_10ft_slice_and_delta: measured points, dense CFD slice, signed sensor differences.
- matched_10ft_profiles_and_errors: both sensor columns and per-sensor errors.
- cfd_nine_slices: same CFD simulation at all nine source planes.
- nine_station_sensor_deltas: point differences across nine planes, explicitly exploratory.
- sensor_deltas.csv and station_metrics.csv: underlying values and errors.
- cfd_slice_*ft.csv: exported xyz and velocity components.
- manifest.json: saved time, interpolation conventions, source hashes and limitations.
- sliceExportDict and log.sliceExport: exact export configuration and execution log.

The source dataset and generated outputs remain excluded from Git. The plotting command and this documentation are tracked.

Verification: all 16 Python tests passed. All four PNG figures were visually inspected for labels, axes, colour scales and layout. PDF versions were generated from the same Matplotlib figures.

