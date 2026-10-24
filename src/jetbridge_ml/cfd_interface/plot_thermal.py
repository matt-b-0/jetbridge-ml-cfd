"""Postprocess a thermal baseline and same-boundary zero-gravity control."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
import re
import shlex
import subprocess

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import Normalize, TwoSlopeNorm
import numpy as np
import pandas as pd
from scipy.spatial import cKDTree

from .plot_comparison import align_samples, mesh_profile
from jetbridge_ml.validation.metrics import regression_metrics


def _probe_temperature_drift(trace, final_iteration, window=100):
    """Return maximum per-probe range within the saved iterate's closed window."""
    trace=np.asarray(trace,float)
    keep=(trace[:,0]>=final_iteration-window) & (trace[:,0]<=final_iteration)
    selected=trace[keep,1:]
    if len(selected)<2:
        raise ValueError("Insufficient scheduled probes in the selected iteration window")
    return float(np.ptp(selected,axis=0).max())


def export(case, output, sensors):
    """Sample the latest saved thermal field and report its solver status.

    Parameters
    ----------
    case : pathlib.Path
        Solved thermal case with log.solver and saved U/T fields.
    output : pathlib.Path
        Existing output directory for export dictionaries and logs.
    sensors : pandas.DataFrame
        Matched absolute-metre experimental positions and measured means.

    Returns
    -------
    tuple
        Sensor comparison, metric/status dictionary, cross-section fields and
        longitudinal fields. All temperatures in the comparison use Celsius.
    """
    times = sorted((p for p in case.iterdir() if p.is_dir() and re.fullmatch(r"\d+(?:\.\d+)?",p.name)), key=lambda p:float(p.name))
    latest = times[-1].name
    if latest == "0":
        raise ValueError("No saved solution beyond initial conditions")
    log=(case/"log.solver").read_text()
    converged = f"SIMPLE solution converged in {latest} iterations" in log
    positions="\n".join(f"({r.x_m} {r.y_m} {r.z_m})" for r in sensors.itertuples())
    z=float(sensors.z_m.iloc[0])
    cfg="""FoamFile { version 2.0; format ascii; class dictionary; object thermalExport; }
functions {
 thermalSlices {
  type surfaces; libs ("libsampling.so"); writeControl writeTime;
  surfaceFormat raw; interpolationScheme cellPoint; fields (U T);
  surfaces (
   plane10 { type cuttingPlane; planeType pointAndNormal;
    pointAndNormalDict { basePoint (0 0 ZVALUE); normalVector (0 0 1); } interpolate true; }
   side { type cuttingPlane; planeType pointAndNormal;
    pointAndNormalDict { basePoint (0.694309 0 0); normalVector (1 0 0); } interpolate true; }
  );
 }
 speedSamples { type sets; libs ("libsampling.so"); writeControl writeTime;
  setFormat raw; interpolationScheme cell; fields (U);
  sets (station10 { type cloud; axis xyz; points (POSITIONS); });
 }
 finalBounds { type fieldMinMax; libs ("libfieldFunctionObjects.so"); fields (U T); }
 finalInlet { type surfaceFieldValue; libs ("libfieldFunctionObjects.so");
  regionType patch; name inlet; operation sum; writeFields false; fields (phi); }
 finalOutlet { type surfaceFieldValue; libs ("libfieldFunctionObjects.so");
  regionType patch; name outlet; operation sum; writeFields false; fields (phi); }
 temperatureSamples { type sets; libs ("libsampling.so"); writeControl writeTime;
  setFormat raw; interpolationScheme cell; fields (T);
  sets (station10 { type cloud; axis xyz; points (POSITIONS); });
 }
}""".replace("ZVALUE",str(z)).replace("POSITIONS",positions)
    dictionary=output/f"export_{case.name}.dict"
    dictionary.write_text(cfg)
    command=["buoyantBoussinesqSimpleFoam","-case",str(case),"-postProcess","-dict",str(dictionary),"-time",latest]
    shell="source /usr/lib/openfoam/openfoam2412/etc/bashrc; exec "+shlex.join(command)
    with (output/f"log.export_{case.name}").open("w") as handle:
        subprocess.run(["bash","-lc",shell],cwd=case,stdout=handle,stderr=subprocess.STDOUT,check=True)
    folder=case/"postProcessing"
    u_path=next((folder/f"speedSamples/{latest}").glob("station10_U.*"))
    t_path=next((folder/f"temperatureSamples/{latest}").glob("station10_T.*"))
    u=align_samples(sensors[["x_m","y_m","z_m"]],np.loadtxt(u_path))
    t=np.loadtxt(t_path)
    dist,idx=cKDTree(t[:,:3]).query(sensors[["x_m","y_m","z_m"]])
    if np.max(dist)>1e-7 or len(set(idx))!=len(sensors):
        raise ValueError("Temperature sample positions mismatch")
    if not np.isfinite(t).all():
        raise ValueError("Nonfinite sampled temperatures")
    result=sensors.copy()
    result["cfd_speed_mps"]=np.linalg.norm(u[:,3:],axis=1)
    result["cfd_temperature_C"]=t[idx,3]-273.15
    result["speed_delta_mps"]=result.cfd_speed_mps-result.speed_mps
    result["temperature_delta_K"]=result.cfd_temperature_C-result.temperature_C
    trace=np.loadtxt(case/"postProcessing/sensors/0/T")
    export_log=(output/f"log.export_{case.name}").read_text()
    speed_bound=re.search(r"max\(mag\(U\)\) = ([0-9.eE+-]+)",export_log)
    temperature_bounds=re.findall(r"(?:min|max)\(T\) = ([0-9.eE+-]+)",export_log)
    max_speed=float(speed_bound[1]) if speed_bound else float(np.linalg.norm(u[:,3:],axis=1).max())
    settings=json.loads((case/"data/processed/setup.json").read_text())
    low=min(settings["inlet_temperature_K"],settings["ambient_temperature_K"])
    high=max(settings["inlet_temperature_K"],settings["ambient_temperature_K"])
    overshoot=bool(temperature_bounds and
                   (min(map(float,temperature_bounds)) < low-1e-4 or max(map(float,temperature_bounds)) > high+1e-4))
    # Coarse case-specific sanity flag, not an experimental validation criterion.
    failed=bool(max_speed > 10 or overshoot)
    metrics=dict(time=latest,converged=converged,numerically_failed=failed,
                 physical_comparison_usable=bool(converged and not failed),
                 maximum_velocity_mps=max_speed,temperature_boundary_overshoot=overshoot,
                 sanity_velocity_threshold_mps=10,
                 scheduled_probe_temperature_range_last100_iterations_K=_probe_temperature_drift(trace,float(latest)),
                 speed=regression_metrics(result.speed_mps,result.cfd_speed_mps),
                 temperature=regression_metrics(result.temperature_C,result.cfd_temperature_C))
    surfaces={f:np.loadtxt(folder/f"thermalSlices/{latest}/{f}_plane10.raw") for f in ("U","T")}
    side={f:np.loadtxt(folder/f"thermalSlices/{latest}/{f}_side.raw") for f in ("U","T")}
    for name,array in {**surfaces,**{"side_"+k:v for k,v in side.items()}}.items():
        np.savetxt(output/f"{case.name}_{name}.csv",array,delimiter=",")
    return result,metrics,surfaces,side


def main():
    """Generate thermal speed/temperature comparisons with explicit assumptions."""
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case",required=True,type=Path)
    parser.add_argument("--control",required=True,type=Path)
    parser.add_argument("--output",required=True,type=Path)
    args=parser.parse_args()
    if args.output.exists():
        parser.error("Output directory must be new")
    output=args.output.resolve()
    output.mkdir(parents=True)
    sensors=pd.read_csv(args.case/"data/processed/experimental_sensors.csv")
    settings=json.loads((args.case/"data/processed/setup.json").read_text())
    thermal,metrics,surface,side=export(args.case.resolve(),output,sensors)
    control,control_metrics,_,_=export(args.control.resolve(),output,sensors)
    thermal.to_csv(output/"thermal_sensor_comparison.csv",index=False)
    control.to_csv(output/"control_sensor_comparison.csv",index=False)
    audit_paths=[]
    for directory,result in ((args.case,metrics),(args.control,control_metrics)):
        audit_paths.extend([directory/result["time"]/"U", directory/result["time"]/"T",
                            directory/"constant/g", directory/"constant/transportProperties",
                            directory/"system/fvSolution", directory/"system/fvSchemes",
                            directory/"system/blockMeshDict", directory/"system/controlDict",
                            directory/"0/T", directory/"0/U", directory/"log.solver"])
    manifest=dict(thermal=metrics,zero_gravity_control=control_metrics,setup=settings,
                  run_sha256={str(p):sha256(p.read_bytes()).hexdigest() for p in audit_paths},
                  note="Fixed walls at lab temperature are a surrogate, not measured wall temperatures; no CFD validation claimed",
                  script_sha256=sha256(Path(__file__).read_bytes()).hexdigest())
    (output/"metrics.json").write_text(json.dumps(manifest,indent=2)+"\n")
    width,zs,floors,ceilings=mesh_profile(args.case/"system/blockMeshDict")
    z=float(sensors.z_m.iloc[0])
    floor,ceiling=np.interp(z,zs,floors),np.interp(z,zs,ceilings)
    status="NUMERICALLY FAILED" if metrics["numerically_failed"] else ("converged" if metrics["converged"] else "NOT CONVERGED")
    plt.rcParams.update({"font.size":10,"axes.spines.top":False,"axes.spines.right":False})
    def save(fig,name):
        for ext in ("png","pdf"):
            fig.savefig(output/f"{name}.{ext}",dpi=180,bbox_inches="tight",facecolor="white")
        plt.close(fig)
    speed=surface["U"]
    temp=surface["T"]
    fields=[np.linalg.norm(speed[:,3:],axis=1),temp[:,3]-273.15]
    fig,axes=plt.subplots(2,3,figsize=(12,10),layout="constrained")
    for row,(field,observed,prediction,label,delta_label) in enumerate((
        (fields[0],thermal.speed_mps,thermal.cfd_speed_mps,"Speed (m/s)","CFD - measured speed (m/s)"),
        (fields[1],thermal.temperature_C,thermal.cfd_temperature_C,"Temperature (°C)","CFD - measured temperature (K)"))):
        xy=speed if row==0 else temp
        lo=0 if row==0 else min(field.min(),observed.min())
        hi=max(field.max(),observed.max())
        levels=np.linspace(lo,hi,25)
        norm=Normalize(lo,hi)
        axes[row,0].scatter(sensors.x_m,sensors.y_m,c=observed,cmap="viridis" if row==0 else "inferno",
                            norm=norm,s=110,edgecolors="black",linewidths=.5)
        image=axes[row,1].tricontourf(xy[:,0],xy[:,1],field,levels=levels,norm=norm,
                                   cmap="viridis" if row==0 else "inferno")
        axes[row,1].scatter(sensors.x_m,sensors.y_m,facecolors="none",edgecolors="white",s=70)
        delta=np.asarray(prediction-observed)
        limit=max(abs(delta).max(),1e-6)
        points=axes[row,2].scatter(sensors.x_m,sensors.y_m,c=delta,cmap="RdBu_r",
                    norm=TwoSlopeNorm(vmin=-limit,vcenter=0,vmax=limit),s=110,edgecolors="black",linewidths=.5)
        axes[row,0].set_title("Measured means")
        axes[row,1].set_title("Buoyant CFD")
        axes[row,2].set_title("Signed sensor differences")
        for ax in axes[row]:
            ax.set(xlim=(0,width),ylim=(floor,ceiling),xlabel="x (m)",ylabel="Absolute y (m)")
            ax.set_aspect("equal")
        fig.colorbar(image,ax=list(axes[row,:2]),label=label,shrink=.7)
        fig.colorbar(points,ax=axes[row,2],label=delta_label,shrink=.7)
    fig.suptitle(f"S01-AC-10-HN-1: cold supply | {status}, iteration {metrics['time']}\n"
                 f"Supply {settings['inlet_temperature_K']-273.15:.2f}°C; walls fixed at lab {settings['ambient_temperature_K']-273.15:.2f}°C (surrogate)")
    save(fig,"thermal_slices_and_deltas")
    fig,axes=plt.subplots(2,2,figsize=(10,8),layout="constrained")
    for col,x in enumerate(sorted(sensors.x_m.unique())):
        mask=thermal.x_m==x
        order=np.argsort(thermal.loc[mask,"y_m"])
        y=thermal.loc[mask,"y_m"].to_numpy()[order]
        for row,obs,pred,label in ((0,"speed_mps","cfd_speed_mps","Speed (m/s)"),
                                   (1,"temperature_C","cfd_temperature_C","Temperature (°C)")):
            ax=axes[row,col]
            ax.plot(thermal.loc[mask,obs].to_numpy()[order],y,"o-",color="#245b83",label="Experiment")
            if not metrics["numerically_failed"]:
                ax.plot(thermal.loc[mask,pred].to_numpy()[order],y,"s--",color="#bd4a31",label="Buoyant CFD (provisional)" if not metrics["converged"] else "Buoyant CFD")
            ax.plot(control.loc[mask,pred].to_numpy()[order],y,"^:",color="#777",label="Zero-gravity control")
            ax.set(xlabel=label,ylabel="Absolute y (m)",title=f"x = {x:.2f} m")
            ax.grid(alpha=.2)
            ax.legend(fontsize=8)
    profile_note=("Failed thermal profile omitted; control shown against measurements"
                  if metrics["numerically_failed"] else
                  f"Provisional buoyant speed RMSE {metrics['speed']['rmse']:.4f}; control {control_metrics['speed']['rmse']:.4f} m/s")
    fig.suptitle(f"Same cold experiment and boundaries | {status}\n{profile_note}")
    save(fig,"thermal_profiles_and_control")
    fig,axes=plt.subplots(2,1,figsize=(13,6),layout="constrained")
    for ax,key,label,cmap in ((axes[0],"T","Temperature (°C)","inferno"),(axes[1],"U","Speed (m/s)","viridis")):
        field=side[key]
        vals=field[:,3]-273.15 if key=="T" else np.linalg.norm(field[:,3:],axis=1)
        image=ax.tricontourf(field[:,2],field[:,1],vals,levels=35,cmap=cmap)
        # Raw surface files omit triangle connectivity. Clip the rendered
        # triangulation to the actual piecewise bridge outline, rather than
        # filling the convex hull outside the sloped/flat geometry.
        from matplotlib.patches import Polygon
        outline=np.column_stack([np.r_[zs,zs[::-1]],np.r_[floors,ceilings[::-1]]])
        image.set_clip_path(Polygon(outline,closed=True,transform=ax.transData))
        ax.plot(zs,floors,color="black",lw=1)
        ax.plot(zs,ceilings,color="black",lw=1)
        ax.axvline(z,color="cyan",ls="--",lw=1)
        ax.set(xlabel="z along bridge (m): exhaust at 0, supply at 18.105",ylabel="Absolute y (m)")
        ax.set_aspect("equal")
        fig.colorbar(image,ax=ax,label=label,shrink=.8)
    fig.suptitle(f"Thermal baseline centre-plane x = {width/2:.3f} m | {status}\n"
                "Dashed line: 10 ft sensor plane. Lab-temperature walls are a modelling surrogate.")
    save(fig,"thermal_longitudinal_slices")
    # Residuals are plotted against SIMPLE iteration, never physical seconds.
    residual_rows=[]
    iteration=None
    for line in (args.case/"log.solver").read_text().splitlines():
        time_match=re.match(r"Time = ([0-9.]+)",line)
        if time_match:
            iteration=float(time_match[1])
        residual=re.search(r"Solving for (Ux|Uy|Uz|T|p_rgh|k|epsilon), Initial residual = ([0-9.eE+-]+)",line)
        if residual and iteration is not None:
            residual_rows.append((iteration,residual[1],float(residual[2])))
    history=pd.DataFrame(residual_rows,columns=["iteration","field","initial_residual"])
    history=history.drop_duplicates(["iteration","field"],keep="first")
    history.to_csv(output/"thermal_residual_history.csv",index=False)
    fig,axes=plt.subplots(1,2,figsize=(12,4),layout="constrained")
    for field,group in history.groupby("field"):
        axes[0].semilogy(group.iteration,group.initial_residual,label=field)
    axes[0].set(xlabel="SIMPLE iteration (not seconds)",ylabel="Initial residual",title="Buoyant solver residual history")
    axes[0].legend(fontsize=8,ncol=2)
    axes[0].grid(alpha=.2)
    probe_file=args.case/"postProcessing/sensors/0/T"
    trace=np.loadtxt(probe_file)
    for index in (0,2,5):
        axes[1].plot(trace[:,0],trace[:,index+1]-273.15,label=f"Probe {index+1}, y={sensors.y_m.iloc[index]:.2f} m")
    axes[1].set(xlabel="SIMPLE iteration (not seconds)",ylabel="Temperature (°C)",title="Selected left-column probe evolution")
    axes[1].legend(fontsize=8)
    axes[1].grid(alpha=.2)
    fig.suptitle(f"Numerical diagnostics | {status} | Residual/probe stationarity required before interpretation")
    save(fig,"thermal_convergence_history")
    print(json.dumps({"thermal":metrics,"control":control_metrics},indent=2))


if __name__=="__main__":
    main()
