"""Bounded isothermal mesh, nominal-coordinate and flow-transfer checks."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import numpy as np
import pandas as pd
from scipy.spatial import cKDTree
from jetbridge_ml.cfd_interface.plot_comparison import mesh_profile
from jetbridge_ml.data_processing.faa import read_speed_average
from jetbridge_ml.data_processing.raw_speed import read_raw_speed

SPECS={'coarse':(12,16,42,9,41),'fine':(36,48,126,27,123),'flow80':(24,32,84,18,82)}


def scale_uniform_scalars(text,factor):
    """Scale uniform scalar field values for consistent inlet turbulence inputs."""
    return re.sub(r'(uniform\s+)([\d.eE+-]+)(\s*;)',lambda m:m[1]+f'{float(m[2])*factor:.12g}'+m[3],text)


def prepare_case(baseline,output,name):
    """Prepare an isolated cold-start case with prescribed mesh or flow change.

    Parameters
    ----------
    baseline, output : pathlib.Path
        Existing verified baseline and new case path.
    name : str
        coarse, fine, or flow80 (80 percent of baseline supply).

    Returns
    -------
    dict
        Cell count and flow factor; physics and changes are explicit.
    """
    if output.exists() or name not in SPECS:
        raise ValueError('New output and known sensitivity specification required')
    output.mkdir(parents=True)
    for folder in ('0','system'):
        shutil.copytree(baseline/folder,output/folder)
    shutil.copytree(baseline/'constant',output/'constant',ignore=shutil.ignore_patterns('polyMesh'))
    nx,ny,*nz=SPECS[name]
    mesh=output/'system/blockMeshDict'
    index=iter(nz)
    text=re.sub(r'(hex\s*\([^)]*\)\s*)\(\d+\s+\d+\s+\d+\)',lambda m:m[1]+f'({nx} {ny} {next(index)})',mesh.read_text())
    mesh.write_text(text)
    control=output/'system/controlDict'
    control.write_text(re.sub(r'endTime\s+\d+\s*;', 'endTime 600;',control.read_text()))
    factor=.8 if name=='flow80' else 1.
    if factor!=1:
        u=output/'0/U'
        text=u.read_text()
        text=re.sub(r'(volumetricFlowRate\s+constant\s+)([\d.eE+-]+)',lambda m:m[1]+f'{float(m[2])*factor:.12g}',text)
        text=re.sub(r'(uniform\s*\()([\d.eE+-]+)\s+([\d.eE+-]+)\s+([\d.eE+-]+)(\))',
                    lambda m:m[1]+' '.join(f'{float(m[i])*factor:.12g}' for i in (2,3,4))+m[5],text)
        u.write_text(text)
        for field,power in [('k',2),('epsilon',3)]:
            path=output/'0'/field
            path.write_text(scale_uniform_scalars(path.read_text(),factor**power))
    return dict(cells=nx*ny*sum(nz),flow_factor=factor,mesh_counts=[nx,ny,*nz],cold_start=True)


def foam_run(command,case,log):
    """Run an OpenFOAM command with its log captured in an explicit case."""
    with log.open('w') as handle:
        subprocess.run(['bash','-lc','source /usr/lib/openfoam/openfoam2412/etc/bashrc; exec '+shlex.join(command)],
                       cwd=case,stdout=handle,stderr=subprocess.STDOUT,check=True)


def main():
    """Run three bounded cases and sample the same positions on each mesh."""
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('baseline','dataset','output'):
        p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args()
    if a.output.exists(): p.error('Output must be new')
    a.output.mkdir(parents=True)
    source_paths=[f for folder in ('0','system','constant') for f in (a.baseline/folder).rglob('*') if f.is_file() and 'polyMesh' not in f.parts]
    source_hash={str(f):sha256(f.read_bytes()).hexdigest() for f in source_paths}
    cases={'baseline':a.baseline}
    specs={'baseline':dict(cells=141312,flow_factor=1.,mesh_counts=[24,32,84,18,82])}
    for name in ('coarse','fine','flow80'):
        case=a.output/name
        specs[name]=prepare_case(a.baseline,case,name)
        cases[name]=case
        print('Running',name,specs[name],flush=True)
        foam_run(['blockMesh'],case,case/'log.blockMesh')
        foam_run(['checkMesh'],case,case/'log.checkMesh')
        if 'Mesh OK' not in (case/'log.checkMesh').read_text():
            raise RuntimeError('Mesh check failed')
        foam_run(['simpleFoam'],case,case/'log.simpleFoam')
        print('Finished',name,flush=True)
    width,zs,floors,tops=mesh_profile(a.baseline/'system/blockMeshDict')
    frame=read_speed_average(a.dataset/'03-Averages/V-S01-A-10-HN-1.txt')
    raw=read_raw_speed(a.dataset/'01-CSV/S01-A-10-HN-1.csv').groupby('source_row',sort=True).first()
    published=frame[['x_m','y_m','z_m']].to_numpy()
    nominal=np.column_stack([raw.raw_x_m,raw.raw_local_height_m+np.interp(raw.raw_nominal_z_m,zs,floors),raw.raw_nominal_z_m])
    blocks=[pd.DataFrame(published,columns=['x_m','y_m','z_m']).assign(region='published_sensors',station_ft=10),
            pd.DataFrame(nominal,columns=['x_m','y_m','z_m']).assign(region='nominal_sensors',station_ft=10)]
    for station in (16,28,40,52):
        source=read_speed_average(a.dataset/f'03-Averages/V-S01-A-{station}-HN-1.txt')
        z=float(source.z_m.iloc[0]); floor=np.interp(z,zs,floors); height=np.interp(z,zs,tops)-floor
        for region,nx,ny in [('candidate',32,48),('reference',40,60)]:
            xx,yy=np.meshgrid((np.arange(nx)+.5)*width/nx,floor+(np.arange(ny)+.5)*height/ny)
            blocks.append(pd.DataFrame(dict(x_m=xx.ravel(),y_m=yy.ravel(),z_m=z,region=region,station_ft=station)))
    coordinates=pd.concat(blocks,ignore_index=True)
    points=coordinates[['x_m','y_m','z_m']].to_numpy()
    positions='\n'.join('('+' '.join(f'{v:.12g}' for v in row)+')' for row in points)
    dictionary=a.output/'sample.dict'
    functions=['cloud { type sets; libs ("libsampling.so"); writeControl writeTime; setFormat raw; interpolationScheme cellPoint; fields (U p); sets (points { type cloud; axis xyz; points ('+positions+'); }); }']
    for name,patch,operation,field in [('pin','inlet','areaAverage','p'),('pout','outlet','areaAverage','p'),('qin','inlet','sum','phi'),('qout','outlet','sum','phi')]:
        functions.append(f'{name} {{ type surfaceFieldValue; libs ("libfieldFunctionObjects.so"); regionType patch; name {patch}; operation {operation}; writeFields false; fields ({field}); }}')
    dictionary.write_text('FoamFile { version 2.0; format ascii; class dictionary; object verifyExport; } functions { '+'\n'.join(functions)+' }')
    statuses={}
    for name,case in cases.items():
        log=(case/'log.simpleFoam').read_text()
        times=sorted([d for d in case.iterdir() if d.is_dir() and re.fullmatch(r'\d+(?:\.\d+)?',d.name)],key=lambda d:float(d.name))
        saved=times[-1].name
        converged=bool(re.search(r'SIMPLE solution converged in',log))
        export=a.output/f'log.export_{name}'
        foam_run(['simpleFoam','-case',str(case),'-postProcess','-time',saved,'-dict',str(dictionary)],case,export)
        path=next((case/f'postProcessing/cloud/{saved}').glob('points_p_U.*'))
        values=np.loadtxt(path)
        distance,indices=cKDTree(values[:,:3]).query(points)
        if values.shape!=(len(points),7) or max(distance)>1e-6 or len(set(indices))!=len(points) or not np.isfinite(values).all():
            raise ValueError('Invalid exported coordinate or field values')
        values=values[indices]
        result=coordinates.copy()
        result['p_kinematic_m2s2']=values[:,3]
        result[['Ux_mps','Uy_mps','Uz_mps']]=values[:,4:]
        result['speed_mps']=np.linalg.norm(values[:,4:],axis=1)
        result.to_csv(a.output/f'samples_{name}.csv',index=False)
        record=export.read_text()
        pin=float(re.findall(r'areaAverage\(inlet\) of p = ([\d.eE+-]+)',record)[-1])
        pout=float(re.findall(r'areaAverage\(outlet\) of p = ([\d.eE+-]+)',record)[-1])
        qin=float(re.findall(r'sum\(inlet\) of phi = ([\d.eE+-]+)',record)[-1]); qout=float(re.findall(r'sum\(outlet\) of phi = ([\d.eE+-]+)',record)[-1])
        statuses[name]=dict(**specs[name],case=str(case),saved_iteration=saved,solver_converged=converged,
                            mesh_ok='Mesh OK' in (case/'log.checkMesh').read_text(),pressure_drop_kinematic_m2s2=pin-pout,
                            inlet_m3s=qin,outlet_m3s=qout,relative_flux_imbalance=abs(qin+qout)/abs(qin),
                            sample_sha256=sha256((a.output/f'samples_{name}.csv').read_bytes()).hexdigest())
    for path,digest in source_hash.items():
        if sha256(Path(path).read_bytes()).hexdigest()!=digest:
            raise RuntimeError('Baseline source inputs changed')
    manifest=dict(cases=statuses,source_sha256=source_hash,script_sha256=sha256(Path(__file__).read_bytes()).hexdigest(),
                  transfer_protocol='Predefined 24-sensor hybrid; test at synthetic 80 percent baseline flow; retrain values and training-only SVR tuning, no layout adjustment',
                  limits=['Mesh counts differ with unequal refinement factors; no Richardson/GCI claim','Coordinate comparison is sensitivity to nominal-inch mapping, not a correction to published coordinates',
                          'Flow80 adjusts inlet U, k and epsilon to retain intensity and length-scale assumptions; not matched to a measured run'])
    (a.output/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps(statuses,indent=2),flush=True)


if __name__=='__main__': main()
