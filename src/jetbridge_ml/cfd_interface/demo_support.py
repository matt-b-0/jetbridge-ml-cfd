"""Fresh OpenFOAM exports used by the demonstration orchestrator."""
from pathlib import Path
import numpy as np
import pandas as pd
from jetbridge_ml.data_processing.faa import read_speed_average
from .plot_comparison import mesh_profile, STATIONS
from .report_figures import sample_grid


def export_report_grid(case, dataset, output, saved_time):
    """Sample the fresh isothermal solve on the archived report's query grid.

    Parameters
    ----------
    case, dataset, output : pathlib.Path
        Solved case, included experimental subset and new output directory.
    saved_time : str
        Saved converged SIMPLE iterate, not physical time.

    Returns
    -------
    pathlib.Path
        Fresh table with physical coordinates, U components and scalar speed.
    """
    case, dataset, output = map(Path, (case, dataset, output))
    output.mkdir(parents=True, exist_ok=False)
    width, zs, floors, tops = mesh_profile(case / 'system/blockMeshDict')
    nx, ny, nz = 32, 48, 181
    xs = (np.arange(nx) + .5) * width / nx
    eta = (np.arange(ny) + .5) / ny
    planes = []
    for station in STATIONS:
        source = read_speed_average(dataset / f'03-Averages/V-S01-A-{station}-HN-1.txt')
        z = float(source.z_m.iloc[0])
        floor = np.interp(z, zs, floors)
        height = np.interp(z, zs, tops) - floor
        x, y = np.meshgrid(xs, floor + eta * height)
        planes.append(np.column_stack([x.ravel(), y.ravel(), np.full(x.size, z)]))
    sidez = (np.arange(nz) + .5) * zs[-1] / nz
    sy = np.interp(sidez, zs, floors)[None, :] + eta[:, None] * np.interp(sidez, zs, tops - floors)[None, :]
    sz = np.broadcast_to(sidez, sy.shape)
    side = np.column_stack([np.full(sy.size, width / 2), sy.ravel(), sz.ravel()])
    points = np.vstack([*planes, side])
    fields = sample_grid(case, saved_time, output, points, False)
    table = pd.DataFrame(points, columns=['x_m', 'y_m', 'z_m'])
    table[['Ux_mps', 'Uy_mps', 'Uz_mps']] = fields['U']
    table['speed_mps'] = np.linalg.norm(fields['U'], axis=1)
    count = nx * ny * len(STATIONS)
    table['region'] = ['cross_section'] * count + ['longitudinal_midplane'] * len(side)
    target = output / 'sampled_iso.csv'
    table.to_csv(target, index=False)
    return target
