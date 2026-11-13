"""Report Table 3. Run time against demand volume: day 001 duplicated x1, x2, x4, x8 (same fleet), sequential timing."""
import csv, json, shutil, tempfile, time
from shared_helpers import *
from solution.policies.helpers import waiting_ids

def make_synthetic(factor, root):
    root = Path(root) / f"x{factor}"; (root / "demand").mkdir(parents=True, exist_ok=True)
    shutil.copy(PROJ / "data" / "dist.csv", root / "dist.csv"); shutil.copy(PROJ / "data" / "config.json", root / "config.json")
    rows = list(csv.DictReader(open(PROJ / "data" / "demand" / "day_001.csv", newline="", encoding="utf-8-sig")))
    with open(root / "demand" / "day_001.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader()
        for k in range(factor):
            for r in rows:
                r2 = dict(r); r2["parcel_id"] = f"{r['parcel_id']}_{k}" if k else r["parcel_id"]; w.writerow(r2)
    return root

if __name__ == "__main__":
    out = {}
    for factor in (1, 2, 4, 8):
        root = make_synthetic(factor, Path(tempfile.gettempdir()) / "is115_synthetic_days")
        with open(root / "demand" / "day_001.csv", newline="") as f: n_parcels = sum(1 for _ in csv.DictReader(f))
        for name in ("baseline", "hybrid_otdr", "batched_nn"):
            calls = []
            base = fresh_policy(name)
            def timed(parcel, context, base=base, calls=calls):
                t0 = time.perf_counter(); r = base(parcel, context); calls.append((len(waiting_ids(parcel)), time.perf_counter() - t0)); return r
            m = run_day(timed, "day_001", data=root)
            out.setdefault(name, {})[factor] = {"parcels": n_parcels, "seconds": m["seconds"], "calls": len(calls),
                "max_waiting": max(c[0] for c in calls), "mean_ms_per_call": 1000 * mean(c[1] for c in calls), "max_ms_per_call": 1000 * max(c[1] for c in calls)}
            print(name, factor, out[name][factor], flush=True)
    json.dump(out, open(OUT / "runtime_scalability.json", "w"), indent=1)
