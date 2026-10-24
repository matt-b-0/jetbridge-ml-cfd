"""One-command analysis with explicit optional CFD inputs and a portable gallery."""
import argparse
from datetime import datetime,timezone
from hashlib import sha256
from importlib.metadata import version
import json
from pathlib import Path
import shutil
import subprocess
import sys
import pandas as pd


def gallery(output,destination):
    """Publish selected derived plots and small summaries into a new directory.

    Parameters
    ----------
    output, destination : pathlib.Path
        Completed analysis and new gallery destination.

    Returns
    -------
    None
        Raw data, point predictions and CFD fields are excluded.
    """
    if destination.exists():
        raise ValueError('Gallery destination must be new')
    destination.mkdir(parents=True)
    selected={'experimental':['experimental_nested_errors.png','summary.csv'],
              'paired':['paired_model_errors.png','paired_runs.csv','paired_stations.csv','paired_layouts.csv','versus_mean.csv','summary.json'],
              'sensor_design':['sensor_count_errors.png','summary.csv'],
              'matched':['matched_sampling_and_height.png','audit.json'],
              'thermal':['thermal_continuation_diagnostics.png','audit.json'],
              'verification':['mesh_coordinate_sensitivity.png','flow_transfer.png','mesh_metrics.csv','coordinate_metrics.csv','transfer_metrics.csv','summary.json']}
    lines=['# Reproducible analysis gallery','','Derived plots and small summary tables only. Experimental prediction, CFD reconstruction and thermal diagnostics remain distinct.','']
    for section,files in selected.items():
        directory=output/section
        if not directory.exists(): continue
        target=destination/section; target.mkdir()
        lines.extend(['## '+section.replace('_',' ').title(),''])
        for name in files:
            source=directory/name
            if source.exists():
                shutil.copyfile(source,target/name)
                relative=f'{section}/{name}'
                lines.extend([f'![{name}]({relative})' if source.suffix=='.png' else f'[{name}]({relative})',''])
    shutil.copyfile(output/'SUMMARY.md',destination/'SUMMARY.md')
    shutil.copyfile(output/'pipeline_manifest.json',destination/'pipeline_manifest.json')
    lines.extend(['[Run summary](SUMMARY.md)','', 'Thermal results remain unconverged; no experimental validation is claimed. Mesh checks assess sensitivity, not automatic mesh independence.'])
    (destination/'README.md').write_text('\n'.join(lines)+'\n')


def main():
    """Run experimental evaluation plus explicitly selected optional analyses."""
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('dataset','output'):
        p.add_argument('--'+name,type=Path,required=True)
    for name in ('baseline-case','cfd-candidates','cfd-reference','thermal-restart','thermal-continuation','verification-results','gallery'):
        p.add_argument('--'+name,type=Path)
    a=p.parse_args()
    for left,right in ((a.cfd_candidates,a.cfd_reference),(a.thermal_restart,a.thermal_continuation)):
        if (left is None)!=(right is None): p.error('Optional CFD candidate/reference and thermal restart/continuation inputs must be paired')
    if a.output.exists() or (a.gallery and a.gallery.exists()): p.error('Output and gallery must be new directories')
    if not (a.dataset/'03-Averages').is_dir(): p.error('Dataset 03-Averages directory missing')
    a.output.mkdir(parents=True)
    root=Path(__file__).resolve().parents[2]
    mesh=root/'cfd/cases/empty_bridge_s01_a_10_hn_1/system/blockMeshDict'
    commands=[]
    def run(module,args,section):
        command=[sys.executable,'-m',module,*map(str,args),'--output',str(a.output/section)]
        print('Running',section,flush=True)
        with (a.output/f'log.{section}').open('w') as log:
            subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,check=True)
        commands.append(dict(section=section,command=command))
    run('jetbridge_ml.experimental_svr',['--dataset',a.dataset,'--mesh',mesh],'experimental')
    run('jetbridge_ml.paired_analysis',['--metrics',a.output/'experimental/metrics.csv'],'paired')
    run('jetbridge_ml.stability_study',[],'stability')
    if a.cfd_candidates:
        run('jetbridge_ml.sensor_design_study',['--candidates',a.cfd_candidates,'--reference',a.cfd_reference],'sensor_design')
    if a.baseline_case:
        run('jetbridge_ml.cfd_interface.matched_audit',['--dataset',a.dataset,'--case',a.baseline_case],'matched')
    if a.thermal_restart:
        run('jetbridge_ml.cfd_interface.thermal_audit',['--restart-source',a.thermal_restart,'--continuation',a.thermal_continuation],'thermal')
    if a.verification_results:
        run('jetbridge_ml.cfd_interface.verification_results',['--study',a.verification_results],'verification')
    summary=pd.read_csv(a.output/'experimental/summary.csv')
    common=summary[summary.subset=='common_hull']
    lines=['# Analysis summary','','Experimental error is nested held-location prediction, not CFD agreement.','',
           '| Method | Mean per-run RMSE (m/s) | MAE (m/s) | Bias (m/s) |','| --- | ---: | ---: | ---: |']
    for row in common.itertuples():
        lines.append(f'| {row.method} | {row.mean_run_rmse:.6f} | {row.mean_run_mae:.6f} | {row.mean_run_bias:+.6f} |')
    pairs=json.loads((a.output/'paired/summary.json').read_text())
    lines.extend(['',f"RBF wins {pairs['rbf_wins']} of {pairs['runs']} paired run comparisons; SVR wins {pairs['svr_wins']}. Negative paired error favours RBF.",
                  '', 'Layout-stratified paired differences (descriptive; density and station are confounded):',
                  *[f"- {row['layout_points']}-point layouts: {row['runs']} runs; mean RBF-minus-SVR RMSE {row['mean_difference']:+.6f} m/s" for row in pairs['layout_strata']],
                  '', 'Runs and stations are descriptive groups sharing one apparatus; no IID-sensor statistical significance is claimed.','',
                  '## Completed sections','',*['- '+item['section'] for item in commands],'',
                  'Optional CFD sections are omitted unless their inputs are supplied. The runner does not silently solve CFD or download raw data. Thermal results remain separate from training/reference data.'])
    (a.output/'SUMMARY.md').write_text('\n'.join(lines)+'\n')
    manifest=dict(created_utc=datetime.now(timezone.utc).isoformat(),python=sys.version,commands=commands,
                  packages={name:version(name) for name in ('numpy','scipy','pandas','scikit-learn','matplotlib')},
                  code_sha256={str(f.relative_to(root)):sha256(f.read_bytes()).hexdigest() for f in (root/'src/jetbridge_ml').rglob('*.py')},
                  manifests={str(f.relative_to(a.output)):sha256(f.read_bytes()).hexdigest() for f in a.output.glob('*/manifest.json')})
    (a.output/'pipeline_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    if a.gallery: gallery(a.output,a.gallery)
    print('Analysis complete:',a.output,flush=True)


if __name__=='__main__': main()
