"""OTDR-focused hybrid: urgent-nearest selection, 2-opt and safe batching."""

from typing import Dict, List

from simulator.models import Parcel, SimulationContext
from solution.policies.helpers import all_deliveries_on_time, route_details
from solution.policies.window_nearest import dispatch as build_window_route

BATCH_LOAD_RATIO = 0.40
SAFE_SLACK_MINUTES = 60.0
LATEST_BATCHING_TIME = 16 * 60.0
TOLERANCE = 1e-9


def _two_opt(
    route: List[str], parcel: Dict[str, Parcel], context: SimulationContext
) -> List[str]:
    """Shorten a route with feasible 2-opt reversals while preserving on-time delivery."""

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
    """Build an on-time route, shorten it, and wait only when batching is safe."""

    route = build_window_route(parcel, context)
    if not route:
        return []
    route = _two_opt(route, parcel, context)

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
