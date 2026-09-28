"""Scalar metrics (README section 24) and the motion-quality score."""
from __future__ import annotations

import csv
import math
from pathlib import Path

import numpy as np

VISIBLE_DEG = 2.0      # tip-heading excursion treated as visible on camera (~50 mm at the tip)


def _extrema(t, x, thr):
    """Alternating local extrema of x whose magnitude exceeds thr."""
    out = []
    for k in range(1, len(x) - 1):
        if (x[k] - x[k-1]) * (x[k+1] - x[k]) <= 0 and abs(x[k]) > thr:
            if out and np.sign(out[-1][1]) == np.sign(x[k]):
                if abs(x[k]) > abs(out[-1][1]):
                    out[-1] = (t[k], x[k])
                continue
            out.append((t[k], x[k]))
    return out


def common(r):
    t = r["time"]
    speed = np.linalg.norm(r["tip_vel"], axis=1)
    acc = np.linalg.norm(r["tip_acc"], axis=1)
    ang = np.abs(np.stack([r["yaw"], r["pitch"], r["roll"]]))
    return dict(
        peak_tip_velocity=float(speed.max()),
        peak_tip_acceleration=float(acc.max()),
        maximum_joint_angle=float(ang.max()),
        maximum_joint_yaw=float(np.abs(r["yaw"]).max()),
        maximum_joint_roll=float(np.abs(r["roll"]).max()),
        max_tip_displacement=float(r["tip_disp"].max()),
        max_floor_force=float(r["floor_force"].max()),
        min_tip_height=float(r["tip_height"].min()),
        peak_stop_torque=float(np.max(r["peak_stop_torque"])),
        peak_neck_moment=float(np.max(r["peak_neck_moment"])),
        min_seat_compression=float(np.min(r["min_seat_comp"])),
        max_cord_tension=float(np.max(r["cord_tension"])),
        max_hip_tracking_error_deg=float(r["hip_err"].max()),
        min_floor_clearance=float(r["clearance"].min()) if "clearance" in r else float("nan"),
        rest_floor_clearance=float(r["clearance"][0]) if "clearance" in r else float("nan"),
        peak_root_moment=float(r["root_moment"].max()) if "root_moment" in r else float("nan"),
        rest_root_moment=float(r["root_moment"][5]) if "root_moment" in r else float("nan"),
    )


def step_response(r, final):
    """Metrics for a hip yaw step (hip snap / dramatic turn)."""
    t, tip, hip = r["time"], r["tip_heading"], r["hip_yaw"]
    ts = r["stop_time"]
    lag = hip - tip
    after = t >= ts
    dev = tip - final
    ex = _extrema(t[after], dev[after], VISIBLE_DEG)
    # count swings that happen after the tip first passes the hip heading
    tail = dev[after]
    end = float(np.mean(tail[-40:]))
    outside = np.where(np.abs(tail - end) > VISIBLE_DEG)[0]
    settle = float(t[after][outside[-1]] - ts) if len(outside) else 0.0
    m = dict(
        maximum_tip_lag=float(lag.max()),
        maximum_tip_overshoot=float(max(0.0, (tip - final).max())),
        overshoot_pct=float(max(0.0, (tip - final).max()) / abs(final) * 100),
        visible_swings=len(ex),
        oscillation_count=int(math.ceil(len(ex) / 2)),
        settling_time=settle,
        residual_offset=abs(end),
        peak_extrema=[round(float(v), 2) for _, v in ex[:6]],
    )
    m.update(common(r))
    return m


def walk_response(r):
    t = r["time"]
    ss = t >= t[-1] / 2
    hip_amp = (r["hip_yaw"][ss].max() - r["hip_yaw"][ss].min()) / 2
    tip_amp = (r["tip_heading"][ss].max() - r["tip_heading"][ss].min()) / 2
    lat = r["tip_disp_lat"][ss]
    m = dict(
        hip_yaw_amplitude=float(hip_amp),
        tip_heading_amplitude=float(tip_amp),
        whip_ratio=float(tip_amp / max(hip_amp, 1e-6)),
        tip_lateral_amplitude=float((lat.max() - lat.min()) / 2),
        stop_hits=int((np.max(r["stop_torque"][ss], axis=1) > 0.05).sum()),
    )
    m.update(common(r))
    return m


def displacement_response(r):
    t = r["time"]
    after = t >= r["stop_time"]
    lat = r["tip_disp_lat"]
    end = float(np.mean(lat[-40:]))
    outside = np.where(np.abs(lat[after] - end) > 0.03)[0]
    m = dict(
        max_tip_lateral=float(np.abs(lat).max()),
        residual_lateral=abs(end),
        settling_time=float(t[after][outside[-1]] - r["stop_time"]) if len(outside) else 0.0,
    )
    m.update(common(r))
    return m


def evaluate(r):
    name = r["motion"]
    if name.startswith("hip_snap"):
        return step_response(r, 30.0)
    if name.startswith("dramatic_turn"):
        return step_response(r, 45.0)
    if name.startswith("walk"):
        return walk_response(r)
    return displacement_response(r)


def score(results: dict) -> tuple[float, dict]:
    """Penalty (lower is better) for departures from the README motion target.

    Each term is 0 inside the desired band and grows quadratically outside.
    The bands encode README sections 1, 11, 14, 15 and 26.
    """
    def band(x, lo, hi, scale):
        if x < lo:
            return ((lo - x) / scale) ** 2
        if x > hi:
            return ((x - hi) / scale) ** 2
        return 0.0

    s = results["hip_snap_30"]
    terms = {
        "snap_lag": band(s["maximum_tip_lag"], 10, 40, 5),
        "snap_overshoot": band(s["maximum_tip_overshoot"], 4, 12, 2),
        "snap_oscillations": band(s["oscillation_count"], 1, 2, 0.7),
        "snap_settle": band(s["settling_time"], 0.8, 3.0, 0.7),
        "snap_residual": band(s["residual_offset"], 0, 3, 1.5),
    }
    if "dramatic_turn_45" in results:
        d = results["dramatic_turn_45"]
        terms["turn_overshoot"] = band(d["maximum_tip_overshoot"], 6, 18, 3)
        terms["turn_stop_torque"] = band(d["peak_stop_torque"], 0, 15, 5)
    if "linear" in results and results["linear"]["lowest_mode_hz"] == results["linear"]["lowest_mode_hz"]:
        terms["unstable_twist"] = band(results["linear"]["lowest_mode_hz"], 0.1, 99, 0.05)
    walks = [v for k, v in results.items() if k.startswith("walk") and not k.endswith("literal")]
    for w in walks:
        terms[f"walk_whip_{len(terms)}"] = band(w["whip_ratio"], 0.8, 2.2, 0.5)
        terms[f"walk_floor_{len(terms)}"] = band(w["max_floor_force"], 0, 0.5, 2)
    return float(sum(terms.values())), terms


def write_csv(r, path: Path):
    """Per-timestep CSV (README section 24)."""
    n = r["yaw"].shape[1]
    header = ["time", "pelvis_x", "pelvis_y", "pelvis_z", "pelvis_yaw", "pelvis_pitch", "pelvis_roll"]
    for key in ("yaw", "pitch", "roll"):
        header += [f"joint{i+1}_{key}" for i in range(n)]
    header += ["tip_x", "tip_y", "tip_z", "tip_vx", "tip_vy", "tip_vz", "tip_ax", "tip_ay", "tip_az",
               "tip_heading", "tip_displacement", "cord_tension", "floor_force"]
    header += [f"joint{i+1}_ball_force" for i in range(n)] + [f"joint{i+1}_neck_moment" for i in range(n)]
    path.parent.mkdir(parents=True, exist_ok=True)
    import gzip
    opener = (lambda: gzip.open(path, "wt", newline="")) if path.suffix == ".gz" else (lambda: open(path, "w", newline=""))
    with opener() as f:
        w = csv.writer(f)
        w.writerow(header)
        for k in range(len(r["time"])):
            row = [r["time"][k], *r["pelvis_pos"][k], *r["pelvis_ypr"][k], *r["yaw"][k], *r["pitch"][k], *r["roll"][k],
                   *r["tip_pos"][k], *r["tip_vel"][k], *r["tip_acc"][k], r["tip_heading"][k], r["tip_disp"][k],
                   r["cord_tension"][k], r["floor_force"][k], *r["joint_force"][k], *r["neck_moment"][k]]
            w.writerow([f"{v:.6g}" for v in row])
