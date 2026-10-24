"""Tiny demonstration: leave-one-location-out nearest-neighbour predictions.

Not a research-ready validation result; only 12 same-plane sensors are used.
"""
from pathlib import Path

import numpy as np

from jetbridge_ml.data_processing import load_sensor_speed_csv
from jetbridge_ml.interpolation import nearest_neighbor
from jetbridge_ml.validation import regression_metrics

ROOT = Path(__file__).resolve().parents[1]
CSV = ROOT / 'cfd/cases/empty_bridge_s01_a_10_hn_1/data/processed/experimental_sensor_speeds.csv'


def main() -> None:
    xyz, speeds = load_sensor_speed_csv(CSV)
    preds = np.empty_like(speeds)
    for i in range(len(speeds)):
        mask = np.arange(len(speeds)) != i
        preds[i] = nearest_neighbor(xyz[mask], speeds[mask], xyz[i:i + 1])[0]
    metrics = regression_metrics(speeds, preds)
    print(f"Demonstration only: {len(speeds)} leave-one-location-out predictions")
    print(f"Nearest-neighbour RMSE = {metrics['rmse']:.5f} m/s")
    print(f"Nearest-neighbour MAE  = {metrics['mae']:.5f} m/s")
    print("Do not interpret this as independent field reconstruction accuracy.")


if __name__ == '__main__':
    main()
