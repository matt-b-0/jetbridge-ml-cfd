"""Build an experimental or archived-CFD reconstruction lab in a GUI job."""
import json
import numpy as np
import pandas as pd
from scipy.spatial import Delaunay
from jetbridge_ml.benchmark import summarize
from jetbridge_ml.cfd_interface.plot_comparison import mesh_profile
from jetbridge_ml.data_processing.faa import read_speed_average
from jetbridge_ml.experimental_svr import evaluate_experimental_plane
from jetbridge_ml.validation.reconstruction_lab import METHODS, fit_predict, sensitivity_study, sensor_designs
from .lab_views import export_views


def build_lab(root, output, spec, check_cancel):
    """Execute the lab without modifying inputs or launching CFD.

    Parameters
    ----------
    root, output : pathlib.Path
        Repository and existing isolated job directory.
    spec : RunSpec
        lab or lab_cfd request, with a supported experiment ID.
    check_cancel : callable
        Worker cancellation callback.

    Returns
    -------
    dict
        Study lineage, protocol and output summary for the job manifest.
    """
    width,zs,floors,tops=mesh_profile(root/'cfd/cases/empty_bridge_s01_a_10_hn_1/system/blockMeshDict')
    virtual=spec.kind=='lab_cfd'
    print('STAGE: Loading '+('archived CFD virtual-sensor reference' if virtual else 'experimental sensor means'),flush=True)
    if virtual:
        reference=pd.read_csv(root/'data/demo/virtual_samples/dense_test.csv')
        reference=reference[reference.station_ft==16].sort_values(['grid_row','grid_col']).reset_index(drop=True)
        if len(reference)!=2400 or reference[['x_m','y_m']].duplicated().any():
            raise ValueError('Expected a unique 40 × 60 archived CFD plane at 16 ft')
        q=reference[['x_m','y_m']].to_numpy();truth=reference.speed_mps.to_numpy()
        if not np.isfinite(np.c_[q,truth]).all():
            raise ValueError('Non-finite CFD reference')
        pool_mask=(reference.grid_row%4==1)&(reference.grid_col%4==1)
        pool=reference[pool_mask];test=reference[~pool_mask]
        pool_x=pool[['x_m','y_m']].to_numpy();pool_y=pool.speed_mps.to_numpy()
        designs,_,_=sensor_designs(pool_x,test[['x_m','y_m']].to_numpy())
        display=next(d for d in designs if d['repeat']==0 and d['count']==24)['train']
        x,y=pool_x[display],pool_y[display]
        z=float(reference.z_m.iloc[0]);nx,ny=40,60
        lineage='ARCHIVED converged CFD · virtual sensors · 16 ft'
        title='Virtual sensor reconstruction · archived isothermal CFD'
        evaluation='A fixed 24-sensor design predicts a disjoint dense test grid in one archived CFD plane. Common-hull RMSE measures numerical reconstruction, not experimental accuracy. No new CFD run.'
        held=None;searches=[]
    else:
        frame=read_speed_average(root/f'data/demo/experimental/03-Averages/V-{spec.run_id}.txt')
        frame=frame[np.isfinite(frame.speed_mps)].copy()
        x=frame[['x_m','y_m']].to_numpy();y=frame.speed_mps.to_numpy();z=float(frame.z_m.iloc[0])
        pool_x,pool_y=x,y;test=None;truth=None
        floor=float(np.interp(z,zs,floors));height=float(np.interp(z,zs,tops)-floor)
        nx,ny=40,60
        xx,hh=np.meshgrid((np.arange(nx)+.5)*width/nx,(np.arange(ny)+.5)*height/ny)
        q=np.c_[xx.ravel(),hh.ravel()+floor]
        print('STAGE: Nested held-location evaluation (SVR tunes on retained sensors only)',flush=True)
        check_cancel()
        held,search,audit=evaluate_experimental_plane(frame)
        search.to_csv(output/'lab_nested_search.csv',index=False)
        audit.to_csv(output/'lab_nested_split_audit.csv',index=False)
        held=held[held.method.isin(METHODS)].copy()
        searches=[]
        lineage='EXPERIMENTAL means · '+spec.run_id
        title='Experimental reconstruction · '+spec.run_id
        evaluation='Each source sensor is withheld in turn. SVR parameters are selected by grouped inner cross-validation using only the remaining locations. Maps use a separate full-array refit. Replicates are not pooled.'
    floor=float(np.interp(z,zs,floors));height=float(np.interp(z,zs,tops)-floor)
    inside=Delaunay(x).find_simplex(q,tol=1e-10)>=0
    fields={};timing=[]
    print('STAGE: Matched field maps and three-trial fitting timings',flush=True)
    for method in METHODS:
        for repeat in range(3):
            check_cancel()
            values,elapsed,evidence=fit_predict(method,x,y,q)
            timing.append(dict(method=method,repeat=repeat,seconds=elapsed,training_count=len(x),query_count=len(q),
                               includes_svr_search=method=='svr'))
            if repeat==0 and evidence:searches.append(dict(stage='full_refit',**evidence))
        fields[method]=[float(v) if np.isfinite(v) else None for v in values]
    if virtual:
        records=[]
        for method in METHODS:
            values=np.array(fields[method],float)
            for index in test.index:
                records.append(dict(run_id=spec.run_id,method=method,source_row=int(index),
                                    x_m=q[index,0],y_m=q[index,1],speed_mps=truth[index],
                                    prediction_mps=values[index],inside_hull=bool(inside[index]),target_available=True))
        held=pd.DataFrame(records)
    metrics_all=summarize(held)
    metrics=metrics_all[metrics_all.subset=='common_hull'].copy()
    if (metrics.n_predicted==0).any():
        raise ValueError('No common supported held-out predictions for the lab')
    print('STAGE: Sensor-count learning and paired noise sensitivity',flush=True)
    study,splits,study_search=sensitivity_study(pool_x,pool_y,
        None if not virtual else test[['x_m','y_m']].to_numpy(),
        None if not virtual else test.speed_mps.to_numpy(),check_cancel)
    held.to_csv(output/'lab_heldout_predictions.csv',index=False)
    metrics_all.to_csv(output/'lab_metrics.csv',index=False)
    study.to_csv(output/'lab_sensitivity.csv',index=False)
    pd.DataFrame(timing).to_csv(output/'lab_timing.csv',index=False)
    table=pd.DataFrame(q,columns=['x_m','y_m']);table['height_m']=q[:,1]-floor
    table['inside_full_sensor_hull']=inside
    for method in METHODS:table[method+'_mps']=fields[method]
    table.to_csv(output/'lab_fields.csv',index=False)
    (output/'lab_split_audit.json').write_text(json.dumps(splits,indent=2))
    (output/'lab_search_audit.json').write_text(json.dumps(dict(full_refit=searches,sensitivity=study_search),indent=2))
    protocol='Seed 3001; three nested layouts with fixed hull anchors; separate fixed test locations; paired training-only Gaussian perturbations; no clipping.'
    if not virtual and spec.run_id.startswith('S01-A-58-'):
        protocol += ' The 58 ft A/B array was acquired sequentially, not as a synchronised field.'
    payload=dict(title=title,lineage=lineage,evaluation=evaluation,protocol=protocol,
                 width=float(width),height=height,floor=floor,nx=nx,ny=ny,
                 query=q.tolist(),sensors=np.c_[x,y].tolist(),inside=inside.tolist(),
                 fields=fields,timing=timing)
    if virtual:payload['reference']=truth.tolist()
    print('STAGE: Report figures and interactive offline dashboard',flush=True)
    check_cancel();export_views(output,payload,held,study,metrics)
    return dict(lineage=lineage,evaluation=evaluation,protocol=protocol,methods=list(METHODS),
                sensor_count=len(x),reference_plane_station_ft=16 if virtual else int(spec.run_id.split('-')[2]),
                physical_validation='not established',dashboard='reconstruction_lab.html',
                thermal_fields_used=False,metrics=metrics.replace({np.nan:None}).to_dict('records'))
