"""Build an offline presentation tutorial from actual source and JUnit evidence.

Run with Python's standard library from any working directory. This does not
execute scientific tests: run pytest and pdoc first, then rebuild this guide.
"""

import ast
from datetime import datetime
from hashlib import sha256
import html
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "presentation"
STYLE = """
body{font:19px/1.6 system-ui,sans-serif;color:#142d3e;background:#fafbfc;margin:auto;max-width:1120px;padding:32px}
h1{font-size:40px;line-height:1.2}h2{margin-top:42px;color:#007f85}h3{margin-top:28px}
a{color:#006c76}nav{display:flex;gap:22px;flex-wrap:wrap;border-block:1px solid #cddadd;padding:16px 0}
table{border-collapse:collapse;width:100%;margin:18px 0}td,th{border:1px solid #cbd5db;padding:10px;text-align:left;vertical-align:top}
th{background:#e8f1f2}pre{overflow:auto;padding:18px;background:#edf2f5;font-size:15px}code{font-size:.9em}
.lines td:nth-child(1){width:42px;color:#64748b}.lines td:nth-child(2){width:52%;white-space:pre-wrap;overflow-wrap:anywhere;font:15px/1.55 Consolas,monospace}
.lines td:nth-child(3){font-size:17px}.notice{border-left:5px solid #007f85;padding:12px 20px;background:#eaf4f4}
details{margin:16px 0}summary{cursor:pointer;font-weight:650}button{font:inherit;padding:7px 15px;background:white;border:1px solid #007f85;border-radius:4px}
@media(max-width:700px){body{padding:16px;font-size:17px}h1{font-size:30px}.lines td:nth-child(2){width:45%}.lines td:nth-child(3){font-size:14px}nav{gap:12px}}
@media print{nav,button{display:none}body{max-width:none}details{display:block}}
"""


def esc(value):
    """Escape source text before inserting it in a local HTML document."""
    return html.escape(str(value))


def inline(value):
    """Render limited emphasis and inline code after escaping all input."""
    value = re.sub(r'`([^`]+)`', r'<code>\1</code>', esc(value))
    return re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', value)


def page(title, body):
    """Wrap content in a consistent offline navigation shell."""
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>{esc(title)}</title><style>{STYLE}</style></head>
<body><h1>{esc(title)}</h1><nav><a href="index.html">Presentation tutorial</a><a href="test_walkthrough.html">Tests line by line</a>
<a href="test_report.html">Fresh test report</a><a href="test_catalog.html">All test source</a><a href="../html/jetbridge_ml.html">HTML API</a>
<a href="../../README.md">README source</a></nav>{body}</body></html>'''


EXPLANATIONS = {
    'import numpy as np': 'Import NumPy for numerical arrays and independent array comparisons.',
    'import pandas as pd': 'Import pandas to construct synthetic input tables in the same format as the real workflow.',
    'import pytest': 'Import pytest for approximate scalar comparisons, expected exceptions and parametrised cases.',
    'actual = np.array([0.1, 0.3])': 'Define two known reference speeds in m/s. These are synthetic test values, not FAA observations.',
    'predicted = np.array([0.3, 0.1])': 'Reverse the values: prediction minus reference becomes +0.2 and -0.2 m/s.',
    'metrics = regression_metrics(actual, predicted)': 'Call the actual production metric function with the two arrays.',
    'assert metrics["bias"] == pytest.approx(0.0, abs=1e-12)': 'The average signed error is zero. Allow an absolute 1e-12 rounding difference near zero.',
    'assert metrics["mae"] == pytest.approx(0.2)': 'The mean of the absolute errors is (0.2 + 0.2)/2 = 0.2 m/s.',
    'assert metrics["rmse"] == pytest.approx(0.2)': 'The square root of the mean squared error is sqrt((0.04 + 0.04)/2) = 0.2 m/s.',
    '@pytest.mark.parametrize("method", ["nearest", "linear", "rbf"])': 'Run the following function three times, once for each conventional method. Each case counts separately.',
    'sensors = np.array([[0.0, 0.0], [1.0, 0.0], [0.0, 1.0], [1.0, 1.0]])': 'Use four corner sensors on a unit square in a planar coordinate system.',
    'speeds = np.array([0.1, 0.2, 0.3, 0.4])': 'Attach one scalar speed to each coordinate, keeping coordinate/value pairs aligned.',
    'queries = np.array([[0.12, 0.18], [0.83, 0.74]])': 'Choose two interior query points. Neither has a nearest-neighbour distance tie.',
    'order = np.array([2, 0, 3, 1])': 'Specify a different sensor row order without altering the physical data.',
    'original = predict_plane(method, sensors, speeds, queries)': 'Calculate predictions with the original row ordering.',
    'reordered = predict_plane(method, sensors[order], speeds[order], queries)': 'Apply the same permutation to coordinates and speeds, then predict at unchanged queries.',
    'np.testing.assert_allclose(original, reordered, rtol=0.0, atol=1e-12)': 'Require predictions to agree within absolute numerical tolerance; CSV row ordering should not change this case.',
    'actual = np.array([0.1, 0.2, 0.3])': 'Set three reference speeds for a unit-consistency check.',
    'predicted = np.array([0.12, 0.18, 0.34])': 'Set known predictions with nonzero errors and positive aggregate bias.',
    'metres = regression_metrics(actual, predicted)': 'Calculate the errors using speeds expressed in m/s.',
    'centimetres = regression_metrics(100.0 * actual, 100.0 * predicted)': 'Convert both arrays to cm/s and calculate metrics again.',
    'for name in ("rmse", "mae", "bias"):': 'Check each of the three metrics independently.',
    'assert centimetres[name] == pytest.approx(100.0 * metres[name])': 'Verify linear unit scaling: each speed-error metric has speed units, rather than squared-speed units.',
    'with pytest.raises(ValueError, match="finite"):': 'Expect the production function to reject a non-finite prediction with a relevant error message.',
    'regression_metrics([0.1, 0.2], [0.1, np.nan])': 'Supply one missing prediction. The caller must explicitly choose supported targets before scoring.',
    'GRID=dict(C=[.1],gamma=[.1],epsilon=[.002])': 'Use one SVR candidate to keep the regression test fast. This is not the full research search.',
    'x,y=np.meshgrid([0.,.5,1.],[0.,.5,1.])': 'Create a 3 by 3 planar grid containing nine distinct sensor locations.',
    "frame=pd.DataFrame(dict(x_m=x.ravel(),y_m=y.ravel(),z_m=3.05,": 'Begin a synthetic one-run input table; flatten the coordinate grid and assign a fixed streamwise position.',
    "speed_mps=.1+.02*x.ravel()+.01*y.ravel(),source_row=np.arange(9),run_id='one'))": 'Use an independently specified affine speed field and retain source-row IDs for auditing.',
    'first,_,audit=evaluate_experimental_plane(frame,GRID)': 'Run the real nested evaluation; keep predictions and the training/split audit.',
    "changed=frame.copy(); changed.loc[0,'speed_mps']=9.": 'Copy the table, then replace only sensor 0’s target with an extreme value.',
    'second,_,_=evaluate_experimental_plane(changed,GRID)': 'Repeat real fitting and selection with that altered table.',
    "a=first[(first.fold==0)&(first.method=='svr')].iloc[0]": 'Select the original prediction from the fold that withheld sensor 0.',
    "b=second[(second.fold==0)&(second.method=='svr')].iloc[0]": 'Select the equivalent prediction after changing the hidden target.',
    'assert a.prediction_mps==b.prediction_mps': 'Require the prediction to be unchanged: a hidden answer must not influence its fitted model.',
    'for item in audit[audit.outer_source_row==0].itertuples():': 'Inspect all inner split records associated with outer test sensor 0.',
    "assert '0' not in item.outer_training_source_rows.split(';')": 'Check that sensor 0 never appears in the outer training row IDs.',
    "assert set(item.training_indices.split(';')).isdisjoint(item.validation_indices.split(';'))": 'Check that inner training and validation indices do not overlap.',
    'x=np.array([[0,0],[0,0],[1,0],[1,1],[0,1],[.5,.5]],float)': 'Include two observations at the same coordinate to test grouped-location exclusion.',
    'y=.1+.01*x[:,0]': 'Assign a known speed varying only with the first coordinate.',
    '_,_,_,audit=select_plane_svr(x,y,grid=GRID)': 'Call training-only parameter selection and retain its inner split/scaler audit.',
    'for row in audit.itertuples():': 'Inspect each recorded inner fold.',
    "train=np.array(list(map(int,row.training_indices.split(';'))))": 'Decode the stored training indices into an integer NumPy array.',
    "val=np.array(list(map(int,row.validation_indices.split(';'))))": 'Decode the stored validation indices separately.',
    "np.testing.assert_allclose(list(map(float,row.scaler_mean.split(';'))),x[train].mean(axis=0))": 'Independently calculate training-coordinate means and compare them with the fitted scaler means.',
    'assert set(map(tuple,x[train])).isdisjoint(map(tuple,x[val]))': 'Check coordinates, not just row numbers: duplicate locations must stay on the same side of the split.',
    '@pytest.mark.parametrize("method", ["linear", "rbf"])': 'Exercise both interpolators that should reproduce the specified affine field.',
    'x = np.array([[0, 0], [1, 0], [0, 1], [1, 1], [.5, .5]])': 'Define four square corners and one interior training coordinate.',
    'q = np.array([[.2, .3], [.6, .8]])': 'Choose two interior points that are not training sensors.',
    'result = predict_plane(method, x, 2 + 3*x[:, 0] - x[:, 1], q)': 'Fit using values from the known affine formula f(x,y)=2+3x-y and predict the query points.',
    'np.testing.assert_allclose(result, 2 + 3*q[:, 0] - q[:, 1], atol=1e-12)': 'Compare with the formula evaluated independently at the queries. This verifies an exact-property benchmark.',
    'x = np.array([[0, 0], [1, 0], [0, 1]])': 'Use three non-collinear coordinates defining a triangle.',
    'result = predict_plane("linear", x, [1, 1, 1], [[.2, .2], [2, 2]])': 'Predict once inside the triangle and once well outside it, using constant training values.',
    'assert result[0] == pytest.approx(1)': 'Inside support, interpolation should reproduce the constant value.',
    'assert np.isnan(result[1])': 'Outside support, require an explicit missing value rather than an invented linear extrapolation.',
}


def explain(line):
    """Explain selected demonstration lines, retaining their exact source."""
    text = line.strip()
    if not text:
        return 'Blank line separates logical steps; it has no computational effect.'
    if text in EXPLANATIONS:
        return EXPLANATIONS[text]
    if text.startswith(('from ', 'import ')):
        return 'Import the production function or supporting library named here; this is the implementation the test exercises.'
    if text.startswith('def '):
        name = text.split('def ', 1)[1].split('(')[0]
        return 'Define the test: ' + name.removeprefix('test_').replace('_', ' ') + '. pytest discovers names starting with test_.'
    if text.startswith(('"""', "'''")):
        return 'Documentation states the property being tested; it is not an assertion or a numerical operation.'
    if text.startswith('#'):
        return 'Comment explaining intent; Python does not execute it.'
    return 'Continuation of the module documentation describing the scope and limits of these checks.'


def annotated(relative, selected=None, markdown=False):
    """Render exact source lines and explanations for selected test functions."""
    source = (ROOT / relative).read_text(encoding='utf-8')
    lines = source.splitlines()
    indices = set(range(len(lines))) if selected is None else set()
    if selected is not None:
        tree = ast.parse(source)
        for node in tree.body:
            if isinstance(node, ast.FunctionDef) and node.name in selected:
                start = min([node.lineno] + [d.lineno for d in node.decorator_list])
                indices.update(range(start - 1, node.end_lineno))
            elif isinstance(node, (ast.Import, ast.ImportFrom)):
                indices.update(range(node.lineno - 1, node.end_lineno))
            elif isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'GRID' for t in node.targets):
                indices.update(range(node.lineno - 1, node.end_lineno))
    if markdown:
        rows = []
        for i in sorted(indices):
            code = lines[i].replace('|', '&#124;') or '(blank)'
            rows.append(f'| {i+1} | `{code}` | {explain(lines[i])} |')
        return f'\n## {relative}\n\n[Open actual source](../../{relative}).\n\n| Line | Actual code | Explanation |\n| --- | --- | --- |\n' + '\n'.join(rows) + '\n'
    rows = ''.join(f'<tr id="{Path(relative).stem}-L{i+1}"><td>{i+1}</td><td>{esc(lines[i])}</td><td>{esc(explain(lines[i]))}</td></tr>' for i in sorted(indices))
    return f'<h2>{esc(relative)}</h2><p><a href="../../{relative}">Open original source</a>. Line numbers below refer to that exact file.</p><table class="lines"><tr><th>Line</th><th>Actual code</th><th>Explanation</th></tr>{rows}</table>'


TUTORIAL = '''# Presentation tutorial

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
'''


def build():
    """Write the tutorial, annotated tests, catalogue and fresh-result pages."""
    OUT.mkdir(parents=True, exist_ok=True)
    report = ROOT / 'docs/report/test-results.xml'
    tree = ET.parse(report)
    cases = tree.findall('.//testcase')
    skipped = [c for c in cases if c.find('skipped') is not None]
    failed = [c for c in cases if c.find('failure') is not None or c.find('error') is not None]
    passed = len(cases) - len(skipped) - len(failed)
    summary = f'{passed} passed, {len(skipped)} skipped, {len(failed)} failed/error'
    rows = []
    for c in cases:
        child = next((c.find(tag) for tag in ('failure', 'error', 'skipped') if c.find(tag) is not None), None)
        state = child.tag if child is not None else 'passed'
        detail = child.get('message', '') if child is not None else ''
        rows.append(f'<tr><td>{esc(c.get("classname"))}</td><td>{esc(c.get("name"))}</td><td>{esc(state)}</td><td>{esc(detail)}</td></tr>')
    suite = tree.find('.//testsuite')
    body = f'<h2>{esc(summary)}</h2><p>JUnit timestamp: {esc(suite.get("timestamp"))}. Suite duration: {esc(suite.get("time"))} seconds.</p>'
    body += '<p class="notice">Fresh WSL scientific-worker execution. Tk/display-dependent layout tests were skipped, not passed. This report checks software/numerical behaviour; it does not certify physical CFD accuracy.</p>'
    body += '<p><a href="../report/test-results.xml">Original JUnit XML</a></p><table><tr><th>Module</th><th>Case</th><th>Status</th><th>Reason</th></tr>' + ''.join(rows) + '</table>'
    (OUT / 'test_report.html').write_text(page('Test report — 11 November 2026', body), encoding='utf-8')
    walkthrough = '<p>Read each test as controlled inputs → production call → independent expected answer → assertion. Source is read directly at build time; no example code is substituted.</p>'
    walkthrough += annotated('tests/test_presentation_examples.py')
    walkthrough += annotated('tests/test_plane_benchmark.py', {'test_affine_field_reproduction', 'test_linear_extrapolation_is_explicit'})
    walkthrough += annotated('tests/test_four_workstreams.py', {'test_nested_test_target_does_not_change_its_model', 'test_inner_scaling_and_location_groups_exclude_validation'})
    walkthrough += '<h2>Scope</h2><p>These tests verify stated numerical properties and split isolation. They do not validate every field or prove experimental representativeness. For all remaining tests, use the complete source catalogue.</p>'
    (OUT / 'test_walkthrough.html').write_text(page('Tests explained line by line', walkthrough), encoding='utf-8')
    markdown = '# Tests explained line by line\n\nThese are the same actual source lines as the offline HTML walkthrough. Read each test as controlled inputs, production call, expected answer and assertion.\n'
    markdown += annotated('tests/test_presentation_examples.py', markdown=True)
    markdown += annotated('tests/test_plane_benchmark.py', {'test_affine_field_reproduction', 'test_linear_extrapolation_is_explicit'}, markdown=True)
    markdown += annotated('tests/test_four_workstreams.py', {'test_nested_test_target_does_not_change_its_model', 'test_inner_scaling_and_location_groups_exclude_validation'}, markdown=True)
    (OUT / 'TEST_WALKTHROUGH.md').write_text(markdown, encoding='utf-8')
    catalog = '<p>All current test modules, with exact expandable source. Parametrisation can produce multiple pytest cases per function. See the fresh report for executed case names and skip reasons.</p>'
    hashes = {}
    for file in sorted((ROOT / 'tests').glob('test_*.py')):
        text = file.read_text(encoding='utf-8')
        hashes[str(file.relative_to(ROOT))] = sha256(file.read_bytes()).hexdigest()
        module = ast.parse(text)
        functions = [n for n in ast.walk(module) if isinstance(n, ast.FunctionDef) and n.name.startswith('test_')]
        items = ''.join(f'<li><code>{esc(n.name)}</code>: {esc(ast.get_docstring(n) or n.name[5:].replace("_", " "))}</li>' for n in functions)
        catalog += f'<details><summary>{esc(file.name)} — {len(functions)} test functions</summary><p><a href="../../tests/{esc(file.name)}">Open Python source</a></p><ul>{items}</ul><pre>{esc(text)}</pre></details>'
    (OUT / 'test_catalog.html').write_text(page('Complete test source catalogue', catalog), encoding='utf-8')
    intro = f'<p class="notice">Current verification: <strong>{esc(summary)}</strong>. Ruff correctness gate passed. Scientific scores are unchanged. Main talk: slides 1–9, target 300 seconds; backups are for questions.</p>'
    intro += '<h2>Repository overview</h2><p><a href="https://github.com/matt-b-0/jetbridge-ml-cfd">Published GitHub repository</a> · <a href="../../README.md">Current local README</a>. Local presentation updates are not automatically published.</p>'
    intro += '<p>data_processing reads source inputs; interpolation supplies baselines; machine_learning handles SVR; validation handles metrics and checks; cfd_interface handles numerical reference fields; gui presents the existing workflows.</p>'
    intro += '<h2>Open the API pages</h2><ul><li><a href="../html/jetbridge_ml/validation/metrics.html">RMSE, MAE and bias</a></li><li><a href="../html/jetbridge_ml/interpolation/plane.html">Interpolation methods and support</a></li><li><a href="../html/jetbridge_ml/machine_learning/selection.html">Training-only SVR selection</a></li><li><a href="../html/jetbridge_ml/validation/reconstruction_lab.html">Reconstruction Lab experiments</a></li><li><a href="../html/jetbridge_ml/gui/app.html">Desktop application reference</a></li><li><a href="../html/jetbridge_ml/gui/progress.html">Residual display reference</a></li></ul>'
    # A deliberately simple Markdown rendering keeps the builder standard-library only.
    blocks = []
    in_code = False
    in_table = False
    for line in TUTORIAL.splitlines():
        if not line.startswith('|') and in_table:
            blocks.append('</table>')
            in_table = False
        if line.startswith('```'):
            blocks.append('</pre>' if in_code else '<pre>')
            in_code = not in_code
        elif in_code:
            blocks.append(esc(line) + '\n')
        elif line.startswith('## '):
            blocks.append('<h2>' + esc(line[3:]) + '</h2>')
        elif line.startswith('# '):
            continue
        elif line.startswith('|'):
            cells = [value.strip() for value in line.strip('|').split('|')]
            if all(re.fullmatch(r'[-: ]+', value) for value in cells):
                continue
            if not in_table:
                blocks.append('<table>')
                in_table = True
            blocks.append('<tr>' + ''.join('<td>' + esc(value) + '</td>' for value in cells) + '</tr>')
        elif line.strip():
            blocks.append('<p>' + inline(line) + '</p>')
    (OUT / 'index.html').write_text(page('Jet Bridge presentation tutorial', intro + ''.join(blocks)), encoding='utf-8')
    (OUT / 'PRESENTATION_TUTORIAL.md').write_text(TUTORIAL, encoding='utf-8')
    for name in ('app', 'progress'):
        dest = ROOT / f'docs/html/jetbridge_ml/gui/{name}.html'
        if dest.exists() and 'source-based desktop reference' not in dest.read_text(encoding='utf-8'):
            continue  # Preserve genuine pdoc output when the runtime can import Tk.
        source_path = ROOT / f'src/jetbridge_ml/gui/{name}.py'
        source = source_path.read_text(encoding='utf-8')
        module = ast.parse(source)
        members = []
        for node in ast.walk(module):
            if isinstance(node, (ast.ClassDef, ast.FunctionDef)):
                signature = node.name if isinstance(node, ast.ClassDef) else f'{node.name}({ast.unparse(node.args)})'
                members.append(f'<h3>{esc(signature)}</h3><p>Source line {node.lineno}. {esc(ast.get_docstring(node) or "See implementation and desktop usage guide for behaviour.")}</p>')
        content = '<p class="notice">Current source-based desktop reference. This headless worker has no Tk and did not import or execute this module. Signatures and docstrings are extracted with Python ast; this is not a pdoc introspection page.</p>'
        content += '<p><a href="../../../presentation/index.html">Presentation tutorial</a> · <a href="../../../GUI.md">Desktop usage guide</a></p>'
        content += ''.join(members) + '<h2>Complete current source</h2><pre>' + esc(source) + '</pre>'
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(f'<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{name} desktop reference</title><style>{STYLE}</style><body><h1>gui.{name}</h1>{content}</body></html>', encoding='utf-8')
    verification = dict(date='2026-11-11', generated_at=datetime.now().isoformat(timespec='seconds'), passed=passed, skipped=len(skipped), failures=len(failed), junit_sha256=sha256(report.read_bytes()).hexdigest(), test_source_sha256=hashes, documentation='pdoc scientific API; AST source references for two Tk-only modules', physical_validation=False)
    (OUT / 'verification.json').write_text(json.dumps(verification, indent=2) + '\n', encoding='utf-8')
    # Verify local HTML navigation and fragments against existing files.
    missing = []
    for file in list(OUT.glob('*.html')) + [ROOT / f'docs/html/jetbridge_ml/gui/{n}.html' for n in ('app', 'progress')]:
        for link in re.findall(r'href="([^"]+)"', file.read_text(encoding='utf-8')):
            if link.startswith(('http:', 'https:', '#')):
                continue
            if not (file.parent / html.unescape(link).split('#')[0]).resolve().exists():
                missing.append(f'{file.name}: {link}')
    if missing:
        raise RuntimeError('Broken local links: ' + '; '.join(missing))
    print(summary)
    print(f'Guide: {OUT / "index.html"}')


if __name__ == '__main__':
    build()
