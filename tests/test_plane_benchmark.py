"""Independent numerical and leakage checks using synthetic source fixtures."""
import numpy as np
import pandas as pd
import pytest

from jetbridge_ml.data_processing.faa import read_speed_average
from jetbridge_ml.interpolation.plane import predict_plane
from jetbridge_ml.validation.spatial import leave_location_out
from jetbridge_ml.benchmark import evaluate_plane, summarize


def make_source(tmp_path, mean="1 2 -9999 4"):
    path = tmp_path / "V-S01-A-10-HN-1.txt"
    path.write_text(
        'TITLE="synthetic"\nVARIABLES="X (m)", "Y (m)", "Z (m)", "Mean", "dMean", "Median", "dMedian", "StdDev"\n'
        'ZONE I=2, J=2, K=1 F=BLOCK\n'
        '0 0 1 1\n0 1 0 1\n3.05 3.05 3.05 3.05\n'
        + mean + '\n' + '0 0 0 0\n' * 4)
    return path


def test_parser_units_metadata_and_missing(tmp_path):
    frame = read_speed_average(make_source(tmp_path))
    assert frame.y_m.tolist() == [0, 1, 0, 1]  # No second floor offset.
    assert frame.z_m.tolist() == [3.05] * 4
    assert frame.run_id.unique().tolist() == ["S01-A-10-HN-1"]
    assert frame.station_ft.unique().tolist() == [10]
    assert np.isnan(frame.speed_mps.iloc[2])


def test_parser_rejects_wrong_units_and_truncation(tmp_path):
    path = make_source(tmp_path)
    text = path.read_text()
    path.write_text(text.replace("X (m)", "X (in)"))
    with pytest.raises(ValueError, match="units"):
        read_speed_average(path)
    path.write_text(text.rsplit("0", 1)[0])
    with pytest.raises(ValueError, match="length"):
        read_speed_average(path)


@pytest.mark.parametrize("method", ["linear", "rbf"])
def test_affine_field_reproduction(method):
    x = np.array([[0, 0], [1, 0], [0, 1], [1, 1], [.5, .5]])
    q = np.array([[.2, .3], [.6, .8]])
    result = predict_plane(method, x, 2 + 3*x[:, 0] - x[:, 1], q)
    np.testing.assert_allclose(result, 2 + 3*q[:, 0] - q[:, 1], atol=1e-12)


def test_linear_extrapolation_is_explicit():
    x = np.array([[0, 0], [1, 0], [0, 1]])
    result = predict_plane("linear", x, [1, 1, 1], [[.2, .2], [2, 2]])
    assert result[0] == pytest.approx(1)
    assert np.isnan(result[1])


def test_repeated_locations_never_cross_split():
    x = np.array([[0, 0], [0, 0], [1, 0], [1, 0], [0, 1]])
    folds = list(leave_location_out(x))
    assert len(folds) == 3
    for train, test in folds:
        assert not set(map(tuple, x[train])) & set(map(tuple, x[test]))
    assert sorted(np.concatenate([test for _, test in folds])) == list(range(5))


def test_benchmark_same_folds_and_common_coverage():
    x = np.repeat([0., 1.], 6)
    y = np.tile(np.arange(6.), 2)
    frame = pd.DataFrame(dict(x_m=x, y_m=y, z_m=3., speed_mps=.1 + .01*y,
                              run_id="synthetic", source_row=np.arange(12)))
    first = evaluate_plane(frame)
    second = evaluate_plane(frame)
    pd.testing.assert_frame_equal(first.drop(columns="seconds"), second.drop(columns="seconds"))
    for _, fold in first.groupby("fold"):
        assert fold.source_row.nunique() == 1
        assert fold.train_rows.nunique() == 1
        assert str(fold.source_row.iloc[0]) not in fold.train_rows.iloc[0].split(";")
    metrics = summarize(first)
    common = metrics[metrics.subset == "common_hull"]
    assert common.n_predicted.tolist() == [8, 8, 8]
    assert common.coverage.tolist() == [1, 1, 1]
    outside_linear = metrics[(metrics.method == "linear") & (metrics.subset == "outside_hull")]
    assert outside_linear.n_predicted.iloc[0] == 0
    assert np.isnan(outside_linear.rmse.iloc[0])


def test_unseen_target_values_cannot_affect_predictions():
    frame = pd.DataFrame(dict(x_m=np.repeat([0., 1.], 6),
                              y_m=np.tile(np.arange(6.), 2), z_m=3.,
                              speed_mps=np.arange(12.) / 100,
                              run_id="synthetic", source_row=np.arange(12)))
    baseline = evaluate_plane(frame)
    changed = frame.copy()
    changed.loc[3, "speed_mps"] = 1000
    altered = evaluate_plane(changed)
    a = baseline[baseline.source_row == 3].prediction_mps
    b = altered[altered.source_row == 3].prediction_mps
    np.testing.assert_allclose(a, b)
