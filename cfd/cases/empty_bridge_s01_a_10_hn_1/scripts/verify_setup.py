#!/usr/bin/env python3
"""Static geometry and case sanity checks (no OpenFOAM executable needed)."""
from pathlib import Path
import csv,re,math,json
root=Path(__file__).resolve().parents[1]
mesh=(root/'system/blockMeshDict').read_text()
assert 'hex (0 1 2 3 4 5 6 7)' in mesh
assert 'hex (4 5 6 7 8 9 10 11)' in mesh
assert 'hex (8 9 10 11 12 13 14 15)' in mesh
assert 'hex (24 32 84)' not in mesh   # blocks must list vertices then cells
assert mesh.count('simpleGrading')==3
expected_blocks=[(0,1,2,3,4,5,6,7),(4,5,6,7,8,9,10,11),(8,9,10,11,12,13,14,15)]
blocks=[tuple(int(x) for x in s.split()) for s in re.findall(r'hex\s*\(([^()]+)\)',mesh)]
assert blocks==expected_blocks
verts_section=mesh.split('vertices',1)[1].split('blocks',1)[0]
verts=[tuple(map(float,v.split())) for v in re.findall(r'^\s*\(([-.\d ]+)\)\s*//\s*\d+',verts_section,re.M)]
assert len(verts)==16, len(verts)
w=1.388618; h=2.441448
stations=[(0.,0.),(8.2931,0.6731),(10.0965,0.6731),(18.10512,1.343025)]
for idx,(z,floor) in enumerate(stations):
    expected=[(0,floor,z),(w,floor,z),(w,floor+h,z),(0,floor+h,z)]
    for a,b in zip(verts[4*idx:4*idx+4],expected):
        assert all(math.isclose(x,y,abs_tol=2e-6) for x,y in zip(a,b)),(a,b)
with (root/'data/processed/experimental_sensor_speeds.csv').open() as f:
    points=list(csv.DictReader(f))
assert len(points)==12
for pt in points:
    x,y,z=[float(pt[t]) for t in ['x_m','y_m','z_m']]
    assert 0<x<w and math.isclose(z,3.05)
    assert stations[1][1]/stations[1][0]*z < y < stations[1][1]/stations[1][0]*z+h
Q=json.loads((root/'data/processed/flow_rate_summary.json').read_text())['selected_m3_per_s']
U=(root/'0/U').read_text()
m=re.search(r'volumetricFlowRate\s+constant\s+([0-9.eE+-]+)',U)
assert m and math.isclose(float(m.group(1)),Q,rel_tol=1e-7)
print('PASS: 3 connected blocks, 16 vertices, 12 in-domain probes, volume flow BC =',Q,'m3/s')
print('NOTE: this is NOT an OpenFOAM mesh quality check; run checkMesh after blockMesh.')
