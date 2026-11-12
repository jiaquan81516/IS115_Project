"""Where does each policy do well or badly? OTDR by window length and by arrival period, all six policies, days 001-020.
Also compares Hybrid OTDR with Window nearest by arrival hour on the three days where Hybrid scored lower (days 2, 4, 19)."""
import csv, json
from shared_helpers import *
from simulator.loaders import parse_time

POLICIES = ["baseline", "deadline_first", "window_nearest", "hybrid_otdr", "seeded_nn", "batched_nn"]
WL = (("under 1 h", 0, 60), ("1 to 2 h", 60, 120), ("2 to 4 h", 120, 240), ("4 h or more", 240, 1e9))
AP = (("08:00-10:59", 480, 660), ("11:00-12:59", 660, 780), ("15:00-17:59", 900, 1080))

def day_parcels(day):
    pf, _, _ = day_input_paths(PROJ / "data", day)
    return list(csv.DictReader(open(pf, newline="", encoding="utf-8-sig")))

def ontime_map(policy, day, P):
    ev = [json.loads(l) for l in open(PROJ / "results" / policy / day / "log.txt") if l.strip()]
    done = {e["parcel_id"]: e["time"] for e in ev if e["event_type"] == "delivery"}
    out = {}
    for p in P:
        ws, we = parse_time(p["delivery_window_start"]), parse_time(p["delivery_window_end"])
        t = done.get(p["parcel_id"]); out[p["parcel_id"]] = t is not None and ws - 1e-9 <= t <= we + 1e-9
    return out

if __name__ == "__main__":
    res = {pol: {"window": {k: [0, 0] for k, _, _ in WL}, "arrival": {k: [0, 0] for k, _, _ in AP}, "hour": {}} for pol in POLICIES}
    cmp = {"days_2_4_19": {"hybrid_otdr": {}, "window_nearest": {}}, "other_days": {"hybrid_otdr": {}, "window_nearest": {}}, "n_days": {"days_2_4_19": 3, "other_days": 17}}
    for i in range(1, 21):
        day = f"day_{i:03d}"; P = day_parcels(day)
        for pol in POLICIES:
            om = ontime_map(pol, day, P)
            for p in P:
                length = parse_time(p["delivery_window_end"]) - parse_time(p["delivery_window_start"]); a = parse_time(p["arrival_time"]); ok = om[p["parcel_id"]]
                for k, lo, hi in WL:
                    if lo <= length < hi: res[pol]["window"][k][0] += ok; res[pol]["window"][k][1] += 1
                for k, lo, hi in AP:
                    if lo <= a < hi: res[pol]["arrival"][k][0] += ok; res[pol]["arrival"][k][1] += 1
                if pol in ("hybrid_otdr", "window_nearest"):
                    grp = "days_2_4_19" if i in (2, 4, 19) else "other_days"; h = str(int(a // 60))
                    cell = cmp[grp][pol].setdefault(h, [0, 0]); cell[0] += ok; cell[1] += 1
    out = {"otdr_by_window_length_percent": {}, "otdr_by_arrival_period_percent": {}, "hybrid_vs_window_nearest_by_arrival_hour": {}}
    for pol in POLICIES:
        out["otdr_by_window_length_percent"][pol] = {k: round(100 * v[0] / v[1], 2) for k, v in res[pol]["window"].items()}
        out["otdr_by_arrival_period_percent"][pol] = {k: round(100 * v[0] / v[1], 2) for k, v in res[pol]["arrival"].items()}
    out["parcels_per_day_by_window_length"] = {k: res["baseline"]["window"][k][1] / 20 for k in res["baseline"]["window"]}
    out["parcels_per_day_by_arrival_period"] = {k: res["baseline"]["arrival"][k][1] / 20 for k in res["baseline"]["arrival"]}
    for grp in ("days_2_4_19", "other_days"):
        nd = cmp["n_days"][grp]
        out["hybrid_vs_window_nearest_by_arrival_hour"][grp] = {pol: {h: {"on_time_per_day": c[0] / nd, "parcels_per_day": c[1] / nd} for h, c in sorted(cmp[grp][pol].items(), key=lambda x: int(x[0]))} for pol in ("hybrid_otdr", "window_nearest")}
    json.dump(out, open(OUT / "table9_by_window_and_arrival.json", "w"), indent=1)
    for k in ("otdr_by_window_length_percent", "otdr_by_arrival_period_percent"):
        print(k)
        for pol, v in out[k].items(): print(f"  {pol:15s}", v)
    print(out["parcels_per_day_by_window_length"], out["parcels_per_day_by_arrival_period"])
    for grp in ("days_2_4_19", "other_days"):
        print(grp)
        for pol in ("hybrid_otdr", "window_nearest"):
            print("  ", pol, {h: round(v["on_time_per_day"], 1) for h, v in out["hybrid_vs_window_nearest_by_arrival_hour"][grp][pol].items()})
