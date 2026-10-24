"""Training-only selection for small two-dimensional speed reconstructions."""
import itertools
import numpy as np
import pandas as pd
from sklearn.model_selection import GroupKFold
from jetbridge_ml.machine_learning.svr import fit_svr

DEFAULT_GRID=dict(C=[.1,1.,10.],gamma=[.1,1.],epsilon=[.002,.01])


def select_plane_svr(x, y, groups=None, grid=None):
    """Tune an SVR using three grouped training-only folds.

    Parameters
    ----------
    x, y : array-like
        Finite training coordinates and speed targets; outer test is excluded.
    groups : array-like, optional
        Location group per row. Defaults to one unique group per coordinate.
    grid : dict, optional
        Predefined C/gamma/epsilon values, independent of outer test targets.

    Returns
    -------
    tuple
        Fitted model, selected parameters, search table and inner split audit.
    """
    x,y=np.asarray(x,float),np.asarray(y,float)
    if x.ndim!=2 or x.shape[1]!=2 or y.shape!=(len(x),) or not np.isfinite(x).all() or not np.isfinite(y).all():
        raise ValueError('Finite two-dimensional coordinates and scalar targets required')
    if groups is None:
        _,groups=np.unique(x,axis=0,return_inverse=True)
    groups=np.asarray(groups)
    if len(np.unique(groups))<3:
        raise ValueError('At least three training location groups required')
    grid=grid or DEFAULT_GRID
    splits=list(GroupKFold(n_splits=3).split(x,y,groups))
    rows,audit=[],[]
    for number,(c,g,e) in enumerate(itertools.product(grid['C'],grid['gamma'],grid['epsilon']),1):
        errors=[]
        params=dict(C=c,gamma=g,epsilon=e)
        for fold,(train,validation) in enumerate(splits):
            model,warning=fit_svr(x[train],y[train],groups[train],params)
            if warning or model.named_steps['svr'].fit_status_:
                raise RuntimeError('Inner SVR optimization did not converge')
            error=float(np.sqrt(np.mean((model.predict(x[validation])-y[validation])**2)))
            errors.append(error)
            audit.append(dict(candidate=number,inner_fold=fold,
                              training_indices=';'.join(map(str,train)),validation_indices=';'.join(map(str,validation)),
                              scaler_mean=';'.join(map(str,model.named_steps['standardscaler'].mean_)),rmse=error))
        rows.append(dict(candidate=number,**params,cv_rmse=float(np.mean(errors))))
    search=pd.DataFrame(rows)
    best=search.sort_values(['cv_rmse','candidate']).iloc[0]
    params={k:float(best[k]) for k in ('C','gamma','epsilon')}
    model,warning=fit_svr(x,y,groups,params)
    if warning or model.named_steps['svr'].fit_status_:
        raise RuntimeError('Final SVR optimization did not converge')
    return model,params,search,pd.DataFrame(audit)
