"""Summarize a labeled verification CSV: label,granted,score,processing_ms."""
import argparse
import csv
import json
from pathlib import Path

import numpy as np


def as_bool(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "granted"}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("csv_file", type=Path)
    args = parser.parse_args()
    rows = list(csv.DictReader(args.csv_file.open(encoding="utf-8-sig", newline="")))
    genuine = [row for row in rows if row["label"].lower() == "genuine"]
    impostor = [row for row in rows if row["label"].lower() == "impostor"]
    tp = sum(as_bool(row["granted"]) for row in genuine)
    fn = len(genuine) - tp
    fp = sum(as_bool(row["granted"]) for row in impostor)
    tn = len(impostor) - fp
    latency = [float(row["processing_ms"]) for row in rows]
    report = {
        "samples": len(rows), "confusion_matrix": {"tp": tp, "fn": fn, "fp": fp, "tn": tn},
        "accuracy": round((tp + tn) / len(rows), 4) if rows else 0,
        "far": round(fp / len(impostor), 4) if impostor else None,
        "frr": round(fn / len(genuine), 4) if genuine else None,
        "latency_ms": {"median": round(float(np.median(latency)), 2), "p95": round(float(np.percentile(latency, 95)), 2)} if latency else {},
    }
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

