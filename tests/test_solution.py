"""Focused correctness tests for the OTDR monitor and window-aware policy."""

import copy
import unittest

from solution.performance_monitor import calculate_metrics
from solution.policies.window_nearest import dispatch


class PerformanceMonitorTests(unittest.TestCase):
    def test_counts_on_time_early_late_and_undelivered(self) -> None:
        parcels = [
            {"parcel_id": "A", "arrival_time": "08:00", "delivery_location_id": "L1",
             "delivery_window_start": "09:00", "delivery_window_end": "10:00", "size": "1"},
            {"parcel_id": "B", "arrival_time": "08:00", "delivery_location_id": "L2",
             "delivery_window_start": "09:00", "delivery_window_end": "10:00", "size": "1"},
            {"parcel_id": "C", "arrival_time": "08:00", "delivery_location_id": "L3",
             "delivery_window_start": "09:00", "delivery_window_end": "10:00", "size": "1"},
            {"parcel_id": "D", "arrival_time": "08:00", "delivery_location_id": "L4",
             "delivery_window_start": "09:00", "delivery_window_end": "10:00", "size": "1"},
        ]
        distances = []
        for location in ("L1", "L2", "L3"):
            distances.extend([
                {"location_1": "HUB", "location_2": location, "dist": "10"},
                {"location_1": location, "location_2": "HUB", "dist": "10"},
            ])
        events = [
            {"event_type": "hub_departure", "time": 530, "vehicle_id": 1, "trip_id": 1},
            {"event_type": "delivery", "time": 570, "vehicle_id": 1, "trip_id": 1, "parcel_id": "A"},
            {"event_type": "hub_departure", "time": 520, "vehicle_id": 2, "trip_id": 1},
            {"event_type": "delivery", "time": 530, "vehicle_id": 2, "trip_id": 1, "parcel_id": "B"},
            {"event_type": "hub_departure", "time": 600, "vehicle_id": 3, "trip_id": 1},
            {"event_type": "delivery", "time": 610, "vehicle_id": 3, "trip_id": 1, "parcel_id": "C"},
        ]
        result = calculate_metrics(
            parcels, distances, {"capacity": 30}, events
        )
        self.assertEqual(result["on_time_deliveries"], 1)
        self.assertEqual(result["early_deliveries"], 1)
        self.assertEqual(result["late_deliveries"], 1)
        self.assertEqual(result["undelivered_parcels"], 1)
        self.assertEqual(result["otdr_percent"], 25.0)


class WindowNearestTests(unittest.TestCase):
    def context(self, current_time: float):
        return {
            "current_time": current_time,
            "vehicle_id": 1,
            "capacity": 30.0,
            "travel_distance": {"HUB": {"HUB": 0.0, "L1": 10.0},
                                "L1": {"HUB": 10.0, "L1": 0.0}},
            "departure_delay": 30.0,
            "return_cutoff": 1080.0,
            "max_trip_distance_km": 320.0,
            "fleet": {1: {"available_at": current_time, "max_trip_distance_km": 320.0}},
        }

    def test_waits_when_delivery_would_be_early(self) -> None:
        parcels = {"A": {"arrival_time": 480.0, "delivery_location_id": "L1",
                         "delivery_window_start": 600.0, "delivery_window_end": 700.0,
                         "size": 1.0, "delivery_time": None,
                         "vehicle_assigned": None, "trip_id": None}}
        original = copy.deepcopy(parcels)
        self.assertEqual(dispatch(parcels, self.context(480.0)), [])
        self.assertEqual(dispatch(parcels, self.context(560.0)), ["A"])
        self.assertEqual(parcels, original)


if __name__ == "__main__":
    unittest.main()
