# Presentation tutorial

Updated 11 November 2026. The deck has nine main slides totalling a target of five minutes. Remaining slides are for questions. Practise with a timer: five minutes is a budget, not a measured delivery duration.

## Prepare the demonstration

1. Open the revised PowerPoint. Use Presenter View to see its speaking notes. The main talk ends on slide 9.
2. Open `docs/presentation/index.html` in a browser. It works offline and links the API, annotated tests, all test source and the fresh test report.
3. Open `tests/test_presentation_examples.py` and `tests/test_four_workstreams.py` in your editor. The HTML walkthrough already contains their relevant source with real line numbers, so an editor is optional.
4. Keep the metrics API in another browser tab: `docs/html/jetbridge_ml/validation/metrics.html`. Set browser zoom around 110–125% for the projector.
5. Check that the report says 128 passed and 1 skipped for this revision. If you change source later, rerun the commands below and rebuild the guide; do not reuse an old count.
6. Rehearse Alt+Tab from PowerPoint to the browser and back. Do not launch a CFD solve or run the entire suite during the five-minute talk. Use a short test invocation only if time and environment have been checked beforehand.

## Five-minute delivery

| Slide | Time | Say and show |
|---|---:|---|
| 1 Problem | 15 s | Sparse sensors leave unobserved regions. Compare interpolation with SVR. |
| 2 Inputs/outputs | 25 s | x/y positions in metres and scalar speeds in m/s produce maps, errors, support masks and timings. 36 files, 504 sensor means; sequential observations. |
| 3 Approach | 30 s | Explain nearest/linear as baselines, thin-plate RBF as interpolation and SVR as regularised regression. |
| 4 Validation | 35 s | Remove one location, tune within the remaining data, predict the removed value. Explain training-only scaling and common support. |
| 5 Results | 35 s | RBF 0.04959 versus SVR 0.05774 m/s. State the 58 ft concentration and station/layout confounding. |
| 6 CFD setup | 25 s | Name steady isothermal RANS, measured inlet supply and sealed walls. Initial values are guesses; boundaries constrain the solve. |
| 7 CFD comparison | 30 s | All twelve matched CFD speeds are high. Convergence and conservation do not establish physical agreement. |
| 8 Live documentation/test demo | 65 s | Follow the sequence below. |
| 9 Limits and AI | 40 s | Explain coverage, excluded thermal fields, AI assistance and actual author decisions. End here. |

## The 65-second browser demonstration

- First 10 seconds: show the local tutorial navigation and its repository overview. Say: “The README specifies environment, inputs and reproduction commands.” The repository hyperlink is available if you want to show GitHub, but local files avoid depending on internet access.
- Next 15 seconds: open the metrics API. Point to Parameters, Returns and Raises, then expand the function source. Say: “Bias is prediction minus observation; unsupported values must be handled explicitly.” Return to the tutorial.
- Next 25 seconds: open Tests line by line, showing the first test. Actual values are [0.1, 0.3], predicted values [0.3, 0.1]. Errors are +0.2 and -0.2. Bias is zero, but RMSE and MAE are 0.2 m/s. Point to each assertion and explain floating-point tolerance.
- Final 15 seconds: show the fresh test report, including its skip reason. Say: “These are software and numerical checks. They do not certify the CFD physics.” Return to PowerPoint for slide 9.

If a window switch takes more than 10 seconds, use the on-slide metric example. Keep detailed source explanations for the three-minute question period.

## Read a test in four steps

Identify the property, identify the controlled input, calculate the expected answer independently, then locate the assertion. A passed function is evidence only for its stated property and tested inputs.

`np.array` constructs a numerical array. `assert` makes a falsifiable check: pytest fails when it is false. `pytest.approx` allows floating-point rounding. `assert_allclose` performs an array comparison. `@pytest.mark.parametrize` repeats one test for several inputs; three method names yield three test cases. `pytest.raises` verifies deliberate rejection of bad input. A pytest fixture such as `tmp_path` provides a temporary directory isolated from source data.

The tutorial annotates every line in the small presentation test module, plus the existing affine-field, unsupported-region, real-SVR leakage and inner-scaling tests. All other test modules have an expandable source catalogue. Native GUI checks and scientific worker checks are identified separately.

## Tests to explain during questions

**Known affine field:** f(x,y)=2+3x-y gives an independent expected value at unseen queries. Linear and thin-plate RBF should reproduce it within rounding. This verifies implementation for that field; it does not prove accuracy for arbitrary real airflow.

**Linear support:** inside the sensor triangle a constant field returns one; outside it the prediction is NaN. Missing coverage must be reported rather than hidden or compared with fully supported methods unfairly.

**Hidden-target mutation:** evaluate synthetic data, alter only the target for outer sensor 0 to 9 m/s, and compare its two held-out predictions. They must be identical because sensor 0 is withheld from its own model. This uses real SVR fits with one candidate to keep the test small. It checks outer exclusion, not every possible source of leakage.

**Inner scaling and groups:** decode the recorded split indices, calculate coordinate means using inner training rows, and compare those means with the scaler audit. Check that the same coordinate never appears in both inner training and validation. This detects preprocessing and duplicate-location leakage.

**Row ordering:** permute both coordinates and their attached speeds. Predictions should remain unchanged for the selected non-tied queries. A nearest-neighbour tie is deliberately excluded; no physical preference is claimed between exactly equidistant sensors.

**Units and coverage:** converting both arrays from m/s to cm/s multiplies RMSE, MAE and bias by 100. A NaN prediction must raise an exception until the caller explicitly decides how to restrict coverage.

## Explain the HTML pages

The presentation tutorial is a teaching aid. The pdoc API pages document actual importable functions and show their current source. The Reconstruction Lab dashboard is a separate scientific results page: full-array maps are fitted surfaces, while Unseen sensors reports held-out predictions. Sensor count retains hull anchors and fixed test targets; Input noise is synthetic training-only noise; Accuracy & cost uses its own documented timing protocol. Do not substitute dashboard timings for the separate controlled performance study.

This WSL worker lacks Tk. Its pdoc build excludes only `gui.app` and `gui.progress`; those pages are generated from their current Python syntax tree and explicitly labelled source-based desktop references. They include all classes, functions, method signatures, available docstrings and complete source without claiming successful Tk import. The scientific worker, reconstruction and other GUI support modules use ordinary pdoc pages.

## Likely questions and defensible answers

- **Why use RBF and SVR?** RBF is a credible smooth interpolation baseline. SVR adds regularisation; whether that helps is tested rather than assumed.
- **Why common support?** Linear cannot predict outside its training hull. Restricting the primary comparison gives all methods the same eligible targets. Outside-hull errors remain separate.
- **What does RMSE measure?** Typical error magnitude with greater weight on large errors, in m/s. Bias measures systematic direction and may cancel.
- **Why is the CFD comparison imperfect?** Full-face inlet, sealed walls, turbulence and boundary simplifications may differ from the apparatus. The cause of the discrepancy is unresolved.
- **Did more sensors always help?** No. Placement changes too. Some independently placed larger arrays were worse; exploratory layouts do not establish an optimum.
- **What was optimised?** SVR parameters were selected using inner training folds. Layout and expanded-grid studies provide bounded exploratory evidence, not global optima.
- **What about runtime and memory?** The controlled script separates fitting, prediction and search, with warm-up and repeated timings. Tracemalloc reports traced Python allocations rather than total process memory. Small arrays do not establish large-scale scalability.
- **Did you verify the physics?** I performed numerical checks and matched measurement comparisons, with limitations. Neither test success nor conservation establishes full physical validation.
- **What did AI contribute?** Use the author-supplied statement and log. Name actual checks and decisions you personally made. Do not claim to have independently checked something solely because an agent ran a test.

## Reproduce the checks and documentation

From the repository root in the scientific environment:

```bash
PYTHONPATH=src python -m pytest -q --junitxml=docs/report/test-results.xml
python -m ruff check src tests run_all.py launch_gui.py tools/build_presentation_guide.py tools/build_api_docs.py
PYTHONPATH=src python tools/build_api_docs.py
python tools/build_presentation_guide.py
```

For the short live numerical example:

```bash
PYTHONPATH=src python -m pytest tests/test_presentation_examples.py -v
```

If Tk is installed in the scientific environment, the ordinary full `python -m pdoc jetbridge_ml -o docs/html` build can include the desktop modules. The guide builder then links their pdoc pages instead of replacing them. This revision's native layout check was skipped because Tk was unavailable. Prior November 5 GUI evidence remains historical, separate from the fresh November 11 suite.

## Before submission

The brief requires a 5–10 page main report, references/appendices excluded; an accessible GitHub link; and a zipped clone in Moodle. Ensure the final clone includes the GUI work, updated tests and docs, then verify it before submission. The documentation builders do not publish or commit changes; repository history records publication. Keep the personal AI statement accurate and be ready to explain the functions you show.
