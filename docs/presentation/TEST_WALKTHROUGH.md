# Tests explained line by line

These are the same actual source lines as the offline HTML walkthrough. Read each test as controlled inputs, production call, expected answer and assertion.

## tests/test_core.py

[Open actual source](../../tests/test_core.py).

| Line | Actual code | Explanation |
| --- | --- | --- |
| 1 | `"""Six core checks for the presentation and the default pytest run.` | Documentation states the property being tested; it is not an assertion or a numerical operation. |
| 2 | `(blank)` | Blank line separates logical steps; it has no computational effect. |
| 3 | `Five test functions produce six cases: the affine-field test runs once for` | Continuation of the module documentation describing the scope and limits of these checks. |
| 4 | `linear interpolation and once for RBF. Optional regression checks are in` | Continuation of the module documentation describing the scope and limits of these checks. |
| 5 | `tests/extended. These checks do not certify physical CFD accuracy.` | Continuation of the module documentation describing the scope and limits of these checks. |
| 6 | `"""` | Documentation states the property being tested; it is not an assertion or a numerical operation. |
| 7 | `(blank)` | Blank line separates logical steps; it has no computational effect. |
| 8 | `import numpy as np` | Import NumPy for numerical arrays and independent array comparisons. |
| 9 | `import pandas as pd` | Import pandas to construct synthetic input tables in the same format as the real workflow. |
| 10 | `import pytest` | Import pytest for approximate scalar comparisons, expected exceptions and parametrised cases. |
| 11 | `(blank)` | Blank line separates logical steps; it has no computational effect. |
| 12 | `from jetbridge_ml.experimental_svr import evaluate_experimental_plane` | Import the production function or supporting library named here; this is the implementation the test exercises. |
| 13 | `from jetbridge_ml.interpolation import nearest_neighbor` | Import the production function or supporting library named here; this is the implementation the test exercises. |
| 14 | `from jetbridge_ml.interpolation.plane import predict_plane` | Import the production function or supporting library named here; this is the implementation the test exercises. |
| 15 | `from jetbridge_ml.validation.metrics import regression_metrics` | Import the production function or supporting library named here; this is the implementation the test exercises. |
| 16 | `(blank)` | Blank line separates logical steps; it has no computational effect. |
| 17 | `# One candidate keeps the leakage check quick; research uses the full grid.` | Comment explaining intent; Python does not execute it. |
| 18 | `GRID=dict(C=[.1],gamma=[.1],epsilon=[.002])` | Use one SVR candidate to keep the regression test fast. This is not the full research search. |
| 19 | `(blank)` | Blank line separates logical steps; it has no computational effect. |
| 20 | `(blank)` | Blank line separates logical steps; it has no computational effect. |
| 21 | `(blank)` | Blank line separates logical steps; it has no computational effect. |
| 22 | `def test_nearest_neighbor_matches_known_locations():` | Define the test: nearest neighbor matches known locations. pytest discovers names starting with test_. |
| 23 | `    locations = np.array([[0.0, 0.0], [2.0, 0.0], [0.0, 2.0]])` | Define three known sensor coordinates on a plane. |
| 24 | `    values = np.array([1.0, 4.0, 9.0])` | Attach a deliberately distinct value to each sensor so the selected neighbour is unambiguous. |
| 25 | `    out = nearest_neighbor(locations, values, np.array([[0.1, 0.1], [1.8, 0.0]]))` | Query near the first and second sensors using the production nearest-neighbour implementation. |
| 26 | `    np.testing.assert_array_equal(out, [1.0, 4.0])` | Require the two independently known neighbour values exactly; no fitting tolerance is needed here. |
| 27 | `(blank)` | Blank line separates logical steps; it has no computational effect. |
| 28 | `(blank)` | Blank line separates logical steps; it has no computational effect. |
| 29 | `def test_zero_bias_can_hide_large_local_errors():` | Define the test: zero bias can hide large local errors. pytest discovers names starting with test_. |
| 30 | `    """Opposite signed errors cancel in bias, but not in MAE or RMSE."""` | Documentation states the property being tested; it is not an assertion or a numerical operation. |
| 31 | `    actual = np.array([0.1, 0.3])` | Define two known reference speeds in m/s. These are synthetic test values, not FAA observations. |
| 32 | `    predicted = np.array([0.3, 0.1])` | Reverse the values: prediction minus reference becomes +0.2 and -0.2 m/s. |
| 33 | `    metrics = regression_metrics(actual, predicted)` | Call the actual production metric function with the two arrays. |
| 34 | `    assert metrics["bias"] == pytest.approx(0.0, abs=1e-12)` | The average signed error is zero. Allow an absolute 1e-12 rounding difference near zero. |
| 35 | `    assert metrics["mae"] == pytest.approx(0.2)` | The mean of the absolute errors is (0.2 + 0.2)/2 = 0.2 m/s. |
| 36 | `    assert metrics["rmse"] == pytest.approx(0.2)` | The square root of the mean squared error is sqrt((0.04 + 0.04)/2) = 0.2 m/s. |
| 37 | `(blank)` | Blank line separates logical steps; it has no computational effect. |
| 38 | `(blank)` | Blank line separates logical steps; it has no computational effect. |
| 39 | `@pytest.mark.parametrize("method", ["linear", "rbf"])` | Exercise both interpolators that should reproduce the specified affine field. |
| 40 | `def test_affine_field_reproduction(method):` | Define the test: affine field reproduction. pytest discovers names starting with test_. |
| 41 | `    x = np.array([[0, 0], [1, 0], [0, 1], [1, 1], [.5, .5]])` | Define four square corners and one interior training coordinate. |
| 42 | `    q = np.array([[.2, .3], [.6, .8]])` | Choose two interior points that are not training sensors. |
| 43 | `    result = predict_plane(method, x, 2 + 3*x[:, 0] - x[:, 1], q)` | Fit using values from the known affine formula f(x,y)=2+3x-y and predict the query points. |
| 44 | `    np.testing.assert_allclose(result, 2 + 3*q[:, 0] - q[:, 1], atol=1e-12)` | Compare with the formula evaluated independently at the queries. This verifies an exact-property benchmark. |
| 45 | `(blank)` | Blank line separates logical steps; it has no computational effect. |
| 46 | `(blank)` | Blank line separates logical steps; it has no computational effect. |
| 47 | `def test_linear_extrapolation_is_explicit():` | Define the test: linear extrapolation is explicit. pytest discovers names starting with test_. |
| 48 | `    x = np.array([[0, 0], [1, 0], [0, 1]])` | Use three non-collinear coordinates defining a triangle. |
| 49 | `    result = predict_plane("linear", x, [1, 1, 1], [[.2, .2], [2, 2]])` | Predict once inside the triangle and once well outside it, using constant training values. |
| 50 | `    assert result[0] == pytest.approx(1)` | Inside support, interpolation should reproduce the constant value. |
| 51 | `    assert np.isnan(result[1])` | Outside support, require an explicit missing value rather than an invented linear extrapolation. |
| 52 | `(blank)` | Blank line separates logical steps; it has no computational effect. |
| 53 | `(blank)` | Blank line separates logical steps; it has no computational effect. |
| 54 | `def test_nested_test_target_does_not_change_its_model():` | Define the test: nested test target does not change its model. pytest discovers names starting with test_. |
| 55 | `    x,y=np.meshgrid([0.,.5,1.],[0.,.5,1.])` | Create a 3 by 3 planar grid containing nine distinct sensor locations. |
| 56 | `    frame=pd.DataFrame(dict(x_m=x.ravel(),y_m=y.ravel(),z_m=3.05,` | Begin a synthetic one-run input table; flatten the coordinate grid and assign a fixed streamwise position. |
| 57 | `                            speed_mps=.1+.02*x.ravel()+.01*y.ravel(),source_row=np.arange(9),run_id='one'))` | Use an independently specified affine speed field and retain source-row IDs for auditing. |
| 58 | `    first,_,audit=evaluate_experimental_plane(frame,GRID)` | Run the real nested evaluation; keep predictions and the training/split audit. |
| 59 | `    changed=frame.copy(); changed.loc[0,'speed_mps']=9.` | Copy the table, then replace only sensor 0’s target with an extreme value. |
| 60 | `    second,_,_=evaluate_experimental_plane(changed,GRID)` | Repeat real fitting and selection with that altered table. |
| 61 | `    a=first[(first.fold==0)&(first.method=='svr')].iloc[0]` | Select the original prediction from the fold that withheld sensor 0. |
| 62 | `    b=second[(second.fold==0)&(second.method=='svr')].iloc[0]` | Select the equivalent prediction after changing the hidden target. |
| 63 | `    assert a.prediction_mps==b.prediction_mps` | Require the prediction to be unchanged: a hidden answer must not influence its fitted model. |
| 64 | `    for item in audit[audit.outer_source_row==0].itertuples():` | Inspect all inner split records associated with outer test sensor 0. |
| 65 | `        assert '0' not in item.outer_training_source_rows.split(';')` | Check that sensor 0 never appears in the outer training row IDs. |
| 66 | `        assert set(item.training_indices.split(';')).isdisjoint(item.validation_indices.split(';'))` | Check that inner training and validation indices do not overlap. |
