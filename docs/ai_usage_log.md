# AI-use log (for MMA3001 reflection)

Record every material use of AI, the independent verification you performed, and decisions you made yourself. Example starting entry:

| Date | Tool / contribution | Verification or limitation | Student decision |
|---|---|---|---|
| 2026-10-24 | ChatGPT: suggested repository structure, wrote starter `AGENTS.md` / context files, basic Python package and unit tests | Python tests must be rerun locally; existing CFD baseline was not executed in the source environment | Review design, independently validate numerical assumptions, decide whether to adopt each suggestion |

Update this table as work develops; do not claim checks you haven't done yourself.
| 2026-10-24 | Codex: audited included source geometry and sensor coordinate mapping; initialised local Git repository on main and configured Linux script line endings | 14 of 16 vertices match the included boundary template; upper ceiling differs by 0.127 mm; published probe coordinates match source averages; no OpenFOAM mesh or solver checks run. WSL installation attempted; completion pending. Raw source files remain ignored. | Geometry and sensor corrections remain pending review; no GitHub publication performed |
