"""Build into an isolated directory; publish only after dbt and export succeed."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time

import duckdb

ROOT = Path(__file__).resolve().parents[1]


def build(sample=True):
    started = time.monotonic()
    artifacts = ROOT / "artifacts"
    artifacts.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(dir=artifacts) as scratch:
        stage = Path(scratch)
        source = stage / "input.parquet"
        command = [sys.executable, str(ROOT / "download_data.py"), "--output", str(source)]
        if sample:
            command += ["--sample", str(ROOT / "data/sample.csv")]
        subprocess.run(command, check=True)
        environment = dict(os.environ, EV_INPUT_PATH=str(source), EV_DB_PATH=str(stage / "ev.duckdb"))
        subprocess.run(["dbt", "run", "--profiles-dir", "."], cwd=ROOT / "dbt", env=environment, check=True)
        tables = ["yearly_trend", "make_trend_by_model", "county_summary", "data_quality", "enriched_electric_vehicles"]
        with duckdb.connect(str(stage / "ev.duckdb"), read_only=True) as connection:
            for table in tables:
                connection.sql(f"select * from {table}").df().to_csv(stage / f"{table}.csv", index=False)
        metadata = {"dataset": "synthetic sample" if sample else "Washington EV population snapshot",
                    "built_at": datetime.now(timezone.utc).isoformat(),
                    "duration_seconds": round(time.monotonic() - started, 2),
                    "source_url": None if sample else "https://data.wa.gov/api/views/f6w7-q2d2/rows.json?accessType=DOWNLOAD"}
        (stage / "metadata.json").write_text(json.dumps(metadata, indent=2))
        # Immutable run directory plus atomic pointer prevents readers seeing mixed runs.
        run = artifacts / ("run-" + str(time.time_ns()))
        shutil.copytree(stage, run)
        pointer = artifacts / "current.tmp"
        pointer.write_text(run.name)
        pointer.replace(artifacts / "current")
        print(json.dumps(metadata, indent=2))
        return run


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true", help="Download the current WA source instead of the synthetic fixture")
    args = parser.parse_args()
    build(sample=not args.live)
