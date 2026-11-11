"""Plain-language interpretation of GUI evidence, without validation claims."""

def validation_message(kind, manifest=None):
    """Describe experimental agreement separately from numerical convergence."""
    manifest = manifest or {}
    if kind in ('lab','lab_cfd'):
        return 'Reconstruction comparison: '+('archived CFD numerical reference; not experimental validation.' if kind=='lab_cfd' else 'held-out experimental sensors; no CFD run.')
    if kind == 'experimental':
        return 'CFD agreement: not assessed in reconstruction-only mode.'
    if kind == 'thermal':
        return 'Thermal evidence: archived and unconverged; physical accuracy unestablished.'
    if manifest.get('cfd_sensor_metrics'):
        return 'Experimental comparison available; physical validation remains incomplete.'
    return 'Experimental agreement has not been assessed for this job yet.'


def guide_text(kind, run_id, method, mesh, manifest=None):
    """Return contextual user guidance for the selected request and its evidence."""
    manifest = manifest or {}
    status = validation_message(kind, manifest)
    if kind in ('lab','lab_cfd'):
        return f'''RECONSTRUCTION LAB

{status}

Select the experimental setup, then Run selected setup. All four methods are compared automatically; mesh and MPI controls are inactive. Open result gallery after completion to use the interactive dashboard. Figures also appear in Results.

FIVE VIEWS

1. Compare fields: identical sensors, axes and colour scale; hover over values and toggle overlays. Full-array maps are illustrative fits.
2. Unseen sensors: scores come from held-out locations, with training-only SVR tuning. Linear unsupported values remain missing.
3. Sensor count: three nested layouts share fixed held-out targets and retain hull vertices, preserving support.
4. Input noise: paired synthetic Gaussian noise perturbs training values only. Shading is trial range, not instrument uncertainty.
5. Accuracy and cost: median of three fits and grid predictions, including SVR search; accuracy comes from separate held-out fits.

SCIENTIFIC LIMITS

Experiments fit one replicate at a time. The CFD lab uses archived converged isothermal data at 16 ft with disjoint virtual training/test points, not measured truth or a new CFD run. Thermal fields are excluded. Outside-hull predictions and negative values stay visible. More sensors or a smoother plot do not establish physical validity.

REPRODUCIBILITY

Seeded designs, raw prediction and sensitivity CSVs, inner search/split audits, source hashes, machine-specific timings and shareable PNG/PDF figures accompany every successful lab run.
'''

    return f'''WHAT THIS TOOL HELPS YOU INVESTIGATE

How well can a sparse sensor array reconstruct air speed, and how closely does the CFD model agree with the measurements? Select the experiment and analysis, then inspect both the figures and the numerical status.

CURRENT SELECTION

Experiment: {run_id}
Workflow: {kind}
Reconstruction: {method}
Mesh resolution: {mesh if kind == 'fresh' else 'not selectable in this mode'}
{status}

HOW TO USE IT

1. Check runtime, then choose the experiment and workflow.
2. Choose a reconstruction method. Mesh resolution applies to fresh CFD only.
3. Run selected setup. Follow Log and Residuals while it runs.
4. Inspect Results, including the error metrics, support hatching and saved status.

The reconstruction method changes the experimental fit. It does not change OpenFOAM's turbulence model or numerical schemes. Coarse, Standard and Fine describe cell counts; none guarantees accuracy.

WHAT THE FIGURES MEAN

Measured means: actual scalar air-speed observations at the published sensor positions. They are not signed axial velocities.

Reconstruction map: a surface fitted using all available sensors. Hatching marks extrapolation outside their convex hull. A smooth surface is not measured truth. Negative speed predictions are physically inadmissible and are reported rather than hidden.

Held-location errors: predictions at sensors excluded from fitting. These assess spatial prediction. Full-array refit plots do not provide these scores.

CFD paired dots: each grey segment joins measured and CFD speeds at the same position. A CFD marker to the right means overprediction, and one to the left means underprediction. Segment length is a discrepancy, not an uncertainty bar.

Mesh plot: the selected grid and sensor positions. A finer grid alone does not demonstrate mesh independence.

WHAT RMSE AND BIAS MEAN

RMSE is the typical size of prediction error, with extra weight on larger errors, in m/s. Lower is better within the same comparison. There is no universal acceptable value: an engineering use needs an error tolerance and measurement-uncertainty context.

Bias is the average prediction minus observation. Positive means average overprediction. A small bias can coexist with large errors that cancel out.

Held-location metrics evaluate the reconstruction method. CFD-versus-measurement metrics evaluate agreement of the numerical flow model with experiment. These are different comparisons.

WHAT THE RESIDUAL PLOT MEANS

Residuals describe imbalance in the discretised equations during the solve. The plot uses each field's first reported initial residual per SIMPLE iteration, on a logarithmic vertical scale. A change from 1e-2 to 1e-4 is a hundredfold reduction. SIMPLE iterations are not physical seconds or machine-learning epochs.

Falling residuals suggest the equations are settling. Oscillation, growth or a plateau may require investigation. Some velocity components can have zero residual; all-zero series are omitted from the log plot, and isolated zero values use its lower edge. Saved histories retain the actual zeros.

The solver's reported stopping criteria determine its convergence status. A curve falling below an arbitrary visual level does not certify convergence. Mesh checks and final flux balance are separate checks. Archived histories are labelled and are not a live CFD run.

WHAT PHYSICAL VALIDATION MEANS

Physical validation asks whether a numerical model represents the real apparatus accurately enough for a specified engineering decision.

This GUI displays evidence relevant to that question: matched CFD/experimental errors, numerical status and the assumptions behind a case. It currently does not issue a physically validated PASS/FAIL rating.

A completed job means the requested computation finished. A mesh check, falling residuals and a small flux imbalance check numerical behaviour. Agreement with independent measurements, measurement uncertainty and an application-specific acceptance criterion are still needed to establish physical adequacy.

The current model idealises the inlet as a full face, seals the walls and assumes a turbulence model. The existing disagreement with experiment remains unresolved. A new job or lower RMSE alone does not validate these assumptions.

ARCHIVED AND THERMAL RESULTS

Archived isothermal mode reuses the matched baseline's recorded samples. Thermal mode presents an archived unconverged diagnostic case, not a new successful thermal prediction. These sources remain identified in the status and manifest.

WHERE THE EVIDENCE IS SAVED

Open result gallery or Output folder for CSV tables, figures, complete logs and manifest.json. The residual history is saved as residual_history.csv; a final residual PNG/PDF is available when a history exists. Failed or cancelled jobs keep their partial evidence and status.
'''
