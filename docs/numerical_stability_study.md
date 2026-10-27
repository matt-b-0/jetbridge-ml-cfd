# Course-aligned numerical stability and input-sensitivity study

## Purpose and project scope
A bounded investigation of: **How do solver stability and input-noise sensitivity limit the reliability of CFD-supported interpolation of sparse jet-bridge measurements?**

This supports the existing interpolation-versus-ML project. It does not replace the main question with an open-ended CFD validation programme. Synthetic verification, geometry-based interpolation sensitivity, experimental errors and CFD diagnostics remain distinct.

## Links to the supplied MMA3001 topics

| Unit topics | Implemented investigation | Engineering purpose |
|---|---|---|
| 2.2 Numerical errors; 1.5 testing/validation | Known exact solutions, independent eigenmode checks, diagnostic-window regression test | Separate coding error, discretisation error and failed convergence |
| 2.3 linear systems; 7.1 finite differences | Central-difference heat operator; implicit matrix solves | Show where the discrete equations and linear solves arise |
| 7.2–7.3 ODEs/Euler; 9.1–9.3 stability, stiffness, implicit solutions | Method-of-lines heat system and theta schemes | Connect spatial resolution to stiff decay rates and stable stepping |
| 10.1 relaxation; 10.4 PDE classification | Weighted Jacobi for a known elliptic boundary-value problem | Quantify convergence rate and limits of damping |
| 11.1 FTCS; 11.2 Dirichlet BCs; 11.4 stability; 11.5 Crank–Nicolson | Parabolic diffusion with fixed perturbation endpoints | Demonstrate unstable, bounded, oscillatory and accurate behaviour separately |
| 6.3 refinement / Richardson concepts | Step halving and observed convergence order | Verify expected error order without conflating spatial and temporal errors |
| 3.1–3.2 fitting/extrapolation/noise; 3.5 2D interpolation | Actual sensor-layout noise-amplification maps | Assess sensitivity where dense reconstruction is unsupported by observations |
| 1.2–1.4 reproducibility/documentation/AI reflection | CLI, hashes, fixed settings, tests and recorded limitations | Make the numerical claims reproducible and auditable |

No new ML model, physical CFD solution or experimental calibration was introduced.

## 1. Controlled parabolic PDE experiment
Solve a temperature perturbation on the unit interval:
\[
u_\tau = u_{\xi\xi},\quad u(0,\tau)=u(1,\tau)=0,
\qquad \tau=\alpha t/L^2.
\]
A linear fixed-temperature background could be added; the perturbation itself has units K. This is a synthetic diffusion problem, not a full jet-bridge temperature model. It omits advection, buoyancy, turbulence and wall thermal inertia.

With N intervals, the interior finite-difference matrix L has diagonal -2 and adjacent entries +1. The update is
\[
(I-\theta rL)u^{n+1}=(I+(1-\theta)rL)u^n,\quad
r=\alpha\Delta t/\Delta x^2.
\]
theta=0 gives FTCS, theta=1 implicit Euler, theta=1/2 Crank–Nicolson. The eigenmode amplification is
\[
g_k=\frac{1+(1-\theta)r\lambda_k}{1-\theta r\lambda_k},
\quad\lambda_k=-4\sin^2(k\pi/(2N)).
\]
The code computes the finite-grid spectral radius max(abs(g_k)) and independently checks the predicted amplification against explicit sine-mode trajectories.

For the heat equation the familiar FTCS condition r<=1/2 is the grid-independent stability limit; on a particular finite Dirichlet grid the exact admissible bound is slightly larger. Implicit Euler and Crank–Nicolson are stable for this linear diffusion system for all positive r. This does not establish unconditional stability for a nonlinear buoyant CFD solver. [MIT lecture: von Neumann stability analysis](https://ocw.mit.edu/courses/18-336-numerical-methods-for-partial-differential-equations-spring-2009/c7c12accea163007923288875bb42604_MIT18_336S09_lec14.pdf).

The initial condition is 0.5*sin(pi*xi)+0.01*sin((N-1)*pi*xi), N=20. Including a small high-frequency mode makes instability observable rather than relying on accidental roundoff excitation. Its exact continuous solution is the sum of the corresponding exponentially decaying sine modes.

| Method | r | Spectral radius | Observed behaviour over 40 steps |
|---|---:|---:|---|
| FTCS | 0.25 | 0.993844 | Stable |
| FTCS | 0.75 | 1.981533 | Unstable; final error approximately 5.50e9 K |
| FTCS | 5 | 18.876883 | Rapid numerical growth |
| Implicit Euler | 5 | 0.890380 | Stable, strong high-frequency damping |
| Crank–Nicolson | 5 | 0.884023 | Stable; high-frequency component alternates sign |

The r cases have different final dimensionless times because each uses 40 steps. Compare methods within each r, not accuracy across different final times. The enormous unstable-case values are intentionally generated numerical errors, not physical temperatures.

Crank–Nicolson's bounded oscillation is a direct demonstration that **stability does not imply monotonicity or accuracy**. A stable low-order method can also have a smaller error at one grid/time because spatial and temporal errors cancel. That observation is not evidence of a better convergence order.

### Accuracy and stiffness checks
A separate fixed-final-time study uses a smooth first sine mode, N=40 and final tau=0.02. Temporal errors are measured against its exact semi-discrete solution, so spatial truncation does not contaminate the time-order estimate. Halving the two finest time steps gave observed orders:
- Implicit Euler: 0.9973, consistent with first order.
- Crank–Nicolson: 2.0000, consistent with second order.

A separate exact semi-discrete versus exact continuous comparison at N=10,20,40,80 demonstrates approximately second-order spatial error. This isolates the derivative discretisation rather than assuming every refinement error is temporal.

The method-of-lines system has eigenvalues alpha*lambda_k/dx^2. Refining the mesh makes the fastest decay scale grow as dx^-2 while the slowest scale tends to a constant, increasing stiffness. This is why spatial refinement can make explicit stepping expensive. It is not proof that stiffness caused the observed CFD failure.

## 2. Controlled elliptic/relaxation experiment
Discretise -u''=pi^2 sin(pi*x), with u(0)=u(1)=0. Use the exact discrete solution A^(-1)b as the iteration reference, keeping discretisation error separate.

Weighted Jacobi updates:
\[
u^{m+1}=u^m+\omega D^{-1}(b-Au^m),\quad
G_\omega=I-\omega D^{-1}A.
\]
For a stationary linear iteration, rho(G)<1 is the convergence criterion. With N=20 and 400 iterations:

| omega | Spectral radius | Final relative residual |
|---:|---:|---:|
| 0.2 | 0.997538 | 0.373011 |
| 0.6 | 0.992613 | 0.051521 |
| 1.0 | 0.987688 | 0.013362 |
| 1.2 | 1.385226 | approximately 6.54e56 |

These are convergence-rate comparisons, not claims that every stable run reached a tight tolerance in 400 iterations. The over-relaxed example diverges, and excessive damping makes this particular convergent system slower.

For a separate illustrative scalar fixed-point map with derivative mu, field-update relaxation gives amplification 1-omega+omega*mu. When mu=-1.2, some damping stabilises the map. When mu=+1.1, every positive omega still produces amplification greater than one: making the update smaller can merely slow divergence.

**These map eigenvalues are illustrative, not fitted or inferred CFD Jacobians.** OpenFOAM field relaxation and equation relaxation are also different operations. Its equation relaxation changes the linear system; weighted Jacobi is not an implementation of SIMPLE. [OpenFOAM algorithm-control documentation](https://www.openfoam.com/documentation/user-guide/6-solving/6.3-solution-and-algorithm-control), [OpenFOAM under-relaxation documentation](https://doc.openfoam.com/2606/tools/processing/numerics/solvers/under-relaxation/).

## 3. Direct connection to the interpolation project
For a fixed interpolator linear in its training values, predictions satisfy y_query=W*y_train. If every input perturbation is bounded by epsilon,
\[
|\delta y_i|\le\epsilon\sum_j|W_{ij}|.
\]
We compute this tight pointwise worst-case bound for nearest, linear and the existing fixed zero-smoothing thin-plate-spline RBF. Each query's worst case may use a different noise vector. This is sensitivity, not a noise distribution, instrument uncertainty estimate, condition number of a particular linear system, or prediction-error bound.

Only the actual 12 sensor coordinates from the starter 10 ft layout are used; measured values are not fitted or perturbed. The query grid covers the full actual mesh cross-section at source z=3.05 m, with 50x70 points. No artificial wall observations or no-slip interpolation anchors are added.

| Method | Supported query points | Maximum gain inside sensor hull | Maximum gain outside |
|---|---:|---:|---:|
| Nearest | 3500/3500 | 1.00 | 1.00 |
| Linear | 1392/3500 | 1.00 | Unsupported |
| RBF | 3500/3500 | 1.41 | 2.55 |

For illustrative independent bounded perturbations of +/-0.001 m/s per input, the largest RBF worst-case change over this grid is approximately 0.00255 m/s. This is a geometry-based sensitivity bound, not a statement about actual SWEMA noise or confidence intervals.

The 39.77% linear coverage refers to full-plane query-grid points. It must not be confused with the earlier 360/504 coverage of held-out sensor observations across multiple runs. Filling the plane with nearest predictions does not make those predictions accurate or physically wall-consistent. Likewise, lower held-out RBF errors do not make its extrapolation insensitive.

## 4. What the existing CFD evidence says
The audit reads logs and scheduled T probes without changing any CFD inputs or solutions.

| Run | Last iteration | Final first p_rgh residual | Final T residual | Maximum probe-T range in final 100 iterations |
|---|---:|---:|---:|---:|
| Original thermal | 3000 | 0.003193 | 0.0005412 | 0.0005338 K |
| Zero-gravity control | 733 | 0.000004066 | 0.00000009937 | 0.0000520 K |
| Stabilized thermal | 1000 | 0.03415 | 0.0002940 | 0.1187674 K |

Only the control met the configured solver criteria. The original thermal run's temperature probes look almost stationary even though its velocity field failed badly. This is direct evidence that monitoring a single temperature statistic, residual or net flux is insufficient.

The stabilized pressure residual is about 3415 times its 1e-5 threshold; T is about 294 times its 1e-6 threshold. Its temperature drift also remains material. It cannot be used as a converged dense reference.

### Important limits and diagnostic correction
1. The original CFD run used steady SIMPLE, not FTCS. Its deltaT is an iteration increment, not a physical time step. The diffusion CFL/FTCS limit cannot be applied directly to diagnose that run.
2. Residual trends alone do not identify the eigenvalues of the nonlinear SIMPLE iteration; residual normalisation and the state change during the solve.
3. The stronger-relaxation restart ALSO changed initialisation by importing the control solution. The observed difference does not isolate a causal relaxation effect. It also used a different iteration cap.
4. An unsettled steady iteration does not prove the physical flow is unsteady. Numerical coupling, boundary assumptions, wall treatment, turbulence closure and physical unsteadiness remain possible explanations.
5. A reporting bug was corrected: snapshot-967 temperature drift previously included later probe records up to 997. The correct closed window [867,967] gives 0.1324055 K. The separate final-run audit at iteration 1000 uses [900,1000] and gives 0.1187674 K. The old 0.1723 K value was not a true last-100-iteration snapshot statistic. Sensor comparisons and saved CFD fields were unaffected.

## 5. Bounded next CFD experiment
Before claiming a remedy, run a one-factor numerical comparison with identical initial fields, physical boundaries, mesh, discretisation, solver tolerances and iteration cap. Vary one relaxation factor at a time, e.g. U=0.1/0.2/0.3 with other factors fixed. Preserve convergence histories, runtime, probe drift, signed flux, velocity/temperature bounds and turbulence-field behaviour. Select numerical settings on these diagnostics, not experimental test-sensor errors.

If a transient formulation is then investigated, use actual solver Courant diagnostics, time-step refinement and sufficient physical averaging duration; compare implicit Euler/Crank–Nicolson only with attention to damping, boundedness and accuracy. Do not transplant a pure-diffusion FTCS bound as a complete convection/buoyancy/turbulence stability condition. Thermal wall evidence or sensitivity studies are still needed before physical interpretation.

Keep this as a limited numerical-verification subsection. Continue using analytic fields and independently checked stable CFD fields for interpolation/ML benchmarks; do not use the failed buoyant fields as ground truth.

## Reproduce and verify
Use the Python environment pinned in requirements-benchmark.txt. From the project:
```bash
python -m pytest -q
python -m jetbridge_ml.stability_study \
 --output /home/mattb/projects/new-stability-study \
 --thermal /home/mattb/projects/jetbridge-thermal-s01-ac-10-hn-1 \
 --control /home/mattb/projects/jetbridge-thermal-control-s01-ac-10-hn-1 \
 --stabilized /home/mattb/projects/jetbridge-thermal-stabilized-s01-ac-10-hn-1
```
Omit the three CFD flags to run just the synthetic and actual-layout sensitivity examples. The default sensor CSV and mesh come from the repository starter case; --sensors and --mesh can override them. Output must be a new directory.

Outputs include six PNG/PDF figures, raw numerical CSV tables and a manifest of fixed settings, package versions, source hashes, sensor/mesh hashes and read-only CFD input hashes. No random data or hyperparameter tuning is used. Full-plane sensitivity maps are geometry-only. Generated outputs remain under ignored data/processed/stability_study/ or an external folder.

All 36 tests passed, including discrete-mode amplification, explicit stability boundary, implicit/CN damping, temporal/spatial order, known linear-system solution, interpolation-noise bounds, and the saved-iteration window regression test. Repeated diffusion, temporal-refinement and relaxation tables matched byte-for-byte. PNG figures were visually inspected; crowded refinement tick labels and obscured stable relaxation curves were corrected.

Local findings were saved without pushing to GitHub. Existing raw experimental records and CFD solution fields were not modified.

## Current demo and quality workflow on 27 October 2026
The repository now includes the attributed study input subset and compact archived numerical evidence. Use the root run_all.py driver and docs/LIVE_DEMO.md for one-clone execution; older commands above describe the original research runs. Static checking uses python -m ruff check src tests run_all.py; numerical tests use python -m pytest -q; API documentation uses python -m pdoc jetbridge_ml -o docs/html. See docs/DEVELOPMENT.md for scope and limitations. Live/full execute fresh isothermal CFD in new output folders; archived unconverged thermal evidence remains explicitly separate.
