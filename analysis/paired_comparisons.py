"""Report Table 5. Paired day-by-day OTDR differences between policies, with 95% t-intervals.

Reads results/summary.csv (written by solution.summarize_results), so run that first.
Every policy ran on the same 20 days, so the comparison is paired: for each day take
OTDR(first policy) - OTDR(second policy), then report the mean difference, a 95% confidence
interval (mean +/- t * sd / sqrt(n), sample sd) and how many days the first policy won.

Standard library only. Writes analysis/output/paired_comparisons.json.
"""
import csv, json, math, os, statistics
from pathlib import Path

PROJ = Path(os.environ.get("PROJ", ".")).resolve()
OUT = Path(os.environ.get("ANALYSIS_OUT", PROJ / "analysis" / "output"))
OUT.mkdir(parents=True, exist_ok=True)

# Two-sided 95% critical values of Student's t (the standard library has no t distribution).
T_95 = {9: 2.262157, 19: 2.093024}

PAIRS = [  # (first, second): each step of the development sequence, then the headline comparisons
    ("deadline_first", "baseline"),
    ("window_nearest", "baseline"),
    ("hybrid_otdr", "window_nearest"),
    ("seeded_nn", "hybrid_otdr"),
    ("batched_nn", "seeded_nn"),
    ("batched_nn", "hybrid_otdr"),
    ("batched_nn", "baseline"),
]
SPLITS = {
    "all_days_001_020": [f"day_{i:03d}" for i in range(1, 21)],
    "evaluation_days_011_020": [f"day_{i:03d}" for i in range(11, 21)],
}


def load_otdr():
    """Return {policy: {day: OTDR %}} from results/summary.csv."""
    otdr = {}
    with open(PROJ / "results" / "summary.csv", newline="", encoding="utf-8") as stream:
        for row in csv.DictReader(stream):
            otdr.setdefault(row["policy"], {})[row["day"]] = float(row["otdr_percent"])
    return otdr


def compare(otdr, first, second, days):
    diffs = [otdr[first][d] - otdr[second][d] for d in days]
    n = len(diffs)
    mean = statistics.mean(diffs)
    half_width = T_95[n - 1] * statistics.stdev(diffs) / math.sqrt(n)
    return {
        "days": n,
        "mean_difference_pts": round(mean, 2),
        "ci95_low": round(mean - half_width, 2),
        "ci95_high": round(mean + half_width, 2),
        "days_first_better": sum(d > 0 for d in diffs),
        "days_equal": sum(d == 0 for d in diffs),
        "days_first_worse": sum(d < 0 for d in diffs),
        "largest_loss_pts": round(min(diffs), 2),
    }


if __name__ == "__main__":
    otdr = load_otdr()
    out = {split: {f"{a} - {b}": compare(otdr, a, b, days) for a, b in PAIRS} for split, days in SPLITS.items()}
    all_days = SPLITS["all_days_001_020"]
    out["days_batched_nn_is_best_or_tied"] = sum(
        otdr["batched_nn"][d] >= max(otdr[p][d] for p in otdr) for d in all_days
    )
    out["days_batched_nn_is_beaten"] = [
        d for d in all_days if otdr["batched_nn"][d] < max(otdr[p][d] for p in otdr)
    ]
    json.dump(out, open(OUT / "paired_comparisons.json", "w"), indent=1)
    for split in SPLITS:
        print(split)
        for label, r in out[split].items():
            print(f"  {label:32s} {r['mean_difference_pts']:+6.2f} pts  [{r['ci95_low']:+.2f}, {r['ci95_high']:+.2f}]  "
                  f"better {r['days_first_better']:2d}  equal {r['days_equal']}  worse {r['days_first_worse']}")
    print("Batched NN best or tied on", out["days_batched_nn_is_best_or_tied"], "of 20 days; beaten on", out["days_batched_nn_is_beaten"])
