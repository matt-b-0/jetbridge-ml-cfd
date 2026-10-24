"""Geometry-only noise sensitivity for fixed linear-in-data interpolators."""
import numpy as np
from scipy.spatial import Delaunay

from .plane import predict_plane


def interpolation_noise_gain(method, locations, queries):
    """Compute worst-case absolute amplification of bounded input perturbations.

    Parameters
    ----------
    method : str
        nearest, linear, or fixed zero-smoothing thin-plate-spline rbf.
    locations, queries : array-like
        Training and query x/y metre coordinates.

    Returns
    -------
    tuple
        Per-query infinity-norm gain sum(abs(weights)), the weight matrix,
        and training-hull membership. Linear unsupported queries remain NaN.
        Each query's worst case may require a different noise vector.
    """
    x,q=np.asarray(locations,float),np.asarray(queries,float)
    weights=np.column_stack([predict_plane(method,x,basis,q) for basis in np.eye(len(x))])
    gain=np.sum(abs(weights),axis=1)
    inside=Delaunay(x).find_simplex(q,tol=1e-10)>=0
    return gain,weights,inside
