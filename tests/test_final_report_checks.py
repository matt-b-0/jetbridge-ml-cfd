import numpy as np
import pandas as pd
from jetbridge_ml.final_report_checks import extended_outer_prediction


def test_extended_search_excludes_outer_target_even_if_it_changes():
    frame=pd.DataFrame(dict(x_m=[0.,1.,0.,1.,.3,.8],y_m=[0.,0.,2.,2.,.7,1.5],speed_mps=[.1,.2,.15,.25,.17,.22],source_row=[10,11,12,13,14,15]))
    value,params,_,audit=extended_outer_prediction(frame,2)
    changed=frame.copy();changed.loc[2,'speed_mps']=99.
    other,other_params,_,_=extended_outer_prediction(changed,2)
    assert value==other and params==other_params
    assert all('12' not in rows.split(';') for rows in audit.outer_training_source_rows)
    for row in audit.itertuples():
        train=list(map(int,row.training_indices.split(';')))
        valid=list(map(int,row.validation_indices.split(';')))
        assert not set(train)&set(valid)
        expected=frame.drop(index=2).iloc[train][['x_m','y_m']].mean().to_numpy()
        np.testing.assert_allclose(list(map(float,row.scaler_mean.split(';'))),expected)
