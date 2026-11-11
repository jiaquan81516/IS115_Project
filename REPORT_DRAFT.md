# Improving On-Time Delivery Rate in Last-Mile Delivery Planning

**Module:** IS115  
**Team:** [Insert names and student IDs]  
**Date:** [Insert submission date]

## Executive summary

This project improves the on-time delivery rate (OTDR) of a last-mile parcel operation with ten electric vehicles. The supplied baseline selects parcels in arrival order and checks only capacity, vehicle range and the 18:00 return cutoff. It does not use delivery-window urgency, predicted stop times or route optimisation.

We evaluated three alternatives on 20 historical demand days. A deadline-first policy tested urgency ordering alone. A window-nearest policy combined a deadline priority queue with predicted delivery times and distance-aware greedy selection. A hybrid policy added feasible 2-opt route improvement and strategic batching.

The hybrid policy achieved the best overall result. Its mean OTDR was 87.87%, compared with 27.41% for the baseline, an improvement of 60.47 percentage points. It improved OTDR on all 20 days, reduced mean daily travel distance by 29.56%, and raised average capacity utilisation from 49.83% to 73.59%. On the evaluation split of days 011–020, it retained a mean OTDR of 87.82%.

## 1. Problem statement and motivation

The operation receives approximately 763–811 parcels per day. Each parcel has an arrival time, destination, size and preferred delivery window. Ten identical electric vehicles operate from one hub. Each vehicle has capacity 30, a per-trip range of 320 km and must return by 18:00. Planning occurs every ten minutes, and a confirmed vehicle departs 30 minutes later.

Capacity, range and the return cutoff are hard constraints. The simulator rejects any route that violates them. Delivery windows are soft constraints: early and late deliveries are allowed, but they reduce service performance.

The baseline has three weaknesses relevant to OTDR:

1. **Inefficient route ordering.** It follows parcel arrival order, which can create unnecessary movement between distant locations.
2. **No delivery-window priority.** An earlier arrival with a late deadline can be chosen before a later arrival with an urgent deadline.
3. **No time-aware departure decision.** The baseline checks whether a vehicle returns by 18:00 but does not check whether individual deliveries occur inside their preferred windows. Immediate dispatch can also produce early deliveries.

These weaknesses consume range, delay urgent parcels and leave capacity unused. The project therefore asks whether urgency, predicted delivery times, route locality and strategic waiting can improve OTDR without violating the hard constraints.

## 2. Performance metric

The primary metric is:

\[
\text{OTDR}=\frac{\text{number of parcels delivered within their preferred windows}}
{\text{total parcels received}}\times 100\%.
\]

A delivery is on time when:

\[
\text{window start} \leq \text{actual delivery time} \leq \text{window end}.
\]

The denominator includes every parcel in that day's demand file. Consequently, an early, late or undelivered parcel does not contribute to the numerator. This definition avoids a misleading score in which a policy delivers only a small set of easy parcels and ignores the rest.

The performance monitor also reports delivery rate, early and late deliveries, undelivered parcels, trip count, distance and capacity utilisation. These secondary measures explain why OTDR changes and expose operational trade-offs.

## 3. Approaches

### 3.1 Supplied baseline: FIFO first-fit

The baseline sorts waiting parcels by arrival time and parcel ID. It appends a parcel when the resulting route remains within capacity, range and the return cutoff. An infeasible parcel is skipped, and the policy continues checking later parcels.

This approach is simple and fast, but it treats the preferred windows as irrelevant. Arrival order can also cause geographical backtracking. On day 001, the baseline used only 55.95% of capacity on average while travelling 262.16 km per trip. It delivered 349 of 799 parcels, with only 213 delivered on time.

### 3.2 Approach 1: earliest deadline first

The first alternative sorts waiting parcels by delivery-window end, then window start, arrival time and parcel ID. It uses the same greedy first-fit construction but gives earlier deadlines priority.

This approach tests whether urgency ordering alone solves the problem. It does not predict actual stop times and does not prevent early or late deliveries. It also retains the baseline's append-only route construction.

The experiment shows that deadline order alone is insufficient. Mean delivery rate increased, but mean OTDR fell because vehicles continued accepting routes whose stops missed their windows.

### 3.3 Approach 2: window-aware nearest selection

The second alternative stores waiting parcels in a min-heap keyed by delivery-window end. During route construction, it examines unassigned parcels and considers only additions that satisfy all hard constraints and keep every selected delivery within its preferred window.

Among feasible candidates, it prioritises the earliest deadline and then the distance from the current stop. This combines urgency with geographical locality. If no parcel can currently be delivered on time, the policy returns an empty route and waits for a later planning round. This prevents early dispatch without requiring changes to the simulator.

This policy directly addresses all three identified problems: it predicts stop times, uses delivery-window urgency and reduces unnecessary travel through nearest-location tie-breaking.

### 3.4 Approach 3: hybrid OTDR policy

The hybrid begins with the window-aware route and adds two improvements.

First, it applies feasible 2-opt local search. A segment of the route is reversed only if the new route is shorter and every selected parcel remains on time. This prevents distance reduction from sacrificing OTDR.

Second, it uses strategic batching. Before 16:00, the vehicle waits when its proposed load is below 40% of capacity and every selected delivery has more than 60 minutes of remaining slack. The next planning rounds may add nearby parcels. The policy dispatches immediately when the load is larger or deadlines are closer.

The batching thresholds were selected using the development split, days 001–010. Days 011–020 were retained as an evaluation split.

## 4. Algorithms, data structures and complexity

Let \(n\) be the number of waiting parcels and \(m\) the number selected for one trip.

| Policy | Main algorithm and data structure | Time complexity per dispatch | Extra space |
|---|---|---:|---:|
| Baseline | Sorting and greedy first-fit | \(O(n\log n)\) | \(O(n)\) |
| Deadline first | Sorted list and repeated route feasibility checks | \(O(n^2)\) worst case | \(O(n)\) |
| Window nearest | Min-heap, greedy feasible selection and delivery-time simulation | \(O(nm^2+n\log n)\); \(O(n^3)\) when \(m=n\) | \(O(n+m)\) |
| Hybrid | Window-nearest construction plus repeated feasible 2-opt passes | Window-nearest cost plus \(O(m^3)\) per complete 2-opt pass | \(O(n+m)\) |

The window-aware policies are computationally more expensive, but route length is restricted by vehicle capacity, range and the return cutoff. A day-001 benchmark took approximately 0.08 seconds for the baseline, 0.10 seconds for deadline-first, 0.83 seconds for window-nearest and 0.99 seconds for the hybrid on the development machine. All policies are therefore practical for the supplied ten-minute planning interval.

The min-heap is the primary non-trivial data structure. It supports urgency ordering through efficient insertion and removal. Greedy feasible selection, 2-opt local search and strategic batching are the principal algorithms.

## 5. Experimental method

All policies used the same 20 demand files, distance matrix, fleet configuration and unchanged simulator. Each policy-day pair produced an independent event log. The performance monitor joined delivery events to parcel records by parcel ID and calculated OTDR from all demand records, including undelivered parcels.

Days 001–010 formed the development split. They were used to inspect behaviour and select batching thresholds. Days 011–020 formed the evaluation split. The main table also reports all 20 days to describe the complete historical performance.

The experiments used only the Python standard library. Automated tests verified OTDR classification, the treatment of undelivered parcels, strategic waiting for an early delivery and the read-only policy interface.

## 6. Results

### 6.1 Results across all 20 days

| Policy | Mean OTDR | OTDR standard deviation | OTDR range | Mean trips | Mean distance | Mean capacity utilisation |
|---|---:|---:|---:|---:|---:|---:|
| Baseline | 27.41% | 1.61 | 24.75–31.18% | 20.65 | 5,203.55 km | 49.83% |
| Deadline first | 17.18% | 1.40 | 13.93–20.12% | 21.25 | 5,180.32 km | 61.38% |
| Window nearest | 82.94% | 5.05 | 77.81–95.05% | 31.15 | 4,169.58 km | 67.48% |
| Hybrid OTDR | **87.87%** | **3.40** | **81.71–95.03%** | 30.25 | **3,665.59 km** | **73.59%** |

The hybrid improved mean OTDR by 60.47 percentage points relative to baseline and won on every historical day. The paired mean improvement had an approximate 95% confidence interval of 58.65–62.29 percentage points. Mean distance fell by 29.56%, while capacity utilisation rose by 23.76 percentage points.

The hybrid made more trips than the baseline, but each trip was shorter and better loaded. This is operationally reasonable because each vehicle receives a full recharge at the hub and the objective is OTDR rather than minimising trip count.

### 6.2 Development and evaluation split

| Policy | Days 001–010 mean OTDR | Days 011–020 mean OTDR |
|---|---:|---:|
| Baseline | 27.23% | 27.58% |
| Deadline first | 16.79% | 17.57% |
| Window nearest | 84.30% | 81.58% |
| Hybrid OTDR | **87.93%** | **87.82%** |

The hybrid's development and evaluation results differ by only 0.12 percentage points. This stability supports the feasibility of the batching rule beyond the days used to select it.

## 7. Discussion

### Why deadline-first performed poorly

Deadline-first increased average delivery rate from 40.45% to 51.50%, but its OTDR fell to 17.18%. It moved more parcels without ensuring that they arrived inside their windows. This separates two objectives that can otherwise be confused: delivering a parcel is not the same as delivering it on time.

### Why window-aware selection worked

The window-nearest policy rejects route additions whose predicted stop time is early or late. It also returns an empty route when all current deliveries would be early. This converts the preferred window from ignored information into an explicit optimisation criterion while leaving it a soft simulator constraint.

Distance-aware selection reduces backtracking and allows more parcels to fit within the range and time limits. Its deliveries were all inside their preferred windows, so its delivery rate equalled its OTDR.

### Why the hybrid performed best

Strategic batching avoids dispatching a nearly empty vehicle when deadlines permit a short wait. The additional arrivals improve route density and capacity utilisation. Feasible 2-opt then reduces route distance without moving any delivery outside its window.

The combination matters. Urgency sorting alone failed, while time prediction, locality and batching produced a large and consistent improvement.

### Trade-offs and limitations

The improved policies perform more computation than the baseline. Their observed execution times remain below one second per simulated day, but larger real-world fleets may require candidate filtering, spatial indexing or a fixed computation budget.

The batching thresholds are heuristic rather than mathematically optimal. Demand outside the historical 20 days may have different arrival patterns. Future evaluation should use additional unseen days and sensitivity analysis around the 40% load and 60-minute slack thresholds.

The model assumes fixed travel times, zero service time and immediate full recharge at the hub. Real deployments would need traffic uncertainty, parking and service time, driver breaks, charging limits and failed deliveries. The current results therefore demonstrate algorithmic feasibility within the supplied simulator, not guaranteed real-world performance.

## 8. Recommendation and conclusion

We recommend the hybrid OTDR policy. It directly addresses the baseline's three weaknesses and achieved the strongest average, minimum and evaluation-split OTDR. It also travelled less distance and used vehicle capacity more effectively than the baseline.

The project demonstrates that a single priority rule is not enough. High OTDR requires the policy to predict delivery times, preserve route feasibility, consider geographical locality and delay small non-urgent trips when waiting is safe. Within the supplied operating model, this combination raised mean OTDR from 27.41% to 87.87%.

## References and disclosure

1. IS115 Project Brief, *Last-Mile Delivery Planning*, supplied project document.
2. [Add the relevant course materials for priority queues, greedy algorithms and 2-opt/local search.]
3. [Add any external references used in the final report using the required citation style.]
4. LLM assistance disclosure: [Describe the models used, prompts explored, code-review process and how all generated suggestions were tested and verified. Attach or reference the required prompt transcript if applicable.]
