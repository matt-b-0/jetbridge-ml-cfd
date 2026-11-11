"""MPI execution helpers; no changes to the physical case definition."""
import os
from pathlib import Path


def available_cpus():
    """Return CPUs available to this worker, respecting Linux affinity.

    Returns
    -------
    int
        Number of available logical CPUs.
    """
    return len(os.sched_getaffinity(0)) if hasattr(os, 'sched_getaffinity') else (os.cpu_count() or 1)


def validate_resources(processes):
    """Reject oversubscription before creating an OpenFOAM case.

    Parameters
    ----------
    processes : int
        Validated requested process count.

    Raises
    ------
    ValueError
        If the request exceeds the worker CPU allocation.
    """
    if processes > available_cpus():
        raise ValueError(f'Requested {processes} processes; only {available_cpus()} CPUs available')


def mpi_command(processes, application):
    """Build literal Open MPI arguments without oversubscribing the host.

    Parameters
    ----------
    processes : int
        Number of MPI ranks.
    application : str
        OpenFOAM executable name.

    Returns
    -------
    list of str
        Argument vector for the MPI launcher.
    """
    return ['mpirun', '--use-hwthread-cpus', '--bind-to', 'none', '-np', str(processes), application, '-parallel']


def write_decomposition(case, processes):
    """Write Scotch decomposition settings into a newly prepared case only.

    Parameters
    ----------
    case : pathlib.Path
        Fresh copied OpenFOAM case, never an original input case.
    processes : int
        Number of mesh partitions, matching MPI ranks.
    """
    target = Path(case) / 'system/decomposeParDict'
    target.write_text('FoamFile\n{\n version 2.0;\n format ascii;\n class dictionary;\n object decomposeParDict;\n}\n'
                      f'numberOfSubdomains {processes};\nmethod scotch;\ndistributed no;\nroots ();\n')
