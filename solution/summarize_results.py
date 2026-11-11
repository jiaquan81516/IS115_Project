"""Aggregate per-day metrics into reproducible CSV and JSON summaries."""

import argparse
import csv
import json
import statistics
from pathlib import Path
from typing import Any, Dict, List, Optional

DEFAULT_POLICIES = (
    "baseline",
    "deadline_first",
    "window_nearest",
    "hybrid_otdr",
)
SUMMARY_METRICS = (
    "otdr_percent",
    "delivery_rate_percent",
    "on_time_deliveries",
    "number_of_trips",
    "total_distance_km",
    "average_capacity_utilization_percent",
)


def load_results(results: Path, policies: List[str]) -> List[Dict[str, Any]]:
    """Load every available metrics.json for the selected policies."""

    rows: List[Dict[str, Any]] = []
    for policy in policies:
        for metrics_path in sorted((results / policy).glob("day_*/metrics.json")):
            metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
            rows.append({"policy": policy, "day": metrics_path.parent.name, **metrics})
    return rows


def aggregate(rows: List[Dict[str, Any]], policies: List[str]) -> Dict[str, Any]:
    """Calculate mean, sample standard deviation, minimum and maximum by policy."""

    summary: Dict[str, Any] = {}
    for policy in policies:
        selected = [row for row in rows if row["policy"] == policy]
        policy_summary: Dict[str, Any] = {"days": len(selected)}
        for metric in SUMMARY_METRICS:
            values = [float(row[metric]) for row in selected]
            if not values:
                continue
            policy_summary[metric] = {
                "mean": round(statistics.mean(values), 4),
                "sample_standard_deviation": (
                    round(statistics.stdev(values), 4) if len(values) > 1 else 0.0
                ),
                "minimum": round(min(values), 4),
                "maximum": round(max(values), 4),
            }
        summary[policy] = policy_summary
    return summary


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path, default=Path("results"))
    parser.add_argument("--policies", nargs="+", default=list(DEFAULT_POLICIES))
    args = parser.parse_args(argv)

    rows = load_results(args.results, args.policies)
    if not rows:
        parser.error("no metrics files found")

    csv_path = args.results / "summary.csv"
    fieldnames = list(rows[0])
    with csv_path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    json_path = args.results / "summary.json"
    json_path.write_text(
        json.dumps(aggregate(rows, args.policies), indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    split_path = args.results / "split_summary.json"
    development = [row for row in rows if "day_001" <= row["day"] <= "day_010"]
    evaluation = [row for row in rows if "day_011" <= row["day"] <= "day_020"]
    split_path.write_text(
        json.dumps(
            {
                "development_days_001_010": aggregate(development, args.policies),
                "evaluation_days_011_020": aggregate(evaluation, args.policies),
            },
            indent=2,
            allow_nan=False,
        ) + "\n",
        encoding="utf-8",
    )
    print(f"Detailed summary: {csv_path}")
    print(f"Aggregate summary: {json_path}")
    print(f"Development/evaluation summary: {split_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
