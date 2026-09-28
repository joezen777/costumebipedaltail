"""Pelvis (hip block) motion inputs: README sections 13-17.

Each motion returns hip generalized coordinates [x, y, z, yaw, pitch, roll]
(metres, radians) relative to the standing pose, with velocity and
acceleration, as a function of time since the test started.
"""
from __future__ import annotations

import math

import numpy as np


def min_jerk(t, T):
    """Minimum-jerk 0->1 ramp (typical of voluntary human movement)."""
    if t <= 0:
        return 0.0, 0.0, 0.0
    if t >= T:
        return 1.0, 0.0, 0.0
    x = t / T
    s = 10 * x**3 - 15 * x**4 + 6 * x**5
    ds = (30 * x**2 - 60 * x**3 + 30 * x**4) / T
    dds = (60 * x - 180 * x**2 + 120 * x**3) / T**2
    return s, ds, dds


class Motion:
    name = "static"
    duration = 4.0
    stop_time = 0.0    # when the hip stops moving (for settling metrics)

    def __call__(self, t):
        z = np.zeros(6)
        return z, z.copy(), z.copy()


class Ramp(Motion):
    """Move selected hip coordinates from 0 to target over T, then hold."""

    def __init__(self, name, target, T, duration=6.0, start=0.2, back_at=None):
        self.name, self.target, self.T = name, np.asarray(target, float), T
        self.duration, self.start, self.back_at = duration, start, back_at
        self.stop_time = start + T

    def __call__(self, t):
        s, ds, dds = min_jerk(t - self.start, self.T)
        if self.back_at is not None and t > self.back_at:
            s2, ds2, dds2 = min_jerk(t - self.back_at, self.T)
            s, ds, dds = s - s2, ds - ds2, dds - dds2
        return self.target * s, self.target * ds, self.target * dds


class Walk(Motion):
    """Simplified walking pelvis: yaw/roll at stride frequency, bob at step frequency.

    With ``literal=True`` all components oscillate at ``step_hz`` as written in
    the README; physically the pelvis yaws once per stride (half step rate).
    """

    def __init__(self, step_hz=1.8, yaw_deg=5, roll_deg=3, bob=0.02, duration=10.0, ramp=1.5, literal=False):
        self.name = f"walk_{step_hz:.2f}Hz" + ("_literal" if literal else "")
        self.f, self.duration, self.ramp = step_hz, duration, ramp
        self.yaw, self.roll, self.bob = math.radians(yaw_deg), math.radians(roll_deg), bob
        self.literal = literal
        self.stop_time = duration

    def __call__(self, t):
        fs = self.f if self.literal else self.f / 2
        ws, wb = 2 * math.pi * fs, 2 * math.pi * self.f
        env, denv, ddenv = min_jerk(t, self.ramp)
        q = np.zeros(6); v = np.zeros(6); a = np.zeros(6)
        # (amplitude, omega, phase) per coordinate index
        comps = {3: (self.yaw, ws, 0.0), 5: (self.roll, ws, math.pi / 2), 2: (self.bob, wb, 0.0)}
        for k, (A, w, ph) in comps.items():
            x = A * math.sin(w * t + ph); dx = A * w * math.cos(w * t + ph); ddx = -A * w * w * math.sin(w * t + ph)
            q[k] = env * x
            v[k] = denv * x + env * dx
            a[k] = ddenv * x + 2 * denv * dx + env * ddx
        return q, v, a


def hip_snap(angle_deg=30.0, T=0.35):
    return Ramp(f"hip_snap_{angle_deg:g}", [0, 0, 0, math.radians(angle_deg), 0, 0], T, duration=6.0)


def dramatic_turn():
    return Ramp("dramatic_turn_45", [0, 0, 0, math.radians(45), 0, 0], 0.5, duration=6.0)


def side_step():
    return Ramp("side_step_300mm", [0, 0.3, 0, 0, 0, 0], 0.5, duration=5.0)


def crouch():
    # pelvis drops 150 mm and tilts forward (nose-down, +pitch about world y) 10 deg
    return Ramp("crouch", [0, 0, -0.15, 0, math.radians(10), 0], 0.6, duration=6.0, back_at=3.0)


def standard_tests():
    return [hip_snap(), dramatic_turn(), Walk(1.5), Walk(2.0), Walk(1.75, literal=True), side_step(), crouch()]
