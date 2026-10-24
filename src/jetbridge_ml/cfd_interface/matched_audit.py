"""Audit raw averages, HVAC windows and isothermal sampling conventions."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
import re
import shlex
import subprocess
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from jetbridge_ml.cfd_interface.plot_comparison import align_samples,mesh_profile
from jetbridge_ml.data_processing.faa import read_speed_average
from jetbridge_ml.data_processing.raw_speed import read_raw_speed
from jetbridge_ml.validation.metrics import regression_metrics


def main():
    """Recompute matched source means without calibrating CFD or model targets."""
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('dataset','case','output'):
        p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args()
    if a.output.exists():
        p.error('Choose a fresh output directory')
    a.output.mkdir(parents=True)
    periods=pd.read_csv(a.dataset/'06-Periods/Periods.csv',encoding='cp1252')
    all_periods=[]
    inputs=[a.dataset/'06-Periods/Periods.csv',a.dataset/'Data Dictionary.csv']
    for path in sorted((a.dataset/'03-Averages').glob('V-S01-A-*-HN-*.txt')):
        run=path.stem[2:]
        selection=periods[periods.Set==run]
        if selection.empty:
            selection=periods[periods.Set.str.fullmatch(re.escape(run)+r'[AB]')]
        if len(selection) not in (1,2):
            raise ValueError('Missing or ambiguous source periods')
        # The 58 ft 24-sensor averages combine sequential A/B half-layouts.
        # Retain their measured HVAC periods separately; do not invent a union.
        for _,period in selection.iterrows():
            file=a.dataset/f'05-HVAC/{period.Set}.csv'
            hvac=pd.read_csv(file,encoding='cp1252').replace(-9999,np.nan)
            stable=hvac[hvac['Time (sec)'].between(period['Stable-Start (sec)'],period['Stable-End (sec)'])]
            entire=hvac[hvac['Time (sec)'].between(period['Entire Set-Start (sec)'],period['Entire Set-End (sec)'])]
            all_periods.append(dict(run_id=str(period.Set),average_run_id=run,station_ft=int(period.Station),replicate=str(period.Rep),
                               entire_start=float(period['Entire Set-Start (sec)']),entire_end=float(period['Entire Set-End (sec)']),
                               stable_start=float(period['Stable-Start (sec)']),stable_end=float(period['Stable-End (sec)']),
                               windows_equal=bool(period['Stable-Start (sec)']==period['Entire Set-Start (sec)'] and period['Stable-End (sec)']==period['Entire Set-End (sec)']),
                               full_file_q_m3s=float(hvac['Q.FS (lps)'].mean()/1000),entire_q_m3s=float(entire['Q.FS (lps)'].mean()/1000),stable_q_m3s=float(stable['Q.FS (lps)'].mean()/1000),
                               stable_q_count=int(stable['Q.FS (lps)'].count()),supply_C=float(entire['T.db.SA (°C)'].mean()),lab_C=float(entire['Tdb.Lab (°C)'].mean()),pressure_Pa=float(entire['dP (Pa)'].mean())))
            inputs.extend([file,path])
    inventory=pd.DataFrame(all_periods)
    inventory.to_csv(a.output/'run_boundary_inventory.csv',index=False)
    match=inventory[inventory.run_id=='S01-A-10-HN-1'].iloc[0]
    source=a.dataset/'03-Averages/V-S01-A-10-HN-1.txt'
    rawpath=a.dataset/'01-CSV/S01-A-10-HN-1.csv'
    raw=read_raw_speed(rawpath)
    observed=read_speed_average(source)
    _,zs,floors,tops=mesh_profile(a.case/'system/blockMeshDict')
    rows=[]
    for row,part in raw.groupby('source_row'):
        selection=part[part.time_sec.between(match.entire_start,match.entire_end)]
        published=observed[observed.source_row==row].iloc[0]
        rows.append(dict(source_row=int(row),raw_entire_file_mean_mps=float(part.speed_mps.mean()),
                         raw_period_mean_mps=float(selection.speed_mps.mean()),raw_speed_std_mps=float(part.speed_mps.std()),
                         raw_valid_count=int(part.speed_mps.count()),published_mean_mps=float(published.speed_mps),
                         raw_x_m=float(part.raw_x_m.iloc[0]),raw_local_height_m=float(part.raw_local_height_m.iloc[0]),
                         raw_nominal_z_m=float(part.raw_nominal_z_m.iloc[0])))
    audit=observed.merge(pd.DataFrame(rows),on='source_row',validate='one_to_one')
    audit['raw_mean_minus_published_mps']=audit.raw_entire_file_mean_mps-audit.speed_mps
    audit['floor_y_m']=np.interp(audit.z_m,zs,floors)
    audit['height_m']=audit.y_m-audit.floor_y_m
    audit['raw_x_minus_published_m']=audit.raw_x_m-audit.x_m
    audit['raw_nominal_z_minus_published_m']=audit.raw_nominal_z_m-audit.z_m
    audit['raw_local_height_minus_published_local_m']=audit.raw_local_height_m-audit.height_m
    positions='\n'.join('('+ ' '.join(map(str,r))+')' for r in audit[['x_m','y_m','z_m']].to_numpy())
    functions=[]
    for name,scheme in (('auditCell','cell'),('auditCellPoint','cellPoint')):
        functions.append(f'{name} {{ type sets; libs ("libsampling.so"); writeControl writeTime; setFormat raw; interpolationScheme {scheme}; fields (U); sets (matched {{ type cloud; axis xyz; points ({positions}); }}); }}')
    dictionary=a.output/'sampling.dict'
    dictionary.write_text('FoamFile { version 2.0; format ascii; class dictionary; object matchedAudit; } functions { '+'\n'.join(functions)+' }')
    command=['simpleFoam','-case',str(a.case),'-postProcess','-time','237','-dict',str(dictionary)]
    with (a.output/'log.sampling').open('w') as log:
        subprocess.run(['bash','-lc','source /usr/lib/openfoam/openfoam2412/etc/bashrc; exec '+shlex.join(command)],stdout=log,stderr=subprocess.STDOUT,check=True)
    stats={}
    for name,scheme in (('auditCell','cell'),('auditCellPoint','cellPoint')):
        data=np.loadtxt(next((a.case/f'postProcessing/{name}/237').glob('matched_U.*')))
        data=align_samples(audit[['x_m','y_m','z_m']],data)
        audit[f'cfd_{scheme}_speed_mps']=np.linalg.norm(data[:,3:],axis=1)
        audit[f'{scheme}_error_mps']=audit[f'cfd_{scheme}_speed_mps']-audit.speed_mps
        stats[scheme]=dict(**regression_metrics(audit.speed_mps,audit[f'cfd_{scheme}_speed_mps']),
                           pearson_r=float(np.corrcoef(audit.speed_mps,audit[f'cfd_{scheme}_speed_mps'])[0,1]),
                           error_height_pearson_r=float(np.corrcoef(audit.height_m,audit[f'{scheme}_error_mps'])[0,1]))
    audit.to_csv(a.output/'matched_sensor_audit.csv',index=False)
    q=float(re.search(r'volumetricFlowRate\s+constant\s+([\d.eE+-]+)',(a.case/'0/U').read_text())[1])
    result=dict(run_id='S01-A-10-HN-1',saved_iteration=237,configured_q_m3s=q,matched_hvac=match.to_dict(),
                q_minus_entire_mean_m3s=q-float(match.entire_q_m3s),
                max_raw_mean_rounding_difference_mps=float(abs(audit.raw_mean_minus_published_mps).max()),
                raw_means_match_published_3decimal_rounding=bool((abs(audit.raw_mean_minus_published_mps)<=.000501).all()),
                max_coordinate_rounding_difference_m=dict(x=float(abs(audit.raw_x_minus_published_m).max()),z=float(abs(audit.raw_nominal_z_minus_published_m).max()),local_height=float(abs(audit.raw_local_height_minus_published_local_m).max())),
                sampling_metrics=stats,
                limitations=['Raw inches are nominal local coordinates; published absolute metre coordinates remain sampling authority',
                             'Raw sample standard deviation is temporal variability, not uncertainty of the mean',
                             'Correlations are descriptive for 12 spatial samples and do not establish validation',
                             'Only the selected 10 ft run is matched to this CFD inlet; inventory does not match every other station to this solution'])
    def save(fig,name):
        for ext in ('png','pdf'):
            fig.savefig(a.output/f'{name}.{ext}',dpi=300,bbox_inches='tight')
        plt.close(fig)
    fig,axes=plt.subplots(1,2,figsize=(10,4.2),layout='constrained')
    for scheme in ('cell','cellPoint'):
        axes[0].scatter(audit.speed_mps,audit[f'cfd_{scheme}_speed_mps'],label=scheme,s=45)
        axes[1].plot(audit[f'{scheme}_error_mps'],audit.height_m,'o',label=scheme)
    axes[0].plot([.08,.2],[.08,.2],'k--',lw=.8)
    axes[0].set(xlabel='Measured mean speed (m/s)',ylabel='CFD speed (m/s)',title='Matched source coordinates')
    axes[1].axvline(0,color='black',lw=.8)
    axes[1].set(xlabel='CFD minus measured speed (m/s)',ylabel='Height above local floor (m)',title='Sampling-convention sensitivity')
    for ax in axes:
        ax.legend(); ax.grid(alpha=.2)
    fig.suptitle('Isothermal 10 ft audit | CFD converged, physical validation unresolved')
    save(fig,'matched_sampling_and_height')
    fig,axes=plt.subplots(3,1,figsize=(10,8),layout='constrained')
    for ax,index in zip(axes,(0,2,5)):
        part=raw[(raw.source_row==index)&raw.time_sec.between(match.entire_start,match.entire_end)]
        row=audit[audit.source_row==index].iloc[0]
        ax.plot(part.time_sec-match.entire_start,part.speed_mps,lw=.6,alpha=.55,label='Raw speed')
        ax.axhline(row.speed_mps,color='#26749c',label='Published mean')
        ax.axhline(row.cfd_cellPoint_speed_mps,color='#bd4932',ls='--',label='CFD cellPoint speed')
        ax.set(xlabel='Elapsed measurement time (s)',ylabel='Speed (m/s)',title=f'Source sensor row {index+1}, local height {row.height_m:.2f} m')
        ax.legend(fontsize=8,ncol=3)
    save(fig,'raw_measurements_and_cfd')
    fig,axes=plt.subplots(1,2,figsize=(10,4),layout='constrained')
    axes[0].scatter(inventory.station_ft,inventory.entire_q_m3s,s=25,label='Individual measured runs')
    axes[0].axhline(q,color='#bd4932',ls='--',label='Single CFD supply setting')
    axes[0].set(xlabel='Station label (ft)',ylabel='Supplied flow (m³/s)',title='Operating-condition inventory')
    axes[0].legend(fontsize=8)
    axes[1].bar(audit.source_row+1,audit.raw_mean_minus_published_mps)
    axes[1].axhline(.0005,color='black',ls='--'); axes[1].axhline(-.0005,color='black',ls='--')
    axes[1].set(xlabel='Source sensor row',ylabel='Raw mean minus published mean (m/s)',title='Published three-decimal rounding check')
    save(fig,'boundary_and_raw_average_audit')
    inputs.extend([rawpath,a.case/'0/U',a.case/'237/U',a.case/'system/blockMeshDict',Path(__file__),Path(__file__).parents[1]/'data_processing/raw_speed.py'])
    result['sha256']={str(path):sha256(path.read_bytes()).hexdigest() for path in inputs}
    (a.output/'audit.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='sha256'},indent=2),flush=True)


if __name__=='__main__':
    main()
