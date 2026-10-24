"""Export consistent virtual training sensors and held-out dense CFD planes."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
import shlex
import subprocess

import numpy as np
import pandas as pd

from .plot_comparison import align_samples, mesh_profile
from jetbridge_ml.data_processing.faa import read_speed_average

TRAIN_STATIONS=(10,22,34,46,58)
TEST_STATIONS=(16,28,40,52)


def main():
    """Sample a confirmed converged isothermal field without changing its inputs."""
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case",required=True,type=Path)
    parser.add_argument("--dataset",required=True,type=Path)
    parser.add_argument("--output",required=True,type=Path)
    parser.add_argument("--time",default="237")
    parser.add_argument("--nx",type=int,default=40)
    parser.add_argument("--ny",type=int,default=60)
    args=parser.parse_args()
    if args.output.exists():
        parser.error("Output must be new")
    if min(args.nx,args.ny)<2:
        parser.error("At least two grid points per transverse dimension")
    case=args.case.resolve()
    if f"SIMPLE solution converged in {args.time} iterations" not in (case/"log.simpleFoam").read_text():
        parser.error("Saved field is not confirmed converged in the solver log")
    if "Mesh OK." not in (case/"log.checkMesh").read_text():
        parser.error("Mesh check not confirmed")
    width,zs,floors,ceilings=mesh_profile(case/"system/blockMeshDict")
    sparse={}
    dense={}
    source_paths=[]
    for station in sorted(TRAIN_STATIONS+TEST_STATIONS):
        path=args.dataset/f"03-Averages/V-S01-A-{station}-HN-1.txt"
        source_paths.append(path)
        # Only geometry is retained; experimental speeds are never training labels.
        frame=read_speed_average(path)[["x_m","y_m","z_m","source_row"]].copy()
        frame["station_ft"]=station
        frame["height_m"]=frame.y_m-np.interp(frame.z_m,zs,floors)
        sparse[station]=frame
        if station in TEST_STATIONS:
            z=float(frame.z_m.iloc[0])
            floor,ceiling=np.interp(z,zs,floors),np.interp(z,zs,ceilings)
            gx,gy=np.meshgrid((np.arange(args.nx)+.5)*width/args.nx,
                             floor+(np.arange(args.ny)+.5)*(ceiling-floor)/args.ny)
            dense[station]=pd.DataFrame(dict(x_m=gx.ravel(),y_m=gy.ravel(),z_m=z,
                station_ft=station,height_m=gy.ravel()-floor,
                grid_row=np.repeat(np.arange(args.ny),args.nx),
                grid_col=np.tile(np.arange(args.nx),args.ny)))
    def sets(frames):
        result=[]
        for station,frame in frames.items():
            points="\n".join(f"({r.x_m:.12g} {r.y_m:.12g} {r.z_m:.12g})" for r in frame.itertuples())
            result.append(f"station{station} {{ type cloud; axis xyz; points ({points}); }}")
        return "\n".join(result)
    config='FoamFile { version 2.0; format ascii; class dictionary; object virtualSensorExport; }\nfunctions {\n'
    for name,frames in (("virtualSparse",sparse),("virtualDense",dense)):
        config+=f"""{name}
{{
 type sets; libs ("libsampling.so"); writeControl writeTime;
 setFormat raw; interpolationScheme cellPoint; fields (U);
 sets ({sets(frames)});
}}
"""
    config+="}\n"
    args.output.mkdir(parents=True)
    dictionary=(args.output/"virtualSensorExportDict").resolve()
    dictionary.write_text(config)
    command=["simpleFoam","-case",str(case),"-postProcess","-dict",str(dictionary),"-time",args.time]
    shell="source /usr/lib/openfoam/openfoam2412/etc/bashrc; exec "+shlex.join(command)
    with (args.output/"log.sampling").open("w") as handle:
        subprocess.run(["bash","-lc",shell],cwd=case,stdout=handle,stderr=subprocess.STDOUT,check=True)
    for name,frames in (("virtualSparse",sparse),("virtualDense",dense)):
        rows=[]
        for station,frame in frames.items():
            matches=list((case/f"postProcessing/{name}/{args.time}").glob(f"station{station}_U.*"))
            if len(matches)!=1:
                raise ValueError(f"Missing unique sample file for {station}")
            sample=align_samples(frame[["x_m","y_m","z_m"]],np.loadtxt(matches[0]))
            frame=frame.copy()
            frame[["Ux_mps","Uy_mps","Uz_mps"]]=sample[:,3:]
            frame["speed_mps"]=np.linalg.norm(sample[:,3:],axis=1)
            frame["data_role"]="CFD virtual sensors" if name=="virtualSparse" else "CFD held-out reference"
            rows.append(frame)
        pd.concat(rows,ignore_index=True).to_csv(args.output/("sparse.csv" if name=="virtualSparse" else "dense_test.csv"),index=False)
    paths=[case/args.time/"U",case/"system/blockMeshDict",case/"system/controlDict",
           case/"log.simpleFoam",case/"log.checkMesh"]+source_paths
    manifest=dict(case=str(case),time=args.time,train_stations=list(TRAIN_STATIONS),
                  test_stations=list(TEST_STATIONS),nx=args.nx,ny=args.ny,
                  sampling="cellPoint for both sparse inputs and dense reference; speed=norm(U)",
                  coordinate_frame="absolute source xyz metres retained; local height is a separate derived feature",
                  sha256={str(p):sha256(p.read_bytes()).hexdigest() for p in paths},
                  exporter_sha256=sha256(Path(__file__).read_bytes()).hexdigest(),
                  limitations=["Single CFD solution, not experimental truth",
                               "Mesh sensitivity and physical validation remain outstanding",
                               "No thermal failed/unconverged fields used",
                               "Dense queries oversample the discrete CFD field; they are not independent experiments",
                               "Actual geometry retains documented upper-ceiling discrepancy"])
    (args.output/"sampling_manifest.json").write_text(json.dumps(manifest,indent=2)+"\n")
    print("Training stations:",TRAIN_STATIONS,"Test stations:",TEST_STATIONS)
    print("Samples exported to",args.output)


if __name__=="__main__":
    main()
