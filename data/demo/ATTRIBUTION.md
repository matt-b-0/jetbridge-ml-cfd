# Included experimental and numerical demonstration data

The experimental files under `experimental/` are unmodified selected files from:

Lebbin, P. and Laengert, S. (2026). *Communicable Disease Transmission in Air Travel: Jet Bridge Ventilation Dataset*. Civil Aerospace Medical Institute, Federal Aviation Administration; National Research Council of Canada. DOI: https://doi.org/10.21949/qqdx-gh59.

The official repository record https://rosap.ntl.bts.gov/view/dot/92577 explicitly lists Creative Commons Attribution 4.0 International (CC BY 4.0), verified on 27 October 2026. Licence: https://creativecommons.org/licenses/by/4.0/. This is attribution to the dataset's creators, not an endorsement of this student project. The later released dataset record is the cited reuse statement; older planning documents can describe different anticipated terms.

The selection includes source geometry templates, statistical-average files, HVAC records, acquisition periods, the data dictionary and the matched isothermal raw speed record. Duplicate TXT time-series exports and unrelated particle time series are excluded because this workflow does not use them. The source archive remains available from the DOI. Original experimental files are not edited or converted in this bundle; the readers perform documented conversions in memory.

`field_tables/`, `verification/`, `virtual_samples/`, `reference/`, `thermal_comparisons/` and `iso_comparisons/` contain compact derived CFD/analysis exports from the recorded project runs. They are numerical evidence, not raw experimental truth. Thermal field samples are unconverged snapshots and remain excluded from reference/training use. All generated meshes and solved time-directory fields are excluded.

`cases_metadata/` contains only case dictionaries, original run logs, probe histories and setup metadata. It is not a collection of runnable saved solutions. No placeholder U/T field is supplied to impersonate a solved case. New CFD runs are created from the tracked runnable baseline under `cfd/cases/`, in separate output directories.

`manifest.json` records each included input's path, size, origin, role and SHA-256. The runner verifies it before use. Figure modules that explicitly replay these tables record that fact in their own manifests; the demo manifest records the fresh/archived split for each stage.

The dataset's CC BY 4.0 statement is independent of the student's project code. The project-code licence remains undecided under the author's instruction; this notice does not select one.
