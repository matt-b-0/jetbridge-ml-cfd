"""Report synthesis figures from saved experimental and CFD verification tables."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
import zipfile
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import TwoSlopeNorm
import numpy as np
import pandas as pd
from jetbridge_ml.cfd_interface.plot_comparison import mesh_profile
from jetbridge_ml.machine_learning.selection import select_plane_svr
from jetbridge_ml.interpolation.plane import predict_plane
from jetbridge_ml.sensor_design_study import design_indices

METHODS=['mean','nearest','linear','rbf','svr']
COLORS=['#424242','#888888','#2681a0','#d69330','#a34863']


def main():
    """Create nine captioned 300 dpi PNG/vector PDF figures without CFD solves."""
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('analysis','verification-samples','output'):
        parser.add_argument('--'+name,type=Path,required=True)
    a=parser.parse_args()
    if a.output.exists(): parser.error('Output must be new')
    a.output.mkdir(parents=True)
    paths=[a.analysis/'experimental/metrics.csv',a.analysis/'experimental/predictions.csv',
           a.analysis/'paired/paired_runs.csv',a.analysis/'matched/matched_sensor_audit.csv',
           a.analysis/'verification/mesh_metrics.csv',a.analysis/'verification/coordinate_metrics.csv',
           a.analysis/'verification/transfer_metrics.csv']
    metrics,pred,pairs,matched,mesh,coords,transfer=[pd.read_csv(p) for p in paths]
    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,'pdf.fonttype':42})
    captions=[]
    def save(fig,name,caption):
        for ext in ('png','pdf'):
            fig.savefig(a.output/f'{name}.{ext}',dpi=300,bbox_inches='tight',facecolor='white')
        plt.close(fig)
        captions.append((name,caption))
        print('Saved',name,flush=True)
    common=metrics[metrics.subset=='common_hull']
    wide=common.pivot(index='run_id',columns='method',values='rmse')
    fig,axes=plt.subplots(1,2,figsize=(11,4.5),layout='constrained')
    averages=common.groupby('method').rmse.mean().reindex(METHODS)
    axes[0].barh(METHODS,averages,color=COLORS)
    axes[0].invert_yaxis()
    axes[0].set(xlabel='Mean per-run RMSE (m/s)',title='Same supported experimental targets')
    for i,v in enumerate(averages): axes[0].text(v+.001,i,f'{v:.4f}',va='center',fontsize=8)
    axes[0].set_xlim(0,float(averages.max())*1.18)
    diffs=[(wide[m]-wide['mean']).to_numpy() for m in METHODS[1:]]
    axes[1].boxplot(diffs,showmeans=True)
    axes[1].set_xticks(np.arange(1,5),METHODS[1:])
    axes[1].axhline(0,color='black',ls='--',lw=.8)
    axes[1].set(ylabel='Method RMSE − mean-baseline RMSE (m/s)',title='Negative means better than retained-sensor mean')
    fig.suptitle('Experimental model skill | 36 runs | nested held-location evaluation')
    save(fig,'01_model_skill','Left: equal-run mean RMSE at common supported locations. Right: descriptive distribution of paired run differences against the training-only mean baseline; boxplots are not confidence intervals. Runs share one apparatus.')
    station=pred[pred.inside_hull].groupby(['station_ft','run_id','method']).error_mps.apply(lambda v:float(np.sqrt(np.mean(v**2)))).groupby(['station_ft','method']).mean().unstack('method').reindex(columns=METHODS)
    fig,ax=plt.subplots(figsize=(8,6),layout='constrained')
    image=ax.imshow(station.to_numpy(),cmap='magma_r',aspect='auto',vmin=0)
    for i in range(len(station)):
        for j in range(len(METHODS)):
            value=station.iloc[i,j]
            ax.text(j,i,f'{value:.3f}',ha='center',va='center',color='white' if value>station.to_numpy().max()*.55 else 'black',fontsize=9)
    ax.set(xticks=np.arange(5),xticklabels=METHODS,yticks=np.arange(len(station)),yticklabels=station.index,xlabel='Prediction method',ylabel='Station label (ft)',title='Where does each method perform well?')
    fig.colorbar(image,ax=ax,label='Mean per-run held-location RMSE (m/s)')
    save(fig,'02_station_error_heatmap','Errors averaged within station and replicate before station aggregation, on common supported targets. Different stations have different operating conditions; the heatmap is not a matched multi-station CFD validation.')
    fig,axes=plt.subplots(1,2,figsize=(10,4.3),layout='constrained')
    for ax,n in zip(axes,[12,24]):
        part=pairs[pairs.layout_points==n]
        ax.scatter(part.rbf_rmse,part.svr_rmse,c=part.station_ft,cmap='viridis',vmin=10,vmax=58,s=55,edgecolors='black',linewidths=.4)
        limit=max(part.rbf_rmse.max(),part.svr_rmse.max())*1.12
        ax.plot([0,limit],[0,limit],'k--',lw=.8)
        ax.set(xlabel='RBF RMSE (m/s)',ylabel='SVR RMSE (m/s)',title=f'{n}-sensor layout | {len(part)} runs',xlim=(0,limit),ylim=(0,limit))
        ax.set_aspect('equal')
    fig.suptitle('Above equality favours RBF; below favours SVR\n24-point layouts occur only at 58 ft: station and density are confounded')
    save(fig,'03_layout_stratified_comparison','Paired model errors split by source layout size. These groups were inspected after evaluation and are descriptive. Their differences cannot identify a causal effect of sensor count; all 24-point layouts are at the inlet station.')
    fig,axes=plt.subplots(1,2,figsize=(11,4.5),layout='constrained')
    for ax,inside in zip(axes,[True,False]):
        for method,color in zip(METHODS,COLORS):
            values=abs(pred[(pred.method==method)&(pred.inside_hull==inside)].error_mps.dropna().to_numpy())
            if not len(values): continue
            values=np.sort(values)
            ax.plot(values,np.arange(1,len(values)+1)/len(values),label=method,color=color)
        ax.set(xlabel='Absolute held-out error (m/s)',ylabel='Fraction of evaluated targets',title='Supported region' if inside else 'Outside training hull')
        ax.legend(fontsize=8); ax.grid(alpha=.2)
    fig.suptitle('Experimental error distributions | equal target weights, no independence assumption')
    save(fig,'04_experimental_error_distributions','Empirical target-error distributions, separate from the equal-run RMSE ranking. Dense-layout runs receive more target weight here. Linear has no outside-hull predictions; curves do not represent uncertainty or confidence intervals.')
    fig,axes=plt.subplots(1,2,figsize=(10,4.4),layout='constrained')
    obs=matched.speed_mps.to_numpy(); fitted=matched.cfd_cellPoint_speed_mps.to_numpy(); delta=fitted-obs
    image=axes[0].scatter((fitted+obs)/2,delta,c=matched.height_m,cmap='cividis',s=70,edgecolors='black',linewidths=.4)
    axes[0].axhline(delta.mean(),color='#bd4932',ls='--',label=f'Mean bias {delta.mean():+.4f} m/s')
    axes[0].axhline(0,color='black',lw=.8)
    axes[0].set(xlabel='Mean of CFD and measured speed (m/s)',ylabel='CFD − measured speed (m/s)',title='Matched 10 ft agreement diagnostic')
    axes[0].legend(fontsize=8)
    fig.colorbar(image,ax=axes[0],label='Local sensor height (m)',shrink=.7)
    axes[1].bar(matched.source_row+1,matched.cfd_cellPoint_speed_mps-matched.cfd_cell_speed_mps,color='#2681a0')
    axes[1].axhline(0,color='black',lw=.8)
    axes[1].set(xlabel='Source sensor ID',ylabel='cellPoint − cell speed (m/s)',title='Sampling-convention effect at same positions')
    save(fig,'05_matched_agreement','Only the matched isothermal 10 ft run is shown. CFD error is plotted against paired mean speed, with no normal-theory limits of agreement because the 12 spatial samples do not justify that assumption. Sampling differences are not experimental discrepancies.')
    root=Path(__file__).resolve().parents[2]
    _,zs,floors,_=mesh_profile(root/'cfd/cases/empty_bridge_s01_a_10_hn_1/system/blockMeshDict')
    samples={}
    for name in ['coarse','baseline','fine','flow80']:
        path=a.verification_samples/f'samples_{name}.csv'; paths.append(path)
        samples[name]=pd.read_csv(path)
    fig,axes=plt.subplots(1,4,figsize=(12,5),layout='constrained')
    for ax,s in zip(axes,[16,28,40,52]):
        for name,color in [('coarse','#888888'),('baseline','#2681a0'),('fine','#d69330')]:
            table=samples[name]; table=table[(table.region=='reference')&(table.station_ft==s)]
            xs=np.unique(table.x_m); x=xs[np.argmin(abs(xs-xs.mean()))]
            part=table[np.isclose(table.x_m,x,atol=1e-10)].sort_values('y_m')
            height=part.y_m-np.interp(part.z_m,zs,floors)
            ax.plot(part.speed_mps,height,label=name,color=color)
        ax.set(xlabel='Speed (m/s)',ylabel='Height above floor (m)',title=f'{s} ft | x={x:.3f} m')
        ax.legend(fontsize=8); ax.grid(alpha=.2)
    fig.suptitle('Near-midwidth profiles on three converged meshes | identical physical sample coordinates')
    save(fig,'06_mesh_height_profiles','Vertical profiles at the same near-midwidth x coordinate on three meshes. The fine solution is not exact truth; differences quantify numerical sensitivity, not experimental validation or demonstrated mesh independence.')
    fig,axes=plt.subplots(2,3,figsize=(10,9),layout='constrained')
    fields=[]; maximum_error=0; maximum_speed=0
    for name in ['baseline','flow80']:
        table=samples[name]; candidate=table[(table.region=='candidate')&(table.station_ft==16)]
        reference=table[(table.region=='reference')&(table.station_ft==16)]
        x=candidate[['x_m','y_m']].to_numpy(); q=reference[['x_m','y_m']].to_numpy()
        indices=design_indices(x,4,6,'hybrid')
        model,_,_,_=select_plane_svr(x[indices],candidate.speed_mps.to_numpy()[indices])
        scaler=model.named_steps['standardscaler']
        rbf=predict_plane('rbf',scaler.transform(x[indices]),candidate.speed_mps.to_numpy()[indices],scaler.transform(q))
        svr=model.predict(q); target=reference.speed_mps.to_numpy()
        arrays=[target,rbf-target,svr-target]
        maximum_error=max(maximum_error,float(max(abs(arrays[1]).max(),abs(arrays[2]).max())))
        maximum_speed=max(maximum_speed,float(target.max()))
        fields.append((name,reference,candidate.iloc[indices],arrays))
    for row,(name,reference,selection,arrays) in enumerate(fields):
        h=reference.y_m-np.interp(reference.z_m,zs,floors)
        for col,values in enumerate(arrays):
            ax=axes[row,col]
            xx=reference.x_m.to_numpy().reshape(60,40); yy=h.to_numpy().reshape(60,40)
            image=ax.pcolormesh(xx,yy,values.reshape(60,40),shading='nearest',cmap='viridis' if col==0 else 'RdBu_r',
                                norm=plt.Normalize(0,maximum_speed) if col==0 else TwoSlopeNorm(vmin=-maximum_error,vcenter=0,vmax=maximum_error),rasterized=True)
            ax.set_aspect('equal'); ax.set(xlabel='x (m)',ylabel='Height above floor (m)',title=name+' | '+['CFD speed','RBF − CFD','SVR − CFD'][col])
            if col==0:
                ax.scatter(selection.x_m,selection.y_m-np.interp(selection.z_m,zs,floors),s=13,facecolors='none',edgecolors='white')
            fig.colorbar(image,ax=ax,label='m/s',shrink=.7)
    fig.suptitle('Fixed 24-sensor hybrid layout at 16 ft | models refitted on retained values\nNumerical reconstruction only; common error scale across both flow cases')
    save(fig,'07_flow_transfer_error_maps','CFD speed and reconstruction differences on the 16 ft plane at baseline and synthetic 80% flow. White circles mark retained virtual sensors. SVR selection uses only retained values. This tests fixed-layout transfer with refitted models, not a frozen surrogate or experimental validation.')
    fig,axes=plt.subplots(1,2,figsize=(10,4.5),layout='constrained')
    for ax,method in zip(axes,['rbf','svr']):
        part=transfer[(transfer.method==method)&(transfer.subset=='full_section')]
        pivot=part.pivot(index=['case','station_ft'],columns='placement',values='rmse')
        for name,color in [('baseline','#2681a0'),('flow80','#bd4932')]:
            section=pivot.loc[name]
            gain=100*(section.interior-section.hybrid)/section.interior
            ax.plot(gain.index,gain,'o-',label=name,color=color)
        ax.axhline(0,color='black',lw=.8)
        ax.set(xlabel='Station label (ft)',ylabel='RMSE reduction from interior to hybrid (%)',title=method.upper())
        ax.legend(fontsize=8); ax.grid(alpha=.2)
    fig.suptitle('Fixed-layout benefit by plane | positive means lower full-section numerical error')
    save(fig,'08_layout_transfer_gain','Relative reductions compare the same number of sensors and same evaluation grid within each flow/plane. Results are limited to one geometry, one turbulence model and a controlled 80% flow perturbation; not broad physical generalisation.')
    thermal_path=a.analysis/'thermal/audit.json'; paths.append(thermal_path)
    thermal=json.loads(thermal_path.read_text())
    fig,axes=plt.subplots(1,2,figsize=(11,4.5),layout='constrained')
    keys=['original_restart','continuation']
    screen_keys=['mesh_check_passed','solver_reported_convergence','residual_screen_passed','stationarity_screen_passed','flux_screen_passed','temperature_boundary_screen_passed']
    names=['Mesh check','Solver convergence','Residual screen','Probe stationarity','Flux screen','Temperature bounds']
    from matplotlib.colors import ListedColormap
    matrix=np.array([[thermal[key][screen] for key in keys] for screen in screen_keys],int)
    axes[0].imshow(matrix,cmap=ListedColormap(['#d69330','#2681a0']),vmin=0,vmax=1,aspect='auto')
    for i in range(6):
        for j in range(2): axes[0].text(j,i,'PASS' if matrix[i,j] else 'FAIL',ha='center',va='center',color='white',weight='bold')
    axes[0].set(yticks=np.arange(6),yticklabels=names,xticks=[0,1],xticklabels=['Original restart\nlog ends at 1000','Continuation\nlog ends at 1967'],title='Separate numerical checks')
    for key,color in zip(keys,['#888888','#a34863']):
        record=thermal[key]
        ratios=[record['last_initial_residuals'][f]/record['residual_thresholds'][f] for f in ['p_rgh','Uz','T','k']]
        ratios.append(record['maximum_probe_temperature_range_K']/record['stationarity_screen_K'])
        axes[1].semilogy(np.arange(5),ratios,'o-',label=key.replace('_',' '),color=color)
    axes[1].axhline(1,color='black',ls='--',lw=.8,label='Screen threshold')
    axes[1].set(xticks=np.arange(5),xticklabels=['p_rgh','Uz','T','k','Probe range'],ylabel='Recorded value / screen threshold',title='Above 1 fails the stated screen')
    axes[1].legend(fontsize=8); axes[1].grid(alpha=.2)
    fig.suptitle('Thermal cases remain NOT CONVERGED | balanced flux does not imply a settled solution')
    save(fig,'09_thermal_numerical_screens','Numerical screens at the ends of the two logs. Original log ends at 1000 but its latest saved field is 967; continuation ends and saves at 1967. Temperature range uses each log-end 100-iteration probe window. Threshold-normalised quantities are diagnostic ratios, not uncertainties or physical validation metrics.')
    manifest=dict(figures=len(captions),input_sha256={str(p):sha256(p.read_bytes()).hexdigest() for p in paths},script_sha256=sha256(Path(__file__).read_bytes()).hexdigest(),
                  note='No CFD solves or experimental model retraining; fixed-layout CFD reconstructions are refitted using training-only selection')
    (a.output/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    lines=['# Additional report figures','','Nine PNG/PDF figures. Use PDF for report linework and PNG for slides. Error plots retain their reference-data and coverage distinctions.','']
    for name,caption in captions:
        lines.extend(['## '+name,'',caption,'',f'![{name}]({name}.png)','',f'[PDF]({name}.pdf)',''])
    (a.output/'README.md').write_text('\n'.join(lines)+'\n')
    fig,axes=plt.subplots(3,3,figsize=(15,12),layout='constrained')
    for ax,(name,_) in zip(axes.flat,captions):
        ax.imshow(plt.imread(a.output/f'{name}.png')); ax.axis('off'); ax.set_title(name.replace('_',' '),fontsize=8)
    fig.savefig(a.output/'00_overview.png',dpi=160,facecolor='white'); plt.close(fig)
    with zipfile.ZipFile(a.output/'additional_report_figures.zip','w',zipfile.ZIP_DEFLATED) as archive:
        for p in sorted(a.output.iterdir()):
            if p.suffix in ('.png','.pdf','.json','.md'): archive.write(p,p.name)


if __name__=='__main__': main()
