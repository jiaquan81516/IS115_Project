"""Window-aware greedy policy using a deadline priority queue and nearest choices."""

import heapq
from typing import Dict, List, Optional, Tuple

from simulator.models import Parcel, SimulationContext
from solution.policies.helpers import HUB, all_deliveries_on_time, waiting_ids


def dispatch(parcel: Dict[str, Parcel], context: SimulationContext) -> List[str]:
    """Choose on-time parcels by deadline, using distance to break similar urgency."""

    queue: List[Tuple[float, float, float, str]] = []
    for parcel_id in waiting_ids(parcel):
        record = parcel[parcel_id]
        heapq.heappush(queue, (
            record["delivery_window_end"],
            record["delivery_window_start"],
            record["arrival_time"],
            parcel_id,
        ))

    route: List[str] = []
    distances = context["travel_distance"]
    while queue:
        location = parcel[route[-1]]["delivery_location_id"] if route else HUB
        examined: List[Tuple[float, float, float, str]] = []
        best: Optional[
            Tuple[Tuple[float, float, float, str], Tuple[float, float, float, str]]
        ] = None
        while queue:
            item = heapq.heappop(queue)
            parcel_id = item[3]
            if all_deliveries_on_time(route + [parcel_id], parcel, context):
                score = (
                    item[0],
                    distances[location][parcel[parcel_id]["delivery_location_id"]],
                    item[1],
                    parcel_id,
                )
                if best is None or score < best[0]:
                    if best is not None:
                        examined.append(best[1])
                    best = (score, item)
                    continue
            examined.append(item)
        for item in examined:
            heapq.heappush(queue, item)
        if best is None:
            break
        route.append(best[1][3])
    return route
