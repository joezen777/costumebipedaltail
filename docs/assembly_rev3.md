# Assembly revision 3: one-piece balls, keyed caps, snap latches

What prompted it (from trying the build):
- **No room for a screwdriver.** The ball-flange bolt heads sit 15.5–18.5 mm from the neck axis, directly under
  a ball of radius 22–28 mm. No key can reach them from outside.
- **Split caps felt weak.** Each half is held only by its two bolts.
- **Nothing holds the parts** together while you drive the bolts.

The bodies and the hip mount are **unchanged**; only the balls and caps are reprinted, plus small new parts. All
checks run on the exported meshes in each joint frame: `PYTHONPATH=. python cad/check_assembly_rev3.py`.

## What changed

| Part | Before | Now |
|---|---|---|
| Ball | clamshell halves + dowels; roll-key screw head trapped inside | **one piece** (`ball_N.stl`), printed flange-down; **access holes** (7.8 mm) straight up through the ball over each reachable flange bolt: drop the bolt in, drive it with a long hex key |
| Roll key | M4 × 12 socket screw, head inside the ball | **M4 × 12 set screw** (grub screw) in a tapped 3.4 mm hole at the dorsal pole, 3 mm proud; or an M4 × 16 with the head cut off |
| Cap | two halves held only by their bolts | two halves locked across both seams by **bowtie (double-dovetail) keys** (`cap_key_N_v`/`_d`, one per seam), pushed into seam pockets |
| Cap ↔ body | bolts only | **lobe clips** (`lobe_clip.stl`, 4 per joint; 2 on J6) snap over each cap-bolt lobe and the body lobe behind it |
| Ball ↔ parent body | 4 bolts | **flange clips** (`flange_clip_N.stl`, 2 per joint, J2–J6) snap over both flange rims; reachable bolts; **J2, J3, J5, J6: flange faces bonded** (see below) |

## Why some bolts are glued instead

On the rest-bent joints, the ball's neck turns toward the parent axis just above the flange, so it sits right over
the two bolts on the outside of the bend:
- J2 and J3: the dorsal pair.
- J5 and J6: the ventral pair.

On the meshes:
- **From above:** a straight shaft for those bolts would cut 70–260 mm³ out of the neck, starting 2–5 mm above
  the flange, where the neck carries its largest bending moment.
- **From below:** inside the parent body there are only 15–25 mm of straight room behind the flange, where a bolt
  plus a hex key's short arm needs about 35 mm.
- **Moving the bolts:** that would mean reprinting the bodies.

So on those four joints:
- The two reachable bolts go in through the access holes.
- The **flange faces are bonded** with epoxy (or CA on roughened faces).
- The two flange clips sit over the glued side to hold it while it cures.

A bonded flange face (about 1000 mm²) is much stronger than the four bolts it replaces. The trade-off is that
those four joints are **permanent**: replacing a broken ball there means replacing its parent body too.

J1 and J4 keep all four bolts (all reachable) and stay removable.

| Joint | Bolts through access holes | Bonded |
|---|---|---|
| J1 | 4 (45°, 135°, 225°, 315°) | no |
| J2 | 2 (135°, 225°: ventral) | yes, dorsal side unbolted |
| J3 | 2 (135°, 225°) | yes |
| J4 | 4 | no |
| J5 | 2 (45°, 315°: dorsal) | yes, ventral side unbolted |
| J6 | 2 (45°, 315°) | yes |

Azimuth 0° is dorsal, measured round the flange axis.

## Why bowtie keys instead of a sliding dovetail rail

A rail dovetail along the seam engages only by sliding one half the full rail length along the joint axis. Neither
half can do that:
- **Toward the body:** the ball is in the way. A half moved distally cannot go round the ball, because the cap
  mouth is smaller than the ball.
- **Toward the flange:** there are only 7–12 mm before the ball flange.

A bowtie key needs no sliding of the halves:
1. Close the halves round the neck as before.
2. Slide the cap onto the body.
3. Push one key into each seam. Keys go in from the mouth face, except the dorsal-side key on J4–J6, which goes in
   from the body-side face before step 2.

The key's dovetail flanks carry the seam-opening load as **shear on glueable faces** in two planes. A drop of CA on
each key makes the cap effectively one piece. The TPU bumper ring, glued over the mouth face, then covers the key
ends.

## Checks (on the exported meshes)

| Check | Result |
|---|---|
| One-piece ball removes no material outside the ball sphere (the neck and wedge are untouched) | 0.00 mm³ removed on all 6 balls |
| Every listed access hole is a clear 7.2 mm shaft from the bolt seat up and out of the ball | all 16 shafts clear (0.00 mm³) |
| ≥ 0.8 mm of cap material round every key pocket (no break-through into the cavity, roll-key slot, ears or lobes) | all 12 pockets; at most 1.1 mm³ of wall thinner than 0.8 mm (J4–J6 body-face pockets) |
| Keys go straight in from the mouth face without touching anything | all 12 keys clear (0.00 mm³), with the key held 2 mm beyond its own length |
| Lobe clips: grip only their lobes, push on radially, clear of the ball, parent and TPU straps | 22 clips: 2.7 mm³ snap grip each, 0.00 elsewhere and on the push-on path; J6 uses only its 2 ventral lobes (the TPU strap nuts at the cap ear sit beside the dorsal ones) |
| Flange clips: grip only the two flanges, push on radially, clear of the cap, body and TPU straps | 10 clips: 2.2 mm³ clamp each, 0.00 elsewhere and on the push-on path |

## Printing

| Part | Material, nozzle | Orientation and settings |
|---|---|---|
| `ball_N` | PETG, 1.2 mm | flange face down, as exported. **Turn supports on** (tree supports, "everywhere") for the ball's underside round the neck. 0.4 mm layers, **8 walls** (so the neck is solid perimeters) + 20 % infill, hot and slow for layer bonding |
| `cap_N_a`, `cap_N_b` | PETG, 1.2 mm | as before (body-side face down, no supports); key pockets open upward |
| `cap_key_N_v`, `cap_key_N_d` (1 each per joint) | PETG, 0.4 mm nozzle preferred (1.2 works) | as exported, standing on the bowtie profile; tight fit (0.15 mm per side). `_v` goes in the ventral-side seam from the mouth face. `_d` goes in the dorsal-side seam: from the mouth face on J1–J3, but from the **body-side face** on J4–J6 (fit it before the cap slides onto the body; there the roll-key slot and the spring ear crowd the mouth face) |
| `lobe_clip` (×22) | PETG | as exported (C profile on the bed); 4 per cap, but only the 2 ventral lobes on J6 |
| `flange_clip_N` (×2 each, J2–J6) | PETG | as exported (U profile on the bed) |

- **Supports:** the scars land on the ball's cap-side half, never on the seat side the cord preload bears on.
  - The rest-bent balls stand tilted up to 30° on their wedge flange, so on one side the supported band reaches
    into the cap's contact band.
  - The cap only bears when the ball is pulled outward. Still, sand the scars smooth, so the cap and the TPU mouth
    ring slide cleanly.
- **Neck strength, printed upright:** the layers now run across the neck instead of along it. Taking PETG's
  layer-to-layer strength as about 60 % of in-plane, the neck safety factors drop from 3.3–4.6 to roughly
  **about 2.0–2.8** (J5 lowest, about 2.0), in the worst simulated move (jump included). These are estimates. Print the
  balls with 8 walls, so the neck is solid, and check the necks after the drop tests.
- **Weight:** 8 walls make the balls nearly solid, adding 17–54 g each (about 190 g in all) over the mass model.
  - Simulated with the TPU straps, the tail rests 1.1 cm lower (50.8 cm instead of 51.9 cm of floor clearance).
  - The hip snap, jump and hip moment are unchanged.
  - If a joint sags, the `+` tight spare straps take it back up.

## Hardware changes

- **Ball-flange bolts:** 16 × M4 × 16 instead of 24.
- **Roll keys:** 6 × M4 × 12 set screws instead of 6 socket screws.
- **Adhesive:** 2-part epoxy (or CA) for the four bonded flanges and the cap keys.
- **No washers under ball-flange bolt heads:** a 9 mm TPU washer won't go down a 7.8 mm access hole.

## Assembly (per joint; J1 shown, the others follow the table)

1. **Roll key:** thread the set screw into the ball's dorsal tap hole until 3 mm stands proud.
2. **Ball → parent flange** (hip mount for J1, previous body's distal flange otherwise):
   - Line up the bolt holes with the roll key on top (dorsal).
   - **J2, J3, J5, J6:** spread epoxy on the flange faces first, then snap the two flange clips over both rims on
     the unbolted side.
   - Drop each bolt down its access hole, head up, and drive it with a long hex key through the same hole.
3. **Body:** fit the seat liner, then set the body on the ball with the roll key in the seat slot.
4. **Cap:**
   - Close the two halves round the neck about 5 mm back from the body.
   - **J4–J6:** hold the cap about 8 mm back and push `cap_key_N_d` into the dorsal-side seam pocket from the
     body-side face.
   - Slide the cap forward onto the body; the roll key enters the cap slot.
   - Push the remaining key(s) into the seam pockets from the mouth face: `_v` on every joint, plus `_d` on J1–J3.
     Add a drop of CA if you want them permanent.
5. **Latch and bolt the cap:**
   - Snap a lobe clip over each of the four cap-bolt lobes and the body lobe behind it.
   - Bolt the cap: 4 × M4 × 16 from the mouth side. The hex key's short arm fits; there are 29–120 mm of straight
     room behind every head.
6. **Mouth ring:** glue the TPU bumper ring onto the mouth face.
7. **Straps or springs.**

The FreeCAD/STEP model (`cad/freecad/output/`) has **not** been updated for this revision. The OpenSCAD model
and the STLs are the reference.
