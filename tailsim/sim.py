"""Time-domain simulation of the passive tail.

Force model per step (all passive; the performer's hip is the only input):

* Hip block: kinematically prescribed through a stiff PD servo with
  feed-forward so the tail's reaction barely perturbs the pelvis path
  (tracking error is recorded).
* Central cord: tension-only spring/damper through every ball centre,
  T = max(0, preload + k (L - L0) + c dL/dt).
* Spring spine: per joint, one dorsal and two lateral extension springs
  spanning the joint outside the socket; tension-only,
  T = max(0, T0 + k (L - Lrest) + c dL/dt). They supply yaw centring and
  hold the tail up against gravity (see docs/physics.md).
* Ball/socket Coulomb friction: the frictionloss of each joint's three
  hinges is mu * r_f * |F_joint|, where F_joint is the force the ball
  actually transmits (inertial + gravity load of the distal subtree plus the
  cord and spring compression across that joint), refreshed every few steps.
* Angular stops: soft joint limits (TPU bumpers).
"""
from __future__ import annotations

import math

import mujoco
import numpy as np

from .model import build
from .params import TailParams

G = 9.81


def tendon_moments(m, d):
    """Dense tendon moment arms dL/dq, shape (ntendon, nv)."""
    J = np.asarray(d.ten_J)
    if J.size == m.ntendon * m.nv:
        return J.reshape(m.ntendon, m.nv).copy()
    out = np.zeros((m.ntendon, m.nv))
    for t in range(m.ntendon):
        a, n = m.ten_J_rowadr[t], m.ten_J_rownnz[t]
        out[t, m.ten_J_colind[a:a+n]] = J[a:a+n]
    return out


def _wrap(a):
    return (a + math.pi) % (2 * math.pi) - math.pi


class TailSim:
    load_every = 4          # joint-load / friction refresh interval (steps)

    def __init__(self, p: TailParams, settle: bool = True):
        self.p = p
        self.model, self.info = build(p)
        self.data = mujoco.MjData(self.model)
        m, d, info = self.model, self.data, self.info
        self.mu, visc = p.friction_values()
        self.r_fric = p.friction_radius_factor * p.ball_radii()
        mujoco.mj_forward(m, d)
        M = np.zeros((m.nv, m.nv))
        mujoco.mj_fullM(m, d, M)
        self.M_rest = M
        self.I_yaw = np.array([M[k, k] for k in info.yaw_dofs])
        self.I_pitch = np.array([M[k, k] for k in info.pitch_dofs])
        for i in range(p.n):
            s = self.I_yaw[i] / self.I_yaw[0]
            for dofs in (info.yaw_dofs, info.pitch_dofs, info.roll_dofs):
                if dofs:
                    m.dof_damping[dofs[i]] += visc * s
        if p.joint_type == "hinge":
            # a pinned hinge: friction radius is the pin, plus preloaded washers (scaled by distal mass)
            self.r_fric = np.full(p.n, p.hinge_pin_radius)
        self.hip_inertia = np.array([M[k, k] for k in info.hip_dofs])
        self.hip_ref0 = d.qpos[info.hip_qpos].copy()
        self.m_distal = np.array([m.body_subtreemass[b] for b in info.body_ids])
        if info.cord_tendon is not None:
            self.cord_L0 = float(d.ten_length[info.cord_tendon])
        self.cord_T = p.cord_preload if info.cord_tendon is not None else 0.0
        self._index_arrays()
        self._design_springs()
        self._T0 = np.array([s["T0"] for s in self.spring])
        self._k = np.array([s["k"] for s in self.spring])
        self._L0 = np.array([s["L0"] for s in self.spring])
        self.spring_T = self._T0.copy()
        self.last_N = self._static_N()
        self.last_comp = self.last_N.copy()
        self.last_M = np.zeros(p.n)
        self.last_stop = np.zeros(p.n)
        self._radii = p.diameters() / 2 * 0.9
        if settle:
            self._settle()

    # ------------------------------------------------------------------ setup
    def _index_arrays(self):
        m, info = self.model, self.info
        self.sp_joint = np.array([j for j, _, _ in info.spring_tendons], int)
        self.sp_tid = np.array([t for _, _, t in info.spring_tendons], int)
        self.sp_aid = np.array(info.spring_act, int)
        self.sp_site_p = np.array([m.wrap_objid[m.tendon_adr[t]] for t in self.sp_tid], int)
        self.sp_site_c = np.array([m.wrap_objid[m.tendon_adr[t] + 1] for t in self.sp_tid], int)
        if info.cord_tendon is not None:
            adr = m.tendon_adr[info.cord_tendon]
            self.cord_prev = np.array([m.wrap_objid[adr + i] for i in range(self.p.n)], int)
        self.body_ids = np.array(info.body_ids, int)
        self.jnt_to_joint = -np.ones(m.njnt, int)
        for i in range(self.p.n):
            for dofs in (info.yaw_dofs, info.pitch_dofs, info.roll_dofs):
                if dofs:
                    self.jnt_to_joint[m.dof_jntid[dofs[i]]] = i
        self.fric_dofs = np.array([d for d in (info.yaw_dofs, info.pitch_dofs, info.roll_dofs) if d], int)

    def _static_N(self):
        """Quasi-static ball load: distal weight plus every tension crossing."""
        N = self.m_distal * G + self.cord_T
        if len(self.spring):
            N = N + np.bincount(self.sp_joint, weights=np.array([s["T0"] for s in self.spring]), minlength=self.p.n)
        return N

    def _spring_qfrc(self, qpos):
        """Generalized force of the static spring system at a pose."""
        m, d2 = self.model, self._d2
        d2.qpos[:] = qpos
        mujoco.mj_fwdPosition(m, d2)
        mom = tendon_moments(m, d2)
        T = np.array([max(0.0, s["T0"] + s["k"] * (d2.ten_length[s["tid"]] - s["L0"])) for s in self.spring])
        return -(T[:, None] * mom[self.sp_tid]).sum(0)

    def stiffness_at_rest(self, qpos=None, dq=1e-4):
        """Effective yaw and pitch spring stiffness of each joint (N*m/rad),
        including the geometric softening caused by spring preload."""
        qpos = self.data.qpos.copy() if qpos is None else qpos
        info = self.info
        Ky, Kp = np.zeros(self.p.n), np.zeros(self.p.n)
        for i in range(self.p.n):
            for arr, dofs, qa in ((Ky, info.yaw_dofs, info.yaw_qpos), (Kp, info.pitch_dofs, info.pitch_qpos)):
                qa_, qb_ = qpos.copy(), qpos.copy()
                qa_[qa[i]] += dq; qb_[qa[i]] -= dq
                arr[i] = -(self._spring_qfrc(qa_)[dofs[i]] - self._spring_qfrc(qb_)[dofs[i]]) / (2 * dq)
        return Ky, Kp

    def _design_springs(self):
        """Size the spring spine at the rest pose (docs/physics.md).

        Target stiffness per joint is the larger of an inertia rule
        K = (2 pi f)^2 I_distal and a friction rule K = tau_friction / deadband,
        so the springs can always pull a joint out of its Coulomb dead band.
        The iteration corrects for geometric softening by spring preload.
        """
        p, m, d, info = self.p, self.model, self.data, self.info
        self.spring = []
        self._d2 = mujoco.MjData(m)
        self.K_target = (np.zeros(p.n), np.zeros(p.n))
        self.K_eff = (np.zeros(p.n), np.zeros(p.n))
        if not p.springs_enabled:
            return
        grav = d.qfrc_bias.copy()
        mom = tendon_moments(m, d)
        yl = np.radians(p.yaw_limit_list())
        for (i, side, tid), aid in zip(info.spring_tendons, info.spring_act):
            L = float(d.ten_length[tid])
            if side in "LR":
                r = abs(mom[tid, info.yaw_dofs[i]])
                k = (2 * math.pi * p.yaw_local_hz) ** 2 * self.I_yaw[i] / (2 * r * r)
                T0 = p.lateral_preload_margin * k * r * yl[i]
            else:
                r = mom[tid, info.pitch_dofs[i]]
                k = (2 * math.pi * p.pitch_local_hz) ** 2 * self.I_pitch[i] / (r * r)
                T0 = -grav[info.pitch_dofs[i]] / r      # balances gravity at rest
                if T0 < 0:
                    raise RuntimeError(f"dorsal spring {i+1} would need compression")
            self.spring.append(dict(joint=i, side=side, tid=tid, aid=aid, k=k, T0=T0, L0=L, arm=abs(r)))
        rest = d.qpos.copy()
        if p.spring_override is not None:
            # same physical springs as a previously designed tail (hardware study)
            for s, o in zip(self.spring, p.spring_override):
                s["k"], s["T0"] = float(o["k"]), float(o["T0"])
            from .linear import linear_modes
            self.K_target = (np.zeros(p.n), np.zeros(p.n))
            self.K_eff = self.stiffness_at_rest(rest)
            self.stiffen_steps = 0
            self.lowest_mode_hz = float(linear_modes(self, rest)[0][0])
            return
        db = math.radians(p.deadband_deg)
        for _ in range(8):
            tau_f = self.mu * self.r_fric * self._static_N()
            Kyt = np.maximum((2 * math.pi * p.yaw_local_hz) ** 2 * self.I_yaw, tau_f / db)
            Kpt = np.maximum((2 * math.pi * p.pitch_local_hz) ** 2 * self.I_pitch, tau_f / db)
            Ky, Kp = self.stiffness_at_rest(rest)
            for s in self.spring:
                i = s["joint"]
                if s["side"] in "LR":
                    s["k"] *= float(np.clip(Kyt[i] / max(Ky[i], 1e-6), 0.3, 3.0))
                    s["T0"] = p.lateral_preload_margin * s["k"] * s["arm"] * yl[i]
                else:
                    s["k"] *= float(np.clip(Kpt[i] / max(Kp[i], 1e-6), 0.3, 3.0))
        self.K_target = (Kyt, Kpt)
        self.K_eff = self.stiffness_at_rest(rest)
        # guard: the coupled yaw/pitch/roll system must be statically stable
        from .linear import linear_modes
        self.stiffen_steps = 0
        self.lowest_mode_hz = float("nan")
        if "D" not in p.spring_sides:
            return      # tail rests on stops/floor: no free equilibrium to linearise about
        while self.stiffen_steps < 12:
            f = linear_modes(self, rest)[0]
            if f[0] > p.min_mode_hz:
                break
            for s in self.spring:
                if s["side"] in "LR":
                    s["k"] *= 1.25
                    s["T0"] = p.lateral_preload_margin * s["k"] * s["arm"] * yl[s["joint"]]
            self.stiffen_steps += 1
        self.lowest_mode_hz = float(linear_modes(self, rest)[0][0])

    def spring_table(self):
        return [{kk: (float(v) if not isinstance(v, str) else v) for kk, v in s.items() if kk not in ("tid", "aid")}
                for s in self.spring]

    def _settle(self):
        """Let the tail find static equilibrium with the hip held still."""
        steps = int(self.p.settle_time / self.p.dt)
        z = np.zeros(6)
        for s in range(steps):
            self._step(z, z, z, s)
        self.data.qvel[:] = 0
        mujoco.mj_forward(self.model, self.data)
        self.rest_qpos = self.data.qpos.copy()
        self.tip_rest_hip = self._to_hip(self.data.site_xpos[self.info.tip_site])
        self.heading0 = self._tip_heading()

    # ------------------------------------------------------------------ forces
    def _apply_forces(self, q_ref, v_ref, a_ref):
        d, info, p = self.data, self.info, self.p
        qh, vh = d.qpos[info.hip_qpos], d.qvel[info.hip_dofs]
        w = 60.0
        kp = self.hip_inertia * w * w
        kv = self.hip_inertia * 2 * 0.9 * w
        d.ctrl[info.hip_act] = (d.qfrc_bias[info.hip_dofs] + self.hip_inertia * a_ref
                                + kp * (self.hip_ref0 + q_ref - qh) + kv * (v_ref - vh))
        if len(self.spring):
            L = d.ten_length[self.sp_tid]; Ld = d.ten_velocity[self.sp_tid]
            T = np.maximum(0.0, self._T0 + self._k * (L - self._L0) + p.spring_damping * Ld)
            self.spring_T = T
            d.ctrl[self.sp_aid] = -T
        if info.cord_tendon is not None:
            L = d.ten_length[info.cord_tendon]; Ld = d.ten_velocity[info.cord_tendon]
            self.cord_T = max(0.0, p.cord_preload + p.cord_stiffness * (L - self.cord_L0) + p.cord_damping * Ld)
            d.ctrl[info.cord_act] = -self.cord_T

    def joint_loads(self):
        """Ball force, seat compression and neck bending moment for each joint."""
        m, d, info, p = self.model, self.data, self.info, self.p
        mujoco.mj_rnePostConstraint(m, d)
        b = self.body_ids
        root_com = d.subtree_com[m.body_rootid[b[0]]]
        f_need = d.cfrc_int[b, 3:6]
        piv = d.xpos[b]
        t_need = d.cfrc_int[b, 0:3] + np.cross(root_com[None, :] - piv, f_need)
        f_t = np.zeros((p.n, 3)); t_t = np.zeros((p.n, 3))
        if len(self.spring):
            xs_p, xs_c = d.site_xpos[self.sp_site_p], d.site_xpos[self.sp_site_c]
            u = xs_p - xs_c
            u /= np.linalg.norm(u, axis=1)[:, None]
            F = self.spring_T[:, None] * u
            tq = np.cross(xs_c - piv[self.sp_joint], F)
            for c in range(3):
                f_t[:, c] = np.bincount(self.sp_joint, weights=F[:, c], minlength=p.n)
                t_t[:, c] = np.bincount(self.sp_joint, weights=tq[:, c], minlength=p.n)
        if info.cord_tendon is not None:
            u = d.site_xpos[self.cord_prev] - piv
            nu = np.linalg.norm(u, axis=1)
            ok = nu > 1e-9
            f_t[ok] += self.cord_T * u[ok] / nu[ok, None]
        fj = f_need - f_t
        e = d.xmat[b].reshape(-1, 3, 3)[:, :, 0]
        self.last_root_moment = float(np.linalg.norm(t_need[0]))
        N = np.linalg.norm(fj, axis=1)
        comp = (fj * e).sum(1)
        Mneck = np.linalg.norm(t_need - t_t, axis=1)
        return N, comp, Mneck

    def _update_friction(self):
        fl = self.mu * self.r_fric * self.last_N
        if self.p.joint_type == "hinge" and self.p.hinge_washer_torque:
            fl = fl + self.p.hinge_washer_torque * self.m_distal / self.m_distal[0]
        if self.p.stop_friction:
            # a joint held against its stop also slides on the stop face (normal ~ stop torque / R)
            fl = fl + self.mu * self.last_stop
        self.model.dof_frictionloss[self.fric_dofs] = fl[None, :]

    def _step(self, q_ref, v_ref, a_ref, s):
        m, d = self.model, self.data
        if s % self.load_every == 0:
            self.last_N, self.last_comp, self.last_M = self.joint_loads()
            self.last_stop = self.stop_torques()
            self._update_friction()
        mujoco.mj_step1(m, d)
        self._apply_forces(q_ref, v_ref, a_ref)
        mujoco.mj_step2(m, d)

    # ------------------------------------------------------------------ helpers
    def _hip_pose(self):
        d = self.data
        return d.xpos[1].copy(), d.xmat[1].reshape(3, 3).copy()

    def _to_hip(self, x):
        pos, R = self._hip_pose()
        return R.T @ (x - pos)

    def _tip_heading(self):
        d, info = self.data, self.info
        piv = d.site_xpos[info.pivot_sites[0]]
        tip = d.site_xpos[info.tip_site]
        return _wrap(math.atan2(tip[1] - piv[1], tip[0] - piv[0]) - math.pi)

    def stop_torques(self):
        """Angular-stop (joint limit) torque magnitude per tail joint."""
        d = self.data
        out = np.zeros(self.p.n)
        if d.nefc:
            mask = d.efc_type[:d.nefc] == mujoco.mjtConstraint.mjCNSTR_LIMIT_JOINT
            if mask.any():
                j = self.jnt_to_joint[d.efc_id[:d.nefc][mask]]
                f = np.abs(d.efc_force[:d.nefc][mask])
                ok = j >= 0
                np.maximum.at(out, j[ok], f[ok])
        return out

    def floor_force(self):
        m, d = self.model, self.data
        ff = 0.0
        f6 = np.zeros(6)
        for c in range(d.ncon):
            mujoco.mj_contactForce(m, d, c, f6)
            ff += abs(f6[0])
        return ff

    # ------------------------------------------------------------------ run
    def run(self, motion):
        m, d, info, p = self.model, self.data, self.info, self.p
        steps = int(round(motion.duration / p.dt))
        keys = ("time", "pelvis_pos", "pelvis_ypr", "yaw", "pitch", "roll", "tip_pos", "tip_vel", "tip_acc",
                "cord_tension", "tip_heading", "hip_yaw", "tip_disp", "tip_disp_lat", "joint_force", "seat_comp",
                "neck_moment", "stop_torque", "floor_force", "hip_err", "spring_T", "tip_height", "bodies",
                "clearance", "root_moment")
        rec = {k: [] for k in keys}
        vel6 = np.zeros(6); acc6 = np.zeros(6)
        peak_stop = np.zeros(p.n)
        peak_neck = np.zeros(p.n)
        min_comp = np.full(p.n, np.inf)
        for s in range(steps + 1):
            t = s * p.dt
            q_ref, v_ref, a_ref = motion(t)
            if s % self.load_every == 0 and s:
                peak_stop = np.maximum(peak_stop, self.stop_torques())
                peak_neck = np.maximum(peak_neck, self.last_M)
                min_comp = np.minimum(min_comp, self.last_comp)
            if s % p.record_every == 0:
                mujoco.mj_objectVelocity(m, d, mujoco.mjtObj.mjOBJ_SITE, info.tip_site, vel6, 0)
                mujoco.mj_objectAcceleration(m, d, mujoco.mjtObj.mjOBJ_SITE, info.tip_site, acc6, 0)
                tip = d.site_xpos[info.tip_site].copy()
                pos, R = self._hip_pose()
                disp = tip - (pos + R @ self.tip_rest_hip)
                rec["time"].append(t)
                rec["pelvis_pos"].append(pos)
                rec["pelvis_ypr"].append(np.degrees(d.qpos[info.hip_qpos[3:6]] - self.hip_ref0[3:6]))
                rec["yaw"].append(np.degrees(d.qpos[info.yaw_qpos]))
                rec["pitch"].append(np.degrees(d.qpos[info.pitch_qpos]) if info.pitch_qpos else np.zeros(p.n))
                rec["roll"].append(np.degrees(d.qpos[info.roll_qpos]) if info.roll_qpos else np.zeros(p.n))
                rec["tip_pos"].append(tip)
                rec["tip_vel"].append(vel6[3:].copy())
                # MuJoCo's cacc carries the -g offset of the world frame
                rec["tip_acc"].append(acc6[3:] + m.opt.gravity)
                rec["cord_tension"].append(self.cord_T)
                rec["tip_heading"].append(math.degrees(_wrap(self._tip_heading() - self.heading0)))
                rec["hip_yaw"].append(math.degrees(d.qpos[info.hip_qpos[3]] - self.hip_ref0[3]))
                rec["tip_disp"].append(np.linalg.norm(disp))
                rec["tip_disp_lat"].append((R.T @ disp)[1])
                rec["joint_force"].append(self.last_N.copy())
                rec["seat_comp"].append(self.last_comp.copy())
                rec["neck_moment"].append(self.last_M.copy())
                rec["stop_torque"].append(self.stop_torques())
                rec["floor_force"].append(self.floor_force())
                rec["hip_err"].append(math.degrees(abs(d.qpos[info.hip_qpos[3]] - self.hip_ref0[3] - q_ref[3])))
                rec["spring_T"].append(np.asarray(self.spring_T).copy())
                rec["tip_height"].append(tip[2])
                zc = np.r_[d.site_xpos[info.pivot_sites][:, 2] - self._radii, tip[2] - p.tip_diameter / 2]
                rec["clearance"].append(zc.min())
                rec["root_moment"].append(getattr(self, "last_root_moment", 0.0))
                rec["bodies"].append(np.vstack([d.site_xpos[info.pivot_sites], d.site_xpos[info.tip_site][None]]))
            if s < steps:
                self._step(q_ref, v_ref, a_ref, s)
        out = {k: np.asarray(v) for k, v in rec.items()}
        out.update(peak_stop_torque=peak_stop, peak_neck_moment=peak_neck, min_seat_comp=min_comp,
                   motion=motion.name, stop_time=motion.stop_time, label=p.label,
                   hip_pivot=self.data.site_xpos[info.pivot_sites[0]].copy())
        return out


def simulate(p: TailParams, motion):
    return TailSim(p).run(motion)
