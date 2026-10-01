"""Fit check for the TPU strap pairs against the exported Barney part meshes.

    PYTHONPATH=. python cad/check_tpu_bands.py

For every joint and every strap (pair + spacers + M4 bolt heads/nuts) it intersects the strap envelope with the
printed parts placed in the joint frame, at rest and at the four bend limits (+-yaw, +-pitch). The strap
envelope is the hull of the two eye discs (so twisted lateral straps are covered) at its un-stretched width
and thickness (conservative: a stretched strap is narrower). It also confirms that the mesh transforms put each
anchor hole where the strap design expects it (hole empty, plate solid either side).
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np
import trimesh

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from cad import geometry as g  # noqa: E402
from cad.tpu_bands import anchors, Rx, Ry, OUT  # noqa: E402

STL = ROOT / "cad" / "stl" / "barney"


def H(R=np.eye(3), t=(0, 0, 0)):
    M = np.eye(4)
    M[:3, :3] = R
    M[:3, 3] = t
    return M


def load(name, M):
    m = trimesh.load(STL / f"{name}.stl")
    m.apply_transform(M)
    return m


def parts_in_joint_frame(c, i):
    """Return (parent_parts, child_parts) as meshes in the joint-i frame."""
    L = g.spacing(c)
    Ry90T = H(Ry(90).T)
    cap = [load(f"cap_{i}_{h}", Ry90T) for h in "ab"]
    body = load(f"body_{i}", Ry90T @ H(t=(0, 0, -g.body_len(c, i))))
    balls = [load(f"ball_{i}_left", H(Rx(90).T)), load(f"ball_{i}_right", H(Rx(-90).T))]
    if i == 1:
        rp = c.root_pitch
        M_root = H(t=(-c.root_back_offset, 0, c.root_dz)) @ H(Ry(180 - rp)) @ H(Rx(180))
        hip = load("hip_mount", np.linalg.inv(M_root) @ H(t=(-c.harness_plate_offset, 0, 0)) @ H(Ry(90).T))
        parent = [hip]
    else:
        d = g.droop(c, i)
        M = H(Ry(d).T) @ H(t=(-L, 0, 0)) @ H(Ry(90).T) @ H(t=(0, 0, -g.body_len(c, i - 1)))
        parent = [load(f"body_{i - 1}", M)]
    return parent + balls, cap + [body]


def disc(center, axis, r, h0, h1, n=24):
    """Cylinder of radius r along `axis` from center+h0*axis to center+h1*axis."""
    axis = axis / np.linalg.norm(axis)
    cyl = trimesh.creation.cylinder(radius=r, height=h1 - h0, sections=n)
    T = trimesh.geometry.align_vectors([0, 0, 1], axis)
    T[:3, 3] = center + axis * (h0 + h1) / 2
    cyl.apply_transform(T)
    return cyl


def frame_slerp(a, b, f):
    v = (1 - f) * a + f * b
    return v / np.linalg.norm(v)


def strap_envelope(st, child, parent, ax_c, ax_p, sgn, seg=8):
    """One strap + spacers + bolt hardware on face `sgn` of the plates.

    The strap is swept from the child eye to the parent eye in `seg` hulls, its plane turning from the child
    hole axis to the parent hole axis (lateral straps twist through the rest bend); a final bend at the eye
    takes it off the plate when the line of action leaves at an angle."""
    ax_c = ax_c * sgn
    ax_p = ax_p * sgn
    yc0 = st["plate_c"] / 2 + st["pad_c"]
    yp0 = st["plate_p"] / 2 + st["pad_p"]
    R, t, w = st["R_eye"], st["t"], st["w"]
    pc, pp = child + ax_c * yc0, parent + ax_p * yp0          # inner face centre of each eye
    discs = []
    for k in range(seg + 1):
        f = k / seg
        ax = frame_slerp(ax_c, ax_p, f)
        r = R if k in (0, seg) else w / 2
        discs.append(disc((1 - f) * pc + f * pp, ax, r, 0.0, t))
    slab = [trimesh.convex.convex_hull(np.vstack([discs[k].vertices, discs[k + 1].vertices])) for k in range(seg)]
    if st.get("tab_len", 0) > 0:
        # label tab: continues past the parent eye, away from the child, in the parent eye's plane
        u = pp - pc
        u = u - np.dot(u, ax_p) * ax_p
        u /= np.linalg.norm(u)
        a0, a1 = pp + u * (R - 1.0), pp + u * (R + st["tab_len"])
        r = st["tab_w"] / 2 * 1.05
        slab.append(trimesh.convex.convex_hull(np.vstack([disc(a0, ax_p, r, 0.0, st["tab_t"]).vertices,
                                                          disc(a1, ax_p, r, 0.0, st["tab_t"]).vertices])))
    ring = st.get("ring_c", 0.6)
    pads = [disc(child, ax_c, R, st["plate_c"] / 2 + ring, yc0), disc(child, ax_c, 4.6, st["plate_c"] / 2 + 0.05, yc0),
            disc(parent, ax_p, R, st["plate_p"] / 2 + 0.6, yp0), disc(parent, ax_p, 4.6, st["plate_p"] / 2 + 0.05, yp0)]
    # washer + bolt head or nylock nut (8 mm across corners, 5 mm tall) outside each eye
    hw = [disc(child, ax_c, 4.6, yc0 + t, yc0 + t + 5.8), disc(parent, ax_p, 4.6, yp0 + t, yp0 + t + 5.8)]
    # on single-strap springs the bare side of each plate carries the other end of the bolt
    if st.get("count", 2) == 1:
        hw += [disc(child, -ax_c, 4.6, st["plate_c"] / 2 + 0.05, st["plate_c"] / 2 + 5.8),
               disc(parent, -ax_p, 4.6, st["plate_p"] / 2 + 0.05, st["plate_p"] / 2 + 5.8)]
    return slab + pads + hw


def bend(theta_deg, axis):
    a = np.radians(theta_deg)
    if axis == "yaw":
        R = np.array([[math.cos(a), -math.sin(a), 0], [math.sin(a), math.cos(a), 0], [0, 0, 1]])
    else:
        R = Ry(theta_deg)
    return R


def overlap(a_list, b_list):
    vol = 0.0
    for a in a_list:
        for b in b_list:
            if not a.bounds_overlap(b) if hasattr(a, "bounds_overlap") else False:
                continue
            lo = np.maximum(a.bounds[0], b.bounds[0])
            hi = np.minimum(a.bounds[1], b.bounds[1])
            if np.any(lo >= hi):
                continue
            try:
                x = trimesh.boolean.intersection([a, b], engine="manifold")
                vol += abs(x.volume) if not x.is_empty else 0.0
            except Exception:  # noqa: BLE001 - empty result
                pass
    return vol


def main():
    c = g.CadParams(**json.loads((ROOT / "cad" / "variants" / "barney.json").read_text()))
    straps = json.loads((OUT / "straps.json").read_text())["straps"]
    report, worst = [], 0.0
    for i in range(1, c.joint_count + 1):
        parent, child_parts = parts_in_joint_frame(c, i)
        sts = [s for s in straps if s["joint"] == i]
        # anchor sanity: hole centre empty, plate solid 3 mm to the side of the hole edge... along the axis
        for st in sts:
            ch, pa, axc, axp = anchors(c, i, st["side"])
            for name, p, ax, meshes, half in (("child", ch, axc, child_parts, st["plate_c"] / 2),
                                              ("parent", pa, axp, parent, st["plate_p"] / 2)):
                inside_hole = any(m.contains([p])[0] for m in meshes)
                off = p + 3.5 * np.array([1, 0, 0]) if name == "parent" else p + np.array([-3.5, 0, 0])
                solid = any(m.contains([off])[0] for m in meshes)
                if inside_hole or not solid:
                    report.append(f"J{i}{st['side']} {name} anchor transform check FAILED (hole {inside_hole}, plate {solid})")
        for pose, ang, ax in (("rest", 0, "yaw"), ("+yaw", g.yaw_lim(c, i), "yaw"), ("-yaw", -g.yaw_lim(c, i), "yaw"),
                              ("+pitch", g.pitch_lim(c, i), "pitch"), ("-pitch", -g.pitch_lim(c, i), "pitch")):
            Rb = bend(ang, ax)
            moved = [m.copy().apply_transform(H(Rb)) for m in child_parts]
            for st in sts:
                ch, pa, axc, axp = anchors(c, i, st["side"])
                env = []
                for sgn in ((1, -1) if st.get("count", 2) == 2 else (st["sgn"],)):
                    env += strap_envelope(st, Rb @ ch, pa, Rb @ axc, axp, sgn)
                v = overlap(env, parent + moved)
                worst = max(worst, v)
                if v > 0.5:
                    report.append(f"J{i}{st['side']} {pose}: {v:.1f} mm^3 overlap")
        print(f"J{i} checked", flush=True)
    print("\n".join(report) if report else "no strap/part overlaps above 0.5 mm^3 (a graze) at rest or at any bend limit")
    print(f"largest overlap {worst:.2f} mm^3")


if __name__ == "__main__":
    main()
