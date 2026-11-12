"""Tests for the seeded nearest-neighbour policy: construction, hard limits, batching."""

import copy
import tempfile
import unittest
from pathlib import Path

from simulator.loaders import day_input_paths
from simulator.simulator import Simulator
from solution.policies.helpers import all_deliveries_on_time
from solution.policies.seeded_nn import _build_route, dispatch

ROOT = Path(__file__).resolve().parents[1]


def make_distances(pairs):
    """Build a symmetric directed distance table from {(a, b): km}."""

    names = {name for pair in pairs for name in pair} | {"HUB"}
    table = {a: {b: 0.0 for b in names} for a in names}
    for (a, b), km in pairs.items():
        table[a][b] = km
        table[b][a] = km
    return table


def make_context(distances, current_time=480.0):
    return {
        "current_time": current_time,
        "vehicle_id": 1,
        "capacity": 30.0,
        "travel_distance": distances,
        "departure_delay": 30.0,
        "return_cutoff": 1080.0,
        "max_trip_distance_km": 320.0,
        "fleet": {1: {"available_at": current_time, "max_trip_distance_km": 320.0}},
    }


def make_parcel(location, start, end, size=1.0):
    return {"arrival_time": 480.0, "delivery_location_id": location,
            "delivery_window_start": start, "delivery_window_end": end,
            "size": size, "delivery_time": None, "vehicle_assigned": None, "trip_id": None}


class ConstructionTests(unittest.TestCase):
    def test_fills_with_nearest_neighbour_not_earliest_deadline(self) -> None:
        distances = make_distances({
            ("HUB", "S"): 10.0, ("HUB", "X"): 12.0, ("HUB", "Y"): 11.0,
            ("S", "X"): 20.0, ("S", "Y"): 1.0, ("X", "Y"): 20.0,
        })
        parcels = {
            "S": make_parcel("S", 0.0, 600.0),
            "X": make_parcel("X", 0.0, 650.0),  # earlier deadline than Y, but farther from S
            "Y": make_parcel("Y", 0.0, 700.0),
        }
        route = _build_route(parcels, make_context(distances))
        self.assertEqual(route, ["S", "Y", "X"])

    def test_seed_must_be_on_time_as_first_stop(self) -> None:
        distances = make_distances({("HUB", "E"): 10.0, ("HUB", "S"): 10.0, ("E", "S"): 30.0})
        parcels = {
            "E": make_parcel("E", 600.0, 700.0),  # earliest deadline, but early as the first stop
            "S": make_parcel("S", 500.0, 800.0),
        }
        route = _build_route(parcels, make_context(distances))
        self.assertEqual(route[0], "S")
        self.assertTrue(all_deliveries_on_time(route, parcels, make_context(distances)))


class HardConstraintTests(unittest.TestCase):
    def test_capacity_is_never_exceeded(self) -> None:
        distances = make_distances({("HUB", "A"): 10.0})
        parcels = {name: make_parcel("A", 0.0, 1000.0, 15.0) for name in ("P1", "P2", "P3")}
        route = dispatch(parcels, make_context(distances, 600.0))
        self.assertEqual(len(route), 2)

    def test_out_of_range_parcel_is_excluded(self) -> None:
        distances = make_distances({("HUB", "A"): 10.0, ("HUB", "F"): 200.0, ("A", "F"): 190.0})
        parcels = {"A": make_parcel("A", 0.0, 1000.0, 15.0), "F": make_parcel("F", 0.0, 1070.0, 15.0)}
        route = _build_route(parcels, make_context(distances, 600.0))
        self.assertEqual(route, ["A"])

    def test_return_cutoff_is_respected(self) -> None:
        distances = make_distances({("HUB", "A"): 10.0})
        parcels = {"A": make_parcel("A", 0.0, 1100.0, 20.0)}
        # Departs 1070 and would return at 1090, after the 18:00 cutoff.
        self.assertEqual(dispatch(parcels, make_context(distances, 1040.0)), [])


class BatchingAndInterfaceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.distances = make_distances({("HUB", "A"): 10.0})

    def test_holds_small_safe_load_before_cutoff_hour(self) -> None:
        parcels = {"A": make_parcel("A", 0.0, 1070.0, 2.0)}
        self.assertEqual(dispatch(parcels, make_context(self.distances, 600.0)), [])

    def test_dispatches_small_load_late_in_the_day(self) -> None:
        parcels = {"A": make_parcel("A", 0.0, 1070.0, 2.0)}
        self.assertEqual(dispatch(parcels, make_context(self.distances, 1000.0)), ["A"])

    def test_dispatches_when_load_reaches_batching_ratio(self) -> None:
        parcels = {"A": make_parcel("A", 0.0, 1070.0, 15.0)}
        self.assertEqual(dispatch(parcels, make_context(self.distances, 600.0)), ["A"])

    def test_assigned_parcels_are_ignored_and_inputs_not_modified(self) -> None:
        taken = make_parcel("A", 0.0, 1070.0, 15.0)
        taken["vehicle_assigned"] = 2
        parcels = {"T": taken, "A": make_parcel("A", 0.0, 1070.0, 15.0)}
        original = copy.deepcopy(parcels)
        self.assertEqual(dispatch(parcels, make_context(self.distances, 600.0)), ["A"])
        self.assertEqual(parcels, original)


class SimulatorIntegrationTest(unittest.TestCase):
    def test_full_day_runs_without_simulator_validation_errors(self) -> None:
        parcels_csv, dist_csv, config_json = day_input_paths(ROOT / "data", "day_001")
        simulator = Simulator(parcels_csv, dist_csv, config_json, dispatch_policy=dispatch)
        with tempfile.TemporaryDirectory() as folder:
            simulator.run(Path(folder) / "log.txt")  # Raises ValueError on any hard-constraint breach.
        self.assertGreater(len(simulator.delivered), 0)


if __name__ == "__main__":
    unittest.main()
