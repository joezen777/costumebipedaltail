"""Physics-accurate pose renders of the full tail on a suit performer (MuJoCo, EGL).

Tail shape at each instant comes from the simulation of the recommended design on the
Gojira profile (experiments/gojira_final.py -> scratch/gojira_raw.pkl). The performer is a
posed mannequin (not simulated) placed from the simulated pelvis pose.

    MUJOCO_GL=egl PYTHONPATH=. python experiments/pose_renders.py
"""
from __future__ import annotations

import math
import os
import pickle
from pathlib import Path

os.environ.setdefault("MUJOCO_GL", "egl")
import mujoco
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "pose_renders"
DESIGN = "ball_spring_spine"
H = 1.727
PELVIS_Z = 0.55 * H
SKIN = "0.20 0.24 0.18 1"        # dark green-grey creature skin
SUIT = "0.20 0.24 0.18 1"


def rot(yaw, pitch, roll=0.0):
    cy, sy, cp, sp, cr, sr = math.cos(yaw), math.sin(yaw), math.cos(pitch), math.sin(pitch), math.cos(roll), math.sin(roll)
    Rz = np.array([[cy, -sy, 0], [sy, cy, 0], [0, 0, 1]])
    Ry = np.array([[cp, 0, sp], [0, 1, 0], [-sp, 0, cp]])
    Rx = np.array([[1, 0, 0], [0, cr, -sr], [0, sr, cr]])
    return Rz @ Ry @ Rx


def catmull(points, n_per=12):
    P = np.vstack([2 * points[0] - points[1], points, 2 * points[-1] - points[-2]])
    out, u = [], []
    for i in range(1, len(P) - 2):
        for t in np.linspace(0, 1, n_per, endpoint=False):
            p0, p1, p2, p3 = P[i - 1], P[i], P[i + 1], P[i + 2]
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t
                              + (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3))
            u.append(i - 1 + t)
    out.append(points[-1]); u.append(len(points) - 1)
    return np.array(out), np.array(u)


def tube_mesh(points, radii, sides=28):
    C, u = catmull(points)
    r = np.interp(u, np.arange(len(radii)), radii)
    verts, faces = [], []
    up = np.array([0, 0, 1.0])
    for k, c in enumerate(C):
        t = C[min(k + 1, len(C) - 1)] - C[max(k - 1, 0)]
        t /= np.linalg.norm(t)
        a = np.cross(t, up)
        if np.linalg.norm(a) < 1e-6:
            a = np.array([0, 1.0, 0])
        a /= np.linalg.norm(a)
        b = np.cross(t, a)
        for s in range(sides):
            th = 2 * math.pi * s / sides
            # slightly flattened, deeper-than-wide section with a dorsal ridge
            ridge = 1.0 + 0.18 * max(0.0, math.cos(th - math.pi / 2)) ** 8 * (1 - u[k] / u[-1])
            verts.append(c + r[k] * (0.92 * math.cos(th) * a + 1.05 * ridge * math.sin(th) * b))
    n = len(C)
    for k in range(n - 1):
        for s in range(sides):
            a0, a1 = k * sides + s, k * sides + (s + 1) % sides
            b0, b1 = a0 + sides, a1 + sides
            faces += [[a0, b0, a1], [a1, b0, b1]]
    verts.append(C[-1] + 0.01 * (C[-1] - C[-2]) / np.linalg.norm(C[-1] - C[-2]))
    tip = len(verts) - 1
    last = (n - 1) * sides
    faces += [[last + s, tip, last + (s + 1) % sides] for s in range(sides)]
    return np.array(verts), np.array(faces)


def _fmt(v):
    return " ".join(f"{x:.5f}" for x in np.ravel(v))


def capsule(a, b, r, rgba=SUIT):
    return f'<geom type="capsule" fromto="{_fmt(a)} {_fmt(b)}" size="{r:.4f}" rgba="{rgba}"/>'


def performer(pelvis, ypr_deg, pose):
    """Mannequin in a bulky creature suit, from the simulated pelvis pose."""
    yaw, pitch, roll = [math.radians(x) for x in ypr_deg]
    R = rot(yaw, pitch, roll)
    Ryaw = rot(yaw, 0)
    P = np.asarray(pelvis)
    L = lambda v: P + R @ np.asarray(v)                  # pelvis-fixed point
    g = []
    g.append(f'<geom type="ellipsoid" pos="{_fmt(L([0, 0, 0.02]))}" size="0.17 0.21 0.16" '
             f'quat="{_fmt(quat(R))}" rgba="{SUIT}"/>')
    chest = L([0.02, 0, 0.42])
    g.append(f'<geom type="ellipsoid" pos="{_fmt(L([0.0, 0, 0.26]))}" size="0.18 0.23 0.30" quat="{_fmt(quat(R))}" rgba="{SUIT}"/>')
    neck = L([0.06, 0, 0.60])
    head = L([0.14, 0, 0.72])
    g.append(capsule(chest, neck, 0.10))
    g.append(f'<geom type="ellipsoid" pos="{_fmt(head)}" size="0.16 0.10 0.10" quat="{_fmt(quat(R))}" rgba="{SUIT}"/>')
    for side in (1, -1):
        hip = L([0.0, 0.10 * side, -0.05])
        if pose == "jump":
            knee = hip + Ryaw @ np.array([0.10, 0.02 * side, -0.40])
            foot = knee + Ryaw @ np.array([-0.08, 0.0, -0.40])
        else:
            foot = np.array([hip[0] + (0.05 if pose != "bend" else 0.12) * math.cos(yaw), hip[1] + 0.03 * side, 0.06])
            knee = 0.5 * (hip + foot) + Ryaw @ np.array([0.05 if pose != "bend" else 0.12, 0, 0])
        g.append(capsule(hip, knee, 0.105))
        g.append(capsule(knee, foot, 0.085))
        toe = foot + Ryaw @ np.array([0.20, 0.0, -0.02])
        g.append(capsule(foot, toe, 0.07))
        sh = L([0.02, 0.22 * side, 0.46])
        if pose == "jump":
            el = sh + R @ np.array([0.15, 0.08 * side, 0.12])
            hand = el + R @ np.array([0.22, 0.02 * side, 0.05])
        else:
            el = sh + R @ np.array([0.10, 0.06 * side, -0.24])
            hand = el + R @ np.array([0.20, 0.0, -0.05])
        g.append(capsule(sh, el, 0.07))
        g.append(capsule(el, hand, 0.06))
        for c in (-1, 0, 1):
            claw = hand + R @ np.array([0.06, 0.025 * c, -0.02])
            g.append(capsule(hand, claw, 0.018, "0.85 0.82 0.70 1"))
    # dorsal plates down the back (Gojira silhouette)
    for k, (z, s) in enumerate([(0.62, 0.07), (0.50, 0.09), (0.36, 0.10), (0.22, 0.09), (0.08, 0.07)]):
        c = L([-0.19 - s / 2, 0, z + 0.01])
        g.append(f'<geom type="ellipsoid" pos="{_fmt(c)}" size="{s/1.6:.3f} 0.012 {s*0.75:.3f}" quat="{_fmt(quat(R @ rot(0, -0.5)))}" '
                 f'rgba="0.78 0.76 0.70 1"/>')
    return g


def quat(R):
    q = np.zeros(4)
    mujoco.mju_mat2Quat(q, R.reshape(9))
    return q


def scene_xml(frame, D, tip_d, pose, cam):
    pelvis = frame["pelvis_pos"]
    ypr = frame["pelvis_ypr"]
    pts = frame["bodies"]
    R = rot(*[math.radians(x) for x in ypr])
    root_blend = pelvis + R @ np.array([-0.13, 0, -0.02])
    points = np.vstack([root_blend, pts])
    radii = np.r_[0.11, D / 2, tip_d / 2]
    V, F = tube_mesh(points, radii)
    verts = " ".join(_fmt(v) for v in V)
    faces = " ".join(" ".join(str(i) for i in f) for f in F)
    # dorsal plates along the first half of the tail
    plates = []
    for k in range(0, 6):
        a, b = pts[k], pts[k + 1]
        mid = 0.5 * (a + b)
        d = (b - a) / np.linalg.norm(b - a)
        side = np.cross(d, [0, 0, 1.0]); side /= np.linalg.norm(side)
        upv = np.cross(side, d)
        top = mid + upv * (D[k] / 2 * 0.9 + (0.03 - 0.004 * k))
        Rp = np.column_stack([d, side, upv])
        plates.append(f'<geom type="ellipsoid" pos="{_fmt(top)}" size="{0.05 - 0.006 * k:.3f} 0.010 {0.04 - 0.005 * k:.3f}" '
                      f'quat="{_fmt(quat(Rp))}" rgba="0.78 0.76 0.70 1"/>')
    body = performer(pelvis, ypr, pose)
    cx, cy, cz, tx, ty, tz = cam
    return f"""
<mujoco>
  <visual><headlight ambient="0.35 0.35 0.35" diffuse="0.5 0.5 0.5"/><quality shadowsize="4096" offsamples="8"/>
          <global offwidth="1344" offheight="768"/></visual>
  <asset>
    <texture name="grid" type="2d" builtin="checker" rgb1="0.55 0.53 0.50" rgb2="0.50 0.48 0.46" width="512" height="512"/>
    <texture name="sky" type="skybox" builtin="gradient" rgb1="0.78 0.82 0.88" rgb2="0.45 0.50 0.58" width="512" height="512"/>
    <material name="floor" texture="grid" texrepeat="10 10" reflectance="0"/>
    <mesh name="tail" vertex="{verts}" face="{faces}"/>
  </asset>
  <worldbody>
    <light pos="1.5 2.5 4" dir="-0.3 -0.5 -1" diffuse="0.8 0.8 0.78" castshadow="true"/>
    <light pos="-3 -1 3" dir="0.6 0.2 -0.6" diffuse="0.35 0.35 0.4" castshadow="false"/>
    <geom type="plane" size="6 6 0.1" material="floor"/>
    <geom type="mesh" mesh="tail" rgba="{SKIN}"/>
    {''.join(plates)}
    {''.join(body)}
    <camera name="cam" pos="{cx} {cy} {cz}" xyaxes="{_fmt(xyaxes((cx, cy, cz), (tx, ty, tz)))}"/>
  </worldbody>
</mujoco>"""


def xyaxes(eye, target):
    f = np.asarray(target) - np.asarray(eye)
    f /= np.linalg.norm(f)
    x = np.cross(f, [0, 0, 1.0]); x /= np.linalg.norm(x)
    y = np.cross(x, f)
    return np.r_[x, y]


def frame_at(r, t):
    k = int(round(t / (r["time"][1] - r["time"][0])))
    k = min(k, len(r["time"]) - 1)
    return {key: r[key][k] for key in ("pelvis_pos", "pelvis_ypr", "bodies", "tip_heading", "hip_yaw", "clearance")} | {"t": r["time"][k]}


def pick(raw):
    """Choose the instant for each requested pose."""
    from tailsim.motions import jump
    snap = raw["hip_snap_left"]
    lat = np.abs(snap["tip_disp_lat"])
    turn = raw["dramatic_turn_45"]
    tl = jump().t_land
    return {
        "1_standing": (raw["walk_1.50Hz"], 0.0, "stand"),
        "2_bending_over": (raw["bend_over"], 3.0, "bend"),
        "3_turning": (turn, float(turn["time"][np.argmax(np.abs(turn["tip_disp_lat"]))]), "stand"),
        "4_jerk_left": (snap, float(snap["time"][np.argmax(lat)]), "stand"),
        "5_jump_before_landing": (raw["jump"], tl - 0.05, "jump"),
    }


CAMS = {  # eye (x,y,z) and target, world metres; performer faces +x, tail toward -x
    "1_standing": (0.9, 3.0, 1.25, -0.55, 0.0, 0.55),
    "2_bending_over": (0.9, 3.0, 1.25, -0.55, 0.0, 0.55),
    "3_turning": (-2.9, 2.0, 2.3, -0.5, -0.1, 0.35),
    "4_jerk_left": (-2.9, 2.0, 2.3, -0.5, -0.1, 0.35),
    "5_jump_before_landing": (0.9, 3.0, 1.35, -0.55, 0.0, 0.7),
}


def main():
    from experiments.gojira_final import FINALISTS
    raw = pickle.load(open(ROOT / "scratch" / "gojira_raw.pkl", "rb"))[DESIGN]
    p = FINALISTS[DESIGN]
    D = p.diameters()
    OUT.mkdir(parents=True, exist_ok=True)
    info = {}
    for name, (r, t, pose) in pick(raw).items():
        fr = frame_at(r, t)
        xml = scene_xml(fr, D, p.tip_diameter, pose, CAMS[name])
        m = mujoco.MjModel.from_xml_string(xml)
        d = mujoco.MjData(m)
        mujoco.mj_forward(m, d)
        with mujoco.Renderer(m, 768, 1344) as ren:
            ren.update_scene(d, camera="cam")
            img = ren.render()
        Image.fromarray(img).save(OUT / f"{name}.png")
        info[name] = dict(t=float(fr["t"]), hip_yaw=float(fr["hip_yaw"]), tip_heading=float(fr["tip_heading"]),
                          clearance_m=float(fr["clearance"]), pelvis_z=float(fr["pelvis_pos"][2]))
        print(name, {k: round(v, 3) for k, v in info[name].items()})
    import json
    (OUT / "poses.json").write_text(json.dumps(info, indent=1))


if __name__ == "__main__":
    main()
