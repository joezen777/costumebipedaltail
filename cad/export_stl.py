"""Export every printable part as a print-oriented STL and report size/mass.

    python3 cad/export_stl.py [--jobs 4] [--only body_1,cap_1]

Outputs cad/stl/full/*.stl, cad/stl/test_section/*.stl (symlink-free copies)
and cad/stl/parts.json with bounding boxes, volumes and estimated masses.
"""
import argparse
import json
import shutil
import struct
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent
SCAD = ROOT / "openscad" / "suit_tail.scad"
OUT = ROOT / "stl"
sys.path.insert(0, str(ROOT.parent))
from cad.geometry import CadParams  # noqa: E402

PETG = 1.27e-3          # g/mm^3
MAX = 200.0


def parts(n):
    out = [("hip_mount", "print_hip_mount", 1), ("tip_adapter", "print_tip_adapter", 1),
           ("test_ballast_plate", "print_test_ballast_plate", 1)]
    for i in range(1, n + 1):
        out += [(f"ball_{i}_left", "print_ball_left", i), (f"ball_{i}_right", "print_ball_right", i),
                (f"cap_{i}", "print_cap", i), (f"body_{i}", "print_body", i)]
    return out


def read_stl(path):
    data = path.read_bytes()
    if data[:5] == b"solid" and b"facet" in data[:400]:
        v = []
        for line in data.decode(errors="ignore").splitlines():
            line = line.strip()
            if line.startswith("vertex"):
                v.append([float(x) for x in line.split()[1:4]])
        return np.array(v).reshape(-1, 3, 3)
    n = struct.unpack("<I", data[80:84])[0]
    arr = np.frombuffer(data[84:84 + n * 50], dtype=np.dtype([("n", "<f4", 3), ("v", "<f4", (3, 3)), ("a", "<u2")]))
    return arr["v"].astype(float)


def mesh_stats(path):
    tri = read_stl(path)
    vol = float(np.einsum("ij,ij->i", tri[:, 0], np.cross(tri[:, 1], tri[:, 2])).sum() / 6)
    area = float(0.5 * np.linalg.norm(np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0]), axis=1).sum())
    lo, hi = tri.reshape(-1, 3).min(0), tri.reshape(-1, 3).max(0)
    return dict(volume_cm3=abs(vol) / 1000, area_cm2=area / 100, bbox_mm=[round(float(x), 1) for x in hi - lo],
                min_z=float(lo[2]))


def estimate_mass(st, perimeters=3, line=1.3, infill=0.20):
    """Shell (perimeters + top/bottom) is solid, the core is infilled."""
    shell = min(st["area_cm2"] * perimeters * line / 10 / 2, st["volume_cm3"])   # area counts both faces of thin walls
    core = max(st["volume_cm3"] - shell, 0)
    return (shell + infill * core) * PETG * 1000


def to_binary_stl(path):
    """OpenSCAD writes ASCII STL; store binary (about 5x smaller, same triangles)."""
    tri = read_stl(path)
    if path.read_bytes()[:5] != b"solid":
        return
    n = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    n /= np.maximum(np.linalg.norm(n, axis=1), 1e-12)[:, None]
    rec = np.zeros(len(tri), dtype=np.dtype([("n", "<f4", 3), ("v", "<f4", (3, 3)), ("a", "<u2")]))
    rec["n"], rec["v"] = n, tri
    with open(path, "wb") as f:
        f.write(b"suit tail binary STL".ljust(80, b" "))
        f.write(struct.pack("<I", len(tri)))
        f.write(rec.tobytes())


VARIANT = ""


def full_dir():
    return OUT / (VARIANT if VARIANT else "full")


def scad_file():
    return ROOT / "openscad" / (f"suit_tail_{VARIANT}.scad" if VARIANT else "suit_tail.scad")


def render(name, part, idx, force=False):
    path = full_dir() / f"{name}.stl"
    if path.exists() and not force:
        return name, path, "cached"
    path.parent.mkdir(parents=True, exist_ok=True)
    cmd = ["openscad", "-o", str(path), "-D", f'PART="{part}"', "-D", f"INDEX={idx}", str(scad_file())]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode or not path.exists():
        return name, path, "FAILED: " + r.stderr[-400:]
    to_binary_stl(path)
    return name, path, "ok"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--jobs", type=int, default=4)
    ap.add_argument("--only", default="")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--variant", default="")
    a = ap.parse_args()
    global VARIANT
    VARIANT = a.variant
    p = CadParams(**json.loads((ROOT / "variants" / f"{VARIANT}.json").read_text())) if VARIANT else CadParams()
    todo = parts(p.joint_count)
    if a.only:
        keep = set(a.only.split(","))
        todo = [t for t in todo if t[0] in keep]
    with ThreadPoolExecutor(a.jobs) as ex:
        res = list(ex.map(lambda t: render(*t, force=a.force), todo))
    report = {}
    for name, path, status in res:
        if not status.startswith("ok") and status != "cached":
            print(name, status)
            continue
        st = mesh_stats(path)
        st["mass_g"] = round(estimate_mass(st), 1)
        st["fits_200mm"] = all(x <= MAX for x in st["bbox_mm"])
        st["on_bed"] = abs(st["min_z"]) < 0.05
        report[name] = st
        print(f"{name:22s} {status:6s} bbox {st['bbox_mm']} vol {st['volume_cm3']:.1f} cm3 ~{st['mass_g']:.0f} g"
              f" {'OK' if st['fits_200mm'] and st['on_bed'] else 'CHECK'}")
    pj = OUT / (f"parts_{VARIANT}.json" if VARIANT else "parts.json")
    old = json.loads(pj.read_text()) if pj.exists() else {}
    old.update(report)
    pj.write_text(json.dumps(old, indent=1))
    # 4-joint test-section kit
    ts = OUT / (f"{VARIANT}_test_section" if VARIANT else "test_section")
    ts.mkdir(exist_ok=True)
    kit = ["hip_mount", "test_ballast_plate"] + [f"{k}_{i}{s}" for i in range(1, 5) for k, s in
                                                 (("ball", "_left"), ("ball", "_right"), ("cap", ""), ("body", ""))]
    for k in kit:
        src = full_dir() / f"{k}.stl"
        if src.exists():
            shutil.copy2(src, ts / f"{k}.stl")


if __name__ == "__main__":
    main()
