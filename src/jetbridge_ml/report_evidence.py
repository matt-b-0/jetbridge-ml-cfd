"""Additional spatial, selection and repeatability diagnostics for the report."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import Normalize, TwoSlopeNorm
import numpy as np
import pandas as pd
from scipy.spatial import ConvexHull,Delaunay
from jetbridge_ml.cfd_interface.plot_comparison import mesh_profile
from jetbridge_ml.controlled_performance import fit_predictor
from jetbridge_ml.machine_learning.selection import select_plane_svr


def hull_area_fraction(coordinates,width,height):
    """Return planar convex-hull area divided by physical section area.

    Parameters
    ----------
    coordinates : array-like
        Noncollinear sensor positions in metres, shape (n, 2).
    width, height : float
        Positive physical rectangular section dimensions in metres.

    Returns
    -------
    float
        Geometric area fraction, unrelated to held-target support fraction.
    """
    return float(ConvexHull(np.asarray(coordinates)).volume/(width*height))


def main():
    """Generate diagnostics without changing the original outer evaluation."""
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--analysis',type=Path,required=True)
    p.add_argument('--performance',type=Path,required=True)
    p.add_argument('--mesh',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--draws',type=int,default=200)
    a=p.parse_args()
    if a.output.exists() or a.draws<20:p.error('Choose a fresh output and at least 20 draws')
    a.output.mkdir(parents=True)
    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,'pdf.fonttype':42})
    def save(fig,name):
        for ext in ('png','pdf'):fig.savefig(a.output/f'{name}.{ext}',dpi=300,bbox_inches='tight',facecolor='white')
        plt.close(fig)
    predictions=pd.read_csv(a.analysis/'experimental/predictions.csv')
    observed=predictions[predictions.method=='svr'].copy()
    common=observed[observed.inside_hull]
    summary={'evaluated_speed_quartiles_mps':dict(zip(['q25','median','q75'],common.speed_mps.quantile([.25,.5,.75]).tolist()))}
    selected=observed.groupby(['C','gamma','epsilon']).size().reset_index(name='outer_folds')
    selected.to_csv(a.output/'selected_parameter_frequency.csv',index=False)
    summary['selection_n_outer_folds']=len(observed)
    summary['C_counts']=observed.C.value_counts().sort_index().to_dict()
    summary['gamma_counts']=observed.gamma.value_counts().sort_index().to_dict()
    summary['epsilon_counts']=observed.epsilon.value_counts().sort_index().to_dict()
    search=pd.read_csv(a.analysis/'experimental/search.csv')
    spread=search.groupby(['run_id','outer_source_row']).cv_rmse.agg(['min','max'])
    summary['median_grid_cv_rmse_spread_mps']=float((spread['max']-spread['min']).median())
    audit=pd.read_csv(a.analysis/'experimental/nested_split_audit.csv')
    audit['inner_n_train']=audit.training_indices.str.split(';').str.len()
    audit['inner_n_validation']=audit.validation_indices.str.split(';').str.len()
    summary['inner_train_sizes']=sorted(map(int,audit.inner_n_train.unique()))
    summary['inner_validation_sizes']=sorted(map(int,audit.inner_n_validation.unique()))
    fig,ax=plt.subplots(figsize=(6.7,2.6),layout='constrained')
    labels=[f'C={r.C:g}, γ={r.gamma:g}\nε={r.epsilon:g}' for r in selected.itertuples()]
    ax.bar(range(len(selected)),selected.outer_folds,color='#a34863');ax.set_xticks(range(len(selected)),labels,fontsize=8)
    ax.set(ylabel='Selected outer folds',title='Training-only SVR parameter selection');save(fig,'parameter_selection')
    width,zs,floors,tops=mesh_profile(a.mesh)
    coverage=[]
    for run,t in observed.groupby('run_id'):
        z=float(t.z_m.iloc[0]);height=float(np.interp(z,zs,tops)-np.interp(z,zs,floors))
        xy=t[['x_m','y_m']].to_numpy()
        outer=[hull_area_fraction(np.delete(xy,i,axis=0),width,height) for i in range(len(xy))]
        coverage.append(dict(run_id=run,sensors=len(t),full_array_hull_area_fraction=hull_area_fraction(xy,width,height),outer_hull_min=min(outer),outer_hull_max=max(outer)))
    pd.DataFrame(coverage).to_csv(a.output/'physical_hull_coverage.csv',index=False)
    t=observed[observed.run_id=='S01-A-10-HN-1'].sort_values('source_row')
    x=t[['x_m','y_m']].to_numpy();y=t.speed_mps.to_numpy();z=float(t.z_m.iloc[0])
    floor=float(np.interp(z,zs,floors));height=float(np.interp(z,zs,tops)-floor)
    gx,gy=np.meshgrid(np.linspace(0,width,50),np.linspace(floor,floor+height,70));q=np.c_[gx.ravel(),gy.ravel()]
    model,params,_,_=select_plane_svr(x,y)
    fields={'rbf':fit_predictor('rbf',x,y,params)(q),'svr':model.predict(q)}
    inside=Delaunay(x).find_simplex(q,tol=1e-10)>=0
    summary['illustrative_refit_parameters']=params
    summary['illustrative_hull_area_fraction']=hull_area_fraction(x,width,height)
    summary['experimental_field_range_mps']={m:dict(min=float(v.min()),max=float(v.max()),inside_min=float(v[inside].min()),inside_max=float(v[inside].max()),negative=int((v<0).sum())) for m,v in fields.items()}
    lo=min(y.min(),*(v.min() for v in fields.values()));hi=max(y.max(),*(v.max() for v in fields.values()))
    norm=Normalize(lo,hi)
    fig,axes=plt.subplots(1,4,figsize=(7.5,3.4),layout='constrained')
    axes[0].scatter(x[:,0],x[:,1]-floor,c=y,norm=norm,cmap='viridis',s=35,edgecolor='black',linewidth=.4)
    for ax,m in zip(axes[1:3],('rbf','svr')):
        im=ax.pcolormesh(gx,gy-floor,fields[m].reshape(gx.shape),norm=norm,cmap='viridis',shading='auto',rasterized=True)
        ax.contour(gx,gy-floor,inside.reshape(gx.shape),levels=[.5],colors='white',linewidths=.9)
        ax.scatter(x[:,0],x[:,1]-floor,s=6,c='black')
    fig.colorbar(plt.cm.ScalarMappable(norm=norm,cmap='viridis'),ax=axes[:3],label='Speed (m/s)',shrink=.8)
    errors=predictions[(predictions.run_id==t.run_id.iloc[0])&predictions.method.isin(['rbf','svr'])]
    limit=float(errors.error_mps.abs().max());enorm=TwoSlopeNorm(vcenter=0,vmin=-limit,vmax=limit)
    for m,dx,marker in [('rbf',-.035,'o'),('svr',.035,'s')]:
        e=errors[errors.method==m];axes[3].scatter(e.x_m+dx,e.y_m-floor,c=e.error_mps,norm=enorm,cmap='coolwarm',s=28,marker=marker,label=m.upper(),edgecolor='black',linewidth=.3)
    fig.colorbar(plt.cm.ScalarMappable(norm=enorm,cmap='coolwarm'),ax=axes[3],label='LOLO residual (m/s)',shrink=.8)
    for ax,title in zip(axes,['A\nMeasurements','B\nRBF refit','C\nSVR refit','D\nHeld-out errors']):
        ax.set(xlim=(0,width),ylim=(0,height),xlabel='x (m)');ax.set_title(title,fontsize=9);ax.set_aspect('equal')
    axes[0].set_ylabel('Local height (m)');save(fig,'experimental_reconstruction')
    # Numerical reference study: saved predictions only, no refitting on dense truth.
    dense=pd.read_csv(a.analysis/'sensor_design/predictions.csv.gz')
    dense=dense[(dense.station_ft==28)&(dense.sensors==24)&(dense.placement=='hybrid')&dense.method.isin(['rbf','svr'])]
    layout=pd.read_csv(a.analysis/'sensor_design/sensor_layouts.csv')
    layout=layout[(layout.station_ft==28)&(layout.sensors==24)&(layout.placement=='hybrid')]
    fig,axes=plt.subplots(1,5,figsize=(7.7,3.3),layout='constrained')
    ref=dense[dense.method=='rbf'].sort_values(['y_m','x_m']);fy=float(np.interp(ref.z_m.iloc[0],zs,floors))
    vmax=max(dense.speed_mps.max(),dense.prediction_mps.max());norm=Normalize(0,vmax)
    errmax=float((dense.prediction_mps-dense.speed_mps).abs().max());enorm=TwoSlopeNorm(vcenter=0,vmin=-errmax,vmax=errmax)
    for ax,kind,m,title in zip(axes,['reference','prediction','prediction','error','error'],['rbf','rbf','svr','rbf','svr'],['CFD reference','RBF','SVR','RBF error','SVR error']):
        part=dense[dense.method==m].sort_values(['y_m','x_m']);xx=np.sort(part.x_m.unique());yy=np.sort(part.y_m.unique())
        vals=part.speed_mps if kind=='reference' else part.prediction_mps if kind=='prediction' else part.prediction_mps-part.speed_mps
        ax.pcolormesh(xx,yy-fy,vals.to_numpy().reshape(len(yy),len(xx)),shading='auto',norm=enorm if kind=='error' else norm,cmap='coolwarm' if kind=='error' else 'viridis',rasterized=True)
        ax.scatter(layout.x_m,layout.y_m-fy,c='black',s=3);ax.set(title=title,xlabel='x (m)');ax.set_aspect('equal')
    axes[0].set_ylabel('Local height (m)');fig.colorbar(plt.cm.ScalarMappable(norm=norm,cmap='viridis'),ax=axes[:3],label='Speed (m/s)',shrink=.8)
    fig.colorbar(plt.cm.ScalarMappable(norm=enorm,cmap='coolwarm'),ax=axes[3:],label='Error (m/s)',shrink=.8);save(fig,'cfd_reconstruction')
    summary['cfd_example']={m:dict(rmse=float(np.sqrt(np.mean((d.prediction_mps-d.speed_mps)**2))),max_abs_error=float((d.prediction_mps-d.speed_mps).abs().max())) for m,d in dense.groupby('method')}
    # Across-run variation is empirical condition/replicate variation, not instrument uncertainty.
    rep=observed[observed.station_ft==10].pivot(index='source_row',columns='run_id',values='speed_mps')
    sd=rep.std(axis=1,ddof=1).reindex(t.source_row).to_numpy()
    variation=pd.DataFrame(dict(source_row=t.source_row.to_numpy(),mean_across_replicates_mps=rep.mean(axis=1).reindex(t.source_row).to_numpy(),sd_across_replicates_mps=sd))
    variation.to_csv(a.output/'observed_replicate_variation.csv',index=False)
    summary['variation_n_runs']=rep.shape[1];summary['variation_sd_range_mps']=[float(sd.min()),float(sd.max())]
    # Centred independent Gaussian scenario; freeze selected full-data parameters.
    rng=np.random.default_rng(20261025);records=[]
    for draw in range(a.draws):
        delta=rng.normal(size=len(y))*sd
        for m in ('rbf','svr'):
            perturbed=fit_predictor(m,x,y+delta,params)(q)-fields[m]
            for region,mask in [('inside',inside),('outside',~inside)]:
                records.append(dict(draw=draw,method=m,region=region,field_change_rms_mps=float(np.sqrt(np.mean(perturbed[mask]**2))),max_abs_change_mps=float(np.max(np.abs(perturbed[mask])))))
    changes=pd.DataFrame(records);changes.to_csv(a.output/'perturbation_trials.csv',index=False)
    changes.groupby(['method','region']).field_change_rms_mps.quantile([.25,.5,.75]).unstack().to_csv(a.output/'perturbation_summary.csv')
    fig,ax=plt.subplots(figsize=(6.5,2.7),layout='constrained');labels=[];series=[]
    for m in ('rbf','svr'):
        for region in ('inside','outside'):
            labels.append(f'{m.upper()}\n{region} hull');series.append(changes[(changes.method==m)&(changes.region==region)].field_change_rms_mps)
    ax.boxplot(series,tick_labels=labels,showfliers=False);ax.set(ylabel='RMS change in field (m/s)',title=f'Observed-variation scenario: {a.draws} perturbations, fixed parameters');save(fig,'empirical_perturbation')
    matched=pd.read_csv(a.analysis/'matched/matched_sensor_audit.csv')
    fig,ax=plt.subplots(figsize=(6.5,3),layout='constrained')
    ax.errorbar(matched.speed_mps,matched.cfd_cellPoint_speed_mps,xerr=matched.raw_speed_std_mps,fmt='o',ms=4,capsize=2,label='Mean ± time-series SD (not SEM)')
    ax.plot([.04,.21],[.04,.21],'k--',lw=.8,label='Equality');ax.set(xlabel='Measured mean speed (m/s)',ylabel='CFD speed (m/s)',title='Matched 10 ft run with observed temporal variation');ax.legend(fontsize=8);save(fig,'matched_with_variation')
    summary['matched_temporal_sd_range_mps']=[float(matched.raw_speed_std_mps.min()),float(matched.raw_speed_std_mps.max())]
    timings=pd.read_csv(a.performance/'repeated_timings.csv')
    # Two distinct variability sources: repetition within a run, and differences across runs.
    within=timings.groupby(['training_sensors','method','run_id'])[['fit_ms','dense_2400_ms']].quantile([.25,.5,.75]).unstack()
    rows=[]
    for (n,m),part in within.groupby(level=[0,1]):
        row=dict(training_sensors=int(n),method=m)
        for metric in ('fit_ms','dense_2400_ms'):
            row.update({f'{metric}_{name}':float(part[(metric,q)].median()) for name,q in [('q25',.25),('median',.5),('q75',.75)]})
        rows.append(row)
    pd.DataFrame(rows).to_csv(a.output/'timing_repeatability.csv',index=False)
    for name,data in [('experimental_refit_fields',pd.DataFrame(dict(x_m=q[:,0],y_m=q[:,1],inside_hull=inside,rbf_mps=fields['rbf'],svr_mps=fields['svr']))),('experimental_heldout_errors',errors),('cfd_example_predictions',dense),('cfd_example_layout',layout)]:data.to_csv(a.output/f'{name}.csv',index=False)
    paths=[a.analysis/'experimental/predictions.csv',a.analysis/'experimental/search.csv',a.analysis/'sensor_design/predictions.csv.gz',a.performance/'repeated_timings.csv',a.mesh]
    summary['manifest']={'input_sha256':{str(v):sha256(v.read_bytes()).hexdigest() for v in paths},'script_sha256':sha256(Path(__file__).read_bytes()).hexdigest(),'perturbation_seed':20261025,'draws':a.draws,'perturbation_assumptions':'Across-replicate SD; independent centred Gaussian scenario; fixed full-data SVR parameters; no measurement-uncertainty or robustness ranking claim'}
    (a.output/'evidence.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps(summary,indent=2))


if __name__=='__main__':main()
