# Thermal and isothermal report figures

The reproducible collection contains 16 numbered figures, each as a 300 dpi PNG and a PDF with vector text/axes/linework (colour meshes rasterized), plus a contact sheet, figure captions, source manifests and a ZIP. Generated outputs are ignored by Git at `data/processed/report_figures/`. See `FIGURE_GUIDE.md` there for full captions and individual previews.

## Figure selection

| Figures | Purpose |
| --- | --- |
| 01 | Three-dimensional geometry and actual experimental sensor layout |
| 02–03 | Mid-width longitudinal speed and temperature contours |
| 04–07 | Nine-section speed galleries for all three cases, plus buoyant temperature sections |
| 08 | Buoyant snapshot minus zero-gravity control, speed and temperature |
| 09 | Projected velocity arrows over speed contours |
| 10 | Axial section-sample means and reverse-flow sample fractions |
| 11–12 | Matched sensor parity and signed differences |
| 13 | Thermal sensor-height profiles against measurements and control |
| 14–15 | Solver residuals and thermal probe stationarity |
| 16 | Equal-weight section-sample speed/temperature distributions |

For a short main report, start with 01, 02, 03, 11 and 14. Choose relevant galleries for an appendix rather than inserting every figure into a 5–10 page report.

## Scientific status

The isothermal field is the converged baseline at iteration 237. The zero-gravity thermal control converged at 733. The buoyant thermal field is the **NOT CONVERGED snapshot at iteration 967**; its log and probe history extend to 1000. The initial divergent buoyant field is excluded. The figures retain these labels. SIMPLE iterations are not physical seconds.

Fixed thermal walls use laboratory air temperature as an unmeasured wall-temperature surrogate. The zero-gravity control shares thermal boundary conditions with the buoyant case, but initialization and relaxation differ. A difference plot does not establish a converged buoyancy effect. The isothermal and thermal cases have different operating conditions; they are not a controlled pair isolating temperature alone. No experimental validation or mesh independence is claimed.

Fields are sampled with cellPoint at 32 by 48 midpoint positions on each of nine source-coordinate sections, plus 181 by 48 midpoint locations in the vertical mid-width plane. All cases have identical checked geometry and sampling positions. Absolute y is preserved for longitudinal plots; section plots explicitly subtract the local CFD floor. Existing 0.127 mm ceiling discrepancy is retained. Rounded raw output coordinates are matched uniquely within one micrometre; this accommodates the isothermal case's eight-significant-digit writer without editing its settings.

Comparison figures reuse the existing matched 10 ft cell-sampled sensor exports, with source hashes and saved-iteration checks. They are descriptive comparisons, not an additional validation. The thermal and control coordinate/observation rows are checked for equality. Measured scalar speed is compared with full speed magnitude. Projected arrows show CFD components (Uz, Uy), not experimental vectors or particle tracks. Sample means, reverse-flow percentages and cumulative distributions are not mesh-integrated flux checks or whole-volume distributions. The section grids are equally weighted; no volumetric-flow constraint is imposed.

## Reproduce

Use the pinned WSL Python environment and existing run directories. Set `REPO` to the Linux path of this repository and `PYTHONPATH` to its src directory; source OpenFOAM. Choose a fresh output directory because existing results are preserved.

```bash
REPO=/mnt/c/Users/mattb_ar68ij9/OneDrive/Documents/UNI/2026/MMA3001/Project/jetbridge-ml-cfd
export PYTHONPATH="$REPO/src"
source /usr/lib/openfoam/openfoam2412/etc/bashrc
/home/mattb/projects/jetbridge-python-env/bin/python -m jetbridge_ml.cfd_interface.report_figures \
  --isothermal /home/mattb/projects/jetbridge-baseline-20261024 \
  --thermal /home/mattb/projects/jetbridge-thermal-stabilized-s01-ac-10-hn-1 \
  --control /home/mattb/projects/jetbridge-thermal-control-s01-ac-10-hn-1 \
  --dataset /mnt/c/Users/mattb_ar68ij9/Downloads/dot_92577_DS3/JetBridge_2026 \
  --iso-comparisons "$REPO/data/processed/cfd_visuals" \
  --thermal-comparisons "$REPO/data/processed/thermal_visuals" \
  --output /home/mattb/projects/new-report-figures
```

If comparison exports are absent, regenerate them using the workflows in cfd_comparison_visuals.md and thermal_case_results.md. Use the stabilized case, not the failed initial thermal case. The manifest records source hashes, saved fields, Python/library versions and plotting-code hash. The script runs OpenFOAM postprocessing only; solver inputs, saved numerical fields, raw data and ML models are unchanged.

All 44 project tests pass. Generation additionally checks field presence, expected convergence status, shared geometry, unique sampled-coordinate mapping, finite values and matched comparison iterations. Figures were reviewed using the contact sheet and selected full-size previews. Source code and documentation are committed; figures and large sample tables remain external to Git.
## Current demo and quality workflow on 27 October 2026
The repository now includes the attributed study input subset and compact archived numerical evidence. Use the root run_all.py driver and docs/LIVE_DEMO.md for one-clone execution; older commands above describe the original research runs. Static checking uses python -m ruff check src tests run_all.py; numerical tests use python -m pytest -q; API documentation uses python -m pdoc jetbridge_ml -o docs/html. See docs/DEVELOPMENT.md for scope and limitations. Live/full execute fresh isothermal CFD in new output folders; archived unconverged thermal evidence remains explicitly separate.
