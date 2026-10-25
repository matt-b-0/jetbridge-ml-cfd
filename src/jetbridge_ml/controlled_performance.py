"""Controlled fit and prediction timing for existing experimental model settings."""
import argparse
import gc
from hashlib import sha256
from importlib.metadata import version
import json
from pathlib import Path
import platform
from time import perf_counter_ns
import tracemalloc
import warnings
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.interpolate import LinearNDInterpolator,RBFInterpolator
from scipy.spatial import cKDTree
from sklearn.preprocessing import StandardScaler
from jetbridge_ml.machine_learning.svr import fit_svr
from jetbridge_ml.machine_learning.selection import select_plane_svr
from threadpoolctl import threadpool_limits,threadpool_info

METHODS=('mean','nearest','linear','rbf','svr')


def fit_predictor(method,x,y,params):
    """Fit one predictor including its required coordinate preprocessing.

    Parameters
    ----------
    method : str
        Mean, nearest, linear, thin-plate RBF, or RBF-kernel SVR.
    x, y : numpy.ndarray
        Retained coordinates and speeds only.
    params : dict
        SVR parameters selected previously inside the outer training fold.

    Returns
    -------
    callable
        Batch predictor including its required query transformation.
    """
    if method=='mean':
        mean=float(np.mean(y))
        return lambda q:np.full(len(q),mean)
    if method=='svr':
        model,warning=fit_svr(x,y,np.arange(len(x)),params)
        if warning or model.named_steps['svr'].fit_status_:
            raise RuntimeError('SVR fit did not converge')
        return model.predict
    scaler=StandardScaler().fit(x); tx=scaler.transform(x)
    if method=='nearest':
        tree=cKDTree(tx)
        return lambda q:y[tree.query(scaler.transform(q))[1]]
    if method=='linear':
        model=LinearNDInterpolator(tx,y,fill_value=np.nan)
    elif method=='rbf':
        model=RBFInterpolator(tx,y,kernel='thin_plate_spline',degree=1,smoothing=0)
    else:
        raise ValueError('Unknown model')
    return lambda q:np.asarray(model(scaler.transform(q))).reshape(-1)


def main():
    """Time one identical held-location fold per run with interleaved repetitions."""
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--predictions',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--repeats',type=int,default=20)
    a=p.parse_args()
    if a.output.exists() or a.repeats<5:p.error('New output and at least five repetitions required')
    data=pd.read_csv(a.predictions)
    a.output.mkdir(parents=True)
    rng=np.random.default_rng(20261025)
    times=[]; searches=[]; memory=[]
    with threadpool_limits(limits=1):
        pools=threadpool_info()
        for run,table in data.groupby('run_id',sort=True):
            observed=table.drop_duplicates('source_row').sort_values('source_row')
            heldout=int(observed.source_row.min())
            train=observed[observed.source_row!=heldout]
            x=train[['x_m','y_m']].to_numpy(); y=train.speed_mps.to_numpy()
            q=observed[observed.source_row==heldout][['x_m','y_m']].to_numpy()
            row=table[(table.source_row==heldout)&(table.method=='svr')].iloc[0]
            params={k:float(row[k]) for k in ('C','gamma','epsilon')}
            # Workload spans the observed sensor rectangle, not a CFD truth field.
            xx,yy=np.meshgrid(np.linspace(observed.x_m.min(),observed.x_m.max(),40),np.linspace(observed.y_m.min(),observed.y_m.max(),60))
            dense=np.column_stack([xx.ravel(),yy.ravel()])
            for method in METHODS:
                predict=fit_predictor(method,x,y,params); predict(q); predict(dense)
            for repeat in range(a.repeats):
                for method in rng.permutation(METHODS):
                    start=perf_counter_ns(); predict=fit_predictor(method,x,y,params); fit_ns=perf_counter_ns()-start
                    start=perf_counter_ns(); single=predict(q); one_ns=perf_counter_ns()-start
                    start=perf_counter_ns(); field=predict(dense); dense_ns=perf_counter_ns()-start
                    times.append(dict(run_id=run,training_sensors=len(x),method=method,repeat=repeat,fit_ms=fit_ns/1e6,
                                      one_query_ms=one_ns/1e6,dense_2400_ms=dense_ns/1e6,fit_plus_dense_ms=(fit_ns+dense_ns)/1e6,
                                      dense_finite_predictions=int(np.isfinite(field).sum())))
            for repeat in range(3):
                start=perf_counter_ns(); model,chosen,_,_=select_plane_svr(x,y); elapsed=perf_counter_ns()-start
                np.testing.assert_allclose([chosen[k] for k in params],[params[k] for k in params],rtol=0,atol=0)
                searches.append(dict(run_id=run,training_sensors=len(x),repeat=repeat,search_and_final_fit_ms=elapsed/1e6))
            for method in METHODS:
                gc.collect(); tracemalloc.start()
                predict=fit_predictor(method,x,y,params); result=predict(dense)
                _,peak=tracemalloc.get_traced_memory(); tracemalloc.stop()
                memory.append(dict(run_id=run,training_sensors=len(x),method=method,peak_traced_python_bytes=peak))
            print('Timed',run,len(x),flush=True)
    times=pd.DataFrame(times); searches=pd.DataFrame(searches); memory=pd.DataFrame(memory)
    times.to_csv(a.output/'repeated_timings.csv',index=False); searches.to_csv(a.output/'search_timings.csv',index=False); memory.to_csv(a.output/'traced_allocations.csv',index=False)
    per_run=times.groupby(['run_id','training_sensors','method'],as_index=False)[['fit_ms','one_query_ms','dense_2400_ms','fit_plus_dense_ms']].median()
    per_run.to_csv(a.output/'per_run_medians.csv',index=False)
    summary=per_run.groupby(['training_sensors','method'],as_index=False)[['fit_ms','one_query_ms','dense_2400_ms','fit_plus_dense_ms']].median()
    summary.to_csv(a.output/'summary.csv',index=False)
    search_summary=searches.groupby(['training_sensors','run_id']).search_and_final_fit_ms.median().groupby('training_sensors').median()
    fig,axes=plt.subplots(1,2,figsize=(8.5,3.2),layout='constrained')
    colors=['#444444','#888888','#2681a0','#d69330','#a34863']
    for ax,n in zip(axes,[11,23]):
        part=summary[summary.training_sensors==n].set_index('method').loc[list(METHODS)]
        ax.bar(np.arange(5),part.fit_ms,color=colors,label='Fit including preprocessing')
        ax.bar(np.arange(5),part.dense_2400_ms,bottom=part.fit_ms,color=colors,hatch='///',alpha=.55,label='Predict 2400 queries')
        ax.set(xticks=np.arange(5),xticklabels=METHODS,ylabel='Median elapsed time (ms)',title=f'{n} retained sensors')
        ax.legend(fontsize=7); ax.grid(axis='y',alpha=.2)
    fig.suptitle('Controlled fixed-parameter workload | warm libraries | single-thread numerical pools')
    for ext in ['png','pdf']:fig.savefig(a.output/f'controlled_runtime.{ext}',dpi=300,bbox_inches='tight')
    plt.close(fig)
    model_summary=data.groupby('run_id').source_row.nunique().to_dict()
    record=dict(repeats=a.repeats,warmup='One untimed fit and both query workloads per method/run',
                design='First source location withheld in each of 36 runs; same retained data and query sets across methods; method order shuffled within repetitions',
                seed=20261025,aggregation='Median across repetitions within run, then median across runs within layout size',
                timing='perf_counter_ns; file I/O and table parsing excluded; fitting includes each method required preprocessing; prediction includes query transform',
                svr_search='Separate 12-candidate x 3-fold search plus final refit; three repetitions per run; selected parameters checked against saved outer fold',
                search_median_ms={str(k):float(v) for k,v in search_summary.items()},
                memory='Peak tracemalloc allocation during one fit and 2400-query prediction; includes Python-traced arrays but not all native library or process allocations; not total RAM',
                platform=platform.platform(),cpu=Path('/proc/cpuinfo').read_text().split('model name',1)[1].split('\n',1)[0].strip(' :\t') if Path('/proc/cpuinfo').exists() else platform.processor(),
                packages={p:version(p) for p in ['numpy','scipy','pandas','scikit-learn','threadpoolctl']},threadpools=pools,
                source_sha256=sha256(a.predictions.read_bytes()).hexdigest(),script_sha256=sha256(Path(__file__).read_bytes()).hexdigest(),
                limits=['Illustrative small-array workload, not every outer fold or large-data scaling experiment','Linear returns NaN outside its training hull; timing does not imply equivalent support',
                        'Process scheduling and hardware affect short timings; no precision beyond the recorded repeats is implied','No retuning on test values or changes to reported predictive accuracy'])
    (a.output/'manifest.json').write_text(json.dumps(record,indent=2)+'\n')
    print(summary.to_string(index=False));print('SVR search medians ms:',record['search_median_ms'])


if __name__=='__main__':main()
