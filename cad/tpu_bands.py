"""Printable TPU strap pairs that stand in for the Barney tail's 18 extension springs.

    PYTHONPATH=. python cad/tpu_bands.py                 # nominal material curves
    PYTHONPATH=. python cad/tpu_bands.py --calib cad/tpu_calibration.json   # after the coupon test

Each spring becomes a PAIR of identical flat straps, one on each side of the anchor plate (cap ear / fin boss /
hip-mount arm), held by an M4 bolt through the existing 4.5 mm spring hole at each end. The pull stays on the
original line of action, the two sides cancel (no roll moment), and each strap carries half of k and T0.

Sizing. A strap has no initial tension, so the spring's T0/k fixes how far it must already be stretched at the
rest span P: T0 = F(P), k = dF/dP. For a cross-section A and a gauge length Lg, F = A*sigma(eps) and the two
conditions pin down eps and A for any material curve sigma(eps). Where a band would need more stretch than the
material should hold all night (eps_max), the strain is capped and T0 is still met exactly (rest pose), with k
somewhat stiffer than the spring; tailsim checks the effect (docs/tpu_bands.md).

Frames match cad/openscad/suit_tail.scad: joint i frame at the ball-i centre, +x distal, +z dorsal.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from dataclasses import dataclass, asdict
from pathlib import Path

import numpy as np
from scipy.optimize import brentq

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from cad import geometry as g  # noqa: E402

OUT = ROOT / "cad" / "stl" / "barney_tpu_bands"
HOLE = 4.4            # strap eye hole for an M4 bolt (TPU closes up a little when printed; snug on the bolt)
LAYER = 0.4           # TPU layer height with the 1.2 mm nozzle; strap thicknesses are multiples of this
W_MIN = 3.0           # narrowest gauge that prints reliably as 2+ lines of 1.2 mm TPU
EYE_RATIO = 2.0       # eye section (2 ligaments x eye thickness) / gauge section: keeps the eyes stiff
CLEAR = 0.8           # running clearance to printed parts (mm)
PARENT_STEP = {3: 0.4, 6: 1.5}  # strap plane steps in this much from child to parent eye (mm); default 1.0
PAD_R = HOLE / 2 + 2.4    # spacer pad: a bearing ring round the hole (the ear flares wider further from the hole)


# ----------------------------------------------------------------- materials
@dataclass
class Material:
    """Engineering stress (MPa) vs strain of a broken-in strap, referenced to its broken-in free length.

    kind "tanh":  sigma = s1*tanh(E0*eps/s1) + E2*eps      (95A: stiff start, soft knee, long plateau)
    kind "neo":   sigma = (E/3)*(lam - 1/lam^2)            (65A: rubber-like)
    set_frac: permanent growth of the gauge length after break-in (printed gauge = broken-in gauge / (1+set)).
    eps_max: highest rest strain allowed (creep / stress-relaxation budget for an evening's wear).
    """
    name: str
    kind: str
    E0: float
    s1: float = 1.0
    E2: float = 0.0
    set_frac: float = 0.0
    eps_max: float = 0.3

    def sigma(self, e):
        if self.kind == "tanh":
            return self.s1 * math.tanh(self.E0 * e / self.s1) + self.E2 * e
        lam = 1 + e
        return self.E0 / 3 * (lam - 1 / lam ** 2)

    def dsigma(self, e):
        if self.kind == "tanh":
            return self.E0 / math.cosh(self.E0 * e / self.s1) ** 2 + self.E2
        lam = 1 + e
        return self.E0 / 3 * (1 + 2 / lam ** 3)

    def strain(self, s):
        """Inverse of sigma (monotone)."""
        return brentq(lambda e: self.sigma(e) - s, 0.0, 20.0) if s > 0 else 0.0


# Nominal curves. TPU brands differ by ~3x in modulus, so print the coupons and run --calib before trusting
# forces to better than +-50 %. 95A: datasheet-typical 26 MPa start, knee ~8.6 MPa at 55 %. 65A: ~4.5 MPa.
MATERIALS = {
    "tpu95a": Material("tpu95a", "tanh", E0=22.0, s1=6.8, E2=4.0, set_frac=0.08, eps_max=0.25),
    "tpu65a": Material("tpu65a", "neo", E0=4.5, set_frac=0.03, eps_max=0.80),
}


# ----------------------------------------------------------------- geometry of each spring
def Ry(d):
    d = math.radians(d)
    return np.array([[math.cos(d), 0, math.sin(d)], [0, 1, 0], [-math.sin(d), 0, math.cos(d)]])


def Rx(a):
    a = math.radians(a)
    return np.array([[1, 0, 0], [0, math.cos(a), -math.sin(a)], [0, math.sin(a), math.cos(a)]])


SIDE_ANGLE = {"D": 0, "L": 90, "R": -90}      # at_springs(): rotate about X; L sits at -y, R at +y (mirror pair)


def anchors(c, i, side):
    """Child (cap ear) and parent (fin / hip arm) hole centres in the joint-i frame, and hole axes."""
    a, s, d, ang = g.spring_arm(c, i), g.spring_span_parent(c, i), g.droop(c, i), SIDE_ANGLE[side]
    child = Rx(ang) @ np.array([-c.cap_ear_x, 0.0, a])
    parent = Ry(d).T @ (Rx(ang) @ np.array([-s, 0.0, a]))
    ax_c = Rx(ang) @ np.array([0, 1.0, 0])
    ax_p = Ry(d).T @ (Rx(ang) @ np.array([0, 1.0, 0]))
    return child, parent, ax_c, ax_p


def ear_halfwidth(c, i, z):
    """Half-width (along the hole axis) of the cap ear at radial height z (the ear hull narrows to 0.6 ear_w)."""
    ew, a, R = g.ear_w(c, i), g.spring_arm(c, i), g.cap_outer_r(c, i)
    z_top, z_bot = a + c.cap_ear_x, R - 3
    f = min(1.0, max(0.0, (z_top - z) / (z_top - z_bot)))
    return 0.3 * ew + f * 0.2 * ew


def parent_plate(c, i):
    """Thickness of the parent anchor plate at the hole: hip-mount arm (12 mm) or fin boss (fin_t + 4)."""
    return 12.0 if i == 1 else g.fin_t(c, i - 1) + 4.0


# ----------------------------------------------------------------- strap design
@dataclass
class Strap:
    joint: int
    side: str
    material: str
    count: int             # straps per spring: a symmetric pair on dorsal springs, one strap on lateral springs
    sgn: int               # single strap: which face of the plate (+/- along the hole axis) it lies on
    k_target: float        # N/mm for the PAIR
    T0_target: float       # N for the PAIR
    span: float            # rest pin-to-pin distance (mm)
    arm: float             # physics moment arm (mm), for reporting
    eps: float = 0.0       # gauge strain at rest (broken-in)
    t: float = 0.0
    w: float = 0.0
    R_eye: float = 0.0
    pad_c: float = 0.0     # child-eye spacer (inner face)
    pad_p: float = 0.0     # parent-eye spacer (inner face)
    ring_c: float = 0.6    # height of the narrow bearing ring at the end of the child spacer (clears the ear flank)
    P_print: float = 0.0   # printed pin-to-pin length
    P_free: float = 0.0    # broken-in free pin-to-pin length
    Lg: float = 0.0        # broken-in gauge length
    k_pair: float = 0.0
    T0_pair: float = 0.0
    T_stop_pair: float = 0.0
    T_stop_spring: float = 0.0
    stretch_stop: float = 0.0
    breakin_len: float = 0.0
    plate_c: float = 0.0
    plate_p: float = 0.0
    bolt_c: int = 0
    bolt_p: int = 0
    capped: bool = False

    @property
    def name(self):
        return f"band_J{self.joint}{self.side}"


def eye_ext(mat, sig_gauge, R):
    """Extension of one eye zone (pin centre -> gauge start, length R) at gauge stress sig_gauge."""
    return R * mat.strain(sig_gauge / EYE_RATIO)


def eye_compl(mat, sig_gauge, R):
    e = mat.strain(sig_gauge / EYE_RATIO)
    return R / (EYE_RATIO * mat.dsigma(e))


def solve(mat, F0, k0, P, R):
    """Per-strap gauge strain, area and broken-in gauge length so that F(P) = F0 and dF/dP = k0."""
    def geom(eps):
        sg = mat.sigma(eps)
        A = F0 / sg
        Lg = (P - 2 * R - 2 * eye_ext(mat, sg, R)) / (1 + eps)
        k = A / (Lg / mat.dsigma(eps) + 2 * eye_compl(mat, sg, R))
        return A, Lg, k
    lo, hi = 0.01, mat.eps_max
    if geom(hi)[2] > k0:                     # cannot get soft enough: cap strain, keep T0
        return hi, *geom(hi), True
    eps = brentq(lambda e: geom(e)[2] - k0, lo, hi)
    return eps, *geom(eps), False


def section(A, w_max):
    """Pick thickness (layer multiple) and width for area A, staying within w_max."""
    for n in range(3, 13):
        t = n * LAYER
        w = A / t
        if w <= w_max:
            return t, max(w, W_MIN)
    t = 12 * LAYER
    return t, A / t


def bolt_len(stack):
    need = stack + 2 * 0.8 + 5.0 + 1.0          # two washers, nylock, one thread showing
    for L in (16, 20, 25, 30, 35, 40, 45, 50):
        if L >= need:
            return L
    return 60


def design(c, sim_springs, mats, choose):
    straps = []
    for s in sim_springs:
        i, side = s["joint"] + 1, s["side"]
        child, parent, _, _ = anchors(c, i, side)
        P = float(np.linalg.norm(child - parent))
        lim = g.yaw_lim(c, i) if side in "LR" else g.pitch_lim(c, i)
        k0, T0 = s["k"] / 1000, s["T0"]
        st = Strap(i, side, "", 2 if side == "D" else 1, 1, k0, T0, P, s["arm"] * 1000,
                   T_stop_spring=T0 + k0 * s["arm"] * 1000 * math.radians(lim))
        # Lateral lines of action cross the ear plate at up to the rest bend (the parent fin is tilted by the wedge),
        # so a far-side strap would have to wrap through the ear: lateral springs get ONE strap on the near side.
        ax_c = anchors(c, i, side)[2]
        st.sgn = 1 if float(np.dot(parent - child, ax_c)) >= 0 else -1
        n = st.count
        a, capR = g.spring_arm(c, i), g.cap_outer_r(c, i)
        mat = mats[choose(i, side)]
        st.material = mat.name
        # radial room: inner edge above the cap surface beside the ear, outer edge inside the frame radius
        w_max = min(2 * (a - capR - CLEAR), 2 * (g.RF(c, i) - a - 2), 14.0)
        R = max(HOLE / 2 + 2.0, 0.5 * w_max / 2 + HOLE / 2)      # first guess, refined below
        for _ in range(4):
            eps, A, Lg, k, capped = solve(mat, T0 / n, k0 / n, P, R)
            t, w = section(A, w_max)
            R = max(HOLE / 2 + 2.0, w / 2 + 1.0)
        st.eps, st.t, st.w, st.R_eye, st.Lg, st.capped = eps, t, w, R, Lg, capped
        A = t * w
        # forces from the as-printed section (width clamped to W_MIN can only add force: re-solve the length)
        sg_rest = (T0 / n) / A
        e_rest = mat.strain(sg_rest)
        st.Lg = (P - 2 * R - 2 * eye_ext(mat, sg_rest, R)) / (1 + e_rest)
        st.eps = e_rest
        st.P_free = st.Lg + 2 * R
        st.P_print = st.Lg / (1 + mat.set_frac) + 2 * R
        st.T0_pair = n * A * mat.sigma(e_rest)
        st.k_pair = n * A / (st.Lg / mat.dsigma(e_rest) + 2 * eye_compl(mat, sg_rest, R))
        # force at the stop: line length grows by about arm * angle (physics arm)
        dl = st.arm * math.radians(lim)

        def F_at(dP):
            return n * A * mat.sigma(brentq(lambda e: st.Lg * (1 + e) + 2 * R + 2 * eye_ext(mat, mat.sigma(e), R)
                                             - (P + dP), 0, 20))
        st.T_stop_pair = F_at(dl)
        st.stretch_stop = (P + dl) / st.P_free - 1
        st.breakin_len = round(st.P_print + 1.2 * (P + dl - st.P_print), 0)
        # spacers: strap planes must clear the ear flanks over the strap's radial extent
        st.plate_c = round(2 * ear_halfwidth(c, i, a - PAD_R), 1)
        # lowest point of the strap beside the ear: at the eye (a - R) or, where the line of action dips toward a
        # drooped parent, at the ear's proximal end (x = -cap_ear_t), where the ear hull is wider
        u = (parent - child) / np.linalg.norm(parent - child)
        rad = Rx(SIDE_ANGLE[side]) @ np.array([0, 0, 1.0])
        lam = (g.cap_ear_t(c, i) - c.cap_ear_x) / max(-u[0], 1e-6)
        z_end = float(np.dot(child + u * lam, rad)) - w / 2
        ear_hw = ear_halfwidth(c, i, min(a - max(R, w / 2), z_end))
        # at the out-of-plane bend limit the strap swings across the ear's proximal corner (x = -cap_ear_t):
        # hold it off by the corner's sideways travel (fit check: cad/check_tpu_bands.py)
        swing = g.yaw_lim(c, i) if side == "D" else g.pitch_lim(c, i)
        corner = (g.cap_ear_t(c, i) - c.cap_ear_x) * math.sin(math.radians(swing))
        st.ring_c = round(max(0.6, ear_hw - st.plate_c / 2 + CLEAR + corner), 1)
        st.pad_c = round(max(0.8, st.ring_c, (EYE_RATIO * w * t / (2 * (R - HOLE / 2))) - t), 1)
        st.plate_p = parent_plate(c, i)
        # parent eye: the strap stays (nearly) parallel to its child-end plane so it cannot swing into the ear
        # corner at full yaw; stepping it in by PARENT_STEP keeps the J6 bolt nut clear of body 5's skirt wall
        st.pad_p = round(max(0.6, (EYE_RATIO * w * t / (2 * (R - HOLE / 2))) - t,
                             st.pad_c + (st.plate_c - st.plate_p) / 2 - PARENT_STEP.get(i, 1.0)), 1)
        st.bolt_c = bolt_len(st.plate_c + n * (st.pad_c + t))
        st.bolt_p = bolt_len(st.plate_p + n * (st.pad_p + t))
        straps.append(st)
    return straps


def default_choice(straps_95, straps_65):
    """95A where it runs at low strain with a printable section, else 65A (rubber-like, recovers better)."""
    pick = {}
    for a, b in zip(straps_95, straps_65):
        ok95 = (not a.capped) and a.eps <= 0.25 and a.w >= W_MIN + 0.5 and a.t * a.w >= 4.0
        pick[(a.joint, a.side)] = "tpu95a" if ok95 else "tpu65a"
    return pick


# ----------------------------------------------------------------- meshes
def strap_mesh(st, tight=0.0, n=48):
    """Strap in print orientation: outer face on the bed (z = 0), spacer pads up. Child eye at x = 0."""
    import manifold3d as m3
    P = st.P_print - tight
    R, w, t = st.R_eye, st.w, st.t
    eye = m3.CrossSection.circle(R, n)
    body = m3.CrossSection.batch_hull([eye, eye.translate((P, 0))])
    neck = m3.CrossSection.square((P, w), center=True).translate((P / 2, 0))
    # dog-bone: eyes + gauge, with 45-degree-ish fillets from the eye to the gauge
    fil = R + 2.0
    outline = (m3.CrossSection.batch_hull([eye, m3.CrossSection.square((0.5, w), center=True).translate((fil, 0))])
               + m3.CrossSection.batch_hull([eye.translate((P, 0)), m3.CrossSection.square((0.5, w), center=True).translate((P - fil, 0))])
               + neck)
    outline = (outline ^ body).simplify(0.02)
    solid = m3.Manifold.extrude(outline, t)
    for x, pad, ring in ((0.0, st.pad_c, st.ring_c), (P, st.pad_p, 0.6)):
        if pad > 0:
            # spacer: full eye radius, then a narrow bearing ring that sits on the plate round the hole
            # radii kept 0.3 mm inside the eye outline (coincident walls make degenerate STL facets)
            if pad - ring >= 0.4:
                solid = solid + m3.Manifold.cylinder(pad - ring + 0.01, R - 0.3, R - 0.3, n).translate((x, 0, t - 0.01))
            rr = min(PAD_R, R - 0.6)
            solid = solid + m3.Manifold.cylinder(pad + 0.01, rr, rr, n).translate((x, 0, t - 0.01))
    for x in (0.0, P):
        solid = solid - m3.Manifold.cylinder(t + max(st.pad_c, st.pad_p) + 2, HOLE / 2, HOLE / 2, 32).translate((x, 0, -1))
    return solid


COUPON_GAUGE = 40.0


def coupon(mat_name):
    """Calibration coupon: 40 mm gauge, eyes for M4 bolts with the same eye/gauge section ratio as the straps."""
    w, t = (4.0, 1.2) if mat_name == "tpu95a" else (6.0, 2.0)
    R = HOLE / 2 + EYE_RATIO * w / 2            # two ligaments of w * EYE_RATIO / 2 each
    st = Strap(0, "C", mat_name, 1, 1, 0, 0, 0, 0, t=t, w=w, R_eye=R, pad_c=0.0, pad_p=0.0)
    st.P_print = COUPON_GAUGE + 2 * R
    return st


def to_stl(man, path):
    import trimesh
    mesh = man.simplify(0.005).to_mesh()
    tm = trimesh.Trimesh(vertices=np.asarray(mesh.vert_properties)[:, :3], faces=np.asarray(mesh.tri_verts), process=False)
    path.parent.mkdir(parents=True, exist_ok=True)
    tm.export(path)
    return tm


# ----------------------------------------------------------------- schedule
def face(c, st):
    """Which face of a lateral ear the single strap lies on."""
    ax = anchors(c, st.joint, st.side)[2] * st.sgn
    return "top (dorsal)" if ax[2] > 0 else "bottom (ventral)"


def write_table(c, straps, mats, calib):
    rows, bolts = [], {}
    for s in straps:
        for L in (s.bolt_c, s.bolt_p):
            bolts[L] = bolts.get(L, 0) + 1
        where = "pair, both faces" if s.count == 2 else f"1, {face(c, s)} face"
        rows.append(f"| J{s.joint} {dict(L='left', R='right', D='dorsal')[s.side]} | `{s.material}/{s.name}.stl` | {where} | "
                    f"{s.P_print:.1f} | {s.span:.1f} | {s.w:.1f} × {s.t:.1f} | {s.pad_c:.1f} / {s.pad_p:.1f} | "
                    f"{s.T0_pair:.1f} ({s.T0_target:.1f}) | {s.k_pair:.2f} ({s.k_target:.2f}) | "
                    f"{s.T_stop_pair:.0f} ({s.T_stop_spring:.0f}) | {s.eps * 100:.0f} % | {s.breakin_len:.0f} | "
                    f"M4×{s.bolt_c} / M4×{s.bolt_p} |")
    n95 = sum(s.count for s in straps if s.material == "tpu95a")
    n65 = sum(s.count for s in straps if s.material == "tpu65a")
    src = f"calibrated from `{calib}`" if calib else "NOMINAL material curves (run the coupon test and --calib)"
    mat_lines = "\n".join(f"- `{m.name}`: {m.kind}, E0 {m.E0:.1f} MPa" + (f", s1 {m.s1:.1f}, E2 {m.E2:.1f}" if m.kind == 'tanh' else "")
                          + f", set after break-in {m.set_frac * 100:.0f} %, max rest strain {m.eps_max * 100:.0f} %"
                          for m in mats.values())
    txt = f"""# TPU strap schedule: Barney tail (replaces the 18 extension springs)

Generated by `cad/tpu_bands.py` ({src}). STLs in `cad/stl/barney_tpu_bands/`.
Print {n65} straps in TPU 65A and {n95} in TPU 95A (a dorsal "pair" = print the file twice).

Lengths are pin-centre to pin-centre (mm). Forces are for the whole spring position (both straps of a pair);
the spring targets are in brackets. "Break-in" is the pin-to-pin length to stretch each strap to, 10 times,
before installing.

| spring | file | straps | printed length | installed span | gauge w × t | spacer child / parent | T0 at rest, N | k, N/mm | T at stop, N | rest strain | break-in | bolts child / parent |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
""" + "\n".join(rows) + f"""

Bolts (M4 socket head + washer each side + nylock): {", ".join(f"{n} × M4×{L}" for L, n in sorted(bolts.items()))}.

Material curves used:
{mat_lines}
"""
    (ROOT / "docs" / "tables" / "tpu_bands.md").write_text(txt)


# ----------------------------------------------------------------- main
def load_springs():
    from experiments.barney import configs
    from tailsim.sim import TailSim
    return TailSim(configs()["as_built"], settle=False).spring


def materials(calib_path):
    mats = {k: Material(**asdict(v)) for k, v in MATERIALS.items()}
    if calib_path:
        cal = json.loads(Path(calib_path).read_text())
        for name, data in cal.items():
            mats[name] = fit_material(mats[name], data)
    return mats


def fit_material(base, data):
    """Fit the material curve to a coupon test.

    data = {"width": mm, "thickness": mm, "points": [[load_kg, pin_to_pin_mm], ...]}, measured after break-in,
    the first point at 0 kg. The coupon model is the strap model (gauge + two eyes at EYE_RATIO)."""
    from scipy.optimize import least_squares
    cp = coupon(base.name)
    A = data["width"] * data["thickness"]
    R = cp.R_eye
    pts = sorted(data["points"])
    L0 = pts[0][1]
    Lg0 = L0 - 2 * R
    set_frac = max(0.0, (L0 - cp.P_print) / COUPON_GAUGE)

    def make(x):
        if base.kind == "neo":
            return Material(base.name, "neo", E0=x[0], set_frac=set_frac, eps_max=base.eps_max)
        return Material(base.name, "tanh", *x, set_frac=set_frac, eps_max=base.eps_max)

    def res(x):
        mm = make(x)
        out = []
        for kg, L in pts[1:]:
            sg = kg * 9.81 / A
            out.append(Lg0 * (1 + mm.strain(sg)) + 2 * R * (1 + mm.strain(sg / EYE_RATIO)) - L)
        return out
    if base.kind == "neo":
        r = least_squares(res, [base.E0], bounds=([0.3], [100]))
    else:
        r = least_squares(res, [base.E0, base.s1, base.E2], bounds=([2, 0.5, 0], [200, 50, 50]))
    return make(r.x)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--calib", help="coupon test JSON (see docs/tpu_bands.md)")
    ap.add_argument("--all", choices=list(MATERIALS), help="force one material for every strap")
    ap.add_argument("--no-stl", action="store_true")
    args = ap.parse_args()
    c = g.CadParams(**json.loads((ROOT / "cad" / "variants" / "barney.json").read_text()))
    springs = load_springs()
    mats = materials(args.calib)
    s95 = design(c, springs, mats, lambda i, s: "tpu95a")
    s65 = design(c, springs, mats, lambda i, s: "tpu65a")
    pick = {k: args.all for k in default_choice(s95, s65)} if args.all else default_choice(s95, s65)
    straps = design(c, springs, mats, lambda i, s: pick[(i, s)])
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "straps.json").write_text(json.dumps(dict(
        materials={k: asdict(v) for k, v in mats.items()},
        straps=[dict(asdict(s), name=s.name) for s in straps],
        alt_all_95a=[dict(asdict(s), name=s.name) for s in s95],
        alt_all_65a=[dict(asdict(s), name=s.name) for s in s65]), indent=1))
    for s in straps:
        print(f"{s.name:10s} {s.material} P={s.span:5.1f} print={s.P_print:5.1f} free={s.P_free:5.1f} eps={s.eps:4.2f} "
              f"w={s.w:4.1f} t={s.t:3.1f} R={s.R_eye:3.1f} pads {s.pad_c}/{s.pad_p} k {s.k_pair:4.2f}/{s.k_target:4.2f} "
              f"T0 {s.T0_pair:5.1f}/{s.T0_target:5.1f} Tstop {s.T_stop_pair:5.1f}/{s.T_stop_spring:5.1f} "
              f"bolts {s.bolt_c}/{s.bolt_p}{' CAPPED' if s.capped else ''}")
    write_table(c, straps, mats, args.calib)
    if args.no_stl:
        return
    for s in straps:
        to_stl(strap_mesh(s), OUT / s.material / f"{s.name}.stl")
        if s.side == "D":
            to_stl(strap_mesh(s, tight=2.0), OUT / s.material / f"{s.name}_tight2mm.stl")
    if not args.all:          # single-filament fallback for the 95A straps (fit-checked as `--all tpu65a`)
        for s in s65:
            if pick[(s.joint, s.side)] != "tpu65a":
                to_stl(strap_mesh(s), OUT / "tpu65a" / f"alt_{s.name}_if_no_95a.stl")
    for mname in MATERIALS:
        to_stl(strap_mesh(coupon(mname)), OUT / "calibration" / f"coupon_{mname}.stl")
    if args.calib:            # calibrated straps change width / eyes / spacers: re-run the fit check
        from cad import check_tpu_bands
        check_tpu_bands.main()


if __name__ == "__main__":
    main()
