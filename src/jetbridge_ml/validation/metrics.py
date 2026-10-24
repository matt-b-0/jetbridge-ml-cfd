"""Metrics for out-of-sample scalar prediction."""
import numpy as np


def regression_metrics(actual: np.ndarray, predicted: np.ndarray) -> dict[str, float]:
    """Return RMSE, MAE and signed mean prediction bias in input units.

    Parameters
    ----------
    actual : numpy.ndarray
        Held-out reference observations, shape (n,).
    predicted : numpy.ndarray
        Predictions at identical locations, shape (n,).

    Returns
    -------
    dict of str to float
        ``rmse``, ``mae`` and ``bias`` (predicted minus actual).
    """
    a = np.asarray(actual, dtype=float).reshape(-1)
    p = np.asarray(predicted, dtype=float).reshape(-1)
    if a.size == 0 or a.shape != p.shape or not np.isfinite(a).all() or not np.isfinite(p).all():
        raise ValueError('actual and predicted must be equal-size finite nonempty arrays')
    err = p-a
    return {
        'rmse': float(np.sqrt(np.mean(err**2))),
        'mae': float(np.mean(np.abs(err))),
        'bias': float(np.mean(err)),
    }
