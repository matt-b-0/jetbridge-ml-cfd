# A manageable presentation and test run

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
