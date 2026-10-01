"""Mesh check for the cap-mouth bumper rings (cad/tpu_liners.py) on the exported Barney parts.

    PYTHONPATH=. python cad/check_tpu_liners.py

Per joint and bend direction (+-yaw, +-pitch), with the ring on the cap's outer face:
- 0.3 deg inside the stop: the ring touches neither the ball/neck nor the parent flange's bolt heads;
- 1.0 deg past the stop: the neck is into the TPU ring while the PETG cap rim is still clear (PETG never touches
  PETG at the stop);
- at the stop, the ring and the parent ball flange + M4 heads (7 x 4 mm) stay apart.
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
from cad.check_tpu_bands import H, Rx, bend, overlap, parts_in_joint_frame  # noqa: E402
from cad.tpu_liners import OUT, RING_T  # noqa: E402


def ring_in_joint_frame(c, i):
    m = trimesh.load(OUT / "mouth_rings" / f"mouth_ring_J{i}.stl")
    M = H(np.array([[0, 0, -1], [-1, 0, 0], [0, 1, 0]]), (-g.cap_h(c, i), 0, 0))   # print z -> -x, notch -> dorsal
    return m.apply_transform(M)


def flange_heads(c, i):
    d = g.droop(c, i)
    heads = []
    for a in (45, 135, 225, 315):
        h = trimesh.creation.cylinder(radius=3.5, height=4.0, sections=16)
        T = H(Rx(a)) @ H(t=(0, 0, g.flange_bolt_r(c, i)))
        T = T @ H(np.array([[0, 0, 1], [0, 1, 0], [-1, 0, 0]]), (0, 0, 0))   # cylinder axis along x
        h.apply_transform(T)
        h.apply_transform(H(t=(-g.DF(c, i) + 2.0, 0, 0)))
        h.apply_transform(H(np.array([[math.cos(math.radians(d)), 0, -math.sin(math.radians(d))], [0, 1, 0],
                                      [math.sin(math.radians(d)), 0, math.cos(math.radians(d))]])))
        heads.append(h)
    return heads


def main():
    from cad.tpu_liners import _rdir
    c = g.CadParams(**json.loads((ROOT / "cad" / "variants" / "barney.json").read_text()))
    rows = {r["joint"]: r for r in json.loads((OUT / "liners.json").read_text())["rows"]}
    bad, nostop = [], []
    for i in range(1, c.joint_count + 1):
        parent, child = parts_in_joint_frame(c, i)
        balls, caps = parent[1:], child[:2]
        ring = ring_in_joint_frame(c, i)
        heads = flange_heads(c, i)
        if overlap([ring], balls + caps) > 0.05:
            bad.append(f"J{i} rest: ring overlaps parts")
        for j, phi in enumerate(range(0, 360, 45)):
            st = rows[i]["stops8"][j]
            res = {}
            for tag, ang in (("inside", st - 0.3), ("past", st + 1.0)):
                R = H(_rdir(ang, phi))
                r = ring.copy().apply_transform(R)
                cp = [m.copy().apply_transform(R) for m in caps]
                res[tag] = (overlap([r], balls), overlap(cp, balls), overlap([r], heads))
            reaches = res["past"][0] > 0.05
            ok = res["inside"][0] < 0.05 and res["inside"][2] < 0.05 and res["past"][1] < 0.05
            note = "" if reaches else "  (neck leans away: no ring or PETG stop in this direction)"
            print(f"J{i} dir {phi:3d}: stop {st:4.1f} | inside: ring/ball {res['inside'][0]:.2f}, ring/heads "
                  f"{res['inside'][2]:.2f} | +1 deg: ring/neck {res['past'][0]:.1f}, PETG cap/neck {res['past'][1]:.2f}"
                  f" mm^3 {'ok' if ok else 'FAIL'}{note}", flush=True)
            if not ok:
                bad.append(f"J{i} dir {phi}")
            if not reaches:
                nostop.append(f"J{i} dir {phi}")
    print("all rings ok" if not bad else "FAILED: " + ", ".join(bad))
    if nostop:
        print("directions where nothing on the cap stops the neck: " + ", ".join(nostop))


if __name__ == "__main__":
    main()
