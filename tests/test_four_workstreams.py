import csv
from pathlib import Path
import numpy as np
import pandas as pd
import pytest
from jetbridge_ml.data_processing.raw_speed import read_raw_speed
from jetbridge_ml.experimental_svr import evaluate_experimental_plane
from jetbridge_ml.machine_learning.selection import select_plane_svr
from jetbridge_ml.sensor_design_study import design_indices
from jetbridge_ml.cfd_interface.thermal_audit import read_probe_trace

GRID=dict(C=[.1],gamma=[.1],epsilon=[.002])


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


def test_inner_scaling_and_location_groups_exclude_validation():
    x=np.array([[0,0],[0,0],[1,0],[1,1],[0,1],[.5,.5]],float)
    y=.1+.01*x[:,0]
    _,_,_,audit=select_plane_svr(x,y,grid=GRID)
    for row in audit.itertuples():
        train=np.array(list(map(int,row.training_indices.split(';'))))
        val=np.array(list(map(int,row.validation_indices.split(';'))))
        np.testing.assert_allclose(list(map(float,row.scaler_mean.split(';'))),x[train].mean(axis=0))
        assert set(map(tuple,x[train])).isdisjoint(map(tuple,x[val]))


@pytest.mark.parametrize('placement',['interior','wall_aware','hybrid'])
@pytest.mark.parametrize('nx,ny',[(2,3),(2,6),(4,6),(6,8)])
def test_layout_unique_and_value_independent(placement,nx,ny):
    x,y=np.meshgrid((np.arange(32)+.5)/32,(np.arange(48)+.5)/48)
    points=np.column_stack([x.ravel(),y.ravel()])
    indices=design_indices(points,nx,ny,placement)
    assert len(indices)==nx*ny==len(set(indices))
    shifted=design_indices(points+[2,4],nx,ny,placement)
    np.testing.assert_array_equal(indices,shifted)


def raw_file(path,speed=-9999):
    rows=[]
    for label,value in [('X (in)',10),('Y (in)',20),('Z (in)',120),('Probe',0)]:
        rows.append([label]+[value]*12)
    rows.append(['']+['Time (sec)','V (m/s)','T (°C)','P (hPa)']*3)
    rows.append(['',1,speed,20,1000,1.1,.2,21,1000,1.2,.3,22,1000])
    with path.open('w',encoding='cp1252',newline='') as handle:
        csv.writer(handle).writerows(rows)


def test_raw_units_sentinel_and_asynchronous_timestamps(tmp_path):
    path=tmp_path/'raw.csv'; raw_file(path)
    frame=read_raw_speed(path)
    assert np.isnan(frame.speed_mps.iloc[0])
    np.testing.assert_allclose(frame.time_sec,[1,1.1,1.2])
    np.testing.assert_allclose(frame.raw_x_m,.254)
    np.testing.assert_allclose(frame.raw_local_height_m,.508)
    np.testing.assert_allclose(frame.raw_nominal_z_m,3.048)


def test_raw_negative_speed_rejected(tmp_path):
    path=tmp_path/'raw.csv'; raw_file(path,-.1)
    with pytest.raises(ValueError,match='Negative'):
        read_raw_speed(path)


def test_probe_restart_segments_sorted_and_deduplicated(tmp_path):
    for segment,data in [('0',[[0,294],[10,295]]),('10',[[10,295],[20,296]])]:
        directory=tmp_path/'postProcessing/sensors'/segment
        directory.mkdir(parents=True)
        np.savetxt(directory/'T',data)
    data=read_probe_trace(tmp_path)
    np.testing.assert_allclose(data,[[0,294],[10,295],[20,296]])


def test_experimental_mixed_replicates_rejected():
    frame=pd.DataFrame(dict(run_id=['a','b'],x_m=[0,1],y_m=[0,1]))
    with pytest.raises(ValueError,match='One replicate'):
        evaluate_experimental_plane(frame,GRID)
