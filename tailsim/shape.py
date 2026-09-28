"""Target rest shapes: the "x^2 + 1" Gojira profile.

The tail leaves the hip pointing down, bottoms out a small clearance above the
floor and curls back up toward the tip:  z(s) = c + a (s - s_v)^2  (s = horizontal
distance behind joint 1). Given joint-1 height, clearance, tip rise and total
length, solve a and s_v, then place joint centres at equal arc spacing and
return the root pitch and per-joint rest droop (negative = bends upward).
"""
from __future__ import annotations

import math

import numpy as np


def _curve(a, sv, c, h, x_end, n=4000):
    x = np.linspace(0, x_end, n)
    z = c + a * (x - sv) ** 2
    ds = np.sqrt(np.diff(x) ** 2 + np.diff(z) ** 2)
    return x, z, np.r_[0, np.cumsum(ds)]


def parabola(h, clearance, rise, length):
    """Solve z = c + a (x - sv)^2 through (0, h) with arc length `length`
    ending at height c + rise. Returns (a, sv, x_tip)."""
    c = clearance

    def arc_for(a):
        sv = math.sqrt((h - c) / a)
        x_tip = sv + math.sqrt(rise / a)
        return _curve(a, sv, c, h, x_tip)[2][-1], sv, x_tip

    lo, hi = 0.05, 200.0
    for _ in range(200):
        mid = math.sqrt(lo * hi)
        L, _, _ = arc_for(mid)
        if L > length:
            lo = mid           # too long -> sharper curve
        else:
            hi = mid
    L, sv, x_tip = arc_for(mid)
    return mid, sv, x_tip


def gojira_joints(h, clearance, rise, mech_length, n, tip_length):
    """Root pitch (deg, down positive) and per-joint droop list for the chord
    polygon through joint centres (and the tip) spaced along the parabola."""
    total = mech_length + tip_length
    a, sv, x_tip = parabola(h, clearance, rise, total)
    x, z, s = _curve(a, sv, clearance, h, x_tip)
    stations = [k * mech_length / n for k in range(n + 1)] + [total]
    px = np.interp(stations, s, x)
    pz = np.interp(stations, s, z)
    ang = np.degrees(np.arctan2(-(np.diff(pz)), np.diff(px)))      # chord pitch, down positive
    root = ang[0]
    droop = np.r_[0.0, np.diff(ang[:n])]                              # joint i>1 bend
    tip_bend = ang[n] - ang[n - 1]
    return dict(a=a, s_vertex=sv, x_tip=x_tip, root_pitch=root, droop=list(droop), tip_bend=tip_bend,
                points=np.c_[px, pz], lowest=float(z.min()))
