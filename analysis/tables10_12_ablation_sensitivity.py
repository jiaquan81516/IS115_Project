"""Ablation (what each part adds) and sensitivity of the three Batched NN constants, days 001-020."""
import json, sys
from multiprocessing import Pool
from shared_helpers import *

def noop(route, parcel, context): return route

# name -> (module, overrides)
VARIANTS = {
  "hybrid_otdr (as submitted)":            ("hybrid_otdr", {}),
  "hybrid_otdr without 2-opt":             ("hybrid_otdr", {"_two_opt": noop}),
  "seeded_nn (no hold rule)":              ("seeded_nn", {}),
  "batched_nn without 2-opt":              ("batched_nn", {"_two_opt": noop}),
  "batched_nn, hold on window slack only": ("batched_nn", {"CUTOFF_MARGIN": -1e9}),
  "batched_nn (as submitted)":             ("batched_nn", {}),
}
SENS = [("LOAD_TARGET", v) for v in (0.5, 0.6, 0.7, 0.8, 0.9, 1.0)] \
     + [("WINDOW_MARGIN", v) for v in (10.0, 20.0, 30.0, 45.0, 60.0)] \
     + [("CUTOFF_MARGIN", v) for v in (0.0, 10.0, 20.0, 40.0)]

def job(a):
    kind, label, mod, ov, day = a
    return kind, label, day, run_day(fresh_policy(mod, **ov), f"day_{day:03d}")

if __name__ == "__main__":
    jobs = []
    for label, (mod, ov) in VARIANTS.items():
        for d in range(1, 21): jobs.append(("ablation", label, mod, ov, d))
    for k, v in SENS:
        for d in range(1, 21): jobs.append(("sens", f"{k}={v}", "batched_nn", {k: v}, d))
    with Pool(4) as p: res = p.map(job, jobs, chunksize=5)
    agg = {}
    for kind, label, day, m in res:
        agg.setdefault((kind, label), {})[day] = m
    out = {"ablation": {}, "sensitivity": {}}
    for (kind, label), byday in agg.items():
        days = sorted(byday)
        row = {k: mean(byday[d][k] for d in days) for k in ("otdr_percent", "total_distance_km", "average_capacity_utilization_percent", "number_of_trips")}
        row["otdr_dev"] = mean(byday[d]["otdr_percent"] for d in days[:10]); row["otdr_eval"] = mean(byday[d]["otdr_percent"] for d in days[10:])
        row["otdr_by_day"] = [byday[d]["otdr_percent"] for d in days]
        out["ablation" if kind == "ablation" else "sensitivity"][label] = row
    json.dump(out, open(OUT / "tables10_12_ablation_sensitivity.json", "w"), indent=1)
    for kind in out:
        for label, r in out[kind].items():
            print(f"{kind:11s} {label:42s} OTDR {r['otdr_percent']:.2f}  dev {r['otdr_dev']:.2f} eval {r['otdr_eval']:.2f}  km {r['total_distance_km']:.0f} util {r['average_capacity_utilization_percent']:.1f} trips {r['number_of_trips']:.1f}")
