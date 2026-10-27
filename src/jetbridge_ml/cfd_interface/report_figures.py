"""Reproducible report figures from existing isothermal and thermal CFD fields.

Only OpenFOAM postprocessing is invoked; no solver iteration or input edit occurs.
"""
import argparse
from hashlib import sha256
from importlib.metadata import version
import json
from pathlib import Path
import platform
import re
import shlex
import subprocess
import zipfile

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import Normalize, TwoSlopeNorm
from matplotlib.patches import Polygon
import numpy as np
import pandas as pd

from jetbridge_ml.cfd_interface.plot_comparison import mesh_profile
from jetbridge_ml.data_processing.faa import read_speed_average

LABELS = {'iso': 'Isothermal | converged, iteration 237',
          'control': 'Thermal zero-gravity control | converged, iteration 733',
          'thermal': 'Buoyant thermal snapshot | NOT CONVERGED, iteration 967'}
COLORS = {'iso': '#26749c', 'control': '#797979', 'thermal': '#bd4932'}
STATIONS = (10,16,22,28,34,40,46,52,58)


def sample_grid(case, time, output, points, thermal):
    """Sample saved fields at unique metre coordinates and check row alignment.

    Parameters
    ----------
    case, output : pathlib.Path
        Existing case and report output directory.
    time : str
        Saved SIMPLE iteration, not physical time.
    points : numpy.ndarray
        Unique absolute xyz positions, shape (n, 3).
    thermal : bool
        Whether temperature is available.

    Returns
    -------
    dict
        Aligned U and optional T arrays.
    """
    fields = 'U T' if thermal else 'U'
    positions = '\n'.join('('+ ' '.join(f'{v:.12g}' for v in row)+')' for row in points)
    config = ('FoamFile { version 2.0; format ascii; class dictionary; object reportExport; }\n'
              'functions { reportCloud { type sets; libs ("libsampling.so"); '
              'writeControl writeTime; setFormat raw; interpolationScheme cellPoint; '
              f'fields ({fields}); sets (grid {{ type cloud; axis xyz; points ({positions}); }}); '
              '} }')
    dictionary = output / f'sampling_{case.name}.dict'
    dictionary.write_text(config)
    solver = 'buoyantBoussinesqSimpleFoam' if thermal else 'simpleFoam'
    command = [solver,'-case',str(case),'-postProcess','-time',time,'-dict',str(dictionary)]
    shell = 'source /usr/lib/openfoam/openfoam2412/etc/bashrc; exec '+shlex.join(command)
    with (output/f'log.sample_{case.name}').open('w') as log:
        subprocess.run(['bash','-lc',shell],stdout=log,stderr=subprocess.STDOUT,check=True,cwd=case)
    directory = case / f'postProcessing/reportCloud/{time}'
    from scipy.spatial import cKDTree
    raw = np.loadtxt(next(directory.glob('grid_T_U.*' if thermal else 'grid_U.*')))
    if raw.shape != (len(points),7 if thermal else 6):
        raise ValueError('Unexpected OpenFOAM raw field columns')
    velocity = np.column_stack([raw[:,:3],raw[:,4:]]) if thermal else raw
    distances, indices = cKDTree(velocity[:,:3]).query(points)
    # Runtime cases write eight significant digits: at z=18 m rounding can
    # reach 0.5 micrometres. One micrometre is far below sampling-grid spacing.
    if velocity.shape != (len(points),6) or max(distances)>1e-6 or len(set(indices))!=len(points):
        raise ValueError('Velocity coordinates do not uniquely match requested grid')
    result = {'U': velocity[indices,3:]}
    if thermal:
        temperature = raw[:,:4]
        distances, indices = cKDTree(temperature[:,:3]).query(points)
        if temperature.shape != (len(points),4) or max(distances)>1e-6 or len(set(indices))!=len(points):
            raise ValueError('Temperature coordinates do not match requested grid')
        result['T'] = temperature[indices,3]-273.15
    if not all(np.isfinite(v).all() for v in result.values()):
        raise ValueError('Nonfinite sampled field')
    return result


def residual_history(path):
    """Read first initial residual per field and SIMPLE iteration from a log."""
    rows=[]
    iteration=None
    for line in path.read_text().splitlines():
        match=re.match(r'Time = ([0-9.]+)',line)
        if match:
            iteration=float(match[1])
        match=re.search(r'Solving for (\w+), Initial residual = ([0-9.eE+-]+)',line)
        if match and iteration is not None:
            rows.append((iteration,match[1],float(match[2])))
    return pd.DataFrame(rows,columns=['iteration','field','residual']).drop_duplicates(['iteration','field'])


def read_archived_grid(path, points, thermal):
    """Read an explicitly archived grid, rejecting mismatches and invalid data.

    Parameters
    ----------
    path : pathlib.Path
        Saved CSV with physical coordinates and sampled U, optionally T.
    points : numpy.ndarray
        Expected ordered coordinates in metres, shape (n, 3).
    thermal : bool
        Require stored Celsius temperatures when true.

    Returns
    -------
    dict
        Finite velocity components and optional Celsius temperature arrays.
    """
    cached=pd.read_csv(path)
    np.testing.assert_allclose(cached[['x_m','y_m','z_m']],points,rtol=0,atol=1e-8)
    if cached[['x_m','y_m','z_m']].duplicated().any():
        raise ValueError('Archived grid has duplicate coordinates')
    fields={'U':cached[['Ux_mps','Uy_mps','Uz_mps']].to_numpy()}
    if thermal:fields['T']=cached.temperature_C.to_numpy()
    if not all(np.isfinite(values).all() for values in fields.values()):
        raise ValueError('Archived field contains nonfinite values')
    return fields


def main():
    """Export a captioned PNG/PDF figure collection from three saved cases."""
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('isothermal','thermal','control','dataset','thermal-comparisons','iso-comparisons','output'):
        parser.add_argument('--'+name,required=True,type=Path)
    parser.add_argument('--replay-tables',type=Path,help='Explicitly redraw archived sample tables without a CFD field')
    parser.add_argument('--iso-time',default='237')
    args=parser.parse_args()
    labels=dict(LABELS)
    labels['iso']=f'Isothermal | converged, iteration {args.iso_time}'
    out=args.output.resolve()
    if out.exists():
        parser.error('Choose a fresh output directory')
    out.mkdir(parents=True)
    cases={'iso':(args.isothermal.resolve(),args.iso_time),'control':(args.control.resolve(),'733'),
           'thermal':(args.thermal.resolve(),'967')}
    width,zs,floors,tops=mesh_profile(args.isothermal/'system/blockMeshDict')
    profiles=[mesh_profile(path/'system/blockMeshDict') for path,_ in cases.values()]
    for profile in profiles:
        for a,b in zip(profile,(width,zs,floors,tops)):
            np.testing.assert_allclose(a,b,rtol=0,atol=1e-12)
    for key,(path,time) in cases.items():
        log=(path/('log.simpleFoam' if key=='iso' else 'log.solver')).read_text()
        converged=f'SIMPLE solution converged in {time} iterations' in log
        if converged != (key!='thermal'):
            raise ValueError('Case convergence status changed; review captions')
        if not args.replay_tables and not (path/time/'U').exists():
            raise ValueError('Saved field missing')
    sensors={s:read_speed_average(args.dataset/f'03-Averages/V-S01-A-{s}-HN-1.txt') for s in STATIONS}
    # Uniform midpoint grids: avoid boundary ambiguity and retain actual geometry.
    nx,nh,nz=32,48,181
    xs=(np.arange(nx)+.5)*width/nx
    eta=(np.arange(nh)+.5)/nh
    plane_points=[]
    for s in STATIONS:
        z=float(sensors[s].z_m.iloc[0])
        floor=np.interp(z,zs,floors)
        h=np.interp(z,zs,tops)-floor
        x,y=np.meshgrid(xs,floor+eta*h)
        plane_points.append(np.column_stack([x.ravel(),y.ravel(),np.full(x.size,z)]))
    sidez=(np.arange(nz)+.5)*zs[-1]/nz
    sy=np.interp(sidez,zs,floors)[None,:]+eta[:,None]*np.interp(sidez,zs,tops-floors)[None,:]
    sz=np.broadcast_to(sidez,sy.shape)
    sidepoints=np.column_stack([np.full(sy.size,width/2),sy.ravel(),sz.ravel()])
    points=np.vstack([*plane_points,sidepoints])
    if len(np.unique(points,axis=0))!=len(points):
        raise ValueError('Sampling coordinates must be unique')
    count=nx*nh*len(STATIONS)
    data={}
    source_hashes={}
    for key,(path,time) in cases.items():
        print('Sampling',key,time,flush=True)
        if args.replay_tables:
            fields=read_archived_grid(args.replay_tables/f'sampled_{key}.csv',points,key!='iso')
            source_hashes[str(args.replay_tables/f'sampled_{key}.csv')]=sha256((args.replay_tables/f'sampled_{key}.csv').read_bytes()).hexdigest()
        else:
            fields=sample_grid(path,time,out,points,key!='iso')
        fields['speed']=np.linalg.norm(fields['U'],axis=1)
        data[key]=fields
        table=pd.DataFrame(points,columns=['x_m','y_m','z_m'])
        table[['Ux_mps','Uy_mps','Uz_mps']]=fields['U']
        table['speed_mps']=fields['speed']
        table['region']=['cross_section']*count+['longitudinal_midplane']*len(sidepoints)
        if 'T' in fields:
            table['temperature_C']=fields['T']
        table.to_csv(out/f'sampled_{key}.csv',index=False)
        for p in [path/time/'U',path/'system/blockMeshDict',path/'system/fvSolution',path/'0/U',
                  path/('log.simpleFoam' if key=='iso' else 'log.solver')]+([path/time/'T',path/'0/T',path/'constant/g'] if key!='iso' else []):
            if p.exists(): source_hashes[str(p)]=sha256(p.read_bytes()).hexdigest()
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,
                         'axes.spines.right':False,'pdf.fonttype':42,'savefig.facecolor':'white'})
    captions=[]
    def save(fig,name,caption):
        for ext in ('png','pdf'):
            fig.savefig(out/f'{name}.{ext}',dpi=300,bbox_inches='tight',facecolor='white')
        plt.close(fig)
        captions.append((name,caption))
        print('Saved',name,flush=True)
    outline=np.column_stack([np.r_[zs,zs[::-1]],np.r_[floors,tops[::-1]]])
    def sideplot(ax,values,label,norm,cmap):
        image=ax.pcolormesh(sz,sy,values[count:].reshape(nh,nz),shading='nearest',cmap=cmap,norm=norm,rasterized=True)
        image.set_clip_path(Polygon(outline,closed=True,transform=ax.transData))
        ax.plot(zs,floors,'k-',lw=.8)
        ax.plot(zs,tops,'k-',lw=.8)
        ax.set(xlim=(0,zs[-1]),ylim=(0,tops.max()),xlabel='Distance z (m): exhaust at 0; supply at 18.105',ylabel='Absolute y (m)',title=label)
        ax.set_aspect('equal')
        return image
    # Geometry overview with real experimental locations, without field interpolation.
    fig=plt.figure(figsize=(12,6),layout='constrained')
    ax=fig.add_subplot(111,projection='3d')
    for z,f,t in zip(zs,floors,tops):
        ax.plot([z]*5,[0,width,width,0,0],[f,f,t,t,f],color='#344b5c',lw=1.3)
    for x in (0,width):
        for y in (floors,tops):
            ax.plot(zs,np.full(len(zs),x),y,color='#344b5c',lw=1.3)
    for s,frame in sensors.items():
        ax.scatter(frame.z_m,frame.x_m,frame.y_m,s=7,alpha=.8,label=f'{s} ft')
    ax.set(xlabel='z (m)',ylabel='x (m)',zlabel='y (m)',title='Bridge geometry and experimental sensor positions\nSource coordinates: z along bridge, x across width, y above laboratory floor')
    ax.set_xticks([0,3,6,9,12,15,18])
    ax.set_yticks([0,width],labels=['0','1.389'])
    ax.set_zticks([0,1,2,3])
    ax.xaxis.labelpad=14
    ax.set_box_aspect((18.1,2.5,4))
    ax.view_init(elev=19,azim=-62)
    ax.legend(ncol=3,fontsize=8,loc='upper left')
    save(fig,'01_geometry_and_sensors','Actual CFD geometry and FAA sensor positions; axes retain source meanings. Full-face supply at z=18.10512 m, exhaust at z=0. The known 0.127 mm source-ceiling discrepancy is retained.')
    vmax=max(v['speed'].max() for v in data.values())
    fig,axes=plt.subplots(3,1,figsize=(12,9),layout='constrained')
    for ax,key in zip(axes,cases):
        image=sideplot(ax,data[key]['speed'],labels[key],Normalize(0,vmax),'viridis')
    fig.colorbar(image,ax=list(axes),label='Speed magnitude (m/s)',shrink=.7)
    save(fig,'02_longitudinal_speed_shared_scale','Mid-width vertical slices, common speed scale. Cases have different inlet flows and thermal conditions; this is a descriptive comparison, not a controlled buoyancy test. Buoyant snapshot is not converged. Midplane sampling excludes boundary faces.')
    fig,axes=plt.subplots(2,1,figsize=(12,6.5),layout='constrained')
    lo=min(data[k]['T'].min() for k in ('control','thermal'))
    hi=max(data[k]['T'].max() for k in ('control','thermal'))
    for ax,key in zip(axes,('control','thermal')):
        image=sideplot(ax,data[key]['T'],labels[key],Normalize(lo,hi),'inferno')
    fig.colorbar(image,ax=list(axes),label='Temperature (°C)',shrink=.7)
    save(fig,'03_longitudinal_temperature','Cold supply and walls fixed at lab temperature (unmeasured wall-temperature surrogate). Zero-gravity control converged; buoyant iterate 967 has not. SIMPLE iteration is not physical time.')
    for key,index in (('iso','04'),('thermal','05'),('control','06')):
        fig,axes=plt.subplots(3,3,figsize=(9,11),layout='constrained')
        limit=data[key]['speed'][:count].max()
        for i,(ax,s) in enumerate(zip(axes.flat,STATIONS)):
            pos=plane_points[i]
            floor=np.interp(pos[0,2],zs,floors)
            image=ax.pcolormesh(pos[:,0].reshape(nh,nx),(pos[:,1]-floor).reshape(nh,nx),
                                data[key]['speed'][i*nx*nh:(i+1)*nx*nh].reshape(nh,nx),
                                cmap='viridis',vmin=0,vmax=limit,shading='nearest',rasterized=True)
            ax.set(xlabel='Width x (m)',ylabel='Height above floor (m)',title=f'{s} ft | z={pos[0,2]:.3f} m')
            ax.set_aspect('equal')
        fig.colorbar(image,ax=list(axes.flat),label='Speed (m/s)',shrink=.6)
        fig.suptitle(labels[key]+'\nNine sections of one numerical field; shared scale within this figure')
        save(fig,index+'_'+key+'_speed_sections','Nine source-coordinate planes from '+labels[key]+'. All panels use a common scale within this figure. Heights subtract the actual local CFD floor. These are CFD fields, not nine independently matched experimental runs.')
    fig,axes=plt.subplots(3,3,figsize=(9,11),layout='constrained')
    for i,(ax,s) in enumerate(zip(axes.flat,STATIONS)):
        pos=plane_points[i]
        floor=np.interp(pos[0,2],zs,floors)
        image=ax.pcolormesh(pos[:,0].reshape(nh,nx),(pos[:,1]-floor).reshape(nh,nx),data['thermal']['T'][i*nx*nh:(i+1)*nx*nh].reshape(nh,nx),cmap='inferno',vmin=lo,vmax=hi,shading='nearest',rasterized=True)
        ax.set(xlabel='Width x (m)',ylabel='Height above floor (m)',title=f'{s} ft | z={pos[0,2]:.3f} m')
        ax.set_aspect('equal')
    fig.colorbar(image,ax=list(axes.flat),label='Temperature (°C)',shrink=.6)
    fig.suptitle(labels['thermal']+'\nTemperature sections; fixed lab-temperature walls are a surrogate')
    save(fig,'07_thermal_temperature_sections','Provisional buoyant temperature cross-sections. The cold lower layer is a feature of this unconverged snapshot, not a validated prediction of thermal stratification.')
    fig,axes=plt.subplots(2,1,figsize=(12,6.5),layout='constrained')
    for ax,field,label in zip(axes,('speed','T'),('Speed difference (m/s)','Temperature difference (K)')):
        delta=data['thermal'][field]-data['control'][field]
        limit=max(abs(delta[count:]).max(),1e-12)
        image=sideplot(ax,delta,'Buoyant snapshot minus zero-gravity control',TwoSlopeNorm(vmin=-limit,vcenter=0,vmax=limit),'RdBu_r')
        fig.colorbar(image,ax=ax,label=label,shrink=.75)
    save(fig,'08_thermal_minus_control','Difference between buoyant snapshot 967 and control 733 at identical sampled positions. Same thermal inputs, gravity differs; solver relaxation and initialization also differ, and buoyant convergence is incomplete. Differences cannot yet be attributed solely to converged physical buoyancy.')
    # Physical projected velocity components: arrows are not scalar-speed gradients.
    fig,axes=plt.subplots(3,1,figsize=(12,9),layout='constrained')
    for ax,key in zip(axes,cases):
        image=sideplot(ax,data[key]['speed'],labels[key],Normalize(0,vmax),'viridis')
        u=data[key]['U'][count:].reshape(nh,nz,3)
        sel=(slice(2,None,5),slice(3,None,9))
        quiver=ax.quiver(sz[sel],sy[sel],u[:,:,2][sel],u[:,:,1][sel],color='white',angles='xy',scale_units='xy',scale=1.4,width=.0022)
        ax.quiverkey(quiver,.88,1.08,.2,'0.2 m/s projected',labelpos='E',coordinates='axes',color='black')
    fig.colorbar(image,ax=list(axes),label='Full speed magnitude (m/s)',shrink=.7)
    save(fig,'09_midplane_velocity_arrows','Arrows show projected CFD (Uz, Uy) vectors in the mid-width vertical plane; arrow scale is identical across cases. Colour is full three-component speed. Arrows are not streamlines, particle paths or experimental vectors. Thermal buoyant snapshot is unconverged.')
    # Uniform cross-section sampling permits descriptive mean statistics, not exact mesh flux.
    fig,axes=plt.subplots(1,3,figsize=(13,4.2),layout='constrained')
    stats=[]
    zvalues=[float(sensors[s].z_m.iloc[0]) for s in STATIONS]
    for key in cases:
        speed=data[key]['speed'][:count].reshape(9,nh,nx)
        uz=data[key]['U'][:count,2].reshape(9,nh,nx)
        axes[0].plot(zvalues,speed.mean(axis=(1,2)),'o-',color=COLORS[key],label=key)
        axes[1].plot(zvalues,(uz>0).mean(axis=(1,2))*100,'o-',color=COLORS[key],label=key)
        if key!='iso':
            temperature=data[key]['T'][:count].reshape(9,nh,nx)
            axes[2].plot(zvalues,temperature.mean(axis=(1,2)),'o-',color=COLORS[key],label=key)
        for i,s in enumerate(STATIONS):
            stats.append(dict(case=key,station_ft=s,z_m=zvalues[i],sample_mean_speed_mps=speed[i].mean(),reverse_sample_percent=(uz[i]>0).mean()*100,
                              sample_mean_temperature_C=float(temperature[i].mean()) if key!='iso' else np.nan))
    for ax,label in zip(axes,('Sample-mean speed (m/s)','Sample points with Uz > 0 (%)','Sample-mean temperature (°C)')):
        ax.set(xlabel='Bridge distance z (m)',ylabel=label)
        ax.grid(alpha=.2)
        ax.legend(fontsize=8)
    fig.suptitle('Uniform section-sample statistics | thermal = unconverged buoyant snapshot')
    save(fig,'10_axial_section_statistics','Statistics of uniform 32 by 48 midpoint samples on each section. Positive Uz denotes local reverse flow relative to supply-to-exhaust direction. Percentages are sample-area approximations, not flux fractions; means are not experimental observations or mesh-integrated conservation checks.')
    pd.DataFrame(stats).to_csv(out/'section_statistics.csv',index=False)
    # Experimental comparisons retain the original exporter cell-sampling convention.
    iso=pd.read_csv(args.iso_comparisons/'sensor_deltas.csv')
    iso=iso[iso.station_ft==10].copy()
    therm=pd.read_csv(args.thermal_comparisons/'thermal_sensor_comparison.csv')
    control=pd.read_csv(args.thermal_comparisons/'control_sensor_comparison.csv')
    comparison_status=json.loads((args.thermal_comparisons/'metrics.json').read_text())
    if str(comparison_status['thermal']['time'])!='967' or str(comparison_status['zero_gravity_control']['time'])!='733':
        raise ValueError('Thermal sensor-comparison snapshots differ from report fields')
    iso_status=json.loads((args.iso_comparisons/'manifest.json').read_text())
    if str(iso_status['time'])!=args.iso_time:
        raise ValueError('Isothermal comparison snapshot differs from report field')
    np.testing.assert_allclose(therm[['x_m','y_m','z_m','speed_mps','temperature_C']],
                               control[['x_m','y_m','z_m','speed_mps','temperature_C']],rtol=0,atol=1e-12)
    comparisons=[(iso,'speed_mps','cfd_speed_mps','Isothermal speed (m/s)'),
                 (therm,'speed_mps','cfd_speed_mps','Buoyant snapshot speed (m/s)'),
                 (therm,'temperature_C','cfd_temperature_C','Buoyant snapshot temperature (°C)')]
    fig,axes=plt.subplots(1,3,figsize=(12,4.2),layout='constrained')
    for ax,(table,obs,pred,label) in zip(axes,comparisons):
        h=table.y_m-np.interp(table.z_m,zs,floors)
        image=ax.scatter(table[obs],table[pred],c=h,cmap='cividis',s=65,edgecolors='black',linewidths=.5)
        low=min(table[obs].min(),table[pred].min())
        high=max(table[obs].max(),table[pred].max())
        margin=max((high-low)*.07,.001)
        ax.plot([low-margin,high+margin],[low-margin,high+margin],'k--',lw=1)
        rmse=np.sqrt(np.mean((table[pred]-table[obs])**2))
        ax.set(xlabel='Measured mean',ylabel='CFD at sensor',title=f'{label}\nRMSE = {rmse:.4f}',xlim=(low-margin,high+margin),ylim=(low-margin,high+margin))
        ax.set_aspect('equal')
        fig.colorbar(image,ax=ax,label='Height above floor (m)',shrink=.7)
    fig.suptitle('Matched 10 ft sensor comparisons | thermal panels NOT CONVERGED')
    save(fig,'11_sensor_parity','Matched isothermal S01-A-10-HN-1 and thermal S01-AC-10-HN-1 comparisons. Thermal values describe provisional iterate 967, not validation. Dashed lines indicate equality; colour shows local sensor height. Existing comparison exports use cell sampling, whereas field figures use cellPoint.')
    fig,axes=plt.subplots(1,3,figsize=(13,4.3),layout='constrained')
    for ax,(table,obs,pred,label) in zip(axes,comparisons):
        delta=table[pred]-table[obs]
        ax.bar(np.arange(1,len(table)+1),delta,color=np.where(delta>=0,'#bd4932','#26749c'))
        ax.axhline(0,color='black',lw=.8)
        ax.set(xlabel='Source row / sensor ID',ylabel='CFD minus measurement ('+('K' if obs=='temperature_C' else 'm/s')+')',title=label,xticks=np.arange(1,len(table)+1))
        ax.grid(axis='y',alpha=.2)
    fig.suptitle('Signed sensor differences | buoyant thermal snapshot NOT CONVERGED')
    save(fig,'12_signed_sensor_differences','Positive values indicate CFD overprediction. Isothermal speed and thermal speed differences use m/s; temperature differences use K. Source row numbering matches comparison tables. Thermal errors are descriptive snapshot diagnostics.')
    fig,axes=plt.subplots(2,2,figsize=(10,8),layout='constrained')
    for col,x in enumerate(sorted(therm.x_m.unique())):
        for row,(obs,pred,label) in enumerate((('speed_mps','cfd_speed_mps','Speed (m/s)'),('temperature_C','cfd_temperature_C','Temperature (°C)'))):
            ax=axes[row,col]
            for table,key,marker in ((therm,'thermal','s--'),(control,'control','^:')):
                part=table[table.x_m==x].sort_values('y_m')
                h=part.y_m-np.interp(part.z_m,zs,floors)
                ax.plot(part[pred],h,marker,color=COLORS[key],label=key)
            ax.plot(part[obs],h,'o-',color='#26749c',label='Measured mean')
            ax.set(xlabel=label,ylabel='Height above local floor (m)',title=f'Sensor column x={x:.2f} m')
            ax.legend(fontsize=8)
            ax.grid(alpha=.2)
    fig.suptitle('Cold-supply 10 ft profiles | thermal = NOT CONVERGED snapshot 967')
    save(fig,'13_thermal_sensor_height_profiles','Measured thermal means, converged zero-gravity control and unconverged buoyant snapshot at the same absolute source sensor coordinates. Connecting lines guide the eye and are not dense measurements. Walls fixed at lab temperature are a surrogate.')
    fig,axes=plt.subplots(1,3,figsize=(13,4.5),layout='constrained')
    for ax,(key,(path,time)) in zip(axes,cases.items()):
        history=residual_history(path/('log.simpleFoam' if key=='iso' else 'log.solver'))
        history.to_csv(out/f'residuals_{key}.csv',index=False)
        for field,part in history.groupby('field'):
            ax.semilogy(part.iteration,part.residual,label=field,lw=1)
        ax.set(xlabel='SIMPLE iteration (not seconds)',ylabel='Initial linear-solver residual',title=labels[key].replace(' | ','\n'))
        ax.legend(ncol=2,fontsize=7)
        ax.grid(alpha=.2)
    save(fig,'14_residual_histories','First initial residual per field per SIMPLE iteration. Cases have different initialization and relaxation, so histories do not isolate the effect of gravity. Configured solver convergence is not experimental validation; buoyant run remains unconverged at iteration 1000 although its latest saved field is 967.')
    fig,ax=plt.subplots(figsize=(10,4.2),layout='constrained')
    trace=np.loadtxt(args.thermal/'postProcessing/sensors/0/T')
    # Probe numbers follow the original experimental source row order.
    for i in (0,2,5):
        ax.plot(trace[:,0],trace[:,i+1]-273.15,label=f'Probe {i+1}')
    ax.axvline(967,color='black',ls='--',lw=1,label='Saved field used: 967')
    ax.axvspan(867,967,color='#aaa',alpha=.15,label='Saved-snapshot diagnostic window')
    ax.set(xlabel='SIMPLE iteration (not physical time)',ylabel='Temperature (°C)',title='Buoyant thermal probe evolution | NOT CONVERGED')
    ax.legend(ncol=2,fontsize=8)
    ax.grid(alpha=.2)
    save(fig,'15_thermal_probe_stationarity','Selected scheduled temperature probes from the buoyant restart. The last saved field is 967; log/probe records extend to 1000. Shading marks [867,967], the snapshot diagnostic interval. Iteration changes do not represent physical transient time.')
    # Distributions summarize samples, not probabilities or uncertainty bands.
    fig,axes=plt.subplots(1,2,figsize=(10,4.2),layout='constrained')
    for key in cases:
        speed=np.sort(data[key]['speed'][:count])
        axes[0].plot(speed,np.arange(1,len(speed)+1)/len(speed),label=key,color=COLORS[key])
    for key in ('control','thermal'):
        temp=np.sort(data[key]['T'][:count])
        axes[1].plot(temp,np.arange(1,len(temp)+1)/len(temp),label=key,color=COLORS[key])
    for ax,label in zip(axes,('Speed (m/s)','Temperature (°C)')):
        ax.set(xlabel=label,ylabel='Cumulative fraction of section samples')
        ax.legend(fontsize=8)
        ax.grid(alpha=.2)
    fig.suptitle('Equal-weight samples across nine sections | thermal snapshot NOT CONVERGED')
    save(fig,'16_section_sample_distributions','Empirical cumulative distributions of equal-weight samples across nine sections. Not whole-volume distributions, experimental uncertainty or statistical confidence. Buoyant snapshot is unconverged; iso/control use different operating conditions.')
    manifest={'python':platform.python_version(),'packages':{p:version(p) for p in ('numpy','pandas','scipy','matplotlib')},
              'cases':{k:{'path':str(p),'saved_iteration':t,'status':labels[k]} for k,(p,t) in cases.items()},
              'sampling':'cellPoint; 32x48 midpoint samples per section, 181x48 mid-width side samples; unique XYZ checked within 1 micrometre (raw writer has 8 significant digits)',
              'figure_count':len(captions),'replayed_sample_tables':bool(args.replay_tables),'script_sha256':sha256(Path(__file__).read_bytes()).hexdigest(),
              'source_sha256':source_hashes,
              'limitations':['No new simulation, mesh study or physical validation','Thermal wall temperature is an unmeasured lab-temperature surrogate',
                             'Initial divergent thermal field excluded','Sample statistics are not mesh-integrated conservation checks']}
    for directory in (args.iso_comparisons,args.thermal_comparisons):
        for filename in ('sensor_deltas.csv','thermal_sensor_comparison.csv','control_sensor_comparison.csv','manifest.json','metrics.json'):
            p=directory/filename
            if p.exists():
                manifest['source_sha256'][str(p)]=sha256(p.read_bytes()).hexdigest()
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    lines=['# Report figure collection','',
           '16 figures in 300 dpi PNG and vector PDF. Contour colour meshes are rasterized within PDFs to keep file sizes practical; text, axes and linework remain vector.',
           '', 'Thermal means the **unconverged buoyant snapshot at iteration 967**. The zero-gravity thermal control converged at 733; the isothermal baseline converged at 237. No experimental validation is claimed.',
           '', '## Suggested compact report selection','',
           'Use 01 for setup, 02 and 03 for field behaviour, 11 for measurement comparison, and 14 for numerical limitations. Place the remaining galleries in an appendix. Do not omit the thermal convergence labels.', '']
    for name,caption in captions:
        lines.extend([f'## {name}', '',caption,'',f'![{name}]({name}.png)','',f'[Vector PDF]({name}.pdf)',''])
    (out/'FIGURE_GUIDE.md').write_text('\n'.join(lines))
    # Small contact sheet provides an overview without opening sixteen large files.
    import matplotlib.image as mpimg
    fig,axes=plt.subplots(4,4,figsize=(16,16),layout='constrained')
    for ax,(name,_) in zip(axes.flat,captions):
        ax.imshow(mpimg.imread(out/f'{name}.png'))
        ax.set_title(name.replace('_',' '),fontsize=8)
        ax.axis('off')
    fig.savefig(out/'00_contact_sheet.png',dpi=140,facecolor='white')
    plt.close(fig)
    with zipfile.ZipFile(out/'report_figures.zip','w',zipfile.ZIP_DEFLATED) as archive:
        for p in sorted(out.iterdir()):
            if p.suffix in ('.png','.pdf') or p.name in ('FIGURE_GUIDE.md','manifest.json'):
                archive.write(p,p.name)
    print('Report figures complete:',out,flush=True)


if __name__=='__main__':
    main()
