#!/usr/bin/env bash
# Reproduce every number and figure in the report with one command.
#
#   bash run_all.sh                 # everything (about 5 minutes)
#   bash run_all.sh --skip-analysis # experiments and summary only (about 2 minutes)
#   bash run_all.sh --skip-charts   # do not draw PNG charts (no matplotlib needed)
#
# Run it from the project root. Needs Python 3.9+; matplotlib only for the charts.
# The simulator is deterministic (no random numbers), so reruns give identical results.
set -euo pipefail
cd "$(dirname "$0")"

POLICIES="baseline deadline_first window_nearest hybrid_otdr seeded_nn batched_nn"
SKIP_ANALYSIS=0; SKIP_CHARTS=0
for arg in "$@"; do
  case "$arg" in
    --skip-analysis) SKIP_ANALYSIS=1 ;;
    --skip-charts)   SKIP_CHARTS=1 ;;
    *) echo "unknown option: $arg" >&2; exit 2 ;;
  esac
done

echo "[1/4] Simulating 6 policies x 20 days"
for policy in $POLICIES; do
  for number in $(seq 1 20); do
    day=$(printf "day_%03d" "$number")
    output="results/$policy/$day"
    python3 -m simulator --policy "solution.policies.$policy" --data data --day "$day" --output "$output" > /dev/null
    python3 -m solution.performance_monitor --data data --day "$day" --log "$output/log.txt" > /dev/null
  done
  echo "      done: $policy"
done

echo "[2/4] Aggregating results"
python3 -m solution.summarize_results --results results --policies $POLICIES > /dev/null

if [ "$SKIP_ANALYSIS" -eq 0 ]; then
  echo "[3/4] Supplementary analyses (writes analysis/output/*.json)"
  for script in paired_comparisons trip_sizes table9_by_window_and_arrival \
                figure9_losses_and_ceiling tables10_12_ablation_sensitivity runtime_scalability; do
    echo "      running: $script"
    python3 "analysis/$script.py" > /dev/null
  done
else
  echo "[3/4] Supplementary analyses skipped"
fi

if [ "$SKIP_CHARTS" -eq 0 ] && [ "$SKIP_ANALYSIS" -eq 0 ]; then
  echo "[4/4] Charts (writes analysis/figures/*.png)"
  python3 analysis/draw_charts.py > /dev/null
else
  echo "[4/4] Charts skipped"
fi

# Compare the headline with the report (Batched NN mean OTDR over 20 days).
python3 - <<'PY'
import json
s = json.load(open("results/summary.json"))
base, got = s["baseline"]["otdr_percent"]["mean"], s["batched_nn"]["otdr_percent"]["mean"]
print(f"\nBaseline  mean OTDR: {base:.2f}%   (report: 27.41%)")
print(f"Batched NN mean OTDR: {got:.2f}%   (report: 92.96%)")
print("Headline matches the report." if abs(got - 92.96) < 0.01 and abs(base - 27.41) < 0.01
      else "WARNING: headline differs from the report; check the data and policy files.")
PY
