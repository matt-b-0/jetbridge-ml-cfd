"""Reproduce reduced PDE/relaxation experiments and audit existing CFD logs."""
import argparse
from datetime import datetime, timezone
from hashlib import sha256
from importlib.metadata import version
import json
from pathlib import Path
import platform
import re

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from .validation.stability import diffusion_laplacian, heat_evolution, weighted_jacobi
from .interpolation.sensitivity import interpolation_noise_gain
from .cfd_interface.plot_comparison import mesh_profile


def _residuals(case):
    rows, current = [], None
    for line in (case/"log.solver").read_text().splitlines():
        time = re.match(r"Time = ([0-9.]+)",line)
        if time:
            current = float(time[1])
        value = re.search(r"Solving for (Ux|Uy|Uz|T|p_rgh|k|epsilon), Initial residual = ([0-9.eE+-]+)",line)
        if value and current is not None:
            rows.append((current,value[1],float(value[2])))
    return pd.DataFrame(rows,columns=["iteration","field","initial_residual"]).drop_duplicates(["iteration","field"],keep="first")


def main():
    """Run fixed, untuned numerical verification experiments into a new folder."""
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output",required=True,type=Path)
    parser.add_argument("--thermal",type=Path)
    parser.add_argument("--control",type=Path)
    parser.add_argument("--stabilized",type=Path)
    parser.add_argument("--sensors",type=Path,default=Path(__file__).resolve().parents[2]/"cfd/cases/empty_bridge_s01_a_10_hn_1/data/processed/experimental_sensor_speeds.csv")
    parser.add_argument("--mesh",type=Path,default=Path(__file__).resolve().parents[2]/"cfd/cases/empty_bridge_s01_a_10_hn_1/system/blockMeshDict")
    args=parser.parse_args()
    if args.output.exists():
        parser.error("Choose a new output directory")
    out=args.output
    out.mkdir(parents=True)
    plt.rcParams.update({"font.size":10,"axes.spines.top":False,"axes.spines.right":False})
    def save(fig,name):
        for suffix in ("png","pdf"):
            fig.savefig(out/f"{name}.{suffix}",dpi=180,bbox_inches="tight",facecolor="white")
        plt.close(fig)

    methods={"FTCS":0.,"Implicit Euler":1.,"Crank-Nicolson":.5}
    intervals=20
    x=np.arange(1,intervals)/intervals
    initial=.5*np.sin(np.pi*x)+.01*np.sin((intervals-1)*np.pi*x)
    # Exact continuum solution: both sine modes obey homogeneous endpoints.
    def exact(tau):
        return (.5*np.exp(-np.pi**2*tau)*np.sin(np.pi*x)
                +.01*np.exp(-((intervals-1)*np.pi)**2*tau)*np.sin((intervals-1)*np.pi*x))
    trials=[]
    fig,axes=plt.subplots(1,3,figsize=(13,4),layout="constrained")
    for ax,r in zip(axes,(.25,.75,5.)):
        for name,theta in methods.items():
            tau,history,rho=heat_evolution(intervals,r,theta,40,initial)
            errors=np.array([np.linalg.norm(u-exact(t))/np.sqrt(len(x)) for t,u in zip(tau,history)])
            ax.semilogy(tau[1:],errors[1:],label=f"{name}, rho={rho:.3f}")
            trials.append(dict(method=name,r=r,steps=40,final_tau=float(tau[-1]),
                               spectral_radius=rho,final_rmse_K=float(errors[-1]),
                               maximum_abs_perturbation_K=float(abs(history).max())))
        ax.set(xlabel="Dimensionless time alpha*t/L²",ylabel="Error to exact PDE solution (K)",title=f"Diffusion number r = {r}")
        ax.legend(fontsize=8)
        ax.grid(alpha=.2)
    fig.suptitle("Reduced 1D diffusion: stability differs from accuracy (not a CFD time-step test)")
    save(fig,"diffusion_stability")
    pd.DataFrame(trials).to_csv(out/"diffusion_trials.csv",index=False)

    # Highest finite-grid mode shows sign-alternating Crank-Nicolson damping.
    mode=np.sin((intervals-1)*np.pi*x)
    fig,axes=plt.subplots(1,2,figsize=(11,4),layout="constrained")
    for name,theta in methods.items():
        _,history,rho=heat_evolution(intervals,5,theta,12,mode)
        amplitude=history@mode/(mode@mode)
        if name!="FTCS":
            axes[0].plot(np.arange(13),amplitude,"o-",label=name)
        axes[1].semilogy(np.arange(13),abs(amplitude),label=name)
    axes[0].axhline(0,color="black",lw=.7)
    axes[0].set(xlabel="Time-step index",ylabel="Signed high-frequency amplitude",title="Stable can still oscillate")
    axes[1].set(xlabel="Time-step index",ylabel="Absolute high-frequency amplitude",title="FTCS grows; implicit methods remain bounded")
    for ax in axes:
        ax.legend()
        ax.grid(alpha=.2)
    fig.suptitle("r = 5: high-frequency mode (controlled verification example)")
    save(fig,"high_frequency_damping")

    # Separate temporal error from spatial error using the known semi-discrete mode.
    orders=[]
    n=40
    xx=np.arange(1,n)/n
    final_tau=.02
    eig=-4*n*n*np.sin(np.pi/(2*n))**2
    reference=np.sin(np.pi*xx)*np.exp(eig*final_tau)
    for name,theta in (("Implicit Euler",1.),("Crank-Nicolson",.5)):
        for steps in (4,8,16,32,64):
            dt=final_tau/steps
            _,history,_=heat_evolution(n,dt*n*n,theta,steps,np.sin(np.pi*xx))
            error=np.linalg.norm(history[-1]-reference)/np.sqrt(n-1)
            orders.append(dict(method=name,steps=steps,dtau=dt,temporal_rmse_K=float(error)))
    order_frame=pd.DataFrame(orders)
    order_frame.to_csv(out/"temporal_refinement.csv",index=False)
    spatial=[]
    for n in (10,20,40,80):
        xx=np.arange(1,n)/n
        semi=np.sin(np.pi*xx)*np.exp(-4*n*n*np.sin(np.pi/(2*n))**2*final_tau)
        continuous=np.sin(np.pi*xx)*np.exp(-np.pi*np.pi*final_tau)
        spatial.append(dict(intervals=n,dx=1/n,spatial_rmse_K=float(np.linalg.norm(semi-continuous)/np.sqrt(n-1))))
    spatial_frame=pd.DataFrame(spatial)
    spatial_frame.to_csv(out/"spatial_refinement.csv",index=False)
    fig,axes=plt.subplots(1,2,figsize=(11,4),layout="constrained")
    for name,group in order_frame.groupby("method",sort=False):
        axes[0].loglog(group.dtau,group.temporal_rmse_K,"o-",label=name)
    axes[0].set(xlabel="Dimensionless time step",ylabel="Error to semi-discrete exact solution (K)",title="Time-refinement check")
    axes[0].legend()
    axes[1].loglog(spatial_frame.dx,spatial_frame.spatial_rmse_K,"o-")
    axes[1].set(xlabel="Dimensionless spatial step",ylabel="Spatial error to exact PDE solution (K)",title="Central-difference spatial check")
    for ax in axes:
        ax.grid(alpha=.2,which="both")
    from matplotlib.ticker import FixedLocator, FormatStrFormatter, NullFormatter
    for ax,values in zip(axes,(sorted(order_frame.dtau.unique()),sorted(spatial_frame.dx.unique()))):
        ax.xaxis.set_major_locator(FixedLocator(values))
        ax.xaxis.set_major_formatter(FormatStrFormatter("%.1e"))
        ax.xaxis.set_minor_formatter(NullFormatter())
        ax.tick_params(axis="x",labelsize=8)
    save(fig,"accuracy_refinement")

    # Elliptic BVP: -u''=pi² sin(pi*x); discrete solution is the reference for iteration.
    n=20
    xx=np.arange(1,n)/n
    a=-n*n*diffusion_laplacian(n)
    b=np.pi*np.pi*np.sin(np.pi*xx)
    reference=np.linalg.solve(a,b)
    relaxation=[]
    fig,axes=plt.subplots(1,3,figsize=(14,4),layout="constrained")
    for omega in (.2,.6,1.,1.2):
        initial=.01*np.sin((n-1)*np.pi*xx)
        history,residual,rho=weighted_jacobi(a,b,omega,400,initial)
        axes[0 if omega<=1 else 1].semilogy(np.arange(401),residual,label=f"omega={omega}, rho={rho:.4f}")
        relaxation.append(dict(omega=omega,spectral_radius=rho,relative_residual=float(residual[-1]),
                               discrete_solution_rmse=float(np.linalg.norm(history[-1]-reference)/np.sqrt(n-1))))
    axes[0].set(xlabel="Jacobi iteration",ylabel="Relative linear-system residual",title="Convergent relaxation weights")
    axes[0].legend(fontsize=8)
    axes[1].set(xlabel="Jacobi iteration",ylabel="Relative linear-system residual",title="Over-relaxation diverges")
    axes[1].legend(fontsize=8)
    weights=np.linspace(.01,1.3,200)
    # Scalar linearised fixed-point examples, not inferred CFD Jacobians.
    axes[2].plot(weights,abs(1-weights+weights*(-1.2)),label="Illustrative map eigenvalue -1.2")
    axes[2].plot(weights,abs(1-weights+weights*(1.1)),label="Illustrative map eigenvalue +1.1")
    axes[2].axhline(1,color="black",ls="--",label="Amplification magnitude = 1")
    axes[2].set(xlabel="Field-update relaxation weight",ylabel="Error amplification magnitude",
                title="Damping cannot fix every unstable map")
    axes[2].legend(fontsize=8)
    for ax in axes:
        ax.grid(alpha=.2)
    fig.suptitle("Reduced relaxation examples: analogy, not an OpenFOAM SIMPLE stability proof")
    save(fig,"relaxation_stability")
    pd.DataFrame(relaxation).to_csv(out/"relaxation_trials.csv",index=False)

    sensors=pd.read_csv(args.sensors)
    if sensors.z_m.nunique()!=1:
        raise ValueError("Sensitivity example requires a single sensor plane")
    width,zs,floors,ceilings=mesh_profile(args.mesh)
    station=float(sensors.z_m.iloc[0])
    floor,ceiling=np.interp(station,zs,floors),np.interp(station,zs,ceilings)
    gx,gy=np.meshgrid(np.linspace(0,width,50),np.linspace(floor,ceiling,70))
    queries=np.column_stack([gx.ravel(),gy.ravel()])
    locations=sensors[["x_m","y_m"]].to_numpy()
    gain_rows,table=[],[]
    gains={}
    for method in ("nearest","linear","rbf"):
        gain,weights,inside=interpolation_noise_gain(method,locations,queries)
        gains[method]=gain
        valid=np.isfinite(gain)
        table.append(dict(method=method,queries=len(gain),supported=int(valid.sum()),
                          coverage=float(valid.mean()),max_gain=float(gain[valid].max()),
                          max_gain_inside=float(gain[valid & inside].max()),
                          max_gain_outside=float(gain[valid & ~inside].max()) if np.any(valid & ~inside) else np.nan,
                          example_noise_bound_mps=.001,
                          max_worst_case_prediction_change_mps=.001*float(gain[valid].max())))
        gain_rows.extend(dict(method=method,x_m=float(q[0]),y_m=float(q[1]),
                              inside_hull=bool(h),gain=float(g))
                         for q,g,h in zip(queries,gain,inside))
    pd.DataFrame(table).to_csv(out/"interpolation_noise_summary.csv",index=False)
    pd.DataFrame(gain_rows).to_csv(out/"interpolation_noise_map.csv",index=False)
    from matplotlib.colors import Normalize
    norm=Normalize(1,max(np.nanmax(a) for a in gains.values()))
    cmap=plt.get_cmap("magma").copy()
    cmap.set_bad("#d9d9d9")
    fig,axes=plt.subplots(1,3,figsize=(10,6),layout="constrained")
    for ax,method in zip(axes,("nearest","linear","rbf")):
        image=ax.pcolormesh(gx,gy,np.ma.masked_invalid(gains[method].reshape(gx.shape)),
                           shading="auto",norm=norm,cmap=cmap)
        ax.scatter(locations[:,0],locations[:,1],facecolors="none",edgecolors="cyan",s=50)
        ax.set(xlabel="x (m)",ylabel="Absolute y (m)",title=method,xlim=(0,width),ylim=(floor,ceiling))
        ax.set_aspect("equal")
    fig.colorbar(image,ax=list(axes),label="Worst-case input-noise amplification (dimensionless)",shrink=.65)
    fig.suptitle("Actual 12-sensor layout: sensitivity, not prediction accuracy\nGrey = unsupported linear extrapolation; cyan = sensor locations")
    save(fig,"interpolation_noise_amplification")

    cases={name:path for name,path in (("Original thermal",args.thermal),("Zero-gravity control",args.control),
                                      ("Stabilized thermal",args.stabilized)) if path is not None}
    audits=[]
    hashes={}
    if cases:
        fig,axes=plt.subplots(len(cases),2,figsize=(12,3.5*len(cases)),squeeze=False,layout="constrained")
        for row,(name,path) in enumerate(cases.items()):
            log=(path/"log.solver").read_text()
            history=_residuals(path)
            for field in ("p_rgh","T","Ux"):
                group=history[history.field==field]
                axes[row,0].semilogy(group.iteration,group.initial_residual,label=field)
            trace=np.loadtxt(path/"postProcessing/sensors/0/T")
            for index in (0,2,5):
                axes[row,1].plot(trace[:,0],trace[:,index+1]-273.15,label=f"Probe {index+1}")
            axes[row,0].set(title=name,xlabel="SIMPLE iteration (not seconds)",ylabel="Initial residual")
            axes[row,1].set(title="Scheduled temperature probes",xlabel="SIMPLE iteration (not seconds)",ylabel="Temperature (°C)")
            for ax in axes[row]:
                ax.legend(fontsize=8)
                ax.grid(alpha=.2)
            last=history.iteration.max()
            converged=bool(re.search(r"SIMPLE solution converged in \d+ iterations",log))
            recent=trace[trace[:,0]>=last-100,1:]
            for field,group in history.groupby("field"):
                tail=group[group.iteration>=last-100]
                audits.append(dict(case=name,field=field,last_iteration=last,solver_converged=converged,
                                   final_initial_residual=float(group.iloc[-1].initial_residual),
                                   median_last100=float(tail.initial_residual.median()),
                                   max_temperature_probe_range_last100_K=float(np.ptp(recent,axis=0).max())))
            for file in (path/"log.solver",path/"system/fvSolution",path/"system/fvSchemes",path/"constant/g",
                         path/"postProcessing/sensors/0/T"):
                hashes[str(file)]=sha256(file.read_bytes()).hexdigest()
        fig.suptitle("Existing CFD evidence: residuals and probe drift; no physical-time stability inference")
        save(fig,"cfd_stability_audit")
        pd.DataFrame(audits).to_csv(out/"cfd_audit.csv",index=False)
    manifest=dict(created_utc=datetime.now(timezone.utc).isoformat(),python=platform.python_version(),
                  packages={name:version(name) for name in ("numpy","scipy","pandas","matplotlib")},
                  diffusion_intervals=20,diffusion_steps=40,diffusion_numbers=[.25,.75,5],
                  modes={"low_amplitude_K":.5,"high_amplitude_K":.01},seed=None,
                  data_role="Synthetic verification, actual-layout sensitivity and existing CFD audit; no experimental fitting or new CFD run",
                  limitations=["Pure diffusion, no advection/buoyancy/turbulence",
                               "Reduced relaxation is not OpenFOAM equation relaxation",
                               "Existing CFD restarts also changed initialisation: relaxation effect is confounded",
                               "SIMPLE iterations are not physical time; CFL limits cannot diagnose these steady runs",
                               "CFD root cause remains unproved"],
                  source_sha256={str(p):sha256(p.read_bytes()).hexdigest() for p in (Path(__file__),Path(__file__).parent/"validation/stability.py",Path(__file__).parent/"interpolation/sensitivity.py",Path(__file__).parent/"interpolation/plane.py",Path(__file__).parent/"interpolation/nearest.py")},
                  cfd_input_sha256=hashes,
                  interpolation_inputs_sha256={str(p):sha256(p.read_bytes()).hexdigest() for p in (args.sensors,args.mesh)},
                  interpolation_query_grid=[50,70],illustrative_input_noise_bound_mps=.001)
    (out/"manifest.json").write_text(json.dumps(manifest,indent=2)+"\n")
    print(pd.DataFrame(trials).to_string(index=False))
    print(pd.DataFrame(relaxation).to_string(index=False))
    for name,g in order_frame.groupby("method"):
        g=g.sort_values("dtau")
        slope=np.log(g.temporal_rmse_K.iloc[1]/g.temporal_rmse_K.iloc[0])/np.log(2)
        print(f"{name}: observed temporal order = {slope:.4f}")
    print("Results:",out)


if __name__=="__main__":
    main()
