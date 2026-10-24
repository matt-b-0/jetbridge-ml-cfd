"""Check geometry-only interpolation sensitivity against direct predictions."""
import numpy as np
import pytest
from jetbridge_ml.interpolation.plane import predict_plane
from jetbridge_ml.interpolation.sensitivity import interpolation_noise_gain


@pytest.mark.parametrize("method",["nearest","linear","rbf"])
def test_noise_weights_reproduce_direct_predictions(method):
    x=np.array([[0.,0.],[0.,1.],[1.,0.],[1.,1.],[.5,.5]])
    q=np.array([[.2,.3],[.7,.8],[-.2,.5]])
    values=np.array([.1,.2,.4,.8,.5])
    gain,weights,_=interpolation_noise_gain(method,x,q)
    actual=predict_plane(method,x,values,q)
    valid=np.isfinite(gain)
    np.testing.assert_allclose(weights[valid]@values,actual[valid],atol=1e-12)


@pytest.mark.parametrize("method",["nearest","linear"])
def test_supported_convex_weights_do_not_amplify_bounded_noise(method):
    x=np.array([[0.,0.],[0.,1.],[1.,0.],[1.,1.]])
    gain,_,inside=interpolation_noise_gain(method,x,[[.2,.3],[.7,.8]])
    assert inside.all()
    np.testing.assert_allclose(gain,[1,1],atol=1e-12)


def test_rbf_worst_case_noise_bound_is_attained_at_selected_query():
    x=np.array([[0.,0.],[0.,1.],[1.,0.],[1.,1.],[.5,.5]])
    query=np.array([[-.3,.2]])
    gain,weights,_=interpolation_noise_gain("rbf",x,query)
    base=np.array([.1,.2,.4,.8,.5])
    epsilon=.001
    perturbation=epsilon*np.sign(weights[0])
    delta=predict_plane("rbf",x,base+perturbation,query)-predict_plane("rbf",x,base,query)
    assert delta[0]==pytest.approx(epsilon*gain[0],abs=1e-12)
