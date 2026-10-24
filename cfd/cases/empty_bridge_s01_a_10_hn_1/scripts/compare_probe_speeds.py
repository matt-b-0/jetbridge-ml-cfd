#!/usr/bin/env python3
"""Compare final OpenFOAM probe velocity magnitudes to sensor air speed.

Usage from case root: python3 scripts/compare_probe_speeds.py
No 3D experimental velocity directions are assumed.
"""
from pathlib import Path
import re,csv,math
root=Path(__file__).resolve().parents[1]
files=list((root/'postProcessing'/'sensors').glob('*/U'))
if not files:
    raise SystemExit('No probe U output found. Run OpenFOAM solver first.')
p=sorted(files, key=lambda f: float(f.parent.name))[-1]
last=None
for line in p.read_text().splitlines():
    if not line.strip() or line.lstrip().startswith('#'):continue
    last=line
if last is None:raise SystemExit('No numeric probe data yet.')
vecs=re.findall(r'\(([^()]*)\)',last)
with (root/'data/processed/experimental_sensor_speeds.csv').open() as h:
    obs=list(csv.DictReader(h))
if len(vecs)!=len(obs):
    raise SystemExit(f'Expected {len(obs)} velocity vectors, found {len(vecs)} in {p}.')
errors=[]
with (root/'data/processed/cfd_vs_experiment.csv').open('w',newline='') as h:
    w=csv.writer(h)
    w.writerow(['sensor_id','x_m','y_m','z_m','experimental_speed_mps','cfd_speed_mps','error_mps'])
    for row,txt in zip(obs,vecs):
        u=list(map(float,txt.split())); speed=math.sqrt(sum(a*a for a in u))
        observed=float(row['speed_m_per_s']); error=speed-observed; errors.append(error)
        w.writerow([row['sensor_id'],row['x_m'],row['y_m'],row['z_m'],observed,speed,error])
print('Probe output:',p)
print('RMSE (m/s):',round(math.sqrt(sum(e*e for e in errors)/len(errors)),6))
print('MAE (m/s):',round(sum(map(abs,errors))/len(errors),6))
print('Results: data/processed/cfd_vs_experiment.csv')
