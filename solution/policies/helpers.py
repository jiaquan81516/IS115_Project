"""Shared route calculations for the experimental dispatch policies."""

import math
from typing import Dict, List, Tuple

from simulator.models import Parcel, SimulationContext

HUB = "HUB"
TOLERANCE = 1e-9


def waiting_ids(parcel: Dict[str, Parcel]) -> List[str]:
    """Return IDs of arrived parcels that have not been assigned or delivered."""

    return [
        parcel_id
        for parcel_id, record in parcel.items()
        if record["vehicle_assigned"] is None and record["delivery_time"] is None
    ]


def route_details(
    route: List[str], parcel: Dict[str, Parcel], context: SimulationContext
) -> Tuple[float, float, Dict[str, float], float]:
    """Return load, distance, delivery times and hub-return time for a route."""

    departure = context["current_time"] + context["departure_delay"]
    distances = context["travel_distance"]
    load = math.fsum(parcel[parcel_id]["size"] for parcel_id in route)
    travelled = 0.0
    location = HUB
    delivery_times: Dict[str, float] = {}
    for parcel_id in route:
        destination = parcel[parcel_id]["delivery_location_id"]
        travelled += distances[location][destination]
        delivery_times[parcel_id] = departure + travelled
        location = destination
    total_distance = travelled + distances[location][HUB]
    return_time = departure + total_distance
    return load, total_distance, delivery_times, return_time


def hard_feasible(
    route: List[str], parcel: Dict[str, Parcel], context: SimulationContext
) -> bool:
    """Whether a route satisfies capacity, range and the hub-return cutoff."""

    load, distance, _, return_time = route_details(route, parcel, context)
    return (
        load <= context["capacity"] + TOLERANCE
        and distance <= context["max_trip_distance_km"] + TOLERANCE
        and return_time <= context["return_cutoff"] + TOLERANCE
    )


def all_deliveries_on_time(
    route: List[str], parcel: Dict[str, Parcel], context: SimulationContext
) -> bool:
    """Whether every selected parcel is predicted inside its preferred window."""

    if not hard_feasible(route, parcel, context):
        return False
    _, _, delivery_times, _ = route_details(route, parcel, context)
    return all(
        parcel[parcel_id]["delivery_window_start"] - TOLERANCE
        <= delivery_times[parcel_id]
        <= parcel[parcel_id]["delivery_window_end"] + TOLERANCE
        for parcel_id in route
    )
