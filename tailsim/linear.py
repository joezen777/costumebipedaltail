"""Linearized small-motion modes of the tail about its rest pose (hip fixed)."""
from __future__ import annotations

import math

import mujoco
import numpy as np


def linear_modes(sim, qpos=None, eps=1e-5):
    """Return (freqs_hz, eigvals, modes, dof_names, M, K) for all tail dofs.

    K includes spring geometry, gravity and passive (foam tip) stiffness.
    Negative eigenvalues indicate a statically unstable direction.
    """
    m, info = sim.model, sim.info
    tail = sorted(info.yaw_dofs + info.pitch_dofs + info.roll_dofs + info.tip_dofs)
    qadr = [m.jnt_qposadr[m.dof_jntid[k]] for k in tail]
    q0 = (sim.data.qpos if qpos is None else qpos).copy()
    d2 = mujoco.MjData(m)

    def gen(q):
        f = sim._spring_qfrc(q) if sim.spring else np.zeros(m.nv)
        d2.qpos[:] = q
        d2.qvel[:] = 0
        mujoco.mj_forward(m, d2)
        return f - d2.qfrc_bias + d2.qfrc_passive

    K = np.zeros((len(tail), len(tail)))
    for a, qa in enumerate(qadr):
        qp, qm = q0.copy(), q0.copy()
        qp[qa] += eps
        qm[qa] -= eps
        K[:, a] = -(gen(qp)[tail] - gen(qm)[tail]) / (2 * eps)
    d2.qpos[:] = q0
    mujoco.mj_forward(m, d2)
    Mf = np.zeros((m.nv, m.nv))
    mujoco.mj_fullM(m, d2, Mf)
    M = Mf[np.ix_(tail, tail)]
    K = 0.5 * (K + K.T)
    w2, V = np.linalg.eig(np.linalg.solve(M, K))
    o = np.argsort(w2.real)
    w2, V = w2.real[o], V.real[:, o]
    f = np.sign(w2) * np.sqrt(np.abs(w2)) / (2 * math.pi)
    names = [mujoco.mj_id2name(m, mujoco.mjtObj.mjOBJ_JOINT, m.dof_jntid[k]) for k in tail]
    return f, w2, V, names, M, K
