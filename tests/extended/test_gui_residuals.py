"""Residual parsing and interpretation must not imply physical validation."""
from pathlib import Path
import csv
import pytest
from jetbridge_ml.gui.residuals import ResidualRecorder, read_history
from jetbridge_ml.gui.guidance import validation_message, guide_text


def test_records_first_initial_residual_and_preserves_final_and_zero(tmp_path):
    path=tmp_path/'history.csv';tracker=ResidualRecorder(path)
    tracker.feed('smoothSolver: Solving for Uz, Initial residual = 0.9, Final residual = 1e-7, No Iterations 2')
    tracker.feed('Time = 1\n')
    tracker.feed('GAMG: Solving for p, Initial residual = 0.03, Final residual = 2e-8, No Iterations 3')
    tracker.feed('GAMG: Solving for p, Initial residual = 0.004, Final residual = 1e-9, No Iterations 2')
    tracker.feed('smoothSolver: Solving for Ux, Initial residual = 0, Final residual = 0, No Iterations 0')
    tracker.feed('Time = 2\n')
    tracker.feed('GAMG: Solving for p, Initial residual = 0.001, Final residual = 1e-10, No Iterations 1')
    tracker.close()
    with path.open() as handle:rows=list(csv.DictReader(handle))
    assert len(rows)==3
    assert float(rows[0]['initial_residual'])==.03
    assert float(rows[0]['final_residual'])==2e-8
    assert rows[1]['field']=='Ux' and float(rows[1]['initial_residual'])==0
    assert float(rows[2]['iteration'])==2


def test_stream_reader_ignores_partial_nonfinite_and_invalid_rows(tmp_path):
    path=tmp_path/'history.csv'
    path.write_text('iteration,field,initial_residual,source\n1,p,0.1,fresh\n2,p,nan,fresh\n3,p,-1,fresh\n4,p,')
    rows=read_history(path)
    assert len(rows)==1 and rows[0]['initial_residual']==.1
    assert read_history(tmp_path/'not-yet-created.csv')==[]


def test_archived_residual_column_can_be_read_without_inventing_final_values(tmp_path):
    path=tmp_path/'thermal.csv';path.write_text('iteration,field,residual\n10,T,0.025\n')
    assert read_history(path)==[dict(iteration=10.,field='T',initial_residual=.025,source='saved history')]


@pytest.mark.parametrize('kind',['fresh','archive'])
def test_even_zero_comparison_error_does_not_certify_physical_accuracy(kind):
    text=validation_message(kind,{'cfd_sensor_metrics':{'rmse':0.,'bias':0.},'solver_converged':True})
    assert 'incomplete' in text and 'comparison' in text.lower()


def test_experimental_and_thermal_modes_have_distinct_evidence_messages():
    assert 'not assessed' in validation_message('experimental')
    assert 'unconverged' in validation_message('thermal')
    text=guide_text('fresh','S01-A-10-HN-1','RBF','Standard')
    assert 'first reported initial residual' in text
    assert 'measurement uncertainty' in text
    assert 'not physical seconds' in text


def test_fresh_case_paths_reject_spaces_but_archived_outputs_allow_them(tmp_path):
    from jetbridge_ml.gui.config import validate_output
    root=tmp_path/'repo';root.mkdir()
    output=tmp_path/'folder with spaces'/'new_run'
    with pytest.raises(ValueError,match='cannot contain spaces'):
        validate_output(root,output,fresh_cfd=True)
    assert validate_output(root,output)==output.resolve()
