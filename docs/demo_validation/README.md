# Demo verification on 27 October 2026

The executable implementation/data revision is `42814365cd0fcc86ccd49b29a3be330f0c74935c`. A new public GitHub clone under the Linux home directory, without the original OneDrive dataset, completed replay and live profiles. The bundled manifest verified all 2,333 declared inputs. Ruff and 82 tests passed. Hosted CI passed: https://github.com/matt-b-0/jetbridge-ml-cfd/actions/runs/40484525200.

| Profile | PNG output files | Total stage time | Fresh CFD |
| --- | ---: | ---: | --- |
| replay | 74 | 210 s / 3.5 min | None |
| live | 80 | 286 s / 4.8 min | Baseline |
| full | 80 | 772 s / 12.9 min | Baseline, coarse, fine, flow80 |

Times are measured on this workstation, exclude initial input hashing and are not guarantees. PNG counts include contact sheets and repeated analysis views, not 80 statistically independent results. Live/full additionally render the matched raw/sampling audit and its analysis views. Replay retains archived matched values for the other report figures.

The complete full run was exercised locally. It passed all four mesh/convergence checks at 237, 115, 380 and 237 iterations respectively. Live and replay were then checked from the published frozen implementation. Both runs recorded the expected runner hash. All three profiles reproduced the original experimental error summaries within rtol 1e-10 / atol 1e-12. Timing results are newly measured and are not expected to match archived timings.

The per-profile folders retain stage manifests, output inventories and available JUnit records. These small records are included instead of the generated meshes, solved fields or complete output galleries. `summary.json` records the numerical comparison checks; `lint.txt` and `test-results.xml` record the final local quality gate.

Thermal graphics redraw archived unconverged numerical evidence; they are never presented as newly converged CFD or used as reference/training data. No physical experimental validation or automatic mesh-independence claim follows from this successful software demonstration. Data attribution is separate from the undecided project-code licence.
