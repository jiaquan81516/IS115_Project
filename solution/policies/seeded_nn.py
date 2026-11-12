"""Seeded nearest-neighbour OTDR policy: a geography-first alternative to hybrid_otdr."""

import heapq
from typing import Dict, List, Optional, Tuple

from simulator.models import Parcel, SimulationContext
from solution.policies.helpers import (
    HUB, TOLERANCE, all_deliveries_on_time, route_details, waiting_ids,
)
# The 2-opt routine and the batching constants are reused unchanged, so the only
# difference from hybrid_otdr is how the route is constructed.
from solution.policies.hybrid_otdr import (
    BATCH_LOAD_RATIO, LATEST_BATCHING_TIME, SAFE_SLACK_MINUTES, _two_opt,
)

# ##############################
# SEEDED NEAREST-NEIGHBOUR FILL (new policy)
#
# hybrid_otdr / window_nearest build a route by repeatedly taking the feasible
# parcel with the earliest window end. Distance only breaks exact deadline ties,
# so routes zig-zag between destinations and use a lot of vehicle time. With ten
# vehicles, 30-minute loading and bursty arrivals, vehicle time is the scarce
# resource around midday, and most lost on-time parcels had no idle vehicle at
# all during their feasible dispatch window.
#
# This policy changes only the construction rule:
#   1. Seed: a min-heap on window end gives the most urgent parcel that can be
#      delivered inside its window as the FIRST stop.
#   2. Fill: greedy nearest neighbour. Repeatedly append the waiting parcel that
#      is closest to the current stop, among parcels whose predicted delivery
#      stays inside its own window and that keep capacity, 320 km range and the
#      18:00 return cutoff satisfied. Ties go to the earlier window end.
#   3. Improve: the same feasible 2-opt as hybrid_otdr (a reversal is accepted
#      only if shorter and every stop stays inside its window).
#   4. Batch: the same rule as hybrid_otdr (hold small, non-urgent loads before
#      16:00), with the same constants. No new constants are introduced.
#
# Appending a stop never changes the arrival time of earlier stops, so checking
# the new stop alone is exactly equivalent to re-checking the whole route. That
# gives an O(1) test per candidate instead of O(m).
#
# Time per dispatch call: O(n log n) for the seed heap, O(m * n) for the fill
# and the 2-opt cost inherited from hybrid_otdr. Extra space: O(n + m).
# Trade-off: deadline order inside a route is given up. An earlier-deadline
# parcel that is far from the current stop may be left for a later vehicle.
# ##############################


def _build_route(parcel: Dict[str, Parcel], context: SimulationContext) -> List[str]:
    """Build one on-time route: urgent seed, then nearest feasible neighbour."""

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


def dispatch(parcel: Dict[str, Parcel], context: SimulationContext) -> List[str]:
    """Build a nearest-neighbour on-time route, shorten it, and batch small safe loads."""

    route = _build_route(parcel, context)
    if not route:
        return []
    route = _two_opt(route, parcel, context)
    if not all_deliveries_on_time(route, parcel, context):
        return []  # Defensive guard; _build_route and _two_opt already enforce this.

    load, _, delivery_times, _ = route_details(route, parcel, context)
    minimum_slack = min(
        parcel[parcel_id]["delivery_window_end"] - delivery_times[parcel_id]
        for parcel_id in route
    )
    if (
        context["current_time"] < LATEST_BATCHING_TIME
        and load < context["capacity"] * BATCH_LOAD_RATIO
        and minimum_slack > SAFE_SLACK_MINUTES
    ):
        return []
    return route

# ##############################
# END OF NEW POLICY: seeded nearest-neighbour fill
# ##############################
