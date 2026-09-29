"""Single-source dimensional spec of the printable tail (millimetres, degrees).

Pure Python (math only) so FreeCAD's bundled interpreter, the physics
package and the OpenSCAD consistency test can all import it.

Frames: each joint frame has its origin at the ball centre, +x distal along
the tail, +z dorsal. The ball belongs to the parent (hip mount or vertebra
i-1); the socket seat, cap and frame belong to vertebra i.

Print assumptions (docs/printing.md): Ender 3 V2 + Sprite Pro with a
1.2 mm nozzle, 1.3 mm extrusion width, 0.6 mm layers, PETG.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
import json
import math

# --------------------------------------------------------------------- inputs


@dataclass
class CadParams:
    joint_count: int = 8
    tail_length: float = 1400.0
    mech_length: float = 1200.0
    root_diameter: float = 190.0
    last_mech_diameter: float = 70.0
    tip_diameter: float = 40.0
    taper_exponent: float = 1.3
    skin_root: float = 20.0
    skin_tip: float = 4.0
    cord_diameter: float = 6.0
    cord_preload: float = 20.0          # N, set with the tip compression spring
    max_yaw: list = field(default_factory=lambda: [8, 10, 12, 15, 18, 20, 24, 28])
    pitch_ratio: float = 0.7
    max_roll: float = 7.0
    root_pitch: float = 15.0
    rest_droop: float = 1.5
    rest_droop_list: list = field(default_factory=list)  # per-joint rest bend (deg, + = down); [0] unused (root_pitch)
    # ball / socket
    ball_ratio: float = 0.15
    ball_min: float = 17.0
    ball_max: float = 28.0
    clear: float = 0.4                  # radial running clearance, 1.2 mm nozzle FDM
    liner: float = 0.5                  # PTFE tape / thin felt liner in the seat
    stop_pad: float = 0.8               # adhesive felt/rubber pad at the cap mouth
    # printing
    line_w: float = 1.3
    layer_h: float = 0.6
    # hardware
    bolt_d: float = 4.0                 # M4 throughout
    bolt_clear: float = 4.5
    nut_af: float = 7.0                 # M4 nut across flats
    nut_h: float = 3.2
    head_d: float = 7.0                 # M4 socket-head cap screw
    head_h: float = 4.0
    pin_protrude: float = 3.0           # roll-key screw: M4x12 on large balls, M3x8 on small
    cap_ear_x: float = 5.0              # child spring anchor, mm proximal of the pivot (on the cap)
    spring_hole: float = 4.5            # anchor hole for spring hook / M4 pin
    coil_od_ratio: float = 0.08         # max spring coil OD / envelope diameter
    # hip mount
    root_back_offset: float = 200.0     # pelvis centre -> joint 1 centre
    root_dz: float = 0.0                # joint 1 centre height relative to the pelvis centre (mm)
    plate_z: float = 0.0                # mounting-plate centre height relative to the pelvis centre (mm)
    harness_plate_offset: float = 120.0 # pelvis centre -> back of hip plate
    hip_plate_w: float = 190.0
    hip_plate_h: float = 150.0
    hip_plate_t: float = 8.0
    max_print: float = 200.0

    def to_json(self):
        return json.dumps(asdict(self), indent=2)


# ------------------------------------------------------------------ derived


def _u(p, i):
    n = p.joint_count
    return (i - 1) / (n - 1) if n > 1 else 0.0


def _interp(ref, n, i):
    if len(ref) == n:
        return float(ref[i - 1])
    x = (i - 1) / (n - 1) * (len(ref) - 1) if n > 1 else 0
    k = min(int(x), len(ref) - 2)
    return ref[k] + (ref[k + 1] - ref[k]) * (x - k)


def spacing(p):
    return p.mech_length / p.joint_count


def D(p, i):
    """Envelope diameter of vertebra i (1-based), README section 4."""
    return p.last_mech_diameter + (p.root_diameter - p.last_mech_diameter) * (1 - _u(p, i)) ** p.taper_exponent


def skin(p, i):
    return p.skin_root + (p.skin_tip - p.skin_root) * _u(p, i)


def RF(p, i):
    """Frame (skin former) radius."""
    return D(p, i) / 2 - skin(p, i)


def RB(p, i):
    return min(max(p.ball_ratio * D(p, i), p.ball_min), p.ball_max)


def RS(p, i):
    return RB(p, i) + p.clear + p.liner


def bore_r(p):
    return p.cord_diameter / 2 + 1.0


def wall(p, lines=3):
    return lines * p.line_w


def RN(p, i):
    """Ball neck radius: half the ball, never thinner than 3 lines around the cord bore."""
    return max(0.5 * RB(p, i), bore_r(p) + wall(p))


def yaw_lim(p, i):
    return _interp(p.max_yaw, p.joint_count, i)


def pitch_lim(p, i):
    return p.pitch_ratio * yaw_lim(p, i)


def alpha(p, i):
    """Angular half-width the neck (+ stop pad) occupies seen from the centre."""
    return math.degrees(math.asin((RN(p, i) + p.stop_pad) / RS(p, i)))


def beta_y(p, i):
    return yaw_lim(p, i) + alpha(p, i)


def beta_p(p, i):
    return pitch_lim(p, i) + alpha(p, i)


def wall_socket(p):
    return 5 * p.line_w                       # 6.5 mm: room for the roll-key slot


def slot_depth(p):
    return p.pin_protrude + 1.0


def cap_h(p, i):
    """Axial height of the cap: the deepest point of the elliptical mouth."""
    return RS(p, i) * math.cos(math.radians(beta_p(p, i)))


def mouth_r(p, i):
    """Radius of the mouth rim on the socket sphere, yaw direction (largest)."""
    return RS(p, i) * math.sin(math.radians(beta_y(p, i)))


def bolt_pcd_r(p, i):
    """Cap bolt circle, on lobes at 45 deg azimuths just outside the socket wall."""
    return RS(p, i) + wall_socket(p) + p.bolt_clear / 2 + p.line_w + 1.0


def lobe_r(p):
    return p.bolt_clear / 2 + 2 * p.line_w + 0.5


def cap_outer_r(p, i):
    return RS(p, i) + wall_socket(p)


def flange_bolt_r(p, i):
    """Ball flange bolt circle (heads sit beside the neck)."""
    return RN(p, i) + p.head_d / 2 + 1.0


def flange_r(p, i):
    return flange_bolt_r(p, i) + lobe_r(p)


def flange_t(p):
    return 6.0


def max_bend(p, i):
    return max(yaw_lim(p, i), pitch_lim(p, i))


def cap_lobe_t(p):
    return 6.0


def droop(p, i):
    """Rest bend of joint i (deg, positive = down). Joint 1's is part of the root pitch."""
    if i == 1:
        return 0.0
    if p.rest_droop_list:
        return float(p.rest_droop_list[i - 1])
    return p.rest_droop


def DF(p, i):
    """Ball centre -> ball flange face distance (neck length, along the parent axis).

    The flange (with its bolt heads) must clear the cap's top face and its
    bolt lobes when the joint is at its largest bend. A wedge flange (rest bend)
    tilts the flange rim toward the cap, so that tilt is added."""
    t = math.radians(max_bend(p, i))
    top = cap_h(p, i) * math.cos(t) + cap_outer_r(p, i) * math.sin(t)
    lobes = cap_lobe_t(p) + p.head_h + (bolt_pcd_r(p, i) + lobe_r(p)) * math.sin(t)
    wedge = flange_r(p, i) * math.sin(math.radians(abs(droop(p, i))))
    return max(top, lobes) + p.head_h + 2.0 + wedge


def seat_depth(p, i):
    """Socket housing extends this far distally from the ball centre."""
    return RS(p, i) + wall(p)


def spring_span_child(p):
    """Signed x of the child anchor: an ear on the socket cap, 5 mm PROXIMAL of
    the pivot. With both anchors on the proximal side the preloaded springs add
    positive (centring) geometric stiffness instead of a yaw-roll saddle
    (docs/physics.md, "spring geometry and twist stability")."""
    return -p.cap_ear_x


def spring_span_parent(p, i):
    """Parent anchor: hole 4 mm inside the distal edge of the previous fins
    (or the hip-mount arms for joint 1); the spring coil lies beyond the fin end."""
    return DF(p, i) + flange_t(p) + 4.0


def fin_t(p, i):
    """Frame fin thickness: three 1.3 mm lines on large vertebrae, two on small ones."""
    return (3 if RF(p, i) > 50 else 2) * p.line_w + 0.1


# The cap is printed as two halves split on a plane through the joint axis at this angle (about X, from dorsal).
# A one-piece cap can never be fitted: its mouth is smaller than both the ball and the ball's bolt flange, and
# the split ball does not help (half a ball is still a full diameter wide). The halves slide onto the assembled
# ball and neck from the sides and bolt to the body with two of the four cap bolts each.
CAP_SPLIT_DEG = 22.5


def cap_split_margins(p, i):
    """Tangential clearance (mm) from the cap split line to the nearest spring ear, bolt lobe and roll-key slot."""
    s = math.sin(math.radians(CAP_SPLIT_DEG))
    ear = cap_outer_r(p, i) * s - ear_w(p, i) / 2                       # dorsal ear, 22.5 deg away
    lobe = (cap_outer_r(p, i) - 3) * math.sin(math.radians(45 - CAP_SPLIT_DEG)) - lobe_r(p)   # lobe at 45 deg
    slot = RS(p, i) * s - slot_width(p, i) / 2                          # dorsal roll-key slot
    return ear, lobe, slot


def ear_w(p, i):
    """Width of the spring ears on the cap (tangential)."""
    return max(12.0, 0.6 * cap_outer_r(p, i))


def neck_section_modulus(p, i):
    """Elastic section modulus of the hollow ball neck (mm^3)."""
    Do, Di = 2 * RN(p, i), 2 * bore_r(p)
    return math.pi * (Do ** 4 - Di ** 4) / (32 * Do)


def cap_ear_t(p, i=None):
    """Spring-ear thickness: 16 mm on the root caps (dorsal spring pairs up to ~400 N), 12 mm elsewhere."""
    return 16.0 if (i is not None and RB(p, i) >= 22) else 12.0


def spring_arm(p, i):
    """Radial offset of the spring line of action for joint i."""
    need = cap_outer_r(p, i) + coil_od(p, i) / 2 + 0.5
    return min(max(need, 0.8 * RF(p, i)), D(p, i) / 2 - 6.0)


def body_len(p, i):
    """Vertebra body: from its proximal ball centre (x = 0) to its distal flange face."""
    L = spacing(p)
    if i == p.joint_count:
        return L - tip_plug_len(p)
    return L - DF(p, i + 1) - flange_t(p)


def tip_plug_len(p):
    return 25.0


def pin_spec(p, i):
    """(thread d, length, head d, head h) of the roll-key screw for joint i."""
    return (4.0, 12.0, 7.0, 4.0) if RB(p, i) >= 19 else (3.0, 8.0, 5.5, 3.0)


def pin_pocket_z(p, i):
    """z of the underside of the roll-key screw head inside the ball."""
    return RB(p, i) + p.pin_protrude - pin_spec(p, i)[1]


def slot_width(p, i):
    """Roll-key slot width: pin diameter plus the roll travel either side."""
    d = pin_spec(p, i)[0]
    r = RB(p, i) + p.pin_protrude / 2
    return d + 0.6 + 2 * r * math.sin(math.radians(p.max_roll))


def coil_od(p, i):
    return min(max(p.coil_od_ratio * D(p, i), 5.0), 16.0)


def cord_flare(p, i):
    return max_bend(p, i) + 6.0


def summary(p: CadParams):
    rows = []
    for i in range(1, p.joint_count + 1):
        rows.append(dict(
            i=i, D=D(p, i), RF=RF(p, i), RB=RB(p, i), RS=RS(p, i), RN=RN(p, i),
            yaw=yaw_lim(p, i), pitch=pitch_lim(p, i), alpha=alpha(p, i), beta_y=beta_y(p, i), beta_p=beta_p(p, i),
            cap_h=cap_h(p, i), mouth_r=mouth_r(p, i), retention_lip=RB(p, i) - mouth_r(p, i),
            bolt_pcd_r=bolt_pcd_r(p, i), cap_outer_r=cap_outer_r(p, i), flange_r=flange_r(p, i), DF=DF(p, i),
            body_len=body_len(p, i), spring_arm=spring_arm(p, i), pin_pocket_z=pin_pocket_z(p, i),
            span_parent=spring_span_parent(p, i), span_child=spring_span_child(p),
        ))
    return rows


def checks(p: CadParams):
    """Return a list of (name, ok, detail) manufacturability/clearance checks."""
    out = []
    for r in summary(p):
        i = r["i"]
        out.append((f"J{i} retention lip >= 1.5 mm", r["retention_lip"] >= 1.5, f"{r['retention_lip']:.2f} mm"))
        clear = r["spring_arm"] - coil_od(p, i) / 2 - r["cap_outer_r"]
        out.append((f"J{i} spring clears cap", clear >= 0.4, f"{clear:.2f} mm"))
        room = D(p, i) / 2 - r["spring_arm"]
        out.append((f"J{i} spring anchor inside skin envelope", room >= 5.9, f"{room:.2f} mm"))
        ear_swing = (r["spring_arm"] + 5) * math.sin(math.radians(max_bend(p, i))) + cap_ear_t(p, i)
        out.append((f"J{i} cap ear clears parent fins at full bend", DF(p, i) + flange_t(p) - ear_swing >= 3,
                    f"{DF(p, i) + flange_t(p) - ear_swing:.1f} mm"))
        sl = r["span_parent"] + r["span_child"]
        out.append((f"J{i} spring installed length >= 30 mm", sl >= 30, f"{sl:.1f} mm"))
        out.append((f"V{i} body length positive", r["body_len"] > r["RS"] + 10, f"{r['body_len']:.1f} mm"))
        out.append((f"V{i} fits {p.max_print:.0f} mm cube", 2 * RF(p, i) <= p.max_print and r["body_len"] <= p.max_print,
                    f"dia {2*RF(p, i):.1f}, len {r['body_len']:.1f}"))
        pz = r["pin_pocket_z"] - pin_spec(p, i)[3]
        out.append((f"J{i} roll-key head clears cord bore", pz > bore_r(p) + 1.0, f"head bottom z={pz:.1f}"))
        out.append((f"J{i} neck wall >= 3 lines", r["RN"] - bore_r(p) >= 3 * p.line_w - 1e-9, f"{r['RN']-bore_r(p):.2f} mm"))
        m = cap_split_margins(p, i)
        out.append((f"J{i} cap split clears ears, lobes and roll slot by >= 2 mm", min(m) >= 2.0,
                    "ear %.1f / lobe %.1f / slot %.1f mm" % m))
    return out


if __name__ == "__main__":
    p = CadParams()
    for r in summary(p):
        print({k: round(v, 2) for k, v in r.items()})
    for name, ok, det in checks(p):
        if not ok:
            print("FAIL", name, det)
    print("checks:", sum(ok for _, ok, _ in checks(p)), "/", len(checks(p)))
