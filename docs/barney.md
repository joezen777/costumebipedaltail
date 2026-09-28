# Barney-style tail (client revision): the design to build

## Client brief (revision)

- **Length:** half the previous tail's length.
- **Shape:** a Barney-like tail, roughly an x³ profile. It sticks out a little at the back, goes down, then points
  back again.
- **Follow-up:** the end should stick out more, like a reverse sigmoid: start up, go down, then flatten out. The
  first S-curve ended ~35° nose-down, like a hill, because it only levelled off in the non-bending foam tip.
- **Mounting:** on a pharmacy lower-lumbar support belt, attached directly or hanging down from it.
- **Mechanics:** as approved in the Gojira variant (ball-and-socket chain, spring spine with cap-ear anchors, felt
  liners, cord, wedge-flange rest curve).
- **Scope:** this replaces both earlier variants, the life-size STLs and the 1:8 resin replica.

## Design

| Item | Value |
|---|---|
| Length | **0.90 m**: 0.75 m articulated (6 joints × 125 mm) + 0.15 m foam tip (half the 1.8 m Gojira tail) |
| Envelope | 190 mm at the root → 100 mm at vertebra 6 → 60 mm rounded foam tip (linear taper: fat, Barney-like) |
| Rest shape | **Reverse sigmoid** z = h − 0.35 m / (1 + e^−(x − 0.28 m)/0.05 m): leaves the back nearly level (root pitch 6.2°), dips at up to ~58° mid-tail, then flattens so the last vertebra and foam tip stick straight back. Wedge-flange rest bends +29.2°, +22.7°, -3.7°, -30.6°, -20.9° |
| Mount | Plate on the lumbar belt's back panel; the tail pivot **hangs 70 mm below the plate centre** (pivot 30 mm below the pelvis centre). One printed part does both "attach directly" and "hang down" |
| Belt attachment | Four 5 × 28 mm slots for 25 mm hook-and-loop straps around the belt's back panel, plus top and bottom 50 mm webbing slots. Add a 3 mm EVA pad behind the plate for comfort on the curved lower back |
| Mechanics | As approved: ball-and-socket + dorsal/left/right extension springs on cap ears + felt liners + 5–10 N cord + roll key |
| Tuning for the short tail | Spring dead band 6° (softer centring springs; a short tail is livelier). Round cap stop openings (pitch travel = yaw travel) so the tail's own weight can't hammer the stops on a jump landing. Minimum ball radius 22 mm for neck strength |

## Simulated behaviour

As built: the moving masses are measured from the exported STLs plus hardware, foam and skin, and the springs are
sized for them.

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

Figures:
- `results/figures/barney_*.png`: hip snap, turn, jump, bend over, walking.
- `barney_hip_snap_waterfall.png`: the swing travelling root → tip.

Data: `results/data/barney.json`.

### Why these three tuning changes (found in simulation, not guessed)

1. **Softer centring springs (dead band 3.5° → 6°).** The half-length tail has fewer, lighter segments, so with the
   Gojira spring rule it overshot the hips by ~31° with two swing-backs. At 6° it overshoots
   10° with one swing-back.
2. **Round stop openings.** On a 25 cm jump landing (~2.4 g) the short, stubby tail bottomed out on its pitch stops
   at every joint, putting 11–23 N·m through the ball necks. Matching pitch travel to yaw travel cut the stop torque
   from 23 to 7 N·m.
3. **Minimum ball radius 17 → 22 mm.** This brings every neck to SF ≥ 3.5 against the simulated loads; the sharper reverse-sigmoid bends load joint 5 hardest.

The comparison of mechanisms on the hover profile (rigid gate hinges, elastic tube, stop-held chains; see
[gojira.md](gojira.md)) still applies. The spring-spine ball chain is the only one that is both compliant and
self-centring.

## Build files

| What | Where |
|---|---|
| Print-ready STLs (26 parts, 1.80 kg PETG) | `cad/stl/barney/`; list in [tables/barney_parts.md](tables/barney_parts.md) |
| OpenSCAD (generated variant of the parametric model) | `cad/openscad/suit_tail_barney.scad` |
| FreeCAD + STEP | `cad/freecad/output/suit_tail_barney.FCStd`, `.step` |
| Springs / strength / mass | [tables/barney_springs.md](tables/barney_springs.md), [tables/barney_strength.md](tables/barney_strength.md), [tables/barney_mass_budget.md](tables/barney_mass_budget.md) |
| 1:8 snap-together resin kit | `cad/stl/replica_1to8_resin/` (README there) |
| 1:8 protogen figurine with the adjustable-height plate slot | `cad/stl/figurine_1to8_resin/` (README there) |
| CAD renders, pose renders, photos | `results/cad_renders_barney/`, `results/pose_renders/`, `results/simulated_photos/` |

The whole tail is only 6 joints, so it *is* the prototype. There is no separate 4-joint test section; run the
measurements in [test_plan.md](test_plan.md) on the complete tail.
