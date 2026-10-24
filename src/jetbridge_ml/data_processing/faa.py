"""Read FAA replicate-averaged scalar air-speed planes without changing coordinates."""
from pathlib import Path
import re

import numpy as np
import pandas as pd


def read_speed_average(path: str | Path) -> pd.DataFrame:
    """Read one numeric-station FAA BLOCK file.

    Parameters
    ----------
    path : str or Path
        V-Sxx-setup-station-flow-replicate.txt in 03-Averages.

    Returns
    -------
    pandas.DataFrame
        Absolute metre coordinates, speed in m/s, source row and run metadata.
        Missing speed sentinels become NaN; invalid coordinates are rejected.
    """
    path = Path(path)
    match = re.fullmatch(
        r"V-(S\d+)-([A-Z0-9]+)-(\d+)-(HN|HP|LN|LP)-(\d+[A-Z]?)", path.stem)
    if not match:
        raise ValueError(f"Unsupported replicate filename: {path.name}")
    text = path.read_text(encoding="cp1252")
    variables = re.search(r"(?m)^VARIABLES=(.*)$", text)
    zones = list(re.finditer(r"(?m)^ZONE\s+(.*)$", text))
    if variables is None or len(zones) != 1:
        raise ValueError("Expected VARIABLES and exactly one ZONE")
    names = re.findall(r'"([^"]+)"', variables[1])
    expected = ["X (m)", "Y (m)", "Z (m)", "Mean", "dMean", "Median", "dMedian", "StdDev"]
    if names != expected:
        raise ValueError(f"Unexpected units/variables: {names}")
    header = zones[0][1]
    dims = [re.search(rf"\b{axis}\s*=\s*(\d+)", header) for axis in "IJK"]
    if not all(dims) or not re.search(r"\bF\s*=\s*BLOCK\b", header):
        raise ValueError("Expected I/J/K dimensions and F=BLOCK")
    count = int(np.prod([int(dim[1]) for dim in dims]))
    tokens = text[zones[0].end():].split()
    values = np.array([float(token) for token in tokens])
    if count < 4 or values.size != count * len(names):
        raise ValueError("BLOCK data length does not match dimensions")
    data = values.reshape(len(names), count)
    xyz = data[:3].T
    if not np.isfinite(xyz).all() or np.any(xyz == -9999):
        raise ValueError("Invalid sensor coordinates")
    if np.unique(xyz, axis=0).shape[0] != count or np.ptp(xyz[:, 2]) > 1e-9:
        raise ValueError("Expected unique coordinates on one z plane")
    speed = data[3].copy()
    speed[speed == -9999] = np.nan
    if np.isinf(speed).any() or np.any(speed[np.isfinite(speed)] < 0):
        raise ValueError("Invalid negative/infinite speed")
    config, setup, station, flow, replicate = match.groups()
    frame = pd.DataFrame(xyz, columns=["x_m", "y_m", "z_m"])
    frame["speed_mps"] = speed
    frame["source_row"] = np.arange(count)
    frame["run_id"] = path.stem[2:]
    frame["config"], frame["setup"] = config, setup
    frame["station_ft"], frame["flow"], frame["replicate"] = int(station), flow, replicate
    return frame
