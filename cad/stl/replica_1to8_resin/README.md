# 1:8 scale resin replica: Gojira tail

This folder has everything needed to print a **static 1:8 display replica** of the recommended Gojira tail on the
Anycubic Photon Mono 5s (build volume 218 × 123 × 200 mm) in ABS-Like Pro 2 resin.

![preview](preview.png)

A scaled *working* tail isn't possible at 1:8. The M4 holes would be 0.56 mm, and the balls, springs and cord
couldn't be assembled. So each replica is **one solid piece** built from the real design:

| File | What it is | Size (mm) | Resin (solid) |
|---|---|---|---|
| `replica_mechanism_1to8.stl` | The actual print STLs of all 10 vertebrae, caps, ball halves, hip mount and tip adapter, assembled in the rest pose. The central cord and all 30 springs are modelled as solid rods, which join everything into one body. The foam tip is a solid cone. | 195.0 × 23.8 × 114.3 | 5.8 ml |
| `replica_skinned_1to8.stl` | The finished look: foam-skin envelope with dorsal plates and foam tip, plus the harness plate at the root | 202.9 × 23.8 × 120.0 | 40.2 ml |
| `replica_stand_1to8.stl` | Floor plate + post. Glue the replica's hip-mount (harness) plate flat against the post's rear face. The tail then hangs at the true 1:8 height, hovering ~1 cm above the base. | 193.8 × 37.5 × 129.4 | 47.1 ml |

Print one tail (mechanism **or** skinned) plus the stand. Every file is a single watertight body and fits the
printer (`report.json`).

## Print settings (Photon Mono 5s, ABS-Like Pro 2)

- **Layer height:** 0.03–0.05 mm.
- **Orientation:** put the long axis along the 218 mm X direction, standing roughly upright (root up), tilted
  about 30° so no large flat face meets the FEP. Use light–medium supports on the underside of the curve.
- **Mechanism replica:**
  - Print **solid**; don't hollow it, since its walls are already thin.
  - Smallest features: frame fins ≈ 0.34 mm, skin rings ≈ 0.35 mm, spring rods ≈ 0.6 mm diameter. That's fine for
    resin, but wash and remove supports gently and cure lightly (brittle when over-cured).
- **Skinned replica:** hollow it in the slicer (1.5 mm wall, two drain holes on the underside), which saves about
  two-thirds of the resin.
- **Stand:** large and flat. It prints fine in resin, but it's cheaper as a PETG FDM print.

Regenerate with `PYTHONPATH=. ~/.venvs/costumebipedaltail/bin/python cad/export_replica.py`.
It builds from `cad/stl/gojira/`, so it follows any design change.
