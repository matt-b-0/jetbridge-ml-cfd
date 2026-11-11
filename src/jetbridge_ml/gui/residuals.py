"""Dependency-free OpenFOAM initial-residual recording and history reading."""
import csv
import math
from pathlib import Path
import re

COLUMNS=('iteration','field','initial_residual','final_residual','linear_iterations','source')
TIME=re.compile(r'^Time\s*=\s*([0-9.eE+-]+)\s*$')
SOLVE=re.compile(r'Solving for (\w+), Initial residual = ([^,]+), Final residual = ([^,]+), No Iterations (\d+)')


class ResidualRecorder:
    """Record the first solve of each field at each SIMPLE iteration.

    Parameters
    ----------
    path : pathlib.Path
        New CSV destination, flushed after each recorded solver line.
    source : str
        Fresh or archived lineage displayed with the saved history.
    """
    def __init__(self,path,source='fresh isothermal CFD'):
        self.handle=Path(path).open('w',newline='',encoding='utf-8')
        self.writer=csv.DictWriter(self.handle,fieldnames=COLUMNS)
        self.writer.writeheader();self.handle.flush()
        self.source=source;self.iteration=None;self.seen=set();self.count=0

    def feed(self,line):
        """Consume one log line, retaining actual zeros and initial/final values."""
        time=TIME.match(line.strip())
        if time:self.iteration=float(time[1]);return None
        match=SOLVE.search(line)
        if not match or self.iteration is None:return None
        key=(self.iteration,match[1])
        if key in self.seen:return None
        initial,final=float(match[2]),float(match[3])
        record=dict(iteration=self.iteration,field=match[1],initial_residual=initial,
                    final_residual=final,linear_iterations=int(match[4]),source=self.source)
        self.writer.writerow(record);self.handle.flush();self.seen.add(key);self.count+=1
        return record

    def close(self):
        """Close the history after success, failure or user cancellation."""
        self.handle.close()


def read_history(path):
    """Read finite initial residuals, tolerating a writer's incomplete last row.

    Parameters
    ----------
    path : pathlib.Path
        Streaming or saved residual CSV.

    Returns
    -------
    list of dict
        Actual nonnegative residuals with their iteration, field and source.
    """
    records=[]
    try:
        with Path(path).open(newline='',encoding='utf-8-sig') as handle:
            for row in csv.DictReader(handle):
                try:
                    it=float(row['iteration']);value=float(row.get('initial_residual',row.get('residual','')))
                    field=row['field']
                    if not field or not math.isfinite(it) or not math.isfinite(value) or value<0:continue
                    records.append(dict(iteration=it,field=field,initial_residual=value,source=row.get('source','saved history')))
                except (TypeError,ValueError,KeyError):continue
    except (FileNotFoundError,PermissionError):return []
    return records
