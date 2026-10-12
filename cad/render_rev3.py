"""Preview sheet of the revision-3 parts (results/cad_renders_barney/rev3_parts.png).

    PYTHONPATH=. python cad/render_rev3.py
"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import trimesh  # noqa: E402
from matplotlib.collections import PolyCollection  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
STL = ROOT / "cad" / "stl" / "barney"
OUT = ROOT / "results" / "cad_renders_barney" / "rev3_parts.png"


def view(ax, f, title, axis=2, flip=False):
    m = trimesh.load(STL / f)
    n = m.face_normals[:, axis] * (-1 if flip else 1)
    keep = n > 0.05
    tri = m.triangles[keep]
    other = [k for k in range(3) if k != axis]
    h = tri[:, :, axis].mean(1) * (-1 if flip else 1)
    h = (h - h.min()) / np.ptp(h) if np.ptp(h) > 0.5 else np.ones_like(h)   # height-shaded: pockets read dark
    shade = (0.25 + 0.75 * h) * (0.6 + 0.4 * n[keep])
    cols = np.clip(np.outer(shade, matplotlib.colors.to_rgb("#e0b52c")), 0, 1)
    order = np.argsort(tri[:, :, axis].mean(1) * (-1 if flip else 1))
    ax.add_collection(PolyCollection(tri[order][:, :, other], facecolors=cols[order], edgecolors="none"))
    ax.set_aspect("equal")
    ax.autoscale()
    ax.set_title(title, fontsize=8)
    ax.tick_params(labelsize=6)


def main():
    fig, axs = plt.subplots(2, 4, figsize=(15, 8), dpi=120)
    view(axs[0, 0], "ball_1.stl", "ball_1 from above: 4 long-hex-key access holes\n(set-screw roll key at the dorsal pole)")
    view(axs[0, 1], "ball_2.stl", "ball_2 from above: 2 access holes\n(dorsal pair covered by the bent neck: bonded flange)")
    view(axs[0, 2], "ball_2.stl", "ball_2 side view (printed flange down)", axis=1)
    view(axs[0, 3], "cap_2_b.stl", "cap_2_b, mouth face up: bowtie key pockets\nat both seam ends", flip=False)
    view(axs[1, 0], "cap_5_a.stl", "cap_5_a, body-side face (bed side):\ndorsal-seam key pocket", flip=True)
    view(axs[1, 1], "cap_key_2_v.stl", "cap_key (double dovetail)\npush into the seam pocket")
    view(axs[1, 2], "lobe_clip.stl", "lobe_clip: snaps over the cap lobe\n+ body lobe (cap ↔ body latch)")
    view(axs[1, 3], "flange_clip_2.stl", "flange_clip_2: U over both flange rims\n(ball ↔ body latch)")
    fig.suptitle("Barney tail, revision 3: one-piece balls, keyed caps, snap latches")
    fig.savefig(OUT, bbox_inches="tight")
    print(OUT)


if __name__ == "__main__":
    main()
