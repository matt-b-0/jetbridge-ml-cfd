# Resolved implementation checks and remaining research questions

## Reproduced implementation

- OpenCFD v2412 is the tested solver distribution; its runtime is sourced by the demo driver.
- The full demo reproduced all four isothermal mesh/convergence checks and regenerated 80 PNG figures. This is numerical consistency, not physical validation.
- Matched raw/HVAC windows, unique averaged sensor positions and nested held-location splits are documented in the existing audits. Separate replicate files are not pooled.
- Experimental speed prediction, CFD-field reconstruction and net signed flux remain separate comparisons.
- The official FAA/NRC data record identifies CC BY 4.0; the included subset has attribution and hashes in data/demo. The project-code licence remains undecided under the author's instruction.

## Remaining scientific questions

1. What wall treatment, inlet diffuser detail, leakage and pressure-boundary evidence are needed to explain the local CFD/experiment discrepancy?
2. Can matched-condition comparisons across stations resolve the motivating upstream/downstream pattern without pooling asynchronous or different-flow observations?
3. What independent sensor layout or operating case and engineering acceptance threshold should support a stronger prediction claim?
4. Can thermal assumptions and numerical settings be tested systematically until an eligible converged thermal reference exists? Current thermal evidence remains unconverged.
5. How do documented instrument uncertainty and spatially correlated flow variations change reconstruction sensitivity?

For execution and quality checks use [LIVE_DEMO.md](LIVE_DEMO.md) and [DEVELOPMENT.md](DEVELOPMENT.md): python run_all.py, Ruff linting, pytest and generated API documentation. Passing these checks does not resolve the scientific questions above.
