import numpy as np
import pytest
from sklearn.preprocessing import StandardScaler
from jetbridge_ml.controlled_performance import fit_predictor
from jetbridge_ml.interpolation.plane import predict_plane
from jetbridge_ml.machine_learning.svr import fit_svr

X=np.array([[0.,0.],[2.,0.],[0.,5.],[2.,5.],[.8,2.]])
Y=np.array([.1,.2,.15,.3,.18])
Q=np.array([[.2,.7],[1.5,3.],[3.,8.]])
PARAMS=dict(C=1.,gamma=.1,epsilon=.002)

@pytest.mark.parametrize('method',['nearest','linear','rbf'])
def test_timed_wrapper_preserves_existing_scaled_prediction(method):
    scale=StandardScaler().fit(X)
    expected=predict_plane(method,scale.transform(X),Y,scale.transform(Q))
    np.testing.assert_allclose(fit_predictor(method,X,Y,PARAMS)(Q),expected,equal_nan=True)

def test_mean_and_svr_match_reference_training():
    np.testing.assert_allclose(fit_predictor('mean',X,Y,PARAMS)(Q),np.mean(Y))
    model,warning=fit_svr(X,Y,np.arange(len(X)),PARAMS)
    assert not warning
    np.testing.assert_allclose(fit_predictor('svr',X,Y,PARAMS)(Q),model.predict(Q))

def test_unknown_method_rejected():
    with pytest.raises(ValueError,match='Unknown model'):
        fit_predictor('not-a-model',X,Y,PARAMS)
