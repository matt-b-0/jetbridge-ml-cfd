"""Numerical, station-isolation and artifact checks for the CFD/SVR benchmark."""
import joblib
import numpy as np
import pandas as pd
import pytest
from jetbridge_ml.interpolation.spatial import predict_spatial
from jetbridge_ml.machine_learning.svr import fit_svr, grouped_svr_search, station_weights
from jetbridge_ml.virtual_benchmark import training_partition, _score


@pytest.mark.parametrize("method",["linear","rbf"])
def test_3d_interpolation_reproduces_affine_field(method):
    x=np.array([[i,j,k] for i in (0.,1.) for j in (0.,1.) for k in (0.,1.)])
    q=np.array([[.2,.3,.4],[.7,.8,.9]])
    values=.1+.02*x[:,0]-.01*x[:,1]+.03*x[:,2]
    np.testing.assert_allclose(predict_spatial(method,x,values,q),
                               .1+.02*q[:,0]-.01*q[:,1]+.03*q[:,2],atol=1e-12)


def test_3d_linear_marks_extrapolation_and_rejects_flat_input():
    x=np.array([[0.,0.,0.],[1,0,0],[0,1,0],[0,0,1]])
    assert np.isnan(predict_spatial("linear",x,np.ones(4),[[2,2,2]])[0])
    with pytest.raises(ValueError,match="span"):
        predict_spatial("rbf",x*np.array([1,1,0]),np.ones(4),[[.1,.1,0]])


def sample_training():
    groups=np.repeat([10,22,34],4)
    x=np.column_stack([np.tile([0.,1.,0.,1.],3),np.tile([0.,0.,1.,1.],3),groups.astype(float)])
    y=.1+.01*x[:,0]+.02*x[:,1]+.0005*x[:,2]
    return x,y,groups


def test_station_weights_have_equal_totals():
    groups=np.array([10,10,22,22,22,22])
    weights=station_weights(groups)
    assert weights.mean()==pytest.approx(1)
    assert weights[groups==10].sum()==pytest.approx(weights[groups==22].sum())


def test_grouped_scaling_excludes_validation_station_and_model_reloads(tmp_path):
    x,y,groups=sample_training()
    model,params,summary,audit=grouped_svr_search(x,y,groups,dict(C=[.1,1],gamma=[.2],epsilon=[.002]))
    assert len(summary)==2
    for row in audit.itertuples():
        assert str(row.heldout_station) not in row.training_stations.split(";")
        np.testing.assert_allclose(np.array(row.scaler_mean.split(";"),float),x[groups!=row.heldout_station].mean(axis=0))
    assert model.named_steps["svr"].fit_status_==0
    path=tmp_path/"svr.joblib"
    joblib.dump(model,path)
    np.testing.assert_array_equal(model.predict(x),joblib.load(path).predict(x))


def test_unseen_sparse_targets_do_not_enter_training_partition():
    frame=pd.DataFrame(dict(x_m=[.3,.4,.5,.6],height_m=[1.,1.,1.,1.],z_m=[3.,5.,7.,9.],
                            station_ft=[10,22,34,16],speed_mps=[.1,.2,.3,.4]))
    first=training_partition(frame,(10,22,34),(16,))
    frame.loc[3,"speed_mps"]=10000.
    second=training_partition(frame,(10,22,34),(16,))
    pd.testing.assert_frame_equal(first,second)
    with pytest.raises(ValueError,match="overlap"):
        training_partition(frame,(10,16),(16,))


def test_common_support_and_negative_predictions_are_reported():
    dense=pd.DataFrame(dict(station_ft=[16]*3,speed_mps=[.1,.2,.3]))
    pred={"nearest":np.array([.1,.2,.2]),"linear":np.array([.1,.2,np.nan]),"svr":np.array([.1,.2,-.1])}
    metrics=_score(dense,pred,np.array([True,True,False]),np.array([True,True,False]))
    common=metrics[metrics.subset=="common_hull"]
    assert common.n_predicted.tolist()==[2,2,2]
    assert common.rmse.tolist()==pytest.approx([0,0,0])
    linear=metrics[(metrics.method=="linear")&(metrics.subset=="outside_hull")].iloc[0]
    assert linear.n_requested==1 and linear.n_predicted==0
    svr=metrics[(metrics.method=="svr")&(metrics.subset=="outside_hull")].iloc[0]
    assert svr.negative_predictions==1


def test_iteration_budget_warning_is_not_called_an_epoch():
    x,y,groups=sample_training()
    model,warning=fit_svr(x,y,groups,dict(C=10,gamma=.2,epsilon=.0001),max_iter=1)
    assert warning and model.named_steps["svr"].fit_status_!=0
    assert model.named_steps["svr"].n_iter_==1
