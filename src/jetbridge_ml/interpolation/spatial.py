"""Three-dimensional baselines for the virtual-sensor benchmark."""
import numpy as np
from scipy.interpolate import LinearNDInterpolator, RBFInterpolator

from .nearest import nearest_neighbor


def predict_spatial(method, locations, values, queries):
    """Predict scalar values from full-rank three-dimensional coordinates.

    Parameters
    ----------
    method : str
        nearest, linear, or fixed thin-plate-spline rbf.
    locations, queries : array-like
        Finite (n, 3) and (m, 3) coordinate arrays.
    values : array-like
        Finite training scalars, shape (n,).

    Returns
    -------
    numpy.ndarray
        Query predictions; unsupported linear extrapolation remains NaN.
    """
    x,q,y=np.asarray(locations,float),np.asarray(queries,float),np.asarray(values,float)
    if x.ndim!=2 or x.shape[1]!=3 or q.ndim!=2 or q.shape[1]!=3 or y.shape!=(len(x),):
        raise ValueError("Expected (n,3), (n,), (m,3) arrays")
    if len(x)<4 or not all(np.isfinite(a).all() for a in (x,q,y)):
        raise ValueError("Need at least four finite training points")
    if len(np.unique(x,axis=0))!=len(x) or np.linalg.matrix_rank(x-x.mean(axis=0))<3:
        raise ValueError("Training points must be unique and span three dimensions")
    if method=="nearest":
        return nearest_neighbor(x,y,q)
    if method=="linear":
        return np.asarray(LinearNDInterpolator(x,y,fill_value=np.nan)(q)).reshape(-1)
    if method=="rbf":
        return RBFInterpolator(x,y,kernel="thin_plate_spline",degree=1,smoothing=0)(q)
    raise ValueError(f"Unknown interpolation method: {method}")
