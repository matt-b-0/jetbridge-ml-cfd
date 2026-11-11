"""Dependency-free configuration and input validation for the desktop GUI."""
from dataclasses import dataclass
import ntpath
from pathlib import Path
import re

KINDS = {'lab': 'Reconstruction Lab  -  experimental comparison',
         'lab_cfd': 'Reconstruction Lab  -  archived CFD virtual sensors',
         'experimental': 'Experimental reconstruction',
         'fresh': 'Fresh isothermal CFD + reconstruction',
         'archive': 'Archived isothermal comparison',
         'thermal': 'Archived thermal diagnostics (NOT CONVERGED)'}
METHODS = {'rbf': 'Thin-plate RBF', 'linear': 'Linear interpolation',
           'nearest': 'Nearest neighbour', 'svr': 'Support vector regression'}
MESHES = {'coarse': (12, 16, 42, 9, 41),
          'standard': (24, 32, 84, 18, 82),
          'fine': (36, 48, 126, 27, 123)}
BASELINE = 'S01-A-10-HN-1'
THERMAL = 'S01-AC-10-HN-1'


def cell_count(mesh):
    """Return the exact cell count behind a qualitative resolution label."""
    nx, ny, *nz = MESHES[mesh]
    return nx * ny * sum(nz)


def available_runs(root, kind):
    """List only supported bundled experiments for the requested workflow."""
    root = Path(root)
    if kind == 'lab_cfd':
        return ['S01-A-16-HN-1']
    if kind in ('archive', 'thermal'):
        return [THERMAL if kind == 'thermal' else BASELINE]
    result = []
    for p in (root / 'data/demo/experimental/03-Averages').glob('V-S01-A-*-HN-*.txt'):
        run = p.stem[2:]
        if re.fullmatch(r'S01-A-\d+-HN-\d+', run):
            # A/B acquisition at 58 ft has no single matched CFD inlet.
            if kind != 'fresh' or int(run.split('-')[2]) != 58:
                result.append(run)
    return sorted(result, key=lambda s: (int(s.split('-')[2]), int(s.split('-')[-1])))


@dataclass(frozen=True)
class RunSpec:
    """Store an explicit scientific request, separate from runtime configuration."""
    kind: str = 'experimental'
    run_id: str = BASELINE
    method: str = 'rbf'
    mesh: str = 'standard'
    processes: int = 1

    def validate(self, root):
        """Reject unsupported combinations rather than silently ignoring controls."""
        if type(self.processes) is not int or not 1 <= self.processes <= 32:
            raise ValueError('Solver processes must be an integer from 1 to 32')
        if self.kind != 'fresh' and self.processes != 1:
            raise ValueError('MPI applies only to fresh CFD runs')
        if self.kind not in KINDS or self.method not in METHODS or self.mesh not in MESHES:
            raise ValueError('Unknown workflow, method or mesh resolution')
        if self.run_id not in available_runs(root, self.kind):
            raise ValueError('This experiment is not supported by the selected workflow')
        if self.kind != 'fresh' and self.mesh != 'standard':
            raise ValueError('Mesh selection applies only to fresh CFD; use standard elsewhere')
        if self.kind in ('lab', 'lab_cfd') and self.method != 'rbf':
            raise ValueError('Reconstruction Lab compares all methods; use the rbf placeholder')
        if self.kind == 'thermal' and self.method != 'rbf':
            raise ValueError('Thermal diagnostics do not fit interpolation or ML models')
        return self


def validate_output(root, output, *, fresh_cfd=False):
    """Require a fresh destination outside original inputs and source folders."""
    root, output = Path(root).resolve(), Path(output).resolve()
    if fresh_cfd and any(char.isspace() for char in str(output)):
        raise ValueError('OpenFOAM case paths cannot contain spaces. Choose an output folder without spaces for fresh CFD.')
    if output.exists():
        raise ValueError('Output already exists; every job must have a new folder')
    if root == output or root.is_relative_to(output):
        raise ValueError('Output cannot contain the repository')
    for folder in ('src', 'tests', 'data', 'cfd', 'docs', '.git'):
        if output.is_relative_to(root / folder):
            raise ValueError(f'Output cannot be inside {folder}')
    return output


def windows_to_wsl(value):
    """Convert a drive-qualified local path using WSL's standard /mnt mount."""
    drive, tail = ntpath.splitdrive(str(value))
    if not re.fullmatch('[A-Za-z]:', drive):
        raise ValueError('Choose a local drive path, not a UNC/network destination')
    return '/mnt/' + drive[0].lower() + tail.replace('\\', '/')


def worker_arguments(root, output, spec):
    """Build literal subprocess arguments without shell interpolation."""
    return ['--root', str(root), '--output', str(output), '--kind', spec.kind,
            '--run-id', spec.run_id, '--method', spec.method, '--mesh', spec.mesh, '--processes', str(spec.processes)]
