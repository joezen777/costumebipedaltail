"""1:8 display figurine (skinny 5 ft 8 in male, protogen head) with a sliding tail-plate slot.

Exports the figurine parts from cad/openscad/figurine_1to8.scad as print-ready STLs (one clean
volume each), checks they fit the Photon Mono 5s, checks that the 1:8 kit's hip plate slides in the
back channel without touching it at every level, and checks the figure + tail can't tip over on
its base.

    PYTHONPATH=. ~/.venvs/costumebipedaltail/bin/python cad/export_figurine.py
Output: cad/stl/figurine_1to8_resin/ (+ report.json)
"""
import json
import re
import subprocess
import sys
from pathlib import Path

import numpy as np
import trimesh

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "cad"))
from export_stl import clean_mesh, off_to_stl  # noqa: E402

SCAD = ROOT / "cad" / "openscad" / "figurine_1to8.scad"
OUT = ROOT / "cad" / "stl" / "figurine_1to8_resin"
KIT = ROOT / "cad" / "stl" / "replica_1to8_resin"
PRINTER = (218.0, 123.0, 200.0)
RESIN_DENSITY = 1.10  # g/ml, ABS-like resin (cured)
JOBS = [("20_figure_body", "body"), ("21_protogen_head", "head"), ("22_display_base", "base"), ("23_level_pin", "pin")]


def render(args):
    name, fig = args
    path = OUT / f"{name}.stl"
    off = path.with_suffix(".off")
    r = subprocess.run(["openscad", "-o", str(off), "-D", f'FIG="{fig}"', str(SCAD)],
                       capture_output=True, text=True, cwd=SCAD.parent)
    if r.returncode or not off.exists():
        return name, False, r.stderr[-300:]
    off_to_stl(off, path)
    return name, clean_mesh(path), ""


def scad_levels():
    """LEVELS and DZ_MIN as written in the SCAD source (plate raise from the design height, mm at 1:8)."""
    src = SCAD.read_text()
    lo, step, hi = map(float, re.search(r"LEVELS\s*=\s*\[for \(d = \[(-?\d+) : (\d+) : (-?\d+)\]", src).groups())
    dz_min = float(re.search(r"DZ_MIN\s*=\s*(-?\d+)", src).group(1))
    return [dz_min] + list(np.arange(lo, hi + 0.1, step))


def plate_clearance(body, hip, levels):
    """Interference between the hip plate and the body with the plate slid to each level.

    Cheap two-way containment test (no distance fields): plate vertices + surface samples inside
    the body, and body vertices inside the plate. Both must be zero for a free sliding fit."""
    pts = np.vstack([hip.vertices, hip.sample(2000)])
    out = {}
    for dz in levels:
        p = pts + [0, 0, dz]
        lo, hi = p.min(0) - 0.5, p.max(0) + 0.5
        near = body.vertices[np.all((body.vertices > lo) & (body.vertices < hi), axis=1)]
        hit_b = int(hip.contains(near - [0, 0, dz]).sum()) if len(near) else 0
        out[f"{dz:+.0f}"] = dict(plate_points_in_body=int(body.contains(p).sum()), body_points_in_plate=hit_b)
    return out


def tipping(meshes, levels, base_extent):
    """Combined centre of mass (figure + head + base + hip plate + tail) vs the base footprint."""
    rows = {}
    fixed = [meshes[k] for k in ("20_figure_body", "21_protogen_head", "22_display_base")]
    tail = [meshes["01_hip_mount_plate"]] + [meshes[f"tail_{i}"] for i in range(1, 7)]
    for dz in levels[:1]:                     # the plate only moves in z, so x/y of the CoM don't change
        m, c = 0.0, np.zeros(3)
        for mm in fixed + tail:
            off = np.array([0, 0, dz]) if any(mm is t for t in tail) else 0
            m += mm.volume; c += mm.volume * (mm.center_mass + off)
        c /= m
        rows = dict(com_x_mm=round(float(c[0]), 1), com_y_mm=round(float(c[1]), 1),
                                  margin_to_rear_edge_mm=round(float(c[0] - base_extent[0][0]), 1))
    return rows, round(m / 1000 * RESIN_DENSITY, 1)        # mm^3 -> ml -> g


def posed_tail(tmp):
    """Kit vertebrae placed in the body frame at the design level (same chain as mini_kit.scad)."""
    out = []
    for i in range(1, 7):
        path = Path(tmp) / f"v{i}.stl"
        subprocess.run(["openscad", "-o", str(path), "-D", 'FIG="tail_posed"', "-D", f"INDEX={i}", str(SCAD)],
                       capture_output=True, cwd=SCAD.parent, check=True)
        out.append(trimesh.load(path))
    return out


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    if "--checks-only" in sys.argv:
        res = [(n, clean_mesh(OUT / f"{n}.stl"), "") for n, _ in JOBS]   # re-check the existing STLs
    else:
        res = [render(j) for j in JOBS]          # one OpenSCAD at a time keeps memory low
    report = {}
    meshes = {}
    for name, ok, err in res:
        m = trimesh.load(OUT / f"{name}.stl")
        meshes[name] = m
        ext = sorted(m.extents, reverse=True)
        report[name] = dict(single_clean_volume=ok, extents_mm=[round(float(x), 1) for x in m.extents],
                            volume_ml=round(float(m.volume) / 1000, 3),
                            fits_printer=all(e <= lim for e, lim in zip(ext, sorted(PRINTER, reverse=True))), error=err)
        print(name, report[name])

    levels = scad_levels()
    hip = trimesh.load(KIT / "01_hip_mount_plate.stl")
    report["plate_levels_mm"] = levels
    report["plate_clearance"] = plate_clearance(meshes["20_figure_body"], hip, levels)
    print("clearance", report["plate_clearance"])

    import tempfile
    with tempfile.TemporaryDirectory() as td:
        meshes["01_hip_mount_plate"] = hip
        for i, m in enumerate(posed_tail(td), 1):
            meshes[f"tail_{i}"] = m
    rows, total_g = tipping(meshes, levels, meshes["22_display_base"].bounds)
    report["tipping"] = rows
    report["display_mass_g"] = total_g
    print("tipping", rows)
    (OUT / "report.json").write_text(json.dumps(report, indent=1))


if __name__ == "__main__":
    main()
