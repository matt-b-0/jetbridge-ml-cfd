"""Prepare a bounded continuation without changing physics or solver relaxation."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
import re
import shutil


def main():
    """Copy a saved thermal case to a new directory and extend its iteration cap."""
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--case',type=Path,required=True)
    p.add_argument('--time',type=int,default=967)
    p.add_argument('--iterations',type=int,default=1000)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    if a.output.exists() or a.iterations<100 or not (a.case/str(a.time)/'T').exists():
        p.error('New output, existing thermal saved field and at least 100 iterations required')
    a.output.mkdir(parents=True)
    for name in ('constant','system','data'):
        shutil.copytree(a.case/name,a.output/name)
    shutil.copytree(a.case/str(a.time),a.output/str(a.time))
    control=a.output/'system/controlDict'
    text=control.read_text()
    text=re.sub(r'startTime\s+\d+\s*;',f'startTime {a.time};',text)
    text=re.sub(r'endTime\s+\d+\s*;',f'endTime {a.time+a.iterations};',text)
    text=text.replace('fields (T);','fields (T U);')
    control.write_text(text)
    paths=[a.case/'system/fvSolution',a.case/'system/fvSchemes',a.case/'system/blockMeshDict',
           a.case/'constant/g',a.case/'constant/transportProperties']
    paths += [p for p in (a.case/str(a.time)).iterdir() if p.is_file()]
    manifest=dict(source=str(a.case),restart=a.time,end=a.time+a.iterations,
                  purpose='Bounded same-physics same-relaxation continuation; no experimental fitting',
                  diagnostics='Require configured residual convergence, finite bounded fields, flux balance and probe stationarity; no validation claim',
                  probe_range_screen_K=.01,probe_window_iterations=100,
                  source_sha256={str(p):sha256(p.read_bytes()).hexdigest() for p in paths},
                  script_sha256=sha256(Path(__file__).read_bytes()).hexdigest())
    (a.output/'continuation.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(a.output)


if __name__=='__main__':
    main()
