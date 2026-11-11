import pandas as pd
import pytest
from jetbridge_ml.data_processing import load_sensor_speed_csv


def test_processed_sensor_loader(tmp_path):
    p = tmp_path / 'test.csv'
    pd.DataFrame({'x_m': [0., 1.], 'y_m': [1., 1.], 'z_m': [3., 3.], 'speed_m_per_s': [0.1, 0.2]}).to_csv(p, index=False)
    xyz, speeds = load_sensor_speed_csv(p)
    assert xyz.shape == (2, 3)
    assert speeds.tolist() == [0.1, 0.2]


def test_missing_columns_rejected(tmp_path):
    p = tmp_path / 'bad.csv'
    pd.DataFrame({'x_m': [0.]}).to_csv(p, index=False)
    with pytest.raises(ValueError):
        load_sensor_speed_csv(p)
