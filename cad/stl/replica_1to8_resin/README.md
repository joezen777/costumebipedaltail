# 1:8 scale snap-together resin replica: Barney tail

A working miniature of the approved mechanism, printed on the Anycubic Photon Mono 5s in ABS-Like Pro 2. It's scaled
1:8 from the full-size Barney tail (0.9 m becomes ~11 cm):
- **Joints:** each vertebra **clicks** into the next with a ball-and-socket snap joint. The socket cup has three
  flex slits.
- **Cord:** twine threads through the centre bore, standing in for the braided cord.
- **Springs:** orthodontic (dental brace) elastics hook over mushroom pegs.
- **Rest curve:** the S-curve is built into the kinked necks, as the full-size wedge flanges build it in.

![assembled preview](preview.png)

## Print list (one of each)

| File | Size (mm) | Resin (ml) |
|---|---|---|
| `00_snap_test_coupon.stl` | 23.4x20.0x8.9 | 0.465 |
| `01_hip_mount_plate.stl` | 16.1x23.8x26.4 | 1.139 |
| `99_display_stand.stl` | 147.5x36.0x135.7 | 30.114 |
| `11_vertebra_1.stl` | 20.1x18.8x19.8 | 0.578 |
| `12_vertebra_2.stl` | 19.6x17.1x18.2 | 0.502 |
| `13_vertebra_3.stl` | 18.9x15.7x16.0 | 0.426 |
| `14_vertebra_4.stl` | 18.8x14.3x14.4 | 0.38 |
| `15_vertebra_5.stl` | 19.1x13.4x14.7 | 0.351 |
| `16_vertebra_6.stl` | 37.9x12.8x12.8 | 1.91 |

- `00_snap_test_coupon`: a socket and ball for the largest and smallest joint. **Print it first** to check the snap.
- `01_hip_mount_plate`: the lumbar-belt plate with the joint-1 ball and its four pegs. Its tab pushes into the stand
  post.
- `11`–`16` `_vertebra_N`: one per joint, root to tip. Number 6 carries the rounded foam tip.
- `99_display_stand`: floor plate and post. It's also fine to print it on the FDM printer in PETG.

## Print settings

- **Layers:** 0.03–0.05 mm. Solid, no hollowing (the parts are small and thin-walled).
- **Orientation:** stand each vertebra on its socket end (cup facing down), tilted 20–30°, with light supports on the
  outside only. Keep supports out of the cup and off the ball.
- **Snap tuning:** the ball-to-socket radial clearance is 0.08 mm (`mclear` in `cad/openscad/mini_kit.scad`).
  - Balls won't click in: raise it to 0.10–0.12.
  - Joints are floppy: lower it to 0.05.
  - Then re-export: `PYTHONPATH=. ~/.venvs/costumebipedaltail/bin/python cad/export_replica.py`.
- **Post-processing:** wash and cure gently. Over-cured ABS-like resin cracks at the cup slits.

## Assembly

1. **Thread the twine.** Use 0.8–1.0 mm waxed polyester or cotton twine (bores are Ø1.3 mm), about 30 cm.
   - Knot it at the top exit of the hip-mount boss.
   - Thread it through the ball of joint 1, each vertebra in order, and out of the tie-off hole under vertebra 6.
   - Leave it slack for now.
2. **Click the joints together.** Press each ball into the next vertebra's cup, going root to tip; the three slits
   let the cup open. Check that each joint swivels freely.
3. **Fit the elastics.** Each joint takes four orthodontic elastics (dorsal, ventral, left, right): **24 in total,
   plus spares**.
   - Each band hooks over a peg on the parent vertebra and the matching peg on the child's socket ear.
   - Peg-to-peg spans per joint (mm): J1 4.9, J2 5.6, J3 5.3, J4 4.5, J5 4.7, J6 5.5.
   - **1/8" (3.2 mm) medium-force orthodontic elastics** stretch to that length with light tension. Use 3/16" light
     elastics if 1/8" pull the joints stiff.
   - All four bands on a joint must be the same size, so the tail sits in its designed S-curve.
4. **Tension the twine.** Pull it snug and tie it off under vertebra 6. It holds the balls seated, just like the
   full-size cord.
5. **Mount it.** Push the hip-plate tab into the stand post. Swing the tail and let go: the elastics centre it, as the
   springs do on the full-size tail.

At this scale gravity is negligible next to the elastics' pull. That's why the kit uses four balanced bands per joint
instead of the full-size three (dorsal + left + right, where the dorsal spring also carries the tail's weight).

## Shopping list for the kit

| Item | Qty |
|---|---|
| ABS-Like Pro 2 resin | ~40 ml (tail + hip plate ~6 ml; the stand is ~30 ml, or print it in PETG) |
| Orthodontic elastics 1/8" medium (and a few 3/16" light) | 1 pack of 100 |
| Waxed twine 0.8–1.0 mm | 30 cm |
