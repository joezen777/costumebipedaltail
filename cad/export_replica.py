"""1:8 scale snap-together resin replica kit of the Barney tail (Anycubic Photon Mono 5s).

Exports every kit piece from cad/openscad/mini_kit.scad as a print-ready STL (one clean volume
each) and checks it fits the printer.

    PYTHONPATH=. ~/.venvs/costumebipedaltail/bin/python cad/export_replica.py
Output: cad/stl/replica_1to8_resin/ (+ report.json)
"""
import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import trimesh

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "cad"))
from cad import geometry as g  # noqa: E402
from export_stl import clean_mesh, off_to_stl  # noqa: E402

SCAD = ROOT / "cad" / "openscad" / "mini_kit.scad"
OUT = ROOT / "cad" / "stl" / "replica_1to8_resin"
PRINTER = (218.0, 123.0, 200.0)
S = 1 / 8


def render(args):
    name, mini, idx = args
    path = OUT / f"{name}.stl"
    off = path.with_suffix(".off")
    cmd = ["openscad", "-o", str(off), "-D", f'MINI="{mini}"', "-D", f"INDEX={idx}", str(SCAD)]
    r = subprocess.run(cmd, capture_output=True, text=True, cwd=SCAD.parent)
    if r.returncode or not off.exists():
        return name, False, r.stderr[-300:]
    off_to_stl(off, path)
    return name, clean_mesh(path), ""


def band_spans(p):
    """Peg-to-peg distance of the elastics per joint (mm, 1:8)."""
    out = []
    for j in range(1, p.joint_count + 1):
        Rb = max(g.RB(p, j) * S, 2.4)
        apm = max(g.spring_span_parent(p, j) * S, 0.45 * Rb + 1.4 + 2.5)
        out.append(round(apm - 0.6, 1))
    return out


def main():
    p = g.CadParams(**json.loads((ROOT / "cad" / "variants" / "barney.json").read_text()))
    n = p.joint_count
    OUT.mkdir(parents=True, exist_ok=True)
    jobs = [("00_snap_test_coupon", "coupon", 1), ("01_hip_mount_plate", "hip", 1), ("99_display_stand", "stand", 1)]
    jobs += [(f"{10 + i:02d}_vertebra_{i}", "vertebra", i) for i in range(1, n + 1)]
    with ThreadPoolExecutor(4) as ex:
        res = list(ex.map(render, jobs))
    report = {"band_spans_mm": band_spans(p)}
    for name, ok, err in res:
        m = trimesh.load(OUT / f"{name}.stl")
        ext = sorted(m.extents, reverse=True)
        report[name] = dict(single_clean_volume=ok, extents_mm=[round(float(x), 1) for x in m.extents],
                            volume_ml=round(float(m.volume) / 1000, 3),
                            fits_printer=all(e <= lim for e, lim in zip(ext, sorted(PRINTER, reverse=True))), error=err)
        print(name, report[name])
    (OUT / "report.json").write_text(json.dumps(report, indent=1))
    print("band spans", report["band_spans_mm"])


if __name__ == "__main__":
    main()
