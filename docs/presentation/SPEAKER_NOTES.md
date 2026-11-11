# Speaker notes

Main talk: slides 1–9, target 300 seconds. All remaining slides are for questions. Current delivery notes are extracted from the packaged PowerPoint below; older nested evidence notes are omitted from this readable copy and remain in the deck.

## Slide 1: Jet bridge airflow

MAIN TALK 1/9 — target 15 seconds; total 300 seconds.

My project investigates how reliably sparse measurements reconstruct jet-bridge air speed. I compare conventional interpolation with support vector regression, and use CFD for separate numerical sampling experiments.

## Slide 2: Experimental data and geometry

MAIN TALK 2/9 — target 25 seconds; total 300 seconds.

The inputs are sensor positions in metres and scalar speeds in metres per second. Thirty-six files at nine stations supply five hundred and four sensor means. Outputs are reconstructed maps, held-out errors, support masks and timings. Measurements are sequential and come from one apparatus.

## Slide 3: Interpolation and regression

MAIN TALK 3/9 — target 30 seconds; total 300 seconds.

Mean, nearest and linear methods provide simple baselines. Thin-plate RBF fits a smooth interpolating surface. SVR uses regularisation and an RBF kernel. I compare them on the same withheld locations rather than assuming that machine learning will be better.

## Slide 4: Prediction tests at withheld locations

MAIN TALK 4/9 — target 35 seconds; total 300 seconds.

Each outer fold removes a complete location. A three-fold inner search selects SVR settings from the remaining data, with scaling fitted inside training folds. This prevents test information from entering tuning. Linear cannot extrapolate, so the main scores use common supported locations.

## Slide 5: RBF has the lowest aggregate error

MAIN TALK 5/9 — target 35 seconds; total 300 seconds.

RBF has the lowest aggregate RMSE, about zero point zero five metres per second, compared with zero point zero five eight for SVR. Its advantage is concentrated at the fifty-eight-foot layout. The twelve-point group slightly favours SVR. Station and count are confounded, so I cannot claim a density-only effect.

## Slide 6: CFD setup and initial conditions

MAIN TALK 6/9 — target 25 seconds; total 300 seconds.

The isothermal CFD baseline uses steady k-epsilon RANS, a measured supplied flow and sealed no-slip walls. The standard mesh has one hundred and forty-one thousand three hundred and twelve cells. Full-face inlet and wall assumptions limit its physical realism.

## Slide 7: CFD overpredicts speed at all 12 sensors

MAIN TALK 7/9 — target 30 seconds; total 300 seconds.

At twelve matched sensors CFD overpredicts every measured mean, with bias around zero point zero three seven metres per second. Numerical convergence and flux balance do not resolve that experimental disagreement. Unconverged thermal fields remain excluded from trusted references.

## Slide 8: Repository, documentation and tests

MAIN TALK 8/9 — target 65 seconds; total 300 seconds.

I will briefly show the repository and documentation. [Switch to the pre-opened local presentation page.] The README gives the setup and reproducible workflows. The API link opens the actual function documentation with parameters, returns and source. [Open metrics API, then return.] This small test uses errors of plus and minus zero point two metres per second. Bias cancels to zero, but MAE and RMSE both remain zero point two. That is why I report several metrics. The fresh test report is linked here; the leakage test and affine-field checks are available for questions. [Return to PowerPoint.]

DEMO FALLBACK: if switching takes over 10 seconds, use the on-slide example and the backup test slide. Do not wait for CFD or the full suite during the talk.

Sources: MMA3001 project brief pp. 8–15; current local jetbridge-ml-cfd source, tests and docs. Scientific scores remain those of evidence revision 51a464a. Presentation revision 11 November 2026. Local changes have not been published.

## Slide 9: Limitations and AI reflection

MAIN TALK 9/9 — target 40 seconds; total 300 seconds.

The principal lesson is that spatial coverage and validation design matter more than model complexity. AI assisted code, debugging and reporting, as disclosed in my author statement and log. My engineering objectives, interpretation and conclusions remained central. I would next improve boundary measurements and test an independently specified sensor layout.

## Slide 10: Backup  Libraries and their roles

QUESTION ONLY. Explain the library by the numerical responsibility it serves. Data processing, interpolation, ML and CFD remain separate modules. Source: pyproject.toml, README.md and src/jetbridge_ml in the project repository. An epoch-loss plot is not a standard SVR training measure.

## Slide 11: Backup  Reconstructing a CFD field

QUESTION ONLY. Virtual sensors sample the numerical field and predictions are compared with disjoint CFD reference points. These RMSEs must not be mixed with experimental held-location RMSEs. Source: docs/report/final_checks/cfd_reconstruction_large.png and docs/report/evidence/cfd_example_predictions.csv.

## Slide 12: Backup  Numerical stability and accuracy

QUESTION ONLY. This separate taught-method exercise compares FTCS, backward Euler and Crank–Nicolson. The FTCS condition applies to the specified linear one-dimensional diffusion problem, not to the steady SIMPLE iteration in the nonlinear CFD case. Stability and accuracy differ. Source: docs/report/assets/diffusion_stability.png and docs/numerical_stability_study.md.

## Slide 13: Backup  Sources and scope

QUESTION ONLY. Detailed source paths accompany the relevant slide notes. Dataset DOI and attribution: data/demo/ATTRIBUTION.md. Author reflection: docs/report/ai_statement.txt. Scientific data and figures are retained from the published report. Presentation drafted 3 November 2026.

## Slide 14: Alternative B  Size of the CFD overprediction

OPTIONAL FIGURE WORKSHOP. Alternative to the main comparison on slide 7. End the main talk at slide 9.

Source: matched_sensor_audit.csv, S01-A-10-HN-1, 12 published mean speeds and CFD cellPoint samples at saved iteration 237. Same input as the original slide 8. Source revision 51a464a. Coordinates: published x/y/z, local height y minus floor elevation. Temporal SD is fluctuation of raw observations, not uncertainty of the mean. The figure is descriptive for one matched run, not an inferential significance test. No CFD rerun or recalibration.

## Slide 15: Alternative C  Height profiles and temporal variation

OPTIONAL FIGURE WORKSHOP. Alternative to the main comparison on slide 7. End the main talk at slide 9.

Source: matched_sensor_audit.csv, S01-A-10-HN-1, 12 published mean speeds and CFD cellPoint samples at saved iteration 237. Same input as the original slide 8. Source revision 51a464a. Coordinates: published x/y/z, local height y minus floor elevation. Temporal SD is fluctuation of raw observations, not uncertainty of the mean. The figure is descriptive for one matched run, not an inferential significance test. No CFD rerun or recalibration.

## Slide 16: Alternative D  A simpler parity comparison

OPTIONAL FIGURE WORKSHOP. Alternative to the main comparison on slide 7. End the main talk at slide 9.

Source: matched_sensor_audit.csv, S01-A-10-HN-1, 12 published mean speeds and CFD cellPoint samples at saved iteration 237. Same input as the original slide 8. Source revision 51a464a. Coordinates: published x/y/z, local height y minus floor elevation. Temporal SD is fluctuation of raw observations, not uncertainty of the mean. The figure is descriptive for one matched run, not an inferential significance test. No CFD rerun or recalibration.

## Slide 17: Backup  Rubric evidence

QUESTION ONLY. Exact rubric headings are on pp. 10–15. Page 8 defines the report and repository deliverables; page 9 requires a 5-minute talk plus 3 minutes of questions. Do not claim a guaranteed grade. Explain concrete evidence for each row.

Sources: MMA3001 project brief pp. 8–15; current local jetbridge-ml-cfd source, tests and docs. Scientific scores remain those of evidence revision 51a464a. Presentation revision 11 November 2026. Local changes have not been published.

## Slide 18: Backup  A test with a known answer

QUESTION ONLY. Explain imports first, then actual and predicted arrays. regression_metrics computes the three metrics. Each assertion compares to a hand-derived value. Errors cancel only in signed bias. pytest.approx tolerates floating-point representation; it does not allow arbitrary error. This checks metric implementation, not physical CFD validity. Full line-by-line explanations appear in docs/presentation/index.html.

Sources: MMA3001 project brief pp. 8–15; current local jetbridge-ml-cfd source, tests and docs. Scientific scores remain those of evidence revision 51a464a. Presentation revision 11 November 2026. Local changes have not been published.

## Slide 19: Backup  Preventing test-data leakage

QUESTION ONLY. Open tests/test_four_workstreams.py at test_nested_test_target_does_not_change_its_model, then test_inner_scaling_and_location_groups_exclude_validation. The first exercises real SVR with a reduced test grid. The second verifies scaler means and coordinate grouping. Do not confuse these checks with the monkeypatched noise-fit test, which tests orchestration rather than real model fitting.

Sources: MMA3001 project brief pp. 8–15; current local jetbridge-ml-cfd source, tests and docs. Scientific scores remain those of evidence revision 51a464a. Presentation revision 11 November 2026. Local changes have not been published.

## Slide 20: Backup  Accuracy, robustness and computational cost

QUESTION ONLY. Source: controlled_performance.py, sensor_design_study.py, numerical_stability_study.md and current summary. Controlled timing uses warm-up, interleaved repeats and single-thread limits. Reconstruction Lab timings use a different protocol and must not be substituted silently. Sensor layouts are exploratory; synthetic noise is not measured instrument uncertainty.

Sources: MMA3001 project brief pp. 8–15; current local jetbridge-ml-cfd source, tests and docs. Scientific scores remain those of evidence revision 51a464a. Presentation revision 11 November 2026. Local changes have not been published.
