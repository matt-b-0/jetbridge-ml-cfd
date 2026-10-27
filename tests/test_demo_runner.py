"""Demo isolation, provenance and archive validation regression tests."""
import importlib.util
import json
from hashlib import sha256
from pathlib import Path
import subprocess
import sys
import numpy as np
import pandas as pd
import pytest
from jetbridge_ml.cfd_interface.report_figures import read_archived_grid

spec=importlib.util.spec_from_file_location('demo_runner',Path(__file__).resolve().parents[1]/'run_all.py')
runner=importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


def test_bundle_hash_and_escape_checks(tmp_path):
    value=tmp_path/'data.csv';value.write_text('measured\n')
    manifest=tmp_path/'manifest.json'
    record=dict(path='data.csv',sha256=sha256(value.read_bytes()).hexdigest())
    manifest.write_text(json.dumps(dict(files=[record])))
    assert runner.verify_bundle(tmp_path)==1
    value.write_text('changed\n')
    with pytest.raises(ValueError,match='missing or changed'):runner.verify_bundle(tmp_path)
    record['path']='../outside.csv';manifest.write_text(json.dumps(dict(files=[record])))
    with pytest.raises(ValueError,match='escapes'):runner.verify_bundle(tmp_path)


def test_no_output_overwrite_or_source_write(tmp_path):
    with pytest.raises(ValueError,match='exists'):runner.validate_destination(tmp_path)
    with pytest.raises(ValueError,match='cannot be inside'):
        runner.validate_destination(runner.ROOT/'data/demo/new-output')


def test_failed_stage_is_recorded_and_logs_preserved(tmp_path):
    demo=runner.Demo(tmp_path,'replay')
    with pytest.raises(subprocess.CalledProcessError):
        demo.command('intentional_failure',[sys.executable,'-c','print("diagnostic"); raise SystemExit(7)'])
    assert demo.records[-1]['status']=='failed'
    assert 'diagnostic' in (tmp_path/'log.intentional_failure').read_text()


def test_archived_field_requires_matching_finite_coordinates(tmp_path):
    points=np.array([[0.,0.,1.],[1.,0.,1.]])
    frame=pd.DataFrame(points,columns=['x_m','y_m','z_m'])
    frame[['Ux_mps','Uy_mps','Uz_mps']]=0.
    target=tmp_path/'samples.csv';frame.to_csv(target,index=False)
    assert read_archived_grid(target,points,False)['U'].shape==(2,3)
    with pytest.raises(AssertionError):read_archived_grid(target,points+1,False)
    frame.loc[0,'Ux_mps']=np.nan;frame.to_csv(target,index=False)
    with pytest.raises(ValueError,match='nonfinite'):read_archived_grid(target,points,False)


def test_yplus_does_not_replace_solver_convergence_evidence(tmp_path):
    case=tmp_path/'case';case.mkdir()
    original=case/'log.simpleFoam';original.write_text('SIMPLE solution converged in 237 iterations')
    demo=runner.Demo(tmp_path,'live')
    commands=[]
    def fake(name,command,**kwargs):
        commands.append(command)
        (tmp_path/f'log.{name}').write_text('yPlus diagnostic')
    demo.command=fake
    demo.foam('yPlus',['simpleFoam','-postProcess','-func','yPlus'],case)
    assert 'converged' in original.read_text()
    assert (case/'log.yPlus').read_text()=='yPlus diagnostic'
    shell=commands[0][-1]
    assert shell.index('source ')<shell.index('set -e')


def test_included_research_inputs_survive_a_git_checkout():
    assert runner.verify_bundle(runner.BUNDLE)>2000


def test_plan_is_safe_without_creating_an_output(tmp_path):
    output=tmp_path/'not-created'
    result=subprocess.run([sys.executable,str(runner.ROOT/'run_all.py'),'--profile','full','--output',str(output),'--plan'],capture_output=True,text=True,check=True)
    assert json.loads(result.stdout)['fresh_mesh_study'] is True
    assert not output.exists()
