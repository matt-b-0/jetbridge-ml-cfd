"""Station-grouped SVR fitting with train-only scaling and recorded search."""
import itertools
import warnings

import numpy as np
import pandas as pd
from sklearn.exceptions import ConvergenceWarning
from sklearn.model_selection import LeaveOneGroupOut
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVR


def station_weights(groups):
    """Return mean-one weights giving each station equal total weight.

    Parameters
    ----------
    groups : array-like
        Station identifier per training observation.

    Returns
    -------
    numpy.ndarray
        Positive weights; mean is one and station sums are equal.
    """
    groups=np.asarray(groups)
    _,index,count=np.unique(groups,return_inverse=True,return_counts=True)
    if len(groups)==0:
        raise ValueError("Nonempty groups required")
    return len(groups)/(len(count)*count[index])


def fit_svr(x,y,groups,parameters,max_iter=-1):
    """Fit fixed SVR parameters using only supplied training observations.

    Parameters
    ----------
    x, y : array-like
        Finite training feature matrix and scalar targets.
    groups : array-like
        Training station labels for balanced fitting weights.
    parameters : dict
        C, gamma, epsilon for an RBF-kernel SVR.
    max_iter : int
        Libsvm optimization iteration limit; -1 means unlimited.

    Returns
    -------
    tuple
        Fitted StandardScaler/SVR pipeline and convergence-warning flag.
        SVR uses optimization iterations, not neural-network epochs.
    """
    x,y,groups=np.asarray(x,float),np.asarray(y,float),np.asarray(groups)
    if x.ndim!=2 or y.shape!=(len(x),) or groups.shape!=(len(x),) or len(x)<2:
        raise ValueError("Inconsistent nonempty training arrays")
    if not np.isfinite(x).all() or not np.isfinite(y).all():
        raise ValueError("Training data must be finite")
    model=make_pipeline(StandardScaler(),SVR(kernel="rbf",tol=1e-6,max_iter=max_iter,**parameters))
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always",ConvergenceWarning)
        model.fit(x,y,svr__sample_weight=station_weights(groups))
    warning=any(issubclass(w.category,ConvergenceWarning) for w in caught)
    return model,warning


def grouped_svr_search(x,y,groups,grid=None):
    """Select parameters by leave-one-training-station-out RMSE.

    Parameters
    ----------
    x, y : array-like
        Training features and CFD-derived scalar speeds only.
    groups : array-like
        At least three distinct training stations.
    grid : dict, optional
        Lists for C, gamma and epsilon. Defaults are predefined, not test-tuned.

    Returns
    -------
    tuple
        Fitted best model, selected parameters, candidate summary table and
        fold audit records. The held-out dense planes are never arguments.
    """
    x,y,groups=np.asarray(x,float),np.asarray(y,float),np.asarray(groups)
    if len(np.unique(groups))<3:
        raise ValueError("At least three training stations required")
    grid=grid or dict(C=[.1,1.,10.],gamma=[.05,.2,1.],epsilon=[.0005,.002,.005])
    candidates,audit=[],[]
    for number,(c,gamma,epsilon) in enumerate(itertools.product(grid["C"],grid["gamma"],grid["epsilon"]),1):
        params=dict(C=c,gamma=gamma,epsilon=epsilon)
        errors,training=[],[]
        for train,test in LeaveOneGroupOut().split(x,y,groups):
            model,warning=fit_svr(x[train],y[train],groups[train],params)
            if warning or model.named_steps["svr"].fit_status_!=0:
                raise RuntimeError("A full CV fit did not converge")
            error=float(np.sqrt(np.mean((model.predict(x[test])-y[test])**2)))
            train_error=float(np.sqrt(np.mean((model.predict(x[train])-y[train])**2)))
            errors.append(error)
            training.append(train_error)
            audit.append(dict(candidate=number,heldout_station=int(groups[test][0]),
                              training_stations=";".join(map(str,np.unique(groups[train]))),
                              n_train=len(train),n_validation=len(test),rmse=error,
                              scaler_mean=";".join(map(str,model.named_steps["standardscaler"].mean_))))
        candidates.append(dict(candidate=number,**params,cv_rmse=float(np.mean(errors)),
                               cv_station_sd=float(np.std(errors,ddof=1)),
                               training_rmse=float(np.mean(training))))
    summary=pd.DataFrame(candidates)
    best=summary.sort_values(["cv_rmse","candidate"]).iloc[0]
    parameters={key:float(best[key]) for key in ("C","gamma","epsilon")}
    model,warning=fit_svr(x,y,groups,parameters)
    if warning or model.named_steps["svr"].fit_status_!=0:
        raise RuntimeError("Final SVR fit did not converge")
    return model,parameters,summary,pd.DataFrame(audit)
