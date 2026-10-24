"""Summarize isothermal verification and a fixed-layout flow transfer test."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.spatial import Delaunay
from jetbridge_ml.interpolation.plane import predict_plane
from jetbridge_ml.machine_learning.selection import select_plane_svr
from jetbridge_ml.sensor_design_study import design_indices
from jetbridge_ml.validation.metrics import regression_metrics


def mesh_differences(samples,manifest):
    """Compare identical positions against the finest numerical solution.

    Parameters
    ----------
    samples : dict
        DataFrames for coarse, baseline and fine fields at identical positions.
    manifest : dict
        CFD status records, including pressure drop and mesh counts.

    Returns
    -------
    pandas.DataFrame
        Numerical differences, not an exact-error or mesh-independence estimate.
    """
    rows=[]
    fine=samples['fine']
    for name in ('coarse','baseline','fine'):
        table=samples[name]
        np.testing.assert_allclose(table[['x_m','y_m','z_m']],fine[['x_m','y_m','z_m']],rtol=0,atol=1e-10)
        for region in ('published_sensors','reference'):
            mask=table.region==region
            delta=table.loc[mask,'speed_mps'].to_numpy()-fine.loc[mask,'speed_mps'].to_numpy()
            scale=np.sqrt(np.mean(fine.loc[mask,'speed_mps'].to_numpy()**2))
            rows.append(dict(case=name,region=region,cells=manifest['cases'][name]['cells'],n_points=int(mask.sum()),
                             speed_rmse_to_fine_mps=float(np.sqrt(np.mean(delta**2))),
                             relative_l2_to_fine=float(np.sqrt(np.mean(delta**2))/scale),
                             pressure_drop_kinematic_m2s2=manifest['cases'][name]['pressure_drop_kinematic_m2s2'],
                             pressure_drop_difference_to_fine=manifest['cases'][name]['pressure_drop_kinematic_m2s2']-manifest['cases']['fine']['pressure_drop_kinematic_m2s2']))
    return pd.DataFrame(rows)


def main():
    """Evaluate predefined layouts without selecting a new layout on transfer data."""
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--study',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    if a.output.exists(): p.error('Output must be new')
    manifest=json.loads((a.study/'manifest.json').read_text())
    samples={name:pd.read_csv(a.study/f'samples_{name}.csv') for name in manifest['cases']}
    for name,status in manifest['cases'].items():
        if not status['solver_converged'] or not status['mesh_ok'] or status['relative_flux_imbalance']>.001:
            raise ValueError(f'{name} failed numerical prerequisite checks; no trusted comparison generated')
        path=a.study/f'samples_{name}.csv'
        if sha256(path.read_bytes()).hexdigest()!=status['sample_sha256']:
            raise ValueError('Sample hash mismatch')
    mesh=mesh_differences(samples,manifest)
    coordinate=[]
    for name,table in samples.items():
        published=table[table.region=='published_sensors'].speed_mps.to_numpy()
        nominal=table[table.region=='nominal_sensors'].speed_mps.to_numpy()
        delta=nominal-published
        coordinate.append(dict(case=name,points=len(delta),nominal_minus_published_rmse_mps=float(np.sqrt(np.mean(delta**2))),
                               maximum_absolute_speed_change_mps=float(abs(delta).max()),mean_speed_change_mps=float(delta.mean())))
    transfer=[]; layouts=[]; searches=[]
    # These two geometric layouts and count were fixed before viewing flow80.
    for name in ('baseline','flow80'):
        table=samples[name]
        for station in (16,28,40,52):
            candidate=table[(table.region=='candidate')&(table.station_ft==station)]
            reference=table[(table.region=='reference')&(table.station_ft==station)]
            x=candidate[['x_m','y_m']].to_numpy(); q=reference[['x_m','y_m']].to_numpy()
            choices={place:design_indices(x,4,6,place) for place in ('interior','hybrid')}
            common=np.logical_and.reduce([Delaunay(x[idx]).find_simplex(q,tol=1e-10)>=0 for idx in choices.values()])
            for place,indices in choices.items():
                model,params,search,_=select_plane_svr(x[indices],candidate.speed_mps.to_numpy()[indices])
                search['case']=name; search['station_ft']=station; search['placement']=place; searches.append(search)
                scaler=model.named_steps['standardscaler']
                tx,tq=scaler.transform(x[indices]),scaler.transform(q)
                selected=candidate.iloc[indices].copy(); selected['case']=name; selected['placement']=place; layouts.append(selected)
                for method in ('nearest','linear','rbf','svr'):
                    values=model.predict(q) if method=='svr' else predict_plane(method,tx,candidate.speed_mps.to_numpy()[indices],tq)
                    for subset,mask in [('fixed_common_core',common),('full_section',np.ones(len(q),bool))]:
                        good=mask&np.isfinite(values)
                        transfer.append(dict(case=name,station_ft=station,placement=place,sensors=24,method=method,subset=subset,
                                             n_requested=int(mask.sum()),n_predicted=int(good.sum()),coverage=float(good.sum()/mask.sum()),
                                             **regression_metrics(reference.speed_mps.to_numpy()[good],values[good])))
    a.output.mkdir(parents=True)
    mesh.to_csv(a.output/'mesh_metrics.csv',index=False)
    pd.DataFrame(coordinate).to_csv(a.output/'coordinate_metrics.csv',index=False)
    transfer=pd.DataFrame(transfer)
    transfer.to_csv(a.output/'transfer_metrics.csv',index=False)
    pd.concat(layouts).to_csv(a.output/'transfer_layouts.csv',index=False)
    pd.concat(searches).to_csv(a.output/'training_search.csv',index=False)
    def save(fig,name):
        for ext in ('png','pdf'): fig.savefig(a.output/f'{name}.{ext}',dpi=300,bbox_inches='tight')
        plt.close(fig)
    fig,axes=plt.subplots(1,3,figsize=(13,4.2),layout='constrained')
    for region,label in [('published_sensors','12 sensor positions'),('reference','Dense section points')]:
        part=mesh[mesh.region==region].sort_values('cells')
        axes[0].plot(part.cells,part.speed_rmse_to_fine_mps,'o-',label=label)
    axes[0].set(xlabel='Mesh cells',ylabel='Speed RMSE versus fine mesh (m/s)',title='Differences, not exact errors')
    axes[0].legend(fontsize=7)
    pressure=mesh[mesh.region=='published_sensors'].sort_values('cells')
    axes[1].plot(pressure.cells,pressure.pressure_drop_kinematic_m2s2,'o-')
    axes[1].set(xlabel='Mesh cells',ylabel='Kinematic pressure drop (m²/s²)',title='Area-mean inlet minus outlet')
    coords=pd.DataFrame(coordinate).set_index('case').loc[['coarse','baseline','fine']]
    axes[2].bar(coords.index,coords.nominal_minus_published_rmse_mps,color='#2681a0')
    axes[2].set(ylabel='Speed change RMSE (m/s)',title='Nominal inch versus published metre positions')
    for ax in axes: ax.grid(alpha=.2)
    fig.suptitle('Isothermal numerical sensitivity | converged solves; physical validation remains outstanding')
    save(fig,'mesh_coordinate_sensitivity')
    summary=transfer.groupby(['case','placement','method','subset'],as_index=False).agg(mean_plane_rmse=('rmse','mean'),coverage=('coverage','mean'))
    fig,axes=plt.subplots(1,2,figsize=(10,4.3),layout='constrained')
    colors={'nearest':'#888888','rbf':'#d69330','svr':'#a34863'}
    for ax,name in zip(axes,('baseline','flow80')):
        for i,method in enumerate(colors):
            part=summary[(summary.case==name)&(summary.subset=='full_section')&(summary.method==method)].set_index('placement').loc[['interior','hybrid']]
            ax.bar(np.arange(2)+(i-1)*.24,part.mean_plane_rmse,width=.24,label=method,color=colors[method])
        ax.set(xticks=[0,1],xticklabels=['Interior','Hybrid'],ylabel='Mean plane full-section RMSE (m/s)',title=name+' | fixed 24-sensor geometry')
        ax.legend(fontsize=8); ax.grid(axis='y',alpha=.2)
    fig.suptitle('Layout transfer to synthetic 80% supply flow | models refitted on new retained sensor values\nNo layout changes; linear omitted here because full-section coverage is incomplete')
    save(fig,'flow_transfer')
    summary.to_csv(a.output/'transfer_summary.csv',index=False)
    record=dict(cases=manifest['cases'],coordinate_sensitivity=coordinate,
                limitations=['Three meshes and unequal refinement ratios: sensitivity evidence only, no GCI, observed-order or mesh-independence claim',
                             'Fine mesh is a numerical comparison reference, not exact physical truth',
                             'Nominal inches/local-floor mapping is an alternative coordinate interpretation, not a verified correction',
                             'Flow transfer tests fixed layout generalisation with refitted models; it does not test a frozen surrogate across flow rates',
                             'Synthetic 80% flow is not a new matched experimental case; walls/turbulence/diffuser assumptions retained'],
                input_manifest_sha256=sha256((a.study/'manifest.json').read_bytes()).hexdigest(),script_sha256=sha256(Path(__file__).read_bytes()).hexdigest())
    (a.output/'summary.json').write_text(json.dumps(record,indent=2)+'\n')
    print(mesh.to_string(index=False),flush=True)
    print(summary[summary.subset=='full_section'].to_string(index=False),flush=True)


if __name__=='__main__': main()
