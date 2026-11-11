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
h2,h3,summary,td{overflow-wrap:anywhere}
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
<body><h1>{esc(title)}</h1><nav><a href="../html/index.html">Report and code</a><a href="test_walkthrough.html">Six tests</a>
<a href="test_report.html">Test result</a></nav>{body}</body></html>'''


EXPLANATIONS = {
    'locations = np.array([[0.0, 0.0], [2.0, 0.0], [0.0, 2.0]])': 'Define three known sensor coordinates on a plane.',
    'values = np.array([1.0, 4.0, 9.0])': 'Attach a deliberately distinct value to each sensor so the selected neighbour is unambiguous.',
    'out = nearest_neighbor(locations, values, np.array([[0.1, 0.1], [1.8, 0.0]]))': 'Query near the first and second sensors using the production nearest-neighbour implementation.',
    'np.testing.assert_array_equal(out, [1.0, 4.0])': 'Require the two independently known neighbour values exactly; no fitting tolerance is needed here.',
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


TUTORIAL = '''# A manageable presentation and test run

## One test file, six checks

Open `tests/test_core.py`. It is the only test file needed for the presentation. Five functions produce six cases because the affine-field test runs for linear and RBF separately.

| Case | What you can explain |
| --- | --- |
| Nearest neighbour | Queries near known sensors return their expected values. |
| Error metrics | Opposite errors cancel in bias, but MAE and RMSE remain positive. |
| Linear interpolation | Reproduce a known affine field at unseen interior points. |
| RBF interpolation | Reproduce that same field with thin-plate RBF. |
| Unsupported region | Linear returns NaN outside the sensor triangle. |
| Leakage prevention | Altering a hidden target cannot change its own held-out SVR prediction. |

## Run the six checks

From the repository root in the scientific environment:

```bash
PYTHONPATH=src python -m pytest -v
```

Expected result: **6 passed**. The default configuration collects only `tests/test_core.py`. No CFD solve or display is needed. Run this before the talk and keep the output open.

On this laptop, Ubuntu already has the project environment. Use:

```bash
cd "/mnt/c/Users/mattb_ar68ij9/OneDrive/Documents/UNI/2026/MMA3001/Project/jetbridge-ml-cfd"
PYTHONPATH=src /home/mattb/projects/jetbridge-python-env/bin/python -m pytest -v
```

## A five-minute talk with room to breathe

Use slides 1–6, plus a short repository demonstration after slide 5. Other slides remain available for questions.

| Part | Time | Explain |
| --- | --- | --- |
| Slides 1–2 | 45 s | Predict speeds between sparse sensors; positions and measured speeds are the inputs. |
| Slide 3 | 40 s | Compare nearest, linear, thin-plate RBF and regularised SVR. |
| Slide 4 | 50 s | Withhold one location, tune on remaining data, and predict the removed value. |
| Slide 5 | 50 s | RBF has the lowest aggregate error; its advantage concentrates at 58 ft. |
| Repository demonstration | 45 s | Show README, one API function and one simple passing test. |
| Slide 6 | 40 s | Explain coverage limits and actual AI assistance. |

Total target: 4 minutes 30 seconds, leaving 30 seconds for transitions. Practise with a timer. The six main slides have updated notes; finish at slide 6.

## The demonstration

Open the README, metrics API and core test result before starting. Show the folder structure briefly. In the API, point to Parameters, Returns and Raises. In `test_core.py`, show `test_zero_bias_can_hide_large_local_errors`:

- Reference speeds are [0.1, 0.3] m/s; predictions are [0.3, 0.1].
- Prediction errors are +0.2 and -0.2 m/s.
- Bias is zero, while MAE and RMSE are both 0.2 m/s.
- `assert` checks the result; `pytest.approx` allows floating-point rounding.

That is enough source detail for the main talk. Use the line-by-line page for questions. For leakage questions, the final function changes sensor 0's hidden target to 9 m/s and checks its held-out SVR prediction is unchanged. Its single-candidate search keeps the regression test small; the research search is larger.

## Optional development checks

The other checks are retained in `tests/extended/`. They cover data parsing, numerical stability, CFD mapping, GUI behaviour and reproducibility. You do not need to present each one. The full WSL run still reports 128 passed and one skipped native-GUI module; the six core cases are part of that total, not duplicates.

To run everything deliberately:

```bash
PYTHONPATH=src python -m pytest tests -q
```

GitHub CI and run_all.py continue to run the full suite. A software pass does not establish physical CFD validation. The Tk layout module needs Tk and a display and is skipped in the headless worker.

## Documentation and GitHub

The tutorial, API and test report work offline after downloading/extracting the repository. GitHub-readable Markdown and slide PNGs are linked from `docs/presentation/README.md`. GitHub itself displays HTML source rather than executing the pages. Two Tk-only API pages are explicitly source-based references in this worker.

To refresh documentation after changes:

```bash
PYTHONPATH=src python -m pytest -q --junitxml=docs/report/core-test-results.xml
PYTHONPATH=src python -m pytest tests -q --junitxml=docs/report/test-results.xml
PYTHONPATH=src python tools/build_api_docs.py
python tools/build_presentation_guide.py
```

Explain only checks and decisions you actually understand. Use the supplied author statement for AI reflection; do not claim personal verification solely because an agent ran a test.
'''


def build():
    """Write the tutorial, annotated tests, catalogue and fresh-result pages."""
    OUT.mkdir(parents=True, exist_ok=True)
    report = ROOT / 'docs/report/core-test-results.xml'
    full_report = ROOT / 'docs/report/test-results.xml'
    full_cases = ET.parse(full_report).findall('.//testcase')
    full_skipped = sum(c.find('skipped') is not None for c in full_cases)
    full_failed = sum(c.find('failure') is not None or c.find('error') is not None for c in full_cases)
    full_passed = len(full_cases) - full_skipped - full_failed
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
    body += f'<p class="notice">The default run is six core cases in one file. Optional full regression run: {full_passed} passed, {full_skipped} skipped, {full_failed} failed/error. These are software/numerical checks, not physical CFD certification.</p>'
    body += '<p><a href="../report/core-test-results.xml">Core JUnit XML</a> · <a href="../report/test-results.xml">Optional full-suite JUnit XML</a></p><table><tr><th>Module</th><th>Case</th><th>Status</th><th>Reason</th></tr>' + ''.join(rows) + '</table>'
    (OUT / 'test_report.html').write_text(page('Test report — 11 November 2026', body), encoding='utf-8')
    walkthrough = '<p>Read each test as controlled inputs → production call → independent expected answer → assertion. Source is read directly at build time; no example code is substituted.</p>'
    walkthrough += annotated('tests/test_core.py')
    walkthrough += '<h2>Scope</h2><p>These tests verify stated numerical properties and split isolation. They do not validate every field or prove experimental representativeness. For all remaining tests, use the complete source catalogue.</p>'
    (OUT / 'test_walkthrough.html').write_text(page('Tests explained line by line', walkthrough), encoding='utf-8')
    markdown = '# Tests explained line by line\n\nThese are the same actual source lines as the offline HTML walkthrough. Read each test as controlled inputs, production call, expected answer and assertion.\n'
    markdown += annotated('tests/test_core.py', markdown=True)
    (OUT / 'TEST_WALKTHROUGH.md').write_text(markdown, encoding='utf-8')
    catalog = '<p>Only tests/test_core.py is needed for the presentation and default run. The extended folder below contains optional development regressions. Parametrisation can produce multiple cases per function.</p>'
    hashes = {}
    for file in sorted((ROOT / 'tests').rglob('test_*.py')):
        text = file.read_text(encoding='utf-8')
        hashes[str(file.relative_to(ROOT))] = sha256(file.read_bytes()).hexdigest()
        module = ast.parse(text)
        functions = [n for n in ast.walk(module) if isinstance(n, ast.FunctionDef) and n.name.startswith('test_')]
        items = ''.join(f'<li><code>{esc(n.name)}</code>: {esc(ast.get_docstring(n) or n.name[5:].replace("_", " "))}</li>' for n in functions)
        relative = file.relative_to(ROOT).as_posix()
        catalog += f'<details><summary>{esc(relative)} — {len(functions)} test functions</summary><p><a href="../../{esc(relative)}">Open Python source</a></p><ul>{items}</ul><pre>{esc(text)}</pre></details>'
    (OUT / 'test_catalog.html').write_text(page('Complete test source catalogue', catalog), encoding='utf-8')
    intro = f'<p class="notice">Default run: <strong>{esc(summary)}</strong>, all in tests/test_core.py. Optional full regression run: {full_passed} passed, {full_skipped} skipped. Scientific scores are unchanged. Use the shortened presentation route below.</p>'
    intro += '<h2>Repository overview</h2><p><a href="https://github.com/matt-b-0/jetbridge-ml-cfd">Published GitHub repository</a> · <a href="../../README.md">Current local README</a>. Local presentation updates are not automatically published.</p>'
    intro += '<p>data_processing reads source inputs; interpolation supplies baselines; machine_learning handles SVR; validation handles metrics and checks; cfd_interface handles numerical reference fields; gui presents the existing workflows.</p>'
    intro += '<h2>Code behind the submitted report</h2><p><a href="../html/index.html">Open the short source guide</a>: inputs, methods, hidden-sensor validation and errors. The full API is optional background.</p>'
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
    # Keep the teaching entry points short. Detailed commentary remains optional.
    (OUT / 'test_line_by_line.html').write_text(page('Optional line-by-line source commentary', walkthrough), encoding='utf-8')
    checks = '''<p>All six checks are in <a href="../../tests/test_core.py">one file: tests/test_core.py</a>. Five functions produce six cases because the known-field check runs for linear and RBF separately.</p>
<table><tr><th>Check</th><th>What you should understand</th></tr>
<tr><td>Nearest neighbour</td><td>The nearest known sensor supplies the predicted value.</td></tr>
<tr><td>Errors</td><td>Opposite errors can cancel in bias; RMSE and MAE still reveal them.</td></tr>
<tr><td>Linear interpolation</td><td>A known affine field should be reproduced at interior queries.</td></tr>
<tr><td>RBF interpolation</td><td>The same field should also be reproduced by thin-plate RBF.</td></tr>
<tr><td>Support</td><td>Linear should return NaN outside its sensor triangle.</td></tr>
<tr><td>Leakage</td><td>A hidden target must not influence the model predicting it.</td></tr></table>
<h2>Run them</h2><pre>PYTHONPATH=src python -m pytest -v</pre><p>Run from the repository root in the scientific environment. Expected result: <strong>6 passed</strong>.</p>
<h2>One example to explain aloud</h2><p>Reference speeds [0.1, 0.3] and predictions [0.3, 0.1] produce errors +0.2 and −0.2 m/s. Bias = 0; MAE = RMSE = 0.2 m/s. An assertion checks this independently known answer.</p>'''
    core = (ROOT / 'tests/test_core.py').read_text(encoding='utf-8')
    for node in ast.parse(core).body:
        if isinstance(node, ast.FunctionDef) and node.name.startswith('test_'):
            start = min([node.lineno] + [d.lineno for d in node.decorator_list])
            snippet = '\n'.join(core.splitlines()[start-1:node.end_lineno])
            checks += f'<details><summary>Show code: {esc(node.name)}</summary><pre>{esc(snippet)}</pre></details>'
    checks += '<p><a href="test_report.html">See the result</a> · <a href="test_line_by_line.html">Optional line-by-line commentary</a></p><details><summary>Optional development tests</summary><p>The remaining checks are in tests/extended. Run <code>PYTHONPATH=src python -m pytest tests -q</code> to include them. <a href="test_catalog.html">Source catalogue</a>.</p></details>'
    (OUT / 'test_walkthrough.html').write_text(page('Six core checks', checks), encoding='utf-8')
    start_page = '''<p>Use these three pages for the presentation. You do not need to learn the full API.</p>
<ol><li><a href="../html/index.html"><strong>Report and code</strong></a> — the problem, result and six functions behind the submitted PDF.</li>
<li><a href="test_walkthrough.html"><strong>Six tests</strong></a> — what each check establishes and how to run them.</li>
<li><a href="test_report.html"><strong>Test result</strong></a> — the six passing cases.</li></ol>
<h2>Short talk route</h2><p>Use slides 1–6, with a 45-second repository demonstration after slide 5. Aim for 4 minutes 30 seconds, leaving room for transitions. Finish at slide 6; other slides are available for questions.</p>
<p>Explain the problem, compare methods, describe hidden-sensor validation, show the result, then state limitations and actual AI assistance.</p>
<h2>What to demonstrate</h2><p>Open the short source guide, show <code>regression_metrics</code>, then explain the opposite-error test and its passing result. The detailed source is there if you are asked a question.</p>
<p><a href="../report/MMA3001_Jet_Bridge_FinalSubmission.pdf">Submitted report</a> · <a href="PRESENTATION_TUTORIAL.md">Rehearsal instructions</a> · <a href="README.md">PowerPoint and slide previews</a></p>'''
    (OUT / 'index.html').write_text(page('Presentation start', start_page), encoding='utf-8')
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
    verification = dict(date='2026-11-11', generated_at=datetime.now().isoformat(timespec='seconds'), passed=passed, skipped=len(skipped), failures=len(failed), full_passed=full_passed, full_skipped=full_skipped, full_failures=full_failed, junit_sha256=sha256(report.read_bytes()).hexdigest(), full_junit_sha256=sha256(full_report.read_bytes()).hexdigest(), test_source_sha256=hashes, documentation='pdoc scientific API; AST source references for two Tk-only modules', physical_validation=False)
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
