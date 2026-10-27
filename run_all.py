"""Run the jet-bridge demonstration from included inputs in one new workspace.

Run inside Ubuntu/WSL with OpenCFD v2412 for live/full profiles. Replay redraws
recorded numerical evidence and never claims to have run a CFD solver.
"""
import argparse
from datetime import datetime, timezone
from hashlib import sha256
import html
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
from time import perf_counter

ROOT = Path(__file__).resolve().parent
BUNDLE = ROOT / 'data/demo'
FOAM = Path('/usr/lib/openfoam/openfoam2412/etc/bashrc')


def verify_bundle(bundle):
    """Verify every declared input before using it.

    Parameters
    ----------
    bundle : pathlib.Path
        Included demo data directory containing manifest.json.

    Returns
    -------
    int
        Number of hash-verified data files.
    """
    bundle = Path(bundle).resolve()
    manifest = json.loads((bundle / 'manifest.json').read_text())
    for record in manifest['files']:
        path = (bundle / record['path']).resolve()
        if not path.is_relative_to(bundle):
            raise ValueError('Bundle manifest escapes its directory')
        if not path.is_file() or sha256(path.read_bytes()).hexdigest() != record['sha256']:
            raise ValueError(f'Bundled input missing or changed: {record["path"]}')
    return len(manifest['files'])


def validate_destination(path):
    """Reject overwrites and output inside tracked input/source directories.

    Parameters
    ----------
    path : pathlib.Path
        Requested fresh output directory.

    Returns
    -------
    pathlib.Path
        Resolved safe destination; no directory is created here.
    """
    path = Path(path).resolve()
    if path.exists():
        raise ValueError('Output exists; choose a new directory. Previous runs are preserved.')
    for protected in ('data/demo', 'cfd/cases', 'src', 'tests', 'docs', '.git'):
        if path.is_relative_to(ROOT / protected):
            raise ValueError(f'Output cannot be inside {protected}')
    return path


class Demo:
    """Execute logged stages and retain a failure-aware provenance manifest."""

    def __init__(self, output, profile):
        self.output = output
        self.profile = profile
        self.records = []
        self.runner_digest = sha256(Path(__file__).read_bytes()).hexdigest()
        self.environment = dict(os.environ, PYTHONPATH=str(ROOT / 'src'), PYTHONUTF8='1')
        self.active = None

    def command(self, name, command, cwd=ROOT, lineage='computed from included measurements'):
        """Execute one checked subprocess with a visible stage and saved log."""
        self.active = name
        logfile = self.output / f'log.{name}'
        print(f'[{len(self.records) + 1:02d}] {name}  ({lineage})', flush=True)
        started = perf_counter()
        record = dict(stage=name, command=list(map(str, command)), lineage=lineage, log=logfile.name)
        self.records.append(record)
        try:
            with logfile.open('w', encoding='utf-8') as handle:
                subprocess.run(list(map(str, command)), cwd=cwd, env=self.environment,
                               stdout=handle, stderr=subprocess.STDOUT, check=True)
        except subprocess.CalledProcessError:
            record['status'] = 'failed'
            raise
        finally:
            record['elapsed_seconds'] = round(perf_counter() - started, 3)
        record['status'] = 'complete'
        print(f'     done in {record["elapsed_seconds"]:.1f} s', flush=True)

    def module(self, name, module, arguments, lineage='computed from included inputs'):
        """Run an existing module using the same Python interpreter."""
        self.command(name, [sys.executable, '-m', module, *map(str, arguments)], lineage=lineage)

    def foam(self, name, command, case):
        """Run a fresh OpenFOAM stage after sourcing the supported runtime."""
        import shlex
        # OpenFOAM's environment scripts use optional probes with nonzero returns.
        # Enable fail-fast execution after sourcing, not inside those scripts.
        shell = 'source ' + shlex.quote(str(FOAM)) + '; set -e; exec ' + shlex.join(command)
        self.command(name, ['bash', '-lc', shell], cwd=case, lineage='fresh CFD execution')
        target = 'log.yPlus' if name == 'yPlus' else 'log.' + command[0]
        shutil.copyfile(self.output / f'log.{name}', case / target)

    def gallery(self):
        """Index all regenerated figures, retaining their stage directories."""
        pictures = sorted(self.output.rglob('*.png'))
        rows = []
        inventory = []
        for path in pictures:
            relative = path.relative_to(self.output).as_posix()
            inventory.append(dict(path=relative, sha256=sha256(path.read_bytes()).hexdigest()))
            rows.append(f'<section><h3>{html.escape(relative)}</h3><a href="{html.escape(relative)}">'
                        f'<img loading="lazy" src="{html.escape(relative)}" alt="{html.escape(relative)}"></a></section>')
        warning = ('Fresh isothermal CFD is separated from archived mesh/thermal diagnostics. '
                   'Thermal fields remain unconverged and excluded from training. '
                   'Replay means redrawing saved evidence, not executing its original simulation.')
        page = '<!doctype html><meta charset="utf-8"><title>Jet bridge demo figures</title>'
        page += '<style>body{font:16px system-ui;max-width:1200px;margin:2rem auto}img{max-width:100%}section{margin:3rem 0}</style>'
        page += f'<h1>Jet bridge demo — {self.profile}</h1><p>{warning}</p>' + ''.join(rows)
        (self.output / 'index.html').write_text(page, encoding='utf-8')
        (self.output / 'figure_inventory.json').write_text(json.dumps(inventory, indent=2) + '\n')
        return len(inventory)

    def run(self, quality=True):
        """Run the declared pipeline, failing before downstream fits on bad CFD."""
        out = self.output
        dataset = BUNDLE / 'experimental'
        metadata = BUNDLE / 'cases_metadata'
        analysis = out / 'analysis'
        analysis.mkdir()
        for section in ('matched', 'thermal', 'verification'):
            shutil.copytree(BUNDLE / 'reference' / section, analysis / section)
        tables = out / 'field_tables'
        shutil.copytree(BUNDLE / 'field_tables', tables)
        if quality:
            self.module('lint', 'ruff', ['check', 'src', 'tests', 'run_all.py'], 'static correctness checks')
            self.module('tests', 'pytest', ['-q', '-p', 'no:cacheprovider', '--junitxml', out / 'test-results.xml'], 'numerical/software tests')
        mesh = ROOT / 'cfd/cases/empty_bridge_s01_a_10_hn_1/system/blockMeshDict'
        iso = metadata / 'iso'
        iso_comparisons = BUNDLE / 'iso_comparisons'
        verification = BUNDLE / 'verification'
        saved = '237'
        if self.profile != 'replay':
            iso = out / 'cfd/baseline'
            iso.mkdir(parents=True)
            source = ROOT / 'cfd/cases/empty_bridge_s01_a_10_hn_1'
            for folder in ('0', 'constant', 'system'):
                shutil.copytree(source / folder, iso / folder, ignore=shutil.ignore_patterns('polyMesh'))
            control = iso / 'system/controlDict'
            control.write_text(re.sub(r'endTime\s+\d+\s*;', 'endTime 600;', control.read_text()))
            for tool in ('blockMesh', 'checkMesh', 'simpleFoam'):
                self.foam(tool, [tool], iso)
                if tool == 'checkMesh' and 'Mesh OK' not in (iso / 'log.checkMesh').read_text():
                    raise RuntimeError('Fresh mesh did not pass checkMesh')
            log = (iso / 'log.simpleFoam').read_text()
            match = re.search(r'SIMPLE solution converged in (\d+) iterations', log)
            if not match:
                raise RuntimeError('Baseline did not converge within 600 iterations; numerical references rejected')
            saved = match[1]
            if not (iso / saved / 'U').is_file():
                raise RuntimeError('Converged saved velocity field is missing')
            self.foam('yPlus', ['simpleFoam', '-postProcess', '-func', 'yPlus', '-time', saved], iso)
            self.module('fresh_report_grid', 'jetbridge_ml.demo_grid', ['--case', iso, '--dataset', dataset, '--output', out / 'fresh_grid', '--time', saved], 'fresh isothermal samples')
            shutil.copyfile(out / 'fresh_grid/sampled_iso.csv', tables / 'sampled_iso.csv')
            iso_comparisons = out / 'iso_comparisons'
            self.module('iso_comparisons', 'jetbridge_ml.cfd_interface.plot_comparison', ['--case', iso, '--dataset', dataset, '--output', iso_comparisons, '--time', saved], 'fresh isothermal versus experimental means')
            self.module('matched', 'jetbridge_ml.cfd_interface.matched_audit', ['--case', iso, '--dataset', dataset, '--output', out / 'matched_fresh'], 'fresh matched sensor samples')
            shutil.copytree(out / 'matched_fresh', analysis / 'matched', dirs_exist_ok=True)
            self.module('virtual_samples', 'jetbridge_ml.cfd_interface.virtual_sensors', ['--case', iso, '--dataset', dataset, '--output', out / 'virtual_samples', '--time', saved], 'fresh numerical virtual sensors')
            self.module('virtual_svr', 'jetbridge_ml.virtual_benchmark', ['--samples', out / 'virtual_samples', '--output', out / 'virtual_svr'], 'fresh CFD reference; not physical truth')
            dense = out / 'virtual_samples/dense_test.csv'
            if self.profile == 'full':
                verification = out / 'verification_cases'
                self.module('verification_cases', 'jetbridge_ml.cfd_interface.verification_study', ['--baseline', iso, '--dataset', dataset, '--output', verification], 'fresh coarse/fine/flow80 CFD solves')
                status = json.loads((verification / 'manifest.json').read_text())
                if not all(c['solver_converged'] and c['mesh_ok'] for c in status['cases'].values()):
                    raise RuntimeError('A verification CFD case failed mesh/convergence checks')
        else:
            dense = BUNDLE / 'virtual_samples/dense_test.csv'
            iso_comparisons = out / 'iso_comparisons'
            self.module('iso_comparisons', 'jetbridge_ml.cfd_interface.plot_comparison', ['--case', iso, '--dataset', dataset, '--output', iso_comparisons, '--time', saved, '--replay-inputs', BUNDLE / 'iso_comparisons'], 'archived numerical samples; no CFD execution')
            self.module('virtual_svr', 'jetbridge_ml.virtual_benchmark', ['--samples', BUNDLE / 'virtual_samples', '--output', out / 'virtual_svr'], 'archived converged numerical samples; no CFD execution')
        self.module('verification_summary', 'jetbridge_ml.cfd_interface.verification_results', ['--study', verification, '--output', out / 'verification_summary'], 'fresh verification cases' if self.profile == 'full' else 'archived mesh/flow tables')
        shutil.copytree(out / 'verification_summary', analysis / 'verification', dirs_exist_ok=True)
        self.module('experimental', 'jetbridge_ml.experimental_svr', ['--dataset', dataset, '--mesh', mesh, '--output', analysis / 'experimental'])
        self.module('legacy_interpolation', 'jetbridge_ml.benchmark', ['--dataset', dataset, '--output', out / 'legacy_interpolation'])
        self.module('paired', 'jetbridge_ml.paired_analysis', ['--metrics', analysis / 'experimental/metrics.csv', '--output', analysis / 'paired'])
        self.module('stability', 'jetbridge_ml.stability_study', ['--output', analysis / 'stability'])
        self.module('sensor_design', 'jetbridge_ml.sensor_design_study', ['--candidates', tables / 'sampled_iso.csv', '--reference', dense, '--output', analysis / 'sensor_design'], 'fresh baseline samples' if self.profile != 'replay' else 'archived baseline samples')
        self.module('thermal_comparisons', 'jetbridge_ml.cfd_interface.plot_thermal', ['--case', metadata / 'thermal', '--control', metadata / 'control', '--replay-inputs', BUNDLE / 'thermal_comparisons', '--output', out / 'thermal_comparisons'], 'ARCHIVED unconverged thermal diagnostics')
        self.module('thermal_diagnostics', 'jetbridge_ml.cfd_interface.thermal_audit', ['--restart-source', metadata / 'thermal', '--continuation', metadata / 'continuation', '--archived-inputs', BUNDLE / 'reference/thermal', '--output', out / 'thermal_diagnostics'], 'ARCHIVED unconverged thermal diagnostics')
        shutil.copytree(out / 'thermal_diagnostics', analysis / 'thermal', dirs_exist_ok=True)
        self.module('field_gallery', 'jetbridge_ml.cfd_interface.report_figures', ['--isothermal', iso, '--thermal', metadata / 'thermal', '--control', metadata / 'control', '--dataset', dataset, '--iso-comparisons', iso_comparisons, '--thermal-comparisons', out / 'thermal_comparisons', '--replay-tables', tables, '--iso-time', saved, '--output', out / 'field_gallery'], 'fresh iso / archived thermal' if self.profile != 'replay' else 'archived field tables')
        self.module('additional_figures', 'jetbridge_ml.report_synthesis', ['--analysis', analysis, '--verification-samples', verification, '--output', out / 'additional_figures'])
        self.module('performance', 'jetbridge_ml.controlled_performance', ['--predictions', analysis / 'experimental/predictions.csv', '--output', out / 'performance', '--repeats', '20'], 'new hardware-dependent repeated timings')
        self.module('compact_figures', 'jetbridge_ml.revision_figures', ['--analysis', analysis, '--mesh', mesh, '--output', out / 'compact_figures'])
        self.module('report_evidence', 'jetbridge_ml.report_evidence', ['--analysis', analysis, '--performance', out / 'performance', '--mesh', mesh, '--output', out / 'report_evidence'])
        self.module('final_checks', 'jetbridge_ml.final_report_checks', ['--predictions', analysis / 'experimental/predictions.csv', '--evidence', out / 'report_evidence', '--mesh', mesh, '--output', out / 'final_checks'])
        self.module('api_docs', 'pdoc', ['jetbridge_ml', '-o', out / 'html'], 'regenerated API documentation')
        return self.gallery()


def main():
    """Parse the demo profile, verify data and write success/failure provenance."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profile', choices=('live', 'full', 'replay'), default='live')
    parser.add_argument('--output', type=Path)
    parser.add_argument('--skip-quality', action='store_true', help='Skip lint/tests only; recorded in manifest')
    parser.add_argument('--plan', action='store_true', help='Print scope without creating files or running commands')
    args = parser.parse_args()
    if args.plan:
        print(json.dumps(dict(profile=args.profile, fresh_cfd=args.profile != 'replay', fresh_mesh_study=args.profile == 'full', archived_thermal=True, preserved_primary_scores=True), indent=2))
        return
    output = validate_destination(args.output or ROOT / 'demo_runs' / datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'))
    print('Verifying included input hashes before creating a run...', flush=True)
    count = verify_bundle(BUNDLE)
    print(f'Verified {count} included files.', flush=True)
    if args.profile != 'replay' and (os.name == 'nt' or not FOAM.is_file()):
        parser.error('Run live/full inside Ubuntu/WSL with OpenCFD v2412 installed; see docs/LIVE_DEMO.md. Replay needs no OpenFOAM.')
    output.mkdir(parents=True)
    demo = Demo(output, args.profile)
    manifest = dict(profile=args.profile, verified_input_files=count, quality_checks=not args.skip_quality,
                    thermal='archived, unconverged; not training/reference data', status='running',
                    started_utc=datetime.now(timezone.utc).isoformat(), python=sys.version,
                    bundle_manifest_sha256=sha256((BUNDLE / 'manifest.json').read_bytes()).hexdigest())
    try:
        manifest['figure_count'] = demo.run(quality=not args.skip_quality)
        manifest['status'] = 'complete'
        print(f'DEMO COMPLETE: {manifest["figure_count"]} regenerated PNG figures\nOpen {output / "index.html"}', flush=True)
    except Exception as error:
        manifest.update(status='failed', failed_stage=demo.active, error=str(error))
        print(f'DEMO FAILED at {demo.active}: {error}\nLogs preserved at {output}', file=sys.stderr)
        raise
    finally:
        manifest['stages'] = demo.records
        manifest['runner_sha256'] = demo.runner_digest
        (output / 'demo_manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')


if __name__ == '__main__':
    main()
