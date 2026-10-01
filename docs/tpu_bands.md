# Printed TPU straps in place of the extension springs (Barney tail)

The 18 extension springs were delayed in shipping. This is a same-night stand-in: printed TPU straps, sized
against the spring schedule and bolted through the existing 4.5 mm spring holes. You don't need to reprint
anything already built.

- STLs: [`cad/stl/barney_tpu_bands/`](../cad/stl/barney_tpu_bands/). Schedule: [tables/tpu_bands.md](tables/tpu_bands.md).
- Generator: `cad/tpu_bands.py`. Fit check: `cad/check_tpu_bands.py`. Simulation: `experiments/tpu_band_sim.py` →
  [tables/tpu_band_sim.md](tables/tpu_band_sim.md).

![print sheet](../results/cad_renders_barney/tpu_straps_print_sheet.png)

## How a strap replaces a spring

- **Dorsal springs** become a **pair** of identical straps, one on each face of the cap ear and of the parent
  fin or hip-mount arm, with an M4 bolt through each hole.
  - The pull stays on the spring's line of action.
  - The two sides cancel, so there is no roll moment.
  - Each strap carries half of k and T0.
- **Lateral springs** become **one** strap, on the face of the ear that the line of action leans toward (the
  table says top or bottom).
  - The rest-bend wedges tilt the parent's lateral fin by up to 30° relative to the cap ear. The lateral line of
    action therefore crosses the ear plate.
  - A strap on the far face would have to wrap through the ear (the fit check found this).
  - The bolt takes the small offset moment.
- **Spacer pads** are printed on the inner face of each eye.
  - They hold the strap clear of the ear, which flares wider below the hole.
  - At the out-of-plane bend limit they also clear the ear's proximal corner.
  - They make the eye about twice as stiff as the gauge, so the stretch happens in the gauge.
- **Eye holes** are 4.4 mm and sit snug on an M4 bolt.

### Why the strain, not the material, sets the length

A strap has no initial tension. To give the spring's preload T0 *and* its rate k at the rest span P, a linear
strap must already be stretched by T0/k, so its free length is P − T0/k. That depends only on the spring
schedule, not on the material:

| spring | T0/k | rest span P | rest strain if linear |
|---|---|---|---|
| J1 dorsal | 16.3 mm | 38.2 mm | 74 % |
| J4 dorsal | 18.7 mm | 32.9 mm | 132 % |
| J5 dorsal | 10.5 mm | 29.0 mm | 57 % |
| others | 4–12 mm | 34–75 mm | 11–30 % |

So the material has to sit at large stretch all evening and still behave like a spring:
- **TPU 95A** has a stiff start and a yield-like knee at about 10–55 %, with large set and creep past the knee.
  - It can only match where it stays under about 25 %, with a section big enough to print.
  - With a 1.2 mm nozzle, the smallest printable strap (3 × 1.2 mm) is already 2–4× too stiff for every lateral
    spring and for most dorsals.
  - That rules out an all-95A set (`--all tpu95a` prints the numbers).
- **TPU 65A** is rubber-like.
  - In a neo-Hookean material σ/σ′ grows with stretch, so it behaves like "initial tension".
  - J1 dorsal needs about 70 % instead of 74 %, and it tolerates 50–80 % far better than 95A.
  - It also takes sections that are easy to print.
- **Result:** 22 straps in **65A**, plus the J2 dorsal pair in **95A**.
  - J2 dorsal is long (75 mm span), so it runs at only 17 % strain in a slim 6.7 × 1.2 mm strap.
  - The 65A alternative (`tpu65a/alt_band_J2D_if_no_95a.stl`) is bulkier (13 × 3.6 mm, M4 × 40) but also passes
    the fit check. Use it if you'd rather not change filament.
- **J4 dorsal** is the one strap that can't match both numbers. Its strain is capped at 80 %, T0 is still exact
  (so the rest pose is right), and k is 11 % high. That makes no visible difference in simulation.

## Results (nominal material curves)

| Check | Result |
|---|---|
| T0 at rest | equal to the spring target on all 18 positions |
| k | within 1 % on 17 positions; J4 dorsal +11 % |
| Force at the angular stop | 3–16 % below the springs (rubber softens), never above |
| Fit check: straps + spacers + washers + bolt heads + nylocks vs the printed meshes, at rest and at ±yaw, ±pitch limits | no overlap; the worst case is a 0.2 mm³ graze of a J3 dorsal strap on its ear corner at the full-yaw stop |
| Hip snap, 45° turn, walk, jump, crouch (MuJoCo, as built) | same as springs (overshoot 9°, settles in 1.25 s, tip/hip 1.95, crouch clearance 47 cm) |
| Material 30 % softer / stiffer than assumed (rest pose re-trimmed) | overshoot 2° / 15°, turn 25° / 37°, settle 1.51 / 1.19 s: both acceptable |

TPU hysteresis adds damping that the model leaves out, so the real tail should overshoot a little *less*.

## Material uncertainty and the coupon test

TPU brands differ by up to about 3× in modulus. The STLs in the repo use **nominal** curves:
- 95A: 22 MPa start, knee about 7 MPa.
- 65A: neo-Hookean, E = 4.5 MPa.

The rest-pose trim below absorbs a modest error. For forces within ±10 %, run the coupon test first (about
30 min):

1. **Print** `calibration/coupon_tpu65a.stl` (and `coupon_tpu95a.stl` if you use 95A) with the strap settings
   below. The gauge is 40 mm, the eyes take M4 bolts, and the printed pin-to-pin length is 60 mm.
2. **Break in:**
   - 65A: stretch it by hand 10 times to about 95 mm pin-to-pin.
   - 95A: 10 times to about 72 mm.
3. **Hang** it from an M4 bolt or a screwdriver shank, with a second bolt through the lower eye holding a bag.
4. **Measure the pin-to-pin length** (centre to centre, i.e. outside of the bolts minus 4 mm) with calipers:
   - with the empty bag, then
   - for 65A: 0.5, 1.0, 1.5 and 2.0 kg (water bottles; weigh them, bag included);
   - for 95A: 1, 2 and 3 kg.
   - Read each value after 30 s.
5. **Record** the readings, plus the coupon's actual width and thickness, in `cad/tpu_calibration.json`:
   ```json
   {"tpu65a": {"width": 6.1, "thickness": 2.0, "points": [[0, 61.2], [0.5, 65.0], [1.0, 69.3], [1.5, 74.0], [2.0, 79.4]]}}
   ```
   (The numbers are an example; the first point is the empty bag.)
6. **Regenerate**: `PYTHONPATH=. python cad/tpu_bands.py --calib cad/tpu_calibration.json`.
   - This rewrites the STLs and the schedule, then re-runs the fit check automatically.
   - Don't print if the check reports an overlap.

## Printing (Ender 3 V2, Sprite Pro, 1.2 mm nozzle)

| Setting | TPU 65A | TPU 95A |
|---|---|---|
| Layer height | 0.4 mm (strap thicknesses are multiples of it) | 0.4 mm |
| Line width | 1.3 mm | 1.3 mm |
| Speed | 10–15 mm/s | 20–25 mm/s |
| Nozzle / bed | spool's range (≈ 220–230 °C) / 40–50 °C | ≈ 225–235 °C / 50 °C |
| Retraction | off (or ≤ 0.5 mm, slow) | ≤ 1 mm, slow |
| Walls | **enough to make the whole strap perimeters** (8–10 walls) | same |
| Infill | 100 % (normally fully covered by the walls) | 100 % |
| Bed | glue stick on PEI as a release layer (TPU fuses to bare PEI) | same |
| Orientation | as exported: flat face on the bed, spacer pads up; no supports | same |

- **Walls:** all-perimeter straps put continuous lines along the gauge and around each eye. That is what makes
  the strap strong and repeatable, so don't let the slicer fill the gauge with crosswise infill.
- **What to print:** every dorsal file **twice** (one strap per face) and every lateral file once. That is 24
  straps, about 25 cm³ of 65A and 2 cm³ of 95A: roughly 1–1.5 h at these speeds.
- **Spares:** also print the `_tight2mm` dorsal variants (same strap, 2 mm shorter, +5–12 % preload) for
  trimming.

## Hardware

- M4 socket-head bolts at the lengths in the schedule: 12 × M4×25, 12 × M4×30, 11 × M4×35, 1 × M4×40.
- Plus 36 M4 nylock nuts and 72 M4 washers.
- Use the listed lengths. The fit check modelled one washer and a nylock on each end, and a longer bolt's tail
  isn't checked.

## Installing

1. **Break in every strap.** Stretch it 10 times to the "break-in" length in the schedule (pin-to-pin, by hand
   against a ruler). The first stretch takes out most of the set; installing straps without break-in loses
   preload in the first minutes of wear.
2. **Stack order on a bolt:**
   - Dorsal pair: head, washer, strap (pad facing the ear), ear, strap (pad facing the ear), washer, nylock.
   - Lateral single strap: head on the bare face, washer if it fits, ear, strap (pad facing the ear), washer,
     nylock. The strap goes on the face named in the schedule.
3. **Child (cap ear) end first, then the parent end.**
   - The heavy dorsal straps (J1 about 48 N each) need about 12 mm of stretch to reach the fin or arm hole.
   - Lift the tail so the joint sits pitched up against its stop; this shortens the dorsal span.
   - Pull the eye over with a screwdriver shaft through it, line it up with a 4 mm drill-bit shank, then push the
     bolt through as you withdraw the bit.
4. **Leave the eyes free to swivel.**
   - Tighten each nylock until the stack has no play, then back it off about ¼ turn.
   - The strap must pivot on the bolt as the joint bends. A clamped eye would force the strap to bend edgewise
     and add stiffness the simulation doesn't have.
5. **Trim the rest pose.**
   - Wear the belt at the design height, or hang the tail from the hip mount at the worn angle.
   - The tail should match the neutral render: the end level and sticking straight back, skin about 52 cm off the
     floor.
   - If a joint sags, swap that dorsal pair for its `_tight2mm` variant.
   - Laterals only need the left and right sides to look symmetric.

## Caveats

- **Creep:**
  - Pre-stretched TPU loses preload over hours: 65A a few %, 95A more.
  - Check the tip height between wearings and swap to the tight variants if it drops.
  - Keep the spare straps and a hex key in the costume kit.
- **Heat:** TPU softens noticeably above about 40 °C, for example in a closed car. Don't store the tail with the
  straps under tension in heat; unbolt the dorsal pairs' parent ends.
- **Stop loads:** forces at the angular stop are 3–16 % below the springs, so the strength margins in
  [tables/barney_strength.md](tables/barney_strength.md) still hold.
- **When the springs arrive:** use [tables/barney_springs.md](tables/barney_springs.md). Its "installed length"
  column was **corrected** in this change. It had listed the straight-line fin-to-ear distance; the rest-bend
  wedges tilt the parent fin, so the true dorsal spans on J2–J6 are 75, 62, 33, 29 and 34 mm. The simulation
  always used the true spans. If you ordered springs by the old column, check that each spring's force at the
  true span is T0, and trim with a cord loop on the hook as before.
