"""Scientific views for GUI jobs, reusing existing interpolation and test splits."""
import json
from pathlib import Path
import re
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import Normalize
import numpy as np
import pandas as pd
from scipy.spatial import Delaunay, ConvexHull
from sklearn.preprocessing import StandardScaler
from jetbridge_ml.experimental_svr import evaluate_experimental_plane
from jetbridge_ml.interpolation.plane import predict_plane
from jetbridge_ml.machine_learning.selection import select_plane_svr
from jetbridge_ml.benchmark import summarize
from jetbridge_ml.validation.metrics import regression_metrics
from jetbridge_ml.cfd_interface.plot_comparison import mesh_profile


def save(fig, output, name):
    """Save matching shareable PNG/PDF files and release the plot."""
    for ext in ('png', 'pdf'):
        fig.savefig(Path(output) / f'{name}.{ext}', dpi=180, bbox_inches='tight')
    plt.close(fig)


def reconstruction(frame, query, method, floor, output):
    """Plot a full-array refit and separately score withheld sensors.

    Parameters
    ----------
    frame : pandas.DataFrame
        One replicate with absolute metre coordinates and scalar m/s speeds.
    query : numpy.ndarray
        Flattened regular x/y display grid, shape (n, 2), at cell centres.
    method : str
        Existing nearest, linear, rbf or svr method.
    floor : float
        Laboratory elevation of the local bridge floor, metres.
    output : pathlib.Path
        Existing isolated result directory.

    Returns
    -------
    dict
        Supported held-location errors and full-refit coverage diagnostics.
    """
    valid = frame[np.isfinite(frame.speed_mps)].copy()
    x, y = valid[['x_m','y_m']].to_numpy(), valid.speed_mps.to_numpy()
    if len(valid) < 4:
        raise ValueError('At least four valid sensor values are required')
    scaler = StandardScaler().fit(x)
    inside = Delaunay(scaler.transform(x)).find_simplex(scaler.transform(query), tol=1e-10) >= 0
    params = None
    if method == 'svr':
        model, params, search, audit = select_plane_svr(x, y)
        values = model.predict(query)
        search.to_csv(output / 'full_refit_svr_search.csv', index=False)
        audit.to_csv(output / 'full_refit_svr_split_audit.csv', index=False)
    else:
        values = predict_plane(method, scaler.transform(x), y, scaler.transform(query))
    fields = pd.DataFrame(query, columns=['x_m','y_m'])
    fields['height_m'] = fields.y_m - floor
    fields['prediction_mps'] = values; fields['inside_full_hull'] = inside
    fields.to_csv(output / 'experimental_refit.csv', index=False)
    # Reuse the audited nested evaluation; full refit never supplies its scores.
    pred, searches, audits = evaluate_experimental_plane(frame)
    selected = pred[pred.method == method].copy()
    selected.to_csv(output / 'heldout_predictions.csv', index=False)
    searches.to_csv(output / 'nested_svr_search.csv', index=False)
    audits.to_csv(output / 'nested_split_audit.csv', index=False)
    metrics = summarize(selected)
    metrics.to_csv(output / 'heldout_metrics.csv', index=False)
    ny, nx = len(np.unique(query[:,1])), len(np.unique(query[:,0]))
    finite = np.concatenate([y, values[np.isfinite(values)]])
    norm = Normalize(float(finite.min()), float(finite.max()))
    fig, axes = plt.subplots(1,2,figsize=(10,6),layout='constrained')
    width = float(query[:,0].min() + query[:,0].max())
    local_query = query[:,1] - floor
    clear_height = float(local_query.min() + local_query.max())
    for ax in axes:
        ax.set(xlabel='x (m)',ylabel='Height above floor (m)',
               xlim=(0,width),ylim=(0,clear_height))
        ax.set_aspect('equal')
    axes[0].scatter(x[:,0],x[:,1]-floor,c=y,norm=norm,cmap='viridis',s=70)
    axes[0].set_title('Measured means')
    image = axes[1].pcolormesh(query[:,0].reshape(ny,nx),(query[:,1]-floor).reshape(ny,nx),
                             values.reshape(ny,nx),norm=norm,cmap='viridis',shading='nearest')
    axes[1].contourf(query[:,0].reshape(ny,nx),(query[:,1]-floor).reshape(ny,nx),
                     (~inside).reshape(ny,nx),levels=[.5,1.5],colors='none',hatches=['////'])
    hull = ConvexHull(x); boundary = np.r_[hull.vertices,hull.vertices[0]]
    axes[1].plot(x[boundary,0],x[boundary,1]-floor,'k-',lw=1)
    axes[1].scatter(x[:,0],x[:,1]-floor,c='black',s=18)
    axes[1].set_title(f'{method.upper()} full-array refit')
    fig.colorbar(image,ax=axes,label='Scalar speed (m/s)',shrink=.75)
    fig.suptitle(f'{frame.run_id.iloc[0]}\nHatching marks extrapolation; a refit is not a prediction test')
    save(fig,output,'experimental_reconstruction')
    fig,ax=plt.subplots(figsize=(9,4),layout='constrained')
    colors=np.where(selected.inside_hull,'#007F85','#CB792E')
    ax.bar(selected.source_row,selected.prediction_mps-selected.speed_mps,color=colors)
    ax.axhline(0,color='black',lw=.8)
    ax.set(xlabel='Published source sensor row (zero based)',ylabel='Prediction − measured (m/s)',
           title='Held-location prediction errors. Teal = supported, orange = outside training hull')
    save(fig,output,'heldout_errors')
    supported=metrics[metrics.subset=='common_hull'].iloc[0]
    summary={key:float(supported[key]) if np.isfinite(supported[key]) else None for key in ('rmse','mae','bias','coverage')}
    summary.update(negative_full_grid_predictions=int(np.sum(values<0)),
                   unsupported_full_grid_fraction=float(np.mean(~inside)),
                   full_refit_parameters=params,
                   evaluation='Separate replicate; nested held-location tests; full refit used for visualisation only',
                   internal_evaluation='Existing all-method benchmark reused; selected method shown')
    return summary


def mesh_plot(mesh, frame, resolution, output):
    """Draw the selected exact dictionary grid with local sensor heights."""
    width,zs,floors,tops=mesh_profile(mesh)
    counts=[tuple(map(int,m)) for m in re.findall(r'hex\s*\([^)]*\)\s*\((\d+)\s+(\d+)\s+(\d+)\)',mesh.read_text())]
    nx,ny,_=counts[0];z=float(frame.z_m.iloc[0]);floor=np.interp(z,zs,floors)
    height=np.interp(z,zs,tops)-floor
    fig,axes=plt.subplots(1,2,figsize=(10,5),layout='constrained')
    for x in np.linspace(0,width,nx+1):axes[0].plot([x,x],[0,height],color='#8296A4',lw=.45)
    for h in np.linspace(0,height,ny+1):axes[0].plot([0,width],[h,h],color='#8296A4',lw=.45)
    axes[0].scatter(frame.x_m,frame.y_m-floor,c='#007F85',s=24)
    axes[0].set(xlabel='x (m)',ylabel='Height above floor (m)',title=f'{nx} × {ny} cross-section')
    axes[0].set_aspect('equal')
    for block,(_,_,nz) in enumerate(counts):
        for stream in np.linspace(zs[block],zs[block+1],nz+1):
            fy=np.interp(stream,zs,floors);ty=np.interp(stream,zs,tops)
            axes[1].plot([stream,stream],[fy,ty],color='#8296A4',lw=.35)
        for eta in np.linspace(0,1,ny+1):
            axes[1].plot(zs[block:block+2],floors[block:block+2]+eta*(tops[block:block+2]-floors[block:block+2]),color='#8296A4',lw=.35)
    axes[1].set(xlabel='z along bridge (m)',ylabel='Absolute laboratory y (m)',title='Three lengthwise mesh blocks')
    fig.suptitle(f'{resolution.title()} resolution: {sum(a*b*c for a,b,c in counts):,} cells\nUniform grading; resolution is not a physical-accuracy rating')
    save(fig,output,'mesh_setup')


def cfd_comparison(frame, sensor_speed, field, query, floor, output, lineage):
    """Compare matched scalar speeds without treating CFD as measured truth."""
    sensor_speed=np.asarray(sensor_speed,float)
    if sensor_speed.shape!=(len(frame),) or not np.isfinite(sensor_speed).all():
        raise ValueError('Expected one finite CFD speed per matched sensor')
    matched=frame.copy();matched['cfd_speed_mps']=sensor_speed
    matched['delta_mps']=sensor_speed-frame.speed_mps
    matched.to_csv(output/'cfd_sensor_comparison.csv',index=False)
    mask=np.isfinite(frame.speed_mps)
    metrics={k:float(v) for k,v in regression_metrics(frame.speed_mps[mask],sensor_speed[mask]).items()}
    (output/'cfd_metrics.json').write_text(json.dumps(metrics,indent=2)+'\n')
    fig,axes=plt.subplots(1,2,figsize=(10,5),layout='constrained',sharex=True,sharey=True)
    for ax,(x,part) in zip(axes,matched.groupby('x_m',sort=True)):
        h=part.y_m-floor
        ax.hlines(h,part.speed_mps,part.cfd_speed_mps,color='#9AA8B0',lw=2)
        ax.scatter(part.speed_mps,h,color='#007F85',label='Measured mean')
        ax.scatter(part.cfd_speed_mps,h,color='#D66B24',marker='s',label='CFD speed')
        ax.set(xlabel='Scalar speed (m/s)',title=f'x = {x:.2f} m')
    axes[0].set_ylabel('Height above floor (m)');axes[0].legend()
    fig.suptitle(f'{lineage}\nMatched-sensor RMSE {metrics["rmse"]:.5f} m/s; physical accuracy unresolved')
    save(fig,output,'cfd_matched_sensors')
    if field is not None:
        table=pd.DataFrame(query,columns=['x_m','y_m']);table['speed_mps']=field
        table.to_csv(output/'cfd_plane.csv',index=False)
        nx,ny=len(np.unique(query[:,0])),len(np.unique(query[:,1]))
        fig,ax=plt.subplots(figsize=(6,6),layout='constrained')
        image=ax.pcolormesh(query[:,0].reshape(ny,nx),(query[:,1]-floor).reshape(ny,nx),field.reshape(ny,nx),shading='nearest')
        ax.scatter(frame.x_m,frame.y_m-floor,s=16,c='white',edgecolors='black')
        ax.set(xlabel='x (m)',ylabel='Height above floor (m)',title=lineage+' scalar speed')
        fig.colorbar(image,ax=ax,label='CFD speed (m/s)')
        save(fig,output,'cfd_cross_section')


def residual_plot(history, output, lineage):
    """Export the recorded first initial residual per field and iteration."""
    from .residuals import read_history
    rows=read_history(history)
    if not rows:return
    frame=pd.DataFrame(rows)
    fig,ax=plt.subplots(figsize=(10,5),layout='constrained')
    for field,group in frame.groupby('field'):
        group=group.sort_values('iteration')
        if not (group.initial_residual>0).any():continue
        # Keep exact zero values in the CSV; logarithmic curves show positives.
        values=group.initial_residual.where(group.initial_residual>0,np.nan)
        ax.semilogy(group.iteration,values,label=field,lw=1.5)
    ax.set(xlabel='SIMPLE iteration (not physical seconds)',ylabel='Initial residual',
           title=lineage+'\nResidual convergence does not establish physical accuracy')
    if ax.lines:ax.legend(ncol=3)
    ax.grid(alpha=.2,which='both')
    save(fig,output,'residual_progress')
