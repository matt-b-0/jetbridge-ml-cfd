# Development linting tests and documentation

Run commands from the repository root. The standard development install is:

```bash
python -m pip install -e '.[dev]'
```

For the tested research environment, use the pinned `requirements-benchmark.txt` and then `python -m pip install --no-deps -e .` as described in LIVE_DEMO.md.

## Pylint-style checking with Ruff

Ruff is the selected fast static checker. It fills the requested Pylint-like role; it is not Pylint itself. The initial repository gate checks syntax errors, undefined names and invalid control/statement patterns using E9, F63, F7 and F82. It deliberately does not claim that the legacy compact scientific scripts satisfy every stylistic rule.

```bash
python -m ruff check src tests run_all.py
python -m pytest -q
python -m pytest -q --junitxml=test-results.xml
python -m pdoc jetbridge_ml -o docs/html
```

GitHub Actions runs the same lint gate and automated tests on Python 3.10 and 3.12 and saves the JUnit reports. A lint pass is not a numerical test, and neither establishes physical validation of the CFD. The demo runner runs lint/tests first unless `--skip-quality` is explicitly selected and recorded.

To review broader style and unused-import diagnostics without changing files:

```bash
python -m ruff check --select E,F src tests run_all.py
```

That broader audit may report legacy findings; it is not the current CI acceptance gate. Review changes before applying any automated fixes. Do not mass-format research scripts as part of a scientific correction or silently suppress correctness findings. Formatting should be a separate reviewed change.

## Adding work safely

Keep source parsers, interpolation, fitted ML, CFD export and validation in their existing modules. `run_all.py` orchestrates them; it must not introduce a second implementation of the physical model or tune against outer test targets. Add a NumPy-style docstring for new public scientific functions and meaningful regression checks for changed behaviour.

The demo data manifest verifies bundled file hashes. Original FAA/NRC files are preserved; changes to generated exports need new provenance. `.gitattributes` preserves demo input bytes across Windows/Linux clones. Output directories are fresh and ignored. Never commit generated meshes or full time folders. The data attribution is independent of the still-undecided project-code licence.

Use `python run_all.py --profile replay` to test included-data figure generation and live/full profiles for real OpenFOAM execution. [LIVE_DEMO.md](LIVE_DEMO.md) defines what is fresh and what is archived in each profile. The tracked report builders regenerate Word files separately and require python-docx plus a layout render; a successful Python figure run does not update a Word report automatically.
