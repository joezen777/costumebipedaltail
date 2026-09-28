"""Build the MuJoCo model of hip block + ball-jointed vertebrae + foam tip.

Frames
------
World: +x is the performer's forward direction, +z up, floor at z = 0.
Each vertebra body has its origin at its proximal ball-joint centre and its
local +x pointing distally along the tail, +z dorsal. Joint i connects the
parent (hip block or vertebra i-1) to vertebra i and is modelled as three
serial hinges yaw(z) -> pitch(y) -> roll(x) sharing the ball centre, which is
a ball joint with independently limited yaw/pitch/roll ranges.
Positive local pitch bends the tail downward; positive yaw is counter-clockwise
viewed from above (the same sense as positive pelvis yaw).
"""
from __future__ import annotations

from dataclasses import dataclass
import math

import mujoco
import numpy as np

from .params import TailParams


def _quat_from_matrix(R):
    q = np.zeros(4)
    mujoco.mju_mat2Quat(q, np.asarray(R, float).reshape(9))
    return q


def _rot_y(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])


def root_rotation(p: TailParams):
    """Rotation of vertebra 1 relative to the hip block: backward and down."""
    th = math.radians(p.root_pitch_deg)
    ex = np.array([-math.cos(th), 0, -math.sin(th)])
    ez = np.array([-math.sin(th), 0, math.cos(th)])
    ey = np.cross(ez, ex)
    return np.column_stack([ex, ey, ez])


def _fmt(v):
    return " ".join(f"{float(x):.6g}" for x in np.ravel(v))


def segment_inertia(m, D, L):
    ro = D / 2
    ri = 0.5 * ro
    ixx = m / 2 * (ro**2 + ri**2)
    iyy = m / 12 * (3 * (ro**2 + ri**2) + L**2)
    return np.array([ixx, iyy, iyy])


@dataclass
class ModelInfo:
    n: int
    yaw_dofs: list
    pitch_dofs: list
    roll_dofs: list
    yaw_qpos: list
    pitch_qpos: list
    roll_qpos: list
    hip_dofs: list
    hip_qpos: list
    body_ids: list
    tip_body: int
    tip_site: int
    pivot_sites: list
    cord_tendon: int | None
    spring_tendons: list          # list of (joint index, side, tendon id)
    spring_act: list
    cord_act: int | None
    hip_act: list
    tip_dofs: list


def build_xml(p: TailParams) -> str:
    n, L = p.n, p.spacing
    D = p.diameters()
    m = p.mass_list()
    lat, dor = p.spring_arms()
    yaw_lim = p.yaw_limit_list()
    pitch_lim = p.pitch_limit_list()
    a = p.spring_anchor_span
    R1 = root_rotation(p)
    q1 = _quat_from_matrix(R1)
    pivot1_in_hip = np.array([-p.root_back_offset, 0, 0])
    stop = f'solreflimit="{p.stop_timeconst} {p.stop_dampratio}"'
    roll_attr = 'limited="false"' if p.roll_unrestricted else f'limited="true" range="{-p.max_roll} {p.max_roll}"'

    # cord anchor inside the hip mount, 60 mm upstream of the joint 1 ball centre
    sites_hip = [f'<site name="cord_0" pos="{_fmt(pivot1_in_hip + R1 @ np.array([-0.06, 0, 0]))}" size="0.004"/>']
    # spring anchors of joint 1 on the hip block (expressed via root rotation)
    for side, off in (("L", (0, lat[0], 0)), ("R", (0, -lat[0], 0)), ("D", (0, 0, dor[0]))):
        pos = pivot1_in_hip + R1 @ np.array([-a, off[1], off[2]])
        sites_hip.append(f'<site name="sp_1_{side}_p" pos="{_fmt(pos)}" size="0.003"/>')

    body_xml = []
    for i in range(n):
        Di = D[i]
        inertia = segment_inertia(m[i], Di, L)
        com = np.array([L / 2, 0, -p.com_offset])
        if i == 0:
            pos, quat = pivot1_in_hip, q1
        else:
            pos, quat = np.array([L, 0, 0]), _quat_from_matrix(_rot_y(math.radians(p.rest_droop_deg)))
        yl, pl = yaw_lim[i], pitch_lim[i]
        s = [f'<body name="v{i+1}" pos="{_fmt(pos)}" quat="{_fmt(quat)}">',
             f'<joint name="j{i+1}_yaw" axis="0 0 1" limited="true" range="{-yl} {yl}" {stop}/>',
             f'<joint name="j{i+1}_pitch" axis="0 1 0" limited="true" range="{-pl} {pl}" {stop}/>',
             f'<joint name="j{i+1}_roll" axis="1 0 0" {roll_attr} {stop}/>',
             f'<inertial pos="{_fmt(com)}" mass="{m[i]:.6g}" diaginertia="{_fmt(inertia)}"/>',
             f'<geom name="g{i+1}" type="capsule" fromto="{0.12*L:.5g} 0 0 {0.88*L:.5g} 0 0" size="{Di/2*0.9:.5g}" '
             f'contype="2" conaffinity="0" mass="0" rgba="0.35 0.55 0.3 0.6" solref="0.02 1" condim="3" friction="{p.floor_friction} 0.005 0.0001"/>',
             f'<site name="cord_{i+1}" pos="0 0 0" size="0.004"/>']
        # proximal spring anchors on this vertebra (child side of joint i+1)
        for side, off in (("L", (0, lat[i], 0)), ("R", (0, -lat[i], 0)), ("D", (0, 0, dor[i]))):
            s.append(f'<site name="sp_{i+1}_{side}_c" pos="{_fmt([a, off[1], off[2]])}" size="0.003"/>')
        # distal anchors for the next joint, in this vertebra's frame
        if i + 1 < n:
            Rn = _rot_y(math.radians(p.rest_droop_deg))
            for side, off in (("L", (0, lat[i+1], 0)), ("R", (0, -lat[i+1], 0)), ("D", (0, 0, dor[i+1]))):
                ppos = np.array([L, 0, 0]) + Rn @ np.array([-a, off[1], off[2]])
                s.append(f'<site name="sp_{i+2}_{side}_p" pos="{_fmt(ppos)}" size="0.003"/>')
        body_xml.append(s)

    # foam tip on the last vertebra: compliant yaw/pitch bending, soft contact
    tl = p.foam_tip_length
    tip = [f'<body name="tip" pos="{L} 0 0">',
           f'<joint name="tip_yaw" axis="0 0 1" stiffness="{p.tip_bend_stiffness}" damping="{p.tip_bend_damping}" range="-45 45" limited="true"/>',
           f'<joint name="tip_pitch" axis="0 1 0" stiffness="{p.tip_bend_stiffness}" damping="{p.tip_bend_damping}" range="-45 45" limited="true"/>',
           f'<inertial pos="{0.4*tl} 0 0" mass="{p.foam_tip_mass}" diaginertia="{_fmt(segment_inertia(p.foam_tip_mass, (p.last_mech_diameter+p.tip_diameter)/2, tl))}"/>',
           f'<geom name="gtip" type="capsule" fromto="0.02 0 0 {tl-p.tip_diameter/2:.5g} 0 0" size="{p.tip_diameter/2:.5g}" '
           f'contype="2" conaffinity="0" mass="0" rgba="0.8 0.6 0.3 0.6" solref="0.04 1" condim="3" friction="{p.floor_friction} 0.005 0.0001"/>',
           f'<site name="tip_end" pos="{tl} 0 0" size="0.005"/>',
           f'<site name="cord_{n+1}" pos="0 0 0" size="0.004"/>',
           '</body>']

    # nest bodies
    nested = []
    for s in body_xml:
        nested.extend(s)
    nested.extend(tip)
    nested.extend(["</body>"] * n)

    tendons, acts = [], []
    if p.cord_enabled:
        sites = "".join(f'<site site="cord_{k}"/>' for k in range(n + 2))
        tendons.append(f'<spatial name="cord" width="0.003" rgba="0.9 0.9 0.2 1">{sites}</spatial>')
        acts.append('<general name="a_cord" tendon="cord" gainprm="1" ctrllimited="false"/>')
    if p.springs_enabled:
        for i in range(n):
            for side in "LRD":
                tendons.append(f'<spatial name="sp_{i+1}_{side}" width="0.002" rgba="0.8 0.2 0.2 1">'
                               f'<site site="sp_{i+1}_{side}_p"/><site site="sp_{i+1}_{side}_c"/></spatial>')
                acts.append(f'<general name="a_sp_{i+1}_{side}" tendon="sp_{i+1}_{side}" gainprm="1" ctrllimited="false"/>')
    for dof in ("hx", "hy", "hz", "hyaw", "hpitch", "hroll"):
        acts.append(f'<motor name="a_{dof}" joint="{dof}" ctrllimited="false"/>')

    floor = ('<geom name="floor" type="plane" size="4 4 0.1" contype="0" conaffinity="2" rgba="0.8 0.8 0.8 1"/>'
             if p.floor_enabled else "")
    xml = f"""
<mujoco model="suit_tail">
  <compiler angle="degree" autolimits="true"/>
  <option timestep="{p.dt}" integrator="implicitfast" gravity="0 0 -9.81"/>
  <default><joint armature="0.0005"/></default>
  <worldbody>
    {floor}
    <body name="hip" pos="0 0 {p.pivot_height}">
      <joint name="hx" type="slide" axis="1 0 0"/>
      <joint name="hy" type="slide" axis="0 1 0"/>
      <joint name="hz" type="slide" axis="0 0 1"/>
      <joint name="hyaw" axis="0 0 1"/>
      <joint name="hpitch" axis="0 1 0"/>
      <joint name="hroll" axis="1 0 0"/>
      <inertial pos="0 0 0" mass="80" diaginertia="8 8 8"/>
      <geom type="box" size="0.12 0.18 0.1" contype="0" conaffinity="0" rgba="0.3 0.3 0.6 0.5"/>
      {''.join(sites_hip)}
      {''.join(nested)}
    </body>
  </worldbody>
  <tendon>{''.join(tendons)}</tendon>
  <actuator>{''.join(acts)}</actuator>
</mujoco>"""
    return xml


def build(p: TailParams):
    xml = build_xml(p)
    model = mujoco.MjModel.from_xml_string(xml)
    n = p.n
    jid = lambda nm: mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, nm)
    dof = lambda nm: int(model.jnt_dofadr[jid(nm)])
    qadr = lambda nm: int(model.jnt_qposadr[jid(nm)])
    tid = lambda nm: mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_TENDON, nm)
    aid = lambda nm: mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_ACTUATOR, nm)
    sid = lambda nm: mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_SITE, nm)
    springs, spring_act = [], []
    if p.springs_enabled:
        for i in range(n):
            for side in "LRD":
                springs.append((i, side, tid(f"sp_{i+1}_{side}")))
                spring_act.append(aid(f"a_sp_{i+1}_{side}"))
    hipn = ("hx", "hy", "hz", "hyaw", "hpitch", "hroll")
    info = ModelInfo(
        n=n,
        yaw_dofs=[dof(f"j{i+1}_yaw") for i in range(n)],
        pitch_dofs=[dof(f"j{i+1}_pitch") for i in range(n)],
        roll_dofs=[dof(f"j{i+1}_roll") for i in range(n)],
        yaw_qpos=[qadr(f"j{i+1}_yaw") for i in range(n)],
        pitch_qpos=[qadr(f"j{i+1}_pitch") for i in range(n)],
        roll_qpos=[qadr(f"j{i+1}_roll") for i in range(n)],
        hip_dofs=[dof(h) for h in hipn],
        hip_qpos=[qadr(h) for h in hipn],
        body_ids=[mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, f"v{i+1}") for i in range(n)],
        tip_body=mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, "tip"),
        tip_site=sid("tip_end"),
        pivot_sites=[sid(f"cord_{i+1}") for i in range(n)],
        cord_tendon=tid("cord") if p.cord_enabled else None,
        spring_tendons=springs,
        spring_act=spring_act,
        cord_act=aid("a_cord") if p.cord_enabled else None,
        hip_act=[aid(f"a_{h}") for h in hipn],
        tip_dofs=[dof("tip_yaw"), dof("tip_pitch")],
    )
    return model, info
