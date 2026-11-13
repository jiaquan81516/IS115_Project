"""Shared helpers for the supplementary analyses (run from the project root: python3 analysis/<script>.py)."""
import csv, importlib.util, json, os, sys, tempfile, time
from multiprocessing import Pool
from pathlib import Path

PROJ = Path(os.environ.get("PROJ", ".")).resolve()
sys.path.insert(0, str(PROJ))
from simulator.simulator import Simulator            # noqa: E402
from simulator.loaders import day_input_paths        # noqa: E402
from solution.performance_monitor import calculate_metrics  # noqa: E402

OUT = Path(os.environ.get("ANALYSIS_OUT", PROJ / "analysis" / "output"))
OUT.mkdir(parents=True, exist_ok=True)
TICKS = list(range(480, 1051, 10))  # planning times 08:00..17:30 in minutes


def fresh_policy(name, **overrides):
    """Load a private copy of solution/policies/<name>.py and override module constants / functions."""
    path = PROJ / "solution" / "policies" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(f"variant_{name}_{abs(hash(str(overrides)))}", path)
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    for key, value in overrides.items(): setattr(mod, key, value)
    return mod.dispatch


def run_day(policy_fn, day, data=None, tmp=None):
    """Simulate one day with policy_fn and return its metrics (plus wall-clock seconds). Logs go to a temporary folder."""
    tmp = tmp or Path(tempfile.gettempdir()) / "is115_analysis_runs"
    data = Path(data or PROJ / "data")
    parcels, dist, cfg = day_input_paths(data, day)
    sim = Simulator(parcels, dist, cfg, dispatch_policy=policy_fn)
    out = Path(tmp) / f"{os.getpid()}_{time.time_ns()}"
    t0 = time.perf_counter(); sim.run(out / "log.txt"); seconds = time.perf_counter() - t0
    P = list(csv.DictReader(open(parcels, newline="", encoding="utf-8-sig")))
    D = list(csv.DictReader(open(dist, newline="", encoding="utf-8-sig")))
    C = json.load(open(cfg, encoding="utf-8-sig"))
    ev = [json.loads(l) for l in open(out / "log.txt") if l.strip()]
    m = calculate_metrics(P, D, C, ev); m["seconds"] = seconds
    return m


def mean(xs): xs = list(xs); return sum(xs) / len(xs)
