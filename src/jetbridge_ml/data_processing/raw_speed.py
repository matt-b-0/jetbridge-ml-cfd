"""Read asynchronous FAA raw air-speed CSV records without pooling probes."""
import csv
from pathlib import Path
import numpy as np
import pandas as pd


def read_raw_speed(path):
    """Read raw speed/temperature records and nominal local-inch coordinates.

    Parameters
    ----------
    path : str or pathlib.Path
        Sxx-setup-station-flow-replicate.csv in 01-CSV.

    Returns
    -------
    pandas.DataFrame
        Long records with per-probe timestamps, scalar SI speed, temperature,
        and nominal raw x/local-height/z coordinates converted from inches.
        Source sentinel values become missing. Coordinates remain explicitly
        nominal, distinct from published absolute-metre sensor coordinates.
    """
    with Path(path).open(encoding='cp1252',newline='') as handle:
        rows=list(csv.reader(handle))
    if [r[0] for r in rows[:4]]!=['X (in)','Y (in)','Z (in)','Probe']:
        raise ValueError('Unexpected raw coordinate header or units')
    n=len(rows[4])-1
    if n%4 or n<12 or any(len(r)!=n+1 for r in rows):
        raise ValueError('Expected four channels per sensor and rectangular CSV')
    if any(rows[4][1+i:5+i]!=['Time (sec)','V (m/s)','T (°C)','P (hPa)'] for i in range(0,n,4)):
        raise ValueError('Unexpected channel names or units')
    data=np.array([[float(v) if v else np.nan for v in row[1:]] for row in rows[5:]],float)
    data[data==-9999]=np.nan
    if np.isinf(data).any():
        raise ValueError('Infinite raw observation')
    frames=[]
    for sensor,start in enumerate(range(0,n,4)):
        block=data[:,start:start+4]
        if np.any(block[np.isfinite(block[:,1]),1]<0):
            raise ValueError('Negative air speed')
        xyz=[float(rows[i][start+1])*.0254 for i in range(3)]
        frame=pd.DataFrame(block,columns=['time_sec','speed_mps','temperature_C','pressure_hPa'])
        frame['source_row']=sensor
        frame['raw_x_m'],frame['raw_local_height_m'],frame['raw_nominal_z_m']=xyz
        frames.append(frame[np.isfinite(frame.time_sec)])
    return pd.concat(frames,ignore_index=True)
