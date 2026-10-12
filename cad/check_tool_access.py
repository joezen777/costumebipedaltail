"""Tool access for every fastener in the Barney tail: is there >= 50 mm of straight clear room past each bolt head?

    PYTHONPATH=. python cad/check_tool_access.py

For each bolt, at the assembly step where it is tightened (only the parts present at that step), a column is run
along the bolt axis outward from the top of the head, and the distance to the first object is measured. Holes
count: a column that passes through a hole (like the ball access holes) is clear. Two column sizes:
  * key   r = 1.6 mm: a 2.5 mm hex key (M4 button head, ISO 7380) or a 3 mm key for socket heads;
  * head  r = 3.8 mm: the head itself / a hex bit in a slim holder.
PASS = the key column is clear for >= 50 mm. M4 button heads: 7.6 mm diameter x 2.2 mm, on a 0.8 mm washer
where one is used.

Assembly stages (README "Assembly order"):
  ball-flange bolts: parent part + ball only (body i not yet on);
  cap bolts: parent + ball + body i + cap halves + clips (springs/straps not yet);
  strap bolts (both ends; the head may go on either face): the whole joint i plus its other straps;
  (no strap fasteners at the J2-J6 fin ends - those straps thread through the fin hole - and no tip-adapter
  screws: cord preload + tip clips)
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
from cad.check_assembly_rev3 import FLANGE_CLIPS, LOBE_CLIPS, flange_clip_in_ball_frame, lobe_clip_in_cap_frame  # noqa: E402
from cad.check_tpu_bands import H, Rx, Ry, STL, parts_in_joint_frame, strap_envelope  # noqa: E402
from cad.make_variant import BALL_ACCESS  # noqa: E402
from cad.tpu_bands import anchors  # noqa: E402

NEED = 50.0
HEAD_H, WASHER = 2.2, 0.8
R_KEY, R_HEAD = 1.6, 3.8


def perp(d):
    a = np.array([1.0, 0, 0]) if abs(d[0]) < 0.9 else np.array([0, 1.0, 0])
    u = np.cross(d, a)
    u /= np.linalg.norm(u)
    return u, np.cross(d, u)


def clear_length(origin, d, r, meshes, names, max_len=60.0, step=0.5):
    """Distance along d from origin until a column of radius r hits a mesh; (length, name of the obstacle)."""
    d = d / np.linalg.norm(d)
    u, v = perp(d)
    ring = [np.zeros(3)] + [r * (math.cos(q) * u + math.sin(q) * v) for q in np.linspace(0, 2 * math.pi, 16, endpoint=False)]
    ring += [0.5 * r * (math.cos(q) * u + math.sin(q) * v) for q in np.linspace(0, 2 * math.pi, 8, endpoint=False)]
    ring = np.array(ring)
    for s in np.arange(0.0, max_len + step, step):
        pts = origin + d * s + ring
        for m, n in zip(meshes, names):
            if m.contains(pts).any():
                return s, n
    return max_len, "-"


def rate(origin, d, meshes, names):
    lk, nk = clear_length(origin, d, R_KEY, meshes, names)
    lh, nh = clear_length(origin, d, R_HEAD, meshes, names)
    return lk, nk, lh, nh


def main():
    c = g.CadParams(**json.loads((ROOT / "cad" / "variants" / "barney.json").read_text()))
    straps = json.loads((ROOT / "cad" / "stl" / "barney_tpu_bands" / "straps.json").read_text())["straps"]
    lclip = trimesh.load(STL / "lobe_clip.stl")
    rows, fails = [], []

    def record(what, lk, nk, lh, nh, note="", insert=None, need_in=None):
        """PASS = >= 50 mm of straight key room past the head AND (if given) room to insert the bolt from that face."""
        ok = lk >= NEED and (insert is None or insert >= need_in)
        ins = "" if insert is None else f"; insert room {insert:4.1f} mm (bolt + head {need_in:.0f})"
        rows.append((what, lk, nk, lh, nh, ok, note + ins))
        print(f"{'ok  ' if ok else 'FAIL'} {what}: key {lk:4.1f} mm (stops at {nk}), head-size {lh:4.1f} mm ({nh}){ins} {note}",
              flush=True)
        if not ok:
            fails.append(what)

    for i in range(1, c.joint_count + 1):
        parent, child = parts_in_joint_frame(c, i)
        par, ball = parent[0], parent[1]
        caps, body = list(child[:2]), child[2]
        pname = "hip mount" if i == 1 else f"body {i - 1}"
        fclips = []
        if i in FLANGE_CLIPS:
            fc = trimesh.load(STL / f"flange_clip_{i}.stl")
            fclips = [flange_clip_in_ball_frame(fc, i, c, a) for a in FLANGE_CLIPS[i]]
        lclips = [lobe_clip_in_cap_frame(lclip, i, c, a) for a in LOBE_CLIPS.get(i, (45, 135, 225, 315))]
        d = g.droop(c, i)
        t = Ry(-d) @ np.array([1.0, 0, 0])

        # ball-flange bolts: head on the flange's neck side, turned through the ball's access hole
        stage = [par, ball] + fclips
        names = [pname, f"ball {i}"] + ["flange clip"] * len(fclips)
        for a in (45, 135, 225, 315):
            if a not in BALL_ACCESS["barney"][i - 1]:
                continue
            o = Ry(-d) @ (Rx(a) @ np.array([0, 0, g.flange_bolt_r(c, i)])) + Ry(-d) @ np.array([-g.DF(c, i), 0, 0])
            ins, _ = clear_length(o + t * 0.2, t, R_HEAD, stage, names)
            record(f"J{i} ball-flange bolt {a:3d} deg", *rate(o + t * HEAD_H, t, stage, names),
                   note="[dropped in and driven through the ball's access hole]", insert=ins, need_in=16 + HEAD_H)

        # cap bolts: head on the cap lobe's mouth-side face, axis -x
        stage = [par, ball, body] + caps + fclips + lclips
        names = [pname, f"ball {i}", f"body {i}", f"cap {i}a", f"cap {i}b"] + ["flange clip"] * len(fclips) + ["lobe clip"] * len(lclips)
        from cad.tpu_liners import _rdir
        child_parts = [body] + caps + lclips
        for a in (45, 135, 225, 315):
            seat = Rx(a) @ np.array([0, 0, g.bolt_pcd_r(c, i)]) + np.array([-g.cap_lobe_t(c) - WASHER, 0, 0])
            dvec = np.array([-1.0, 0, 0])
            res = rate(seat + dvec * HEAD_H, dvec, stage, names)
            ins, _ = clear_length(seat, dvec, R_HEAD, stage, names)
            note = "[joint at rest]"
            if res[0] < NEED or ins < 16 + HEAD_H:
                # the joint swings freely before the springs go on: find a bend (within the stops) that clears it
                lim = g.yaw_lim(c, i)
                for phi in range(0, 360, 30):
                    for ang in (0.5 * lim, 0.9 * lim):
                        Rm = _rdir(ang, phi)
                        moved = [m.copy().apply_transform(H(Rm)) for m in child_parts]
                        st2 = [par, ball] + fclips + moved
                        nm2 = [pname, f"ball {i}"] + ["flange clip"] * len(fclips) + [f"body {i}", f"cap {i}a", f"cap {i}b"] + ["lobe clip"] * len(lclips)
                        r2 = rate(Rm @ (seat + dvec * HEAD_H), Rm @ dvec, st2, nm2)
                        i2, _ = clear_length(Rm @ seat, Rm @ dvec, R_HEAD, st2, nm2)
                        if r2[0] >= NEED and i2 >= 16 + HEAD_H and (r2[0], i2) > (res[0], ins):
                            res, ins = r2, i2
                            tip = {0: "right", 90: "up", 180: "left", 270: "down"}.get(phi, f"{phi} deg from right toward up")
                            note = f"[bend the joint {ang:.0f} deg, child tipped {tip}, while tightening]"
                    if res[0] >= NEED and ins >= 16 + HEAD_H:
                        break
            record(f"J{i} cap bolt {a:3d} deg", *res, note=note, insert=ins, need_in=16 + HEAD_H)

        # strap bolts (both ends): either face may take the head
        mine = [s for s in straps if s["joint"] == i]
        base = [par, ball, body] + caps + fclips + lclips
        bnames = [pname, f"ball {i}", f"body {i}", f"cap {i}a", f"cap {i}b"] + ["flange clip"] * len(fclips) + ["lobe clip"] * len(lclips)
        for st in mine:
            others, onames = [], []
            for o2 in mine:
                if o2 is st:
                    continue
                ch2, pa2, c2, p2 = anchors(c, i, o2["side"])
                for sg in ((1, -1) if o2["count"] == 2 else (o2["sgn"],)):
                    env = strap_envelope(o2, ch2, pa2, c2, p2, sg)
                    others += env
                    onames += [f"strap {o2['label']}"] * len(env)
            ch, pa, axc, axp = anchors(c, i, st["side"])
            ends = [("cap-ear end", ch, axc, st["plate_c"], st["pad_c"])]
            if st.get("fin_end", "bolt") == "bolt":          # J2-J6 fin ends are threaded: no fastener there
                ends.append(("fin end" if i > 1 else "hip-arm end", pa, axp, st["plate_p"], st["pad_p"]))
            for (end, p, ax, plate, pad), L in zip(ends, (st["bolt_c"], st["bolt_p"])):
                best = None
                for face in (1, -1):
                    on_strap = st["count"] == 2 or face == st["sgn"]
                    off = plate / 2 + (pad + st["t"] if on_strap else 0) + WASHER
                    dvec = ax * face
                    res = rate(p + dvec * (off + HEAD_H), dvec, base + others, bnames + onames)
                    ins, _ = clear_length(p + dvec * off, dvec, R_HEAD, base + others, bnames + onames)
                    if best is None or (res[0], ins) > (best[1][0], best[2]):
                        best = (face, res, ins)
                face, res, ins = best
                fn = ("top/dorsal" if (ax * face)[2] > 0.5 else "bottom/ventral" if (ax * face)[2] < -0.5
                      else ("left" if (ax * face)[1] < 0 else "right"))
                record(f"J{i} strap {st['label']:5s} bolt, {end}", *res, note=f"[head on the {fn} face]",
                       insert=ins, need_in=L + HEAD_H)

    # The tip adapter's M3 screws are gone: their heads cannot even seat on the tip side (the plug is in the way)
    # and from inside body 6 a key gets only 46 mm. The adapter is held by the cord preload + 2 tip clips
    # (checked in cad/check_assembly_rev3.py).

    out = ROOT / "results" / "data" / "tool_access_check.txt"
    out.write_text("\n".join(f"{'ok  ' if ok else 'FAIL'} {w}: key {lk:.1f} mm ({nk}), head-size {lh:.1f} mm ({nh}) {note}"
                             for w, lk, nk, lh, nh, ok, note in rows) + f"\n\n{len(rows) - len(fails)}/{len(rows)} pass\n")
    print(f"\n{len(rows) - len(fails)}/{len(rows)} fasteners can be inserted and have >= {NEED:.0f} mm of straight key room; "
          f"failures: {len(fails)}")


if __name__ == "__main__":
    main()
