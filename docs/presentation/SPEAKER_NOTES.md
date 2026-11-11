# Speaker notes

Main talk: slides 1–6, target 270 seconds including the browser demonstration, leaving 30 seconds for transitions. All remaining slides are for questions. Current delivery notes are extracted from the packaged PowerPoint below; older nested evidence notes are omitted from this readable copy and remain in the deck.

## Slide 1: Jet bridge airflow

MAIN TALK 1/6. Target 15 seconds. Total target 270 seconds, leaving 30 seconds for transitions.

My report asks how accurately sparse sensors reconstruct air speed across a jet bridge, and whether support vector regression improves on simpler interpolation.

Source: Submitted report p. 1. Scientific results are unchanged from the submitted report.
The optional full API, CFD and detailed figures are for questions.

## Slide 2: Experimental data and geometry

MAIN TALK 2/6. Target 30 seconds. Total target 270 seconds, leaving 30 seconds for transitions.

The inputs are sensor positions in metres and measured scalar speeds in metres per second. Thirty-six averaged files give five hundred and four sensor means. Outputs are predicted speed maps, errors at hidden sensors and support masks. These are sequential measurements from one apparatus, not a simultaneous velocity-vector field.

Source: Submitted report p. 2. Scientific results are unchanged from the submitted report.
The optional full API, CFD and detailed figures are for questions.

## Slide 3: Interpolation and regression

MAIN TALK 3/6. Target 40 seconds. Total target 270 seconds, leaving 30 seconds for transitions.

Nearest neighbour and linear interpolation are simple references, alongside the retained-sensor mean. Thin-plate RBF fits a smooth interpolating surface. SVR uses regularisation to allow fitting errors. I compare their predictions on the same hidden locations rather than assuming a more complex method will win.

Source: Submitted report p. 3. Scientific results are unchanged from the submitted report.
The optional full API, CFD and detailed figures are for questions.

## Slide 4: Prediction tests at withheld locations

MAIN TALK 4/6. Target 50 seconds. Total target 270 seconds, leaving 30 seconds for transitions.

For each experimental file, I hide one sensor location, fit on the remaining sensors and predict the hidden speed. SVR settings are selected in three inner folds using only retained data. Scaling uses training coordinates only. This prevents the hidden answer from affecting its own model. Linear cannot extrapolate, so the primary scores compare the same supported targets.

Source: Submitted report pp. 3–4; experimental_svr.py and machine_learning/selection.py. Scientific results are unchanged from the submitted report.
The optional full API, CFD and detailed figures are for questions.

## Slide 5: RBF has the lowest aggregate error

MAIN TALK 5/6. Target 95 seconds including a 45-second browser demonstration. Total target 270 seconds, leaving 30 seconds for transitions.

RBF has the lowest aggregate RMSE, about zero point zero five metres per second, versus zero point zero five eight for SVR. Most of that advantage is concentrated at fifty-eight feet; the common twelve-point group slightly favours SVR. Location and sensor count change together, so this does not isolate a sensor-count effect. [After about 50 seconds, switch to the pre-opened report/code guide for a 45-second demonstration.] The short HTML documents the source behind the report. This function computes RMSE, MAE and bias. The core test uses errors of plus and minus zero point two. Bias cancels to zero, but RMSE and MAE stay positive. The result shows six core checks passed. [Return to the final main slide.]

Source: Submitted report pp. 4–5; docs/html/index.html; tests/test_core.py. Scientific results are unchanged from the submitted report.
The optional full API, CFD and detailed figures are for questions.

## Slide 6: Limitations and AI reflection

MAIN TALK 6/6. Target 40 seconds. Total target 270 seconds, leaving 30 seconds for transitions.

The main lesson is that spatial coverage matters. A smooth map does not establish accurate extrapolation. CFD was supporting numerical evidence, with physical bias; thermal fields remained unconverged. AI assisted implementation, debugging and reporting as disclosed in the report. Engineering objectives, interpretation and conclusions remained central to my contribution. The next step is better matched measurements and an independent sensor-layout test.

Source: Submitted report p. 10 and author-supplied AI statement. Scientific results are unchanged from the submitted report.
The optional full API, CFD and detailed figures are for questions.

## Slide 7: CFD setup and initial conditions

BACKUP ONLY. Finish the main talk at slide 6.

MAIN TALK 6/9 — target 25 seconds; total 300 seconds.

The isothermal CFD baseline uses steady k-epsilon RANS, a measured supplied flow and sealed no-slip walls. The standard mesh has one hundred and forty-one thousand three hundred and twelve cells. Full-face inlet and wall assumptions limit its physical realism.

## Slide 8: CFD overpredicts speed at all 12 sensors

BACKUP ONLY. Finish the main talk at slide 6.

MAIN TALK 7/9 — target 30 seconds; total 300 seconds.

At twelve matched sensors CFD overpredicts every measured mean, with bias around zero point zero three seven metres per second. Numerical convergence and flux balance do not resolve that experimental disagreement. Unconverged thermal fields remain excluded from trusted references.

## Slide 9: Repository, documentation and tests

BACKUP ONLY. Open docs/html/index.html, the report-focused source guide, and tests/test_core.py. The main route uses a 45-second browser demonstration after slide 5. The default test run has six cases. Full regressions are optional under tests/extended.

## Slide 10: Backup  Libraries and their roles

BACKUP ONLY. Finish the main talk at slide 6.

QUESTION ONLY. Explain the library by the numerical responsibility it serves. Data processing, interpolation, ML and CFD remain separate modules. Source: pyproject.toml, README.md and src/jetbridge_ml in the project repository. An epoch-loss plot is not a standard SVR training measure.

## Slide 11: Backup  Reconstructing a CFD field

BACKUP ONLY. Finish the main talk at slide 6.

QUESTION ONLY. Virtual sensors sample the numerical field and predictions are compared with disjoint CFD reference points. These RMSEs must not be mixed with experimental held-location RMSEs. Source: docs/report/final_checks/cfd_reconstruction_large.png and docs/report/evidence/cfd_example_predictions.csv.

## Slide 12: Backup  Numerical stability and accuracy

BACKUP ONLY. Finish the main talk at slide 6.

QUESTION ONLY. This separate taught-method exercise compares FTCS, backward Euler and Crank–Nicolson. The FTCS condition applies to the specified linear one-dimensional diffusion problem, not to the steady SIMPLE iteration in the nonlinear CFD case. Stability and accuracy differ. Source: docs/report/assets/diffusion_stability.png and docs/numerical_stability_study.md.

## Slide 13: Backup  Sources and scope

BACKUP ONLY. Finish the main talk at slide 6.

QUESTION ONLY. Detailed source paths accompany the relevant slide notes. Dataset DOI and attribution: data/demo/ATTRIBUTION.md. Author reflection: docs/report/ai_statement.txt. Scientific data and figures are retained from the published report. Presentation drafted 3 November 2026.

## Slide 14: Alternative B  Size of the CFD overprediction

BACKUP ONLY. Finish the main talk at slide 6.

OPTIONAL FIGURE WORKSHOP. Alternative to the main comparison on slide 7. Finish the main talk at slide 6.

Source: matched_sensor_audit.csv, S01-A-10-HN-1, 12 published mean speeds and CFD cellPoint samples at saved iteration 237. Same input as the original slide 8. Source revision 51a464a. Coordinates: published x/y/z, local height y minus floor elevation. Temporal SD is fluctuation of raw observations, not uncertainty of the mean. The figure is descriptive for one matched run, not an inferential significance test. No CFD rerun or recalibration.

## Slide 15: Alternative C  Height profiles and temporal variation

BACKUP ONLY. Finish the main talk at slide 6.

OPTIONAL FIGURE WORKSHOP. Alternative to the main comparison on slide 7. Finish the main talk at slide 6.

Source: matched_sensor_audit.csv, S01-A-10-HN-1, 12 published mean speeds and CFD cellPoint samples at saved iteration 237. Same input as the original slide 8. Source revision 51a464a. Coordinates: published x/y/z, local height y minus floor elevation. Temporal SD is fluctuation of raw observations, not uncertainty of the mean. The figure is descriptive for one matched run, not an inferential significance test. No CFD rerun or recalibration.

## Slide 16: Alternative D  A simpler parity comparison

BACKUP ONLY. Finish the main talk at slide 6.

OPTIONAL FIGURE WORKSHOP. Alternative to the main comparison on slide 7. Finish the main talk at slide 6.

Source: matched_sensor_audit.csv, S01-A-10-HN-1, 12 published mean speeds and CFD cellPoint samples at saved iteration 237. Same input as the original slide 8. Source revision 51a464a. Coordinates: published x/y/z, local height y minus floor elevation. Temporal SD is fluctuation of raw observations, not uncertainty of the mean. The figure is descriptive for one matched run, not an inferential significance test. No CFD rerun or recalibration.

## Slide 17: Backup  Rubric evidence

BACKUP ONLY. Finish the main talk at slide 6.

QUESTION ONLY. Exact rubric headings are on pp. 10–15. Page 8 defines the report and repository deliverables; page 9 requires a 5-minute talk plus 3 minutes of questions. Do not claim a guaranteed grade. Explain concrete evidence for each row.

Sources: MMA3001 project brief pp. 8–15; current local jetbridge-ml-cfd source, tests and docs. Scientific scores remain those of evidence revision 51a464a. Presentation revision 11 November 2026. See repository history for publication revision.

## Slide 18: Backup  A test with a known answer

BACKUP ONLY. Finish the main talk at slide 6.

QUESTION ONLY. Explain imports first, then actual and predicted arrays. regression_metrics computes the three metrics. Each assertion compares to a hand-derived value. Errors cancel only in signed bias. pytest.approx tolerates floating-point representation; it does not allow arbitrary error. This checks metric implementation, not physical CFD validity. Full line-by-line explanations appear in docs/presentation/index.html.

Sources: MMA3001 project brief pp. 8–15; current local jetbridge-ml-cfd source, tests and docs. Scientific scores remain those of evidence revision 51a464a. Presentation revision 11 November 2026. See repository history for publication revision.

## Slide 19: Backup  Preventing test-data leakage

BACKUP ONLY. Show test_nested_test_target_does_not_change_its_model in tests/test_core.py. It changes the hidden target and checks the real SVR prediction is unchanged. Optional inner-scaling and grouped-location checks remain in tests/extended/test_four_workstreams.py. The research grid is larger than this one-candidate regression fixture.

## Slide 20: Backup  Accuracy, robustness and computational cost

BACKUP ONLY. Finish the main talk at slide 6.

QUESTION ONLY. Source: controlled_performance.py, sensor_design_study.py, numerical_stability_study.md and current summary. Controlled timing uses warm-up, interleaved repeats and single-thread limits. Reconstruction Lab timings use a different protocol and must not be substituted silently. Sensor layouts are exploratory; synthetic noise is not measured instrument uncertainty.

Sources: MMA3001 project brief pp. 8–15; current local jetbridge-ml-cfd source, tests and docs. Scientific scores remain those of evidence revision 51a464a. Presentation revision 11 November 2026. See repository history for publication revision.
