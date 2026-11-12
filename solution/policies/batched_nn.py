"""Batched seeded nearest-neighbour policy: wait for a fuller trip unless a deadline forces dispatch."""

import heapq
from typing import Dict, List, Optional, Tuple

from simulator.models import Parcel, SimulationContext
from solution.policies.helpers import (
    HUB, TOLERANCE, all_deliveries_on_time, route_details, waiting_ids,
)

# ###############xxxxxxxxx###############
# BATCHED SEEDED NEAREST-NEIGHBOUR (new policy)
#
# Business rules and how each one is met:
#   * Capacity 30, range 320 km, return by 18:00 (hard): every appended stop is
#     checked, so a returned route never breaks them.
#   * Preferred windows (soft, but they are what OTDR measures): a stop is only
#     appended if its predicted delivery time lies inside its own window.
#   * Vehicle time is scarce (30-minute loading + driving): routes should be
#     short and well filled, and a vehicle should not leave nearly empty while a
#     deadline still allows waiting.
#
# Each planning call:
#   1. Seed   - min-heap on window end: the most urgent parcel that is on time as
#               the first stop.
#   2. Fill   - greedy nearest neighbour: append the closest waiting parcel that
#               keeps every rule above satisfied (ties: earlier window end).
#   3. Improve- 2-opt: reverse a segment only if the route gets shorter and every
#               stop stays inside its window.
#   4. Batch  - dispatch if the load is at least LOAD_TARGET of capacity, or if
#               waiting one more round could break a deadline (window slack or
#               return-cutoff slack at or below its margin). Otherwise return []
#               and re-plan in 10 minutes with newly arrived parcels.
#
# Complexity per call (n waiting parcels, m stops in the route): seed heap
# O(n log n); fill O(m * n) because appending only needs a check of the new stop;
# 2-opt O(m^3) per improving pass. Extra space O(n + m).
# Trade-off: nearest-neighbour gives up deadline order inside a route, and the
# three constants below were chosen on days 001-010 and synthetic days built
# from them only.
# ###############xxxxxxxxx###############

LOAD_TARGET = 0.80       # dispatch at once when the load reaches this share of capacity
WINDOW_MARGIN = 30.0     # minutes of window slack at or below which waiting is unsafe
CUTOFF_MARGIN = 10.0     # minutes of return-cutoff slack at or below which waiting is unsafe


def _build_route(parcel: Dict[str, Parcel], context: SimulationContext) -> List[str]:
    """Urgent seed from a min-heap, then nearest feasible neighbour."""

    distances = context["travel_distance"]
    departure = context["current_time"] + context["departure_delay"]
    capacity = context["capacity"]
    max_distance = context["max_trip_distance_km"]
    cutoff = context["return_cutoff"]

    def extension(
        location: str, travelled: float, load: float, parcel_id: str
    ) -> Optional[float]:
        """Return km travelled after appending the parcel, or None if it is not allowed."""

        record = parcel[parcel_id]
        destination = record["delivery_location_id"]
        outbound = travelled + distances[location][destination]
        round_trip = outbound + distances[destination][HUB]
        arrival = departure + outbound
        if (
            load + record["size"] <= capacity + TOLERANCE
            and round_trip <= max_distance + TOLERANCE
            and departure + round_trip <= cutoff + TOLERANCE
            and record["delivery_window_start"] - TOLERANCE <= arrival
            <= record["delivery_window_end"] + TOLERANCE
        ):
            return outbound
        return None

    waiting = waiting_ids(parcel)
    seeds: List[Tuple[float, str]] = [
        (parcel[parcel_id]["delivery_window_end"], parcel_id) for parcel_id in waiting
    ]
    heapq.heapify(seeds)
    route: List[str] = []
    travelled = 0.0
    while seeds:
        _, parcel_id = heapq.heappop(seeds)
        outbound = extension(HUB, 0.0, 0.0, parcel_id)
        if outbound is not None:
            route.append(parcel_id)
            travelled = outbound
            break
    if not route:
        return []

    load = float(parcel[route[0]]["size"])
    location = parcel[route[0]]["delivery_location_id"]
    remaining = set(waiting)
    remaining.discard(route[0])
    while remaining:
        best: Optional[Tuple[Tuple[float, float, str], float]] = None
        for parcel_id in remaining:
            outbound = extension(location, travelled, load, parcel_id)
            if outbound is None:
                continue
            record = parcel[parcel_id]
            score = (
                distances[location][record["delivery_location_id"]],
                record["delivery_window_end"],
                parcel_id,
            )
            if best is None or score < best[0]:
                best = (score, outbound)
        if best is None:
            break
        parcel_id = best[0][2]
        route.append(parcel_id)
        remaining.discard(parcel_id)
        load += parcel[parcel_id]["size"]
        travelled = best[1]
        location = parcel[parcel_id]["delivery_location_id"]
    return route


def _two_opt(
    route: List[str], parcel: Dict[str, Parcel], context: SimulationContext
) -> List[str]:
    """Shorten the route with 2-opt reversals that keep every stop inside its window."""

    best = list(route)
    _, best_distance, _, _ = route_details(best, parcel, context)
    improved = True
    while improved:
        improved = False
        for start in range(len(best) - 1):
            for end in range(start + 2, len(best) + 1):
                candidate = best[:start] + list(reversed(best[start:end])) + best[end:]
                if not all_deliveries_on_time(candidate, parcel, context):
                    continue
                _, distance, _, _ = route_details(candidate, parcel, context)
                if distance + TOLERANCE < best_distance:
                    best = candidate
                    best_distance = distance
                    improved = True
                    break
            if improved:
                break
    return best


def dispatch(parcel: Dict[str, Parcel], context: SimulationContext) -> List[str]:
    """Build a short on-time route and dispatch it once it is full or a deadline forces it."""

    route = _build_route(parcel, context)
    if not route:
        return []
    route = _two_opt(route, parcel, context)

    load, _, delivery_times, return_time = route_details(route, parcel, context)
    window_slack = min(
        parcel[parcel_id]["delivery_window_end"] - delivery_times[parcel_id]
        for parcel_id in route
    )
    cutoff_slack = context["return_cutoff"] - return_time
    if (
        load < context["capacity"] * LOAD_TARGET
        and window_slack > WINDOW_MARGIN
        and cutoff_slack > CUTOFF_MARGIN
    ):
        return []
    return route

# ###############xxxxxxxxx###############
# END OF NEW POLICY: batched seeded nearest-neighbour
# ###############xxxxxxxxx###############
