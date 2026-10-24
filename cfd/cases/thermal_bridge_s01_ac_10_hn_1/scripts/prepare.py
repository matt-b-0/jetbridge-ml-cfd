"""Prepare a separate cold-supply Boussinesq baseline from matched FAA inputs."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
import shutil
import sys

import numpy as np
import pandas as pd

# Package should be installed or src supplied on PYTHONPATH.
from jetbridge_ml.data_processing.faa import read_speed_average


def foam(name, kind, text):
    """Return an OpenFOAM ASCII file with a standard header."""
    return f"FoamFile {{ version 2.0; format ascii; class {kind}; object {name}; }}\n{text}\n"


def main():
    """Generate a new thermal case without modifying the baseline or raw sources."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", required=True, type=Path)
    parser.add_argument("--template", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--no-buoyancy", action="store_true", help="Zero-gravity control with identical thermal boundaries")
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output must be a new case directory")
    run = "S01-AC-10-HN-1"
    periods = pd.read_csv(args.dataset / "06-Periods/Periods.csv", encoding="cp1252")
    row = periods[periods.Set == run]
    if len(row) != 1:
        raise ValueError("Expected one matched period")
    row = row.iloc[0]
    start, end = float(row["Stable-Start (sec)"]), float(row["Stable-End (sec)"])
    if not start < end:
        raise ValueError("Invalid stable window")
    # Published air-speed and temperature averages span the entire run.
    if (start != row["Entire Set-Start (sec)"] or end != row["Entire Set-End (sec)"]):
        raise ValueError("Stable window differs from published entire-run sensor averages")
    hvac_path = args.dataset / f"05-HVAC/{run}.csv"
    hvac = pd.read_csv(hvac_path, encoding="cp1252").replace(-9999, np.nan)
    hvac = hvac[hvac["Time (sec)"].between(start, end)]
    cols = ["T.db.SA (°C)", "Tdb.Lab (°C)", "Q.FS (lps)"]
    means = hvac[cols].mean()
    if not np.isfinite(means).all() or means.iloc[2] <= 0:
        raise ValueError("Invalid HVAC inputs")
    inlet_T, ambient_T = float(means.iloc[0]+273.15), float(means.iloc[1]+273.15)
    q = float(means.iloc[2]/1000)
    beta = 1/ambient_T
    sensors_path = args.dataset / f"03-Averages/V-{run}.txt"
    temperature_path = args.dataset / f"03-Averages/T-{run}.txt"
    sensors = read_speed_average(sensors_path)
    # Same BLOCK schema and coordinates as velocity, with temperature means in deg C.
    temp_text = temperature_path.read_text(encoding="cp1252")
    data = np.array([float(v) for v in temp_text.split("F=BLOCK", 1)[1].split()]).reshape(8, -1)
    if data.shape[1] != len(sensors):
        raise ValueError("Temperature sensor count mismatch")
    np.testing.assert_allclose(data[:3].T, sensors[["x_m","y_m","z_m"]], atol=1e-9)
    if not np.isfinite(data[3]).all() or np.any(data[3] == -9999):
        raise ValueError("Missing measured temperature")
    sensors["temperature_C"] = data[3]
    output = args.output
    for folder in ("0","constant","system","data/processed"):
        (output/folder).mkdir(parents=True, exist_ok=True)
    def write(path, content):
        (output/path).write_text(content)
    shutil.copyfile(args.template/"system/blockMeshDict", output/"system/blockMeshDict")
    shutil.copyfile(args.template/"constant/turbulenceProperties", output/"constant/turbulenceProperties")
    width,height=1.388618,2.441448
    bulk=q/(width*height)
    k=1.5*(.05*bulk)**2
    diameter=2*width*height/(width+height)
    epsilon=.09**.75*k**1.5/(.07*diameter)
    def scalar(name, dims, value, inlet, outlet, walls):
        write("0/"+name,foam(name,"volScalarField",f"""
dimensions {dims};
internalField uniform {value:.12g};
boundaryField
{{
 inlet {{ {inlet} }}
 outlet {{ {outlet} }}
 walls {{ {walls} }}
}}
"""))
    write("0/U",foam("U","volVectorField",f"""
dimensions [0 1 -1 0 0 0 0];
internalField uniform (0 0 {-bulk:.12g});
boundaryField
{{
 inlet {{ type flowRateInletVelocity; volumetricFlowRate constant {q:.12g}; value uniform (0 0 {-bulk:.12g}); }}
 outlet {{ type pressureInletOutletVelocity; value uniform (0 0 0); }}
 walls {{ type noSlip; }}
}}
"""))
    scalar("p","[0 2 -2 0 0 0 0]",0,*["type calculated; value uniform 0;"]*3)
    scalar("p_rgh","[0 2 -2 0 0 0 0]",0,
           "type fixedFluxPressure; rho rhok; value uniform 0;",
           "type fixedValue; value uniform 0;",
           "type fixedFluxPressure; rho rhok; value uniform 0;")
    scalar("T","[0 0 0 1 0 0 0]",ambient_T,
           f"type fixedValue; value uniform {inlet_T:.12g};",
           f"type inletOutlet; inletValue uniform {ambient_T:.12g}; value uniform {ambient_T:.12g};",
           f"type fixedValue; value uniform {ambient_T:.12g};")
    for name,value,wall in (("k",k,"kqRWallFunction"),("epsilon",epsilon,"epsilonWallFunction")):
        dims="[0 2 -2 0 0 0 0]" if name=="k" else "[0 2 -3 0 0 0 0]"
        scalar(name,dims,value, f"type fixedValue; value uniform {value:.12g};",
               f"type inletOutlet; inletValue uniform {value:.12g}; value uniform {value:.12g};",
               f"type {wall}; value uniform {value:.12g};")
    scalar("nut","[0 2 -1 0 0 0 0]",0,"type calculated; value uniform 0;",
           "type calculated; value uniform 0;","type nutkWallFunction; value uniform 0;")
    scalar("alphat","[0 2 -1 0 0 0 0]",0,"type calculated; value uniform 0;",
           "type calculated; value uniform 0;",
           "type alphatJayatillekeWallFunction; Prt 0.85; value uniform 0;")
    gravity = 0 if args.no_buoyancy else -9.81
    write("constant/g",foam("g","uniformDimensionedVectorField",f"dimensions [0 1 -2 0 0 0 0];\nvalue (0 {gravity} 0);"))
    write("constant/transportProperties",foam("transportProperties","dictionary",f"""
transportModel Newtonian;
nu 1.5e-5;
beta {beta:.12g};
TRef {ambient_T:.12g};
Pr 0.71;
Prt 0.85;
"""))
    write("system/fvSchemes",foam("fvSchemes","dictionary","""
ddtSchemes { default steadyState; }
gradSchemes { default Gauss linear; }
divSchemes
{
 default none;
 div(phi,U) bounded Gauss upwind;
 div(phi,T) bounded Gauss upwind;
 div(phi,k) bounded Gauss upwind;
 div(phi,epsilon) bounded Gauss upwind;
 div((nuEff*dev2(T(grad(U))))) Gauss linear;
}
laplacianSchemes { default Gauss linear corrected; }
interpolationSchemes { default linear; }
snGradSchemes { default corrected; }
wallDist { method meshWave; }
"""))
    write("system/fvSolution",foam("fvSolution","dictionary","""
solvers
{
 p_rgh { solver GAMG; tolerance 1e-8; relTol 0.01; smoother GaussSeidel; }
 "(U|T|k|epsilon)" { solver smoothSolver; smoother symGaussSeidel; tolerance 1e-9; relTol 0.1; }
}
SIMPLE
{
 nNonOrthogonalCorrectors 1;
 pRefCell 0; pRefValue 0;
 residualControl { p_rgh 1e-5; U 1e-5; T 1e-6; "(k|epsilon)" 1e-5; }
}
relaxationFactors
{
 fields { p_rgh 0.3; }
 equations { U 0.3; T 0.5; "(k|epsilon)" 0.5; }
}
"""))
    positions="\n".join(f"({r.x_m} {r.y_m} {r.z_m})" for r in sensors.itertuples())
    functions=f"""
sensors
{{
 type probes; libs ("libsampling.so"); fields (U T p_rgh);
 probeLocations ({positions});
 writeControl timeStep; writeInterval 10;
}}
"""
    for name in ("inlet","outlet"):
        functions+=f"""
{name}Flux
{{
 type surfaceFieldValue; libs ("libfieldFunctionObjects.so");
 regionType patch; name {name}; operation sum; writeFields false;
 fields (phi); writeControl timeStep; writeInterval 10;
}}
"""
    functions+="""
temperatureBounds
{
 type fieldMinMax; libs ("libfieldFunctionObjects.so"); fields (T);
 writeControl timeStep; writeInterval 10;
}
"""
    write("system/controlDict",foam("controlDict","dictionary",f"""
application buoyantBoussinesqSimpleFoam;
startFrom startTime; startTime 0; stopAt endTime; endTime 3000;
deltaT 1; writeControl timeStep; writeInterval 100; purgeWrite 3;
writeFormat ascii; writePrecision 10; writeCompression off;
timeFormat general; timePrecision 8; runTimeModifiable true;
functions {{ {functions} }}
"""))
    sensors.to_csv(output/"data/processed/experimental_sensors.csv",index=False)
    inputs=[hvac_path,sensors_path,temperature_path,args.dataset/"06-Periods/Periods.csv",
            args.dataset/"Data Dictionary.csv",args.template/"system/blockMeshDict"]
    settings=dict(run=run,no_buoyancy_control=args.no_buoyancy,inlet_temperature_K=inlet_T,ambient_temperature_K=ambient_T,
                  supply_minus_lab_K=inlet_T-ambient_T,flow_m3ps=q,
                  stable_window_epoch=[start,end],valid_hvac_counts=hvac[cols].count().to_dict(),
                  beta_per_K=beta,relative_density_variation=beta*abs(inlet_T-ambient_T),
                  wall_temperature="Fixed at lab mean: surrogate, NOT measured wall temperature",
                  assumptions=["steady Boussinesq, k-epsilon without explicit buoyancy turbulence production correction",
                               "full-face inlet, sealed walls, no manikins or conjugate wall conduction",
                               "baseline geometry unchanged, known ceiling discrepancy retained",
                               "initial ambient temperature and outlet backflow use lab mean",
                               "outlet fixed reduced hydrostatic pressure p_rgh=0",
                               "temperature field uses Kelvin; source experimental temperatures use Celsius"],
                  sha256={str(p):sha256(p.read_bytes()).hexdigest() for p in inputs},
                  generator_sha256=sha256(Path(__file__).read_bytes()).hexdigest())
    write("data/processed/setup.json",json.dumps(settings,indent=2)+"\n")
    write("Allrun","#!/usr/bin/env bash\nset -euo pipefail\ncd \"$(dirname \"$0\")\"\nblockMesh > log.blockMesh 2>&1\ncheckMesh > log.checkMesh 2>&1\nbuoyantBoussinesqSimpleFoam > log.solver 2>&1\n")
    print(json.dumps(settings,indent=2))


if __name__=="__main__":
    main()
