"""Paired model errors at run and station level, without IID sensor inference."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


def paired_errors(metrics,subset='common_hull'):
    """Pair methods only where they evaluated identical complete target counts.

    Parameters
    ----------
    metrics : pandas.DataFrame
        Per-run metrics from nested experimental evaluation.
    subset : str
        Comparison region, default common supported locations.

    Returns
    -------
    pandas.DataFrame
        One run per row; negative RBF-minus-SVR favours RBF.
    """
    part=metrics[(metrics.subset==subset)&metrics.method.isin(['rbf','svr'])].copy()
    if part.duplicated(['run_id','method']).any():
        raise ValueError('Duplicate run/method metrics')
    if (part.n_requested!=part.n_predicted).any():
        raise ValueError('Paired methods must have complete target coverage')
    counts=part.pivot(index='run_id',columns='method',values='n_requested')
    errors=part.pivot(index='run_id',columns='method',values='rmse')
    if not {'rbf','svr'}.issubset(errors.columns) or errors[['rbf','svr']].isna().any().any() or not (counts.rbf==counts.svr).all():
        raise ValueError('Every run must contain both methods on the same target count')
    result=errors[['rbf','svr']].rename(columns={'rbf':'rbf_rmse','svr':'svr_rmse'}).reset_index()
    extracted=result.run_id.str.extract(r'^S\d+-[A-Z0-9]+-(\d+)-(?:HN|HP|LN|LP)-(.+)$')
    if extracted.isna().any().any():
        raise ValueError('Unrecognised experimental run ID')
    result['station_ft']=extracted[0].astype(int)
    result['replicate']=extracted[1]
    result['rbf_minus_svr_mps']=result.rbf_rmse-result.svr_rmse
    return result.sort_values(['station_ft','run_id']).reset_index(drop=True)


def main():
    """Save descriptive paired errors and transparent baseline comparisons."""
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--metrics',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    if a.output.exists(): p.error('Choose a fresh output directory')
    metrics=pd.read_csv(a.metrics)
    pairs=paired_errors(metrics)
    counts=metrics[(metrics.subset=='all')&(metrics.method=='rbf')].set_index('run_id').n_requested
    if len(counts)!=len(pairs):
        raise ValueError('Layout sizes require one all-target record per paired run')
    pairs['layout_points']=pairs.run_id.map(counts)
    if pairs.layout_points.isna().any():
        raise ValueError('Missing source layout size')
    stations=pairs.groupby('station_ft',as_index=False).agg(runs=('run_id','size'),mean_difference=('rbf_minus_svr_mps','mean'),median_difference=('rbf_minus_svr_mps','median'))
    strata=pairs.groupby('layout_points',as_index=False).agg(runs=('run_id','size'),mean_difference=('rbf_minus_svr_mps','mean'),median_difference=('rbf_minus_svr_mps','median'))
    a.output.mkdir(parents=True)
    pairs.to_csv(a.output/'paired_runs.csv',index=False)
    stations.to_csv(a.output/'paired_stations.csv',index=False)
    strata.to_csv(a.output/'paired_layouts.csv',index=False)
    common=metrics[metrics.subset=='common_hull']
    summary=common.groupby('method',as_index=False).agg(mean_run_rmse=('rmse','mean'),mean_run_mae=('mae','mean'),mean_run_bias=('bias','mean'))
    summary.to_csv(a.output/'model_summary.csv',index=False)
    errors=common.pivot(index='run_id',columns='method',values='rmse')
    improvement=[]
    if 'mean' in errors:
        for method in errors.columns.drop('mean'):
            difference=errors[method]-errors['mean']
            improvement.append(dict(method=method,runs=int(len(difference)),beats_mean_runs=int((difference<0).sum()),mean_rmse_difference_mps=float(difference.mean())))
    pd.DataFrame(improvement).to_csv(a.output/'versus_mean.csv',index=False)
    fig,axes=plt.subplots(1,2,figsize=(12,5),layout='constrained',gridspec_kw={'width_ratios':[1.8,1]})
    colors=np.where(pairs.rbf_minus_svr_mps<0,'#d69330','#a34863')
    axes[0].bar(np.arange(len(pairs)),pairs.rbf_minus_svr_mps,color=colors)
    axes[0].set(xticks=np.arange(len(pairs)),xticklabels=[f'{r.station_ft}/{r.replicate}' for r in pairs.itertuples()],xlabel='Station (ft) / replicate',ylabel='RBF RMSE − SVR RMSE (m/s)',title='Paired errors within each run')
    axes[0].tick_params(axis='x',rotation=90,labelsize=7)
    axes[1].bar(stations.station_ft.astype(str),stations.mean_difference,color=np.where(stations.mean_difference<0,'#d69330','#a34863'))
    axes[1].set(xlabel='Station label (ft)',ylabel='Mean paired difference (m/s)',title='Equal-run mean within station')
    for ax in axes:
        ax.axhline(0,color='black',lw=.8); ax.grid(axis='y',alpha=.2)
    fig.suptitle('Negative favours RBF; positive favours SVR | common supported targets\nDescriptive paired comparisons; no IID-sensor confidence intervals or significance claim')
    for ext in ('png','pdf'):
        fig.savefig(a.output/f'paired_model_errors.{ext}',dpi=300,bbox_inches='tight')
    plt.close(fig)
    diff=pairs.rbf_minus_svr_mps
    record=dict(runs=len(pairs),stations=len(stations),rbf_wins=int((diff<-1e-12).sum()),svr_wins=int((diff>1e-12).sum()),ties=int((abs(diff)<=1e-12).sum()),
                equal_run_mean_difference_mps=float(diff.mean()),median_difference_mps=float(diff.median()),
                equal_station_mean_difference_mps=float(stations.mean_difference.mean()),
                layout_strata=strata.to_dict(orient='records'),
                limitations=['Run/station pairs are descriptive; repeated measurements share an apparatus',
                             'The 24-point layout occurs at 58 ft; station and layout density are confounded, so stratum differences are not a causal sensor-count effect',
                             'No pooling 504 sensors as independent experimental replicates; no significance test or confidence interval',
                             'One configuration and apparatus; not proof of superiority on other systems'],
                input_sha256=sha256(a.metrics.read_bytes()).hexdigest(),script_sha256=sha256(Path(__file__).read_bytes()).hexdigest())
    (a.output/'summary.json').write_text(json.dumps(record,indent=2)+'\n')
    print(json.dumps(record,indent=2),flush=True)


if __name__=='__main__': main()
