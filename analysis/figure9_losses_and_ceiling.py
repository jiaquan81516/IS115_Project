"""Where Batched NN loses parcels (by arrival hour, window length, distance) and the individual-feasibility ceiling."""
import csv, json
from shared_helpers import *
from simulator.loaders import parse_time

def load_day(day):
    pf, df, cf = day_input_paths(PROJ / "data", day)
    P = list(csv.DictReader(open(pf, newline="", encoding="utf-8-sig")))
    dist = {(r["location_1"], r["location_2"]): float(r["dist"]) for r in csv.DictReader(open(df, newline="", encoding="utf-8-sig"))}
    return P, dist

def feasible_alone(p, dist):
    """Could ONE vehicle, planned at some 10-minute tick after arrival, deliver this parcel inside its window?"""
    a, ws, we = parse_time(p["arrival_time"]), parse_time(p["delivery_window_start"]), parse_time(p["delivery_window_end"])
    loc = p["delivery_location_id"]; d = dist[("HUB", loc)]; rt = d + dist[(loc, "HUB")]
    if rt > 320 + 1e-9: return False
    for t in TICKS:
        if t < a: continue
        arr = t + 30 + d
        if ws <= arr <= we and t + 30 + rt <= 1080: return True
    return False

def bucket(v, edges, labels):
    for e, l in zip(edges, labels):
        if v < e: return l
    return labels[-1]

if __name__ == "__main__":
    pol = "batched_nn"
    hour_tot, hour_lost, hour_lost_feas = {}, {}, {}
    wl_tot, wl_lost, dist_tot, dist_lost = {}, {}, {}, {}
    ceil, lost_total, lost_feasible = [], 0, 0
    for i in range(1, 21):
        day = f"day_{i:03d}"; P, dist = load_day(day)
        ev = [json.loads(l) for l in open(PROJ / "results" / pol / day / "log.txt") if l.strip()]
        done = {e["parcel_id"]: e for e in ev if e["event_type"] == "delivery"}
        feas = 0
        for p in P:
            a, ws, we = parse_time(p["arrival_time"]), parse_time(p["delivery_window_start"]), parse_time(p["delivery_window_end"])
            h = int(a // 60); e = done.get(p["parcel_id"])
            ontime = e is not None and ws - 1e-9 <= e["time"] <= we + 1e-9
            f = feasible_alone(p, dist); feas += f
            wl = bucket(we - ws, (60, 120, 240), ("<1 h", "1-2 h", "2-4 h", ">=4 h"))
            dd = bucket(dist[("HUB", p["delivery_location_id"])], (40, 80, 120), ("<40 km", "40-80 km", "80-120 km", ">=120 km"))
            for tot, lost, k in ((hour_tot, hour_lost, h), (wl_tot, wl_lost, wl), (dist_tot, dist_lost, dd)):
                tot[k] = tot.get(k, 0) + 1
                if not ontime: lost[k] = lost.get(k, 0) + 1
            if not ontime:
                lost_total += 1; lost_feasible += f
                if f: hour_lost_feas[h] = hour_lost_feas.get(h, 0) + 1
        ceil.append(100 * feas / len(P))
    out = {"policy": pol, "days": 20,
           "ceiling_percent_mean": mean(ceil), "ceiling_by_day": ceil,
           "not_on_time_per_day": lost_total / 20, "of_which_individually_feasible_per_day": lost_feasible / 20,
           "by_arrival_hour": {str(k): {"parcels_per_day": hour_tot[k] / 20, "not_on_time_per_day": hour_lost.get(k, 0) / 20, "lost_but_feasible_per_day": hour_lost_feas.get(k, 0) / 20} for k in sorted(hour_tot)},
           "by_window_length": {k: {"parcels_per_day": wl_tot[k] / 20, "not_on_time_per_day": wl_lost.get(k, 0) / 20, "share_lost": wl_lost.get(k, 0) / wl_tot[k]} for k in wl_tot},
           "by_distance_from_hub": {k: {"parcels_per_day": dist_tot[k] / 20, "not_on_time_per_day": dist_lost.get(k, 0) / 20, "share_lost": dist_lost.get(k, 0) / dist_tot[k]} for k in dist_tot}}
    json.dump(out, open(OUT / "figure9_losses_and_ceiling.json", "w"), indent=1)
    print(json.dumps(out, indent=1)[:3500])
