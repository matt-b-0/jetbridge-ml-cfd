# Report revisions and reproduction

The first revised Word report has ten main pages, one reference page and two diagnostic appendices. The subsequent Evidence Report has ten main pages, references and four appendices; see the second-review section below. It preserves the original template separately. The existing AI-use paragraph was left unchanged at the student's request; personal reflection has not been invented.

The revision strengthens engineering interpretation of absolute errors, station/density confounding, CFD bias, spatial coverage and the distinction between scalar speed and signed flux. It explains the SVR choice without claiming superiority over untested GPR, examines unsmoothed RBF sensitivity, and replaces incompatible historical timings with a controlled benchmark. Five larger main-text figures replace the previous dense figure arrangement. Thermal diagnostics and the reduced diffusion study are placed in appendices. Thermal results remain unconverged and excluded from trusted reference data.

## Reproduce the analytical additions

Install the project with its dependencies and run commands from the repository root. Existing saved submission-analysis outputs and the baseline mesh dictionary are required. Output directories must not already exist; use new suffixes when repeating.

```bash
python -m jetbridge_ml.controlled_performance --predictions data/processed/submission_analysis/experimental/predictions.csv --output data/processed/report_revision/performance --repeats 20
python -m jetbridge_ml.revision_figures --analysis data/processed/submission_analysis --mesh cfd/cases/empty_bridge_s01_a_10_hn_1/system/blockMeshDict --output data/processed/report_revision/figures
python -m pytest -q
```

The recorded benchmark used Python under Ubuntu 24.04 / WSL2, an Intel i7-1165G7, one numerical thread, a warm-up and shuffled method order. It times the same first-location-held-out fold for every method in each of 36 runs. Search is separate from fitting and prediction. Peak traced allocations exclude some native and process memory. Full raw timing records and hashes are in the ignored local output directory; selected summaries are retained beside the report. Five new regression checks verify that benchmark predictors match the existing scaled numerical methods, preserve unsupported linear results, reproduce SVR training and reject unknown methods. All 72 tests pass with the current source directory on PYTHONPATH. An initial collection attempt resolved an older installed package; explicitly selecting this checkout corrected that environment issue.

The scaled noise diagnostic uses all twelve matched sensor coordinates, a StandardScaler fitted to that geometry, and a 50 by 70 query grid. Its maxima of 1.468 inside and 2.829 outside differ from the earlier unscaled-coordinate study. This is a worst-case bounded-input gain, not instrument uncertainty or an outer-fold prediction score.

## Word document

`build_revised_report.py` and `report_style.py` retain the authoring source. They require python-docx and the locally generated analytical assets, plus existing thermal/diffusion figures. Run the builder from a Python environment with python-docx; output is placed under `revised_output` beside the scripts. The delivered file was rendered with installed Microsoft Word and every page visually reviewed. The packaged LibreOffice renderer was unavailable because soffice.exe is not installed. Word confirmed 13 pages, with references beginning on page 11; no grey AUTHOR TASK prompts remain. Original AI wording was checked against the original builder.

No CFD inputs, raw experimental records, predictive scores or published GitHub history were changed. These local revisions have not been pushed. Before submission, the student must supply name/ID, review the retained AI reflection, and record the final submitted commit in reference 4.

## Second review revision

The evidence report has ten main pages, references and four appendices. See [response and submission audit](SECOND_REVIEW_AUDIT.md) for new spatial plots, real-area coverage, SVR selection frequencies, observed-variation perturbations, y-plus and timing variability. Matthew Brasacchio, 33858659 is filled in. The original AI paragraph is unchanged.

Run python docs/report/build_evidence_report.py to rebuild the evidence report from tracked figure assets; python-docx is required. No ignored figure path is needed by this builder. Original analysis regeneration still requires the external source data and fields. Generated API docs are in docs/html. All 74 tests pass; the retained test report records the run.


## Final review revision on 26 October

See [final-review audit](FINAL_REVIEW_AUDIT.md) for the 58 ft reconstruction, hatched extrapolation, expanded-C sensitivity, larger typography and included representative inputs. Run python docs/report/build_submission_report.py for the current draft. The AI paragraph and undecided licence are retained under direct student instruction.

The current draft is MMA3001_Jet_Bridge_Submission_Draft.docx. Its published implementation is 6c6cf81103f9644dcc6b3adebfcd3ff01775537e; a fresh public clone rebuilt it, passed 75 tests and reproduced the full final diagnostic summary. Hosted checks passed in run 40262525830. The licence and personal AI reflection remain intentionally incomplete under student instruction.

## Current demo and quality workflow on 27 October 2026
The repository now includes the attributed study input subset and compact archived numerical evidence. Use the root run_all.py driver and docs/LIVE_DEMO.md for one-clone execution; older commands above describe the original research runs. Static checking uses python -m ruff check src tests run_all.py; numerical tests use python -m pytest -q; API documentation uses python -m pdoc jetbridge_ml -o docs/html. See docs/DEVELOPMENT.md for scope and limitations. Live/full execute fresh isothermal CFD in new output folders; archived unconverged thermal evidence remains explicitly separate.
