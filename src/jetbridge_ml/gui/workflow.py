"""Isolated, failure-aware scientific jobs launched by the desktop GUI."""
import argparse
from dataclasses import asdict
from datetime import datetime, timezone
from hashlib import sha256
import html
from importlib.metadata import version
import json
import os
import queue
import threading
from pathlib import Path
import re
import shlex
import shutil
import signal
import subprocess
import sys
from time import perf_counter

from .parallel import validate_resources, mpi_command, write_decomposition, available_cpus
from .config import RunSpec, MESHES, cell_count, validate_output
from .residuals import ResidualRecorder, read_history, COLUMNS

FOAM = Path('/usr/lib/openfoam/openfoam2412/etc/bashrc')


class Cancelled(RuntimeError):
    """A user requested cooperative cancellation of this job."""


def verify_inputs(root, spec=None, cancel_file=None):
    """Hash-check exactly the bundled sources read by this job.

    Parameters
    ----------
    root : pathlib.Path
        Checkout containing data/demo and its hash manifest.
    spec : RunSpec, optional
        Request whose declared inputs are checked; None checks the full bundle.
    cancel_file : pathlib.Path, optional
        Job-specific cancellation marker, checked between files.

    Returns
    -------
    dict
        Verified input digests and the bundle manifest digest.
    """
    bundle = root / 'data/demo'
    manifest_path = bundle / 'manifest.json'
    records = json.loads(manifest_path.read_text())['files']
    if spec is None:
        selected = records
    else:
        needed = {'experimental/Data Dictionary.csv',
                  f'experimental/03-Averages/V-{spec.run_id}.txt'}
        prefixes = ()
        if spec.kind == 'fresh':
            needed.update({'experimental/06-Periods/Periods.csv',
                           f'experimental/05-HVAC/{spec.run_id}.csv'})
        if spec.kind == 'lab_cfd':
            needed = {'virtual_samples/dense_test.csv', 'virtual_samples/sampling_manifest.json',
                      'cases_metadata/iso/log.simpleFoam'}
        if spec.kind == 'archive':
            needed.update({'reference/matched/matched_sensor_audit.csv','cases_metadata/iso/log.simpleFoam'})
        if spec.kind == 'thermal':
            prefixes = ('cases_metadata/thermal/', 'cases_metadata/control/', 'thermal_comparisons/')
        selected = [r for r in records if r['path'] in needed or r['path'].startswith(prefixes)]
        if not needed.issubset({r['path'] for r in selected}):
            raise ValueError('Requested inputs are absent from the bundled hash manifest')
    verified = {}
    for record in selected:
        if cancel_file is not None and cancel_file.exists():
            raise Cancelled('Cancelled while verifying selected inputs')
        path = (bundle / record['path']).resolve()
        if not path.is_relative_to(bundle.resolve()) or not path.is_file():
            raise ValueError('Invalid or missing bundled input')
        digest = sha256(path.read_bytes()).hexdigest()
        if digest != record['sha256']:
            raise ValueError(f'Changed bundled input: {record["path"]}')
        verified[record['path']] = digest
    return dict(files=verified, bundle_manifest_sha256=sha256(manifest_path.read_bytes()).hexdigest())


def boundary_inputs(root, run_id):
    """Read the selected run's entire-set HVAC window in SI units.

    Parameters
    ----------
    root : pathlib.Path
        Repository with the attributed experimental subset.
    run_id : str
        Supported single-window S01-A-HN experiment.

    Returns
    -------
    dict
        Flow, temporal coverage and temperature context. No test targets fit Q.
    """
    import numpy as np
    import pandas as pd
    dataset = root / 'data/demo/experimental'
    periods = pd.read_csv(dataset / '06-Periods/Periods.csv', encoding='cp1252')
    match = periods[periods.Set == run_id]
    if len(match) != 1:
        raise ValueError('Fresh CFD requires one unambiguous measured HVAC window')
    row = match.iloc[0]
    path = dataset / f'05-HVAC/{run_id}.csv'
    table = pd.read_csv(path, encoding='cp1252').replace(-9999, np.nan)
    start, end = float(row['Entire Set-Start (sec)']), float(row['Entire Set-End (sec)'])
    window = table[table['Time (sec)'].between(start, end)]
    q = window['Q.FS (lps)']; q = q[np.isfinite(q) & (q >= 0)]
    if not len(q) or q.mean() <= 0:
        raise ValueError('No positive measured supply flow in the source window')
    result = dict(flow_m3s=float(q.mean() / 1000), valid_hvac_readings=len(q),
                  entire_start_sec=start, entire_end_sec=end,
                  averaging='Arithmetic mean of nonnegative valid Q.FS in Entire Set window',
                  source_sha256=sha256(path.read_bytes()).hexdigest(),
                  windows_equal=bool(start == row['Stable-Start (sec)'] and end == row['Stable-End (sec)']))
    for source, key in [('T.db.SA (°C)', 'supply_C'), ('Tdb.Lab (°C)', 'lab_C')]:
        values = window[source].dropna()
        result[key] = float(values.mean()) if len(values) else None
    return result


def prepare_case(root, output, frame, mesh, q):
    """Prepare a cold-start isothermal case without modifying the template.

    Parameters
    ----------
    root, output : pathlib.Path
        Repository and new case destination.
    frame : pandas.DataFrame
        One experiment's absolute metre sensor coordinates.
    mesh : str
        Named resolution from MESHES; all use uniform grading.
    q : float
        Positive measured supply flow in cubic metres per second.

    Returns
    -------
    dict
        Mesh counts, initial velocity scale and declared turbulence assumptions.
    """
    import numpy as np
    from jetbridge_ml.cfd_interface.plot_comparison import mesh_profile
    source = root / 'cfd/cases/empty_bridge_s01_a_10_hn_1'
    output.mkdir(parents=True, exist_ok=False)
    for folder in ('0', 'constant', 'system'):
        shutil.copytree(source / folder, output / folder, ignore=shutil.ignore_patterns('polyMesh'))
    path = output / 'system/blockMeshDict'
    nx, ny, *nz = MESHES[mesh]; index = iter(nz)
    text, count = re.subn(r'(hex\s*\([^)]*\)\s*)\(\d+\s+\d+\s+\d+\)',
                         lambda m: m[1] + f'({nx} {ny} {next(index)})', path.read_text())
    if count != 3:
        raise ValueError('Expected exactly three baseline mesh blocks')
    path.write_text(text)
    width, zs, floors, tops = mesh_profile(path)
    xyz = frame[['x_m', 'y_m', 'z_m']].to_numpy()
    local = xyz[:, 1] - np.interp(xyz[:, 2], zs, floors)
    if (np.any(xyz[:, 0] <= 0) or np.any(xyz[:, 0] >= width) or np.any(local <= 0)
            or np.any(local >= np.interp(xyz[:, 2], zs, tops - floors))
            or np.any(xyz[:, 2] <= zs[0]) or np.any(xyz[:, 2] >= zs[-1])):
        raise ValueError('Experimental sensor falls outside the CFD domain')
    height = tops[0] - floors[0]
    bulk = q / (width * height)
    dh = 2 * width * height / (width + height)
    k = 1.5 * (.05 * bulk) ** 2
    epsilon = .09 ** .75 * k ** 1.5 / (.07 * dh)
    u = output / '0/U'; text = u.read_text()
    text = re.sub(r'(volumetricFlowRate\s+constant\s+)[\d.eE+-]+',
                  lambda m: m[1] + f'{q:.12g}', text)
    text = re.sub(r'uniform\s*\(\s*0\s+0\s+-[\d.eE+]+\s*\)',
                  f'uniform (0 0 {-bulk:.12g})', text)
    u.write_text(text)
    for field, value in [('k', k), ('epsilon', epsilon)]:
        p = output / '0' / field
        p.write_text(re.sub(r'(uniform\s+)[\d.eE+-]+(\s*;)',
                            lambda m: m[1] + f'{value:.12g}' + m[2], p.read_text()))
    path = output / 'system/controlDict'; text = path.read_text()
    text = re.sub(r'endTime\s+\d+\s*;', 'endTime 600;', text)
    points = '\n'.join('(' + ' '.join(f'{v:.12g}' for v in row) + ')' for row in xyz)
    text, count = re.subn(r'probeLocations\s*\(.*?\);', 'probeLocations (\n' + points + '\n);', text, flags=re.S)
    if count != 1:
        raise ValueError('Expected one baseline probe array')
    path.write_text(text)
    return dict(cells=cell_count(mesh), counts=MESHES[mesh], bulk_speed_mps=bulk,
                initial_k_m2s2=k, initial_epsilon_m2s3=epsilon,
                intensity_assumption=.05, length_scale_m=.07 * dh,
                physics='steady isothermal k-epsilon RANS; full-face inlet; sealed no-slip walls',
                mesh_resolution_is_not_accuracy=True, iteration_cap=600)


class Job:
    """Keep stages, cancellation and source provenance separate from the GUI."""

    def __init__(self, root, output, spec):
        self.root, self.output, self.spec = root, output, spec
        self.cancel_file = output.with_name(output.name + '.cancel')
        self.manifest = dict(request=asdict(spec), status='running', stages=[],
                             started_utc=datetime.now(timezone.utc).isoformat(),
                             physical_validation='not established', fresh_cfd=False,
                             fresh_cfd_requested=spec.kind == 'fresh', solver_attempted=False,
                             mesh_resolution=spec.mesh if spec.kind == 'fresh' else 'not selectable',
                             limitations=['Scalar speed is not signed flux',
                                          'Model assumptions and mesh resolution do not establish physical accuracy'])
        self.manifest['python'] = sys.version
        self.manifest['packages'] = {name: version(name) for name in
                                      ('numpy','scipy','pandas','scikit-learn','matplotlib')}
        self.manifest['code_sha256'] = {str(p.relative_to(root)): sha256(p.read_bytes()).hexdigest()
                                       for p in sorted((root / 'src/jetbridge_ml').rglob('*.py'))}
        revision = subprocess.run(['git','-c',f'safe.directory={root}','-C',str(root),'rev-parse','HEAD'],capture_output=True,text=True)
        self.manifest['git_revision'] = revision.stdout.strip() if revision.returncode == 0 else None
        status = subprocess.run(['git','-c',f'safe.directory={root}','-C',str(root),'status','--porcelain'],capture_output=True,text=True)
        self.manifest['working_tree_dirty'] = bool(status.stdout.strip()) if status.returncode == 0 else None
        self.save()

    def save(self):
        """Atomically update a readable manifest, including incomplete jobs."""
        target = self.output / 'manifest.json'
        temp = self.output / 'manifest.tmp'
        temp.write_text(json.dumps(self.manifest, indent=2, allow_nan=False) + '\n')
        temp.replace(target)

    def check_cancel(self):
        """Stop only this isolated job when its GUI requests cancellation."""
        if self.cancel_file.exists():
            raise Cancelled('Cancelled by user; incomplete output retained')

    def command(self, name, command, cwd=None):
        """Stream a subprocess into a log and stop its Linux group on cancellation."""
        self.check_cancel(); print(f'STAGE: {name}', flush=True)
        record = dict(name=name, command=list(map(str, command)), status='running')
        self.manifest['stages'].append(record); self.save(); start = perf_counter()
        env = dict(os.environ, PYTHONPATH=str(self.root / 'src'), PYTHONUNBUFFERED='1')
        tracker = None
        with (self.output / f'log.{name}').open('w') as handle:
            proc = subprocess.Popen(command, cwd=cwd or self.root, env=env, stdout=subprocess.PIPE,
                                    stderr=subprocess.STDOUT, text=True, bufsize=1, start_new_session=True)
            if name == 'simpleFoam':
                self.manifest.update(fresh_cfd=True, solver_attempted=True)
                self.save()
            try:
                if name == 'simpleFoam':
                    tracker = ResidualRecorder(self.output / 'residual_history.csv')
                stream = queue.Queue()
                def read_output():
                    for line in proc.stdout:
                        stream.put(line)
                    stream.put(None)
                threading.Thread(target=read_output, daemon=True).start()
                while True:
                    self.check_cancel()
                    try:
                        line = stream.get(timeout=.2)
                    except queue.Empty:
                        continue
                    if line is None:
                        break
                    handle.write(line); handle.flush()
                    if tracker is not None:tracker.feed(line)
                    if line.startswith('Time = '):
                        if int(float(line.split('=')[1])) % 25 == 0:
                            print(line.strip() + ' (SIMPLE iteration)', flush=True)
                    elif (('converged' in line.lower() and name == 'simpleFoam') or 'Mesh OK' in line or 'ERROR' in line):
                        print(line.strip(), flush=True)
                if proc.wait() != 0:
                    raise RuntimeError(f'{name} failed. See log.{name}')
            except Cancelled:
                record['status'] = 'cancelled'
                raise
            except Exception:
                record['status'] = 'failed'
                raise
            finally:
                if proc.poll() is None:
                    os.killpg(proc.pid, signal.SIGTERM)
                    try:
                        proc.wait(timeout=10)
                    except subprocess.TimeoutExpired:
                        os.killpg(proc.pid, signal.SIGKILL); proc.wait()
                if tracker is not None:
                    tracker.close()
                    self.manifest['residual_samples'] = tracker.count
                record['elapsed_seconds'] = round(perf_counter() - start, 3)
        record['status'] = 'complete'; self.save()

    def foam(self, name, command, case):
        """Source the supported runtime with literal, quoted command arguments."""
        shell = 'source ' + shlex.quote(str(FOAM)) + '; set -e; exec ' + shlex.join(list(map(str, command)))
        self.command(name, ['bash', '-lc', shell], cwd=case)

    def sample(self, case, saved, points):
        """Export matched CFD points and final inlet/outlet flux, with alignment checks."""
        import numpy as np
        from scipy.spatial import cKDTree
        positions = '\n'.join('(' + ' '.join(f'{v:.12g}' for v in row) + ')' for row in points)
        text = ('FoamFile { version 2.0; format ascii; class dictionary; object guiSample; } functions { '
                'guiPoints { type sets; libs ("libsampling.so"); writeControl writeTime; setFormat raw; '
                'interpolationScheme cellPoint; fields (U); sets (points { type cloud; axis xyz; points ('
                + positions + '); }); } ')
        for name, patch in [('guiIn', 'inlet'), ('guiOut', 'outlet')]:
            text += (f'{name} {{ type surfaceFieldValue; libs ("libfieldFunctionObjects.so"); '
                     f'regionType patch; name {patch}; operation sum; writeFields false; fields (phi); }} ')
        dictionary = self.output / 'sample.dict'; dictionary.write_text(text + '}')
        self.foam('sampling', ['simpleFoam', '-case', case, '-postProcess', '-time', saved, '-dict', dictionary], case)
        files = list((case / f'postProcessing/guiPoints/{saved}').glob('points_U.*'))
        if len(files) != 1:
            raise ValueError('Cannot identify sampled velocity file')
        raw = np.loadtxt(files[0]); distance, index = cKDTree(raw[:, :3]).query(points)
        if raw.shape != (len(points), 6) or not np.isfinite(raw).all() or max(distance) > 1e-6 or len(set(index)) != len(points):
            raise ValueError('CFD coordinate/field alignment failed')
        log = (self.output / 'log.sampling').read_text()
        qin = float(re.findall(r'sum\(inlet\) of phi = ([\d.eE+-]+)', log)[-1])
        qout = float(re.findall(r'sum\(outlet\) of phi = ([\d.eE+-]+)', log)[-1])
        imbalance = abs(qin + qout) / abs(qin)
        self.manifest['flux'] = dict(inlet_m3s=qin, outlet_m3s=qout, relative_imbalance=imbalance,
                                      declared_screen=1e-5)
        if imbalance > 1e-5:
            raise RuntimeError('Final flux imbalance exceeds the declared numerical screen')
        return np.linalg.norm(raw[index, 3:], axis=1)

    def gallery(self):
        """Write a local result gallery with lineage and status visible."""
        title = 'Fresh isothermal CFD' if self.spec.kind == 'fresh' else 'Experimental reconstruction'
        if self.spec.kind in ('archive', 'thermal'):
            title = 'ARCHIVED ' + ('unconverged thermal diagnostics' if self.spec.kind == 'thermal' else 'isothermal comparison')
        images = sorted(self.output.rglob('*.png'))
        page = '<!doctype html><meta charset="utf-8"><title>Jet bridge GUI results</title>'
        page += '<style>body{font:17px system-ui;max-width:1200px;margin:2rem auto}img{max-width:100%}</style>'
        if self.spec.kind in ('lab', 'lab_cfd'):
            title = 'Reconstruction Lab'
        page += '<h1>' + html.escape(title) + '</h1><p>' + html.escape(self.spec.run_id) + '</p>'
        if (self.output / 'reconstruction_lab.html').is_file():
            page += '<p><a href="reconstruction_lab.html">Open interactive Reconstruction Lab</a></p>'
        page += '<p>Physical validation remains unresolved. Mesh resolution is not proof of accuracy.</p>'
        for image in images:
            relative = image.relative_to(self.output).as_posix()
            page += f'<h2>{html.escape(image.stem)}</h2><img src="{html.escape(relative)}" alt="{html.escape(image.stem)}">'
        page += '<p><a href="manifest.json">Run manifest and numerical status</a></p>'
        (self.output / 'index.html').write_text(page, encoding='utf-8')
        self.manifest['figures'] = [p.relative_to(self.output).as_posix() for p in images]


def execute(root, output, spec):
    """Run one request in a fresh folder with explicit data lineage.

    Parameters
    ----------
    root, output : pathlib.Path
        Repository and new result destination.
    spec : RunSpec
        Supported experiment, run type, reconstruction and mesh selection.

    Returns
    -------
    dict
        Completed run manifest. Failure and cancellation also retain manifests.
    """
    import numpy as np
    import pandas as pd
    from jetbridge_ml.data_processing.faa import read_speed_average
    from jetbridge_ml.cfd_interface.plot_comparison import mesh_profile
    from .plots import reconstruction, mesh_plot, cfd_comparison
    spec.validate(root); output = validate_output(root, output, fresh_cfd=spec.kind == 'fresh')
    if spec.kind == 'fresh' and (os.name == 'nt' or not FOAM.is_file()):
        raise ValueError('Fresh CFD requires Linux/WSL and OpenCFD v2412')
    if spec.kind == 'fresh':
        validate_resources(spec.processes)
    output.mkdir(parents=True)
    job = Job(root, output, spec)
    originals = root / 'cfd/cases/empty_bridge_s01_a_10_hn_1'
    hashes = {str(p.relative_to(root)): sha256(p.read_bytes()).hexdigest()
              for folder in ('0', 'constant', 'system') for p in (originals / folder).rglob('*')
              if p.is_file() and 'polyMesh' not in p.parts}
    job.manifest['original_case_sha256'] = hashes
    try:
        print('Checking selected bundled input hashes...', flush=True)
        verified = verify_inputs(root, spec, job.cancel_file)
        job.manifest['verified_input_files'] = len(verified['files'])
        job.manifest['verified_inputs'] = verified
        job.check_cancel()
        if spec.kind == 'archive':
            tracker = ResidualRecorder(output / 'residual_history.csv','archived isothermal CFD')
            try:
                with (root / 'data/demo/cases_metadata/iso/log.simpleFoam').open() as source:
                    for line in source:tracker.feed(line)
            finally:tracker.close()
            job.manifest['residual_samples'] = tracker.count
        elif spec.kind == 'thermal':
            import csv
            records = read_history(root / 'data/demo/thermal_comparisons/thermal_residual_history.csv')
            with (output / 'residual_history.csv').open('w',newline='') as handle:
                writer=csv.DictWriter(handle,fieldnames=COLUMNS);writer.writeheader()
                for row in records:
                    row['source']='archived unconverged thermal CFD';writer.writerow(row)
            job.manifest['residual_samples']=len(records)
        dataset = root / 'data/demo/experimental'
        mesh = originals / 'system/blockMeshDict'
        if spec.kind in ('lab', 'lab_cfd'):
            from .lab import build_lab
            if spec.kind == 'lab_cfd':
                source_log = (root / 'data/demo/cases_metadata/iso/log.simpleFoam').read_text()
                if not re.search(r'SIMPLE solution converged in 237 iterations', source_log):
                    raise ValueError('Archived CFD convergence evidence is missing')
            job.manifest['reconstruction_lab'] = build_lab(root, output, spec, job.check_cancel)
        elif spec.kind == 'thermal':
            meta = root / 'data/demo/cases_metadata'
            job.manifest.update(numerical_status='archived NOT CONVERGED', interpolation='not applied',
                                training_reference_eligible=False)
            job.command('thermal_diagnostics', [sys.executable, '-m', 'jetbridge_ml.cfd_interface.plot_thermal',
                        '--case', str(meta / 'thermal'), '--control', str(meta / 'control'),
                        '--replay-inputs', str(root / 'data/demo/thermal_comparisons'),
                        '--output', str(output / 'thermal')])
        else:
            frame = read_speed_average(dataset / f'03-Averages/V-{spec.run_id}.txt')
            job.manifest['experimental_file_sha256'] = sha256((dataset / f'03-Averages/V-{spec.run_id}.txt').read_bytes()).hexdigest()
            job.manifest['sensor_count'] = len(frame)
            width, zs, floors, tops = mesh_profile(mesh)
            z = float(frame.z_m.iloc[0]); floor = float(np.interp(z, zs, floors))
            height = float(np.interp(z, zs, tops) - floor)
            xx, hh = np.meshgrid((np.arange(40)+.5)*width/40, (np.arange(60)+.5)*height/60)
            query = np.column_stack([xx.ravel(), hh.ravel() + floor])
            print('Reconstructing experimental plane and evaluating withheld sensors...', flush=True)
            fit = reconstruction(frame, query, spec.method, floor, output)
            job.manifest['experimental_reconstruction'] = fit
            job.check_cancel()
            if spec.kind == 'fresh':
                boundary = boundary_inputs(root, spec.run_id)
                job.manifest['boundary'] = boundary
                case = output / 'case'
                job.manifest['case_setup'] = prepare_case(root, case, frame, spec.mesh, boundary['flow_m3s'])
                mesh_plot(case / 'system/blockMeshDict', frame, spec.mesh, output)
                job.save()
                job.foam('blockMesh', ['blockMesh'], case)
                job.foam('checkMesh', ['checkMesh'], case)
                mesh_ok = 'Mesh OK' in (output / 'log.checkMesh').read_text()
                job.manifest['mesh_ok'] = mesh_ok
                if not mesh_ok:
                    raise RuntimeError('checkMesh failed; CFD comparison rejected')
                job.manifest['execution'] = dict(processes=spec.processes, available_cpus=available_cpus(),
                                                 decomposition='scotch' if spec.processes > 1 else None)
                if spec.processes > 1:
                    job.foam('mpi_version', ['mpirun', '--version'], case)
                    write_decomposition(case, spec.processes)
                    job.foam('decomposePar', ['decomposePar'], case)
                    job.foam('parallelCheckMesh', mpi_command(spec.processes, 'checkMesh'), case)
                    if 'Mesh OK' not in (output / 'log.parallelCheckMesh').read_text():
                        raise RuntimeError('Parallel checkMesh failed; comparison rejected')
                command = mpi_command(spec.processes, 'simpleFoam') if spec.processes > 1 else ['simpleFoam']
                job.foam('simpleFoam', command, case)
                match = re.search(r'SIMPLE solution converged in (\d+) iterations', (output / 'log.simpleFoam').read_text())
                if not match:
                    job.manifest['solver_converged'] = False
                    raise RuntimeError('Iteration cap reached without convergence; CFD comparison rejected')
                saved = match[1]
                if spec.processes > 1:
                    job.foam('reconstructPar', ['reconstructPar', '-time', saved], case)
                if not (case / saved / 'U').is_file():
                    raise RuntimeError('Converged saved field missing')
                job.manifest.update(solver_converged=True, saved_iteration=int(saved))
                points = np.vstack([frame[['x_m', 'y_m', 'z_m']].to_numpy(),
                                    np.column_stack([query, np.full(len(query), z)])])
                speed = job.sample(case, saved, points)
                cfd_comparison(frame, speed[:len(frame)], speed[len(frame):], query, floor, output, 'Fresh CFD')
                job.manifest['cfd_sensor_metrics'] = json.loads((output / 'cfd_metrics.json').read_text())
            elif spec.kind == 'archive':
                table = pd.read_csv(root / 'data/demo/reference/matched/matched_sensor_audit.csv')
                np.testing.assert_allclose(frame[['x_m','y_m','z_m']], table[['x_m','y_m','z_m']], atol=1e-10, rtol=0)
                np.testing.assert_allclose(frame.speed_mps, table.speed_mps, atol=1e-12, rtol=0)
                cfd_comparison(frame, table.cfd_cellPoint_speed_mps.to_numpy(), None, query, floor, output,
                               'ARCHIVED CFD, iteration 237')
                job.manifest.update(solver_converged='archived source only; no solver run',
                                    cfd_sensor_metrics=json.loads((output / 'cfd_metrics.json').read_text()))
        job.check_cancel()
        job.manifest['status'] = 'diagnostic_only' if spec.kind == 'thermal' else 'complete'
    except Cancelled as exc:
        job.manifest.update(status='cancelled', error=str(exc)); raise
    except Exception as exc:
        job.manifest.update(status='failed', error=str(exc)); raise
    finally:
        changed = [p for p,h in hashes.items() if sha256((root / p).read_bytes()).hexdigest() != h]
        job.manifest['original_case_unchanged'] = not changed
        if changed:
            job.manifest.update(status='failed', error='Original case changed during job')
        job.manifest['finished_utc'] = datetime.now(timezone.utc).isoformat()
        history = output / 'residual_history.csv'
        if history.is_file():
            try:
                from .plots import residual_plot
                label = ('Fresh CFD; converged' if job.manifest.get('solver_converged') is True
                         else 'Fresh CFD; incomplete or unconverged') if spec.kind == 'fresh' else 'ARCHIVED '+spec.kind+' history'
                residual_plot(history,output,label)
            except Exception as error:
                job.manifest.update(status='failed', residual_plot_error=str(error))
        job.gallery(); job.save()
        print('RESULT: ' + str(output / 'manifest.json'), flush=True)
    return job.manifest


def main():
    """Offer a CLI identical to the GUI job request for reproducibility."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--kind', default='experimental')
    parser.add_argument('--run-id', default='S01-A-10-HN-1')
    parser.add_argument('--method', default='rbf')
    parser.add_argument('--mesh', default='standard')
    parser.add_argument('--processes', type=int, default=1)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    if args.check:
        import numpy, scipy, pandas, sklearn, matplotlib  # noqa: F401
        if FOAM.is_file() and os.name != 'nt':
            shell = 'source ' + shlex.quote(str(FOAM)) + '; command -v blockMesh checkMesh simpleFoam'
            subprocess.run(['bash','-lc',shell],check=True)
        print(json.dumps(dict(python=sys.executable, openfoam=FOAM.is_file() and os.name != 'nt')))
        return
    if args.output is None:
        parser.error('--output is required for a job')
    try:
        execute(args.root.resolve(), args.output, RunSpec(args.kind,args.run_id,args.method,args.mesh,args.processes))
    except Cancelled:
        sys.exit(2)


if __name__ == '__main__':
    main()
