"""Read the processed 12-probe CSV provided with the starter CFD case."""
from pathlib import Path

import numpy as np
import pandas as pd


def load_sensor_speed_csv(path: str | Path) -> tuple[np.ndarray, np.ndarray]:
    """Load spatial coordinates and air-speed magnitudes from a processed file.

    Parameters
    ----------
    path : str or Path
        CSV containing x_m, y_m, z_m and speed_m_per_s columns.

    Returns
    -------
    coordinates : numpy.ndarray
        Array of shape (n, 3), in metres, ordered x/y/z.
    speeds : numpy.ndarray
        Positive or zero scalar speeds of shape (n,), in m/s.

    Raises
    ------
    ValueError
        If measurements are missing, non-finite or physically negative.

    Notes
    -----
    These are scalar speeds, not the normal velocity component needed for a
    signed area-flux integral. This reader is for the processed demonstration
    CSV; the general FAA raw-file parser is a separate upcoming task.
    """
    frame = pd.read_csv(path)
    required = ['x_m', 'y_m', 'z_m', 'speed_m_per_s']
    missing = [key for key in required if key not in frame]
    if missing:
        raise ValueError(f'Missing required columns: {missing}')
    numeric = frame[required].apply(pd.to_numeric, errors='coerce').to_numpy(float)
    if numeric.shape[0] == 0 or not np.isfinite(numeric).all():
        raise ValueError('Sensor input must contain finite numeric measurements')
    coords, speeds = numeric[:, :3], numeric[:, 3]
    if np.any(speeds < 0):
        raise ValueError('Speeds must be nonnegative')
    return coords, speeds
