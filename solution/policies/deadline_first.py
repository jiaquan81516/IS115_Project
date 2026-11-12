"""Greedy earliest-deadline-first policy used as the first improvement."""

from typing import Dict, List

from simulator.models import Parcel, SimulationContext
from solution.policies.helpers import hard_feasible, waiting_ids


def dispatch(parcel: Dict[str, Parcel], context: SimulationContext) -> List[str]:
    """Append parcels by earliest window end whenever hard constraints permit."""

    waiting = sorted(
        waiting_ids(parcel),
        key=lambda parcel_id: (
            parcel[parcel_id]["delivery_window_end"],
            parcel[parcel_id]["delivery_window_start"],
            parcel[parcel_id]["arrival_time"],
            parcel_id,
        ),
    )
    route: List[str] = []
    for parcel_id in waiting:
        candidate = route + [parcel_id]
        if hard_feasible(candidate, parcel, context):
            route = candidate
    return route
