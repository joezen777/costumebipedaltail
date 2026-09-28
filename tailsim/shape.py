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


def barney_joints(mech_length, n, tip_length, theta_root=5.0, theta_max=60.0, theta_end=5.0, h=0.92):
    """Barney-style S profile: heading (deg below horizontal) eases from theta_root up to
    theta_max mid-tail and back to theta_end, so the tail sticks out back, turns down, and
    points back again. Joint centres at equal arc spacing; returns root pitch and per-joint
    rest bends (+ = down, - = up) plus the centreline points (x back, z height)."""
    total = mech_length + tip_length
    s = np.linspace(0, total, 4001)
    u = s / total
    base = theta_root * (1 - u) + theta_end * u
    th = np.radians(base + (theta_max - base) * np.sin(np.pi * u) ** 1.5)
    ds = np.diff(s)
    x = np.r_[0, np.cumsum(np.cos(th[:-1]) * ds)]
    z = h - np.r_[0, np.cumsum(np.sin(th[:-1]) * ds)]
    stations = [k * mech_length / n for k in range(n + 1)] + [total]
    px, pz = np.interp(stations, s, x), np.interp(stations, s, z)
    ang = np.degrees(np.arctan2(-(np.diff(pz)), np.diff(px)))
    return dict(root_pitch=float(ang[0]), droop=list(np.r_[0.0, np.diff(ang[:n])]), tip_bend=float(ang[n] - ang[n - 1]),
                points=np.c_[px, pz], lowest=float(z.min()), tip_height=float(z[-1]), reach=float(x[-1]))
