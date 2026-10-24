"""Train and evaluate interpolation/SVR on sparse versus dense CFD samples."""
import argparse
from datetime import datetime, timezone
from hashlib import sha256
from importlib.metadata import version
import json
from pathlib import Path
import platform
import time

import joblib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import Normalize, TwoSlopeNorm
import numpy as np
import pandas as pd
from scipy.spatial import Delaunay
from sklearn.model_selection import LeaveOneGroupOut

from .cfd_interface.virtual_sensors import TRAIN_STATIONS, TEST_STATIONS
from .interpolation.spatial import predict_spatial
from .machine_learning.svr import fit_svr, grouped_svr_search
from .validation.metrics import regression_metrics

FEATURES=("x_m","height_m","z_m")
METHODS=("nearest","linear","rbf","svr")


def training_partition(sparse,train_stations=TRAIN_STATIONS,test_stations=TEST_STATIONS):
    """Select only predeclared training stations before fitting or scaling.

    Parameters
    ----------
    sparse : pandas.DataFrame
        Exported virtual sensors, with features, station_ft and speed_mps.
    train_stations, test_stations : sequence of int
        Disjoint station groups.

    Returns
    -------
    pandas.DataFrame
        Training rows only. Held-out sparse values are not training targets.
    """
    if set(train_stations)&set(test_stations):
        raise ValueError("Training/test stations overlap")
    train=sparse[sparse.station_ft.isin(train_stations)].copy()
    if set(train.station_ft)!=set(train_stations):
        raise ValueError("Missing training station")
    if not np.isfinite(train[list(FEATURES)+["speed_mps"]].to_numpy()).all():
        raise ValueError("Training samples must be finite")
    if train.duplicated(list(FEATURES)).any():
        raise ValueError("Duplicate virtual training locations")
    return train.reset_index(drop=True)


def _training_diagnostics(x,y,groups,params):
    curves=[]
    budget_rows=[]
    for fraction in (.25,.5,.75,1.):
        for train,test in LeaveOneGroupOut().split(x,y,groups):
            rng=np.random.default_rng(20261024)
            chosen=[]
            for group in np.unique(groups[train]):
                candidates=train[groups[train]==group]
                order=rng.permutation(candidates)
                chosen.extend(order[:max(2,int(np.ceil(fraction*len(order))))])
            chosen=np.array(chosen)
            model,warning=fit_svr(x[chosen],y[chosen],groups[chosen],params)
            curves.append(dict(fraction=fraction,n_train=len(chosen),heldout_station=int(groups[test][0]),
                training_rmse=float(np.sqrt(np.mean((model.predict(x[chosen])-y[chosen])**2))),
                validation_rmse=float(np.sqrt(np.mean((model.predict(x[test])-y[test])**2))),
                optimization_warning=warning))
    for budget in (1,2,5,10,20,50,100,300,1000,3000):
        for train,test in LeaveOneGroupOut().split(x,y,groups):
            model,warning=fit_svr(x[train],y[train],groups[train],params,max_iter=budget)
            budget_rows.append(dict(iteration_budget=budget,heldout_station=int(groups[test][0]),
                actual_solver_iterations=int(model.named_steps["svr"].n_iter_),
                optimization_converged=not warning and model.named_steps["svr"].fit_status_==0,
                training_rmse=float(np.sqrt(np.mean((model.predict(x[train])-y[train])**2))),
                validation_rmse=float(np.sqrt(np.mean((model.predict(x[test])-y[test])**2)))))
    return pd.DataFrame(curves),pd.DataFrame(budget_rows)


def _score(dense,predictions,common,inside):
    rows=[]
    for station,indices in dense.groupby("station_ft",sort=True).groups.items():
        indices=np.array(list(indices))
        for method,values in predictions.items():
            for subset,mask in (("common_hull",common),("outside_hull",~inside),("all",np.ones(len(dense),bool))):
                selected=indices[mask[indices]]
                valid=selected[np.isfinite(values[selected])]
                metrics=regression_metrics(dense.speed_mps.to_numpy()[valid],values[valid]) if len(valid) else dict(rmse=np.nan,mae=np.nan,bias=np.nan)
                rows.append(dict(station_ft=int(station),method=method,subset=subset,n_requested=len(selected),
                    n_predicted=len(valid),coverage=len(valid)/len(selected) if len(selected) else np.nan,
                    negative_predictions=int((values[valid]<0).sum()),**metrics))
    return pd.DataFrame(rows)


def main():
    """Fit on declared sparse inputs, then unlock the dense test planes once."""
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--samples",required=True,type=Path)
    parser.add_argument("--output",required=True,type=Path)
    args=parser.parse_args()
    if args.output.exists():
        parser.error("Output directory must be new")
    sample_manifest=json.loads((args.samples/"sampling_manifest.json").read_text())
    if sample_manifest["train_stations"]!=list(TRAIN_STATIONS) or sample_manifest["test_stations"]!=list(TEST_STATIONS):
        parser.error("Sampling split differs from the predeclared benchmark")
    sparse=pd.read_csv(args.samples/"sparse.csv")
    train=training_partition(sparse)
    x=train[list(FEATURES)].to_numpy()
    y=train.speed_mps.to_numpy()
    groups=train.station_ft.to_numpy()
    args.output.mkdir(parents=True)
    start=time.perf_counter()
    model,params,search,fold_audit=grouped_svr_search(x,y,groups)
    search_seconds=time.perf_counter()-start
    search.to_csv(args.output/"hyperparameter_search.csv",index=False)
    fold_audit.to_csv(args.output/"cv_fold_audit.csv",index=False)
    curves,budget=_training_diagnostics(x,y,groups,params)
    curves.to_csv(args.output/"learning_curve.csv",index=False)
    budget.to_csv(args.output/"solver_iteration_curve.csv",index=False)
    joblib.dump(model,args.output/"svr_model.joblib")
    # Dense test labels are read only after selection, fitting and training-only diagnostics.
    dense=pd.read_csv(args.samples/"dense_test.csv").reset_index(drop=True)
    if set(dense.station_ft)!=set(TEST_STATIONS):
        raise ValueError("Unexpected dense test stations")
    if set(train.station_ft)&set(dense.station_ft):
        raise ValueError("Test station leaked into training")
    if not np.isfinite(dense[list(FEATURES)+["speed_mps"]].to_numpy()).all():
        raise ValueError("Invalid dense reference samples")
    q=dense[list(FEATURES)].to_numpy()
    scaler=model.named_steps["standardscaler"]
    xs,qs=scaler.transform(x),scaler.transform(q)
    inside=Delaunay(xs).find_simplex(qs,tol=1e-10)>=0
    predictions={}
    timings=[]
    for method in METHODS:
        start=time.perf_counter()
        predictions[method]=model.predict(q) if method=="svr" else predict_spatial(method,xs,y,qs)
        timings.append(dict(method=method,combined_fit_predict_seconds=time.perf_counter()-start,
                            note="Prediction only; trained SVR fit/search recorded separately" if method=="svr" else "Interpolator construction and prediction"))
    common=inside.copy()
    for values in predictions.values():
        common &= np.isfinite(values)
    metrics=_score(dense,predictions,common,inside)
    metrics.to_csv(args.output/"metrics.csv",index=False)
    pd.DataFrame(timings).to_csv(args.output/"timing.csv",index=False)
    result=dense.copy()
    result["inside_training_hull"]=inside
    result["common_supported"]=common
    for method,values in predictions.items():
        result[method+"_speed_mps"]=values
        result[method+"_delta_mps"]=values-dense.speed_mps
    result.to_csv(args.output/"dense_predictions.csv",index=False)
    train.to_csv(args.output/"training_virtual_sensors.csv",index=False)
    plt.rcParams.update({"font.size":10,"axes.spines.top":False,"axes.spines.right":False})
    def save(fig,name):
        for suffix in ("png","pdf"):
            fig.savefig(args.output/f"{name}.{suffix}",dpi=180,bbox_inches="tight",facecolor="white")
        plt.close(fig)

    fig,axes=plt.subplots(1,2,figsize=(12,4),layout="constrained")
    axes[0].plot(search.candidate,search.cv_rmse,"o-",label="Candidate validation RMSE")
    axes[0].plot(search.candidate,search.cv_rmse.cummin(),lw=2,label="Best so far")
    axes[0].set(xlabel="Hyperparameter configuration evaluated (not epoch)",ylabel="Mean station CV RMSE (m/s)",
                title="Training-station hyperparameter search")
    axes[0].legend(fontsize=8)
    curve=curves.groupby("fraction").agg(n_train=("n_train","mean"),training=("training_rmse","mean"),
                                        validation=("validation_rmse","mean"),sd=("validation_rmse","std"))
    axes[1].plot(curve.n_train,curve.training,"o-",label="Training")
    axes[1].plot(curve.n_train,curve.validation,"s-",label="Held-out training station (CV)")
    axes[1].fill_between(curve.n_train,np.maximum(0,curve.validation-curve.sd),curve.validation+curve.sd,alpha=.15)
    axes[1].set(xlabel="Mean number of training virtual sensors per CV fold",ylabel="RMSE (m/s)",
                title="Descriptive learning curve; fixed selected parameters")
    axes[1].legend(fontsize=8)
    for ax in axes:
        ax.grid(alpha=.2)
    fig.suptitle("SVR training diagnostics: dense test planes excluded; shading is station SD, not a confidence interval")
    save(fig,"svr_learning_and_search")

    curve=budget.groupby("iteration_budget").agg(training=("training_rmse","mean"),validation=("validation_rmse","mean"),
                                                 sd=("validation_rmse","std"),converged=("optimization_converged","sum"))
    fig,ax=plt.subplots(figsize=(9,5),layout="constrained")
    ax.semilogx(curve.index,curve.training,"o-",label="Training RMSE")
    ax.semilogx(curve.index,curve.validation,"s-",label="Station-grouped CV RMSE")
    ax.fill_between(curve.index,np.maximum(0,curve.validation-curve.sd),curve.validation+curve.sd,alpha=.15)
    ax.set(xlabel="Maximum SVR solver iterations per fit (not epochs)",ylabel="Mean RMSE (m/s)",
           title="SVR optimization-budget error curve\nFresh fit at each limit; fixed selected hyperparameters; no dense test data")
    ax.legend()
    ax.grid(alpha=.2)
    save(fig,"svr_solver_iteration_error")

    fig,axes=plt.subplots(1,2,figsize=(11,4),layout="constrained")
    for ax,subset in zip(axes,("common_hull","outside_hull")):
        for method in METHODS:
            part=metrics[(metrics.method==method)&(metrics.subset==subset)].sort_values("station_ft")
            ax.plot(part.station_ft,part.rmse,"o-",label=method)
        ax.set(xlabel="Held-out station (ft)",ylabel="Dense CFD reconstruction RMSE (m/s)",
               title="Common supported points" if subset=="common_hull" else "Outside training hull (linear unsupported)")
        ax.legend(fontsize=8)
        ax.grid(alpha=.2)
    fig.suptitle("Final held-out CFD planes: same sparse inputs; CFD numerical reference, not experimental truth")
    save(fig,"heldout_station_errors")

    ny,nx=int(sample_manifest["ny"]),int(sample_manifest["nx"])
    vmax=max(dense.speed_mps.max(),predictions["svr"].max())
    limit=float(max(abs(result.svr_delta_mps)))
    fig,axes=plt.subplots(4,3,figsize=(11,13),layout="constrained")
    for row,station in enumerate(TEST_STATIONS):
        part=result[result.station_ft==station].sort_values(["grid_row","grid_col"])
        gx,gy=part.x_m.to_numpy().reshape(ny,nx),part.height_m.to_numpy().reshape(ny,nx)
        for col,(key,title) in enumerate((("speed_mps","CFD reference"),("svr_speed_mps","SVR prediction"),("svr_delta_mps","SVR - CFD"))):
            values=part[key].to_numpy().reshape(ny,nx)
            image=axes[row,col].pcolormesh(gx,gy,values,shading="auto",
                cmap="RdBu_r" if col==2 else "viridis",
                norm=TwoSlopeNorm(vmin=-limit,vcenter=0,vmax=limit) if col==2 else Normalize(0,vmax))
            axes[row,col].set_aspect("equal")
            axes[row,col].set(xlabel="x (m)",ylabel=f"{station} ft | height above floor (m)",
                              title=title if row==0 else "")
            fig.colorbar(image,ax=axes[row,col],label="m/s",shrink=.65)
    fig.suptitle("SVR on four wholly held-out cross-sections\nAll targets are from one converged isothermal CFD field")
    save(fig,"svr_heldout_slices")

    limit=max(float(np.nanmax(abs(values-dense.speed_mps.to_numpy()))) for values in predictions.values())
    fig,axes=plt.subplots(4,4,figsize=(13,13),layout="constrained")
    for row,station in enumerate(TEST_STATIONS):
        mask=dense.station_ft.to_numpy()==station
        part=dense[mask]
        gx,gy=part.x_m.to_numpy().reshape(ny,nx),part.height_m.to_numpy().reshape(ny,nx)
        for col,method in enumerate(METHODS):
            delta=(predictions[method][mask]-part.speed_mps.to_numpy()).reshape(ny,nx)
            cmap=plt.get_cmap("RdBu_r").copy()
            cmap.set_bad("#d9d9d9")
            image=axes[row,col].pcolormesh(gx,gy,np.ma.masked_invalid(delta),shading="auto",cmap=cmap,
                                         norm=TwoSlopeNorm(vmin=-limit,vcenter=0,vmax=limit))
            axes[row,col].set_aspect("equal")
            axes[row,col].set(xlabel="x (m)",ylabel=f"{station} ft | local height (m)",title=method if row==0 else "")
    fig.colorbar(image,ax=list(axes.flat),label="Prediction - CFD speed (m/s)",shrink=.6)
    fig.suptitle("Interpolation versus SVR: held-out dense CFD reconstruction differences\nGrey = unsupported linear extrapolation; shared colour scale")
    save(fig,"interpolation_svr_delta_slices")

    paths=[args.samples/"sparse.csv",args.samples/"dense_test.csv",args.samples/"sampling_manifest.json"]
    root=Path(__file__).resolve().parents[2]
    code_paths=[Path(__file__),root/"src/jetbridge_ml/machine_learning/svr.py",
                root/"src/jetbridge_ml/interpolation/spatial.py",root/"src/jetbridge_ml/cfd_interface/virtual_sensors.py"]
    manifest=dict(created_utc=datetime.now(timezone.utc).isoformat(),python=platform.python_version(),
        packages={p:version(p) for p in ("numpy","scipy","pandas","scikit-learn","matplotlib","joblib")},
        train_stations=list(TRAIN_STATIONS),test_stations=list(TEST_STATIONS),training_points=len(train),
        dense_test_points=len(dense),features=list(FEATURES),selected_parameters=params,
        final_svr_solver_iterations=int(model.named_steps["svr"].n_iter_),final_fit_status=int(model.named_steps["svr"].fit_status_),
        hyperparameter_search_seconds=search_seconds,cv="leave one training station out; equal station scoring and fit weights",
        shared_preprocessing="Training-only StandardScaler used for all 3D methods; no target scaling",
        rbf_baseline=dict(kernel="thin_plate_spline",degree=1,smoothing=0),
        random_seed_learning_subsets=20261024,
        input_sha256={str(p):sha256(p.read_bytes()).hexdigest() for p in paths},
        source_sha256={str(p.relative_to(root)):sha256(p.read_bytes()).hexdigest() for p in code_paths},
        interpretation=["SVR has no neural-network epochs",
                        "Iteration-budget curve uses independent fresh fits and training-station CV, not a warm-start trace",
                        "Learning curves are descriptive after parameter selection, not independent test estimates",
                        "Dense test planes unlocked only after fitting and training-only diagnostics",
                        "No physical/experimental validation or CFD-flow conservation imposed on predictions",
                        "Wall regions outside the sensor hull are extrapolation",
                        "No prediction clipping; negative values counted",
                        "All targets are correlated samples from one numerical CFD solution"])
    (args.output/"manifest.json").write_text(json.dumps(manifest,indent=2)+"\n")
    print("Training points:",len(train),"Dense test points:",len(dense),"Selected:",params)
    print("Final SVR solver iterations:",model.named_steps["svr"].n_iter_)
    print(metrics[metrics.subset=="common_hull"].groupby("method")[["rmse","mae","bias"]].mean().to_string())
    print("Results:",args.output)


if __name__=="__main__":
    main()
