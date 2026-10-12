"""Assembly checks for revision 3 (2026-10): one-piece balls with long-hex-key access holes, bowtie-keyed caps,
lobe clips (cap <-> body) and flange clips (ball <-> parent body). All on the exported meshes, in each joint frame.

    PYTHONPATH=. python cad/check_assembly_rev3.py

1. Neck intact: the one-piece ball removes no material outside the ball sphere compared with the old clamshell
   ball (the access holes may only cut the sphere), apart from the flange bolt holes themselves.
2. Every listed access hole is a clear straight shaft from the bolt seat up and out of the ball, wide enough to drop
   an M4 socket head (7 mm) and run a hex key; the parent part is not in the way.
3. Key pockets: >= 0.8 mm of cap material round every pocket wall (no break-through into the cavity, the roll-key
   slot, ears or lobes).
4. Bowtie keys go straight in from the mouth face: the key swept from 15 mm outside to home hits nothing.
5. Lobe clips and flange clips: at home they touch only their lobes / flanges (snap interference, small); the
   radial push-on path hits nothing else; they keep clear of the TPU straps.
"""
from __future__ import annotations

import json
import math
import subprocess
import sys
from pathlib import Path

import numpy as np
import trimesh

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from cad import geometry as g  # noqa: E402
from cad.check_tpu_bands import H, Rx, Ry, STL, ball_print_matrix, overlap, parts_in_joint_frame  # noqa: E402
from cad.make_variant import BALL_ACCESS  # noqa: E402

SCR = ROOT / "scratch" / "rev3_check"
CAP_SPLIT = g.CAP_SPLIT_DEG
LOBE_R = 2.25 + 2 * 1.3 + 0.5          # geometry.lobe_r
FLANGE_CLIPS = {2: (22.5, 337.5), 3: (22.5, 337.5), 4: (22.5, 337.5), 5: (157.5, 202.5), 6: (157.5, 202.5)}
# lobe clips per joint; on J6 the TPU straps' bolt nuts at the cap ear sit next to the two dorsal-side lobes
LOBE_CLIPS = {6: (135, 225)}


def old_ball(c, i):
    """The previous clamshell ball (from git) as one solid in the ball frame."""
    SCR.mkdir(parents=True, exist_ok=True)
    out = []
    for side, R in (("left", Rx(90).T), ("right", Rx(-90).T)):
        f = SCR / f"ball_{i}_{side}.stl"
        if not f.exists():
            f.write_bytes(subprocess.run(["git", "show", f"8ef84ec:cad/stl/barney/ball_{i}_{side}.stl"], cwd=ROOT,
                                         capture_output=True, check=True).stdout)
        m = trimesh.load(f)
        m.apply_transform(H(R))
        out.append(m)
    return trimesh.boolean.union(out, engine="manifold")


def key_dims(c, i, seam):
    """Mirror of the OpenSCAD key functions (suit_tail.scad, 'bowtie keys')."""
    ch, RS, capR = g.cap_h(c, i), g.RS(c, i), g.cap_outer_r(c, i)
    body = seam == 0 and g.RB(c, i) <= 22
    if body:
        D, rin, w1 = 6.0, RS, min(5, capR - RS - 2.3)
    else:
        D = min(6, ch - 7)
        z = ch - D
        s45 = math.sin(math.radians(45))
        rin = RS * s45 - (z - RS * s45) if z > RS * s45 else math.sqrt(RS * RS - z * z)
        w1 = min(6, capR - rin - 3)
    return dict(D=D, w1=w1, w0=0.55 * w1, rk=(rin + capR) / 2, L=4.5, Ld=2.5 if body else 4.5, body=body,
                x_home=-D if body else -ch)


def bowtie(k, grow=0.0, depth=None, x0=None, seam=0):
    """Bowtie prism in the cap frame at seam `seam` (0/180), grown by `grow` mm, from x0 over `depth` (+x)."""
    import manifold3d as m3
    w0, w1, L, Ld = k["w0"] / 2, k["w1"] / 2, k["L"], k["Ld"]
    wd = w0 + (w1 - w0) * Ld / L
    poly = np.array([[-w1, -L], [-w0, 0], [-wd, Ld], [wd, Ld], [w0, 0], [w1, -L]])[::-1]   # counter-clockwise
    cs = m3.CrossSection([poly])
    if grow:
        cs = cs.offset(grow, m3.JoinType.Miter)
    mesh = m3.Manifold.extrude(cs, depth).to_mesh()
    tm = trimesh.Trimesh(np.asarray(mesh.vert_properties)[:, :3], np.asarray(mesh.tri_verts))
    # profile X = radial (-> +z), Y = across the seam (-> +y, toward dorsal), extrusion -> +x; as OpenSCAD's
    # rotate([0, 90, 0]) linear_extrude (X -> -z: the profile is symmetric in X)
    M = np.array([[0, 0, 1], [0, 1, 0], [-1, 0, 0]], float)
    tm.apply_transform(H(M, (x0, 0, k["rk"])))
    tm.apply_transform(H(Rx(CAP_SPLIT + seam)))
    return tm


def lobe_clip_in_cap_frame(clip, i, c, a, push=0.0):
    t = Rx(a) @ np.array([0, 1.0, 0])
    r = Rx(a) @ np.array([0, 0, 1.0])
    M = np.c_[t, r, np.array([1.0, 0, 0])]
    m = clip.copy()
    m.apply_transform(H(M, r * (g.bolt_pcd_r(c, i) + push) + np.array([-5.0, 0, 0])))
    return m


def flange_clip_in_ball_frame(clip, i, c, a, push=0.0):
    d = g.droop(c, i)
    e = Ry(-d) @ np.array([1.0, 0, 0])
    r = Ry(-d) @ (Rx(a) @ np.array([0, 0, 1.0]))
    t = Ry(-d) @ (Rx(a) @ np.array([0, 1.0, 0]))
    M = np.c_[e, r, -t]
    O = Ry(-d) @ np.array([-(g.DF(c, i) + g.flange_t(c)), 0, 0])
    m = clip.copy()
    m.apply_transform(H(M, O + r * (g.flange_r(c, i) + push) + t * 3.0))
    return m


def main():
    c = g.CadParams(**json.loads((ROOT / "cad" / "variants" / "barney.json").read_text()))
    clip = trimesh.load(STL / "lobe_clip.stl")
    straps = json.loads((ROOT / "cad" / "stl" / "barney_tpu_bands" / "straps.json").read_text())["straps"]
    from cad.check_tpu_bands import strap_envelope
    from cad.tpu_bands import anchors
    fails = []

    def rep(ok, msg):
        print(("ok   " if ok else "FAIL ") + msg, flush=True)
        if not ok:
            fails.append(msg)

    joints = [int(x) for x in sys.argv[1:]] or range(1, c.joint_count + 1)
    for i in joints:
        parent, child = parts_in_joint_frame(c, i)
        par, ball, caps, body = parent[0], parent[1], child[:2], child[2]
        RB, df = g.RB(c, i), g.DF(c, i)
        # 1. neck intact
        old = old_ball(c, i)
        removed = trimesh.boolean.difference([old, ball], engine="manifold")
        sph = trimesh.creation.icosphere(subdivisions=4, radius=RB + 0.05)
        outside = trimesh.boolean.difference([removed, sph], engine="manifold") if not removed.is_empty else removed
        # discount the flange slab (bolt holes are unchanged there)
        d = g.droop(c, i)
        slab = trimesh.creation.box(extents=[g.flange_t(c) + 0.2, 200, 200])
        slab.apply_transform(H(Ry(-d), Ry(-d) @ np.array([-df - g.flange_t(c) / 2, 0, 0])))
        v_out = 0.0 if outside.is_empty else trimesh.boolean.difference([outside, slab], engine="manifold").volume
        rep(v_out < 1.0, f"J{i} neck intact: material removed outside the ball sphere = {v_out:.2f} mm^3")
        # 2. access shafts
        t = Ry(-d) @ np.array([1.0, 0, 0])
        for a in BALL_ACCESS["barney"][i - 1]:
            o = Ry(-d) @ (Rx(a) @ np.array([0, 0, g.flange_bolt_r(c, i)]))
            p0 = Ry(-d) @ np.array([-df, 0, 0]) + o
            Lsh = df + RB + 15
            cyl = trimesh.creation.cylinder(radius=3.6, height=Lsh, sections=32)
            T = trimesh.geometry.align_vectors([0, 0, 1], t)
            T[:3, 3] = p0 + t * (Lsh / 2 + 0.3)
            cyl.apply_transform(T)
            v = overlap([cyl], [ball, par])
            rep(v < 0.5, f"J{i} access shaft az {a}: 7.2 mm column from the bolt seat out of the ball hits {v:.2f} mm^3")
        # 3. key pockets keep 0.8 mm walls; 4. keys can be pushed home
        cap_union = trimesh.boolean.union(caps, engine="manifold")
        for seam in (0, 180):
            k = key_dims(c, i, seam)
            x0 = k["x_home"]
            # grown shell reaches 0.8 mm past the pocket's closed end; the pocket itself opens past the open face
            big = bowtie(k, grow=0.8, depth=k["D"] + 0.8, x0=x0 - 0.8 if k["body"] else x0, seam=seam)
            pocket = bowtie(k, grow=0.15, depth=k["D"] + 0.01, x0=x0 if k["body"] else x0 - 0.01, seam=seam)
            # clip the grown shell to the cap's x range so the open face is not counted
            shell = trimesh.boolean.difference([big, pocket], engine="manifold")
            keep = trimesh.creation.box(extents=[g.cap_h(c, i), 300, 300])
            keep.apply_translation([-g.cap_h(c, i) / 2, 0, 0])
            shell = trimesh.boolean.intersection([shell, keep], engine="manifold")
            lost = shell.volume - overlap([shell], [cap_union])
            face = "body-side face" if k["body"] else "mouth face"
            rep(lost < 2.0, f"J{i} key pocket seam {seam} ({face}): wall material missing within 0.8 mm = {lost:.2f} mm^3 "
                            f"(D {k['D']:.1f}, w {k['w0']:.1f}/{k['w1']:.1f}, r {k['rk']:.1f})")
            # the key (length D - 0.3) must have room to be held just outside the pocket and pushed straight home:
            # mouth face: from 2 mm beyond its own length, with the cap bolted to the body;
            # body-side face: before the cap slides onto the body (body absent), cap halves closed on the neck.
            Lk = k["D"] - 0.3
            sgn = 1 if k["body"] else -1
            obstacles = caps + [ball, par] + ([] if k["body"] else [body])
            worst = max(overlap([bowtie(k, grow=-0.15, depth=Lk, x0=x0 + sgn * dx, seam=seam)], obstacles)
                        for dx in np.arange(0, Lk + 2.5, 0.5))
            rep(worst < 0.5, f"J{i} key seam {seam}: held {Lk + 2:.0f} mm out and pushed straight in from the {face}: "
                             f"hits {worst:.2f} mm^3")
        # 5a. lobe clips
        for a in LOBE_CLIPS.get(i, (45, 135, 225, 315)):
            home = lobe_clip_in_cap_frame(clip, i, c, a)
            snap = overlap([home], caps + [body])
            other = overlap([home], [ball, par])
            path = max(overlap([lobe_clip_in_cap_frame(clip, i, c, a, push)], [ball, par]) for push in (3, 6, 10))
            free = overlap([lobe_clip_in_cap_frame(clip, i, c, a, 12)], caps + [body])
            rep(other < 0.05 and path < 0.05 and free < 0.05 and snap < 30,
                f"J{i} lobe clip az {a}: snap interference with the lobes {snap:.1f} mm^3; ball/parent {other:.2f}; "
                f"path {path:.2f}; clear when pulled off 12 mm {free:.2f}")
        # straps vs lobe clips (rest pose)
        env = []
        for st in [s for s in straps if s["joint"] == i]:
            ch, pa, axc, axp = anchors(c, i, st["side"])
            for sgn in ((1, -1) if st["count"] == 2 else (st["sgn"],)):
                env += strap_envelope(st, ch, pa, axc, axp, sgn)
        v = overlap([lobe_clip_in_cap_frame(clip, i, c, a) for a in LOBE_CLIPS.get(i, (45, 135, 225, 315))], env)
        rep(v < 0.05, f"J{i} lobe clips vs TPU straps: {v:.2f} mm^3")
        # 5b. flange clips
        if i in FLANGE_CLIPS:
            fclip = trimesh.load(STL / f"flange_clip_{i}.stl")
            for a in FLANGE_CLIPS[i]:
                home = flange_clip_in_ball_frame(fclip, i, c, a)
                snap = overlap([home], [ball, par])
                others = overlap([home], caps + [body])
                path = max(overlap([flange_clip_in_ball_frame(fclip, i, c, a, push)], caps + [body]) for push in (3, 6))
                free = overlap([flange_clip_in_ball_frame(fclip, i, c, a, 8)], [ball, par])
                rep(snap < 30 and others < 0.05 and path < 0.05 and free < 0.05,
                    f"J{i} flange clip az {a}: clamp/snap overlap with the two flanges {snap:.1f} mm^3; cap/body {others:.2f}; "
                    f"path {path:.2f}; clear when pulled off 8 mm {free:.2f}")
            v = overlap([flange_clip_in_ball_frame(fclip, i, c, a) for a in FLANGE_CLIPS[i]], env)
            rep(v < 0.05, f"J{i} flange clips vs TPU straps: {v:.2f} mm^3")
    print("\nALL OK" if not fails else f"\n{len(fails)} FAILED")


if __name__ == "__main__":
    main()
