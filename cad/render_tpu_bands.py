"""Top-view print sheets: TPU straps (tpu_straps_print_sheet.png) and the felt substitutes + washers
(tpu_liners_rings_washers.png) in results/cad_renders_barney/.

    PYTHONPATH=. python cad/render_tpu_bands.py
"""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import trimesh  # noqa: E402
from matplotlib.collections import PolyCollection  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
BANDS = ROOT / "cad" / "stl" / "barney_tpu_bands"
OUT = ROOT / "results" / "cad_renders_barney" / "tpu_straps_print_sheet.png"


def draw(ax, path, x0, y0, color):
    m = trimesh.load(path)
    up = m.face_normals[:, 2] > 0.5
    tris = m.triangles[up]
    z = tris[:, :, 2].mean(1)
    shade = 0.55 + 0.45 * z / max(z.max(), 1e-6)
    cols = np.clip(np.outer(shade, matplotlib.colors.to_rgb(color)), 0, 1)
    ax.add_collection(PolyCollection(tris[:, :, :2] + [x0, y0], facecolors=cols, edgecolors="none"))
    return m.extents


def main():
    straps = json.loads((BANDS / "straps.json").read_text())["straps"]
    fig, ax = plt.subplots(figsize=(11, 8.5), dpi=130)
    colors = {"tpu65a": "#2f7fbf", "tpu95a": "#d1495b"}
    colors = {k: v for k, v in colors.items() if any(s["material"] == k for s in straps)}
    x, y, row_h = 0.0, 0.0, 0.0
    for s in straps:
        f = BANDS / s["material"] / f"{s['name']}.stl"
        for k in range(s["count"]):
            if x > 200:
                x, y, row_h = 0.0, y - row_h - 14, 0.0
            ext = draw(ax, f, x + s["R_eye"], y, colors[s["material"]])
            label = f"J{s['joint']}{s['side']}" + (f" ({k + 1}/2)" if s["count"] == 2 else "")
            ax.text(x + ext[0] / 2, y - ext[1] / 2 - 4, f"{label}\n{s['P_print']:.1f} mm", ha="center", va="top", fontsize=7)
            x += ext[0] + 8
            row_h = max(row_h, ext[1] + 8)
    yb = y - row_h - 6
    for i, (name, c) in enumerate(colors.items()):
        ax.text(0, yb - 7 * i, f"■ {name.upper()}", color=c, fontsize=10, weight="bold", va="top")
    ax.text(60, yb, "Top view, as printed (outer face on the bed, spacer pads up). Length = printed pin-to-pin.\n"
            "Dorsal springs: print 2 of the same strap (one each side of the ear). Lateral springs: 1 strap.",
            fontsize=8, va="top")
    ax.set_aspect("equal")
    ax.autoscale()
    ax.axis("off")
    ax.set_title("Barney tail: TPU 95A straps replacing the 18 extension springs (0.4 mm nozzle; label tab = fin end)")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT, bbox_inches="tight")
    print(OUT)
    liners_sheet()


def liners_sheet():
    d = ROOT / "cad" / "stl" / "barney_tpu_liners"
    out = OUT.with_name("tpu_liners_rings_washers.png")
    fig, axs = plt.subplots(1, 3, figsize=(15, 5.6), dpi=130)
    for ax, (f, title) in zip(axs, ((d / "seat_liners" / "seat_liner_J1.stl", "Seat liner J1 (prints flat, 0.5 mm)\n"
                                     "petals close into true meridians + latitude circles"),
                                    (d / "mouth_rings" / "mouth_ring_J3.stl", "Cap-mouth bumper ring J3 (1.6 mm)\n"
                                     "bore = real neck swept to the stop; dorsal notch, ventral slit"),
                                    (next(d.glob("plate_washers_M4_*.stl")), "M4 tension washers (one sheet)"))):
        ext = draw(ax, f, 0, 0, "#d1495b")
        ax.set_aspect("equal")
        ax.autoscale()
        ax.set_title(title, fontsize=9)
        ax.tick_params(labelsize=7)
    fig.suptitle("Barney tail: TPU 95A felt substitutes and washers (0.4 mm nozzle)")
    fig.savefig(out, bbox_inches="tight")
    print(out)


if __name__ == "__main__":
    main()
