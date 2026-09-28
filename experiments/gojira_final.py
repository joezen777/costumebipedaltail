"""Finalists on the Gojira profile over every motion (incl. bend-over and jump); keeps raw
trajectories for the pose renders.  PYTHONPATH=. python experiments/gojira_final.py"""
import json
import pickle
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from tailsim import motions, viz
from tailsim.metrics import evaluate
from tailsim.sim import TailSim
from experiments.gojira_compare import gojira

ROOT = Path(__file__).resolve().parents[1]
H = dict(joint_type="hinge", springs_enabled=False, cord_enabled=False)
def elastic_spine(f_yaw=0.7, sag_deg=2.0, zeta=0.12, roll_ratio=0.5, label=None, precamber=True):
    """Continuous pre-curved elastic core (e.g. twin stacked PEX tubes in foam), discretised at the
    joint pitch: bending stiffness per joint from a sag target (pitch) and a frequency rule (yaw)."""
    import math
    import numpy as np
    probe = gojira(springs_enabled=False, cord_enabled=False, mu=0.0, visc=0.0, settle_time=0.0)
    sim = TailSim(probe, settle=False)
    tau = -sim.data.qfrc_bias[sim.info.pitch_dofs]                  # gravity bending moment at the rest curve
    Kp = np.abs(tau) / math.radians(sag_deg)
    Ky = (2 * math.pi * f_yaw) ** 2 * sim.I_yaw
    Kr = roll_ratio * Ky
    cy, cp = 2 * zeta * np.sqrt(Ky * sim.I_yaw), 2 * zeta * np.sqrt(Kp * sim.I_pitch)
    stiff = [[float(Ky[i]), float(Kp[i]), float(Kr[i])] for i in range(len(Ky))]
    # pre-camber: form the core bent upward by the gravity sag so it settles onto the target curve
    ref = [[0.0, -float(np.degrees(tau[i] / Kp[i])) if precamber else 0.0, 0.0] for i in range(len(Ky))]
    damp = [[float(cy[i]), float(cp[i]), float(cy[i])] for i in range(len(Ky))]
    return gojira(label=label or f"elastic spine ({f_yaw} Hz yaw, {sag_deg}° sag)", springs_enabled=False, cord_enabled=False,
                  mu=0.0, visc=0.0, joint_stiffness=stiff, joint_damping=damp, joint_springref=ref, stop_friction=False,
                  yaw_limits=[40] * 10, pitch_up_limits=[40] * 10, pitch_down_limits=[40] * 10, max_roll=20)


FINALISTS = {
    "ball_spring_spine": gojira(label="ball chain + spring spine"),
    "hinge_60": gojira(label="gate hinges, 60° tilt, damping grease", hinge_tilt_deg=60, hinge_washer_torque=2.0, visc=3.0, **H),
    "hinge_45": gojira(label="gate hinges, 45° tilt, damping grease", hinge_tilt_deg=45, hinge_washer_torque=2.0, visc=3.0, **H),
    "as_built": None,       # filled below: CAD masses, springs re-sized for them
    "elastic_07": elastic_spine(0.7, sag_deg=3.0, label="elastic spine, pre-cambered (0.7 Hz yaw)"),
    "elastic_10": elastic_spine(1.0, sag_deg=3.0, label="elastic spine, pre-cambered (1.0 Hz yaw)"),
    "elastic_07_stiff": elastic_spine(0.7, sag_deg=1.0, label="elastic spine, pre-cambered, stiff pitch (0.7 Hz yaw)"),
}
def as_built():
    """Recommended design with the moving masses measured from the exported Gojira STLs."""
    import json as _j
    from cad import geometry as _g
    from tailsim.mass_budget import budget
    base = gojira(label="as built (CAD masses)")
    c = _g.CadParams(**_j.loads((ROOT / "cad" / "variants" / "gojira.json").read_text()))
    sim = TailSim(base, settle=False)
    rows = budget(c, sim.spring_table(), parts_json=ROOT / "cad" / "stl" / "parts_gojira.json")
    return base.variant(masses=[r["total_g"] / 1000 for r in rows])


FINALISTS["as_built"] = as_built()

MOTIONS = {"hip_snap_30": motions.hip_snap, "hip_snap_left": lambda: motions.Ramp("hip_snap_left", [0, 0, 0, 0.5236, 0, 0], 0.25, duration=6.0),
           "dramatic_turn_45": motions.dramatic_turn, "walk_1.50Hz": lambda: motions.Walk(1.5),
           "walk_2.00Hz": lambda: motions.Walk(2.0), "crouch": motions.crouch, "bend_over": motions.bend_over,
           "jump": motions.jump, "side_step_300mm": motions.side_step}


def job(a):
    k, m = a
    r = TailSim(FINALISTS[k]).run(MOTIONS[m]())
    return k, m, r


def main():
    import sys
    only = sys.argv[1].split(",") if len(sys.argv) > 1 else list(FINALISTS)
    raw = {k: {} for k in only}
    with ProcessPoolExecutor(6) as ex:
        for k, m, r in ex.map(job, [(k, m) for k in only for m in MOTIONS]):
            raw[k][m] = r
    met = {k: {"label": FINALISTS[k].label, **{m: evaluate(r) for m, r in v.items()}} for k, v in raw.items()}
    data = ROOT / "results" / "data"
    old = json.loads((data / "gojira_final.json").read_text()) if (data / "gojira_final.json").exists() else {}
    old.update(met)
    (data / "gojira_final.json").write_text(json.dumps(old, indent=1, default=float))
    (ROOT / "scratch").mkdir(exist_ok=True)
    rawp = ROOT / "scratch" / "gojira_raw.pkl"
    allraw = pickle.load(open(rawp, "rb")) if rawp.exists() else {}
    allraw.update(raw)
    with open(rawp, "wb") as f:
        pickle.dump(allraw, f)
    FIN = {k: FINALISTS[k] for k in only}
    fig = ROOT / "results" / "figures"
    if len(only) > 1:
        for m in MOTIONS:
            viz.comparison_plot({FINALISTS[k].label: raw[k][m] for k in only}, fig / f"gojira_{m}.png",
                                title=f"Gojira profile finalists: {m}")
    for k in only:
        for m in ("hip_snap_30", "jump", "bend_over"):
            viz.response_plots(raw[k][m], fig / f"gojira_{k}_{m}.png", f"{FINALISTS[k].label} - {m}")
    for k, v in met.items():
        print(k)
        for m, x in v.items():
            if m == "label":
                continue
            print(f"   {m:18s} lag {x.get('maximum_tip_lag', float('nan')):5.1f} ov {x.get('maximum_tip_overshoot', float('nan')):5.1f} "
                  f"osc {x.get('oscillation_count', '-')} set {x.get('settling_time', float('nan')):4.2f} whip {x.get('whip_ratio', float('nan')):4.2f} "
                  f"clear min {x['min_floor_clearance']:.3f} floorN {x['max_floor_force']:5.1f} hipM {x['peak_root_moment']:5.1f} "
                  f"stopT {x['peak_stop_torque']:5.1f} tipv {x['peak_tip_velocity']:.2f}")


if __name__ == "__main__":
    main()
