# IS115 Last-Mile Delivery Planning: OTDR Optimisation

This project improves the on-time delivery rate (OTDR) of the supplied last-mile delivery simulator. It compares the supplied FIFO baseline with five other dispatch policies across all 20 historical demand days. The selected policy is `batched_nn`.

## Performance metric

```text
OTDR (%) = parcels delivered within the preferred delivery window
           ------------------------------------------------------ × 100
                         total parcels received
```

Early, late and undelivered parcels are not counted as on time. The performance monitor also reports delivery rate, early and late deliveries, trip count, total distance and average capacity utilisation.

## Policies

| Policy | Description | Role |
|---|---|---|
| `baseline` | Supplied FIFO first-fit policy | Supplied |
| `deadline_first` | Sorts parcels by window end, then first-fit | Experiment |
| `window_nearest` | Min-heap for urgency, predicted arrival times, nearest-first greedy selection | Experiment |
| `hybrid_otdr` | `window_nearest` plus 2-opt and a simple wait rule | Benchmark |
| `seeded_nn` | Most urgent parcel seeds the route, nearest neighbour fills it, then 2-opt | Experiment |
| `batched_nn` | `seeded_nn` plus a cutoff-aware hold-or-dispatch rule | **Selected** |

The supplied `simulator/`, `data/` and `baseline.py` are unchanged.

## Requirements

- Python 3.9 or later
- Policies, simulator and performance monitor: Python standard library only
- Charts only (`analysis/draw_charts.py`): `pip install matplotlib`

Run every command from the project root.

## Run one simulation

```bash
python3 -m simulator \
  --policy solution.policies.batched_nn \
  --data data \
  --day day_001 \
  --output results/batched_nn/day_001
```

## Calculate metrics for one simulation

```bash
python3 -m solution.performance_monitor \
  --data data \
  --day day_001 \
  --log results/batched_nn/day_001/log.txt
```

## Reproduce all experiments

```bash
for policy in baseline deadline_first window_nearest hybrid_otdr seeded_nn batched_nn; do
  for number in {1..20}; do
    day=$(printf "day_%03d" "$number")
    output="results/$policy/$day"

    python3 -m simulator \
      --policy "solution.policies.$policy" \
      --data data \
      --day "$day" \
      --output "$output"

    python3 -m solution.performance_monitor \
      --data data \
      --day "$day" \
      --log "$output/log.txt"
  done
done
```

Aggregate the results:

```bash
python3 -m solution.summarize_results --results results --policies \
  baseline deadline_first window_nearest hybrid_otdr seeded_nn batched_nn
```

This creates:

- `results/summary.csv`: one detailed row per policy and day.
- `results/summary.json`: aggregate statistics over all 20 days.
- `results/split_summary.json`: separate development and evaluation summaries.

Days 001–010 are treated as development data. Days 011–020 are treated as evaluation data.

## Supplementary analyses

Run these after the experiments above (they need `results/` to exist). Each writes a JSON file to `analysis/output/`.

```bash
python3 analysis/table9_by_window_and_arrival.py      # Table 9: OTDR by window length and arrival time
python3 analysis/tables10_12_ablation_sensitivity.py  # Tables 10-12: what each part adds, sensitivity, trade-offs (about 3 min)
python3 analysis/figure9_losses_and_ceiling.py        # Figure 9: where parcels are lost, and the OTDR ceiling
python3 analysis/runtime_scalability.py               # Run time as demand grows (about 1 min)
```

## View the charts

```bash
pip install matplotlib
python3 analysis/draw_charts.py
```

PNG files are written to `analysis/figures/` (git-ignored). Add `--show` to also open them in windows.

## Project structure

```text
data/                                   Supplied demand, distance and configuration inputs
simulator/                              Supplied event-driven simulator; unchanged
solution/performance_monitor.py         Metrics for one simulated day
solution/summarize_results.py           Aggregates all runs into summary files
solution/policies/baseline.py           Supplied baseline; unchanged
solution/policies/helpers.py            Shared route and feasibility helpers
solution/policies/deadline_first.py
solution/policies/window_nearest.py
solution/policies/hybrid_otdr.py
solution/policies/seeded_nn.py
solution/policies/batched_nn.py         Selected policy
analysis/shared_helpers.py              Common code for the analysis scripts
analysis/table9_by_window_and_arrival.py
analysis/tables10_12_ablation_sensitivity.py
analysis/figure9_losses_and_ceiling.py
analysis/runtime_scalability.py
analysis/draw_charts.py
analysis/output/                        JSON results of the analysis scripts
results/<policy>/<day>/                 Generated logs and metrics
```
