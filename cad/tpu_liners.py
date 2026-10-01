"""TPU 95A felt substitutes for the Barney tail, plus a sheet of TPU M4 washers. 0.4 mm nozzle, 0.25 / 0.2 mm layers.

    PYTHONPATH=. python cad/tpu_liners.py

1. Seat liner web (one per joint): replaces the 0.5 mm felt in the socket seat (the spherical seat inside each
   vertebra body, pole on the joint axis, cord bore at the pole). It prints FLAT and folds onto the sphere.
   - Orange-peel construction: a hub ring round the cord bore, plus N_GORES petals. Petal k covers longitude
     phi_k +- pi/N. A sphere point (theta from the pole, phi) is printed at flat polar radius r = R*theta, angle
     psi = phi_k + (phi - phi_k) * sin(theta)/theta.
   - Each latitude strand is printed at its true length R*sin(theta)*dphi, and each petal's centre meridian at
     its true length R*dtheta. Pressed into the seat, the petal edges close up: the latitude strands join into
     whole circles and the meridians run pole to rim. The remaining stretch (off-centre meridians) is reported
     and is a few %, which TPU takes up.
   - The dorsal seam stays open over the roll-key slot.
   Seat friction with a TPU liner was simulated (docs/tables/tpu_band_sim.md): better than felt.
2. Cap-mouth bumper ring (one per joint): replaces the 0.8 mm felt stop pad. A flat split ring glued to the
   cap's outer face. Its bore is a cone opening at the joint's stop angle, so the neck lands flat on the whole TPU
   face at exactly the design limit, and the ring reaches 0.8 mm inside the PETG rim (PETG never touches PETG).
3. TPU M4 washers: snug on the thread (3.7 mm bore), 0.8 mm thick (the strap bolt stacks assume 0.8 mm
   washers). Enough for every M4 bolt in the build plus 10 % spares, on one sheet.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from cad import geometry as g  # noqa: E402
from cad.tpu_bands import to_stl, plate  # noqa: E402

OUT = ROOT / "cad" / "stl" / "barney_tpu_liners"
N_GORES = 12
LINER_T = 0.5         # = CadParams.liner (2 x 0.25 mm layers)
STRAND = 0.9          # strand width: two 0.45 mm lines
CELL = 3.5            # target strand spacing on the sphere (mm)
HUB_W = 2.0           # hub ring width (mm of arc)
RING_T = 1.6          # bumper ring thickness (8 x 0.2 mm)
RING_SLIT = 0.4
WASHER = dict(id=3.7, od=9.0, t=0.8)


def cfg():
    return g.CadParams(**json.loads((ROOT / "cad" / "variants" / "barney.json").read_text()))


# ----------------------------------------------------------------- seat liner
def slot_keepout(c, i, R):
    """Roll-key slot in the seat: |y| < w/2 round the dorsal (+z) point, up to angle a from +z in the x-z plane."""
    w = g.slot_width(c, i) + 1.2
    p = g.pin_spec(c, i)
    a = math.radians(g.pitch_lim(c, i) + math.degrees(math.asin((p[0] / 2 + 0.5) / g.RB(c, i))) + 2 + 3)

    def blocked(th, ph):
        x, y, z = R * math.cos(th), R * math.sin(th) * math.cos(ph), R * math.sin(th) * math.sin(ph)
        return z > 0 and abs(y) < w / 2 + STRAND / 2 and math.atan2(x, z) < a
    return blocked


def liner_paths(c, i):
    """Strand centre-lines as lists of (theta, phi, gore) samples; plus the geometry constants."""
    R = g.RS(c, i) - LINER_T / 2
    th_in = math.asin((g.bore_r(c) + 0.6) / R)
    th_hub = th_in + HUB_W / R
    th_rim = math.pi / 2 - (STRAND / 2) / R
    dphi = 2 * math.pi / N_GORES
    blocked = slot_keepout(c, i, R)
    paths = []
    for k in range(N_GORES):
        pk = math.pi / 2 + (k + 0.5) * dphi          # gore centres; the dorsal (+z) meridian is a seam
        edge = dphi / 2
        # meridians: centre, quarter lines (start where they are >= 2.5 mm from the centre line) and the two edges
        for m in (-2, -1, 0, 1, 2):
            frac = m / 2
            th0 = th_hub
            if abs(m) == 1:
                th0 = max(th_hub, math.asin(min(1.0, 2.5 / (R * edge / 2))))
            ths = np.linspace(th0, th_rim, 60)

            def ph_of(th):
                ph = pk + frac * edge
                if abs(m) == 2:          # edge strands sit half a strand inside the gore (they meet at the seam)
                    ph -= math.copysign((STRAND / 2) / (R * math.sin(th)), frac)
                return ph
            paths.append([(t, ph_of(t), k) for t in ths])
        # latitude strands
        n = max(2, int((th_rim - th_hub) * R / CELL))
        for th in np.linspace(th_hub, th_rim, n + 1)[1:]:
            half = edge - (STRAND / 2) / (R * math.sin(th))
            phs = np.linspace(pk - half, pk + half, 40)
            paths.append([(th, ph, k) for ph in phs])
    # split paths where they enter the roll-key slot keep-out
    out = []
    for pth in paths:
        cur = []
        for s in pth:
            if blocked(s[0], s[1]):
                if len(cur) > 1:
                    out.append(cur)
                cur = []
            else:
                cur.append(s)
        if len(cur) > 1:
            out.append(cur)
    return R, th_in, th_hub, dphi, out


def to_flat(R, dphi, th, ph, k):
    pk = math.pi / 2 + (k + 0.5) * dphi
    r = R * th
    psi = pk + (ph - pk) * math.sin(th) / th
    return r * math.cos(psi), r * math.sin(psi)


def to_sphere(R, th, ph):
    return np.array([R * math.cos(th), R * math.sin(th) * math.cos(ph), R * math.sin(th) * math.sin(ph)])


def liner_strain(c, i):
    """Largest length change (fraction) of any strand segment between the flat print and the fitted sphere."""
    R, th_in, th_hub, dphi, paths = liner_paths(c, i)
    worst = 0.0
    for pth in paths:
        for a, b in zip(pth[:-1], pth[1:]):
            f = np.hypot(*np.subtract(to_flat(R, dphi, *a), to_flat(R, dphi, *b)))
            s = np.linalg.norm(to_sphere(R, a[0], a[1]) - to_sphere(R, b[0], b[1]))
            if s > 0.2:
                worst = max(worst, abs(f / s - 1))
    return worst


def liner_mesh(c, i):
    import manifold3d as m3
    from shapely.geometry import LineString, Point
    from shapely.ops import unary_union
    R, th_in, th_hub, dphi, paths = liner_paths(c, i)
    geoms = [LineString([to_flat(R, dphi, *s) for s in pth]).buffer(STRAND / 2, quad_segs=4) for pth in paths]
    hub = Point(0, 0).buffer(R * th_hub, quad_segs=32).difference(Point(0, 0).buffer(R * th_in, quad_segs=32))
    shape = unary_union(geoms + [hub]).simplify(0.02)
    # one piece: drop strand stubs the roll-key slot cut loose from the web
    parts = sorted(getattr(shape, "geoms", [shape]), key=lambda q: -q.area)
    polys = []
    for poly in parts[:1]:
        polys.append(np.asarray(poly.exterior.coords)[:-1])
        polys += [np.asarray(r.coords)[:-1] for r in poly.interiors]
    cs = m3.CrossSection(polys, m3.FillRule.EvenOdd)
    return m3.Manifold.extrude(cs, LINER_T)


# ----------------------------------------------------------------- cap-mouth bumper ring
# The neck is not a plain cylinder: past the cap mouth the rest-bend wedge turns it onto the parent axis, so the
# PETG neck-to-cap contact angle depends on the bend direction (measured below from the meshes). The ring bore is
# therefore cut from the real neck: the union of the ball's sections through the ring, swept over every bend
# direction up to that direction's ring-stop angle = min(design limit, PETG contact - PETG_MARGIN).
PETG_MARGIN = 1.5     # deg: the TPU lands at least this much before PETG anywhere PETG would hit
N_DIR = 48


def _rdir(ang, phi):
    """Child rotation for a bend of `ang` deg toward azimuth phi (0 = +y yaw, 90 = pitch up / dorsal)."""
    ax = np.array([0, -math.sin(math.radians(phi)), math.cos(math.radians(phi))])
    a = math.radians(ang)
    K = np.array([[0, -ax[2], ax[1]], [ax[2], 0, -ax[0]], [-ax[1], ax[0], 0]])
    return np.eye(3) + math.sin(a) * K + (1 - math.cos(a)) * K @ K


def petg_contact(c, i, balls, caps, phis):
    """First PETG cap/neck contact angle per direction (deg), or None if none within the limit + 8 deg."""
    from cad.check_tpu_bands import H, overlap
    lim, out = g.yaw_lim(c, i), []
    for phi in phis:
        lo, hi = 0.0, lim + 8
        if overlap([m.copy().apply_transform(H(_rdir(hi, phi))) for m in caps], balls) < 0.05:
            out.append(None)
            continue
        for _ in range(8):
            mid = (lo + hi) / 2
            v = overlap([m.copy().apply_transform(H(_rdir(mid, phi))) for m in caps], balls)
            lo, hi = (mid, hi) if v < 0.05 else (lo, mid)
        out.append(round(lo, 2))
    return out


def ring_stops(c, i, balls, caps):
    """Ring-stop angle per direction (N_DIR directions) and the measured PETG contact at 8 directions."""
    lim = g.yaw_lim(c, i)
    phis8 = list(range(0, 360, 45))
    petg = petg_contact(c, i, balls, caps, phis8)
    big = lim + 8
    p8 = np.array([big if v is None else v for v in petg] + [big if petg[0] is None else petg[0]])
    phis = np.arange(N_DIR) * 360 / N_DIR
    p = np.interp(phis, phis8 + [360], p8)
    stops = np.minimum(lim, p - PETG_MARGIN)
    return phis, stops, petg


def neck_sweep(c, i, balls, phis, stops, z):
    """Union (shapely, ring print coords) of the ball's sections at ring height z, swept to each stop."""
    from shapely.geometry import Polygon
    from shapely.ops import unary_union
    x = -g.cap_h(c, i) - z
    pieces = []
    for phi, st in zip(phis, stops):
        for f in (0.0, 0.5, 1.0):
            Rt = _rdir(f * st, phi).T                      # ball seen from the bent child = ball rotated by R^T
            for b in balls:
                M = np.eye(4)
                M[:3, :3] = Rt
                sec = b.copy().apply_transform(M).section(plane_origin=[x, 0, 0], plane_normal=[1, 0, 0])
                if sec is None:
                    continue
                for poly in sec.discrete:
                    q = np.asarray(poly)
                    if len(q) >= 3:
                        pieces.append(Polygon(np.c_[-q[:, 1], q[:, 2]]).buffer(0))
    return unary_union(pieces)


def ring_dims(c, i):
    lim = math.radians(g.yaw_lim(c, i))
    RN, h = g.RN(c, i), g.cap_h(c, i)
    rho_bot = (RN + h * math.sin(lim)) / math.cos(lim)  # straight-neck bore (J1, no wedge) for reference
    return dict(rho_bot=rho_bot, r_out=g.cap_outer_r(c, i) - 4.5, overlap=g.mouth_r(c, i) - rho_bot,
                slot_r=g.RS(c, i) - 1.0, slot_w=g.slot_width(c, i) + 1.0)


def ring_mesh(c, i, balls, caps):
    """Printed cap-face side down: 4 slabs, each = annulus - neck sweep (+0.1 mm) through that slab.
    Dorsal notch (+Y) clears the roll-key slot; a slit at ventral lets it open round the neck."""
    import manifold3d as m3
    from shapely.geometry import Point, box
    d = ring_dims(c, i)
    phis, stops, petg = ring_stops(c, i, balls, caps)

    def annulus(k):
        # each slab's outer wall, notch and slit step in by 0.02 mm so no wall is shared between slabs
        # (coincident walls leave 4-face edges in the STL)
        e = 0.02 * k
        a = Point(0, 0).buffer(d["r_out"] - e, quad_segs=48)
        a = a.difference(box(-d["slot_w"] / 2 - e, d["slot_r"] - e, d["slot_w"] / 2 + e, d["r_out"] + 1))
        return a.difference(box(-RING_SLIT / 2 - e, -d["r_out"] - 1, RING_SLIT / 2 + e, 0))
    # (Where the wedge neck leans away from the cap face, J5/J6 pitching down, nothing on the cap face reaches it;
    # a taller ring that is still printable without supports does not reach it either.)
    T = RING_T
    n_slab = max(4, round(T / 0.4))
    dz = T / n_slab
    solid = None
    for k in range(n_slab):
        sweep = neck_sweep(c, i, balls, phis, stops, k * dz).union(neck_sweep(c, i, balls, phis, stops, (k + 1) * dz))
        shape = annulus(k).difference(sweep.buffer(0.1 + 0.02 * k))
        if k > 0:                         # printable: each layer stands on the one below (<= 45 deg overhang)
            shape = shape.intersection(prev.buffer(dz))
        shape = shape.buffer(-0.08, join_style="mitre").buffer(0.08, join_style="mitre").simplify(0.02)   # no pinches
        keep = [q for q in getattr(shape, "geoms", [shape]) if q.area >= 2.0 and (k == 0 or q.intersects(prev))]
        if not keep:
            break
        from shapely.ops import unary_union
        shape = unary_union(keep)
        prev = shape
        polys = []
        for poly in getattr(shape, "geoms", [shape]):
            polys.append(np.asarray(poly.exterior.coords)[:-1])
            polys += [np.asarray(r.coords)[:-1] for r in poly.interiors]
        slab = m3.Manifold.extrude(m3.CrossSection(polys, m3.FillRule.EvenOdd), dz + (0.01 if k < n_slab - 1 else 0))
        slab = slab.translate((0, 0, k * dz))
        solid = slab if solid is None else solid + slab
    return solid, dict(stops8=[float(stops[int(j * N_DIR / 8)]) for j in range(8)], petg8=petg, ring_t=T)


# ----------------------------------------------------------------- washers
def washer_counts(c):
    n = c.joint_count
    straps = json.loads((ROOT / "cad" / "stl" / "barney_tpu_bands" / "straps.json").read_text())["straps"]
    cap = 4 * n                 # cap bolts (head side)
    flange = 4 * n              # ball-flange bolts (head side)
    strap = 2 * 2 * len(straps)  # two bolts per strap position, a washer each side
    total = cap + flange + strap
    return dict(cap=cap, flange=flange, strap=strap, total=total, with_spares=math.ceil(total * 1.1))


def washer_mesh(n=48):
    import manifold3d as m3
    w = WASHER
    return (m3.Manifold.cylinder(w["t"], w["od"] / 2, w["od"] / 2, n)
            - m3.Manifold.cylinder(w["t"] + 2, w["id"] / 2, w["id"] / 2, 32).translate((0, 0, -1)))


# ----------------------------------------------------------------- main
def main():
    import shutil
    c = cfg()
    shutil.rmtree(OUT, ignore_errors=True)
    OUT.mkdir(parents=True)
    from cad.check_tpu_bands import parts_in_joint_frame
    rows, liners, rings = [], [], []
    for i in range(1, c.joint_count + 1):
        parent, child = parts_in_joint_frame(c, i)
        lm = liner_mesh(c, i)
        rm, stop_info = ring_mesh(c, i, parent[1:], child[:2])
        to_stl(lm, OUT / "seat_liners" / f"seat_liner_J{i}.stl")
        to_stl(rm, OUT / "mouth_rings" / f"mouth_ring_J{i}.stl")
        liners.append((lm, 1))
        rings.append((rm, 1))
        d = ring_dims(c, i)
        b = lm.bounding_box()
        rows.append(dict(joint=i, seat_R=g.RS(c, i), liner_flat_d=b[3] - b[0], liner_strain=liner_strain(c, i),
                         **{k: round(v, 2) for k, v in d.items()}, stop_deg=g.yaw_lim(c, i), **stop_info))
        print(f"J{i}: design stop {g.yaw_lim(c, i)} deg; PETG contact at 0..315 deg: {stop_info['petg8']}; "
              f"ring stop: {[round(v, 1) for v in stop_info['stops8']]}", flush=True)
    counts = washer_counts(c)
    names = []
    for name, items in (("seat_liners", liners), ("mouth_rings", rings),
                        ("washers_M4", [(washer_mesh(), counts["with_spares"])])):
        plates = plate(items, gap=3.0 if name != "washers_M4" else 2.0)
        for k, pl in enumerate(plates):
            man = pl[0]
            for m in pl[1:]:
                man = man + m
            qty = f"_{counts['with_spares']}x" if name == "washers_M4" else ""
            fname = f"plate_{name}{qty}{'' if len(plates) == 1 else f'_part{k + 1}of{len(plates)}'}_print1x.stl"
            to_stl(man, OUT / fname)
            names.append((fname, len(pl)))
    (OUT / "liners.json").write_text(json.dumps(dict(rows=rows, washers=counts, plates=names), indent=1))
    print(counts, names)


if __name__ == "__main__":
    main()
