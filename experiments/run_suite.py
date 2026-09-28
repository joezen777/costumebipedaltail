"""Full physics study: milestone hip snap, README section 27 comparison,
ablations and parameter studies. Writes curated outputs to results/.

    PYTHONPATH=. ~/.venvs/costumebipedaltail/bin/python experiments/run_suite.py [--no-anim] [--only NAME]
"""
from __future__ import annotations

import argparse
import json
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

from tailsim import motions
from tailsim.metrics import evaluate, score, write_csv
from tailsim.params import TailParams, configuration_set, REF_MASSES_8
from tailsim.runner import stability
from tailsim.sim import TailSim
from tailsim import viz

RES = Path(__file__).resolve().parents[1] / "results"

MOTIONS = {
    "hip_snap_30": motions.hip_snap,
    "dramatic_turn_45": motions.dramatic_turn,
    "walk_1.50Hz": lambda: motions.Walk(1.5),
    "walk_2.00Hz": lambda: motions.Walk(2.0),
    "walk_1.75Hz_literal": lambda: motions.Walk(1.75, literal=True),
    "side_step_300mm": motions.side_step,
    "crouch": motions.crouch,
}


def _run(args):
    name, p, mname = args
    r = TailSim(p).run(MOTIONS[mname]())
    return name, mname, r


def run_matrix(configs: dict, motion_names, workers=6):
    jobs = [(n, p, m) for n, p in configs.items() for m in motion_names]
    out = {n: {} for n in configs}
    with ProcessPoolExecutor(workers) as ex:
        for name, mname, r in ex.map(_run, jobs):
            out[name][mname] = r
    return out


def metrics_table(raw: dict, configs: dict):
    table = {}
    for name, per in raw.items():
        m = {k: evaluate(r) for k, r in per.items()}
        m["linear"] = stability(configs[name])
        sc, terms = score(m)
        table[name] = dict(score=sc, penalty_terms={k: v for k, v in terms.items() if v > 1e-3}, **m)
    return table


def slim(r):
    return {k: v for k, v in r.items() if k != "bodies"}


def save(obj, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=1, default=lambda x: x.tolist() if hasattr(x, "tolist") else float(x)))


def study_configs():
    base = TailParams()
    cfg = dict(configuration_set(base))
    cfg["reference"] = base.variant(label="reference")
    cfg["naive_no_springs"] = base.variant(label="naive", springs_enabled=False)
    cfg["D_roll_unrestricted"] = cfg["D_progressive"].variant(label="D roll free", roll_unrestricted=True)
    for c in (0.0, 0.015, 0.03, 0.05):
        cfg[f"com_{int(c*1000)}mm"] = base.variant(label=f"COM {c*1000:.0f} mm", com_offset=c)
    for t in (5.0, 10.0, 20.0, 40.0):
        cfg[f"preload_{int(t)}N"] = base.variant(label=f"cord {t:.0f} N", cord_preload=t)
    for f in ("VERY_LOW", "LOW", "MEDIUM", "HIGH"):
        cfg[f"friction_{f}"] = base.variant(label=f"friction {f}", friction=f)
    for n in (6, 10, 12):
        cfg[f"joints_{n}"] = base.variant(label=f"{n} joints", joint_count=n)
    cfg["mass_uniform"] = base.variant(label="uniform mass", masses=[0.25] * 8)
    cfg["limits_uniform_all"] = base.variant(label="uniform limits", progressive_limits=False)
    return cfg


def cad_mass_config():
    """Reference design with the masses measured from the exported CAD."""
    from tailsim.mass_budget import budget
    base = TailParams()
    sim = TailSim(base, settle=False)
    rows = budget(base.cad(), sim.spring_table())
    m = [r["total_g"] / 1000 for r in rows]
    return base.variant(label="CAD masses", masses=m), rows


def test_section_config(ballast=True):
    """4-joint physical prototype: vertebrae 1-4 of the full tail (+ ballast rod)."""
    base = TailParams()
    D = list(base.diameters()[:4])
    kw = dict(joint_count=4, mech_length=0.6, diameters_override=D, yaw_limits=list(base.yaw_limit_list()[:4]),
              masses=list(REF_MASSES_8[:4]), label="4-joint test section")
    if ballast:
        # V5..V8 + foam tip lumped on a stiff M8 rod: same mass and first moment about joint 5
        kw.update(foam_tip_mass=0.625, foam_tip_length=0.72, tip_bend_stiffness=400.0, tip_bend_damping=0.5,
                  tip_diameter=0.02, label="4-joint + ballast rod")
    else:
        kw.update(foam_tip_mass=0.05, foam_tip_length=0.05, label="4-joint bare")
    return TailParams(**kw)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-anim", action="store_true")
    ap.add_argument("--only", default="")
    a = ap.parse_args()
    t0 = time.time()
    fig = RES / "figures"; anim = RES / "animations"; data = RES / "data"

    if not a.only or a.only == "milestone":
        # ---- milestone: reference hip snap (README 29)
        ref = TailParams()
        r = TailSim(ref).run(motions.hip_snap())
        write_csv(r, data / "reference_hip_snap_30.csv")
        viz.response_plots(r, fig / "reference_hip_snap_30.png", "Reference design - 30° hip snap in 0.35 s")
        viz.waterfall(r, fig / "reference_hip_snap_joint_waterfall.png", "Hip snap: joint yaw propagation root -> tip")
        if not a.no_anim:
            viz.animate(r, anim / "reference_hip_snap_30.gif", titles=["reference, 30° hip snap"])
            viz.animate(r, anim / "reference_hip_snap_30.mp4", titles=["reference, 30° hip snap"])
        print("milestone", round(time.time() - t0), "s")

    if not a.only or a.only == "study":
        cfg = study_configs()
        cm, rows = cad_mass_config()
        cfg["cad_masses"] = cm
        save(rows, data / "mass_budget.json")
        raw = run_matrix(cfg, list(MOTIONS))
        table = metrics_table(raw, cfg)
        save(table, data / "study_metrics.json")
        # per-test CSVs for the four README configurations and the reference
        for name in ("A_friction_only", "B_cord_preload", "C_offset_com", "D_progressive", "reference", "naive_no_springs"):
            for mname, r in raw[name].items():
                write_csv(r, data / "csv" / f"{name}__{mname}.csv")
        abcd = {k: raw[k] for k in ("A_friction_only", "B_cord_preload", "C_offset_com", "D_progressive")}
        for mname in MOTIONS:
            viz.comparison_plot({k: v[mname] for k, v in abcd.items()}, fig / f"compare_ABCD_{mname}.png",
                                title=f"Configurations A-D, identical input: {mname}")
            viz.response_plots(raw["reference"][mname], fig / f"reference_{mname}.png", f"Reference design - {mname}")
        for group, keys in (("com", [k for k in cfg if k.startswith("com_")]),
                            ("preload", [k for k in cfg if k.startswith("preload_")]),
                            ("friction", [k for k in cfg if k.startswith("friction_")]),
                            ("naive", ["naive_no_springs", "reference", "cad_masses"]),
                            ("roll", ["D_progressive", "D_roll_unrestricted"])):
            viz.comparison_plot({cfg[k].label: raw[k]["hip_snap_30"] for k in keys}, fig / f"study_{group}_hip_snap.png",
                                title=f"{group} study - 30° hip snap")
        viz.comparison_plot({cfg[k].label: raw[k]["walk_1.50Hz"] for k in ("reference", "naive_no_springs", "friction_VERY_LOW")},
                            fig / "study_walk_1.5Hz.png", title="Walking (1.5 steps/s) - tip heading")
        if not a.no_anim:
            for mname in ("hip_snap_30", "dramatic_turn_45", "walk_1.50Hz"):
                viz.animate([abcd[k][mname] for k in abcd], anim / f"compare_ABCD_{mname}.mp4",
                            titles=["A friction only", "B + cord", "C + offset COM", "D + progressive"])
            viz.animate([abcd[k]["hip_snap_30"] for k in abcd], anim / "compare_ABCD_hip_snap_30.gif",
                        titles=["A friction only", "B + cord", "C + offset COM", "D + progressive"], fps=20)
            viz.animate([raw["naive_no_springs"]["hip_snap_30"], raw["reference"]["hip_snap_30"]],
                        anim / "naive_vs_reference_hip_snap.gif", titles=["no springs (naive)", "reference"], fps=20)
            viz.animate(raw["reference"]["crouch"], anim / "reference_crouch.gif", titles=["reference, crouch"], fps=20)
        print("study", round(time.time() - t0), "s")

    if not a.only or a.only == "test_section":
        cfg = {"test_ballast": test_section_config(True), "test_bare": test_section_config(False)}
        raw = run_matrix(cfg, ["hip_snap_30", "dramatic_turn_45", "walk_1.50Hz"])
        save(metrics_table(raw, cfg), data / "test_section_metrics.json")
        viz.comparison_plot({cfg[k].label: raw[k]["hip_snap_30"] for k in cfg}, fig / "test_section_hip_snap.png",
                            title="4-joint physical test section - 30° hip snap")
        if not a.no_anim:
            viz.animate([raw["test_ballast"]["hip_snap_30"], raw["test_bare"]["hip_snap_30"]],
                        anim / "test_section_hip_snap.gif", titles=["4-joint + ballast", "4-joint bare"], fps=20)
        print("test section", round(time.time() - t0), "s")


if __name__ == "__main__":
    main()
