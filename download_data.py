import argparse
import json
from pathlib import Path
import tempfile

import pandas as pd
import requests

COLUMNS = ["County", "City", "State", "Model Year", "Make", "Model",
           "Electric Range", "Vehicle Location"]
SOURCE_URL = "https://data.wa.gov/api/views/f6w7-q2d2/rows.json?accessType=DOWNLOAD"


def download_data(url=SOURCE_URL):
    response = requests.get(url, timeout=(10, 180))
    response.raise_for_status()
    payload = response.json()
    names = [column["name"] for column in payload["meta"]["view"]["columns"]]
    return pd.DataFrame(payload["data"], columns=names)


def prepare_data(frame):
    missing = set(COLUMNS) - set(frame.columns)
    if missing:
        raise ValueError(f"Missing source columns: {sorted(missing)}")
    return frame[COLUMNS].copy()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("data/electric_vehicles.parquet"))
    parser.add_argument("--refresh", action="store_true")
    args = parser.parse_args()
    if args.output.exists() and not args.refresh:
        print(json.dumps({"status": "cached", "output": str(args.output)}))
        return
    print("Downloading Washington EV data...", flush=True)
    frame = prepare_data(download_data())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=args.output.parent, suffix=".parquet", delete=False) as file:
        temporary = Path(file.name)
    try:
        frame.to_parquet(temporary, index=False)
        temporary.chmod(0o644)
        temporary.replace(args.output)
    finally:
        temporary.unlink(missing_ok=True)
    print(json.dumps({"status": "downloaded", "source_rows": len(frame), "output": str(args.output)}))


if __name__ == "__main__":
    main()
