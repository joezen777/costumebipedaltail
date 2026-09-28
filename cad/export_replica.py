"""1:8 scale resin display replica of the Gojira tail (Anycubic Photon Mono 5s).

A scaled-down *functional* tail is not buildable (M4 holes become 0.56 mm, balls and springs
cannot be assembled), so the replica is a static, single-piece display model:

  replica_mechanism_1to8.stl  the real Gojira print STLs assembled in the rest pose, with the
                              central cord and the 30 springs as solid rods, joined into ONE solid
  replica_skinned_1to8.stl    the finished look: foam-skin envelope + dorsal plates + foam tip
  replica_stand_1to8.stl      floor plate + post; glue the hip-mount plate to the post face

    PYTHONPATH=. ~/.venvs/costumebipedaltail/bin/python cad/export_replica.py
Output: cad/stl/replica_1to8_resin/ (+ README.md there).
"""
import json
import math
import sys
from pathlib import Path

import numpy as np
import trimesh

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from cad import geometry as g  # noqa: E402

SRC = ROOT / "cad" / "stl" / "gojira"
OUT = ROOT / "cad" / "stl" / "replica_1to8_resin"
SCALE = 1 / 8
NUDGE = 0.15      # mm (full scale): pushes flush-mounted parts into each other so the union is one solid
PRINTER = (218.0, 123.0, 200.0)   # Photon Mono 5s build volume, mm


def T(x=0, y=0, z=0):
    m = np.eye(4); m[:3, 3] = (x, y, z); return m


def Ry(deg):
    c, s = math.cos(math.radians(deg)), math.sin(math.radians(deg))
    m = np.eye(4); m[:3, :3] = [[c, 0, s], [0, 1, 0], [-s, 0, c]]; return m


def Rx(deg):
    c, s = math.cos(math.radians(deg)), math.sin(math.radians(deg))
    m = np.eye(4); m[:3, :3] = [[1, 0, 0], [0, c, -s], [0, s, c]]; return m


def root_frame(p):
    th = math.radians(p.root_pitch)
    ex, ez = np.array([-math.cos(th), 0, -math.sin(th)]), np.array([-math.sin(th), 0, math.cos(th)])
    m = np.eye(4); m[:3, 0], m[:3, 1], m[:3, 2] = ex, np.cross(ez, ex), ez
    m[:3, 3] = (-p.root_back_offset, 0, 0)
    return m


def frames(p):
    """Rest frame of vertebra i (pivot i at origin), pelvis frame, mm."""
    F = {1: root_frame(p)}
    for i in range(2, p.joint_count + 1):
        F[i] = F[i - 1] @ T(g.spacing(p)) @ Ry(g.droop(p, i))
    return F


def load(name, M):
    m = trimesh.load(SRC / f"{name}.stl")
    m.apply_transform(M)
    return m


def rod(a, b, r, sections=16):
    a, b = np.asarray(a, float), np.asarray(b, float)
    seg = trimesh.creation.cylinder(radius=r, segment=np.vstack([a, b]), sections=sections)
    ends = [trimesh.creation.icosphere(subdivisions=1, radius=r).apply_translation(x) for x in (a, b)]
    return [seg] + ends


def pt(M, v):
    return (M @ np.r_[v, 1.0])[:3]


def mechanism(p):
    F = frames(p)
    n, L = p.joint_count, g.spacing(p)
    parts = [load("hip_mount", T(-p.harness_plate_offset) @ Ry(-90))]
    for i in range(1, n + 1):
        Fi = F[i]
        parent_x = (F[i - 1] if i > 1 else F[1])[:3, 0]
        shift = T(*(-NUDGE * parent_x))
        # ball of joint i (both clamshell halves), nudged into the parent flange
        parts += [load(f"ball_{i}_left", shift @ Fi @ Rx(-90)), load(f"ball_{i}_right", shift @ Fi @ Rx(90))]
        # vertebra body and its cap (cap nudged into the body face)
        parts.append(load(f"body_{i}", Fi @ Ry(-90) @ T(0, 0, -g.body_len(p, i))))
        parts.append(load(f"cap_{i}", Fi @ T(NUDGE) @ Ry(-90)))
    parts.append(load("tip_adapter", F[n] @ T(g.body_len(p, n) + NUDGE) @ Ry(90)))
    # foam tip (solid cone) on the tip adapter
    tl = p.tail_length - p.mech_length
    cone = trimesh.creation.cone(radius=p.last_mech_diameter / 2, height=tl, sections=48)
    cone.apply_transform(F[n] @ T(L - 1) @ Ry(90))
    parts.append(cone)
    # central cord (Ø6 mm) through every ball centre - also ties each ball to its socket
    pf = g.DF(p, 1) + g.flange_t(p)
    pts = [pt(F[1], [-pf - 20, 0, 0])] + [F[i][:3, 3] for i in range(1, n + 1)] + [pt(F[n], [L + 10, 0, 0])]
    for a, b in zip(pts[:-1], pts[1:]):
        parts += rod(a, b, g.bore_r(p) + 0.3)    # fills the Ø8 bores: fuses balls, sockets and spines into one piece
    # the springs: parent anchor -> cap ear, per joint (dorsal + left + right)
    for i in range(1, n + 1):
        w, par = g.spring_arm(p, i), (F[i - 1] if i > 1 else F[1])
        xp = (L - g.spring_span_parent(p, i)) if i > 1 else -g.spring_span_parent(p, 1)
        r = max(g.coil_od(p, i) / 2 * 0.7, 2.4)          # >= 0.3 mm after scaling
        for off in ([0, w, 0], [0, -w, 0], [0, 0, w]):
            a = pt(par, [xp, off[1], off[2]])
            b = pt(F[i], [-p.cap_ear_x, off[1], off[2]])
            parts += rod(a, b, r)
    return parts


def skinned(p):
    """Finished-look envelope (same construction as the physics pose renders)."""
    from experiments.pose_renders import tube_mesh
    F = frames(p)
    n, L = p.joint_count, g.spacing(p)
    tl = p.tail_length - p.mech_length
    pts = [pt(F[1], [-70.0, 0, 0])] + [F[i][:3, 3] for i in range(1, n + 1)] + \
          [pt(F[n], [L, 0, 0]), pt(F[n], [L + tl, 0, 0])]
    radii = [100.0] + [g.D(p, i) / 2 for i in range(1, n + 1)] + [p.last_mech_diameter / 2, p.tip_diameter / 2]
    V, Fc = tube_mesh(np.array(pts), np.array(radii), sides=48)
    sides = 48
    # close the root end with a fan so the tube is watertight
    V = np.vstack([V, pts[0]])
    c0 = len(V) - 1
    Fc = np.vstack([Fc, [[c0, (s + 1) % sides, s] for s in range(sides)]])
    tube = trimesh.Trimesh(V, Fc, process=True)
    trimesh.repair.fix_normals(tube)
    parts = [tube]
    # dorsal plates along the first 60 % of the tail (flattened ellipsoids)
    for k in range(int(0.6 * n)):
        a, b = F[k + 1][:3, 3], (F[k + 2][:3, 3] if k + 2 <= n else pt(F[n], [L, 0, 0]))
        d = (b - a) / np.linalg.norm(b - a)
        up = F[k + 1][:3, 2]
        for f in (0.3, 0.75):
            c = a + f * (b - a) + up * (g.D(p, k + 1) / 2 * 0.85)
            s = 45 - 3 * k
            e = trimesh.creation.icosphere(subdivisions=3, radius=1.0)
            e.apply_scale([s * 0.8, 6.0, s])
            R = np.eye(4); R[:3, 0], R[:3, 1], R[:3, 2] = d, np.cross(up, d), up
            e.apply_transform(T(*c) @ R)
            parts.append(e)
    # the harness plate the tail hangs from (for gluing to the stand)
    plate = trimesh.creation.box(extents=[p.hip_plate_t, p.hip_plate_w, p.hip_plate_h])
    plate.apply_translation([-p.harness_plate_offset - p.hip_plate_t / 2, 0, 0])
    parts.append(plate)
    return parts


def stand(p):
    """Floor plate + post (full-scale mm, pelvis frame; floor at z = -0.55 * 1727)."""
    floor = -0.55 * 1727
    base = trimesh.creation.box(extents=[1550, 300, 24])
    base.apply_translation([-725 + 50, 0, floor + 12])
    post = trimesh.creation.box(extents=[80, 160, (p.hip_plate_h / 2 + 10) - floor])
    post.apply_translation([-p.harness_plate_offset + 40, 0, (floor + p.hip_plate_h / 2 + 10) / 2])
    return [base, post]


def finish(parts, name):
    m = trimesh.boolean.union(parts, engine="manifold")
    bodies = m.split(only_watertight=False)
    m = trimesh.util.concatenate([b for b in bodies if abs(b.volume) > 1.0])   # drop zero-volume slivers
    m.apply_scale(SCALE)
    m.apply_translation(-m.bounds[0])                       # sit on z = 0, positive octant
    ext = m.extents
    fits = all(e <= lim for e, lim in zip(sorted(ext, reverse=True), sorted(PRINTER, reverse=True)))
    OUT.mkdir(parents=True, exist_ok=True)
    m.export(OUT / name)
    return dict(file=name, bodies=len(m.split(only_watertight=False)), watertight=bool(m.is_watertight),
                extents_mm=[round(float(x), 1) for x in ext], volume_ml=round(float(m.volume) / 1000, 2), fits_printer=fits)


def main():
    p = g.CadParams(**json.loads((ROOT / "cad" / "variants" / "gojira.json").read_text()))
    report = [finish(mechanism(p), "replica_mechanism_1to8.stl"),
              finish(skinned(p), "replica_skinned_1to8.stl"),
              finish(stand(p), "replica_stand_1to8.stl")]
    (OUT / "report.json").write_text(json.dumps(report, indent=1))
    for r in report:
        print(r)


if __name__ == "__main__":
    main()
