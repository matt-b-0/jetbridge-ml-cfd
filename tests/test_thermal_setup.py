"""Check thermal setup from synthetic known-unit experimental records."""
import importlib.util
import json
from pathlib import Path
import sys

import numpy as np
import pandas as pd
import pytest

ROOT=Path(__file__).resolve().parents[1]
SPEC=importlib.util.spec_from_file_location("thermal_prepare", ROOT/"cfd/cases/thermal_bridge_s01_ac_10_hn_1/scripts/prepare.py")
PREPARE=importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PREPARE)


def sources(tmp_path):
    dataset=tmp_path/"dataset"
    for folder in ("06-Periods","05-HVAC","03-Averages"):
        (dataset/folder).mkdir(parents=True)
    run="S01-AC-10-HN-1"
    pd.DataFrame([{"Set":run,"Stable-Start (sec)":100,"Stable-End (sec)":200,
                   "Entire Set-Start (sec)":100,"Entire Set-End (sec)":200}]).to_csv(dataset/"06-Periods/Periods.csv",index=False)
    pd.DataFrame({"Time (sec)":[99,100,150,200],
                  "T.db.SA (°C)":[99,19,21,-9999],
                  "Tdb.Lab (°C)":[99,24,26,-9999],
                  "Q.FS (lps)":[999,400,600,-9999]}).to_csv(dataset/f"05-HVAC/{run}.csv",index=False,encoding="cp1252")
    header='TITLE="test"\nVARIABLES="X (m)", "Y (m)", "Z (m)", "Mean", "dMean", "Median", "dMedian", "StdDev"\nZONE I=2, J=2, K=1 F=BLOCK\n'
    xyz="0.35 0.35 1.04 1.04\n0.45 2.48 0.45 2.48\n3.05 3.05 3.05 3.05\n"
    for prefix,values in (("V",".1 .2 .3 .4"),("T","22 23 24 25")):
        (dataset/f"03-Averages/{prefix}-{run}.txt").write_text(header+xyz+values+"\n"+"0 0 0 0\n"*4)
    (dataset/"Data Dictionary.csv").write_text("Synthetic fixture")
    template=tmp_path/"template"
    (template/"system").mkdir(parents=True)
    (template/"constant").mkdir()
    (template/"system/blockMeshDict").write_text("unchanged geometry")
    (template/"constant/turbulenceProperties").write_text("simulationType RAS;")
    return dataset,template


def generate(tmp_path,monkeypatch,control=False):
    dataset,template=sources(tmp_path)
    output=tmp_path/"case"
    args=["prepare","--dataset",str(dataset),"--template",str(template),"--output",str(output)]
    if control:
        args.append("--no-buoyancy")
    monkeypatch.setattr(sys,"argv",args)
    PREPARE.main()
    return output,dataset,template


def test_thermal_units_window_missing_values_and_gravity(tmp_path,monkeypatch):
    out,_,template=generate(tmp_path,monkeypatch)
    s=json.loads((out/"data/processed/setup.json").read_text())
    assert s["inlet_temperature_K"]==pytest.approx(293.15)
    assert s["ambient_temperature_K"]==pytest.approx(298.15)
    assert s["flow_m3ps"]==pytest.approx(.5)
    assert s["beta_per_K"]==pytest.approx(1/298.15)
    assert s["relative_density_variation"]==pytest.approx(5/298.15)
    assert set(s["valid_hvac_counts"].values())=={2}
    assert "value (0 -9.81 0)" in (out/"constant/g").read_text()
    assert (out/"system/blockMeshDict").read_bytes()==(template/"system/blockMeshDict").read_bytes()
    obs=pd.read_csv(out/"data/processed/experimental_sensors.csv")
    np.testing.assert_allclose(obs.temperature_C,[22,23,24,25])


def test_control_disables_gravity_only(tmp_path,monkeypatch):
    out,_,_=generate(tmp_path,monkeypatch,control=True)
    assert "value (0 0 0)" in (out/"constant/g").read_text()
    s=json.loads((out/"data/processed/setup.json").read_text())
    assert s["no_buoyancy_control"] is True
    assert s["supply_minus_lab_K"]==pytest.approx(-5)


def test_window_mismatch_is_rejected_before_case_creation(tmp_path,monkeypatch):
    dataset,template=sources(tmp_path)
    p=dataset/"06-Periods/Periods.csv"
    frame=pd.read_csv(p)
    frame["Stable-Start (sec)"]=110
    frame.to_csv(p,index=False)
    output=tmp_path/"case"
    monkeypatch.setattr(sys,"argv",["prepare","--dataset",str(dataset),"--template",str(template),"--output",str(output)])
    with pytest.raises(ValueError,match="Stable window differs"):
        PREPARE.main()
    assert not output.exists()
