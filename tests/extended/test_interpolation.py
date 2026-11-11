import numpy as np
import pytest
from jetbridge_ml.interpolation import nearest_neighbor
from jetbridge_ml.validation import regression_metrics




def test_rmse_mae_and_signed_bias():
    result = regression_metrics([1., 2.], [2., 2.])
    assert result['rmse'] == pytest.approx(2**-0.5)
    assert result['mae'] == pytest.approx(0.5)
    assert result['bias'] == pytest.approx(0.5)


def test_bad_input_is_rejected():
    with pytest.raises(ValueError):
        nearest_neighbor([[0., 0.]], [1.], [[float('nan'), 0.]])
