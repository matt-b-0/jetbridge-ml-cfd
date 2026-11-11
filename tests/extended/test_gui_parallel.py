"""MPI requests must remain explicit and within available hardware."""
import pytest
from jetbridge_ml.gui.config import RunSpec, worker_arguments
from jetbridge_ml.gui import parallel


@pytest.mark.parametrize('count', [0, -1, 33, True, 1.5])
def test_invalid_process_count(count):
    with pytest.raises(ValueError, match='integer'):
        RunSpec(processes=count).validate('.')


def test_archived_requests_cannot_claim_mpi():
    with pytest.raises(ValueError, match='fresh'):
        RunSpec(kind='archive', processes=2).validate('.')


def test_cpu_limit(monkeypatch):
    monkeypatch.setattr(parallel, 'available_cpus', lambda: 4)
    parallel.validate_resources(4)
    with pytest.raises(ValueError, match='only 4'):
        parallel.validate_resources(8)


def test_decomposition_and_literal_arguments(tmp_path):
    (tmp_path / 'system').mkdir()
    parallel.write_decomposition(tmp_path, 4)
    text = (tmp_path / 'system/decomposeParDict').read_text()
    assert 'numberOfSubdomains 4;' in text
    assert 'method scotch;' in text
    command = parallel.mpi_command(4, 'simpleFoam')
    assert command[-2:] == ['simpleFoam', '-parallel']
    assert '--oversubscribe' not in command
    assert worker_arguments(tmp_path, tmp_path/'out', RunSpec(kind='fresh', processes=4))[-2:] == ['--processes', '4']


@pytest.mark.skipif(__import__('os').name == 'nt' or not __import__('shutil').which('mpirun'),
                    reason='Requires Linux Open MPI runtime')
def test_cancellation_stops_mpi_ranks(tmp_path):
    import os
    import sys
    import threading
    import time
    from pathlib import Path
    from jetbridge_ml.gui.workflow import Job, Cancelled
    root = Path(__file__).resolve().parents[2]
    output = tmp_path/'job'
    output.mkdir()
    job = Job(root, output, RunSpec(kind='fresh', processes=2))
    script = tmp_path/'rank.py'
    script.write_text("import os,time,pathlib; pathlib.Path(" + repr(str(tmp_path)) +
                      ", 'rank-' + os.environ['OMPI_COMM_WORLD_RANK']).write_text(str(os.getpid())); time.sleep(30)")
    def cancel_when_started():
        for _ in range(100):
            if len(list(tmp_path.glob('rank-*'))) == 2:
                break
            time.sleep(.05)
        job.cancel_file.write_text('cancel')
    thread = threading.Thread(target=cancel_when_started)
    thread.start()
    try:
        with pytest.raises(Cancelled):
            job.command('mpi_cancel', ['mpirun', '--bind-to', 'none', '-np', '2', sys.executable, str(script)])
    finally:
        thread.join()
    ranks = list(tmp_path.glob('rank-*'))
    assert len(ranks) == 2
    for record in ranks:
        pid = int(record.read_text())
        status = Path(f'/proc/{pid}/stat')
        assert not status.exists() or status.read_text().split()[2] == 'Z'
