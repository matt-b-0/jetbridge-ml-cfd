"""Build a short HTML source-code guide tied to the submitted report.

Uses actual function source and bundled report figures. The full generated
API remains optional; this guide is the normal documentation entry point.
"""

import ast
from hashlib import sha256
import html
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'docs/html'
REPORT = ROOT / 'docs/report/MMA3001_Jet_Bridge_FinalSubmission.pdf'
STYLE = '''
body{max-width:960px;margin:auto;padding:30px 24px 60px;background:#fff;color:#193242;font:19px/1.6 system-ui,sans-serif}
h1{font-size:38px;line-height:1.15;margin-bottom:12px}h2{font-size:27px;margin-top:38px;color:#006d73}h3{font-size:21px;margin-bottom:8px}
nav{display:flex;gap:24px;flex-wrap:wrap;border-block:1px solid #cfdbdf;padding:13px 0;margin:24px 0}a{color:#006d73}
table{width:100%;border-collapse:collapse;margin:18px 0;font-size:17px}th,td{padding:10px;border-bottom:1px solid #d6e0e4;text-align:left;vertical-align:top}th{background:#eff5f6}
pre{font:15px/1.55 Consolas,monospace;overflow:auto;background:#f2f5f6;padding:18px}code{font-family:Consolas,monospace;font-size:.88em}
details{padding:14px 0;border-bottom:1px solid #d6e0e4}summary{cursor:pointer;font-weight:650}.muted{color:#566873}.result{font-size:21px;font-weight:650}
@media(max-width:650px){body{font-size:17px;padding:22px 15px}h1{font-size:31px}table{font-size:14px}th,td{padding:7px}nav{gap:15px}}
@media print{details{break-inside:avoid}body{font-size:11pt}nav{display:none}}
'''

FUNCTIONS = [
    ('read_speed_average', 'data_processing/faa.py', 'Read the measurements', 2,
     'One FAA averaged-data text file.', 'A table of x, y, z in metres, speed in m/s and run identifiers.',
     'Checks the file structure, units and coordinates. Converts the -9999 missing-speed marker to NaN; invalid negative/infinite speeds are rejected.'),
    ('predict_plane', 'interpolation/plane.py', 'Apply an interpolation method', 3,
     'A method name, retained sensor coordinates and speeds, and query coordinates.', 'One predicted speed per query; linear gives NaN outside the sensor hull.',
     'Chooses nearest neighbour, linear or thin-plate RBF. It uses the coordinates supplied by the caller; the report workflow supplies training-only standardised coordinates.'),
    ('select_plane_svr', 'machine_learning/selection.py', 'Choose SVR settings', 3,
     'Training coordinates and speeds, with optional location groups and parameter grid.', 'A fitted SVR, selected settings, search results and split/scaler audit.',
     'Uses three inner folds. Scaling is fitted inside each training fold. The outer hidden sensor must already have been excluded by the caller.'),
    ('evaluate_experimental_plane', 'experimental_svr.py', 'Predict sensors that were hidden', 3,
     'One experimental run; an optional SVR search grid.', 'Held-location predictions, parameter-search records and split/scaler audits.',
     'Removes one location before tuning, predicts it with all five methods, and repeats for every location. Each experimental run is fitted separately.'),
    ('regression_metrics', 'validation/metrics.py', 'Calculate prediction error', 4,
     'Reference speeds and predictions at the same supported locations.', 'RMSE, MAE and signed bias, all in m/s when the inputs are m/s.',
     'Computes prediction minus observation. Rejects empty, mismatched or non-finite arrays. Positive bias means overprediction.'),
    ('summarize', 'benchmark.py', 'Compare methods fairly', 4,
     'The table of held-location predictions and hull flags.', 'Per-run method errors and coverage for inside, outside and all targets.',
     'Keeps unsupported queries visible in coverage counts. The report then averages the per-run errors equally over runs; it does not pool every error into one RMSE.'),
]


def esc(value):
    """Escape values before embedding source or text in HTML."""
    return html.escape(str(value))


def function_source(relative, name):
    """Return the exact signature, source span and line number for a function."""
    file = ROOT / 'src/jetbridge_ml' / relative
    text = file.read_text(encoding='utf-8')
    node = next(n for n in ast.parse(text).body if isinstance(n, ast.FunctionDef) and n.name == name)
    source = '\n'.join(text.splitlines()[node.lineno-1:node.end_lineno])
    return f'{name}({ast.unparse(node.args)})', source, node.lineno


def build():
    """Write simple HTML and a matching GitHub-readable source guide."""
    if not REPORT.exists():
        raise FileNotFoundError('Bundle the exact submitted PDF before building the guide')
    OUT.mkdir(parents=True, exist_ok=True)
    body = '''<h1>Code behind my submitted report</h1>
<p>A short guide to <em>Jet Bridge Air Speed Reconstruction</em>, submitted 27 October 2026. Start here for the presentation.</p>
<nav><a href="#report">The report</a><a href="#code">The code</a><a href="../presentation/test_walkthrough.html">Six tests</a></nav>
<h2 id="report">1. The report in one minute</h2>
<p><strong>Question:</strong> can sparse sensor measurements reconstruct air speed across a jet bridge, and does SVR improve on simpler interpolation?</p>
<p><strong>Workflow:</strong> read measured speeds → hide one sensor → fit the retained sensors → predict the hidden speed → compare errors.</p>
<p>Inputs are sensor positions in metres and scalar speeds in m/s. Outputs are predicted speeds, held-location errors and a mask showing spatial support. The study uses 36 averaged files and 504 sensor means from one apparatus.</p>
<table><tr><th>Method</th><th>Mean per-run RMSE (m/s)</th></tr>
<tr><td>Mean baseline</td><td>0.06765</td></tr><tr><td>Nearest neighbour</td><td>0.07129</td></tr>
<tr><td>Linear</td><td>0.05524</td></tr><tr><td>Thin-plate RBF</td><td><strong>0.04959</strong></td></tr><tr><td>SVR</td><td>0.05774</td></tr></table>
<p class="result">RBF has the lowest aggregate error, but its advantage concentrates at the 58 ft station.</p>
<p>These scores use the same 360 supported targets. Linear cannot extrapolate; the other 144 targets are reported separately. The sensor hull is the polygon enclosing known sensor positions. More than half of the physical section lies outside that hull in the illustrated layouts. Smooth maps do not establish accuracy there.</p>
<p>Report pages 6–9 provide supporting CFD, sensitivity and timing evidence. CFD is a separate numerical reference, with unresolved physical bias. The thermal extension is unconverged and excluded from trusted training/reference data.</p>
<p><a href="../report/MMA3001_Jet_Bridge_FinalSubmission.pdf">Open the exact submitted PDF</a> · <a href="../report/MMA3001_Jet_Bridge_FinalSubmission.pdf#page=10">Read its conclusions</a></p>
<h2 id="code">2. The six functions worth knowing</h2>
<p>These are the actual functions used by the report workflow. Each entry explains its inputs, outputs and purpose. Open the code only when you want the implementation detail.</p>'''
    markdown = '''# Code behind the submitted report

This is the GitHub-readable version of the short HTML source documentation. The exact [submitted PDF](../report/MMA3001_Jet_Bridge_FinalSubmission.pdf) is retained unchanged.

**Question:** can sparse measurements reconstruct jet-bridge speed, and does SVR improve on conventional interpolation?

**Workflow:** read measurements → hide one sensor → fit retained sensors → predict the hidden speed → compare errors.

RBF has the lowest mean per-run common-support RMSE (0.04959 m/s), compared with SVR (0.05774 m/s). Its advantage concentrates at 58 ft; station and layout density are confounded. The 360 common supported targets are distinct from the physical hull area. CFD reconstruction and experimental prediction remain separate comparisons.

## Six functions to understand
'''
    for name, relative, title, report_page, inputs, outputs, explanation in FUNCTIONS:
        signature, source, line = function_source(relative, name)
        body += f'''<h3 id="{esc(name)}">{esc(title)} — <code>{esc(name)}</code></h3>
<p><strong>Input:</strong> {esc(inputs)}<br><strong>Output:</strong> {esc(outputs)}<br><strong>What it does:</strong> {esc(explanation)}</p>
<p class="muted">Report p. {report_page} · <a href="../../src/jetbridge_ml/{esc(relative)}">{esc(relative)}, line {line}</a></p>
<details><summary>Show this function’s actual code</summary><pre>{esc(source)}</pre></details>'''
        markdown += f'\n### {title}: `{name}`\n\n- **Input:** {inputs}\n- **Output:** {outputs}\n- **Purpose:** {explanation}\n\nReport p. {report_page}. [Open actual source](../../src/jetbridge_ml/{relative}#L{line}).\n'
    body += '''<h2>3. Show one simple test</h2>
<p>All six core checks are in <a href="../../tests/test_core.py">tests/test_core.py</a>. Run them from the repository root in the scientific environment:</p>
<pre>PYTHONPATH=src python -m pytest -v</pre>
<p>For the talk, explain the metric test: errors of +0.2 and −0.2 m/s give zero bias, but MAE and RMSE are still 0.2 m/s. Then point to the passing result.</p>
<p><a href="../presentation/test_walkthrough.html">Explain the six checks</a> · <a href="../presentation/test_report.html">See the six-test result</a> · <a href="../presentation/PRESENTATION_TUTORIAL.md">Short presentation plan</a></p>
<details><summary>Optional: the full API reference</summary><p><a href="full_api.html">Open all generated API documentation</a>. This is background reference; the six functions above are sufficient for the main source-code demonstration.</p></details>
<p class="muted">The submitted report records its original 82-test development snapshot. Current organisation: six core cases by default; the full regression collection has 128 passes and one skipped native-GUI module. This later documentation/test reorganisation changes no report results.</p>'''
    markdown += '''
## Six core checks

Open [test_core.py](../../tests/test_core.py) and run `PYTHONPATH=src python -m pytest -v` from the repository root. For the talk, explain the test showing that opposite signed errors cancel in bias while RMSE and MAE remain positive. [Test instructions](../../tests/README.md) cover all six cases.

Report pp. 6–9 support the main comparison with separate CFD, sensitivity and timing evidence. Convergence does not establish physical agreement; the thermal extension remains unconverged.

The submitted report's 82-test count is its original development snapshot. The current default is six core cases, with the wider regression collection retained for development. Scientific results are unchanged.
'''
    document = f'<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Code behind my submitted report</title><style>{STYLE}</style></head><body>{body}</body></html>'
    for filename in ('index.html', 'jetbridge_ml.html'):
        (OUT / filename).write_text(document, encoding='utf-8')
    (OUT / 'REPORT_CODE_GUIDE.md').write_text(markdown, encoding='utf-8')
    (OUT / 'report_guide_manifest.json').write_text(json.dumps(dict(report=REPORT.name, report_sha256=sha256(REPORT.read_bytes()).hexdigest(), functions=[dict(name=n, source='src/jetbridge_ml/'+p) for n,p,*_ in FUNCTIONS]), indent=2) + '\n', encoding='utf-8')
    missing = []
    for href in re.findall(r'href="([^"]+)"', document):
        if href.startswith('#'):
            continue
        if not (OUT / html.unescape(href).split('#')[0]).resolve().exists():
            missing.append(href)
    if missing:
        raise RuntimeError('Missing guide link targets: ' + ', '.join(missing))
    print('Built report-focused HTML documentation for six actual functions')


if __name__ == '__main__':
    build()
