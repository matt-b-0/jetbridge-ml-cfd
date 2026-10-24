"""Compare a bounded thermal continuation with its unconverged saved restart."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
import re
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from jetbridge_ml.cfd_interface.report_figures import residual_history


def read_probe_trace(case,field='T'):
    """Merge probe restart segments by SIMPLE iteration without mixing fields.

    Parameters
    ----------
    case : pathlib.Path
        Existing thermal runtime case.
    field : str
        Scalar probe field name, default temperature in Kelvin.

    Returns
    -------
    numpy.ndarray
        Sorted iteration/probe columns with duplicate iterations removed.
    """
    paths=sorted((case/'postProcessing/sensors').glob('*/'+field))
    if not paths:
        raise ValueError('No scheduled probe trace')
    arrays=[np.atleast_2d(np.loadtxt(path)) for path in paths]
    if len({array.shape[1] for array in arrays})!=1:
        raise ValueError('Restart probe layouts differ')
    data=np.vstack(arrays)
    data=data[np.argsort(data[:,0],kind='stable')]
    _,indices=np.unique(data[:,0],return_index=True)
    if not np.isfinite(data).all():
        raise ValueError('Nonfinite probe history')
    return data[indices]


def audit_thermal(case):
    """Summarize residuals, bounds, flux and a predeclared stationarity screen.

    Parameters
    ----------
    case : pathlib.Path
        Completed bounded thermal run with log and probe outputs.

    Returns
    -------
    dict
        Separate numerical checks; no experimental validation is inferred.
    """
    log=(case/'log.solver').read_text()
    last=float(re.findall(r'^Time = ([\d.]+)',log,re.M)[-1])
    history=residual_history(case/'log.solver')
    residuals=history[history.iteration==last].set_index('field').residual.to_dict()
    trace=read_probe_trace(case)
    selected=trace[(trace[:,0]>=last-100)&(trace[:,0]<=last)]
    if len(selected)<2:
        raise ValueError('Insufficient final probe window')
    drift=float(np.ptp(selected[:,1:],axis=0).max())
    inlet=float(re.findall(r'sum\(inlet\) of phi = ([\d.eE+-]+)',log)[-1])
    outlet=float(re.findall(r'sum\(outlet\) of phi = ([\d.eE+-]+)',log)[-1])
    imbalance=abs(inlet+outlet)/abs(inlet)
    tmin=float(re.findall(r'min\(T\) = ([\d.eE+-]+)',log)[-1])
    tmax=float(re.findall(r'max\(T\) = ([\d.eE+-]+)',log)[-1])
    speeds=re.findall(r'max\(mag\(U\)\) = ([\d.eE+-]+)',log)
    maximum=float(speeds[-1]) if speeds else None
    settings=json.loads((case/'data/processed/setup.json').read_text())
    low=min(settings['inlet_temperature_K'],settings['ambient_temperature_K'])
    high=max(settings['inlet_temperature_K'],settings['ambient_temperature_K'])
    bounded=tmin>=low-1e-4 and tmax<=high+1e-4
    thresholds={key:(1e-6 if key=='T' else 1e-5) for key in residuals}
    solver_pass=bool(re.search(r'SIMPLE solution converged in',log))
    residual_pass=all(residuals.get(key,np.inf)<limit for key,limit in {'Ux':1e-5,'Uy':1e-5,'Uz':1e-5,'p_rgh':1e-5,'T':1e-6,'k':1e-5,'epsilon':1e-5}.items())
    saved=sorted([float(p.name) for p in case.iterdir() if p.is_dir() and re.fullmatch(r'\d+(?:\.\d+)?',p.name)])
    return dict(case=str(case),last_iteration=last,last_saved_field_iteration=saved[-1],
                mesh_check_passed='Mesh OK' in (case/'log.checkMesh').read_text(),solver_reported_convergence=solver_pass,
                last_initial_residuals=residuals,residual_thresholds=thresholds,residual_screen_passed=residual_pass,
                probe_window=[last-100,last],probe_records=len(selected),maximum_probe_temperature_range_K=drift,
                stationarity_screen_K=.01,stationarity_screen_passed=drift<.01,
                inlet_m3s=inlet,outlet_m3s=outlet,relative_flux_imbalance=imbalance,flux_screen_passed=imbalance<.001,
                minimum_temperature_K=tmin,maximum_temperature_K=tmax,temperature_boundary_screen_passed=bounded,
                last_reported_maximum_speed_mps=maximum,
                numerical_reference_eligible=bool(solver_pass and residual_pass and drift<.01 and bounded and imbalance<.001),
                experimentally_validated=False)


def main():
    """Save honest continuation diagnostics without fitting experimental data."""
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('restart-source','continuation','output'):
        p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args()
    if a.output.exists(): p.error('Choose a fresh output directory')
    a.output.mkdir(parents=True)
    audits={name:audit_thermal(case) for name,case in [('original_restart',a.restart_source),('continuation',a.continuation)]}
    histories={key:residual_history(case/'log.solver') for key,case in [('original_restart',a.restart_source),('continuation',a.continuation)]}
    # Previous log has no speed fieldMinMax: extract saved-field bound from its exporter record.
    fig,axes=plt.subplots(1,2,figsize=(12,4.5),layout='constrained')
    for key,history in histories.items():
        for field in ('p_rgh','Uz','T'):
            part=history[history.field==field]
            axes[0].semilogy(part.iteration,part.residual,label=key+' '+field,lw=1)
        history.to_csv(a.output/f'{key}_residuals.csv',index=False)
    for label,case in [('Original restart',a.restart_source),('Continuation',a.continuation)]:
        trace=read_probe_trace(case)
        for index in (0,2,5):
            axes[1].plot(trace[:,0],trace[:,index+1]-273.15,label=f'{label}: probe {index+1}',lw=1)
    axes[0].set(xlabel='SIMPLE iteration (not seconds)',ylabel='Initial residual',title='Same-physics continuation')
    axes[1].set(xlabel='SIMPLE iteration (not seconds)',ylabel='Probe temperature (°C)',title='Restarted from saved iteration 967')
    for ax in axes:
        ax.legend(fontsize=7); ax.grid(alpha=.2); ax.axvline(967,color='black',ls='--',lw=.7)
    fig.suptitle('Thermal numerical diagnostics | residual, stationarity and flux checks are separate')
    for ext in ('png','pdf'):
        fig.savefig(a.output/f'thermal_continuation_diagnostics.{ext}',dpi=300,bbox_inches='tight')
    plt.close(fig)
    audits['limitations']=['No change to physical boundaries or solver relaxation; one bounded continuation, not a parameter search',
                           'Restart at 967 overlaps old log iterations 967–1000; histories are shown separately, not concatenated as one exact trajectory',
                           'A 0.01 K range over 100 iterations is a declared screening criterion, not a physical validation tolerance',
                           'Flux balance alone does not establish convergence; steady SIMPLE iteration is not physical time']
    paths=[a.restart_source/'log.solver',a.continuation/'log.solver',a.continuation/'log.checkMesh',a.continuation/'continuation.json',a.continuation/'system/fvSolution',Path(__file__)]
    continuation=json.loads((a.continuation/'continuation.json').read_text())
    for relative in ('system/fvSolution','system/fvSchemes','system/blockMeshDict','constant/g','constant/transportProperties'):
        source=a.restart_source/relative
        target=a.continuation/relative
        if source.read_bytes()!=target.read_bytes():
            raise ValueError('Continuation changed physical or numerical settings')
    for source,digest in continuation['source_sha256'].items():
        if sha256(Path(source).read_bytes()).hexdigest()!=digest:
            raise ValueError('Original restart source changed during continuation')
    for case in (a.restart_source,a.continuation):
        paths.extend((case/'postProcessing/sensors').glob('*/T'))
    audits['source_sha256']={str(path):sha256(path.read_bytes()).hexdigest() for path in paths}
    (a.output/'audit.json').write_text(json.dumps(audits,indent=2)+'\n')
    print(json.dumps({key:value for key,value in audits.items() if key!='source_sha256'},indent=2),flush=True)


if __name__=='__main__': main()
