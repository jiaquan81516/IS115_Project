"""Calculate performance metrics from one simulation run's event log."""

import argparse
import csv
import json
import math
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from simulator.loaders import day_input_paths


def calculate_metrics(
    parcels: List[Dict[str, str]],
    distances: List[Dict[str, str]],
    config: Dict[str, Any],
    events: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Return a JSON-serializable dictionary for the chosen performance metric.

    parcels and distances are the rows of the day's CSV files, config is the
    contents of config.json, and events are the records from the run's log.
    CSV values are strings, so convert them before calculating. In particular,
    parcel times are "HH:MM" strings while event times are minutes after
    midnight: "17:00" is 17 * 60 = 1020.
    """

    def minutes(value: str) -> float:
        hour, minute = map(int, value.split(":"))
        return float(hour * 60 + minute)

    parcel_by_id = {row["parcel_id"]: row for row in parcels}
    distance_lookup: Dict[Tuple[str, str], float] = {
        (row["location_1"], row["location_2"]): float(row["dist"])
        for row in distances
    }

    deliveries: Dict[str, Dict[str, Any]] = {}
    routes: Dict[Tuple[int, int], List[str]] = {}
    number_of_trips = 0
    for event in events:
        event_type = event.get("event_type")
        if event_type == "hub_departure":
            number_of_trips += 1
        elif event_type == "delivery":
            parcel_id = event["parcel_id"]
            if parcel_id in deliveries:
                raise ValueError(f"duplicate delivery event for {parcel_id}")
            if parcel_id not in parcel_by_id:
                raise ValueError(f"delivery event references unknown parcel {parcel_id}")
            deliveries[parcel_id] = event
            key = (event["vehicle_id"], event["trip_id"])
            routes.setdefault(key, []).append(parcel_id)

    on_time = 0
    early = 0
    late = 0
    earliness: List[float] = []
    lateness: List[float] = []
    for parcel_id, event in deliveries.items():
        record = parcel_by_id[parcel_id]
        start = minutes(record["delivery_window_start"])
        end = minutes(record["delivery_window_end"])
        delivery_time = float(event["time"])
        if delivery_time < start:
            early += 1
            earliness.append(start - delivery_time)
        elif delivery_time > end:
            late += 1
            lateness.append(delivery_time - end)
        else:
            on_time += 1

    total_distance = 0.0
    trip_loads: List[float] = []
    for route in routes.values():
        locations = ["HUB"] + [
            parcel_by_id[parcel_id]["delivery_location_id"] for parcel_id in route
        ] + ["HUB"]
        total_distance += math.fsum(
            distance_lookup[(origin, destination)]
            for origin, destination in zip(locations, locations[1:])
        )
        trip_loads.append(math.fsum(float(parcel_by_id[parcel_id]["size"]) for parcel_id in route))

    total = len(parcels)
    delivered = len(deliveries)
    capacity = float(config["capacity"])
    return {
        "total_parcels": total,
        "on_time_deliveries": on_time,
        "otdr_percent": round(100.0 * on_time / total, 4) if total else 0.0,
        "delivered_parcels": delivered,
        "delivery_rate_percent": round(100.0 * delivered / total, 4) if total else 0.0,
        "on_time_among_delivered_percent": (
            round(100.0 * on_time / delivered, 4) if delivered else 0.0
        ),
        "early_deliveries": early,
        "late_deliveries": late,
        "undelivered_parcels": total - delivered,
        "average_earliness_minutes": (
            round(math.fsum(earliness) / len(earliness), 4) if earliness else 0.0
        ),
        "average_lateness_minutes": (
            round(math.fsum(lateness) / len(lateness), 4) if lateness else 0.0
        ),
        "number_of_trips": number_of_trips,
        "total_distance_km": round(total_distance, 4),
        "average_distance_per_trip_km": (
            round(total_distance / number_of_trips, 4) if number_of_trips else 0.0
        ),
        "average_capacity_utilization_percent": (
            round(100.0 * math.fsum(trip_loads) / (capacity * len(trip_loads)), 4)
            if trip_loads else 0.0
        ),
    }


def main(argv: Optional[List[str]] = None) -> int:
    """Load one day's inputs and event log, then write the metrics report."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=Path("data"),
                        help="directory containing dist.csv, config.json and demand/")
    parser.add_argument("--day", required=True, help="day identifier, for example day_001")
    parser.add_argument("--log", type=Path, required=True,
                        help="event log from a simulator run")
    parser.add_argument("--output", type=Path,
                        help="JSON report (default: metrics.json beside the selected log)")
    args = parser.parse_args(argv)
    try:
        parcel_path, distance_path, config_path = day_input_paths(args.data, args.day)
        output = args.output if args.output is not None else args.log.with_name("metrics.json")
        # The input files all live in the data directory, so this also protects them.
        if output.resolve() == args.data.resolve() or args.data.resolve() in output.resolve().parents:
            raise ValueError("report output must be outside the input data directory")
        if output.resolve() == args.log.resolve():
            raise ValueError("report output must not overwrite the log")
        with parcel_path.open(newline="", encoding="utf-8-sig") as stream:
            parcels = list(csv.DictReader(stream))
        with distance_path.open(newline="", encoding="utf-8-sig") as stream:
            distances = list(csv.DictReader(stream))
        config = json.loads(config_path.read_text(encoding="utf-8-sig"))
        with args.log.open(encoding="utf-8") as stream:
            events = [json.loads(line) for line in stream if line.strip()]
        metrics = calculate_metrics(parcels, distances, config, events)
        report = json.dumps(metrics, indent=2, allow_nan=False) + "\n"
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(report, encoding="utf-8")
    except (OSError, ValueError) as exc:
        parser.exit(2, f"error: {exc}\n")
    print(f"Metrics report: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
