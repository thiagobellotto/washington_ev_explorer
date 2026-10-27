"""Acquire a local or Washington source snapshot without silently dropping rows."""
import argparse
import json
from pathlib import Path

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
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sample", type=Path)
    parser.add_argument("--output", type=Path, default=Path("artifacts/input.parquet"))
    parser.add_argument("--bucket", help="Optionally upload the raw snapshot to S3")
    args = parser.parse_args()
    frame = prepare_data(pd.read_csv(args.sample) if args.sample else download_data())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(args.output, index=False)
    if args.bucket:
        import boto3
        boto3.client("s3").upload_file(str(args.output), args.bucket, "electric_vehicles.parquet")
    print(json.dumps({"source_rows": len(frame), "output": str(args.output)}))


if __name__ == "__main__":
    main()
