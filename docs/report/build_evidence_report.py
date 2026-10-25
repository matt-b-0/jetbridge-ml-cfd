"""Revise the retained report source with the second review's evidence."""
from pathlib import Path
import json
BASE=Path(__file__).with_name('build_revised_report.py')
source=BASE.read_text(encoding='utf-8')
source=source.replace("\"'revised_output'\"", "\"'evidence_report_output'\"")
source=source.replace("doc.core_properties.subject='Revised numerical methods report'", "doc.core_properties.subject='Spatial reconstruction and numerical evidence report'\ndoc.core_properties.author='Matthew Brasacchio'")
source=source.replace('[Student name] | [Student ID]','Matthew Brasacchio | 33858659')
source=source.replace('using 36 FAA/NRC experimental runs','using 36 FAA/NRC replicate-average datasets from one apparatus')
source=source.replace('This requires both a local error estimate and a clear indication of where the model extrapolates. A smooth contour alone provides neither.', 'The reconstruction is accompanied by experimentally evaluated predictive errors and an explicit indication of regions outside the training sensor hull. These measures identify important limitations, although they do not provide calibrated uncertainty at every predicted location.')
source=source.replace('Ten main pages are followed by references and two diagnostic appendices.', 'Ten main pages are followed by references and four supporting appendices.')
# Reuse the existing table design, adding numbered descriptive captions.
insert="""
E='docs/report/evidence/'
F='docs/report/assets/'
_original_table=table
table_number=0
def table(headers,rows,widths=None,caption=None):
    global table_number
    table_number+=1
    defaults={'SVR parameter':'Predeclared SVR search grid','Group':'Paired experimental comparisons by source layout','Method':'Predictive accuracy and computational cost'}
    caption=caption or defaults.get(headers[0],'Study specification')
    para=p(f'Table {table_number}. {caption}','Caption')
    para.paragraph_format.keep_with_next=True
    return _original_table(headers,rows,widths)
"""
source=source.replace("F='data/processed/report_revision/figures/'", "F='data/processed/report_revision/figures/'\n"+insert)
def section(start,end,text):
    global source
    a=source.index(start);b=source.index(end,a)
    source=source[:a]+text+'\n\n'+source[b:]

section("page('2 Experimental", "page('3 Models", """
page('2 Experimental data geometry and data contract')
p('The S01-A-HN subset contains 36 replicate-average files and 504 sensor means at nine stations from 10 to 58 ft. Thirty files use 12 positions; six at 58 ft use 24 positions assembled sequentially from A/B measurements. Replicates share one apparatus. Station measurements are not simultaneous and supplied flow varies [1,2].')
fig(F+'geometry_compact.png','Source laboratory geometry and the matched 10 ft array. The sloped floor must be included when converting local sensor heights to absolute laboratory height.',6.15)
table(['Input or output','Contract and unsupported cases'],[
('Experimental input','FAA 03-Averages BLOCK .txt; unique coplanar absolute x, y, z in metres; scalar speed in m/s; replicate ID retained.'),
('Boundary and audit input','HVAC and raw sensor CSV, with source time windows and units checked; supplied L/s divided by 1000 gives m³/s.'),
('CFD input','Exported CSV coordinates in metres and U components / speed in m/s; numerical reference kept separate.'),
('Prediction output','CSV scalar speed in m/s plus hull membership, source/run identifiers and held-location residuals where observed.'),
('Invalid observations','−9999 speed becomes missing and is excluded; duplicate/invalid coordinates, negative/infinite source speeds or nonplanar arrays are rejected.'),
('Unsupported queries','Linear returns NaN outside the training hull; nearest, RBF and SVR extrapolate and are flagged. Negative predictions are not silently clipped.')],[1.5,5.15],caption='Accepted data formats units and handling of unsupported data')
p('The retained frame uses x across width, y above the laboratory floor and z along the bridge. Feet convert with 0.3048; inches with 0.0254. A local height needs the floor offset; published absolute metre coordinates must not receive it again. Width is 1.388618 m, clear height 2.441448 m and length 18.10512 m. Four defining sections and all block vertices were audited; the documented 0.127 mm upper-ceiling difference remains.')
p('The full 12-point hull covers 41.3% of physical cross-sectional area and the 24-point hull 49.7%; outer-held-location hulls cover 37.1–41.3% and 48.0–49.7%, respectively. These area fractions are not the 71.43% of withheld targets supported in evaluation. Hot-sphere speed is not signed axial velocity, and HVAC supply is not an exact flux identity for each experimental plane.')
""")
# Keep the existing model descriptions, adding a bounded-search caveat.
source=source.replace("h('Nested validation and common support',2)", "p('The grid spans two orders of magnitude in C, two spatial scales and two epsilon values as a deliberately small training-only search. It is not established as sufficient. Across 504 outer folds, C = 0.1 / 1 / 10 is selected 243 / 196 / 65 times; gamma = 0.1 / 1 occurs 316 / 188 times. Both tested gamma and epsilon values are grid endpoints. Appendix C records every combination and the limits of selection from small inner folds.')\nh('Nested validation and common support',2)")
section("page('4 Experimental", "page('5 Variation", """
page('4 What the experimental models reconstruct')
p('The matched 10 ft replicate provides a concrete view of the reconstruction. Full-array refits in panels B and C are illustrative fitted surfaces; panel D contains actual outer held-location errors. There is no continuously measured experimental truth between sensors. White boundaries identify the full-array hull, outside which the coloured field is extrapolation.')
fig(E+'experimental_reconstruction.png','S01-A-10-HN-1 measurements and full-array RBF/SVR refits on a common speed scale. Panel D shows prediction-minus-observation residuals from location withholding, with circles for RBF and squares for SVR; small horizontal offsets distinguish methods. The refits do not generate the reported cross-validation scores.',6.55)
p('Both models place higher speeds around the middle heights and lower speeds near the sampled top and bottom. RBF retains more local variation between the two sensor columns; SVR smooths these lobes. On the plotted grid, RBF spans 0.0826–0.1579 m/s and SVR 0.0775–0.1604 m/s; neither predicts negative speed in this example. Their boundary predictions differ without measurements there to establish which is correct. Exact agreement at retained RBF sensors is a fitting property, not a prediction test.')
p('Across all common supported experimental targets, RBF RMSE is 0.04959 m/s, linear 0.05524, SVR 0.05774, the mean 0.06765 and nearest 0.07129. Full MAE/bias and extrapolation tables are in Appendix D. RBF improves on the mean by 26.7% and on SVR by 14.1%, using each comparator as denominator.')
p('The 360 evaluated target speeds have median 0.1765 m/s and interquartile range 0.1380–0.4223 m/s. RBF RMSE is about 28.1% of that median; this scale ratio is not mean percentage error, nor a calibrated local error bar. Substantial prediction error remains despite a favourable relative ranking.')
p('No acceptance threshold has been specified. These results support approximate pattern screening and planning measurements, not precise minimum-speed guarantees, ventilation compliance or disease-risk assessment. An engineer should mark extrapolation, inspect held-location residuals, and add sensors in weakly supported regions before relying on local differences. A mean baseline is reasonable where spatial detail is unnecessary.')
""")
source=source.replace("RBF wins in 21 of 36 runs and SVR in 15.", "RBF wins in 21 of 36 runs and SVR in 15. These counts are descriptive: the files share apparatus, layouts and operating conditions and are not 36 independent facilities or geometries.")
section("page('6 CFD", "page('7 CFD", """
page('6 CFD model assumptions and credibility')
p('The matched S01-A-10-HN-1 case is a simplified sealed bridge. The chosen steady k–epsilon RANS model provides an inexpensive engineering baseline for a mean turbulent flow, but its applicability to this low-speed apparatus has not been independently established. Full-face inlet/outlet boundaries omit the real perforated diffuser and exhaust plenum.')
table(['Parameter','Actual baseline dictionary or check'],[
('Solver and fluid','OpenCFD v2412 patch 260127; simpleFoam; steady incompressible isothermal RANS; ν = 1.5 × 10⁻⁵ m²/s.'),
('Inlet and outlet','Inlet flowRateInletVelocity Q = 0.533865517 m³/s toward −z; inlet p zeroGradient. Outlet p fixedValue 0 m²/s² gauge; U pressureInletOutletVelocity.'),
('Walls','No-slip, impermeable. kqRWallFunction, epsilonWallFunction and nutkWallFunction; no wall inflation layers.'),
('Turbulence boundaries','Fixed inlet k = 9.29896 × 10⁻⁵ m²/s² and epsilon = 1.18900 × 10⁻⁶ m²/s³; outlet inletOutlet with same reverse-flow values. Assumed intensity 5%, length 7% of hydraulic diameter; not measured.'),
('Schemes and relaxation','Bounded upwind convection for U, k and epsilon; corrected linear Laplacian; pressure relaxation 0.3, equation relaxation 0.6; one nonorthogonal corrector.'),
('SIMPLE stopping criteria','Initial residual screens p < 10⁻⁴, U < 10⁻⁵, k and epsilon < 10⁻⁵. Converged at 237. Linear-solver tolerances are separate from these stopping criteria.')],[1.5,5.15],caption='Isothermal CFD specification verified against the case dictionaries')
p('At iteration 237, reported initial residuals include p = 3.22 × 10⁻⁶, Ux = 9.36 × 10⁻⁶, Uy = 2.38 × 10⁻⁶, Uz = 5.33 × 10⁻⁷, k = 6.98 × 10⁻⁷ and epsilon = 6.33 × 10⁻⁸. Global continuity error is 4.00 × 10⁻¹¹. At iteration 200 the relative signed flux imbalance is about 1.50 × 10⁻⁸; final displayed inlet/outlet values round to ±0.53386552 m³/s. Rounded equality is not exact zero. Final probes and patch fluxes were postprocessed at saved field 237.')
p('Saved-field y-plus postprocessing gives wall minimum 10.0, maximum 27.1 and patch average 18.7. This is neither viscous-sublayer resolution nor comfortably high log-layer placement; wall treatment needs reassessment [8]. It is a model limitation, not proof of the cause of disagreement. Coarse/baseline/fine meshes contain 17,664 / 141,312 / 476,928 cells and all pass checkMesh. Baseline-to-fine sensor RMSE is 0.001423 m/s and dense-section relative L2 difference 4.54%; mesh independence is not established.')
p('Cell-point sampling at 12 matched sensors gives RMSE 0.03977 m/s, bias +0.03667 m/s and r = 0.489. Appendix D shows observed temporal variability: SD is 0.0119–0.0287 m/s, not standard error or a confidence interval. The bias is 20.8% of the evaluated-target median 0.1765 m/s, a scale comparison across different populations. Coordinate-choice sampling RMSE is only 0.000293 m/s. Neither a conserved field nor a good surrogate removes physical CFD bias.')
""")
section("page('7 CFD", "page('8 Sensitivity", """
page('7 Spatial CFD errors and the original discrepancy')
p('Virtual sensors permit a continuous numerical comparison unavailable in the experiment. The example at 28 ft uses a 24-sensor hybrid layout on the 32 × 48 candidate grid; predictions are tested on a disjoint 40 × 60 reference grid. Black points show training sensors. The reference is a numerical field, not experimental truth.')
fig(E+'cfd_reconstruction.png','CFD reference, RBF/SVR reconstructions and signed full-section errors at 28 ft. The three speed panels share a colour scale and both error panels share a zero-centred scale. Errors are prediction minus numerical reference; black dots are the 24 training positions.',6.55)
p('Both methods reproduce the broad high-speed core but smooth the near-wall gradient. Negative error bands lie just inside the boundaries; the outermost sampled band can be overpredicted. RBF RMSE is 0.02331 m/s and SVR 0.02515 m/s in this plane, with maximum absolute errors 0.05750 and 0.05904 m/s. Similar-looking fields therefore conceal errors large enough to matter near a wall. Boundary samples help, but a finite smooth reconstruction does not enforce no-slip between them.')
p('Across tested planes, the 24-sensor hybrid layout reduces baseline full-plane RBF RMSE from 0.03388 to 0.02658 m/s and SVR from 0.03365 to 0.02844 m/s relative to interior placement. Boundary-heavy placement is worse, so interior and boundary information are both needed. The exploratory hybrid layout was introduced after inspecting earlier results; it is not an untouched confirmatory design.')
p('At 80% supplied flow, the same positions with refitted models retain an average hybrid advantage: RBF 0.02119 versus 0.02754 m/s and SVR 0.02319 versus 0.02743 m/s. Some planes worsen. This tests layout transfer with new sensor values, not a frozen model predicting a new operating condition. The separate three-dimensional surrogate also has much smaller supported-region than whole-plane errors; coverage drives that distinction.')
h('What remains unresolved upstream and downstream',2)
p('The motivating observation was high upstream and low downstream experimental speeds relative to a flow-driven CFD field. The matched 10 ft audit addresses one downstream plane only and cannot resolve that trend. Station files have different HVAC flows and sequential acquisition, so an unmatched station-error curve would imply comparability that has not been established. A defensible extension needs a matched CFD boundary/window for each station, comparable setup and temperature, signed-vector information if flux is inferred, and uncertainty or repeatability context. Diffuser, leakage and turbulence effects remain hypotheses.')
""")
section("page('8 Sensitivity", "page('9 Computational", """
page('8 Sensitivity and observed measurement variation')
p('For fixed geometry, linear-in-values interpolation has û(q) = Σwᵢ(q)uᵢ. A bounded input perturbation |δuᵢ| ≤ ε implies |δû(q)| ≤ εΣ|wᵢ(q)|. On the standardised full 12-sensor geometry, the maximum RBF gain is 1.468 inside and 2.829 outside the hull; nearest and supported linear interpolation have gain 1. Rounding alone at ±0.0005 m/s would give small bounds of 0.000734 and 0.001415 m/s. It does not represent dominant experimental variation.')
fig(E+'empirical_perturbation.png','Two hundred common perturbation draws applied to both models at the matched 10 ft geometry. Box centres are medians, boxes are Q1–Q3 and whiskers extend to points within 1.5 IQR. This is a sensitivity scenario based on observed between-run variation, not a predictive uncertainty interval.',6.35)
p('Six 10 ft replicate-average datasets give location-wise sample SDs of 0.00576–0.03346 m/s. Each draw adds centred independent Gaussian perturbations with these SDs to the matched replicate speeds, refits both methods and evaluates RMS change over a fixed section grid. The SVR parameters selected on the full original 12-point dataset are frozen (C = 1, gamma = 0.1, epsilon = 0.002), so changes reflect response to data perturbation rather than retuning. RBF retains zero smoothing.')
p('Median RMS change is 0.01153 m/s inside and 0.01602 outside for RBF, versus 0.00952 and 0.01463 m/s for SVR. Corresponding interquartile intervals are 0.00997–0.01417, 0.01305–0.01935, 0.00736–0.01184 and 0.01134–0.01771 m/s. In this constructed scenario SVR changes slightly less, while both methods are more sensitive outside the hull. This does not establish a general robustness ranking.')
p('Between-run variation also contains operating changes: the six files do not hold supplied flow exactly constant. It is labelled observed variation rather than pure instrument uncertainty or controlled repeatability. Independent Gaussian perturbations omit spatial/time correlation and physical co-variation; they are a declared stress-test assumption. No perturbed result changes the original held-location scores.')
p('Zero smoothing preserves local measured features but also input variation. SVR regularisation trades some fit for reduced response in this scenario. A future smoothing comparison should tune only within inner folds and use documented uncertainty or matched-repeat data. Appendix B retains the reduced diffusion verification as a separate taught-method exercise; it cannot diagnose nonlinear CFD convergence.')
""")
section("page('9 Computational", "page('10 Engineering", """
page('9 Computational cost variability and reproducibility')
p('The controlled benchmark withholds the first source location in each of 36 files, leaving n = 11 or 23 training sensors. All methods receive identical retained data, one held-out query and a 2,400-point grid. A warm-up precedes 20 repetitions with shuffled method order, one numerical thread and file I/O excluded. Fitting includes required preprocessing; prediction includes query transformation.')
table(['Method','Fit n = 11 sensors\nms median [Q1–Q3]','Predict 2400 points n = 11\nms median [Q1–Q3]'],[
('Mean','0.014 [0.013–0.016]','0.0022 [0.0021–0.0025]'),
('Nearest','0.38 [0.36–0.47]','0.44 [0.41–0.50]'),
('Linear','0.49 [0.45–0.60]','0.20 [0.18–0.23]'),
('RBF','0.42 [0.38–0.50]','0.45 [0.42–0.51]'),
('SVR','0.95 [0.87–1.18]','0.71 [0.67–0.78]')],[1.1,2.75,2.8],caption='Timing medians and within-run repetition variability at eleven retained sensors')
p('Q1, median and Q3 are calculated across repetitions within each run, then each statistic is summarised by its median across runs. These are typical repetition quartiles, not confidence intervals or pooled cross-run quartiles. The n = 23 results are in Appendix C. At n = 23, median fit/dense-prediction costs are 0.43/0.74 ms for RBF and 0.93/1.31 ms for SVR. Linear may return NaN outside its hull; faster computation is not equivalent coverage.')
p('The separate 12-candidate, three-fold SVR search plus final fit takes median 47.2 ms at n = 11 and 52.4 ms at n = 23 over three repetitions per file. All selected settings reproduce the saved nested-fold choices. A deployment that retunes each new array must include this cost; a deployment with frozen parameters does not. Search dominates SVR fitting, yet approximately 0.05 s is still practical for this offline task. Current accuracy and coverage provide stronger selection grounds than runtime.')
p('The recorded system is WSL2 on an Intel i7-1165G7 at 2.80 GHz, using NumPy 2.5.4, SciPy 1.18.1 and scikit-learn 1.9.1. Scheduling contributes variation, especially for very short mean timings. The 11-to-23 comparison does not establish large-data scaling. Dense global RBF has quadratic matrix storage and approximately cubic direct-solve work; SVR cost depends on support vectors and the optimisation problem. Tracemalloc records omit some native/process memory and are not a total-RAM comparison.')
h('Evidence that can be reproduced',2)
p('The repository separates experimental processing, interpolation, ML and CFD interfaces. Scripts save hashes, split audits, search records and benchmark repetitions. The report extension adds source, selected input evidence, figure data and a test report; 74 tests pass. Generated HTML/API documentation is included. Raw FAA records and large CFD fields remain external, with acquisition and regeneration instructions. The accompanying submission audit distinguishes local reproducibility from public availability; a local revision is not evidence of a GitHub publication.')
""")
section("page('10 Engineering", "page('References')", """
page('10 Engineering conclusions and remaining work')
h('What the evidence supports',2)
p('The central finding is that reconstruction quality depends substantially on measurement coverage and geometry; a more flexible regression method does not consistently compensate for sparse sampling. RBF is the strongest aggregate supported-region baseline and improves on the mean by 26.7%, but its advantage over SVR is concentrated at the 58 ft layout. The common 12-point datasets slightly favour SVR. This is a conditional result for one apparatus, not a universal model ranking.')
p('The spatial plots explain why the distinction matters. Both models produce a plausible smooth experimental core, but more than half the physical section lies outside the full measured hull. In the CFD example, broad core agreement coexists with near-wall error bands. Numerical reconstruction can therefore look convincing while missing regions important to a ventilation decision. Neither model supplies calibrated uncertainty at every location.')
h('Practical recommendation',2)
p('Use RBF and SVR as paired exploratory reconstructions, show measured points and the sensor hull, and report held-location errors in m/s. Use disagreement and weak coverage to plan further measurements, rather than to certify local airflow. Select the simplest method that meets a predeclared engineering tolerance on independent matched observations. With this workload, including SVR search cost does not make computation a limiting factor.')
p('The next priorities are a predeclared layout test that balances interior and boundary coverage; a matched-condition CFD comparison across stations; and a near-wall/turbulence assessment informed by the observed y-plus range. Inlet diffuser and leakage evidence should accompany that assessment. Reducing a surrogate’s error against CFD cannot remove CFD’s physical bias, and matching net flow does not ensure the correct spatial speed distribution.')
h('Thermal extension',2)
p('The cold-supply extension uses an unmeasured wall-temperature surrogate and remains unconverged. Bounded temperature and relative flux imbalance 1.23 × 10⁻⁶ coexist with failed residual and probe-stationarity screens. SIMPLE iteration is not physical time. These diagnostic fields remain excluded from trusted training/reference data; Appendix A records the details.')
h('AI use and individual learning',2)
p('AI assistance supported parsing, workflow and plotting code, numerical checks, documentation and this report scaffold. Verification included unit tests, coordinate/source audits, repeated outputs, mesh checks, solver logs and hosted CI. Errors found during development included a probe-window bug and coordinate-dependent geometric tie selection; these were corrected and recorded in the AI-use log [4].')
""")
source=source.replace('Existing code snapshot 3cb9b93 with local report-revision extensions generated 25 October 2026.', 'Implementation and report-evidence revision generated 25 October 2026; the accompanying submission audit records its exact Git state.')
source=source.replace('Record the final submitted commit when preparing submission.', 'The final submitted clone must include the recorded implementation revision and its external-data regeneration instructions.')
# Insert a complete source entry without altering the existing bibliography order.
source=source.replace("h('Data and code provenance',2)", "p('[8] OpenCFD. nutkWallFunction and yPlus documentation. https://doc.openfoam.com/2312/tools/processing/boundary-conditions/rtm/derived/wall/nutkWallFunction/ and https://doc.openfoam.com/2212/tools/post-processing/function-objects/field/yPlus/. Accessed 25 October 2026. Installed v2412 dictionaries and saved-field output supply the case-specific values.')\nh('Data and code provenance',2)")
source=source.replace('These figures document an unsuccessful numerical extension.', 'This figure documents an unsuccessful numerical extension.')
extra="""
page('Appendix C Parameter selection and timing details')
p('Across 504 outer folds, C reaches the lower endpoint in 243 cases (48.2%) and the upper endpoint in 65 (12.9%). The remaining 196 select C = 1. Every selected gamma and epsilon is necessarily an endpoint because each has only two candidates. These counts do not establish where an unconstrained optimum lies; extension beyond the grid is warranted before claiming sufficient optimisation. The median within-fold spread between best and worst candidate inner RMSE is 0.01585 m/s.')
table(['C','gamma','epsilon m/s','Selected folds'],[(str(c),str(g),str(e),str(n)) for c,g,e,n in [(0.1,0.1,.002,86),(.1,.1,.01,45),(.1,1,.002,51),(.1,1,.01,61),(1,.1,.002,52),(1,.1,.01,79),(1,1,.002,34),(1,1,.01,31),(10,.1,.002,28),(10,.1,.01,26),(10,1,.002,0),(10,1,.01,11)]],[1.0,1.2,1.8,2.65],caption='Frequency of each training-only SVR choice over all outer folds')
p('An outer 12-point array leaves 11 positions; its inner fits use only 7–8 points and validate on 3–4. At 24 points, inner fits use 15–16 and validate on 7–8. Different small subsets can favour different settings. This is a limitation of hyperparameter selection, not evidence that nested validation was unnecessary. No new setting is chosen using outer test scores in this revision.')
table(['Method','Fit n = 23 sensors\nms median [Q1–Q3]','Predict 2400 points n = 23\nms median [Q1–Q3]'],[
('Mean','0.014 [0.013–0.016]','0.0021 [0.0019–0.0024]'),('Nearest','0.38 [0.36–0.46]','0.53 [0.50–0.58]'),('Linear','0.56 [0.50–0.64]','0.21 [0.19–0.24]'),('RBF','0.43 [0.40–0.51]','0.74 [0.69–0.86]'),('SVR','0.93 [0.88–1.03]','1.31 [1.27–1.45]')],[1.1,2.75,2.8],caption='Timing medians and within-run repetition variability at twenty-three retained sensors')
p('The reported intervals summarise repeated computation, not variation in physical measurements. CPU scheduling, cache effects and library implementation affect these millisecond workloads. Full raw timings, the search-cost records and manifests are retained with the reproducibility evidence.')

page('Appendix D Accuracy and matched measurement variation')
table(['Method','RMSE m/s','MAE m/s','Bias m/s'],[('Mean','0.06765','0.05568','−0.00936'),('Nearest','0.07129','0.05929','+0.00126'),('Linear','0.05524','0.04342','−0.00980'),('RBF','0.04959','0.04039','−0.00116'),('SVR','0.05774','0.04974','−0.00770')],[2.4,1.4,1.4,1.45],caption='Equal-run experimental errors on the 360 common supported targets')
p('Outside-hull equal-run RMSE is 0.07789 m/s for the mean, 0.09041 for nearest, 0.06726 for RBF and 0.07999 for SVR. Linear is unsupported. Low aggregate bias can conceal large individual errors; bias and RMSE are not interchangeable.')
fig(E+'matched_with_variation.png','Matched cell-point CFD speed against twelve experimental means with horizontal ±1 temporal SD bars from the raw record. Bars describe fluctuating readings, not uncertainty of the mean, and no independence-based standard-error reduction is applied.',6.2)
p('CFD is above every matched mean. Some temporal SD bars overlap equality and others do not, but this plot supplies no confidence-level test of model agreement. Samples are time-correlated, sensor calibration uncertainty is not quantified, and one plane cannot distinguish turbulence, diffuser, leakage or boundary effects. The 58 valid HVAC readings and 882 valid raw speed samples per sensor support window auditing; they do not supply 882 independent physical replications.')
"""
source=source.replace('for root in [doc.styles.element,doc.element]:',extra+'\nfor root in [doc.styles.element,doc.element]:')
source=source.replace('data/processed/stability_study/diffusion_stability.png','docs/report/assets/diffusion_stability.png')
source=source.replace('MMA3001_Jet_Bridge_Revised_Report.docx','MMA3001_Jet_Bridge_Evidence_Report.docx')
source=source.replace('\nms median',r'\nms median')
exec(compile(source,str(BASE),'exec'))


