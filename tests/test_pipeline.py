import json
import subprocess
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import build


def test_sample_build_and_failed_rebuild_preserve_published_run(monkeypatch):
    run = build.build()
    frame = pd.read_csv(run / "enriched_electric_vehicles.csv")
    assert len(frame) == 12
    accepted = frame[frame.quality_status == "accepted"]
    assert len(accepted) == 10
    assert 2025 in accepted.model_year.values
    assert accepted.latitude.isna().sum() == 1
    assert (accepted[accepted.electric_range == 0].range_category == "Unknown / not reported").all()
    assert json.loads((run / "metadata.json").read_text())["dataset"] == "synthetic sample"
    from streamlit.testing.v1 import AppTest
    app = AppTest.from_file(str(ROOT / "streamlit_app.py")).run(timeout=30)
    assert not app.exception
    assert app.metric[0].value == "10"
    app.multiselect[0].select("TESLA").run()
    assert app.metric[0].value == "3"
    app.multiselect[1].select("Spokane").run()
    assert not app.exception
    assert app.metric[0].value == "0"
    pointer = ROOT / "artifacts/current"
    previous = pointer.read_text()
    real_run = subprocess.run

    def fail_dbt(command, **kwargs):
        if command[0] == "dbt":
            raise subprocess.CalledProcessError(1, command)
        return real_run(command, **kwargs)

    monkeypatch.setattr(build.subprocess, "run", fail_dbt)
    import pytest
    with pytest.raises(subprocess.CalledProcessError):
        build.build()
    assert pointer.read_text() == previous
