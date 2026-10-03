"""Select a DTW-distance threshold from a CSV with columns: label,score.

Usage: backend/.venv/Scripts/python scripts/calibrate_threshold.py results.csv
"""
import argparse
import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from app.services.matching import select_threshold


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("csv_file", type=Path)
    parser.add_argument("--max-far", type=float, default=0.05)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    genuine, impostor = [], []
    with args.csv_file.open(encoding="utf-8-sig", newline="") as source:
        for row in csv.DictReader(source):
            target = genuine if row["label"].strip().lower() == "genuine" else impostor
            target.append(float(row["score"]))
    result = select_threshold(genuine, impostor, args.max_far)
    payload = json.dumps(result, indent=2, ensure_ascii=False)
    if args.out:
        args.out.write_text(payload + "\n", encoding="utf-8")
    print(payload)


if __name__ == "__main__":
    main()
