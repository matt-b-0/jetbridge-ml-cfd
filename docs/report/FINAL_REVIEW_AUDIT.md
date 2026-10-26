# Final report review and reproduction audit

## Review changes

The 26 October revision adds the first 58 ft replicate alongside the matched 10 ft example. The 58 ft figure shows all 24 measured points, full-array fits and genuine leave-one-location-out residuals. The original primary scores are retained. Full-array experimental maps now hatch extrapolation and state physical hull area; the 41.3% / 49.7% figures remain separate from the fraction of supported held targets. RBF's negative extrapolated speed at 58 ft is shown rather than clipped. The report describes both SVR smoothing of measured high-speed contrasts and RBF overshoot, without claiming a continuously known experimental field.

The outer evaluation is clarified as one held-out averaged value within each file: 11/1 train/test points for the 12-point layout and 23/1 for 24 points. Runs are not pooled. The new exploratory search adds C = 0.01 with the same three-fold inner procedure and excludes the outer target before selection. It selects the new value in 143/504 folds, but common-supported mean per-run SVR RMSE changes from 0.05774065 to 0.05883773 m/s. This post-hoc check is kept separate from the original comparison; neither original nor expanded grid is described as a global optimum. The new leakage regression test changes the held-out target drastically and checks that the prediction/parameters stay unchanged and scaling uses inner training rows only.

Body text is 11 points and captions 10 points. CFD panels use two rows, the perturbation figure is enlarged, and detailed residual values remain in `docs/baseline_run_2026-10-24.md` rather than dominating the main argument. The report explicitly separates inlet mass-flow prescription, continuity and local-profile accuracy. The perturbation discussion states that real spatially correlated flow variations could change its comparison.

The AI paragraph is intentionally unchanged under the student's standing instruction. No independent decisions, verification actions or personal learning are invented. The licence is intentionally undecided under the student's explicit answer on 26 October; absence of a LICENSE file is recorded rather than hidden.

## Regenerate the representative diagnostics from a clone

The compact `docs/report/inputs/primary_prediction_evidence.csv` contains 540 derived prediction records: all 504 original SVR outer records and RBF records for the two illustrated runs. It is not the raw FAA archive. Existing CFD reference-example, layout and perturbation-trial tables are included under `docs/report/evidence`. From the repository root in the documented Python environment:

```bash
python -m jetbridge_ml.final_report_checks \
  --predictions docs/report/inputs/primary_prediction_evidence.csv \
  --evidence docs/report/evidence \
  --mesh cfd/cases/empty_bridge_s01_a_10_hn_1/system/blockMeshDict \
  --output data/processed/new-final-checks
python -m pytest -q --junitxml=docs/report/test-results.xml
python -m pdoc jetbridge_ml -o docs/html
```

Use a fresh output directory. Figures, dense plotting values, expanded predictions, inner search/split audits and a hashed summary are saved. The saved representative grids are for plotting and reconstruction diagnostics; they are not new raw measurements or a replacement for the external field files. `docs/project_improvements.md` documents the full original workflow and its external FAA/CFD inputs. Final report generation uses:

```bash
python docs/report/build_submission_report.py
```

The builder needs python-docx. It uses tracked figure assets. Set `JETBRIDGE_REPORT_REVISION` to the recorded implementation commit to reproduce the report's exact revision reference; otherwise it references the current checkout. Word page fields must be refreshed before layout verification.

## Submission status

- README, source, tests, JUnit report, HTML API docs, figure scripts and representative derived inputs are included.
- The raw FAA archive, generated meshes and large CFD fields remain external with documented source/generation instructions.
- No CFD geometry, solver settings or physical model changed in this revision; no new CFD solve was run.
- Original scores and exploratory lower-C results remain explicitly separate.
- A personal AI reflection and licence choice remain outstanding by the student's instructions.
- Publication, exact implementation commit, hosted checks and clone verification are recorded below only after checking them. Document packaging may be a subsequent commit because a report cannot contain its own content-addressed Git hash.

## Verified implementation publication

Implementation/evidence commit: 6c6cf81103f9644dcc6b3adebfcd3ff01775537e. Pushed to the public repository on 26 October 2026 and independently read through the GitHub connector. A fresh clone directly from GitHub rebuilt the Word draft and passed all 75 tests. Its complete 504-fold expanded-C experiment and both station diagnostics reproduced the saved numerical summary exactly in the documented WSL Python environment. No raw FAA archive or large CFD fields were needed for this representative check.

The report identifies this immutable implementation commit. The document-packaging commit is separate; use git rev-parse HEAD in the submitted clone or the archive manifest for the exact packaging revision. The licence is still intentionally undecided, and the AI reflection is intentionally unchanged.


Hosted workflow for implementation 6c6cf81 completed successfully: https://github.com/matt-b-0/jetbridge-ml-cfd/actions/runs/40262525830 (queried from GitHub Actions on 26 October 2026). Local and hosted checks verify software behaviour, not physical validation.


## Final document layout

Microsoft Word confirms 17 pages: main report 1–10, references 11, Appendix A 12, Appendix B 13, Appendix C 14–15 and Appendix D 16–17. All pages were rendered and visually reviewed. The final change affected only pages 5 and 11; both were reinspected. The document has nine captioned figures and nine numbered tables, 11-point body text and 10-point captions. The AI paragraph is verbatim. The packaged LibreOffice renderer is unavailable because soffice.exe is missing; native Word supplied the successful render.

