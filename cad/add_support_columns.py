"""Overhang checker / break-away support columns for the life-size FDM STLs (Ender 3 V2 / Sprite Pro, 1.2 mm, PETG).

The vertebra bodies and hip mount are self-supporting by design (docs/printing.md), and this reports zero columns
for them. It still flags short roofs inside the caps and the tip adapter (spans of 14 mm or less), which Cura
bridges. So nothing is written unless you pass --write.

Built-in columns replace slicer supports (no tree/grid supports needed in Cura). Every part keeps its exported
print orientation; the columns are separate shells in the same STL, with a one-layer air gap above (and below,
when a column stands on the part) so they snap off.

Placement, per part:
- vertical rays on a 7 mm grid plus one through the centre of every overhang patch find each downward-facing
  surface steeper than OVERHANG_DEG with open space under it;
- spans shorter than MIN_SPAN (bolt holes, nut pockets) are left to the slicer to bridge;
- points within half a line width of the layer below (ledges and slopes under ~47 deg) are skipped;
- a column is dropped if it would pass within CLEAR of the part.

    PYTHONPATH=. ~/.venvs/costumebipedaltail/bin/python cad/add_support_columns.py
Report only by default; with --write: cad/stl/barney_supported/<part>.stl (+ report.json).
"""
import json
import sys
from pathlib import Path

import numpy as np
import trimesh

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "cad" / "stl" / "barney"
OUT = ROOT / "cad" / "stl" / "barney_supported"

LAYER = 0.6          # layer height (mm)
LINE = 1.3           # extrusion width (mm)
OVERHANG_DEG = 50.0  # steeper than this (from vertical) needs support
MIN_SPAN = 5.0       # open height below a ceiling before a column is worth it (mm)
GRID = 10.0          # column pitch (mm): ~7 mm bridges between tips
MIN_PITCH = 5.0      # closest two column tips may be (mm)
CLEAR = 0.8          # lateral clearance from the part (mm)
GAP = LAYER          # air gap to the part, top and bottom
TIP_R = LINE         # Ø2.6 contact tip
TIP_H = 2.0          # taper height from the column to the tip
FOOT_R, FOOT_H = 4.0, LAYER  # Ø8 bed foot, one layer
SEG = 12
MIN_GAP = 0.45       # every finished column must stay at least this far from the part (mm)


def _hits(mesh, xy, z0=-1.0):
    """All crossings of vertical rays through xy: list of (z, normal_z) sorted by z, per ray."""
    xy = np.atleast_2d(xy)
    org = np.column_stack([xy, np.full(len(xy), z0)])
    loc, ray, tri = mesh.ray.intersects_location(org, np.tile([0, 0, 1.0], (len(xy), 1)), multiple_hits=True)
    out = [[] for _ in range(len(xy))]
    for p, r, t in zip(loc, ray, tri):
        out[r].append((p[2], mesh.face_normals[t][2]))
    return [sorted(set((round(z, 4), nz) for z, nz in h)) for h in out]


def _solid_intervals(hits):
    """Solid [z_in, z_out] intervals along a ray from its crossings (entering faces point down)."""
    iv, z_in = [], None
    for z, nz in hits:
        if nz < 0 and z_in is None:
            z_in = z
        elif nz > 0 and z_in is not None:
            iv.append((z_in, z))
            z_in = None
    return iv


def _ring(c, r, n=8):
    a = np.linspace(0, 2 * np.pi, n, endpoint=False)
    return np.column_stack([c[0] + r * np.cos(a), c[1] + r * np.sin(a)])


def _inside_at(mesh, xy, z):
    """Is the part solid at height z above each xy (via the ray intervals)?"""
    res = []
    for h in _hits(mesh, xy):
        res.append(any(a - 1e-6 <= z <= b + 1e-6 for a, b in _solid_intervals(h)))
    return np.array(res)


def candidates(mesh):
    """(x, y, z_ceiling, z_floor) for every open span under a steep downward surface."""
    lo, hi = mesh.bounds
    gx = np.arange(lo[0] + GRID / 2, hi[0], GRID)
    gy = np.arange(lo[1] + GRID / 2, hi[1], GRID)
    pts = [np.array([x, y]) for x in gx for y in gy]
    # one extra point in the middle of every overhang patch, so small patches aren't missed
    ang = np.degrees(np.arcsin(np.clip(-mesh.face_normals[:, 2], -1, 1)))
    sel = np.where((ang > OVERHANG_DEG) & (mesh.triangles_center[:, 2] > LAYER))[0]
    if len(sel):
        for c in mesh.submesh([sel], append=True).split(only_watertight=False):
            if c.area > 4.0:
                pts.append(c.centroid[:2])
    pts = np.array(pts)
    thr = -np.sin(np.radians(OVERHANG_DEG))
    out = []
    for p, h in zip(pts, _hits(mesh, pts)):
        floor = 0.0
        for z_in, z_out in _solid_intervals(h):
            nz = next(n for z, n in h if z == z_in)
            if nz < thr and z_in - floor >= MIN_SPAN and z_in > LAYER:
                out.append((p[0], p[1], z_in, floor))
            floor = z_out
    return out


def plan_column(mesh, x, y, z_ceil, z_floor):
    """Column bottom/top/radius for one candidate, or None if it doesn't fit or isn't needed."""
    c = np.array([x, y])
    # self-supporting ledge: part material within half a line width, one layer below the ceiling
    # (half a line of overhang per 0.6 mm layer = 47 deg, matching OVERHANG_DEG)
    if _inside_at(mesh, _ring(c, LINE / 2, 8), z_ceil - LAYER).any():
        return None
    # tip: the lowest part surface over the tip footprint
    tops = []
    for h in _hits(mesh, np.vstack([c, _ring(c, TIP_R, 6)])):
        above = [a for a, b in _solid_intervals(h) if a >= z_ceil - 3.0]
        tops.append(min(above) if above else np.inf)
    top = min(tops) - GAP
    # bottom: the bed, or the highest part surface under the column footprint
    height_guess = top - z_floor
    r = 3.0 if height_guess > 45 else 2.5 if height_guess > 30 else 2.0
    if z_floor <= 0.0:
        bot = 0.0
    else:
        floors = []
        for h in _hits(mesh, np.vstack([c, _ring(c, r, 8)])):
            below = [b for a, b in _solid_intervals(h) if b <= z_floor + 3.0]
            floors.append(max(below) if below else 0.0)
        bot = max(floors) + GAP
    if top - bot < TIP_H + 2 * LAYER:
        return None
    # clearance: nothing solid within r + CLEAR around the shaft (up to where the taper starts), nor within
    # CLEAR of the narrow tip (sloped ceilings come down beside the tip, which is why it tapers)
    lo_z = bot - (GAP if bot > 0 else 0)

    def clear(ring_r, z0, z1):
        return not any(a < z1 and b > z0 for h in _hits(mesh, _ring(c, ring_r, 12)) for a, b in _solid_intervals(h))

    if not clear(TIP_R + CLEAR / 2, top - TIP_H, top + GAP / 2):
        return None
    for rr in sorted({r, 2.0, 1.6}, reverse=True):
        if clear(rr + CLEAR, lo_z, top - TIP_H + GAP):
            return dict(x=float(x), y=float(y), bot=float(bot), top=float(top), r=float(rr))
    return None


def column_mesh(col):
    """One watertight solid per column: a revolved profile (bed foot, shaft, tapered tip)."""
    x, y, bot, top, r = col["x"], col["y"], col["bot"], col["top"], col["r"]
    prof = [(0, bot)]
    if bot == 0.0 and col.get("foot", True):
        prof += [(FOOT_R, 0.0), (FOOT_R, FOOT_H), (r, FOOT_H + (FOOT_R - r))]   # 45 deg flare off the foot
    else:
        prof += [(r, bot)]
    prof += [(r, top - TIP_H), (TIP_R, top), (0, top)]
    m = trimesh.creation.revolve(np.array(prof, dtype=float), sections=SEG)
    m.apply_translation([x, y, 0])
    return m


def _fits(pq, col):
    """True if the finished column stays MIN_GAP clear of the part everywhere (sampled surface)."""
    m = column_mesh(col)
    pts = np.vstack([m.vertices, m.sample(300)])
    return pq.signed_distance(pts).max() < -MIN_GAP        # trimesh: positive inside the part


def support_part(path):
    mesh = trimesh.load(path)
    pq = trimesh.proximity.ProximityQuery(mesh)
    cols = []
    for x, y, zc, zf in candidates(mesh):
        col = plan_column(mesh, x, y, zc, zf)
        if not col or not all(np.hypot(col["x"] - o["x"], col["y"] - o["y"]) >= MIN_PITCH or
                              abs(col["top"] - o["top"]) > 3 for o in cols):
            continue
        if not _fits(pq, col):
            col["foot"] = False                                  # the bed foot may be what collides
            if not _fits(pq, col):
                continue
        cols.append(col)
    if not cols:
        return mesh, cols
    return trimesh.util.concatenate([mesh] + [column_mesh(c) for c in cols]), cols


def main():
    write = "--write" in sys.argv
    sys.argv = [a for a in sys.argv if a != "--write"]
    report = {}
    # ball halves print split-face down; their few steep spots are small and self-bridging, so they never get columns
    names = sys.argv[1:] or sorted(p.stem for p in SRC.glob("*.stl") if not p.stem.startswith("ball_"))
    for name in names:
        out_mesh, cols = support_part(SRC / f"{name}.stl")
        vol = sum(column_mesh(c).volume for c in cols) / 1000 if cols else 0.0
        report[name] = dict(columns=len(cols), column_volume_ml=round(float(vol), 2),
                            tallest_mm=round(max((c["top"] - c["bot"] for c in cols), default=0), 1),
                            on_part=sum(c["bot"] > 0 for c in cols))
        if cols and write:
            OUT.mkdir(parents=True, exist_ok=True)
            out_mesh.export(OUT / f"{name}.stl")
        print(name, report[name], flush=True)
    if not write:
        return
    rp = OUT / "report.json"
    old = json.loads(rp.read_text()) if rp.exists() and sys.argv[1:] else {}
    old.update(report)
    rp.write_text(json.dumps(old, indent=1))


if __name__ == "__main__":
    main()
