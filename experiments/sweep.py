"""Parameter sweep over the README section 25 design variables.

Stage 1 (default): friction level x yaw stiffness x friction dead band x
lateral preload x cord preload, on the reference 8-joint tail.
Writes results/sweep/stage1.json sorted by the motion-quality score.
"""
import itertools
import json
import sys
import time
from dataclasses import asdict
from pathlib import Path

from tailsim.params import TailParams
from tailsim.runner import run_many

OUT = Path(__file__).resolve().parents[1] / "results" / "sweep"


def stage1():
    grid = dict(friction=["VERY_LOW", "LOW", "MEDIUM", "HIGH"], yaw_local_hz=[0.5, 0.7, 0.9, 1.2],
                deadband_deg=[2.0, 3.5], lateral_preload_margin=[0.3, 0.6], cord_preload=[5.0, 20.0])
    keys = list(grid)
    return [TailParams(label="s1", **dict(zip(keys, v))) for v in itertools.product(*grid.values())], keys


def main(stage="stage1"):
    params, keys = globals()[stage]()
    t = time.time()
    res = run_many(params)
    rows = []
    for p, out, sc, terms in res:
        rows.append(dict(params={k: getattr(p, k) for k in keys}, score=sc, terms=terms, results=out))
    rows.sort(key=lambda r: r["score"])
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"{stage}.json").write_text(json.dumps(rows, indent=1, default=float))
    print(f"{len(rows)} configs in {time.time()-t:.0f}s")
    for r in rows[:12]:
        s = r["results"].get("hip_snap_30", {})
        w = r["results"].get("walk_1.50Hz", {})
        print(round(r["score"], 2), r["params"], "lag", round(s.get("maximum_tip_lag", 0), 1), "ov", round(s.get("maximum_tip_overshoot", 0), 1),
              "osc", s.get("oscillation_count"), "set", round(s.get("settling_time", 0), 2), "res", round(s.get("residual_offset", 0), 1),
              "whip", round(w.get("whip_ratio", 0), 2))


if __name__ == "__main__":
    main(*sys.argv[1:])
