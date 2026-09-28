"""Plots and animations of simulation results (README sections 24, 27, 29)."""
from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import animation
import numpy as np

INK = "#1f2430"
HIP = "#3b5bdb"
TIP = "#e8590c"


def response_plots(r, path: Path, title=""):
    """Four-panel figure: hip vs tip yaw, tip displacement, joint yaw waterfall, loads."""
    t = r["time"]
    fig, ax = plt.subplots(2, 2, figsize=(13, 8), constrained_layout=True)
    a = ax[0, 0]
    a.plot(t, r["hip_yaw"], color=HIP, lw=2, label="hip (pelvis) yaw")
    a.plot(t, r["tip_heading"], color=TIP, lw=2, label="tail tip heading")
    a.axvline(r["stop_time"], color="0.6", ls=":", lw=1)
    a.set(xlabel="time (s)", ylabel="yaw (deg)", title="Hip yaw vs tip yaw")
    a.grid(alpha=.3); a.legend()
    a = ax[0, 1]
    a.plot(t, r["tip_disp"] * 1000, color=TIP, lw=2, label="|tip - rigid-carried tip|")
    a.plot(t, r["tip_disp_lat"] * 1000, color="0.4", lw=1.2, label="lateral component (hip frame)")
    a.set(xlabel="time (s)", ylabel="mm", title="Tip displacement relative to a rigid tail")
    a.grid(alpha=.3); a.legend()
    a = ax[1, 0]
    n = r["yaw"].shape[1]
    cmap = plt.get_cmap("viridis")
    for i in range(n):
        a.plot(t, r["yaw"][:, i], color=cmap(i / max(n - 1, 1)), lw=1.6, label=f"J{i+1}")
    a.set(xlabel="time (s)", ylabel="joint yaw (deg)", title="Joint yaw: does the wave travel root -> tip?")
    a.grid(alpha=.3); a.legend(ncol=4, fontsize=8)
    a = ax[1, 1]
    for i in range(n):
        a.plot(t, r["neck_moment"][:, i], color=cmap(i / max(n - 1, 1)), lw=1.2)
    a.plot(t, r["floor_force"], color="k", lw=1.5, ls="--", label="floor contact force (N)")
    a.set(xlabel="time (s)", ylabel="N*m  /  N", title="Ball-neck bending moment per joint; floor force")
    a.grid(alpha=.3); a.legend()
    fig.suptitle(title or f"{r['label']} - {r['motion']}", fontsize=13)
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=110)
    plt.close(fig)


def waterfall(r, path: Path, title=""):
    """Offset joint-yaw traces with the time of each joint's first peak marked."""
    t, y = r["time"], r["yaw"]
    n = y.shape[1]
    fig, a = plt.subplots(figsize=(9, 6), constrained_layout=True)
    cmap = plt.get_cmap("viridis")
    span = max(np.abs(y).max(), 1)
    for i in range(n):
        off = -i * span * 0.9
        a.plot(t, y[:, i] + off, color=cmap(i / max(n - 1, 1)), lw=1.8)
        k = int(np.argmax(np.abs(y[:, i])))
        a.plot(t[k], y[k, i] + off, "o", color=cmap(i / max(n - 1, 1)))
        a.text(t[0] - 0.05 * t[-1], off, f"J{i+1}", va="center", ha="right")
    a.set_yticks([])
    a.set(xlabel="time (s)", title=title or "Joint yaw waterfall (dot = largest excursion)")
    a.grid(alpha=.3, axis="x")
    fig.savefig(path, dpi=110)
    plt.close(fig)


def _actor_outline(ax, view, hip_pos, height, yaw_deg=0.0):
    """Simple performer silhouette for scale (top or side view)."""
    if view == "side":
        x0, z0 = hip_pos[0], 0
        ax.add_patch(plt.Rectangle((x0 - 0.13, 0), 0.26, height * 0.53, fc="0.85", ec="0.6"))
        ax.add_patch(plt.Rectangle((x0 - 0.16, height * 0.53), 0.32, height * 0.34, fc="0.85", ec="0.6"))
        ax.add_patch(plt.Circle((x0, height * 0.93), height * 0.065, fc="0.85", ec="0.6"))
    else:
        c, s = np.cos(np.radians(yaw_deg)), np.sin(np.radians(yaw_deg))
        pts = np.array([[0.13, 0.2], [0.13, -0.2], [-0.13, -0.2], [-0.13, 0.2]])
        R = np.array([[c, -s], [s, c]])
        pts = pts @ R.T + hip_pos[:2]
        ax.add_patch(plt.Polygon(pts, fc="0.85", ec="0.6"))


def animate(results, path: Path, height=1.727, titles=None, fps=30, stride=None):
    """Top + side view animation; several results are shown side by side."""
    if isinstance(results, dict):
        results = [results]
    k = len(results)
    fig, axes = plt.subplots(2, k, figsize=(4.2 * k, 7.2), squeeze=False, constrained_layout=True)
    t = results[0]["time"]
    dt = t[1] - t[0]
    stride = stride or max(1, int(round(1 / (fps * dt))))
    frames = range(0, len(t), stride)
    arts = []
    for j, r in enumerate(results):
        top, side = axes[0, j], axes[1, j]
        b = r["bodies"]
        hp = r["pelvis_pos"]
        for ax, view in ((top, "top"), (side, "side")):
            ax.set_aspect("equal")
            ax.grid(alpha=.25)
        top.set(xlim=(-1.9, 0.5), ylim=(-1.2, 1.2), xlabel="x (m)", ylabel="y (m)")
        side.set(xlim=(-1.9, 0.5), ylim=(0, 1.9), xlabel="x (m)", ylabel="z (m)")
        top.set_title((titles[j] if titles else r["label"]) + "  top", fontsize=10)
        side.set_title("side", fontsize=10)
        _actor_outline(side, "side", hp[0], height)
        side.axhline(0, color="k", lw=1)
        # ghost of the rest pose
        top.plot(b[0, :, 0], b[0, :, 1], color="0.8", lw=1)
        l_top, = top.plot([], [], "-o", color=INK, lw=3, ms=4)
        l_side, = side.plot([], [], "-o", color=INK, lw=3, ms=4)
        tip_top, = top.plot([], [], "o", color=TIP, ms=7)
        trail, = top.plot([], [], "-", color=TIP, lw=1, alpha=.5)
        hip_line, = top.plot([], [], "-", color=HIP, lw=3)
        txt = top.text(0.02, 0.96, "", transform=top.transAxes, va="top", fontsize=9)
        arts.append((r, l_top, l_side, tip_top, trail, hip_line, txt))

    def update(f):
        out = []
        for r, l_top, l_side, tip_top, trail, hip_line, txt in arts:
            b = r["bodies"][f]
            hp = r["pelvis_pos"][f]
            yaw = np.radians(r["pelvis_ypr"][f][0])
            l_top.set_data(np.r_[hp[0], b[:, 0]], np.r_[hp[1], b[:, 1]])
            l_side.set_data(np.r_[hp[0], b[:, 0]], np.r_[hp[2], b[:, 2]])
            tip_top.set_data([b[-1, 0]], [b[-1, 1]])
            f0 = max(0, f - 60)
            trail.set_data(r["bodies"][f0:f + 1, -1, 0], r["bodies"][f0:f + 1, -1, 1])
            d = 0.3 * np.array([np.cos(yaw), np.sin(yaw)])
            hip_line.set_data([hp[0], hp[0] + d[0]], [hp[1], hp[1] + d[1]])
            txt.set_text(f"t={r['time'][f]:.2f}s  hip {r['hip_yaw'][f]:+.0f}°  tip {r['tip_heading'][f]:+.0f}°")
            out += [l_top, l_side, tip_top, trail, hip_line, txt]
        return out

    ani = animation.FuncAnimation(fig, update, frames=frames, blit=True)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.suffix == ".gif":
        ani.save(path, writer=animation.PillowWriter(fps=fps))
    else:
        ani.save(path, writer=animation.FFMpegWriter(fps=fps, bitrate=2400))
    plt.close(fig)


def comparison_plot(results: dict, path: Path, key="tip_heading", title=""):
    """Overlay one signal from several configurations on identical inputs."""
    fig, a = plt.subplots(figsize=(10, 5), constrained_layout=True)
    first = next(iter(results.values()))
    a.plot(first["time"], first["hip_yaw"], color="k", lw=2, ls="--", label="hip yaw (input)")
    for name, r in results.items():
        a.plot(r["time"], r[key], lw=1.8, label=name)
    a.set(xlabel="time (s)", ylabel="deg", title=title)
    a.grid(alpha=.3); a.legend()
    fig.savefig(path, dpi=110)
    plt.close(fig)
