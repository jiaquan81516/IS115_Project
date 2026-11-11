# IS115 Last-Mile Delivery Planning: OTDR Optimisation

This project improves the on-time delivery rate (OTDR) of the supplied last-mile delivery simulator. It compares the supplied FIFO baseline with three policies across all 20 historical demand days.

## Performance metric

The primary metric is:

```text
OTDR (%) = parcels delivered within the preferred delivery window
           ------------------------------------------------------ × 100
                         total parcels received
```

Early, late and undelivered parcels are not counted as on time. Using all received parcels in the denominator prevents a policy from improving its score by leaving difficult parcels undelivered.

The performance monitor also reports delivery rate, early and late deliveries, trip count, total distance and average capacity utilisation.

## Policies

- `baseline`: supplied FIFO first-fit policy.
- `deadline_first`: sorts parcels by earliest delivery-window end and applies first-fit route construction.
- `window_nearest`: uses a min-heap for urgency, predicted delivery times and distance-aware greedy selection. It dispatches only routes whose selected parcels are predicted to be on time.
- `hybrid_otdr`: extends `window_nearest` with feasible 2-opt route improvement and strategic batching for small, non-urgent loads.

The supplied simulator, input data and baseline policy remain unchanged.

## Requirements

- Python 3.9 or later
- Python standard library only

Run every command from the project root.

## Run one simulation

```bash
python3 -m simulator \
  --policy solution.policies.hybrid_otdr \
  --data data \
  --day day_001 \
  --output results/hybrid_otdr/day_001
```

## Calculate metrics for one simulation

```bash
python3 -m solution.performance_monitor \
  --data data \
  --day day_001 \
  --log results/hybrid_otdr/day_001/log.txt
```

## Reproduce all experiments

```bash
for policy in baseline deadline_first window_nearest hybrid_otdr; do
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
python3 -m solution.summarize_results
```

This creates:

- `results/summary.csv`: one detailed row per policy and day.
- `results/summary.json`: aggregate statistics over all 20 days.
- `results/split_summary.json`: separate development and evaluation summaries.

Days 001–010 are treated as development data. Days 011–020 are treated as evaluation data.

## Run tests

```bash
python3 -m unittest discover -s tests -v
```

## Main result

Across all 20 days, the hybrid policy achieved a mean OTDR of **87.87%**, compared with **27.41%** for the baseline. It also reduced mean daily travel distance from 5,203.55 km to 3,665.59 km.

On the evaluation split, days 011–020, the hybrid achieved **87.82%** mean OTDR compared with **27.58%** for the baseline.

## Project structure

```text
data/                         Supplied demand, distance and configuration inputs
simulator/                    Supplied event-driven simulator; unchanged
solution/performance_monitor.py
solution/summarize_results.py
solution/policies/baseline.py Supplied baseline; unchanged
solution/policies/helpers.py
solution/policies/deadline_first.py
solution/policies/window_nearest.py
solution/policies/hybrid_otdr.py
tests/test_solution.py
results/<policy>/<day>/       Generated logs and metrics
REPORT_DRAFT.md               Report draft based on the completed experiments
```
