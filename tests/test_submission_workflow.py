import json
from pathlib import Path
import numpy as np
import pandas as pd
import pytest
from jetbridge_ml.experimental_svr import evaluate_experimental_plane
from jetbridge_ml.paired_analysis import paired_errors
from jetbridge_ml.run_analysis import gallery
from jetbridge_ml.cfd_interface.verification_study import prepare_case


def test_mean_baseline_excludes_outer_target():
    x,y=np.meshgrid([0.,.5,1.],[0.,.5,1.])
    values=np.arange(9)/100+.1
    frame=pd.DataFrame(dict(x_m=x.ravel(),y_m=y.ravel(),speed_mps=values,z_m=3.05,source_row=np.arange(9),run_id='one'))
    predictions,_,_=evaluate_experimental_plane(frame,dict(C=[.1],gamma=[.1],epsilon=[.002]))
    mean=predictions[(predictions.method=='mean')&(predictions.fold==0)].iloc[0]
    assert mean.prediction_mps==pytest.approx(values[1:].mean())
    assert '0' not in mean.train_rows.split(';')


def metrics():
    return pd.DataFrame([dict(run_id='S01-A-10-HN-1',method=m,subset='common_hull',n_requested=8,n_predicted=8,rmse=e)
                         for m,e in [('rbf',.01),('svr',.02)]])


def test_paired_sign_and_incomplete_coverage():
    frame=metrics()
    pairs=paired_errors(frame)
    assert pairs.rbf_minus_svr_mps.iloc[0]==pytest.approx(-.01)
    frame.loc[0,'n_predicted']=7
    with pytest.raises(ValueError,match='coverage'): paired_errors(frame)


def test_paired_missing_method_rejected():
    with pytest.raises(ValueError,match='both methods'): paired_errors(metrics().iloc[:1])


def test_gallery_excludes_raw_and_point_data(tmp_path):
    root=tmp_path/'analysis'; root.mkdir()
    (root/'SUMMARY.md').write_text('summary')
    (root/'pipeline_manifest.json').write_text('{}')
    directory=root/'experimental'; directory.mkdir()
    (directory/'summary.csv').write_text('small summary')
    (directory/'predictions.csv').write_text('must not publish')
    target=tmp_path/'gallery'
    gallery(root,target)
    assert (target/'experimental/summary.csv').exists()
    assert not (target/'experimental/predictions.csv').exists()
    with pytest.raises(ValueError,match='new'): gallery(root,target)


def test_isolated_case_scaling_and_preserved_geometry(tmp_path):
    repo=Path(__file__).resolve().parents[1]
    baseline=repo/'cfd/cases/empty_bridge_s01_a_10_hn_1'
    output=tmp_path/'flow'
    spec=prepare_case(baseline,output,'flow80')
    assert spec['cells']==141312
    assert 'endTime 600;' in (output/'system/controlDict').read_text()
    assert (output/'constant/transportProperties').read_bytes()==(baseline/'constant/transportProperties').read_bytes()
    import re
    pattern=r'volumetricFlowRate\s+constant\s+([\d.eE+-]+)'
    before=float(re.search(pattern,(baseline/'0/U').read_text())[1])
    after=float(re.search(pattern,(output/'0/U').read_text())[1])
    assert after==pytest.approx(before*.8)
    pattern=r'internalField\s+uniform\s+([\d.eE+-]+)'
    for field,power in [('k',2),('epsilon',3)]:
        before=float(re.search(pattern,(baseline/'0'/field).read_text())[1])
        after=float(re.search(pattern,(output/'0'/field).read_text())[1])
        assert after==pytest.approx(before*.8**power)
    coarse=tmp_path/'coarse'
    assert prepare_case(baseline,coarse,'coarse')['cells']==17664
