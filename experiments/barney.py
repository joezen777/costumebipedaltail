"""Barney-style short tail (client revision): 0.9 m, S-shaped rest curve, lumbar-belt mount.

Keeps the approved Gojira mechanics (ball-and-socket chain, dorsal + lateral spring spine with
cap-ear anchors, felt liners, light cord, wedge flanges for the rest curve).

    PYTHONPATH=. python experiments/barney.py            # design config -> as-built config -> all motions
"""
import json
import pickle
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from tailsim import motions, viz
from tailsim.metrics import evaluate
from tailsim.params import TailParams
from tailsim.shape import barney_joints
from tailsim.sim import TailSim

ROOT = Path(__file__).resolve().parents[1]
N, MECH, TIP = 6, 0.75, 0.15
ROOT_DZ, PLATE_Z = -0.03, 0.04          # pivot 30 mm below / plate centre 40 mm above the pelvis centre
SHAPE = barney_joints(MECH, N, TIP, theta_root=5.0, theta_max=60.0, theta_end=5.0, h=0.55 * 1.727 + ROOT_DZ)
LIMITS = [8, 11, 14, 18, 22, 26]


def barney(**kw):
    base = dict(joint_count=N, mech_length=MECH, foam_tip_length=TIP, root_pitch_deg=float(SHAPE["root_pitch"]),
                rest_droop_list=[float(x) for x in SHAPE["droop"]], yaw_limits=LIMITS,
                root_diameter=0.190, last_mech_diameter=0.100, tip_diameter=0.060, taper_exponent=1.0,
                skin_root=0.020, skin_tip=0.010, mass_total=1.3, foam_tip_mass=0.06, tip_bend_stiffness=1.5,
                root_dz=ROOT_DZ, plate_z=PLATE_Z, deadband_deg=6.0, pitch_ratio=1.0, ball_radius_min=0.020, label="Barney tail (design masses)")
    base.update(kw)
    return TailParams(**base)


def as_built():
    """Design with the moving masses measured from the exported STLs + hardware + foam."""
    from cad import geometry as g
    from tailsim.mass_budget import budget
    base = barney(label="Barney tail, as built (CAD masses)")
    pj = ROOT / "cad" / "stl" / "parts_barney.json"
    if not pj.exists():
        return None
    c = g.CadParams(**json.loads((ROOT / "cad" / "variants" / "barney.json").read_text()))
    rows = budget(c, TailSim(base, settle=False).spring_table(), parts_json=pj)
    return base.variant(masses=[r["total_g"] / 1000 for r in rows])


MOTIONS = {"hip_snap_30": motions.hip_snap, "hip_snap_left": lambda: motions.Ramp("hip_snap_left", [0, 0, 0, 0.5236, 0, 0], 0.25, duration=6.0),
           "dramatic_turn_45": motions.dramatic_turn, "walk_1.50Hz": lambda: motions.Walk(1.5),
           "walk_2.00Hz": lambda: motions.Walk(2.0), "crouch": motions.crouch, "bend_over": motions.bend_over,
           "jump": motions.jump, "side_step_300mm": motions.side_step}


def configs():
    c = {"design": barney()}
    ab = as_built()
    if ab is not None:
        c["as_built"] = ab
    return c


def job(a):
    k, m = a
    return k, m, TailSim(configs()[k]).run(MOTIONS[m]())


def main():
    cfg = configs()
    raw = {k: {} for k in cfg}
    with ProcessPoolExecutor(6) as ex:
        for k, m, r in ex.map(job, [(k, m) for k in cfg for m in MOTIONS]):
            raw[k][m] = r
    met = {k: {"label": cfg[k].label, **{m: evaluate(r) for m, r in v.items()}} for k, v in raw.items()}
    (ROOT / "results" / "data").mkdir(parents=True, exist_ok=True)
    (ROOT / "results" / "data" / "barney.json").write_text(json.dumps(
        {"shape": {k: (v.tolist() if hasattr(v, "tolist") else v) for k, v in SHAPE.items()}, "results": met}, indent=1, default=float))
    (ROOT / "scratch").mkdir(exist_ok=True)
    with open(ROOT / "scratch" / "barney_raw.pkl", "wb") as f:
        pickle.dump(raw, f)
    fig = ROOT / "results" / "figures"
    k = "as_built" if "as_built" in raw else "design"
    for m in ("hip_snap_30", "dramatic_turn_45", "jump", "bend_over", "walk_1.50Hz"):
        viz.response_plots(raw[k][m], fig / f"barney_{m}.png", f"{cfg[k].label} - {m}")
    viz.waterfall(raw[k]["hip_snap_30"], fig / "barney_hip_snap_waterfall.png", "Barney tail: joint yaw propagation")
    for k, v in met.items():
        s, t, w, j, c = v["hip_snap_30"], v["dramatic_turn_45"], v["walk_1.50Hz"], v["jump"], v["crouch"]
        print(f"{k}: lag {s['maximum_tip_lag']:.1f} ov {s['maximum_tip_overshoot']:.1f} osc {s['oscillation_count']} set {s['settling_time']:.2f} "
              f"res {s['residual_offset']:.1f} | turn ov {t['maximum_tip_overshoot']:.1f} | whip {w['whip_ratio']:.2f} | "
              f"clear rest {s['rest_floor_clearance']:.3f} min(crouch) {c['min_floor_clearance']:.3f} jump floorN {j['max_floor_force']:.1f} "
              f"| hipM {max(s['peak_root_moment'], j['peak_root_moment']):.1f} | f0 {TailSim(cfg[k], settle=False).lowest_mode_hz:.3f}")


if __name__ == "__main__":
    main()
