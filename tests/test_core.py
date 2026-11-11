"""Six core checks for the presentation and the default pytest run.

Five test functions produce six cases: the affine-field test runs once for
linear interpolation and once for RBF. Optional regression checks are in
tests/extended. These checks do not certify physical CFD accuracy.
"""

import numpy as np
import pandas as pd
import pytest

from jetbridge_ml.experimental_svr import evaluate_experimental_plane
from jetbridge_ml.interpolation import nearest_neighbor
from jetbridge_ml.interpolation.plane import predict_plane
from jetbridge_ml.validation.metrics import regression_metrics

# One candidate keeps the leakage check quick; research uses the full grid.
GRID=dict(C=[.1],gamma=[.1],epsilon=[.002])



def test_nearest_neighbor_matches_known_locations():
    locations = np.array([[0.0, 0.0], [2.0, 0.0], [0.0, 2.0]])
    values = np.array([1.0, 4.0, 9.0])
    out = nearest_neighbor(locations, values, np.array([[0.1, 0.1], [1.8, 0.0]]))
    np.testing.assert_array_equal(out, [1.0, 4.0])


def test_zero_bias_can_hide_large_local_errors():
    """Opposite signed errors cancel in bias, but not in MAE or RMSE."""
    actual = np.array([0.1, 0.3])
    predicted = np.array([0.3, 0.1])
    metrics = regression_metrics(actual, predicted)
    assert metrics["bias"] == pytest.approx(0.0, abs=1e-12)
    assert metrics["mae"] == pytest.approx(0.2)
    assert metrics["rmse"] == pytest.approx(0.2)


@pytest.mark.parametrize("method", ["linear", "rbf"])
def test_affine_field_reproduction(method):
    x = np.array([[0, 0], [1, 0], [0, 1], [1, 1], [.5, .5]])
    q = np.array([[.2, .3], [.6, .8]])
    result = predict_plane(method, x, 2 + 3*x[:, 0] - x[:, 1], q)
    np.testing.assert_allclose(result, 2 + 3*q[:, 0] - q[:, 1], atol=1e-12)


def test_linear_extrapolation_is_explicit():
    x = np.array([[0, 0], [1, 0], [0, 1]])
    result = predict_plane("linear", x, [1, 1, 1], [[.2, .2], [2, 2]])
    assert result[0] == pytest.approx(1)
    assert np.isnan(result[1])


def test_nested_test_target_does_not_change_its_model():
    x,y=np.meshgrid([0.,.5,1.],[0.,.5,1.])
    frame=pd.DataFrame(dict(x_m=x.ravel(),y_m=y.ravel(),z_m=3.05,
                            speed_mps=.1+.02*x.ravel()+.01*y.ravel(),source_row=np.arange(9),run_id='one'))
    first,_,audit=evaluate_experimental_plane(frame,GRID)
    changed=frame.copy(); changed.loc[0,'speed_mps']=9.
    second,_,_=evaluate_experimental_plane(changed,GRID)
    a=first[(first.fold==0)&(first.method=='svr')].iloc[0]
    b=second[(second.fold==0)&(second.method=='svr')].iloc[0]
    assert a.prediction_mps==b.prediction_mps
    for item in audit[audit.outer_source_row==0].itertuples():
        assert '0' not in item.outer_training_source_rows.split(';')
        assert set(item.training_indices.split(';')).isdisjoint(item.validation_indices.split(';'))
