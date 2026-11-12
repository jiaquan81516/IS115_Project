"""Tests for the batched seeded nearest-neighbour policy."""

import copy
import tempfile
import unittest
from pathlib import Path

from simulator.loaders import day_input_paths
from simulator.simulator import Simulator
from solution.policies.batched_nn import _build_route, dispatch

ROOT = Path(__file__).resolve().parents[1]


def make_distances(pairs):
    names = {name for pair in pairs for name in pair} | {"HUB"}
    table = {a: {b: 0.0 for b in names} for a in names}
    for (a, b), km in pairs.items():
        table[a][b] = km
        table[b][a] = km
    return table


def make_context(distances, current_time):
    return {
        "current_time": current_time, "vehicle_id": 1, "capacity": 30.0,
        "travel_distance": distances, "departure_delay": 30.0, "return_cutoff": 1080.0,
        "max_trip_distance_km": 320.0,
        "fleet": {1: {"available_at": current_time, "max_trip_distance_km": 320.0}},
    }


def make_parcel(location, start, end, size=1.0):
    return {"arrival_time": 480.0, "delivery_location_id": location,
            "delivery_window_start": start, "delivery_window_end": end,
            "size": size, "delivery_time": None, "vehicle_assigned": None, "trip_id": None}


class ConstructionTests(unittest.TestCase):
    def test_seed_is_urgent_and_fill_is_nearest_not_earliest_deadline(self) -> None:
        distances = make_distances({
            ("HUB", "S"): 10.0, ("HUB", "X"): 12.0, ("HUB", "Y"): 11.0,
            ("S", "X"): 20.0, ("S", "Y"): 1.0, ("X", "Y"): 20.0,
        })
        parcels = {"S": make_parcel("S", 0.0, 600.0), "X": make_parcel("X", 0.0, 650.0),
                   "Y": make_parcel("Y", 0.0, 700.0)}
        self.assertEqual(_build_route(parcels, make_context(distances, 480.0)), ["S", "Y", "X"])

    def test_parcel_that_would_be_early_is_not_the_seed(self) -> None:
        distances = make_distances({("HUB", "E"): 10.0, ("HUB", "S"): 10.0, ("E", "S"): 30.0})
        parcels = {"E": make_parcel("E", 600.0, 700.0), "S": make_parcel("S", 500.0, 800.0)}
        self.assertEqual(_build_route(parcels, make_context(distances, 480.0))[0], "S")


class HardConstraintTests(unittest.TestCase):
    def test_capacity_is_never_exceeded(self) -> None:
        distances = make_distances({("HUB", "A"): 10.0})
        parcels = {name: make_parcel("A", 0.0, 1000.0, 15.0) for name in ("P1", "P2", "P3")}
        self.assertEqual(len(dispatch(parcels, make_context(distances, 600.0))), 2)

    def test_out_of_range_parcel_is_excluded(self) -> None:
        distances = make_distances({("HUB", "A"): 10.0, ("HUB", "F"): 200.0, ("A", "F"): 190.0})
        parcels = {"A": make_parcel("A", 0.0, 1000.0, 15.0), "F": make_parcel("F", 0.0, 1070.0, 15.0)}
        self.assertEqual(_build_route(parcels, make_context(distances, 600.0)), ["A"])

    def test_route_returning_after_cutoff_is_never_dispatched(self) -> None:
        distances = make_distances({("HUB", "A"): 10.0})
        parcels = {"A": make_parcel("A", 0.0, 1100.0, 20.0)}
        self.assertEqual(dispatch(parcels, make_context(distances, 1040.0)), [])


class HoldOrGoTests(unittest.TestCase):
    def test_holds_small_load_with_plenty_of_slack(self) -> None:
        distances = make_distances({("HUB", "A"): 10.0})
        parcels = {"A": make_parcel("A", 0.0, 1070.0, 2.0)}
        self.assertEqual(dispatch(parcels, make_context(distances, 600.0)), [])

    def test_dispatches_when_load_reaches_target(self) -> None:
        distances = make_distances({("HUB", "A"): 10.0})
        parcels = {"A": make_parcel("A", 0.0, 1070.0, 24.0)}   # 80% of capacity
        self.assertEqual(dispatch(parcels, make_context(distances, 600.0)), ["A"])

    def test_dispatches_small_load_when_window_slack_is_low(self) -> None:
        distances = make_distances({("HUB", "A"): 10.0})
        parcels = {"A": make_parcel("A", 0.0, 660.0, 2.0)}     # delivered 640, window ends 660
        self.assertEqual(dispatch(parcels, make_context(distances, 600.0)), ["A"])

    def test_dispatches_small_load_when_only_cutoff_slack_is_low(self) -> None:
        distances = make_distances({("HUB", "A"): 100.0})
        parcels = {"A": make_parcel("A", 0.0, 1080.0, 2.0)}
        # Window slack is large; the return would be 10 minutes before 18:00 at t=840.
        self.assertEqual(dispatch(parcels, make_context(distances, 830.0)), [])
        self.assertEqual(dispatch(parcels, make_context(distances, 840.0)), ["A"])

    def test_assigned_parcels_ignored_and_inputs_not_modified(self) -> None:
        distances = make_distances({("HUB", "A"): 10.0})
        taken = make_parcel("A", 0.0, 1070.0, 24.0)
        taken["vehicle_assigned"] = 2
        parcels = {"T": taken, "A": make_parcel("A", 0.0, 1070.0, 24.0)}
        original = copy.deepcopy(parcels)
        self.assertEqual(dispatch(parcels, make_context(distances, 600.0)), ["A"])
        self.assertEqual(parcels, original)


class SimulatorIntegrationTest(unittest.TestCase):
    def test_full_day_valid_and_every_delivery_inside_its_window(self) -> None:
        parcels_csv, dist_csv, config_json = day_input_paths(ROOT / "data", "day_001")
        simulator = Simulator(parcels_csv, dist_csv, config_json, dispatch_policy=dispatch)
        with tempfile.TemporaryDirectory() as folder:
            simulator.run(Path(folder) / "log.txt")  # Raises ValueError on any hard-constraint breach.
        self.assertGreater(len(simulator.delivered), 0)
        for parcel_id in simulator.delivered:
            record = simulator.parcel[parcel_id]
            self.assertGreaterEqual(record["delivery_time"], record["delivery_window_start"] - 1e-9)
            self.assertLessEqual(record["delivery_time"], record["delivery_window_end"] + 1e-9)


if __name__ == "__main__":
    unittest.main()
