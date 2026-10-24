"""Exploratory CFD sensor-count and placement reconstruction experiment."""
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
from scipy.spatial import Delaunay, cKDTree
from jetbridge_ml.interpolation.plane import predict_plane
from jetbridge_ml.machine_learning.selection import select_plane_svr, DEFAULT_GRID
from jetbridge_ml.validation.metrics import regression_metrics


def design_indices(points,nx,ny,placement):
    """Select a rectangular sensor layout without looking at CFD target values.

    Parameters
    ----------
    points : array-like
        Candidate x/local-height coordinates.
    nx, ny : int
        Numbers of sensor columns and rows.
    placement : str
        interior, wall_aware or hybrid, with fixed fractional coordinate ranges.

    Returns
    -------
    numpy.ndarray
        Unique candidate indices in layout order.
    """
    points=np.asarray(points,float)
    if placement not in ('interior','wall_aware','hybrid') or nx<2 or ny<2:
        raise ValueError('Valid placement and at least two rows/columns required')
    low,high=(.25,.75) if placement=='interior' else (.03,.97)
    ylow,yhigh=(.12,.88) if placement=='interior' else (.02,.98)
    # Recover rectangle edges from uniform midpoint candidate coordinates.
    xv,yv=np.unique(points[:,0]),np.unique(points[:,1])
    xmin,xmax=xv[0]-(xv[1]-xv[0])/2,xv[-1]+(xv[-1]-xv[-2])/2
    ymin,ymax=yv[0]-(yv[1]-yv[0])/2,yv[-1]+(yv[-1]-yv[-2])/2
    x,y=np.meshgrid(xmin+np.linspace(low,high,nx)*(xmax-xmin),ymin+np.linspace(ylow,yhigh,ny)*(ymax-ymin))
    queries=np.column_stack([x.ravel(),y.ravel()])
    if placement=='hybrid':
        n=nx*ny
        inner_spec={6:(2,1),12:(2,4),24:(4,4),48:(6,6)}
        ix,iy=inner_spec[n]
        gx,gy=np.meshgrid(np.linspace(.25,.75,ix),np.linspace(.2,.8,iy) if iy>1 else [.5])
        inner=np.column_stack([gx.ravel(),gy.ravel()])
        perimeter=n-len(inner)
        edge=np.linspace(0,1,perimeter,endpoint=False)*4
        boundary=[]
        for v in edge:
            if v<1: boundary.append((.03+.94*v,.02))
            elif v<2: boundary.append((.97,.02+.96*(v-1)))
            elif v<3: boundary.append((.97-.94*(v-2),.98))
            else: boundary.append((.03,.98-.96*(v-3)))
        fractional=np.vstack([inner,boundary])
        queries=np.column_stack([xmin+fractional[:,0]*(xmax-xmin),ymin+fractional[:,1]*(ymax-ymin)])
    # Equidistant midpoint ties must not flip with a change of floor elevation.
    # Normalize and round geometric distances before choosing the first index.
    scale=np.array([xmax-xmin,ymax-ymin])
    normalized=np.round((points-[xmin,ymin])/scale,12)
    normalized_query=np.round((queries-[xmin,ymin])/scale,12)
    distance=np.sum((normalized_query[:,None,:]-normalized[None,:,:])**2,axis=2)
    indices=np.argmin(np.round(distance,14),axis=1)
    if len(set(indices))!=nx*ny:
        raise ValueError('Candidate grid is too coarse for requested design')
    return indices


def main():
    """Compare fixed layouts using disjoint training and evaluation sample grids."""
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--candidates',type=Path,required=True)
    p.add_argument('--reference',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    if a.output.exists():
        p.error('Choose a fresh output directory')
    source=pd.read_csv(a.candidates)
    source=source[source.region=='cross_section'].copy()
    dense=pd.read_csv(a.reference)
    design_specs=[(nx,ny,placement) for nx,ny in ((2,3),(2,6),(4,6),(6,8)) for placement in ('interior','wall_aware','hybrid')]
    rows,designs,predictions,searches=[],[],[],[]
    a.output.mkdir(parents=True)
    for station,reference in dense.groupby('station_ft'):
        z=float(reference.z_m.iloc[0])
        candidate=source[np.isclose(source.z_m,z,atol=1e-8)].copy()
        if candidate.empty:
            raise ValueError('Candidate section missing')
        # A constant y shift within one plane does not change scaled distances.
        x=candidate[['x_m','y_m']].to_numpy()
        q=reference[['x_m','y_m']].to_numpy()
        if cKDTree(q).query(x)[0].min()<1e-9:
            raise ValueError('Candidate and evaluation grids overlap')
        choices=[design_indices(x,nx,ny,place) for nx,ny,place in design_specs]
        hulls=[Delaunay(x[idx]).find_simplex(q,tol=1e-10)>=0 for idx in choices]
        common=np.logical_and.reduce(hulls)
        for (nx,ny,place),indices,inside in zip(design_specs,choices,hulls):
            model,params,search,_=select_plane_svr(x[indices],candidate.speed_mps.to_numpy()[indices])
            search['station_ft']=station; search['sensors']=nx*ny; search['placement']=place
            searches.append(search)
            scaler=model.named_steps['standardscaler']
            tx,tq=scaler.transform(x[indices]),scaler.transform(q)
            selection=candidate.iloc[indices].copy()
            selection['station_ft']=station; selection['sensors']=nx*ny; selection['placement']=place
            designs.append(selection)
            for method in ('nearest','linear','rbf','svr'):
                values=model.predict(q) if method=='svr' else predict_plane(method,tx,candidate.speed_mps.to_numpy()[indices],tq)
                for subset,mask in [('fixed_common_core',common),('inside_design_hull',inside),('outside_design_hull',~inside),('full_section',np.ones(len(q),bool))]:
                    finite=mask & np.isfinite(values)
                    stats=regression_metrics(reference.speed_mps.to_numpy()[finite],values[finite]) if finite.any() else dict(rmse=np.nan,mae=np.nan,bias=np.nan)
                    rows.append(dict(station_ft=station,sensors=nx*ny,placement=place,method=method,subset=subset,
                                     n_requested=int(mask.sum()),n_predicted=int(finite.sum()),coverage=float(finite.sum()/mask.sum()) if mask.any() else np.nan,
                                     negative_predictions=int((values[finite]<0).sum()),**stats))
                table=reference.copy()
                table['sensors']=nx*ny; table['placement']=place; table['method']=method
                table['prediction_mps']=values; table['fixed_common_core']=common; table['inside_design_hull']=inside
                predictions.append(table)
            print('Evaluated',station,nx*ny,place,flush=True)
    metrics=pd.DataFrame(rows)
    metrics.to_csv(a.output/'metrics.csv',index=False)
    pd.concat(designs).to_csv(a.output/'sensor_layouts.csv',index=False)
    pd.concat(searches).to_csv(a.output/'training_search.csv',index=False)
    pd.concat(predictions).to_csv(a.output/'predictions.csv.gz',index=False,compression='gzip')
    summary=metrics.groupby(['sensors','placement','method','subset'],as_index=False).agg(mean_plane_rmse=('rmse','mean'),coverage=('coverage','mean'))
    summary.to_csv(a.output/'summary.csv',index=False)
    def save(fig,name):
        for ext in ('png','pdf'):
            fig.savefig(a.output/f'{name}.{ext}',dpi=300,bbox_inches='tight')
        plt.close(fig)
    colors={'nearest':'#777777','linear':'#2681a0','rbf':'#d69330','svr':'#a34863'}
    fig,axes=plt.subplots(3,2,figsize=(11,11),layout='constrained')
    for row,place in enumerate(('interior','wall_aware','hybrid')):
        for col,subset in enumerate(('fixed_common_core','full_section')):
            ax=axes[row,col]
            for method in ('nearest','linear','rbf','svr'):
                if method=='linear' and subset=='full_section':
                    continue
                part=summary[(summary.placement==place)&(summary.subset==subset)&(summary.method==method)]
                ax.plot(part.sensors,part.mean_plane_rmse,'o-',label=method,color=colors[method])
            ax.set(xlabel='Virtual sensors per plane',ylabel='Mean plane RMSE (m/s)',title=f'{place} | {subset}'.replace('_',' '),xticks=[6,12,24,48])
            ax.legend(fontsize=8); ax.grid(alpha=.2)
    fig.suptitle('CFD sensor-density and placement study | one isothermal numerical field\nFixed common core is identical for all layouts; linear has incomplete full-section coverage')
    save(fig,'sensor_count_errors')
    fig,axes=plt.subplots(1,3,figsize=(10,6),layout='constrained')
    examples=pd.concat(designs)
    for ax,place in zip(axes,('interior','wall_aware','hybrid')):
        part=examples[(examples.station_ft==16)&(examples.sensors==12)&(examples.placement==place)]
        ax.scatter(part.x_m,part.y_m,s=45)
        ax.set(xlabel='x (m)',ylabel='Absolute y (m)',title=f'12-sensor {place}',xlim=(0,1.388618),ylim=(.396,2.838))
        ax.set_aspect('equal'); ax.grid(alpha=.2)
    save(fig,'sensor_placement_examples')
    manifest=dict(packages={name:version(name) for name in ('numpy','pandas','scipy','scikit-learn','matplotlib')},
                  training_reference_separation='32x48 candidate grid versus disjoint 40x60 evaluation grid; both cellPoint from same isothermal field',
                  designs=[dict(nx=x,ny=y,placement=place) for x,y,place in design_specs],grid=DEFAULT_GRID,
                  limitations=['Exploratory placement study motivated by previously seen near-wall errors; not a new untouched test',
                               'Midpoint sampling is a numerical reference, not experimental validation or a mesh study',
                               'Fixed common core is intersection of all design hulls; full-section scores require coverage awareness',
                               'Sensor counts and layouts are fitted independently; sequences are not nested subsets'],
                  design_development='Hybrid layouts were added after the boundary-heavy layout performed poorly; all placement results are exploratory, not an untouched final test',
                  input_sha256={str(f):sha256(f.read_bytes()).hexdigest() for f in (a.candidates,a.reference)},
                  code_sha256={str(path):sha256(path.read_bytes()).hexdigest() for path in [Path(__file__),Path(__file__).parent/'machine_learning/selection.py',Path(__file__).parent/'machine_learning/svr.py',Path(__file__).parent/'interpolation/plane.py']})
    (a.output/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(summary[summary.subset=='full_section'].to_string(index=False),flush=True)


if __name__=='__main__':
    main()
