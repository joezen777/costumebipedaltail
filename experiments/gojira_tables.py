"""Build tables for the Gojira variant: springs, strength, mass budget, parts list.

    PYTHONPATH=. python experiments/gojira_tables.py
"""
import json
import math
import sys
from pathlib import Path

import numpy as np

sys.argv = sys.argv[:1]
from cad import geometry as g  # noqa: E402
from experiments.gojira_final import FINALISTS, MOTIONS  # noqa: E402
from experiments.make_tables import md, PETG_ALLOW, PETG_UTS  # noqa: E402
from tailsim.mass_budget import budget  # noqa: E402
from tailsim.sim import TailSim  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "tables"


def main():
    p = FINALISTS["as_built"]
    c = g.CadParams(**json.loads((ROOT / "cad" / "variants" / "gojira.json").read_text()))
    sim = TailSim(p, settle=False)
    rows = []
    for s in sim.spring:
        i = s["joint"] + 1
        lim = p.yaw_limit_list()[i - 1] if s["side"] in "LR" else p.pitch_limit_list()[i - 1]
        tmax = s["T0"] + s["k"] * s["arm"] * math.radians(lim)
        L_inst = g.spring_span_parent(c, i) + g.spring_span_child(c)
        par = "2 in parallel" if tmax > 120 else "1"
        rows.append([f"J{i}", {"L": "left", "R": "right", "D": "dorsal"}[s["side"]], f"{s['k']/1000:.2f}", f"{s['T0']:.1f}",
                     f"{tmax:.1f}", f"{s['arm']*1000:.1f}", f"{L_inst:.1f}", f"{g.coil_od(c, i):.1f}", par])
    (OUT / "gojira_springs.md").write_text(
        "# Spring schedule: Gojira variant (10 joints)\n\nFrom the physics spring design of the recommended tail. "
        "Choose extension springs of the listed rate whose force at the installed length is T0 (a short cord loop on a hook "
        "trims T0). Where the stop tension exceeds ~120 N use two springs in parallel (each with half k and T0).\n\n"
        + md(["joint", "spring", "k (N/mm)", "T0 at rest (N)", "T at stop (N)", "arm (mm)", "installed length (mm)",
              "max coil OD (mm)", "count"], rows))
    # strength from all simulated motions
    peak = dict(neck=np.zeros(p.n), N=np.zeros(p.n), Nlat=np.zeros(p.n), T=np.zeros(len(sim.spring)))
    for mname in MOTIONS:
        r = TailSim(p).run(MOTIONS[mname]())
        peak["neck"] = np.maximum(peak["neck"], r["peak_neck_moment"])
        peak["N"] = np.maximum(peak["N"], r["joint_force"].max(0))
        peak["Nlat"] = np.maximum(peak["Nlat"], np.sqrt(np.maximum(r["joint_force"] ** 2 - r["seat_comp"] ** 2, 0)).max(0))
        peak["T"] = np.maximum(peak["T"], r["spring_T"].max(0))
    rows = []
    for i in range(1, p.n + 1):
        Z = g.neck_section_modulus(c, i)
        M_allow = PETG_ALLOW * Z / 1000
        M_design = peak["neck"][i - 1] + peak["Nlat"][i - 1] * g.DF(c, i) / 1000
        Td = max(t for t, s in zip(peak["T"], sim.spring) if s["joint"] == i - 1)
        ear = Td * (g.spring_arm(c, i) - g.cap_outer_r(c, i)) / 1000 * 1000 / (g.ear_w(c, i) * g.cap_ear_t(c, i) ** 2 / 6)
        rows.append([f"J{i}", f"{M_design:.2f}", f"{M_allow:.1f}", f"{M_allow / max(M_design, 1e-6):.1f}", f"{Td:.0f}",
                     f"{ear:.1f}", f"{PETG_UTS / ear:.1f}"])
    (OUT / "gojira_strength.md").write_text(
        "# Strength check: Gojira variant (all simulated motions incl. jump and bend-over)\n\n"
        "Neck design moment = peak ball moment + peak lateral ball force x neck length; allowable 20 MPa. "
        "Cap ear = peak spring tension as an out-of-plane cantilever on the ear (16 mm on root caps, 12 mm elsewhere) vs PETG UTS 45 MPa.\n\n"
        + md(["joint", "neck design moment (N·m)", "neck allowable (N·m)", "neck SF", "peak spring tension (N)",
              "ear stress (MPa)", "ear SF"], rows))
    pj = ROOT / "cad" / "stl" / "parts_gojira.json"
    if pj.exists():
        rows = []
        for r in budget(c, sim.spring_table(), parts_json=pj):
            rows.append([f"V{r['i']}", f"{r['printed_g']:.0f}", f"{r['hardware_g']:.0f}", f"{r['springs_g']:.0f}",
                         f"{r['foam_g']:.0f}", f"{r['skin_g']:.0f}", f"**{r['total_g']:.0f}**", f"{p.mass_list()[r['i']-1]*1000:.0f}"])
        (OUT / "gojira_mass_budget.md").write_text(
            "# Moving-mass budget: Gojira variant (grams)\n\nPrinted masses from the exported STLs (PETG, 3 perimeters, 20 % infill).\n\n"
            + md(["segment", "printed", "hardware", "springs", "foam", "skin", "total", "simulated"], rows))
        parts = json.loads(pj.read_text())
        rows = [[k, "x".join(f"{v:.0f}" for v in st["bbox_mm"]), f"{st['mass_g']:.0f}"] for k, st in sorted(parts.items())]
        (OUT / "gojira_parts.md").write_text(
            "# Print list: Gojira variant\n\nAll STLs in `cad/stl/gojira/` (4-joint prototype kit: `cad/stl/gojira_test_section/`), "
            "already in print orientation. One of each file; every part fits a 200 mm cube.\n\n"
            + md(["part", "bounding box (mm)", "est. mass (g)"], rows)
            + f"\n**Total printed PETG: {sum(st['mass_g'] for st in parts.values()) / 1000:.2f} kg** "
              f"({len(parts)} files, of which the test-section ballast plate is only for the prototype).\n")
    print("gojira tables written")


if __name__ == "__main__":
    main()
