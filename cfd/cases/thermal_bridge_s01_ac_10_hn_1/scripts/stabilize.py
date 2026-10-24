"""Create a stronger-relaxation restart from a converged zero-gravity control."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
import shutil


def main():
    """Prepare a new restart without changing physical boundaries or source data."""
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--thermal",required=True,type=Path)
    parser.add_argument("--control",required=True,type=Path)
    parser.add_argument("--control-time",default="733")
    parser.add_argument("--output",required=True,type=Path)
    args=parser.parse_args()
    if args.output.exists():
        parser.error("Output must be a new directory")
    log=(args.control/"log.solver").read_text()
    if f"SIMPLE solution converged in {args.control_time} iterations" not in log:
        parser.error("Specified control time is not confirmed converged")
    args.output.mkdir(parents=True)
    for name in ("constant","system","data"):
        shutil.copytree(args.thermal/name,args.output/name)
    shutil.copytree(args.control/args.control_time,args.output/"0")
    # On-disk saved fields retain the same thermal/flow boundary conditions.
    solution=args.output/"system/fvSolution"
    s=solution.read_text().replace("p_rgh 0.3","p_rgh 0.1")
    s=s.replace('U 0.3; T 0.5; "(k|epsilon)" 0.5;',
                'U 0.1; T 0.2; "(k|epsilon)" 0.3;')
    solution.write_text(s)
    control=args.output/"system/controlDict"
    control.write_text(control.read_text().replace("endTime 3000","endTime 1000"))
    settings=args.output/"data/processed/setup.json"
    data=json.loads(settings.read_text())
    data["stabilization_attempt"]=dict(control=str(args.control),control_time=args.control_time,
        initial_field="converged zero-gravity control",p_relaxation=.1,U_relaxation=.1,
        T_relaxation=.2,turbulence_relaxation=.3,maximum_iterations=1000,
        physical_boundaries_unchanged=True,script_sha256=sha256(Path(__file__).read_bytes()).hexdigest())
    settings.write_text(json.dumps(data,indent=2)+"\n")
    print(args.output)


if __name__=="__main__":
    main()
