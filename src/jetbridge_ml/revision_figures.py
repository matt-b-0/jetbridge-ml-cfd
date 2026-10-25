"""Simplified report figures and a geometry-only scaled interpolation sensitivity."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
from jetbridge_ml.cfd_interface.plot_comparison import mesh_profile
from jetbridge_ml.interpolation.sensitivity import interpolation_noise_gain


def main():
    """Create legible single-purpose figures without changing predictive evaluation."""
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--analysis',type=Path,required=True)
    p.add_argument('--mesh',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    if a.output.exists(): p.error('New output required')
    a.output.mkdir(parents=True)
    plt.rcParams.update({'font.size':11,'axes.spines.top':False,'axes.spines.right':False,'pdf.fonttype':42})
    width,zs,floors,tops=mesh_profile(a.mesh)
    pred=pd.read_csv(a.analysis/'experimental/predictions.csv')
    sensors=pred[(pred.run_id=='S01-A-10-HN-1')&(pred.method=='rbf')].sort_values('source_row')
    def save(fig,name):
        for ext in ('png','pdf'):fig.savefig(a.output/f'{name}.{ext}',dpi=300,bbox_inches='tight',facecolor='white')
        plt.close(fig)
    fig,axes=plt.subplots(1,2,figsize=(7,2.8),layout='constrained',gridspec_kw={'width_ratios':[2.2,1]})
    axes[0].plot(zs,floors,'k-',lw=1.5);axes[0].plot(zs,tops,'k-',lw=1.5)
    axes[0].fill_between(zs,floors,tops,color='#e6edf2')
    stations=sorted(pred[['station_ft','z_m']].drop_duplicates().itertuples(index=False))
    for s,z in stations:axes[0].axvline(z,color='#2681a0',alpha=.35,lw=.8)
    axes[0].annotate('Supply',xy=(17.5,2.2),xytext=(14,2.2),arrowprops={'arrowstyle':'<-','color':'#bd4932'},color='#bd4932')
    axes[0].set(xlabel='z along bridge (m)',ylabel='Absolute y (m)',xlim=(0,zs[-1]),ylim=(0,4),title='Piecewise sloped bridge')
    floor=np.interp(3.05,zs,floors);height=np.interp(3.05,zs,tops)-floor
    axes[1].scatter(sensors.x_m,sensors.y_m-floor,s=20,color='#2681a0')
    axes[1].set(xlabel='x (m)',ylabel='Local height (m)',xlim=(0,width),ylim=(0,height),title='10 ft sensors')
    axes[1].set_aspect('equal')
    save(fig,'geometry_compact')
    pairs=pd.read_csv(a.analysis/'paired/paired_runs.csv')
    summary=pairs.groupby('station_ft').rbf_minus_svr_mps.mean()
    fig,ax=plt.subplots(figsize=(6.5,2.8),layout='constrained')
    ax.bar(summary.index.astype(str),summary,color=np.where(summary<0,'#d69330','#a34863'))
    ax.axhline(0,color='black',lw=.8)
    ax.set(xlabel='Station label (ft)',ylabel='RBF RMSE − SVR RMSE (m/s)',title='Negative favours RBF; positive favours SVR')
    ax.grid(axis='y',alpha=.2)
    save(fig,'paired_station_compact')
    matched=pd.read_csv(a.analysis/'matched/matched_sensor_audit.csv')
    fig,ax=plt.subplots(figsize=(6.2,3),layout='constrained')
    image=ax.scatter(matched.speed_mps,matched.cfd_cellPoint_speed_mps,c=matched.height_m,cmap='cividis',s=55,edgecolors='black',linewidths=.4)
    ax.plot([.08,.19],[.08,.19],'k--',lw=.9,label='Equality')
    ax.set(xlabel='Measured mean speed (m/s)',ylabel='CFD speed magnitude (m/s)',title='Matched 10 ft comparison',xlim=(.08,.19),ylim=(.08,.19))
    ax.legend(fontsize=9);ax.grid(alpha=.2)
    fig.colorbar(image,ax=ax,label='Local height (m)',shrink=.85)
    save(fig,'matched_parity_compact')
    transfer=pd.read_csv(a.analysis/'verification/transfer_metrics.csv')
    values=transfer[(transfer.subset=='full_section')&transfer.method.isin(['rbf','svr'])].groupby(['case','placement','method']).rmse.mean()
    fig,ax=plt.subplots(figsize=(6.5,3),layout='constrained')
    for method,color,offset in [('rbf','#d69330',-.17),('svr','#a34863',.17)]:
        numbers=[values.loc[(case,place,method)] for case in ('baseline','flow80') for place in ('interior','hybrid')]
        ax.bar(np.arange(4)+offset,numbers,width=.32,color=color,label=method.upper())
    ax.set(xticks=np.arange(4),xticklabels=['Base interior','Base hybrid','80% interior','80% hybrid'],ylabel='Full-section RMSE (m/s)',title='Fixed 24-sensor layouts with refitted predictors')
    ax.legend();ax.grid(axis='y',alpha=.2)
    save(fig,'transfer_compact')
    xy=sensors[['x_m','y_m']].to_numpy();scaler=StandardScaler().fit(xy)
    x,y=np.meshgrid(np.linspace(0,width,50),np.linspace(floor,floor+height,70));queries=np.column_stack([x.ravel(),y.ravel()])
    rows=[]; maps=[]
    for method in ('nearest','linear','rbf'):
        gain,weights,inside=interpolation_noise_gain(method,scaler.transform(xy),scaler.transform(queries))
        maps.append(pd.DataFrame(dict(method=method,x_m=queries[:,0],y_m=queries[:,1],gain=gain,inside_hull=inside)))
        for region,mask in [('inside',inside),('outside',~inside)]:
            finite=mask&np.isfinite(gain)
            rows.append(dict(method=method,region=region,finite_points=int(finite.sum()),max_gain=float(gain[finite].max()) if finite.any() else None))
        if method=='rbf': rbf_gain=gain.reshape(70,50)
    pd.DataFrame(rows).to_csv(a.output/'scaled_noise_gain.csv',index=False)
    pd.concat(maps).to_csv(a.output/'scaled_noise_map.csv',index=False)
    fig,axes=plt.subplots(1,2,figsize=(6.8,3.5),layout='constrained')
    image=axes[0].pcolormesh(x,y-floor,rbf_gain,cmap='magma',shading='auto',rasterized=True)
    axes[0].scatter(sensors.x_m,sensors.y_m-floor,edgecolors='white',facecolors='none',s=30)
    axes[0].set(xlabel='x (m)',ylabel='Local height (m)',title='Thin-plate RBF gain')
    axes[0].set_aspect('equal');fig.colorbar(image,ax=axes[0],label='Σ |weights|',shrink=.8)
    for column,label,color in [(1,'Near left wall','#bd4932'),(24,'Near centre','#2681a0')]:
        axes[1].plot(rbf_gain[:,column],y[:,0]-floor,label=label,color=color)
    axes[1].axvline(1,color='black',ls='--',lw=.8)
    axes[1].set(xlabel='Worst-case amplification gain',ylabel='Local height (m)',title='Geometric sensitivity')
    axes[1].legend(fontsize=8);axes[1].grid(alpha=.2)
    save(fig,'scaled_noise_gain')
    paths=[a.mesh,a.analysis/'experimental/predictions.csv',a.analysis/'paired/paired_runs.csv',a.analysis/'matched/matched_sensor_audit.csv',a.analysis/'verification/transfer_metrics.csv']
    (a.output/'manifest.json').write_text(json.dumps(dict(input_sha256={str(p):sha256(p.read_bytes()).hexdigest() for p in paths},script_sha256=sha256(Path(__file__).read_bytes()).hexdigest(),
          sensitivity='12 published matched sensor coordinates, training-only StandardScaler on geometry, fixed interpolation parameters, 50x70 full-section queries; geometry-only bounded-input sensitivity, not an uncertainty estimate',
          note='Recomputed standardized-coordinate gain is distinct from earlier unscaled metre-coordinate sensitivity'),indent=2)+'\n')
    print(pd.DataFrame(rows).to_string(index=False))


if __name__=='__main__':main()
