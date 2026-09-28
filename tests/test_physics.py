"""Validation of the tail physics model against independent calculations.

Run:  PYTHONPATH=. ~/.venvs/costumebipedaltail/bin/python -m unittest -v tests.test_physics
"""
import math
import unittest

import mujoco
import numpy as np

from tailsim import motions
from tailsim.params import TailParams
from tailsim.linear import linear_modes
from tailsim.sim import TailSim, G


def conservative(**kw):
    """No friction, no damping, no floor: an energy-conserving tail."""
    base = dict(mu=0.0, visc=0.0, cord_damping=0.0, spring_damping=0.0, floor_enabled=False,
                tip_bend_damping=0.0, stop_timeconst=0.012, settle_time=0.0)
    base.update(kw)
    return TailParams(**base)


def spring_energy(sim):
    d = sim.data
    E = 0.0
    for s in sim.spring:
        x = d.ten_length[s["tid"]] - s["L0"]
        x_slack = -s["T0"] / s["k"]              # extension at which T reaches 0
        if x > x_slack:
            E += s["T0"] * (x - x_slack) + 0.5 * s["k"] * (x * x - x_slack * x_slack)
    return E


def total_energy(sim):
    m, d = sim.model, sim.data
    mujoco.mj_forward(m, d)
    ke = 0.5 * d.qvel @ (sim.M_full() @ d.qvel)
    pe = -sum(m.body_mass[b] * (m.opt.gravity @ d.xipos[b]) for b in range(1, m.nbody))
    tip = sum(0.5 * m.jnt_stiffness[m.dof_jntid[k]] * d.qpos[m.jnt_qposadr[m.dof_jntid[k]]] ** 2 for k in sim.info.tip_dofs)
    return ke + pe + spring_energy(sim) + tip


def _fullM(self):
    M = np.zeros((self.model.nv, self.model.nv))
    mujoco.mj_fullM(self.model, self.data, M)
    return M


TailSim.M_full = _fullM


class TestStatics(unittest.TestCase):
    def test_rest_pose_holds_against_gravity(self):
        """Dorsal springs sized from the gravity bias keep the rest pose."""
        sim = TailSim(TailParams(settle_time=2.0))
        pitch = np.degrees(sim.rest_qpos[sim.info.pitch_qpos])
        self.assertLess(np.abs(pitch).max(), 0.5, pitch)

    def test_static_joint_force_matches_hand_calculation(self):
        """Ball force at joint 1 = distal weight + all tensions crossing (vector sum)."""
        p = TailParams(settle_time=1.0, mu=0.0)
        sim = TailSim(p)
        N, comp, M = sim.joint_loads()
        d, m = sim.data, sim.model
        b = sim.info.body_ids[0]
        W = np.array([0, 0, sim.m_distal[0] * G])      # support needed from the parent
        F_t = np.zeros(3)
        piv = d.xpos[b]
        for k, s in enumerate(sim.spring):
            if s["joint"] == 0:
                u = d.site_xpos[sim.sp_site_p[k]] - d.site_xpos[sim.sp_site_c[k]]
                F_t += sim.spring_T[k] * u / np.linalg.norm(u)
        u = d.site_xpos[sim.cord_prev[0]] - piv
        F_t += sim.cord_T * u / np.linalg.norm(u)
        expect = np.linalg.norm(W - F_t)
        self.assertAlmostEqual(N[0], expect, delta=0.02 * expect)
        # neck moment at rest is small: the dorsal spring carries the weight moment
        self.assertLess(M[0], 0.05 * sim.m_distal[0] * G * 0.6)


class TestDynamics(unittest.TestCase):
    def test_energy_conserved_without_friction(self):
        p = conservative(yaw_limits=[60] * 8)
        sim = TailSim(p, settle=False)
        d = sim.data
        d.qvel[sim.info.yaw_dofs] = 0.6        # rad/s kick in every joint
        E0 = total_energy(sim)
        z = np.zeros(6)
        Es = []
        for s in range(int(2.0 / p.dt)):
            sim._step(z, z, z, s)
            if s % 200 == 0:
                Es.append(total_energy(sim))
        # compare against the initial kinetic energy of the kick
        sim2 = TailSim(p, settle=False)
        sim2.data.qvel[sim2.info.yaw_dofs] = 0.6
        mujoco.mj_forward(sim2.model, sim2.data)
        ke0 = 0.5 * sim2.data.qvel @ (sim2.M_full() @ sim2.data.qvel)
        self.assertLess(max(abs(e - E0) for e in Es), 0.05 * ke0)

    def test_linear_mode_frequency_matches_time_domain(self):
        """Coupled small-motion modes (springs + gravity) predict the free oscillation."""
        p = conservative(yaw_limits=[60] * 8, com_offset=0.03, max_roll=40, yaw_local_hz=1.3)
        sim = TailSim(p, settle=False)
        f, w2, V, names, M, K = linear_modes(sim)
        self.assertGreater(f[0], 0, "reference test configuration must be statically stable")
        m, info = sim.model, sim.info
        tail = sorted(info.yaw_dofs + info.pitch_dofs + info.roll_dofs + info.tip_dofs)
        qadr = [m.jnt_qposadr[m.dof_jntid[k]] for k in tail]
        q0 = sim.data.qpos.copy()
        stable = [j for j in range(len(f)) if f[j] > 0.1][:2]
        for j in stable:
            sim = TailSim(p, settle=False)
            mode = V[:, j] / np.abs(V[:, j]).max()
            sim.data.qpos[qadr] = q0[qadr] + np.radians(0.3) * mode
            w = M @ mode
            z = np.zeros(6)
            ys = []
            for s in range(int(16.0 / p.dt)):
                sim._step(z, z, z, s)
                if s % 10 == 0:
                    ys.append(w @ (sim.data.qpos[qadr] - q0[qadr]))
            ys = np.array(ys) - np.mean(ys)
            spec = np.abs(np.fft.rfft(ys * np.hanning(len(ys)), 16 * len(ys)))
            freqs = np.fft.rfftfreq(16 * len(ys), 10 * p.dt)
            f_sim = freqs[np.argmax(spec)]
            self.assertAlmostEqual(f_sim, f[j], delta=0.05 * f[j] + 0.01)

    def test_time_step_convergence(self):
        a = TailSim(TailParams(settle_time=1.0)).run(motions.hip_snap())
        b = TailSim(TailParams(settle_time=1.0, dt=0.00025, record_every=20)).run(motions.hip_snap())
        n = min(len(a["time"]), len(b["time"]))
        err = np.abs(a["tip_heading"][:n] - b["tip_heading"][:n]).max()
        self.assertLess(err, 1.5)

    def test_hip_follows_prescribed_motion(self):
        r = TailSim(TailParams(settle_time=0.5)).run(motions.dramatic_turn())
        self.assertLess(r["hip_err"].max(), 0.2)

    def test_cord_is_tension_only(self):
        p = TailParams(settle_time=0.2, cord_preload=0.0)
        sim = TailSim(p)
        r = sim.run(motions.hip_snap())
        self.assertGreaterEqual(r["cord_tension"].min(), 0.0)
        self.assertTrue(all((x >= 0).all() for x in r["spring_T"]))

    def test_gravity_bias_restores_roll(self):
        """COM below the pivot produces tau = m g r sin(theta) about the roll axis."""
        p = conservative(com_offset=0.03, springs_enabled=False, cord_enabled=False, max_roll=40)
        sim = TailSim(p, settle=False)
        d, m, info = sim.data, sim.model, sim.info
        k = info.roll_qpos[-1]
        d.qpos[k] = math.radians(10)
        mujoco.mj_forward(m, d)
        tau = -d.qfrc_bias[info.roll_dofs[-1]]
        mass = m.body_mass[info.body_ids[-1]]
        # the roll axis of the last vertebra is tilted by the root/droop angles
        tilt = math.radians(p.root_pitch_deg + p.rest_droop_deg * (p.n - 1))
        expect = -mass * G * 0.03 * math.sin(math.radians(10)) * math.cos(tilt)
        self.assertAlmostEqual(tau, expect, delta=0.08 * abs(expect))


if __name__ == "__main__":
    unittest.main()
