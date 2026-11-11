# Tests explained line by line

These are the same actual source lines as the offline HTML walkthrough. Read each test as controlled inputs, production call, expected answer and assertion.

## tests/test_presentation_examples.py

[Open actual source](../../tests/test_presentation_examples.py).

| Line | Actual code | Explanation |
| --- | --- | --- |
| 1 | `"""Small independent checks that are practical to explain in a demonstration.` | Documentation states the property being tested; it is not an assertion or a numerical operation. |
| 2 | `(blank)` | Blank line separates logical steps; it has no computational effect. |
| 3 | `These extend the existing affine-field, support and nested-leakage tests.` | Continuation of the module documentation describing the scope and limits of these checks. |
| 4 | `They check numerical properties, not the physical validity of jet-bridge CFD.` | Continuation of the module documentation describing the scope and limits of these checks. |
| 5 | `"""` | Documentation states the property being tested; it is not an assertion or a numerical operation. |
| 6 | `(blank)` | Blank line separates logical steps; it has no computational effect. |
| 7 | `import numpy as np` | Import NumPy for numerical arrays and independent array comparisons. |
| 8 | `import pytest` | Import pytest for approximate scalar comparisons, expected exceptions and parametrised cases. |
| 9 | `(blank)` | Blank line separates logical steps; it has no computational effect. |
| 10 | `from jetbridge_ml.interpolation.plane import predict_plane` | Import the production function or supporting library named here; this is the implementation the test exercises. |
| 11 | `from jetbridge_ml.validation.metrics import regression_metrics` | Import the production function or supporting library named here; this is the implementation the test exercises. |
| 12 | `(blank)` | Blank line separates logical steps; it has no computational effect. |
| 13 | `(blank)` | Blank line separates logical steps; it has no computational effect. |
| 14 | `def test_zero_bias_can_hide_large_local_errors():` | Define the test: zero bias can hide large local errors. pytest discovers names starting with test_. |
| 15 | `    """Opposite signed errors cancel in bias, but not in MAE or RMSE."""` | Documentation states the property being tested; it is not an assertion or a numerical operation. |
| 16 | `    actual = np.array([0.1, 0.3])` | Define two known reference speeds in m/s. These are synthetic test values, not FAA observations. |
| 17 | `    predicted = np.array([0.3, 0.1])` | Reverse the values: prediction minus reference becomes +0.2 and -0.2 m/s. |
| 18 | `    metrics = regression_metrics(actual, predicted)` | Call the actual production metric function with the two arrays. |
| 19 | `    assert metrics["bias"] == pytest.approx(0.0, abs=1e-12)` | The average signed error is zero. Allow an absolute 1e-12 rounding difference near zero. |
| 20 | `    assert metrics["mae"] == pytest.approx(0.2)` | The mean of the absolute errors is (0.2 + 0.2)/2 = 0.2 m/s. |
| 21 | `    assert metrics["rmse"] == pytest.approx(0.2)` | The square root of the mean squared error is sqrt((0.04 + 0.04)/2) = 0.2 m/s. |
| 22 | `(blank)` | Blank line separates logical steps; it has no computational effect. |
| 23 | `(blank)` | Blank line separates logical steps; it has no computational effect. |
| 24 | `@pytest.mark.parametrize("method", ["nearest", "linear", "rbf"])` | Run the following function three times, once for each conventional method. Each case counts separately. |
| 25 | `def test_sensor_row_order_does_not_change_predictions(method):` | Define the test: sensor row order does not change predictions. pytest discovers names starting with test_. |
| 26 | `    """Reordering paired coordinates and values must preserve predictions."""` | Documentation states the property being tested; it is not an assertion or a numerical operation. |
| 27 | `    sensors = np.array([[0.0, 0.0], [1.0, 0.0], [0.0, 1.0], [1.0, 1.0]])` | Use four corner sensors on a unit square in a planar coordinate system. |
| 28 | `    speeds = np.array([0.1, 0.2, 0.3, 0.4])` | Attach one scalar speed to each coordinate, keeping coordinate/value pairs aligned. |
| 29 | `    queries = np.array([[0.12, 0.18], [0.83, 0.74]])` | Choose two interior query points. Neither has a nearest-neighbour distance tie. |
| 30 | `    order = np.array([2, 0, 3, 1])` | Specify a different sensor row order without altering the physical data. |
| 31 | `    original = predict_plane(method, sensors, speeds, queries)` | Calculate predictions with the original row ordering. |
| 32 | `    reordered = predict_plane(method, sensors[order], speeds[order], queries)` | Apply the same permutation to coordinates and speeds, then predict at unchanged queries. |
| 33 | `    np.testing.assert_allclose(original, reordered, rtol=0.0, atol=1e-12)` | Require predictions to agree within absolute numerical tolerance; CSV row ordering should not change this case. |
| 34 | `(blank)` | Blank line separates logical steps; it has no computational effect. |
| 35 | `(blank)` | Blank line separates logical steps; it has no computational effect. |
| 36 | `def test_error_metrics_keep_speed_units_when_scaled():` | Define the test: error metrics keep speed units when scaled. pytest discovers names starting with test_. |
| 37 | `    """Changing m/s to cm/s multiplies every error metric by one hundred."""` | Documentation states the property being tested; it is not an assertion or a numerical operation. |
| 38 | `    actual = np.array([0.1, 0.2, 0.3])` | Set three reference speeds for a unit-consistency check. |
| 39 | `    predicted = np.array([0.12, 0.18, 0.34])` | Set known predictions with nonzero errors and positive aggregate bias. |
| 40 | `    metres = regression_metrics(actual, predicted)` | Calculate the errors using speeds expressed in m/s. |
| 41 | `    centimetres = regression_metrics(100.0 * actual, 100.0 * predicted)` | Convert both arrays to cm/s and calculate metrics again. |
| 42 | `    for name in ("rmse", "mae", "bias"):` | Check each of the three metrics independently. |
| 43 | `        assert centimetres[name] == pytest.approx(100.0 * metres[name])` | Verify linear unit scaling: each speed-error metric has speed units, rather than squared-speed units. |
| 44 | `(blank)` | Blank line separates logical steps; it has no computational effect. |
| 45 | `(blank)` | Blank line separates logical steps; it has no computational effect. |
| 46 | `def test_unsupported_predictions_are_not_silently_scored():` | Define the test: unsupported predictions are not silently scored. pytest discovers names starting with test_. |
| 47 | `    """A missing prediction requires an explicit coverage decision."""` | Documentation states the property being tested; it is not an assertion or a numerical operation. |
| 48 | `    with pytest.raises(ValueError, match="finite"):` | Expect the production function to reject a non-finite prediction with a relevant error message. |
| 49 | `        regression_metrics([0.1, 0.2], [0.1, np.nan])` | Supply one missing prediction. The caller must explicitly choose supported targets before scoring. |

## tests/test_plane_benchmark.py

[Open actual source](../../tests/test_plane_benchmark.py).

| Line | Actual code | Explanation |
| --- | --- | --- |
| 2 | `import numpy as np` | Import NumPy for numerical arrays and independent array comparisons. |
| 3 | `import pandas as pd` | Import pandas to construct synthetic input tables in the same format as the real workflow. |
| 4 | `import pytest` | Import pytest for approximate scalar comparisons, expected exceptions and parametrised cases. |
| 6 | `from jetbridge_ml.data_processing.faa import read_speed_average` | Import the production function or supporting library named here; this is the implementation the test exercises. |
| 7 | `from jetbridge_ml.interpolation.plane import predict_plane` | Import the production function or supporting library named here; this is the implementation the test exercises. |
| 8 | `from jetbridge_ml.validation.spatial import leave_location_out` | Import the production function or supporting library named here; this is the implementation the test exercises. |
| 9 | `from jetbridge_ml.benchmark import evaluate_plane, summarize` | Import the production function or supporting library named here; this is the implementation the test exercises. |
| 42 | `@pytest.mark.parametrize("method", ["linear", "rbf"])` | Exercise both interpolators that should reproduce the specified affine field. |
| 43 | `def test_affine_field_reproduction(method):` | Define the test: affine field reproduction. pytest discovers names starting with test_. |
| 44 | `    x = np.array([[0, 0], [1, 0], [0, 1], [1, 1], [.5, .5]])` | Define four square corners and one interior training coordinate. |
| 45 | `    q = np.array([[.2, .3], [.6, .8]])` | Choose two interior points that are not training sensors. |
| 46 | `    result = predict_plane(method, x, 2 + 3*x[:, 0] - x[:, 1], q)` | Fit using values from the known affine formula f(x,y)=2+3x-y and predict the query points. |
| 47 | `    np.testing.assert_allclose(result, 2 + 3*q[:, 0] - q[:, 1], atol=1e-12)` | Compare with the formula evaluated independently at the queries. This verifies an exact-property benchmark. |
| 50 | `def test_linear_extrapolation_is_explicit():` | Define the test: linear extrapolation is explicit. pytest discovers names starting with test_. |
| 51 | `    x = np.array([[0, 0], [1, 0], [0, 1]])` | Use three non-collinear coordinates defining a triangle. |
| 52 | `    result = predict_plane("linear", x, [1, 1, 1], [[.2, .2], [2, 2]])` | Predict once inside the triangle and once well outside it, using constant training values. |
| 53 | `    assert result[0] == pytest.approx(1)` | Inside support, interpolation should reproduce the constant value. |
| 54 | `    assert np.isnan(result[1])` | Outside support, require an explicit missing value rather than an invented linear extrapolation. |

## tests/test_four_workstreams.py

[Open actual source](../../tests/test_four_workstreams.py).

| Line | Actual code | Explanation |
| --- | --- | --- |
| 1 | `import csv` | Import the production function or supporting library named here; this is the implementation the test exercises. |
| 2 | `from pathlib import Path` | Import the production function or supporting library named here; this is the implementation the test exercises. |
| 3 | `import numpy as np` | Import NumPy for numerical arrays and independent array comparisons. |
| 4 | `import pandas as pd` | Import pandas to construct synthetic input tables in the same format as the real workflow. |
| 5 | `import pytest` | Import pytest for approximate scalar comparisons, expected exceptions and parametrised cases. |
| 6 | `from jetbridge_ml.data_processing.raw_speed import read_raw_speed` | Import the production function or supporting library named here; this is the implementation the test exercises. |
| 7 | `from jetbridge_ml.experimental_svr import evaluate_experimental_plane` | Import the production function or supporting library named here; this is the implementation the test exercises. |
| 8 | `from jetbridge_ml.machine_learning.selection import select_plane_svr` | Import the production function or supporting library named here; this is the implementation the test exercises. |
| 9 | `from jetbridge_ml.sensor_design_study import design_indices` | Import the production function or supporting library named here; this is the implementation the test exercises. |
| 10 | `from jetbridge_ml.cfd_interface.thermal_audit import read_probe_trace` | Import the production function or supporting library named here; this is the implementation the test exercises. |
| 12 | `GRID=dict(C=[.1],gamma=[.1],epsilon=[.002])` | Use one SVR candidate to keep the regression test fast. This is not the full research search. |
| 15 | `def test_nested_test_target_does_not_change_its_model():` | Define the test: nested test target does not change its model. pytest discovers names starting with test_. |
| 16 | `    x,y=np.meshgrid([0.,.5,1.],[0.,.5,1.])` | Create a 3 by 3 planar grid containing nine distinct sensor locations. |
| 17 | `    frame=pd.DataFrame(dict(x_m=x.ravel(),y_m=y.ravel(),z_m=3.05,` | Begin a synthetic one-run input table; flatten the coordinate grid and assign a fixed streamwise position. |
| 18 | `                            speed_mps=.1+.02*x.ravel()+.01*y.ravel(),source_row=np.arange(9),run_id='one'))` | Use an independently specified affine speed field and retain source-row IDs for auditing. |
| 19 | `    first,_,audit=evaluate_experimental_plane(frame,GRID)` | Run the real nested evaluation; keep predictions and the training/split audit. |
| 20 | `    changed=frame.copy(); changed.loc[0,'speed_mps']=9.` | Copy the table, then replace only sensor 0’s target with an extreme value. |
| 21 | `    second,_,_=evaluate_experimental_plane(changed,GRID)` | Repeat real fitting and selection with that altered table. |
| 22 | `    a=first[(first.fold==0)&(first.method=='svr')].iloc[0]` | Select the original prediction from the fold that withheld sensor 0. |
| 23 | `    b=second[(second.fold==0)&(second.method=='svr')].iloc[0]` | Select the equivalent prediction after changing the hidden target. |
| 24 | `    assert a.prediction_mps==b.prediction_mps` | Require the prediction to be unchanged: a hidden answer must not influence its fitted model. |
| 25 | `    for item in audit[audit.outer_source_row==0].itertuples():` | Inspect all inner split records associated with outer test sensor 0. |
| 26 | `        assert '0' not in item.outer_training_source_rows.split(';')` | Check that sensor 0 never appears in the outer training row IDs. |
| 27 | `        assert set(item.training_indices.split(';')).isdisjoint(item.validation_indices.split(';'))` | Check that inner training and validation indices do not overlap. |
| 30 | `def test_inner_scaling_and_location_groups_exclude_validation():` | Define the test: inner scaling and location groups exclude validation. pytest discovers names starting with test_. |
| 31 | `    x=np.array([[0,0],[0,0],[1,0],[1,1],[0,1],[.5,.5]],float)` | Include two observations at the same coordinate to test grouped-location exclusion. |
| 32 | `    y=.1+.01*x[:,0]` | Assign a known speed varying only with the first coordinate. |
| 33 | `    _,_,_,audit=select_plane_svr(x,y,grid=GRID)` | Call training-only parameter selection and retain its inner split/scaler audit. |
| 34 | `    for row in audit.itertuples():` | Inspect each recorded inner fold. |
| 35 | `        train=np.array(list(map(int,row.training_indices.split(';'))))` | Decode the stored training indices into an integer NumPy array. |
| 36 | `        val=np.array(list(map(int,row.validation_indices.split(';'))))` | Decode the stored validation indices separately. |
| 37 | `        np.testing.assert_allclose(list(map(float,row.scaler_mean.split(';'))),x[train].mean(axis=0))` | Independently calculate training-coordinate means and compare them with the fitted scaler means. |
| 38 | `        assert set(map(tuple,x[train])).isdisjoint(map(tuple,x[val]))` | Check coordinates, not just row numbers: duplicate locations must stay on the same side of the split. |
