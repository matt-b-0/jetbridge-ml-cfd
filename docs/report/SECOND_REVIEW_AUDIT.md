# Second review response and submission audit

## Completed technical changes

- Experimental four-panel field comparison: measured locations, full-data RBF and SVR refits on a common scale, and genuine held-location residuals. The continuous experimental field is not treated as known truth.
- CFD reference/reconstruction/error panels from disjoint candidate/reference grids at the declared 28 ft, 24-sensor hybrid example. No new solver run or physics adjustment.
- Corrected the introduction: evaluated errors and support masks do not supply calibrated location-specific uncertainty.
- Computed physical hull area: full 12-point layout 41.3%, full 24-point layout 49.7%; outer-fold areas are reported separately from held-target support counts.
- Restored accepted-format, SI-unit, invalid-input and extrapolation specifications; numbered every table.
- Added dictionary-specific solver, boundaries, turbulence inputs, schemes, relaxation and residual criteria. Saved-field wall-y-plus postprocessing gave min/mean/max 10.025/18.740/27.129; the log is retained. Convergence is not physical validation.
- Explained why a matched downstream plane cannot resolve the original upstream/downstream discrepancy, and why an unmatched station-error curve was not created.
- Audited all 504 training-only parameter selections and small inner fold sizes. Search endpoints are frequently selected; grid sufficiency is not claimed and scores were not retuned.
- Reported actual evaluated-speed quartiles, descriptive replicate dependence, temporal variation on the matched scatter and an observed-variation perturbation scenario for both methods.
- Added timing repetition quartiles, explicit training sample sizes and deployment interpretation of the separate SVR search cost.
- Added Matthew Brasacchio, 33858659. Shortened the thermal main-text discussion; retained the AI paragraph verbatim as requested.

## Reproduce the new diagnostics

The earlier processing workflow is documented in `docs/project_improvements.md`. It requires the external FAA dataset and separately regenerated OpenFOAM fields. No claim is made that these large/raw sources are included in the clone. From the project root after creating the existing submission analysis and controlled benchmark:

```bash
python -m jetbridge_ml.report_evidence --analysis data/processed/submission_analysis --performance data/processed/report_revision/performance --mesh cfd/cases/empty_bridge_s01_a_10_hn_1/system/blockMeshDict --output data/processed/second_review_evidence --draws 200
python -m pytest -q --junitxml=docs/report/test-results.xml
python -m pdoc jetbridge_ml -o docs/html
```

Use a fresh diagnostic output directory. The perturbation seed is 20261025. The scenario uses six observed 10 ft datasets, site-wise between-file SD, independent centred Gaussian perturbations and frozen full-data SVR parameters. It is not instrument uncertainty or independent same-condition repeatability. An initial dataframe-index alignment error was corrected before numerical results were generated. Figure labels were then refined without changing the diagnostic values.

After sourcing OpenCFD v2412, wall-y-plus extraction from the existing converged baseline is:

```bash
simpleFoam -case /path/to/solved/baseline -postProcess -func yPlus -latestTime
```

This adds a diagnostic field and postprocessing output to the run copy; original dictionaries and the velocity solution are unchanged.

## Submission checks

| Requirement | Verified state |
| --- | --- |
| README and modular source | Present, extended with report reproduction guide |
| Figure and benchmark scripts | Present, with selected data, input hashes, figure assets and complete repeated timings |
| Word authoring source | Present; evidence report rebuild uses retained source and tracked figure assets |
| Tests and test report | 74 passing tests; JUnit report retained |
| HTML/API documentation | Generated under docs/html; local generation succeeded |
| Raw data and large CFD fields | Intentionally external; source/acquisition and generation commands documented |
| Licence | No LICENSE file found; student choice remains required; no licence invented |
| Individual AI reflection | Existing statement left unchanged at student's request; fuller personal reflection remains outstanding |
| Publication | These changes are local until explicitly published; no claim that GitHub contains them |
| Final clone/archive | Check exact committed revision and included files before submission; a copy with local uncommitted changes is insufficient |

The report is an evidence-based draft rather than a claim that all submission conditions are complete. Public accessibility, licensing, personal reflection and numerical/physical validation are separate questions.
