# AI-use log (for MMA3001 reflection)

Record every material use of AI, the independent verification you performed, and decisions you made yourself. Example starting entry:

| Date | Tool / contribution | Verification or limitation | Student decision |
|---|---|---|---|
| 2026-10-24 | ChatGPT: suggested repository structure, wrote starter `AGENTS.md` / context files, basic Python package and unit tests | Python tests must be rerun locally; existing CFD baseline was not executed in the source environment | Review design, independently validate numerical assumptions, decide whether to adopt each suggestion |

Update this table as work develops; do not claim checks you haven't done yourself.
| 2026-10-24 | Codex: audited included source geometry and sensor coordinate mapping; initialised local Git repository on main and configured Linux script line endings | 14 of 16 vertices match the included boundary template; upper ceiling differs by 0.127 mm; published probe coordinates match source averages; no OpenFOAM mesh or solver checks run. WSL installation attempted; completion pending. Raw source files remain ignored. | Geometry and sensor corrections remain pending review; no GitHub publication performed |
| 2026-10-24 | Codex: installed Ubuntu 24.04 under WSL 2 and OpenCFD OpenFOAM v2412 (2412.260127-1); ran isolated case checks in /var/tmp/jetbridge-check.JeXzJa | Existing static checker passed; blockMesh completed and checkMesh reported Mesh OK (maximum non-orthogonality 4.7816886 degrees, skewness 0.10708159). simpleFoam dry run failed because inletFlux lacks required writeFields entry. No converged simulation or experimental validation. Original case inputs unchanged. | Review compatibility fix before applying to original case; Linux user setup remains to be completed |
