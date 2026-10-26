"""Apply the final review to the retained, reproducible report source."""
from pathlib import Path
import os
import subprocess

previous=Path(__file__).with_name('build_evidence_report.py')
code=previous.read_text(encoding='utf-8')
exec(compile(code.rsplit("exec(compile(source,str(BASE),'exec'))",1)[0],str(previous),'exec'))
repo=Path(__file__).resolve().parents[2]
revision=os.environ.get('JETBRIDGE_REPORT_REVISION') or subprocess.check_output(['git','-C',str(repo),'rev-parse','HEAD'],text=True).strip()
source=source.replace("\"'evidence_report_output'\"","\"'submission_report_output'\"")
source=source.replace('MMA3001_Jet_Bridge_Evidence_Report.docx','MMA3001_Jet_Bridge_Submission_Draft.docx')
source=source.replace('25 October 2026 | https://github.com','26 October 2026 | https://github.com')
source=source.replace("E='docs/report/evidence/'", "E='docs/report/evidence/'\nN='docs/report/final_checks/'\ndoc.styles['Normal'].font.size=Pt(11)\ndoc.styles['Caption'].font.size=Pt(10)")
source=source.replace("return _original_table(headers,rows,widths)","t=_original_table(headers,rows,widths)\n    for row in t.rows:\n        for cell in row.cells:\n            for para in cell.paragraphs:\n                for run in para.runs: run.font.size=Pt(9.5)\n    return t")
source=source.replace("fig(E+'experimental_reconstruction.png'", "fig(N+'experimental_10ft_coverage.png'")
source=source.replace('White boundaries identify the full-array hull, outside which the coloured field is extrapolation.', 'Black hull boundaries and hatching distinguish extrapolation. The annotation reports physical area coverage; unhatched colour is still a fitted estimate, not calibrated local certainty.')
source=source.replace('S01-A-10-HN-1 measurements and full-array RBF/SVR refits on a common speed scale.', 'S01-A-10-HN-1 measurements and full-array refits on a common speed scale. Hatching marks extrapolation; only 41.3% of physical area lies within the full-array hull.')
source=source.replace('RBF spans 0.0826–0.1579 m/s and SVR 0.0775–0.1604 m/s','RBF spans 0.0826–0.1581 m/s and SVR 0.0775–0.1604 m/s')
source=source.replace('The outer loop withholds each sensor location. Any repeated observations at that location stay together. SVR selects among 12 parameter combinations using three grouped inner folds containing only outer training data, then refits before outer prediction. Scaling is fitted within training data. This prevents the held-out target from selecting model complexity.', 'Each file contains one averaged speed at each unique sensor position. Separate files are not pooled. The outer leave-one-location-out split trains on 11 and tests on 1 point for 12-point layouts, or trains on 23 and tests on 1 for 24-point layouts. Inner three-fold tuning groups unique locations, with training-only scaling. There are no multiple observations to group at a position in these averaged fits; grouping protects location separation in the reusable implementation.')
source=source.replace('The grid spans two orders of magnitude in C, two spatial scales and two epsilon values as a deliberately small training-only search. It is not established as sufficient. Across 504 outer folds, C = 0.1 / 1 / 10 is selected 243 / 196 / 65 times; gamma = 0.1 / 1 occurs 316 / 188 times. Both tested gamma and epsilon values are grid endpoints. Appendix C records every combination and the limits of selection from small inner folds.', 'The small grid is not established as sufficient: C = 0.1 is selected in 243/504 folds (48.2%), so stronger regularisation may be requested. Gamma and epsilon each have only two endpoint candidates. An exploratory extension adds C = 0.01 using the same nested splits; Appendix C reports its separate results. It does not justify claiming globally optimal SVR settings.')
# Add the example that directly supports the station-dependent conclusion.
source=source.replace('Broader claims require an independent layout or operating-condition test.', 'Broader claims require an independent layout or operating-condition test. Figure 9 in Appendix D shows the decisive 58 ft example: SVR smooths a high-speed row, while RBF retains more variation but predicts unphysical negative speed outside the hull. Neither relative advantage nor visual fit establishes adequate pointwise accuracy.')
assert 'Figure 9 in Appendix D' in source
# Replace the long residual recital with its engineering implication.
start=source.index("p('At iteration 237, reported initial residuals")
end=source.index("p('Saved-field y-plus",start)
source=source[:start]+"""p('At iteration 237 the configured SIMPLE residual screens are satisfied, with reported global continuity error 4.00 × 10⁻¹¹. Final sensors and patch fluxes were postprocessed at the saved field; complete residual values are retained in the repository [4]. These checks establish numerical consistency with the equations and stopping criteria, not correct physical boundary assumptions.')
p('The prescribed volumetric flow establishes the inlet mass-flow condition, and continuity checks consistency of the computed solution. Neither guarantees a correct local speed profile. The idealised full-face supply can differ materially from the real diffuser even when its net flow is correct. Wall treatment, omitted leakage and the steady turbulence assumption add separate modelling uncertainty.')
"""+source[end:]
# Give the CFD figure a readable two-row layout while retaining the main-page limit.
start=source.index("page('7 Spatial CFD")
end=source.index("page('8 Sensitivity",start)
source=source[:start]+"""
page('7 Spatial CFD errors and the original discrepancy')
p('The 28 ft numerical example uses 24 hybrid virtual sensors and disjoint candidate/reference grids. It tests reconstruction of the saved CFD field, not experimental truth. The larger panels expose where a plausible reconstruction misses local structure.')
fig(N+'cfd_reconstruction_large.png','CFD reference and RBF/SVR reconstructions above; signed full-section errors below. Shared scales support comparison, and black dots mark training samples. Neither smoothness nor net-flow consistency establishes agreement with the physical apparatus.',6.55)
p('Both methods recover the broad high-speed core but smooth its near-wall gradient. Underprediction bands just inside the walls coexist with overprediction in the outermost sampled band. Whole-plane RMSE is 0.02331 m/s for RBF and 0.02515 for SVR; maximum absolute errors reach 0.05750 and 0.05904 m/s. These maps explain why boundary coverage and the intended prediction domain matter.')
p('Across planes, 24-sensor hybrid placement reduces baseline RBF error from 0.03388 to 0.02658 m/s and SVR from 0.03365 to 0.02844 m/s versus interior placement. An average benefit persists at 80% supply flow with refitted models, but not at every plane. This is exploratory layout transfer with new sensor values, not frozen-model generalisation.')
p('The motivating high-upstream/low-downstream experimental discrepancy remains unresolved. A matched 10 ft audit cannot establish a station trend; different HVAC flows and sequential windows make an unmatched error curve misleading. Resolving it requires station-specific matched boundary/window cases, repeatability context and directional measurements if net flux is inferred. Diffuser, leakage and turbulence explanations remain hypotheses.')

"""+source[end:]
source=source.replace("fig(E+'empirical_perturbation.png'", "fig(N+'perturbation_large.png'")
source=source.replace("uncertainty interval.',6.35)","uncertainty interval.',6.55)")
source=source.replace('Independent Gaussian perturbations omit spatial/time correlation and physical co-variation; they are a declared stress-test assumption.', 'The independent Gaussian perturbations omit spatial/time correlation and physical co-variation. Real flow variations may move neighbouring sensors together; correlated perturbations could change the comparison. This is a specified sensitivity scenario, not realistic sensor noise established from calibration.')
source=source.replace('74 tests pass','75 tests pass')
source=source.replace('Implementation and evidence commit 1f293e58f46b93ffc32929764847390a62f29994, generated 25 October 2026. This is a local revision pending publication.',f'Implementation and evidence commit {revision}, generated 26 October 2026. Repository availability and clean-clone checks are recorded in the final-review audit.')
source=source.replace('a local revision is not evidence of a GitHub publication.', 'the final-review audit records the published revision separately from the document packaging commit. The licence remains undecided by the author.')
# Add a separate appendix continuation so font growth does not crowd main pages.
anchor="page('Appendix D Accuracy and matched measurement variation')"
extra="""
page('Appendix C Exploratory lower C sensitivity')
p('The original lower C boundary was selected in 48.2% of outer folds. Adding C = 0.01 directly tests the request for stronger regularisation without changing gamma or epsilon. The expanded grid has 16 candidates; every outer target is withheld before three-fold inner selection, using the same separate-run and training-only scaling rules. The original grid and its primary results remain unchanged.')
table(['Evaluation','Original SVR RMSE m/s','Expanded SVR RMSE m/s'],[
('Common supported targets','0.05774','0.05884'),('Outside-hull targets','0.07999','0.07929'),('12-point files supported','0.01955','0.01943'),('24-point files supported','0.24869','0.25586')],[2.5,2.075,2.075],caption='Separate post-hoc sensitivity to adding C = 0.01 with otherwise identical nested evaluation')
p('The expanded search selects C = 0.01 in 143 of 504 folds (28.4%), C = 0.1 in 111, C = 1 in 187 and C = 10 in 63. Selection at the new lower edge still prevents a claim of a fully bounded optimum. Greater regularisation is sometimes preferred by the inner folds, but aggregate supported-region prediction does not improve. The tiny improvement in the 12-point group coexists with a worse 24-point result.')
p('This extension was motivated after inspection of the primary results. Although each outer target remains excluded from its own tuning, the broader research decision is post-hoc. It is an exploratory sensitivity analysis, not an untouched confirmatory test or a reason to choose a new final model from the outer scores. It shows why lower-bound frequency alone does not establish that expanding the search will improve generalisation.')
p('The original computational timing table measures the 12-candidate search. It must not be relabelled as the cost of this 16-candidate extension, which was not subjected to the same repeated timing experiment. Search/split records and the new leakage regression test are retained with the implementation.')

"""
source=source.replace(anchor,extra+anchor)
anchor='for root in [doc.styles.element,doc.element]:'
extra="""
page('Appendix D The decisive 58 ft example')
p('This is the first 58 ft replicate, not a best-case selection. It uses 24 sequential A/B sensor positions and illustrates the station where the aggregate RBF advantage is concentrated. Full-array fits and held-location residuals remain distinct. Only 49.7% of the physical section lies inside the full measured hull; hatching marks the rest.')
fig(N+'experimental_58ft_coverage.png','S01-A-58-HN-1 measurements, RBF/SVR full-array refits and genuine held-location residuals. Circles are RBF and squares SVR, with small horizontal offsets. All speed panels share a scale including unphysical RBF extrapolation; hatching must not be interpreted as validated area.',6.55)
p('Measured speeds span 0.172–0.805 m/s and vary strongly between nearby heights and columns. The full-array SVR fit (C = 0.1, gamma = 1, epsilon = 0.01) smooths these contrasts, spanning about 0.307–0.599 m/s. RBF retains more variation, but its full-grid range −0.152 to 1.234 m/s overshoots the observations. Its negative speed occurs outside the hull and is physically inadmissible; no clipping is applied to conceal it.')
p('Held-location supported RMSE is 0.18893 m/s for RBF and 0.23342 for SVR in this example. At x = 0.83 m and local height 0.613 m, SVR predicts 0.346 m/s for an observed 0.747 m/s. At x = 1.11 m at the same height, it predicts 0.389 for 0.780 m/s. These underpredictions are consistent with smoothing the high-speed row. RBF also misses it and has a maximum supported absolute error of 0.356 m/s; its relative advantage does not imply adequate pointwise accuracy.')
p('The measured contrast could reflect local flow structure or sequential/operating variation; the sparse data do not resolve that cause. Neither the fitted surface nor this representative residual map establishes continuous experimental truth. The appropriate conclusion concerns conditional model behaviour and support, not a universally superior physical reconstruction.')

"""
source=source.replace(anchor,extra+anchor)
exec(compile(source,str(previous),'exec'))
