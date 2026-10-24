"""Nested held-location experimental interpolation and SVR comparison."""
import argparse
from hashlib import sha256
from importlib.metadata import version
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.spatial import Delaunay
from jetbridge_ml.benchmark import summarize
from jetbridge_ml.cfd_interface.plot_comparison import mesh_profile
from jetbridge_ml.data_processing.faa import read_speed_average
from jetbridge_ml.interpolation.plane import predict_plane
from jetbridge_ml.machine_learning.selection import select_plane_svr, DEFAULT_GRID

METHODS=('nearest','linear','rbf','svr')


def evaluate_experimental_plane(frame,grid=None):
    """Withhold each location before tuning on one independent replicate.

    Parameters
    ----------
    frame : pandas.DataFrame
        One FAA replicate, with unique absolute xyz and scalar speed.
    grid : dict, optional
        Training-only SVR hyperparameter grid.

    Returns
    -------
    tuple
        Outer predictions, search records and nested split/scaler audit.
    """
    if frame.run_id.nunique()!=1 or frame[['x_m','y_m']].duplicated().any():
        raise ValueError('One replicate with unique sensor locations required')
    valid=frame[np.isfinite(frame.speed_mps)].reset_index(drop=True)
    x=valid[['x_m','y_m']].to_numpy()
    y=valid.speed_mps.to_numpy()
    predictions,searches,audits=[],[],[]
    for heldout in range(len(valid)):
        train=np.delete(np.arange(len(valid)),heldout)
        model,params,search,audit=select_plane_svr(x[train],y[train],grid=grid)
        scaler=model.named_steps['standardscaler']
        tx,qx=scaler.transform(x[train]),scaler.transform(x[[heldout]])
        inside=bool(Delaunay(tx).find_simplex(qx,tol=1e-10)[0]>=0)
        for method in METHODS:
            pred=model.predict(x[[heldout]]) if method=='svr' else predict_plane(method,tx,y[train],qx)
            row=valid.iloc[heldout].to_dict()
            row.update(method=method,fold=heldout,prediction_mps=float(pred[0]),inside_hull=inside,
                       target_available=True,train_rows=';'.join(map(str,valid.iloc[train].source_row)))
            if method=='svr':
                row.update(params)
            predictions.append(row)
        for table in (search,audit):
            table['run_id']=frame.run_id.iloc[0]
            table['outer_source_row']=int(valid.source_row.iloc[heldout])
        # Inner indices refer only to these outer training rows, never to test.
        audit['outer_training_source_rows']=';'.join(map(str,valid.iloc[train].source_row))
        audit['outer_scaler_mean']=';'.join(map(str,scaler.mean_))
        searches.append(search)
        audits.append(audit)
    return pd.DataFrame(predictions),pd.concat(searches),pd.concat(audits)


def main():
    """Run the predeclared S01-A-HN replicate comparison and save audit/plots."""
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--dataset',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--mesh',type=Path,required=True)
    a=p.parse_args()
    if a.output.exists():
        p.error('Choose a fresh output directory')
    sources=sorted((a.dataset/'03-Averages').glob('V-S01-A-*-HN-*.txt'))
    if not sources:
        p.error('No matching source replicate files')
    a.output.mkdir(parents=True)
    predictions,searches,audits=[],[],[]
    for i,path in enumerate(sources,1):
        frame=read_speed_average(path)
        pred,search,audit=evaluate_experimental_plane(frame)
        predictions.append(pred); searches.append(search); audits.append(audit)
        print(f'{i}/{len(sources)} {path.stem}',flush=True)
    pred=pd.concat(predictions,ignore_index=True)
    metrics=summarize(pred)
    correlation=[]
    for (run,method),part in pred.groupby(['run_id','method']):
        for subset in ('common_hull','outside_hull','all'):
            selected=part if subset=='all' else part[part.inside_hull==(subset=='common_hull')]
            selected=selected[np.isfinite(selected.prediction_mps)]
            obs,fit=selected.speed_mps.to_numpy(),selected.prediction_mps.to_numpy()
            r=float(np.corrcoef(obs,fit)[0,1]) if len(obs)>1 and np.std(obs)>1e-12 and np.std(fit)>1e-12 else np.nan
            denominator=np.sum((obs-obs.mean())**2) if len(obs) else 0
            r2=float(1-np.sum((obs-fit)**2)/denominator) if denominator>1e-20 else np.nan
            correlation.append(dict(run_id=run,method=method,subset=subset,pearson_r=r,r2=r2))
    metrics=metrics.merge(pd.DataFrame(correlation),on=['run_id','method','subset'])
    _,zs,floors,_=mesh_profile(a.mesh)
    pred['height_m']=pred.y_m-np.interp(pred.z_m,zs,floors)
    pred['error_mps']=pred.prediction_mps-pred.speed_mps
    pred.to_csv(a.output/'predictions.csv',index=False)
    metrics.to_csv(a.output/'metrics.csv',index=False)
    pd.concat(searches).to_csv(a.output/'search.csv',index=False)
    pd.concat(audits).to_csv(a.output/'nested_split_audit.csv',index=False)
    summary=metrics.groupby(['method','subset'],as_index=False).agg(mean_run_rmse=('rmse','mean'),mean_run_mae=('mae','mean'),mean_run_bias=('bias','mean'),n_requested=('n_requested','sum'),n_predicted=('n_predicted','sum'))
    summary.to_csv(a.output/'summary.csv',index=False)
    def save(fig,name):
        for ext in ('png','pdf'):
            fig.savefig(a.output/f'{name}.{ext}',dpi=300,bbox_inches='tight')
        plt.close(fig)
    fig,axes=plt.subplots(1,2,figsize=(10,4),layout='constrained')
    for ax,subset in zip(axes,('common_hull','outside_hull')):
        part=summary[summary.subset==subset].set_index('method').reindex(METHODS)
        ax.bar(METHODS,part.mean_run_rmse,color=['#777','#2681a0','#d69330','#a34863'])
        ax.set(ylabel='Mean per-run outer RMSE (m/s)',title=subset.replace('_',' '))
    fig.suptitle('Experimental prediction: nested held-location evaluation\nLinear does not extrapolate; SVR tuned inside outer training data only')
    save(fig,'experimental_nested_errors')
    fig,axes=plt.subplots(1,4,figsize=(13,3.8),layout='constrained')
    common=pred[pred.inside_hull]
    for ax,method in zip(axes,METHODS):
        part=common[common.method==method]
        image=ax.scatter(part.speed_mps,part.prediction_mps,c=part.station_ft,cmap='viridis',s=12,alpha=.65,vmin=10,vmax=58)
        limit=max(common.speed_mps.max(),common.prediction_mps.max())*1.03
        ax.plot([0,limit],[0,limit],'k--',lw=.8)
        ax.set(xlabel='Measured speed (m/s)',ylabel='Held-out prediction (m/s)',title=method,xlim=(0,limit),ylim=(0,limit))
        ax.set_aspect('equal')
    fig.colorbar(image,ax=list(axes),label='Station label (ft)',shrink=.7)
    fig.suptitle('Common supported experimental locations | independent fit per replicate')
    save(fig,'experimental_parity')
    fig,axes=plt.subplots(1,2,figsize=(11,4),layout='constrained')
    for method in METHODS:
        part=common[common.method==method]
        station=part.groupby(['station_ft','run_id']).error_mps.apply(lambda v:np.sqrt(np.mean(v**2))).groupby('station_ft').mean()
        axes[0].plot(station.index,station.values,'o-',label=method)
        # Binned descriptive mean error, not a confidence interval.
        bins=pd.cut(part.height_m,[0,.5,1,1.5,2,2.5])
        values=part.groupby(bins,observed=True).error_mps.mean()
        axes[1].plot([v.mid for v in values.index],values.values,'o-',label=method)
    axes[0].set(xlabel='Nominal station (ft)',ylabel='Mean per-run RMSE (m/s)')
    axes[1].set(xlabel='Local sensor height bin midpoint (m)',ylabel='Mean signed prediction error (m/s)')
    axes[1].axhline(0,color='black',lw=.8)
    for ax in axes:
        ax.legend(fontsize=8); ax.grid(alpha=.2)
    fig.suptitle('Experimental spatial diagnostics | common supported locations')
    save(fig,'experimental_spatial_errors')
    manifest=dict(packages={name:version(name) for name in ('numpy','pandas','scipy','scikit-learn','matplotlib')},
                  runs=len(sources),outer_targets=int(len(pred)/4),methods=list(METHODS),grid=DEFAULT_GRID,
                  split='Nested outer leave-one-location-out; inner 3-fold grouped location CV; independent fit per replicate; no replicate pooling',
                  scaling='Training-only StandardScaler shared by all baselines in each outer fold; differs from original unscaled exploratory benchmark',
                  interpretation='Outer cross-validation estimates tuned algorithm error, not a new untouched external test; repeats/runs are not independent physical systems',
                  source_sha256={str(f):sha256(f.read_bytes()).hexdigest() for f in sources+[a.mesh]},
                  code_sha256={str(path):sha256(path.read_bytes()).hexdigest() for path in [Path(__file__),Path(__file__).parent/'machine_learning/selection.py',Path(__file__).parent/'machine_learning/svr.py',Path(__file__).parent/'interpolation/plane.py']})
    (a.output/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(summary.to_string(index=False),flush=True)


if __name__=='__main__':
    main()
