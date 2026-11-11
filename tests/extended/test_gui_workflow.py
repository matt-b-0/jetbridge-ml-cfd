"""Scientific request, isolation and cancellation checks for the GUI workflow."""
from dataclasses import replace
from hashlib import sha256
from pathlib import Path
import re
import os
import sys
import threading
import time
import numpy as np
import pytest
from jetbridge_ml.gui.config import RunSpec, available_runs, cell_count, validate_output, windows_to_wsl, worker_arguments
from jetbridge_ml.gui.workflow import Job, Cancelled, boundary_inputs, prepare_case
from jetbridge_ml.data_processing.faa import read_speed_average

ROOT=Path(__file__).resolve().parents[2]


def test_resolution_labels_have_exact_counts():
    assert [cell_count(m) for m in ('coarse','standard','fine')]==[17664,141312,476928]


def test_only_single_window_experiments_can_launch_fresh_cfd():
    assert len(available_runs(ROOT,'experimental'))==36
    assert len(available_runs(ROOT,'fresh'))==30
    with pytest.raises(ValueError):RunSpec('fresh','S01-A-58-HN-1').validate(ROOT)
    with pytest.raises(ValueError):RunSpec(run_id='../../case').validate(ROOT)


def test_archived_mesh_and_case_cannot_be_silently_changed():
    with pytest.raises(ValueError):RunSpec('archive','S01-A-16-HN-1').validate(ROOT)
    with pytest.raises(ValueError):RunSpec('archive',mesh='fine').validate(ROOT)
    with pytest.raises(ValueError):RunSpec('thermal','S01-AC-10-HN-1',method='svr').validate(ROOT)


@pytest.mark.parametrize('folder',['src','data','cfd','docs','.git','tests'])
def test_original_inputs_cannot_be_output(folder):
    with pytest.raises(ValueError):validate_output(ROOT,ROOT/folder/'new_gui_job')


def test_existing_output_and_parent_of_repository_are_rejected(tmp_path):
    with pytest.raises(ValueError):validate_output(ROOT,tmp_path)
    with pytest.raises(ValueError):validate_output(ROOT,ROOT.parent)


def test_wsl_paths_remain_literal_arguments():
    path=r'C:\Users\Student Name\Project'
    converted=windows_to_wsl(path)
    assert converted=='/mnt/c/Users/Student Name/Project'
    args=worker_arguments(converted,'/tmp/my job',RunSpec())
    assert args[1]==converted and args[3]=='/tmp/my job'
    with pytest.raises(ValueError):windows_to_wsl(r'\\server\project')


def test_hvac_uses_recorded_window_and_litres_conversion():
    boundary=boundary_inputs(ROOT,'S01-A-10-HN-1')
    assert boundary['valid_hvac_readings']==58
    assert boundary['flow_m3s']==pytest.approx(.5338655172413794)
    assert boundary['windows_equal']


@pytest.mark.parametrize('mesh',['coarse','standard','fine'])
def test_prepared_case_updates_flow_turbulence_and_selected_probes(tmp_path,mesh):
    source=ROOT/'cfd/cases/empty_bridge_s01_a_10_hn_1'
    files=[p for folder in ('0','constant','system') for p in (source/folder).rglob('*') if p.is_file()]
    before={p:sha256(p.read_bytes()).hexdigest() for p in files}
    frame=read_speed_average(ROOT/'data/demo/experimental/03-Averages/V-S01-A-16-HN-1.txt')
    case=tmp_path/'case';q=.4
    setup=prepare_case(ROOT,case,frame,mesh,q)
    assert setup['cells']==cell_count(mesh)
    text=(case/'0/U').read_text()
    assert float(re.search(r'volumetricFlowRate constant ([\d.eE+-]+)',text)[1])==q
    initial=float(re.search(r'internalField uniform \(0 0 ([\d.eE+-]+)\)',text)[1])
    assert initial==pytest.approx(-q/(1.388618*2.441448))
    k=float(re.search(r'internalField uniform ([\d.eE+-]+)',(case/'0/k').read_text())[1])
    assert k==pytest.approx(1.5*(.05*abs(initial))**2)
    probes=re.search(r'probeLocations\s*\((.*?)\);',(case/'system/controlDict').read_text(),re.S)[1]
    assert len(re.findall(r'\([^()]*\)',probes))==len(frame)
    for row in frame.itertuples():assert f'{row.z_m:.12g}' in probes
    assert all(sha256(p.read_bytes()).hexdigest()==digest for p,digest in before.items())


@pytest.mark.skipif(os.name == 'nt', reason='Scientific worker uses Linux process groups; Windows frontend uses WSL')
def test_cancellation_stops_a_silent_child_process_group(tmp_path):
    output=tmp_path/'job';output.mkdir()
    job=Job(ROOT,output,RunSpec())
    timer=threading.Timer(.3,lambda:job.cancel_file.write_text('cancel'))
    start=time.monotonic();timer.start()
    try:
        with pytest.raises(Cancelled):
            job.command('silent',[sys.executable,'-c','import time;time.sleep(30)'])
    finally:timer.cancel()
    assert time.monotonic()-start<5
    assert job.manifest['stages'][0]['status']=='cancelled'



def test_selected_hash_check_rejects_tampering_without_reading_unrelated_inputs(tmp_path):
    import json
    from jetbridge_ml.gui.workflow import verify_inputs
    bundle=tmp_path/'data/demo'
    paths=['experimental/Data Dictionary.csv','experimental/03-Averages/V-S01-A-10-HN-1.txt','unused.csv']
    records=[]
    for name in paths:
        path=bundle/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(b'original')
        records.append(dict(path=name,sha256=sha256(b'original').hexdigest()))
    (bundle/'manifest.json').write_text(json.dumps(dict(files=records)))
    (bundle/'unused.csv').write_bytes(b'not used in this job')
    result=verify_inputs(tmp_path,RunSpec())
    assert len(result['files'])==2
    (bundle/paths[1]).write_bytes(b'changed target')
    with pytest.raises(ValueError,match='Changed bundled input'):verify_inputs(tmp_path,RunSpec())


def test_hash_check_can_be_cancelled_before_file_io(tmp_path):
    import json
    from jetbridge_ml.gui.workflow import verify_inputs
    bundle=tmp_path/'data/demo';bundle.mkdir(parents=True)
    paths=['experimental/Data Dictionary.csv','experimental/03-Averages/V-S01-A-10-HN-1.txt']
    (bundle/'manifest.json').write_text(json.dumps(dict(files=[dict(path=p,sha256='irrelevant') for p in paths])))
    cancel=tmp_path/'cancel';cancel.touch()
    with pytest.raises(Cancelled):verify_inputs(tmp_path,RunSpec(),cancel)
