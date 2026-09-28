# Printing, materials and assembly

Everything here is for the proof-of-concept (POC) build. STL files in `cad/stl/full/` (full tail) and
`cad/stl/test_section/` (4-joint prototype) are **already in print orientation**. The flat face is on z = 0.
Part sizes, volumes and estimated masses are in `cad/stl/parts.json`.

## Printer and nozzle: Ender 3 V2 + Sprite Pro, 1.2 mm nozzle

The whole geometry is dimensioned around a 1.2 mm nozzle:

| Setting | Value | Why |
|---|---|---|
| Extrusion width | 1.3 mm | Every wall, fin and rib in the CAD is a whole number of lines (`line_w = 1.3`) |
| Layer height | 0.6 mm frames, caps and hip mount; 0.4 mm ball halves | 50 % of the nozzle; finer layers make the ball's bearing band smoother |
| Perimeters | 3 (= 3.9 mm) | Socket walls are 5 lines (6.5 mm) so the roll-key slot keeps a 2.5 mm back wall |
| Infill | 20 % gyroid; **100 % for ball halves of joints 1–3** | The root necks carry the highest bending moment (see docs/design.md) |
| Top/bottom | 3 layers | |
| Nozzle / bed | PETG 240–250 °C / 80 °C, fan 30–50 % | Big nozzles need higher flow: keep volumetric flow ≤ ~25 mm³/s on the Sprite Pro |
| Speed | 25–35 mm/s outer wall | At 1.3 × 0.6 mm this is already 20–27 mm³/s |

Minimum feature sizes used in the design:

- Two-line fins (2.7 mm) on vertebrae 4–8, three-line fins (4.0 mm) on vertebrae 1–3.
- No wall thinner than two lines.
- Holes are modelled at clearance size (M4 → 4.5 mm). With a 1.2 mm nozzle, small horizontal holes come out
  undersize and slightly oval, so **drill them to size**: 4.5 mm for M4, 3.4 mm for M3, 4.5 mm for spring holes.
- Ball-to-socket running clearance is 0.4 mm radial, plus a 0.5 mm allowance for the PTFE tape or thin felt seat
  liner. This is sized for the ±0.3 mm dimensional scatter typical of 0.6 mm layers.
- Nut pockets are M4 hex, 7.0 mm across flats + 0.4 mm. The nylock nut presses in.
- Every overhang is ≤ 45° by design, except three spots:
  - The underside of the ball neck (inside the ball halves; not printed as an overhang because the halves lie flat).
  - Cap mouths on joints 6–8, where the elliptical stop cone reaches 51–59° over a few millimetres. Print these
    slowly; supports are not needed.
  - 7 mm hex bridges over the cap-bolt nut pockets.

## Orientation per part (no supports needed)

| Part | Orientation (as exported) | Notes |
|---|---|---|
| `body_i` (vertebra frame) | Distal flange on the bed, socket bowl facing up | The bowl prints as an open cup; fins are vertical plates with 45° diamond windows; the skin ring has a 45° skirt |
| `cap_i` | Equator face (bolt lobes, spring ears) on the bed | Inner sphere becomes a 45° relief cone above 45° latitude, so there is no ceiling |
| `ball_i_left/right` | Clamshell halves, split face on the bed | Layers run **along** the neck, so neck bending loads the layers in-plane (strong). The dorsal hole captures the roll-key screw head. Align with two 1.75 mm filament dowels and glue with CA/epoxy (optional; the socket and flange bolts already trap the halves) |
| `hip_mount` | Harness-plate face on the bed, boss up | Arms are vertical plates |
| `tip_adapter` | Flange on the bed | Foam spike and barbs are cones |
| `test_ballast_plate` | Flange on the bed | Only for the 4-joint test section |

All parts fit a 200 mm cube; the largest is `hip_mount` at 151 × 190 × 58 mm (`parts.json` gives every bounding box).

## Material choice

### Recommended: PETG for all structural parts, TPU only as optional bumpers

- **PETG** bonds well between layers with a 1.2 mm nozzle (thick, hot lines), is tough rather than brittle, and
  its glass transition (~80 °C) survives a hot costume and a car boot. A lightly-filled PETG frame is lighter than
  a solid resin part of the same shape.
- **PLA** is stiffer but brittle in impact and creeps near 50–55 °C (a sun-baked suit). Fine for a first dry-fit
  of the 4-joint section; not for performance use.
- **TPU 95A** is optional: a 1.2 mm cap-mouth pad (in place of the adhesive felt pad, `stop_pad = 0.8 mm`) or
  sleeve bumpers. The physics model already treats the stops as soft (12 ms time constant).

### Resin (Anycubic Photon Mono 5s, ABS-Like Pro 2): advice

I checked resin against the physics numbers rather than dismissing it.

1. **Build volume.** The Mono 5s's short axis is ~123 mm. Vertebra frames 1–2 are 150 and 133 mm across and do not
   fit. Resin could only ever make balls, caps and the distal frames.
2. **Mass.** Resin parts are solid unless hollowed (~1.1–1.2 g/cm³ solid, against ~0.6–1.0 g/cm³ effective for
   20 % PETG). The simulation is most sensitive to distal mass, and the distal segments are already over the
   README budget (docs/physics.md, "mass budget"), so solid resin would make that worse.
3. **Toughness.** ABS-like resins are much tougher than standard resin but still far below PETG in notched impact.
   The largest loads come from stop impacts and floor strikes. These land on the ball necks and cap lips, which is
   exactly where a brittle failure would release a joint (the cord still holds the chain together).
4. **Where resin *would* help:** sphericity and surface finish of the ball, which lowers and evens out the
   friction. The model shows that friction consistency matters more than its absolute value (the springs are
   sized from friction).

**Verdict: not recommended for structural parts.** The physics would allow resin *ball halves for joints 4–8
only*, hollowed with 2 mm walls and a drain hole in the split face, for a smoother bearing, provided they pass the
drop test in the 4-joint procedure. PETG balls wet-sanded to 400 grit, with PTFE tape in the seat, give most of
the same benefit at no risk. That is the default.

## Hardware (per full 8-joint tail)

| Item | Qty | Use |
|---|---|---|
| M4 × 16 socket-head cap screw + M4 nylock | 32 + 32 | Cap bolts (4 per joint) |
| M4 × 16 socket-head cap screw + M4 nylock | 28 + 28 | Ball flange → vertebra distal flange / hip mount (4 per joint) |
| M4 × 12 socket-head (roll key), joints 1–4 | 4 | Head captured inside the ball; protrudes 3 mm into the socket slot |
| M3 × 8 socket-head (roll key), joints 5–8 | 4 | |
| M3 × 8 screws | 4 | Tip adapter to vertebra 8 |
| M6 bolts / 50 mm webbing | 4 / 2 slots | Hip mount to the harness (150 × 100 mm pattern) |
| Extension springs | 3 per joint (24) | Dorsal + left + right; see `docs/tables/springs.md` |
| 6 mm braided polyester cord | ~1.6 m | Central cord, knotted in the hip-mount pocket |
| Compression spring Ø ≤ 13 mm, ~2 N/mm, 20 mm long | 1 | Cord preload at the tip adapter (compress ~5 mm for 10 N) |
| PTFE tape 0.25 mm or 0.5 mm self-adhesive felt | — | Seat liner (the friction level the physics was tuned for is MEDIUM ≈ felt, μ ≈ 0.25) |
| Adhesive felt/rubber 0.8 mm | — | Cap-mouth stop pad |
| 1.75 mm filament | 16 × 10 mm | Ball-half dowels |

## Assembly

1. Drill all holes to size. Press M4 nylocks into the body pockets (cap lobes and distal flange).
2. Put the roll-key screw in one ball half (head in the pocket, shank out through the dorsal hole). Close the
   second half on the dowels; glue if wanted.
3. Bolt the ball's flange to the previous vertebra's distal flange (joint 1: the hip mount), bolt heads on the neck side.
4. Line the seat with PTFE tape or felt. Put the ball in the seat with the roll-key screw in the dorsal slot. Put
   the cap over the neck with its slot also dorsal, and bolt it with 4 × M4 × 16.
5. Hook the three springs of each joint: parent fin hole (or hip-mount arm) → cap ear of the child.
   Dorsal = the stiff, strongly preloaded one.
6. Thread the cord from the tip adapter through every bore to the hip-mount pocket and knot it there. At the tip,
   add washer + compression spring + washer + cord lock, and compress the spring to the preload
   (10 N ≈ 5 mm at 2 N/mm).
7. Slide on the foam skin (upholstery foam, 20 mm at the root tapering to 4 mm) and glue it to the rings and fin
   edges. Glue the 200 mm foam tip over the tip-adapter spike.
