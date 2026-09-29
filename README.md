# Passive suitmation tail: Barney-style, lumbar-belt mounted, ready to print

A completely passive (no motors, electronics or pneumatics) creature-suit tail for a **5 ft 8 in (1.727 m)**
performer. The client revision asked for:
- **half the length** of the earlier tail;
- a **Barney-like reverse-sigmoid curve**: starts up, goes down, then flattens so the end sticks straight back;
- a mount on a **pharmacy lower-lumbar support belt**;
- the **mechanics approved in the Gojira variant** kept.

It was validated in a MuJoCo physics model, then built as parametric OpenSCAD and FreeCAD models. The print-ready
parts are for an Ender 3 V2 / Sprite Pro with a **1.2 mm nozzle** (no part larger than a 20 cm cube), plus a
**1:8 snap-together resin kit** for the Photon Mono 5s, and a **1:8 low-poly figurine with a protogen head** whose
back slot takes the kit's plate at 14 heights.

- Design document: [docs/barney.md](docs/barney.md)
- Documentation index: [docs/README.md](docs/README.md)
- Original brief: [docs/brief.md](docs/brief.md)

![Barney tail CAD assembly on the performer](results/cad_renders_barney/side_neutral_with_actor.png)

---

## 1. The design

- **Length:** 0.90 m, a 6-joint × 125 mm ball-and-socket chain plus a 0.15 m rounded foam tip.
- **Proportions:** 190 mm thick at the root, 100 mm at vertebra 6, 60 mm at the tip.
- **Rest shape:** a reverse sigmoid, printed into wedge flanges on the balls. It leaves the back nearly level (6°),
  dips at up to 58° mid-tail, then the last vertebra and foam tip run level, sticking straight back.
- **Mount:** a plate strapped to the lumbar belt's back panel, with the tail root hanging 70 mm below it. One part
  covers both "attach directly" and "hang down".
- **Mechanics** (as approved):
  - dorsal + left + right extension springs per joint, anchored on cap ears (twist-stable);
  - felt seat liners;
  - a light central cord;
  - a roll-key screw per joint.

Simulated, with the masses measured from the exported parts:

| Test (as built) | Result |
|---|---|
| Rest (standing) | tail ends pointing back, skin **52 cm** above the floor |
| 30° hip snap | lag 34°, overshoot 10°, 1 swing-back, settles in 1.2 s |
| Jerk left (30° in 0.25 s) | lag 40°, overshoot 8° |
| 45° dramatic turn | overshoot 31° |
| Walking 1.5 / 2.0 steps/s | tip/hip 1.94 / 1.77 |
| Crouch (−150 mm, 10°) | min clearance 47 cm |
| Side step 300 mm | min clearance 50 cm |
| Bending over 45° | tail lifts; hip moment 7.0 N·m |
| Jump (25 cm) | no floor contact; hip moment 13.3 N·m |
| Peak moment on the lumbar belt (any test) | 13 N·m |

Levelling the end out (reverse sigmoid) also calmed the tail: walking sway dropped from ~2.4× to ~1.9× the hip,
and the snap overshoot from 17° to 10°. The end rides about half a metre off the floor.

Four changes made the short tail work, all found in simulation ([docs/barney.md](docs/barney.md)):
- **Reverse-sigmoid rest curve:** the first S-curve ended ~35° nose-down, like a hill, because it only flattened
  inside the foam tip, which can't bend. Now the last vertebra and tip are level and stick straight back.
- **Softer centring springs:** the tail first overshot the hips by 31°.
- **Round cap stop openings:** jump landings were hammering the pitch stops (23 → 7 N·m).
- **Bigger minimum ball (22 mm):** brings every neck to SF ≥ 3.5.

![Hip snap response](results/figures/barney_hip_snap_30.png)

## 2. What to print (full size)

**[`cad/stl/barney/`](cad/stl/barney/): 26 print-ready STLs, 1.80 kg of PETG.**
- One hip mount, 6 vertebra bodies, 6 caps, 12 ball halves (with the rest-curve wedges; keep them in joint order)
  and the tip adapter.
- Sizes and masses: [docs/tables/barney_parts.md](docs/tables/barney_parts.md).
- Settings: [docs/printing.md](docs/printing.md). PETG, 1.3 mm lines, 0.6 mm layers (0.4 mm for ball halves),
  100 % infill for ball halves 1–3.
- **No slicer supports:** the vertebra bodies and hip mount carry their own overhangs with thin structural walls
  (a 45° cone, an arched skirt, arm webs). Every part prints from `cad/stl/barney/` with slicer
  supports off; the few remaining roofs are short bridges. See [docs/printing.md](docs/printing.md).
  ![self-supporting parts](results/cad_renders_barney/print_orientation_self_supporting.png)
- The whole tail is only 6 joints, so it doubles as the prototype for the calibration tests in
  [docs/test_plan.md](docs/test_plan.md).

CAD: [`cad/openscad/suit_tail_barney.scad`](cad/openscad/suit_tail_barney.scad) (a generated variant of the
parametric [`suit_tail.scad`](cad/openscad/suit_tail.scad)); FreeCAD/STEP in [`cad/freecad/output/`](cad/freecad/output/). The FreeCAD/STEP hip mount and vertebra frames
predate the self-supporting redesign, so the STLs are authoritative.

### Shopping list (full-size tail)

Rough commodity prices in USD; buy about 10 % spare small hardware.

| Item | Qty | Use | ~Cost |
|---|---|---|---|
| PETG filament 1.75 mm | 2 × 1 kg | 1.80 kg of parts + purge | $40 |
| 1.2 mm nozzle for the Sprite Pro | 1 | | $10 |
| M4 × 16 socket-head cap screws | 48 | 4 per cap + 4 per ball flange, 6 joints | $6 |
| M4 nylock nuts | 48 | press into the printed hex pockets | $4 |
| M4 × 12 socket-head (roll keys, joints 1–4) / M3 × 8 (joints 5–6 + 4 for the tip adapter) | 4 / 6 | roll-key pins, tip adapter | $2 |
| **Extension springs** | **18** | 3 per joint; schedule in [docs/tables/barney_springs.md](docs/tables/barney_springs.md) | $20–35 |
| · heavy (dorsal J1–J2) | 2 | ~5.5–5.9 N/mm, 66–96 N at rest, up to ~145 N, OD ≤ 15 mm | |
| · medium (dorsal J3–J6) | 4 | ~1.6–3.3 N/mm, 9–41 N at rest, up to ~78 N, OD ≤ 12 mm | |
| · light (lateral pairs, all joints) | 12 | ~0.8–1.7 N/mm, 6–13 N at rest, up to ~33 N, OD 8–15 mm | |
| Compression spring Ø ≤ 13 mm, ~2 N/mm, ~20 mm long | 1 | cord preload at the tip | $2 |
| 6 mm braided polyester cord | 1.5 m | central cord | $4 |
| Cord lock + 2 washers | 1 set | tip end of the cord | $3 |
| Self-adhesive felt 0.5 mm; felt/rubber 0.8 mm | small sheets | seat liners; cap-mouth stop pads | $8 |
| **Lumbar support belt** (pharmacy lower-back brace, elastic with a rigid or semi-rigid back panel) | 1 | the mount | $20–35 |
| 25 mm hook-and-loop straps ~40 cm | 4 | through the plate's corner slots, around the belt's back panel | $8 |
| 50 mm webbing strap ~1 m + buckle (optional) | 1 | through the top slot for extra hold | $6 |
| EVA foam 3 mm | 200 × 160 mm | comfort pad behind the mounting plate | $3 |
| Upholstery foam (~20 mm and ~10 mm sheets) | ~1 m × 1 m | skin over the frame, 20 → 10 mm thick | $25 |
| Foam block | 150 × 100 × 100 mm | rounded 150 mm foam tip | $6 |
| 4-way stretch fabric + contact cement / spray adhesive | ~1 m² + 1 can | outer skin | $25 |
| 1.75 mm filament offcuts; CA or epoxy | 12 × 10 mm | ball-half dowels; glue | $5 |

Tools: 3.4 and 4.5 mm drill bits (to size printed holes), hex keys, 7 mm nut driver, pliers.
**Rough total ~$200–250 including the belt.**

## 3. 1:8 snap-together resin kit (Photon Mono 5s)

**[`cad/stl/replica_1to8_resin/`](cad/stl/replica_1to8_resin/)**: a working miniature of the mechanism, about 11 cm
long.
- **Joints:** each vertebra **clicks** into the next with a slotted snap-fit ball and socket.
- **Cord:** **twine** (0.8–1 mm) threads through the centre, like the cord.
- **Springs:** **orthodontic elastics** (1/8" medium) hook over mushroom pegs, 4 per joint (24 total).
- **Rest curve:** the reverse-sigmoid curve is built into the necks.
- **Also included:** the lumbar-belt plate with a tab, a display stand, and a snap test coupon to print first.

Print settings, assembly and the kit shopping list are in that folder's
[README](cad/stl/replica_1to8_resin/README.md).

![1:8 kit assembled](cad/stl/replica_1to8_resin/preview.png)

### 1:8 figurine with a protogen head

**[`cad/stl/figurine_1to8_resin/`](cad/stl/figurine_1to8_resin/)**: a low-poly 5 ft 8 in male at 1:8 with a
protogen head, for trying the kit at different heights.
- **Back slot:** a T-slot rail on the back takes the kit's hip plate unchanged. It slides in from the top.
- **Levels:** pins through the lip holes stop the plate at 14 levels, from 128 mm below to 288 mm above the design
  height (full-size).
- **Parts:** body, head, base and two level pins.

![figurine with the tail at three levels](cad/stl/figurine_1to8_resin/preview_levels_side.png)

## 4. The tail on a performer: five simulated poses

Every row is one instant of the as-built simulation, shown three ways:
1. **Photo:** a Z-Image Turbo image-to-image pass over the physics render, which keeps the simulated geometry.
2. **Physics render.**
3. **CAD render:** the real exported parts articulated with the simulated joint angles.

| Pose | Simulated photo | Physics render | CAD render |
|---|---|---|---|
| Standing still | ![](results/simulated_photos/1_standing__dn55_s0.png) | ![](results/pose_renders/1_standing.png) | ![](results/cad_renders_barney/1_standing.png) |
| Bending over | ![](results/simulated_photos/2_bending_over__dn55_s0.png) | ![](results/pose_renders/2_bending_over.png) | ![](results/cad_renders_barney/2_bending_over.png) |
| Turning (45°) | ![](results/simulated_photos/3_turning__dn55_s0.png) | ![](results/pose_renders/3_turning.png) | ![](results/cad_renders_barney/3_turning.png) |
| Jerk to the left | ![](results/simulated_photos/4_jerk_left__dn55_s0.png) | ![](results/pose_renders/4_jerk_left.png) | ![](results/cad_renders_barney/4_jerk_left.png) |
| Jump, just before landing | ![](results/simulated_photos/5_jump_before_landing__dn55_s0.png) | ![](results/pose_renders/5_jump_before_landing.png) | ![](results/cad_renders_barney/5_jump_before_landing.png) |

More CAD views in [`results/cad_renders_barney/`](results/cad_renders_barney/):
- top, moderate turn, maximum curvature with limit cones;
- cord path, exploded vertebra, joint sections, hip mount.

| Maximum curvature (limit cones) | Exploded vertebra | Hip mount / belt plate |
|---|---|---|
| ![](results/cad_renders_barney/top_max_curvature_limit_cones.png) | ![](results/cad_renders_barney/exploded_vertebra_2.png) | ![](results/cad_renders_barney/hip_mount.png) |

## 5. How the mechanism was established (design history)

The approved mechanics came from a physics study of the brief's original 1.4 m tail, followed by a 1.8 m
"Gojira" hover variant. Both variants' CAD, exports and renders were replaced by this revision; the findings and
plots remain.

| Finding | Evidence |
|---|---|
| Friction and stops alone can't swing back: **centring springs are required** | [naive vs spring spine](results/figures/study_naive_hip_snap.png), [animation](results/animations/naive_vs_reference_hip_snap.gif) |
| A preloaded spring anchored distal of the pivot causes a **twist instability**; anchoring the child end on the cap proximal of the pivot fixes it | [docs/physics.md §2.4](docs/physics.md), [docs/design.md](docs/design.md) |
| Springs must beat the friction dead band; the **seat liner is the main tuning knob**, cord preload hardly matters | [liner](results/figures/hardware_friction_hip_snap.png), [preload](results/figures/hardware_preload_hip_snap.png) |
| The **roll key** keeps swing energy from leaking into twist | [roll study](results/figures/hardware_com_roll_hip_snap.png), [animation](results/animations/roll_free_vs_roll_key.gif) |
| Configurations A–D on identical inputs | [comparison](results/figures/compare_ABCD_hip_snap_30.png), [docs/tables/study.md](docs/tables/study.md) |
| Rigid gate hinges are unsafe near the floor (860 N on a jump landing); an elastic tube can't hold a shape and swing | [docs/gojira.md](docs/gojira.md) |

Validation ([tests/test_physics.py](tests/test_physics.py), [tests/test_cad.py](tests/test_cad.py), all passing):
- **Physics:** statics; ball loads against hand calculations; energy conserved except for the stop constraints; the
  linear modes match the time-domain simulation; dt convergence; hip tracking; tension-only springs; the
  gravity-bias torque.
- **CAD:** OpenSCAD matches the Python spec (default and Barney variants); every Barney part is one watertight volume
  that fits the printer.

## Reproduce

```bash
python3 -m venv ~/.venvs/costumebipedaltail && ~/.venvs/costumebipedaltail/bin/pip install -r requirements.txt
PYTHONPATH=. ~/.venvs/costumebipedaltail/bin/python -m unittest -v tests.test_physics tests.test_cad
PYTHONPATH=. ~/.venvs/costumebipedaltail/bin/python cad/make_variant.py barney           # CAD variant from the design
cd cad && ~/.venvs/costumebipedaltail/bin/python export_stl.py --variant barney --no-kit && cd ..
PYTHONPATH=. ~/.venvs/costumebipedaltail/bin/python experiments/barney.py                # design + as-built simulation
PYTHONPATH=. ~/.venvs/costumebipedaltail/bin/python experiments/barney_tables.py         # springs / strength / mass tables
PYTHONPATH=. ~/.venvs/costumebipedaltail/bin/python cad/export_replica.py                # 1:8 resin kit
PYTHONPATH=. ~/.venvs/costumebipedaltail/bin/python cad/export_figurine.py               # 1:8 protogen figurine
TAIL_VARIANT=barney ~/Applications/freecad-experiment/squashfs-root/usr/bin/freecadcmd cad/freecad/build_tail.py
python3 cad/render_views.py --variant barney                                             # CAD views
MUJOCO_GL=egl PYTHONPATH=. ~/.venvs/costumebipedaltail/bin/python experiments/pose_renders.py
PYTHONPATH=. ~/.venvs/costumebipedaltail/bin/python experiments/cad_pose_renders.py
python3 experiments/photoreal.py                                                         # needs ComfyUI (~/comfyuiinstall.sh)
```
