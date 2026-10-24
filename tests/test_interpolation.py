import numpy as np
import pytest
from jetbridge_ml.interpolation import nearest_neighbor
from jetbridge_ml.validation import regression_metrics


def test_nearest_neighbor_matches_known_locations():
    locations = np.array([[0.0, 0.0], [2.0, 0.0], [0.0, 2.0]])
    values = np.array([1.0, 4.0, 9.0])
    out = nearest_neighbor(locations, values, np.array([[0.1, 0.1], [1.8, 0.0]]))
    np.testing.assert_array_equal(out, [1.0, 4.0])


def test_rmse_mae_and_signed_bias():
    result = regression_metrics([1., 2.], [2., 2.])
    assert result['rmse'] == pytest.approx(2**-0.5)
    assert result['mae'] == pytest.approx(0.5)
    assert result['bias'] == pytest.approx(0.5)


def test_bad_input_is_rejected():
    with pytest.raises(ValueError):
        nearest_neighbor([[0., 0.]], [1.], [[float('nan'), 0.]])
