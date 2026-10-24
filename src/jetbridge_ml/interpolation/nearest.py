"""Simple nearest-neighbour baseline for spatial air-speed predictions."""
import numpy as np
from scipy.spatial import cKDTree


def nearest_neighbor(
    train_locations: np.ndarray,
    train_values: np.ndarray,
    query_locations: np.ndarray,
) -> np.ndarray:
    """Predict scalar values at query points using the nearest observation.

    Parameters
    ----------
    train_locations : numpy.ndarray
        Coordinates of shape (n, d).
    train_values : numpy.ndarray
        Measured scalar values of shape (n,).
    query_locations : numpy.ndarray
        Locations of shape (m, d).

    Returns
    -------
    numpy.ndarray
        Nearest training value for each query, with shape (m,).
    """
    x = np.asarray(train_locations, dtype=float)
    y = np.asarray(train_values, dtype=float).reshape(-1)
    q = np.asarray(query_locations, dtype=float)
    if x.ndim != 2 or q.ndim != 2 or x.shape[1] != q.shape[1]:
        raise ValueError('Coordinates must be (n, d) and (m, d) with same d')
    if x.shape[0] == 0 or x.shape[0] != len(y):
        raise ValueError('Every nonempty training coordinate needs one value')
    if not all(np.isfinite(arr).all() for arr in (x, y, q)):
        raise ValueError('Arrays must contain finite values')
    _, idx = cKDTree(x).query(q, k=1)
    return y[idx]
