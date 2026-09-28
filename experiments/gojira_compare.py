"""Compare mechanisms on the Gojira "x^2 + 1" profile (tail hovers just above the floor).

    PYTHONPATH=. python experiments/gojira_compare.py
"""
import json
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

from tailsim import motions
from tailsim.metrics import evaluate
from tailsim.params import TailParams
from tailsim.shape import gojira_joints
from tailsim.sim import TailSim

ROOT = Path(__file__).resolve().parents[1]
N, MECH, TIP = 10, 1.5, 0.3
SHAPE = gojira_joints(0.95, 0.12, 0.10, MECH, N, TIP)
LIMITS = [8, 9, 10, 12, 14, 16, 18, 20, 23, 26]


def gojira(**kw):
    base = dict(joint_count=N, mech_length=MECH, foam_tip_length=TIP, root_pitch_deg=float(SHAPE["root_pitch"]),
                rest_droop_list=[float(x) for x in SHAPE["droop"]], yaw_limits=LIMITS, foam_tip_mass=0.1,
                mass_total=2.2, tip_bend_stiffness=1.5, tip_diameter=0.035)
    base.update(kw)
    return TailParams(**base)


def configs():
    hinge = dict(joint_type="hinge", springs_enabled=False, cord_enabled=False)
    on_stops = dict(pitch_down_limits=[0.5] * N)
    return {
        "ball_spring_spine": gojira(label="ball chain + 3 springs/joint (current design)"),
        "ball_on_stops_lateral": gojira(label="ball chain on pitch stops + 2 lateral springs/joint", spring_sides="LR", **on_stops),
        "ball_on_stops_nosprings": gojira(label="ball chain on pitch stops, no springs", springs_enabled=False, **on_stops),
        "hinge_30_w1": gojira(label="gate hinges 30° tilt, washers 1.0 N·m", hinge_tilt_deg=30, hinge_washer_torque=1.0, **hinge),
        "hinge_45_w1": gojira(label="gate hinges 45° tilt, washers 1.0 N·m", hinge_tilt_deg=45, hinge_washer_torque=1.0, **hinge),
        "hinge_45_w2": gojira(label="gate hinges 45° tilt, washers 2.0 N·m", hinge_tilt_deg=45, hinge_washer_torque=2.0, **hinge),
        "hinge_60_w2": gojira(label="gate hinges 60° tilt, washers 2.0 N·m", hinge_tilt_deg=60, hinge_washer_torque=2.0, **hinge),
        "hinge_45_visc": gojira(label="gate hinges 45° tilt, washers 1.0 + grease damping", hinge_tilt_deg=45, hinge_washer_torque=1.0,
                                visc=0.6, **hinge),
    }


MOTIONS = {"hip_snap_30": motions.hip_snap, "dramatic_turn_45": motions.dramatic_turn,
           "walk_1.50Hz": lambda: motions.Walk(1.5), "walk_2.00Hz": lambda: motions.Walk(2.0), "crouch": motions.crouch}


def job(args):
    name, p, m = args
    return name, m, evaluate(TailSim(p).run(MOTIONS[m]()))


def main():
    cfg = configs()
    out = {k: {"label": p.label} for k, p in cfg.items()}
    with ProcessPoolExecutor(6) as ex:
        for name, m, met in ex.map(job, [(k, p, m) for k, p in cfg.items() for m in MOTIONS]):
            out[name][m] = met
    (ROOT / "results" / "data").mkdir(parents=True, exist_ok=True)
    (ROOT / "results" / "data" / "gojira_compare.json").write_text(json.dumps(
        {"shape": {k: (v.tolist() if hasattr(v, "tolist") else v) for k, v in SHAPE.items()}, "results": out}, indent=1, default=float))
    for k, v in out.items():
        s, t, w, w2, c = v["hip_snap_30"], v["dramatic_turn_45"], v["walk_1.50Hz"], v["walk_2.00Hz"], v["crouch"]
        print(f"{k:24s} lag {s['maximum_tip_lag']:5.1f} ov {s['maximum_tip_overshoot']:5.1f} osc {s['oscillation_count']} "
              f"set {s['settling_time']:4.2f} res {s['residual_offset']:4.1f} | turn ov {t['maximum_tip_overshoot']:5.1f} res {t['residual_offset']:4.1f} "
              f"| whip {w['whip_ratio']:.2f}/{w2['whip_ratio']:.2f} | clear rest {s['rest_floor_clearance']:.3f} walk {min(w['min_floor_clearance'], w2['min_floor_clearance']):.3f} "
              f"crouch {c['min_floor_clearance']:.3f} floorN {c['max_floor_force']:.0f} | hipM {s['rest_root_moment']:.1f}/{max(s['peak_root_moment'], t['peak_root_moment']):.1f}")


if __name__ == "__main__":
    main()
