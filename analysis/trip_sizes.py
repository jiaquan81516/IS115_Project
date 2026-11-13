"""Report Section 3. How large do n and m get in practice?

The complexity analysis is written in n (parcels waiting at a dispatch call) and m (parcels on the
trip being built). Capacity is 30 size units, not 30 parcels, and parcels are smaller than one unit
on average, so m can exceed 30. This script measures m from the event logs of every policy:
parcels per trip (mean, maximum, share of trips above 30) over days 001-020.

Reads results/<policy>/<day>/log.txt only. Standard library only.
Writes analysis/output/trip_sizes.json.
"""
import json, os, statistics
from pathlib import Path

PROJ = Path(os.environ.get("PROJ", ".")).resolve()
OUT = Path(os.environ.get("ANALYSIS_OUT", PROJ / "analysis" / "output"))
OUT.mkdir(parents=True, exist_ok=True)
POLICIES = ["baseline", "deadline_first", "window_nearest", "hybrid_otdr", "seeded_nn", "batched_nn"]


def parcels_per_trip(policy, day):
    """Return the number of parcels delivered on each trip of one simulated day."""
    trips = {}
    with open(PROJ / "results" / policy / day / "log.txt", encoding="utf-8") as stream:
        for line in stream:
            if not line.strip(): continue
            event = json.loads(line)
            if event["event_type"] == "delivery":
                key = (event["vehicle_id"], event["trip_id"])
                trips[key] = trips.get(key, 0) + 1
    return list(trips.values())


if __name__ == "__main__":
    out = {}
    for policy in POLICIES:
        sizes = [s for i in range(1, 21) for s in parcels_per_trip(policy, f"day_{i:03d}")]
        out[policy] = {
            "trips": len(sizes),
            "mean_parcels_per_trip": round(statistics.mean(sizes), 2),
            "max_parcels_per_trip": max(sizes),
            "share_of_trips_over_30_parcels_percent": round(100 * sum(s > 30 for s in sizes) / len(sizes), 1),
        }
        print(f"{policy:15s}", out[policy])
    json.dump(out, open(OUT / "trip_sizes.json", "w"), indent=1)
