#!/usr/bin/env python3
"""Replace volumetricFlowRate in 0/U using positive HVAC Q.FS samples.

Usage: python3 scripts/set_hvac_flow.py --statistic mean
"""
from pathlib import Path
import argparse,csv,re,statistics
root=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser()
p.add_argument('--statistic',choices=['mean','median'],default='mean')
p.add_argument('--hvac',type=Path,default=root/'data/source/hvac_S01-A-10-HN-1.csv')
a=p.parse_args()
with a.hvac.open(encoding='latin1',newline='') as f:
    rows=list(csv.DictReader(f))
values=[float(r['Q.FS (lps)']) for r in rows if r['Q.FS (lps)'] and float(r['Q.FS (lps)'])>=0]
q=(statistics.mean(values) if a.statistic=='mean' else statistics.median(values))/1000
file=root/'0/U'; text=file.read_text();
text,n=re.subn(r'(volumetricFlowRate\s+constant\s+)[0-9.eE+-]+',lambda m:m.group(1)+f'{q:.9g}',text)
if n!=1:raise RuntimeError('Expected exactly one volumetricFlowRate entry in 0/U')
file.write_text(text)
print(f'Updated {file}: Q={q:.8f} m3/s from {len(values)} valid values')
