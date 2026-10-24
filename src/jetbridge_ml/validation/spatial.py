"""Deterministic withholding of entire coordinate groups."""
import numpy as np


def leave_location_out(locations):
    """Yield train/test indices with all rows at a location withheld together.

    Parameters
    ----------
    locations : array-like
        Finite coordinate array (n, d); equality is exact in source coordinates.

    Yields
    ------
    tuple of numpy.ndarray
        Training and test row indices, in sorted coordinate fold order.
    """
    x = np.asarray(locations, float)
    if x.ndim != 2 or len(x) < 2 or not np.isfinite(x).all():
        raise ValueError("Expected finite coordinates")
    unique, groups = np.unique(x, axis=0, return_inverse=True)
    if len(unique) < 2:
        raise ValueError("Need at least two distinct locations")
    for fold in range(len(unique)):
        yield np.flatnonzero(groups != fold), np.flatnonzero(groups == fold)
