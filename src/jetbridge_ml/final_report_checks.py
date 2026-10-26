"""Coverage-visible report fields and an exploratory lower-C nested sensitivity."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import Normalize,TwoSlopeNorm
import numpy as np
import pandas as pd
from scipy.spatial import ConvexHull,Delaunay
from jetbridge_ml.cfd_interface.plot_comparison import mesh_profile
from jetbridge_ml.controlled_performance import fit_predictor
from jetbridge_ml.machine_learning.selection import select_plane_svr

EXTENDED_GRID=dict(C=[.01,.1,1.,10.],gamma=[.1,1.],epsilon=[.002,.01])


def extended_outer_prediction(frame,heldout):
    """Select the expanded grid with the outer sensor target excluded.

    Parameters
    ----------
    frame : pandas.DataFrame
        One independently fitted replicate with unique positions and speeds.
    heldout : int
        Positional row index withheld before parameter selection.

    Returns
    -------
    tuple
        Held-out prediction, selected parameters, inner search and split audit.
    """
    retained=frame.drop(frame.index[heldout])
    model,params,search,audit=select_plane_svr(retained[['x_m','y_m']].to_numpy(),retained.speed_mps.to_numpy(),grid=EXTENDED_GRID)
    prediction=float(model.predict(frame.iloc[[heldout]][['x_m','y_m']].to_numpy())[0])
    audit['outer_training_source_rows']=';'.join(map(str,retained.source_row))
    return prediction,params,search,audit


def _save(fig,out,name):
    for ext in ('png','pdf'):fig.savefig(out/f'{name}.{ext}',dpi=300,bbox_inches='tight',facecolor='white')
    plt.close(fig)


def main():
    """Generate declared diagnostic figures and keep primary scores unchanged."""
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--predictions',type=Path,required=True)
    p.add_argument('--evidence',type=Path,required=True)
    p.add_argument('--mesh',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    if a.output.exists():p.error('Choose a fresh output directory')
    a.output.mkdir(parents=True)
    plt.rcParams.update({'font.size':11,'axes.spines.top':False,'axes.spines.right':False,'pdf.fonttype':42,'hatch.linewidth':.45})
    pred=pd.read_csv(a.predictions);observed=pred[pred.method=='svr'].copy()
    width,zs,floors,tops=mesh_profile(a.mesh);summary={}
    for station in (10,58):
        run=f'S01-A-{station}-HN-1';t=observed[observed.run_id==run].sort_values('source_row')
        xy=t[['x_m','y_m']].to_numpy();y=t.speed_mps.to_numpy();z=float(t.z_m.iloc[0])
        floor=float(np.interp(z,zs,floors));height=float(np.interp(z,zs,tops)-floor)
        gx,gy=np.meshgrid(np.linspace(0,width,60),np.linspace(floor,floor+height,90));q=np.c_[gx.ravel(),gy.ravel()]
        model,params,_,_=select_plane_svr(xy,y)
        fields={'rbf':fit_predictor('rbf',xy,y,params)(q),'svr':model.predict(q)}
        inside=Delaunay(xy).find_simplex(q,tol=1e-10)>=0
        coverage=float(ConvexHull(xy).volume/(width*height))
        norm=Normalize(min(y.min(),*(v.min() for v in fields.values())),max(y.max(),*(v.max() for v in fields.values())))
        errors=pred[(pred.run_id==run)&pred.method.isin(['rbf','svr'])]
        limit=float(errors.error_mps.abs().max());enorm=TwoSlopeNorm(vcenter=0,vmin=-limit,vmax=limit)
        fig,axes=plt.subplots(1,4,figsize=(7.6,4.15),layout='constrained')
        axes[0].scatter(xy[:,0],xy[:,1]-floor,c=y,norm=norm,cmap='viridis',s=24,edgecolor='black',linewidth=.35)
        for ax,m in zip(axes[1:3],('rbf','svr')):
            ax.pcolormesh(gx,gy-floor,fields[m].reshape(gx.shape),norm=norm,cmap='viridis',shading='auto',rasterized=True)
            ax.contourf(gx,gy-floor,(~inside).reshape(gx.shape).astype(float),levels=[.5,1.5],colors=['white'],alpha=.42,hatches=['////'])
            ax.contour(gx,gy-floor,inside.reshape(gx.shape),levels=[.5],colors='black',linewidths=.8)
            ax.scatter(xy[:,0],xy[:,1]-floor,s=4,c='black')
        for m,dx,marker in [('rbf',-.025,'o'),('svr',.025,'s')]:
            e=errors[errors.method==m];axes[3].scatter(e.x_m+dx,e.y_m-floor,c=e.error_mps,norm=enorm,cmap='coolwarm',s=22,marker=marker,edgecolor='black',linewidth=.3)
        for ax,title in zip(axes,['A\nMeasurements','B\nRBF refit','C\nSVR refit','D\nHeld-out errors']):
            ax.set(xlim=(0,width),ylim=(0,height),xlabel='x (m)');ax.set_title(title,fontsize=10);ax.set_aspect('equal')
        axes[0].set_ylabel('Local height (m)')
        fig.colorbar(plt.cm.ScalarMappable(norm=norm,cmap='viridis'),ax=axes[:3],label='Speed (m/s)',orientation='horizontal',shrink=.86,pad=.03)
        bar=fig.colorbar(plt.cm.ScalarMappable(norm=enorm,cmap='coolwarm'),ax=axes[3],label='Residual (m/s)',orientation='horizontal',shrink=.9,pad=.03,ticks=[-limit,0,limit])
        bar.ax.set_xticklabels([f'{-limit:.2f}','0',f'{limit:.2f}'],fontsize=8)
        fig.suptitle(f'{station} ft | physical hull area {coverage:.1%}\nHatched region = extrapolation outside the full sensor hull',fontsize=11)
        _save(fig,a.output,f'experimental_{station}ft_coverage')
        records=[]
        for m,e in errors.groupby('method'):
            supported=e[e.inside_hull];worst=supported.loc[supported.error_mps.abs().idxmax()]
            records.append(dict(method=m,supported_rmse_mps=float(np.sqrt(np.mean(supported.error_mps**2))),max_supported_abs_error_mps=float(supported.error_mps.abs().max()),worst_x_m=float(worst.x_m),worst_local_height_m=float(worst.y_m-floor),worst_observed_speed_mps=float(worst.speed_mps),worst_prediction_mps=float(worst.prediction_mps),full_field_min=float(fields[m].min()),full_field_max=float(fields[m].max())))
        summary[str(station)]=dict(run=run,full_refit_params=params,hull_area_fraction=coverage,diagnostics=records)
        errors.to_csv(a.output/f'heldout_errors_{station}ft.csv',index=False)
        pd.DataFrame(dict(x_m=q[:,0],height_m=q[:,1]-floor,inside_hull=inside,rbf_mps=fields['rbf'],svr_mps=fields['svr'])).to_csv(a.output/f'fields_{station}ft.csv',index=False)
    # Re-layout the existing, already evaluated numerical example; no new fit.
    dense=pd.read_csv(a.evidence/'cfd_example_predictions.csv');layout=pd.read_csv(a.evidence/'cfd_example_layout.csv')
    fy=float(np.interp(dense.z_m.iloc[0],zs,floors));vmax=max(dense.speed_mps.max(),dense.prediction_mps.max())
    norm=Normalize(0,vmax);errmax=float((dense.prediction_mps-dense.speed_mps).abs().max());enorm=TwoSlopeNorm(vcenter=0,vmin=-errmax,vmax=errmax)
    fig,axes=plt.subplots(2,3,figsize=(7.6,5.3),layout='constrained')
    for ax,kind,m,title in zip(axes.ravel()[:5],['reference','prediction','prediction','error','error'],['rbf','rbf','svr','rbf','svr'],['CFD reference','RBF reconstruction','SVR reconstruction','RBF error','SVR error']):
        part=dense[dense.method==m].sort_values(['y_m','x_m']);xx=np.sort(part.x_m.unique());yy=np.sort(part.y_m.unique())
        vals=part.speed_mps if kind=='reference' else part.prediction_mps if kind=='prediction' else part.prediction_mps-part.speed_mps
        ax.pcolormesh(xx,yy-fy,vals.to_numpy().reshape(len(yy),len(xx)),shading='auto',norm=enorm if kind=='error' else norm,cmap='coolwarm' if kind=='error' else 'viridis',rasterized=True)
        ax.scatter(layout.x_m,layout.y_m-fy,c='black',s=5);ax.set(title=title,xlabel='x (m)',ylabel='Local height (m)');ax.set_aspect('equal')
    axes[1,2].axis('off');axes[1,2].text(.03,.95,'28 ft numerical example\n24 hybrid virtual sensors\n\nBlack dots = training\nError = prediction − CFD\n\nRBF RMSE 0.02331 m/s\nSVR RMSE 0.02515 m/s',transform=axes[1,2].transAxes,va='top',fontsize=10)
    fig.colorbar(plt.cm.ScalarMappable(norm=norm,cmap='viridis'),ax=list(axes[0]),label='Speed (m/s)',shrink=.85)
    fig.colorbar(plt.cm.ScalarMappable(norm=enorm,cmap='coolwarm'),ax=list(axes[1,:2]),label='Error (m/s)',shrink=.85)
    _save(fig,a.output,'cfd_reconstruction_large')
    trials=pd.read_csv(a.evidence/'perturbation_trials.csv')
    fig,ax=plt.subplots(figsize=(6.7,3.5),layout='constrained')
    labels=[];series=[]
    for m in ('rbf','svr'):
        for region in ('inside','outside'):
            labels.append(f'{m.upper()}\n{region} hull')
            series.append(trials[(trials.method==m)&(trials.region==region)].field_change_rms_mps)
    ax.boxplot(series,tick_labels=labels,showfliers=False)
    ax.set(ylabel='RMS change in field (m/s)',title='Declared independent Gaussian perturbation scenario')
    _save(fig,a.output,'perturbation_large')
    # Preserve all original scores and report the grid extension separately.
    out=[];searches=[];audits=[]
    for run,frame in observed.groupby('run_id',sort=True):
        frame=frame.sort_values('source_row').reset_index(drop=True)
        for heldout in range(len(frame)):
            value,params,search,audit=extended_outer_prediction(frame,heldout)
            row=frame.iloc[heldout].to_dict();row.update(original_prediction_mps=row['prediction_mps'],prediction_mps=value,**params)
            row['error_mps']=value-row['speed_mps'];out.append(row)
            for table in (search,audit):table['run_id']=run;table['outer_source_row']=int(frame.source_row.iloc[heldout])
            searches.append(search);audits.append(audit)
        print('Expanded nested sensitivity',run,flush=True)
    extended=pd.DataFrame(out);extended.to_csv(a.output/'expanded_predictions.csv',index=False)
    pd.concat(searches).to_csv(a.output/'expanded_search.csv',index=False);pd.concat(audits).to_csv(a.output/'expanded_split_audit.csv',index=False)
    metrics=[]
    for run,t in extended.groupby('run_id'):
        for subset,mask in [('common_hull',t.inside_hull),('outside_hull',~t.inside_hull)]:
            d=t[mask]
            metrics.append(dict(run_id=run,sensors=len(t),subset=subset,original_rmse=float(np.sqrt(np.mean((d.original_prediction_mps-d.speed_mps)**2))),expanded_rmse=float(np.sqrt(np.mean(d.error_mps**2)))))
    metrics=pd.DataFrame(metrics);metrics.to_csv(a.output/'expanded_metrics.csv',index=False)
    extended.groupby(['C','gamma','epsilon']).size().to_csv(a.output/'expanded_choices.csv',header=['outer_folds'])
    summary['expanded_grid']=EXTENDED_GRID;summary['expanded_C_counts']=extended.C.value_counts().sort_index().to_dict()
    summary['expanded_summary']=metrics.groupby('subset')[['original_rmse','expanded_rmse']].mean().to_dict('index')
    summary['expanded_by_layout']=metrics[metrics.subset=='common_hull'].groupby('sensors')[['original_rmse','expanded_rmse']].mean().to_dict('index')
    summary['classification']='Post-hoc exploratory grid sensitivity requested after inspecting primary results; primary scores and conclusions retained; outer held-out target excluded from every inner selection.'
    summary['sha256']={str(v):sha256(v.read_bytes()).hexdigest() for v in [a.predictions,a.evidence/'cfd_example_predictions.csv',a.mesh]}
    summary['script_sha256']=sha256(Path(__file__).read_bytes()).hexdigest()
    (a.output/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps(summary,indent=2))


if __name__=='__main__':main()
