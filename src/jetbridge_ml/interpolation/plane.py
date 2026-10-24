"""Fixed, untuned two-dimensional interpolation baselines."""
import numpy as np
from scipy.interpolate import LinearNDInterpolator, RBFInterpolator

from .nearest import nearest_neighbor


def predict_plane(method: str, locations, values, queries) -> np.ndarray:
    """Predict scalar speeds using metre x/y coordinates.

    Parameters
    ----------
    method : str
        nearest, linear, or rbf (thin-plate spline, degree 1, no smoothing).
    locations, queries : array-like
        Finite arrays of shape (n, 2) and (m, 2).
    values : array-like
        Finite scalar training values, shape (n,).

    Returns
    -------
    numpy.ndarray
        Predictions; linear returns NaN outside the training convex hull.
        RBF may extrapolate or predict negative values; no clipping is applied.
    """
    x, q = np.asarray(locations, float), np.asarray(queries, float)
    y = np.asarray(values, float)
    if (x.ndim != 2 or x.shape[1] != 2 or q.ndim != 2 or q.shape[1] != 2
            or y.shape != (len(x),) or len(x) < 3):
        raise ValueError("Expected at least three training points in two dimensions")
    if not all(np.isfinite(a).all() for a in (x, y, q)):
        raise ValueError("Inputs must be finite")
    if len(np.unique(x, axis=0)) != len(x):
        raise ValueError("Duplicate training coordinates")
    if np.linalg.matrix_rank(x - x.mean(axis=0)) < 2:
        raise ValueError("Training coordinates must span a plane")
    if method == "nearest":
        return nearest_neighbor(x, y, q)
    if method == "linear":
        return np.asarray(LinearNDInterpolator(x, y, fill_value=np.nan)(q)).reshape(-1)
    if method == "rbf":
        return RBFInterpolator(x, y, kernel="thin_plate_spline", degree=1, smoothing=0)(q)
    raise ValueError(f"Unknown method: {method}")
