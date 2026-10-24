"""Export solved OpenFOAM slices and plot scalar-speed differences to FAA means.

Run inside the Linux Python environment; original CFD dictionaries are not edited.
"""
import argparse
from hashlib import sha256
import json
from pathlib import Path
import re
import shlex
import subprocess

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import Normalize, TwoSlopeNorm
import numpy as np
import pandas as pd
from scipy.spatial import cKDTree

from jetbridge_ml.data_processing.faa import read_speed_average
from jetbridge_ml.validation.metrics import regression_metrics

STATIONS = (10, 16, 22, 28, 34, 40, 46, 52, 58)


def align_samples(expected, sampled):
    """Match raw xyz/U rows to source positions, rejecting ambiguous locations.

    Parameters
    ----------
    expected : array-like
        Source xyz positions of shape (n, 3), metres.
    sampled : array-like
        OpenFOAM xyz/Ux/Uy/Uz rows of shape (n, 6).

    Returns
    -------
    numpy.ndarray
        Sampled rows in the source coordinate order.
    """
    expected, sampled = np.asarray(expected, float), np.asarray(sampled, float)
    if sampled.shape != (len(expected), 6) or not np.isfinite(sampled).all():
        raise ValueError("Expected one finite xyz/U row per experimental sensor")
    distance, indices = cKDTree(sampled[:, :3]).query(expected)
    if np.max(distance) > 1e-7 or len(set(indices)) != len(expected):
        raise ValueError("Sample coordinates do not uniquely match experimental sensors")
    return sampled[indices]


def mesh_profile(path):
    """Extract z, floor and ceiling elevations from the actual 16-vertex case.

    Parameters
    ----------
    path : str or Path
        Case blockMeshDict path, with SI coordinates.

    Returns
    -------
    tuple
        Width, station z values, floor and ceiling elevations in metres.
    """
    text = Path(path).read_text()
    if not re.search(r"convertToMeters\s+1\s*;", text):
        raise ValueError("This plotting workflow requires metre-valued mesh coordinates")
    part = text.split("vertices", 1)[1].split("blocks", 1)[0]
    vertices = np.array([list(map(float, match)) for match in
                         re.findall(r"\(([\d.]+)\s+([\d.]+)\s+([\d.]+)\)", part)])
    if vertices.shape != (16, 3):
        raise ValueError("Expected 16 bridge vertices")
    return vertices[:, 0].max(), vertices[::4, 2], vertices[::4, 1], vertices[2::4, 1]


def main():
    """Export slices and cell-sampled probes, then save comparison figures."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", type=Path, required=True)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--time", default="237")
    parser.add_argument("--foam-bashrc", type=Path,
                        default=Path("/usr/lib/openfoam/openfoam2412/etc/bashrc"))
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Choose a new output directory; existing results are preserved")
    case, output = args.case.resolve(), args.output.resolve()
    if not (case / args.time / "U").exists():
        parser.error("Requested saved CFD velocity field not found")
    frames = {s: read_speed_average(args.dataset / f"03-Averages/V-S01-A-{s}-HN-1.txt")
              for s in STATIONS}
    width, zs, floors, ceilings = mesh_profile(case / "system/blockMeshDict")
    planes, sets = [], []
    for station, frame in frames.items():
        z = float(frame.z_m.iloc[0])
        points = "\n".join(f"({r.x_m:.9g} {r.y_m:.9g} {r.z_m:.9g})" for r in frame.itertuples())
        planes.append(f"""plane{station}
        {{
            type cuttingPlane;
            planeType pointAndNormal;
            pointAndNormalDict {{ basePoint (0 0 {z:.9g}); normalVector (0 0 1); }}
            interpolate true;
        }}""")
        sets.append(f"""station{station}
        {{
            type cloud;
            axis xyz;
            points ({points});
        }}""")
    dictionary = """FoamFile { version 2.0; format ascii; class dictionary; object sliceExport; }
functions
{
    visualSlices
    {
        type surfaces;
        libs ("libsampling.so");
        writeControl writeTime;
        surfaceFormat raw;
        interpolationScheme cellPoint;
        fields (U);
        surfaces (PLANES);
    }
    comparisonPoints
    {
        type sets;
        libs ("libsampling.so");
        writeControl writeTime;
        setFormat raw;
        interpolationScheme cell;
        fields (U);
        sets (SETS);
    }
}
""".replace("PLANES", "\n".join(planes)).replace("SETS", "\n".join(sets))
    output.mkdir(parents=True)
    config = output / "sliceExportDict"
    config.write_text(dictionary)
    command = ["simpleFoam", "-case", str(case), "-postProcess", "-dict", str(config),
               "-time", args.time]
    shell = f"source {shlex.quote(str(args.foam_bashrc))}; exec {shlex.join(command)}"
    with (output / "log.sliceExport").open("w") as log:
        subprocess.run(["bash", "-lc", shell], stdout=log, stderr=subprocess.STDOUT, check=True, cwd=case)
    rows, surfaces = [], {}
    for station, frame in frames.items():
        point_path = case / f"postProcessing/comparisonPoints/{args.time}/station{station}_U.xy"
        if not point_path.exists():
            candidates = list((case / f"postProcessing/comparisonPoints/{args.time}").glob(f"station{station}_U.*"))
            if len(candidates) != 1:
                raise ValueError(f"Cannot identify sampled sensor file for station {station}")
            point_path = candidates[0]
        sampled = align_samples(frame[["x_m", "y_m", "z_m"]], np.loadtxt(point_path))
        frame = frame.copy()
        frame["sensor_id"] = frame.source_row + 1
        frame["cfd_speed_mps"] = np.linalg.norm(sampled[:, 3:6], axis=1)
        frame["delta_mps"] = frame.cfd_speed_mps - frame.speed_mps
        frame["floor_y_m"] = np.interp(frame.z_m, zs, floors)
        frame["local_height_m"] = frame.y_m - frame.floor_y_m
        frame["boundary_matched_run"] = station == 10
        rows.append(frame)
        surface_path = case / f"postProcessing/visualSlices/{args.time}/U_plane{station}.raw"
        surface = np.loadtxt(surface_path)
        if surface.ndim != 2 or surface.shape[1] != 6 or not np.isfinite(surface).all():
            raise ValueError(f"Unexpected slice columns at {surface_path}")
        surfaces[station] = surface
        np.savetxt(output / f"cfd_slice_{station}ft.csv", surface, delimiter=",",
                   header="x_m,y_m,z_m,Ux_mps,Uy_mps,Uz_mps", comments="")
    observations = pd.concat(rows, ignore_index=True)
    observations.to_csv(output / "sensor_deltas.csv", index=False)
    summary = []
    for station, frame in observations.groupby("station_ft"):
        summary.append(dict(station_ft=int(station), sensors=len(frame),
                            boundary_matched_run=bool(station == 10),
                            **regression_metrics(frame.speed_mps, frame.cfd_speed_mps)))
    pd.DataFrame(summary).to_csv(output / "station_metrics.csv", index=False)
    # Check the matched station against the independently saved solver probe comparison.
    previous = case / "data/processed/cfd_vs_experiment.csv"
    if previous.exists():
        reference = pd.read_csv(previous)
        current = observations[observations.station_ft == 10]
        np.testing.assert_allclose(current.cfd_speed_mps, reference.cfd_speed_mps,
                                   rtol=1e-6, atol=1e-8)

    plt.rcParams.update({"font.size": 10, "axes.spines.top": False,
                         "axes.spines.right": False, "savefig.facecolor": "white"})
    def save(fig, name):
        fig.savefig(output / f"{name}.png", dpi=200, bbox_inches="tight")
        fig.savefig(output / f"{name}.pdf", bbox_inches="tight")
        plt.close(fig)

    matched = observations[observations.station_ft == 10]
    z = float(matched.z_m.iloc[0])
    floor, ceiling = np.interp(z, zs, floors), np.interp(z, zs, ceilings)
    slice10 = surfaces[10]
    speed10 = np.linalg.norm(slice10[:, 3:], axis=1)
    vmax = max(speed10.max(), matched.speed_mps.max())
    norm = Normalize(0, vmax)
    delta_norm = TwoSlopeNorm(vmin=-abs(matched.delta_mps).max(), vcenter=0,
                              vmax=abs(matched.delta_mps).max())
    fig, axes = plt.subplots(1, 3, figsize=(11, 6), layout="constrained")
    for ax in axes:
        ax.set(xlim=(0, width), ylim=(floor, ceiling), xlabel="Width x (m)")
        ax.set_aspect("equal")
        ax.set_ylabel("Absolute elevation y (m)")
    axes[0].scatter(matched.x_m, matched.y_m, c=matched.speed_mps, norm=norm,
                    cmap="viridis", s=150, edgecolors="black", linewidths=.6)
    axes[0].set_title("Experiment: 12 measured means\nNo dense field is measured")
    field = axes[1].tricontourf(slice10[:, 0], slice10[:, 1], speed10,
                               levels=np.linspace(0, vmax, 24), norm=norm, cmap="viridis")
    axes[1].scatter(matched.x_m, matched.y_m, facecolors="none", edgecolors="white", s=90)
    axes[1].set_title("CFD speed magnitude |U|\nFinal iteration 237")
    delta = axes[2].scatter(matched.x_m, matched.y_m, c=matched.delta_mps,
                            norm=delta_norm, cmap="RdBu_r", s=150, edgecolors="black",
                            linewidths=.6)
    axes[2].set_title("Delta = CFD - experiment\nPositive = CFD overprediction")
    for ax in (axes[0], axes[2]):
        for r in matched.itertuples():
            ax.annotate(str(r.sensor_id), (r.x_m, r.y_m), xytext=(10, 0),
                        textcoords="offset points", fontsize=8)
    fig.colorbar(field, ax=list(axes[:2]), label="Speed (m/s)", shrink=.65)
    fig.colorbar(delta, ax=axes[2], label="Signed difference (m/s)", shrink=.65)
    fig.suptitle(f"S01-A-10-HN-1 | Source plane z = {z:.3f} m | Numerically converged baseline")
    save(fig, "matched_10ft_slice_and_delta")

    fig, axes = plt.subplots(1, 3, figsize=(13, 4.6), layout="constrained")
    for ax, (x, group) in zip(axes[:2], matched.groupby("x_m", sort=True)):
        group = group.sort_values("y_m")
        ax.plot(group.speed_mps, group.y_m, "o-", label="Measured mean", color="#276c9b")
        ax.plot(group.cfd_speed_mps, group.y_m, "s--", label="CFD |U|", color="#d35b32")
        ax.set(xlabel="Speed (m/s)", ylabel="Absolute elevation y (m)",
               title=f"Sensor column x = {x:.2f} m", xlim=(.08, .20))
        ax.grid(alpha=.2)
        ax.legend()
    axes[2].bar(matched.sensor_id, matched.delta_mps, color="#d35b32")
    axes[2].axhline(0, color="black", linewidth=.8)
    axes[2].set(xlabel="Sensor ID", ylabel="CFD - experiment (m/s)", title="Signed sensor differences",
                xticks=matched.sensor_id)
    stats = regression_metrics(matched.speed_mps, matched.cfd_speed_mps)
    fig.suptitle(f"Matched 10 ft run | RMSE {stats['rmse']:.4f} m/s | Bias {stats['bias']:+.4f} m/s")
    save(fig, "matched_10ft_profiles_and_errors")

    all_vmax = max(np.linalg.norm(s[:, 3:], axis=1).max() for s in surfaces.values())
    norm_all = Normalize(0, all_vmax)
    fig, axes = plt.subplots(3, 3, figsize=(10, 12), layout="constrained")
    for ax, station in zip(axes.flat, STATIONS):
        surface = surfaces[station]
        frame = observations[observations.station_ft == station]
        z = float(frame.z_m.iloc[0])
        floor, ceiling = np.interp(z, zs, floors), np.interp(z, zs, ceilings)
        image = ax.tricontourf(surface[:, 0], surface[:, 1]-floor,
                              np.linalg.norm(surface[:, 3:], axis=1),
                              levels=np.linspace(0, all_vmax, 30), norm=norm_all, cmap="viridis")
        ax.scatter(frame.x_m, frame.local_height_m, facecolors="none", edgecolors="white", s=30)
        ax.set(xlim=(0, width), ylim=(0, ceiling-floor), xlabel="x (m)", ylabel="y - floor(z) (m)",
               title=f"{station} ft label | source z = {z:.2f} m")
        ax.set_aspect("equal")
    fig.colorbar(image, ax=list(axes.flat), label="CFD speed magnitude (m/s)", shrink=.65)
    fig.suptitle("Nine slices of the same CFD baseline\nOutlines: experimental locations; only the 10 ft run sets the inlet flow")
    save(fig, "cfd_nine_slices")

    maximum = abs(observations.delta_mps).max()
    norm_delta = TwoSlopeNorm(vmin=-maximum, vcenter=0, vmax=maximum)
    fig, axes = plt.subplots(3, 3, figsize=(10, 12), layout="constrained")
    for ax, station in zip(axes.flat, STATIONS):
        frame = observations[observations.station_ft == station]
        z = float(frame.z_m.iloc[0])
        floor, ceiling = np.interp(z, zs, floors), np.interp(z, zs, ceilings)
        delta = ax.scatter(frame.x_m, frame.local_height_m, c=frame.delta_mps, s=85,
                           cmap="RdBu_r", norm=norm_delta, edgecolors="#333", linewidths=.4)
        bias = float(frame.delta_mps.mean())
        ax.set(xlim=(0, width), ylim=(0, ceiling-floor), xlabel="x (m)", ylabel="y - floor(z) (m)",
               title=f"{station} ft | mean delta {bias:+.3f} m/s")
        ax.set_aspect("equal")
    fig.colorbar(delta, ax=list(axes.flat), label="CFD - replicate-1 measured mean (m/s)", shrink=.65)
    fig.suptitle("Sensor differences across nine planes — exploratory\nSingle CFD supply setting; other stations' HVAC conditions are not matched")
    save(fig, "nine_station_sensor_deltas")
    inputs = [case / args.time / "U", case / "system/blockMeshDict", case / "system/controlDict",
              case / "0/U", config] + [args.dataset / f"03-Averages/V-S01-A-{s}-HN-1.txt" for s in STATIONS]
    manifest = dict(time=args.time, case=str(case), matched_run="S01-A-10-HN-1",
                    speed="sqrt(Ux^2 + Uy^2 + Uz^2)", delta="CFD minus measured mean",
                    surface_interpolation="cellPoint", sensor_interpolation="cell",
                    coordinate_frame="source absolute metres; galleries subtract actual mesh floor only for display",
                    sha256={str(p): sha256(p.read_bytes()).hexdigest() for p in inputs},
                    source_code_sha256=sha256(Path(__file__).read_bytes()).hexdigest(),
                    limitations=["Only 10 ft inlet flow was selected from its matching run",
                                 "Single mesh, steady isothermal k-epsilon, full-face supply",
                                 "Known upper ceiling source discrepancy retained",
                                 "Convergence is not experimental validation",
                                 "Measured speeds are sparse scalar magnitudes, not vectors",
                                 "Cross-station runs and CFD do not share a time-resolved measurement window"])
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2)+"\n")
    print(pd.DataFrame(summary).to_string(index=False))
    print(f"Figures and exported data: {output}")


if __name__ == "__main__":
    main()
