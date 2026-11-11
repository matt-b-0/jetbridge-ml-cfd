# Six core checks

Open **[test_core.py](test_core.py)**. This is the only test file you need for the presentation.

| Check | What a pass establishes |
| --- | --- |
| Nearest neighbour | Known query points select the expected sensor values |
| Error metrics | Opposite errors cancel in bias while MAE and RMSE stay positive |
| Linear interpolation | A known affine field is reproduced at unseen interior points |
| RBF interpolation | The same known field is reproduced by thin-plate RBF |
| Unsupported regions | Linear interpolation marks an outside-hull query as missing |
| Leakage prevention | Changing a hidden target cannot change its own held-out SVR prediction |

Five functions produce six cases because the known-field test runs for linear and RBF separately.

From the repository root in the scientific Python environment:

```bash
PYTHONPATH=src python -m pytest -v
```

Expected result: **6 passed**. No CFD solve or desktop display is required.

The remaining regression checks are kept in [extended](extended/) for development. They are optional for your presentation. To include everything:

```bash
PYTHONPATH=src python -m pytest tests -q
```

The full WSL run has 128 passes and one skipped native-GUI module. GitHub CI and the full demo quality gate still run the full collection. No scientific checks were discarded; the six core cases were moved from the existing modules.
