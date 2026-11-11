"""Auditable experiments behind the visual reconstruction lab."""
from time import perf_counter
import numpy as np
import pandas as pd
from scipy.spatial import ConvexHull, Delaunay
from sklearn.preprocessing import StandardScaler
from jetbridge_ml.interpolation.plane import predict_plane
from jetbridge_ml.machine_learning.selection import select_plane_svr

METHODS = ('nearest', 'linear', 'rbf', 'svr')
LABELS = {'nearest': 'Nearest', 'linear': 'Linear', 'rbf': 'Thin-plate RBF', 'svr': 'SVR'}
COLORS = {'nearest': '#64748b', 'linear': '#0284c7', 'rbf': '#0d9488', 'svr': '#8b5cf6'}


def fit_predict(method, x, y, query):
    """Fit a method using training data only and predict supplied coordinates.

    Parameters
    ----------
    method : str
        One of nearest, linear, rbf, svr.
    x, y, query : numpy.ndarray
        Training coordinates/targets and prediction coordinates, in metres/m/s.

    Returns
    -------
    tuple
        Predictions, elapsed fit-plus-predict seconds, and SVR search records.
    """
    start = perf_counter()
    if method == 'svr':
        model, params, search, audit = select_plane_svr(x, y)
        result = model.predict(query)
        evidence = dict(parameters=params, search=search.to_dict('records'),
                        inner_audit=audit.to_dict('records'))
    else:
        scaler = StandardScaler().fit(x)
        result = predict_plane(method, scaler.transform(x), y, scaler.transform(query))
        evidence = {}
    return np.asarray(result), perf_counter() - start, evidence


def sensor_designs(x, test_x=None, repeats=3, seed=3001):
    """Create nested designs with fixed hull anchors and disjoint test points.

    Parameters
    ----------
    x : numpy.ndarray
        Unique finite planar candidate sensor coordinates.
    test_x : numpy.ndarray, optional
        Independent CFD test grid. None selects held-out interior sensors.
    repeats, seed : int
        Number of deterministic nested designs and random generator seed.

    Returns
    -------
    tuple
        Designs, held-out indices (experimental only), and test coordinates.
    """
    x = np.asarray(x, float)
    if len(np.unique(x, axis=0)) != len(x) or not np.isfinite(x).all():
        raise ValueError('Unique finite sensor coordinates required')
    anchors = np.sort(ConvexHull(x).vertices)
    interior = np.setdiff1d(np.arange(len(x)), anchors)
    rng = np.random.default_rng(seed)
    if test_x is None:
        if len(interior) < 3:
            raise ValueError('At least three non-hull sensors needed for held-out experiments')
        test = np.sort(rng.choice(interior, min(max(2, len(x)//4), len(interior)-1), replace=False))
        test_x = x[test]
    else:
        test = np.array([], dtype=int)
        if np.any(np.all(x[:, None, :] == np.asarray(test_x)[None, :, :], axis=2)):
            raise ValueError('Virtual training and test coordinates must be disjoint')
    pool = np.setdiff1d(np.arange(len(x)), test)
    base = max(6, len(anchors))
    counts = sorted(set([base, min(len(pool), 8), min(len(pool), 12),
                         min(len(pool), 24), min(len(pool), 48)]))
    counts = [n for n in counts if len(anchors) <= n <= len(pool)]
    if not counts:
        raise ValueError('Insufficient retained sensors')
    designs = []
    for repeat in range(repeats):
        order = rng.permutation(np.setdiff1d(pool, anchors))
        for count in counts:
            train = np.r_[anchors, order[:count-len(anchors)]]
            designs.append(dict(repeat=repeat, count=count, train=train))
    return designs, test, np.asarray(test_x)


def sensitivity_study(x, y, test_x=None, test_y=None, check_cancel=lambda: None):
    """Evaluate paired nested sensor designs and synthetic training-only noise.

    Parameters
    ----------
    x, y : numpy.ndarray
        Candidate training locations and scalar speeds.
    test_x, test_y : numpy.ndarray, optional
        Independent dense CFD evaluation data, otherwise held-out sensors.
    check_cancel : callable
        Cooperative cancellation check, called between fits.

    Returns
    -------
    tuple
        Raw density/noise/timing records, split audit, and search evidence.
    """
    x, y = np.asarray(x, float), np.asarray(y, float)
    designs, held, query = sensor_designs(x, test_x)
    truth = y[held] if test_x is None else np.asarray(test_y, float)
    support = Delaunay(x[designs[0]['train']]).find_simplex(query, tol=1e-10) >= 0
    if not support.any():
        raise ValueError('No common supported evaluation locations')
    rows, splits, searches = [], [], []
    max_count = max(d['count'] for d in designs)
    for design in designs:
        train = design['train']; repeat = design['repeat']; count = design['count']
        splits.append(dict(repeat=repeat, sensor_count=count, training_indices=train.tolist(),
                           heldout_indices=held.tolist(), common_supported=int(support.sum()),
                           requested_targets=len(query)))
        levels = (0., .02, .05, .10) if count == max_count else (0.,)
        for noise in levels:
            rng = np.random.default_rng(7100 + repeat)
            sigma = noise * float(np.sqrt(np.mean(y[train]**2)))
            perturbed = y[train] + rng.normal(0, sigma, len(train))
            for method in METHODS:
                check_cancel()
                values, elapsed, evidence = fit_predict(method, x[train], perturbed, query)
                error = values[support]-truth[support]
                if not np.isfinite(error).all():
                    raise ValueError('A method failed on the common supported targets')
                rows.append(dict(method=method, repeat=repeat, sensor_count=count,
                                 noise_fraction=noise, noise_sigma_mps=sigma,
                                 rmse=float(np.sqrt(np.mean(error**2))),
                                 mae=float(np.mean(np.abs(error))), seconds=elapsed,
                                 common_supported=int(support.sum()), requested_targets=len(query),
                                 negative_predictions=int(np.sum(values < 0))))
                if evidence:
                    searches.append(dict(repeat=repeat, sensor_count=count, noise_fraction=noise, **evidence))
    return pd.DataFrame(rows), splits, searches
