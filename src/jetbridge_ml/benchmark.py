"""Reproducible experimental plane benchmark; run with python -m jetbridge_ml.benchmark."""
import argparse
from datetime import datetime, timezone
from hashlib import sha256
from importlib.metadata import version
import json
from pathlib import Path
import platform
import subprocess
from time import perf_counter

import numpy as np
import pandas as pd
from scipy.spatial import Delaunay

from .data_processing.faa import read_speed_average
from .interpolation.plane import predict_plane
from .validation.metrics import regression_metrics
from .validation.spatial import leave_location_out

METHODS = ("nearest", "linear", "rbf")


def evaluate_plane(frame):
    """Return per-fold predictions for one replicate, without pooling other runs.

    Parameters
    ----------
    frame : pandas.DataFrame
        Parser output for a single run.

    Returns
    -------
    pandas.DataFrame
        Identical held-out coordinates per method, training rows, hull flags,
        missing-target status, and combined fit/prediction runtime.
    """
    if frame.run_id.nunique() != 1:
        raise ValueError("Evaluate one replicate at a time")
    x = frame[["x_m", "y_m"]].to_numpy()
    y = frame.speed_mps.to_numpy()
    rows = []
    for fold, (train, test) in enumerate(leave_location_out(x)):
        train = train[np.isfinite(y[train])]
        supported = Delaunay(x[train]).find_simplex(x[test], tol=1e-10) >= 0
        for method in METHODS:
            start = perf_counter()
            predicted = predict_plane(method, x[train], y[train], x[test])
            elapsed = perf_counter() - start
            for j, index in enumerate(test):
                row = frame.iloc[index].to_dict()
                row.update(method=method, fold=fold, inside_hull=bool(supported[j]),
                           prediction_mps=float(predicted[j]), seconds=elapsed / len(test),
                           train_rows=";".join(map(str, frame.iloc[train].source_row)),
                           target_available=bool(np.isfinite(y[index])))
                rows.append(row)
    return pd.DataFrame(rows)


def summarize(predictions):
    """Return coverage and errors on common hull points and extrapolation separately.

    Parameters
    ----------
    predictions : pandas.DataFrame
        Per-fold output from evaluate_plane.

    Returns
    -------
    pandas.DataFrame
        Run/method/subset metrics; counts include unsupported predictions.
    """
    rows = []
    for (run, method), group in predictions.groupby(["run_id", "method"], sort=True):
        for subset in ("common_hull", "outside_hull", "all"):
            selected = group[group.target_available]
            if subset != "all":
                selected = selected[selected.inside_hull == (subset == "common_hull")]
            valid = selected[np.isfinite(selected.prediction_mps)]
            metrics = regression_metrics(valid.speed_mps, valid.prediction_mps) if len(valid) else dict(rmse=np.nan, mae=np.nan, bias=np.nan)
            rows.append(dict(run_id=run, method=method, subset=subset,
                             n_requested=len(selected), n_predicted=len(valid),
                             coverage=len(valid)/len(selected) if len(selected) else np.nan,
                             negative_predictions=int((valid.prediction_mps < 0).sum()),
                             **metrics))
    return pd.DataFrame(rows)


def main():
    """Parse CLI options and save an auditable benchmark run to a new directory."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--pattern", default="V-S01-A-*-HN-*.txt")
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output already exists; choose a new directory to preserve prior runs")
    sources = sorted((args.dataset / "03-Averages").glob(args.pattern))
    if not sources:
        parser.error("No matching replicate averages")
    # Parse all sources before creating output: malformed files must fail visibly.
    frames = [read_speed_average(path) for path in sources]
    predictions = pd.concat([evaluate_plane(frame) for frame in frames], ignore_index=True)
    metrics = summarize(predictions)
    inventory = pd.concat(frames).groupby("run_id").agg(station_ft=("station_ft", "first"), layout_points=("source_row", "size"))
    station_metrics = metrics.merge(inventory, on="run_id").groupby(
        ["station_ft", "layout_points", "method", "subset"], as_index=False).agg(
        runs=("run_id", "size"), mean_run_rmse=("rmse", "mean"),
        mean_run_mae=("mae", "mean"), mean_run_bias=("bias", "mean"),
        n_requested=("n_requested", "sum"), n_predicted=("n_predicted", "sum"))
    root = Path(__file__).resolve().parents[2]
    def git(*options):
        result = subprocess.run(["git", "-c", f"safe.directory={root}", "-C", str(root), *options], capture_output=True, text=True)
        return result.stdout.strip() if result.returncode == 0 else None
    context = [args.dataset / "Data Dictionary.csv", args.dataset / "06-Periods/Periods.csv",
               args.dataset / "00-Templates/Boundary - Summary - SWEMA.txt"]
    input_hashes = {str(p.relative_to(args.dataset)): sha256(p.read_bytes()).hexdigest()
                    for p in sources + context}
    code_paths = sorted((root / "src/jetbridge_ml").rglob("*.py"))
    manifest = dict(
        created_utc=datetime.now(timezone.utc).isoformat(), dataset=str(args.dataset.resolve()),
        pattern=args.pattern, runs=len(sources), observations=sum(map(len, frames)),
        missing_speed_targets=int(sum(f.speed_mps.isna().sum() for f in frames)),
        methods=list(METHODS), rbf=dict(kernel="thin_plate_spline", degree=1, smoothing=0),
        split="leave one exact x/y location out; separate fit per replicate; no pooling",
        coordinates="absolute x/y metres from averages; z retained as metadata; no floor offset",
        averaging="published entire-record air-speed means; Periods.csv hashed, not applied",
        seed=None, tuning="none; exploratory cross-validation, not an untouched final test",
        python=platform.python_version(), platform=platform.platform(),
        packages={name: version(name) for name in ("numpy", "scipy", "pandas", "matplotlib", "scikit-learn", "pytest")},
        git_commit=git("rev-parse", "HEAD"), git_status=git("status", "--porcelain"),
        input_sha256=input_hashes,
        code_sha256={str(p.relative_to(root)): sha256(p.read_bytes()).hexdigest() for p in code_paths})
    args.output.mkdir(parents=True)
    predictions.to_csv(args.output / "predictions.csv", index=False)
    metrics.to_csv(args.output / "metrics.csv", index=False)
    station_metrics.to_csv(args.output / "station_metrics.csv", index=False)
    pd.concat(frames, ignore_index=True).to_csv(args.output / "observations.csv", index=False)
    (args.output / "manifest.json").write_text(json.dumps(manifest, indent=2, allow_nan=False) + "\n")
    frozen = subprocess.run([__import__("sys").executable, "-m", "pip", "freeze"],
                            capture_output=True, text=True, check=True)
    (args.output / "environment.txt").write_text(frozen.stdout)
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    common = metrics[metrics.subset == "common_hull"].groupby("method").rmse.mean().reindex(METHODS)
    fig, ax = plt.subplots(figsize=(6, 4))
    common.plot.bar(ax=ax, rot=0)
    ax.set_ylabel("Mean per-run held-out RMSE (m/s)")
    ax.set_title("Experimental reconstruction: common supported locations")
    fig.tight_layout()
    fig.savefig(args.output / "common_hull_rmse.png", dpi=180)
    plt.close(fig)
    fig, ax = plt.subplots(figsize=(7, 4))
    for method in METHODS:
        part = station_metrics[(station_metrics.method == method) & (station_metrics.subset == "common_hull")]
        ax.plot(part.station_ft, part.mean_run_rmse, marker="o", label=method)
    ax.set(xlabel="Nominal station (ft)", ylabel="Mean per-run held-out RMSE (m/s)",
           title="Experimental reconstruction: common supported locations")
    ax.legend()
    fig.tight_layout()
    fig.savefig(args.output / "station_rmse.png", dpi=180)
    plt.close(fig)
    print(f"{len(sources)} runs; {manifest['observations']} observations; output: {args.output}")
    print(common.to_string())


if __name__ == "__main__":
    main()
