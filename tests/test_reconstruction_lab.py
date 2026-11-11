"""Numerical and leakage checks for the reconstruction comparison workflow."""
from pathlib import Path
import numpy as np
import pytest
from scipy.spatial import Delaunay
from jetbridge_ml.validation import reconstruction_lab as lab
from jetbridge_ml.gui.config import RunSpec, available_runs
from jetbridge_ml.gui.guidance import guide_text

ROOT=Path(__file__).resolve().parents[1]


def locations():
    xx,yy=np.meshgrid(np.linspace(0,1,3),np.linspace(0,2,5))
    return np.c_[xx.ravel(),yy.ravel()]


@pytest.mark.parametrize('method',['linear','rbf'])
def test_affine_field_is_reproduced_inside_support(method):
    x=locations();y=.1+.03*x[:,0]+.04*x[:,1]
    q=np.array([[.23,.32],[.61,1.43],[.77,.81]])
    values,seconds,_=lab.fit_predict(method,x,y,q)
    np.testing.assert_allclose(values,.1+.03*q[:,0]+.04*q[:,1],atol=1e-12)
    assert seconds>0


def test_designs_are_nested_disjoint_and_preserve_common_support():
    x=locations()
    designs,held,q=lab.sensor_designs(x)
    again,held_again,_=lab.sensor_designs(x)
    np.testing.assert_array_equal(held,held_again)
    for repeat in range(3):
        previous=set()
        for d in [v for v in designs if v['repeat']==repeat]:
            assert previous.issubset(d['train'])
            assert not set(d['train']).intersection(held)
            assert (Delaunay(x[d['train']]).find_simplex(q)>=0).all()
            previous=set(d['train'])
    for a,b in zip(designs,again):np.testing.assert_array_equal(a['train'],b['train'])


def test_heldout_targets_never_enter_noise_fits(monkeypatch):
    x=locations();y=.2+x[:,0]*.01+x[:,1]*.02
    _,held,_=lab.sensor_designs(x)
    calls=[]
    def fit(method,train_x,train_y,query):
        calls.append((method,train_x.copy(),train_y.copy()))
        assert not any(np.array_equal(a,b) for a in train_x for b in x[held])
        return np.full(len(query),train_y.mean()),.01,{}
    monkeypatch.setattr(lab,'fit_predict',fit)
    first,_,_=lab.sensitivity_study(x,y)
    before=[(m,a.copy(),b.copy()) for m,a,b in calls];calls.clear()
    changed=y.copy();changed[held]+=10
    second,_,_=lab.sensitivity_study(x,changed)
    for (m,a,b),(n,c,d) in zip(before,calls):
        assert m==n;np.testing.assert_array_equal(a,c);np.testing.assert_array_equal(b,d)
    assert second.rmse.mean()>first.rmse.mean()+9
    assert set(first.noise_fraction)=={0,.02,.05,.1}


def test_virtual_design_rejects_training_test_overlap():
    x=locations()
    with pytest.raises(ValueError,match='disjoint'):lab.sensor_designs(x,x[:2])


def test_lab_configuration_and_explanation():
    assert len(available_runs(ROOT,'lab'))==36
    assert available_runs(ROOT,'lab_cfd')==['S01-A-16-HN-1']
    RunSpec(kind='lab').validate(ROOT)
    with pytest.raises(ValueError,match='all methods'):RunSpec(kind='lab',method='svr').validate(ROOT)
    assert 'instrument uncertainty' in guide_text('lab','id','all','standard')
    assert 'archived' in guide_text('lab_cfd','id','all','standard')
