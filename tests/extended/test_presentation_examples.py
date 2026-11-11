"""Small independent checks that are practical to explain in a demonstration.

These extend the existing affine-field, support and nested-leakage tests.
They check numerical properties, not the physical validity of jet-bridge CFD.
"""

import numpy as np
import pytest

from jetbridge_ml.interpolation.plane import predict_plane
from jetbridge_ml.validation.metrics import regression_metrics




@pytest.mark.parametrize("method", ["nearest", "linear", "rbf"])
def test_sensor_row_order_does_not_change_predictions(method):
    """Reordering paired coordinates and values must preserve predictions."""
    sensors = np.array([[0.0, 0.0], [1.0, 0.0], [0.0, 1.0], [1.0, 1.0]])
    speeds = np.array([0.1, 0.2, 0.3, 0.4])
    queries = np.array([[0.12, 0.18], [0.83, 0.74]])
    order = np.array([2, 0, 3, 1])
    original = predict_plane(method, sensors, speeds, queries)
    reordered = predict_plane(method, sensors[order], speeds[order], queries)
    np.testing.assert_allclose(original, reordered, rtol=0.0, atol=1e-12)


def test_error_metrics_keep_speed_units_when_scaled():
    """Changing m/s to cm/s multiplies every error metric by one hundred."""
    actual = np.array([0.1, 0.2, 0.3])
    predicted = np.array([0.12, 0.18, 0.34])
    metres = regression_metrics(actual, predicted)
    centimetres = regression_metrics(100.0 * actual, 100.0 * predicted)
    for name in ("rmse", "mae", "bias"):
        assert centimetres[name] == pytest.approx(100.0 * metres[name])


def test_unsupported_predictions_are_not_silently_scored():
    """A missing prediction requires an explicit coverage decision."""
    with pytest.raises(ValueError, match="finite"):
        regression_metrics([0.1, 0.2], [0.1, np.nan])
