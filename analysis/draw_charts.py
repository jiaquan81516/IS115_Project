"""Redraw the report's data charts from the result files (needs matplotlib: pip install matplotlib).

Run from the project root, after the experiments and analysis/figure9_losses_and_ceiling.py:

    python3 analysis/draw_charts.py

Report Figure 3 -> fig1_otdr_per_day.png        (source: results/summary.csv and the OTDR ceiling)
Report Figure 4 -> fig2_losses_by_arrival_hour.png (source: analysis/output/figure9_losses_and_ceiling.json)
The five fig_*.png bar charts (OTDR, delivery rate, distance, utilisation, on-time deliveries) are extra.

PNG files are written to analysis/figures/ (git-ignored). Add --show to also open them in windows.
"""
import csv, json, sys
from pathlib import Path
import matplotlib
if "--show" not in sys.argv: matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "analysis" / "figures"; OUT.mkdir(parents=True, exist_ok=True)
S = json.load(open(ROOT / "results" / "summary.json"))
LC = json.load(open(ROOT / "analysis" / "output" / "figure9_losses_and_ceiling.json"))
ROWS = list(csv.DictReader(open(ROOT / "results" / "summary.csv")))
ORDER = ["baseline", "deadline_first", "window_nearest", "hybrid_otdr", "seeded_nn", "batched_nn"]
LABEL = {"baseline": "Baseline", "deadline_first": "Deadline-\nfirst", "window_nearest": "Window-\nnearest",
         "hybrid_otdr": "Hybrid\nOTDR", "seeded_nn": "Seeded\nNN", "batched_nn": "Batched\nNN"}
COLOR = dict(zip(ORDER, ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300"]))
INK, MUTED, GRID, SURFACE = "#0b0b0b", "#52514e", "#e3e2dd", "#ffffff"
NAME = {"baseline": "Baseline", "deadline_first": "Deadline first", "window_nearest": "Window nearest",
        "hybrid_otdr": "Hybrid OTDR", "seeded_nn": "Seeded NN", "batched_nn": "Batched NN"}

def clean(ax):
    for sp in ("top", "right", "left"): ax.spines[sp].set_visible(False)
    ax.spines["bottom"].set_color(MUTED); ax.tick_params(axis="y", length=0, colors=MUTED); ax.tick_params(axis="x", length=0)
    ax.grid(axis="y", color=GRID, linewidth=0.6); ax.set_axisbelow(True)

BARS = [("fig_otdr", "otdr_percent", "Mean OTDR", "OTDR (% of parcels received)", "{:.2f}%", (0, 100)),
        ("fig_delivery_rate", "delivery_rate_percent", "Mean delivery rate", "Delivery rate (% of parcels received)", "{:.2f}%", (0, 100)),
        ("fig_distance", "total_distance_km", "Mean total distance per day", "Distance (km per day)", "{:,.2f}", None),
        ("fig_utilisation", "average_capacity_utilization_percent", "Mean capacity utilisation", "Capacity utilisation (% of 30 units)", "{:.2f}%", (0, 100)),
        ("fig_on_time", "on_time_deliveries", "Mean on-time deliveries per day", "On-time deliveries (parcels per day)", "{:.2f}", None)]
for name, metric, title, ylabel, fmt, fixed in BARS:
    vals = [S[p][metric]["mean"] for p in ORDER]; top = 110 if fixed else max(vals) * 1.16
    fig, ax = plt.subplots(figsize=(4.6, 3.3), dpi=150)
    bars = ax.bar(range(6), vals, 0.74, color=[COLOR[p] for p in ORDER], edgecolor="white", zorder=3)
    bars[5].set_edgecolor(INK); bars[5].set_linewidth(1.6)
    ax.set_ylim(0, top)
    for x, v, p in zip(range(6), vals, ORDER):
        ax.text(x, v + top * 0.015, fmt.format(v), ha="center", va="bottom", fontsize=7, fontweight="bold" if p == "batched_nn" else "normal")
    ax.set_xticks(range(6)); ax.set_xticklabels([LABEL[p] for p in ORDER], fontsize=7)
    ax.set_ylabel(ylabel, fontsize=7.5, color=MUTED); ax.set_title(title, fontsize=9.5, fontweight="bold", loc="left")
    clean(ax); fig.tight_layout(); fig.savefig(OUT / f"{name}.png", facecolor="white"); print("wrote", OUT / f"{name}.png")

# Figure 1: OTDR on each of the 20 days, all six policies
fig, ax = plt.subplots(figsize=(7.0, 2.9), dpi=200)
ax.axvspan(10.5, 20.5, color="#f3f2ee", zorder=0)
ax.text(15.5, 3, "evaluation days 11-20", ha="center", fontsize=7, color=MUTED)
ax.text(5.5, 3, "development days 1-10", ha="center", fontsize=7, color=MUTED)
ax.hlines(LC["ceiling_percent_mean"], 0.5, 20.5, color=MUTED, linewidth=0.9, linestyle=(0, (4, 3)), zorder=1)
ax.text(0.6, LC["ceiling_percent_mean"] + 1.2, f"ceiling {LC['ceiling_percent_mean']:.1f}% (mean)", fontsize=6.5, color=MUTED, va="bottom")
ends = {}
for p in ORDER:
    y = [float(r["otdr_percent"]) for r in sorted((r for r in ROWS if r["policy"] == p), key=lambda r: r["day"])]
    top = p == "batched_nn"
    ax.plot(range(1, 21), y, color=COLOR[p], marker="o", ms=3.4 if top else 2.6, lw=2.2 if top else 1.3,
            markeredgecolor=SURFACE, markeredgewidth=0.5, label=NAME[p], zorder=4 if top else 3)
    ends[p] = y[-1]
# Direct labels for the two reference points only; the legend names every series.
ax.text(20.45, ends["batched_nn"], "Batched NN", fontsize=7, va="center", color=INK, fontweight="bold")
ax.text(20.45, ends["baseline"], "Baseline", fontsize=7, va="center", color=INK)
ax.set_xlim(0.5, 22.6); ax.set_ylim(0, 108); ax.set_yticks(range(0, 101, 20))
ax.set_xticks(range(1, 21)); ax.set_xlabel("Day", fontsize=7.5, color=MUTED)
ax.set_ylabel("OTDR (% of parcels received)", fontsize=7.5, color=MUTED)
ax.legend(fontsize=6.8, frameon=False, ncol=6, loc="lower center", bbox_to_anchor=(0.47, 1.0), handlelength=1.6, columnspacing=1.2)
clean(ax); fig.tight_layout(); fig.savefig(OUT / "fig1_otdr_per_day.png", facecolor=SURFACE); print("wrote", OUT / "fig1_otdr_per_day.png")

# Figure 2: parcels not on time by arrival hour (Batched NN)
H = LC["by_arrival_hour"]; hrs = range(8, 18)
av = [H.get(str(h), {}).get("lost_but_feasible_per_day", 0) for h in hrs]; tot = [H.get(str(h), {}).get("not_on_time_per_day", 0) for h in hrs]
fig, ax = plt.subplots(figsize=(7.0, 2.5), dpi=200)
ax.bar(range(10), av, 0.62, color="#eb6834", edgecolor=SURFACE, linewidth=1.2,
       label="Deliverable on its own (some planning round could reach it inside its window)")
ax.bar(range(10), [t - a for t, a in zip(tot, av)], 0.62, bottom=av, color="#9a9993", edgecolor=SURFACE, linewidth=1.2,
       label="Not deliverable by any policy (arrived too late for its window or the 18:00 return)")
for i, t in enumerate(tot):
    if t > 0.05: ax.text(i, t + 0.4, f"{t:.1f}", ha="center", fontsize=7.5, color=INK)
ax.set_xticks(range(10)); ax.set_xticklabels([f"{h:02d}:00" for h in hrs])
ax.set_ylim(0, 26); ax.set_xlabel("Hour the parcel arrived at the hub", fontsize=7.5, color=MUTED)
ax.set_ylabel("Parcels not on time (mean per day)", fontsize=7.5, color=MUTED)
ax.legend(fontsize=6.8, frameon=False, loc="upper left"); clean(ax)
fig.tight_layout(); fig.savefig(OUT / "fig2_losses_by_arrival_hour.png", facecolor=SURFACE); print("wrote", OUT / "fig2_losses_by_arrival_hour.png")
if "--show" in sys.argv: plt.show()
