# Mechanical design

Completely passive tail for a 5 ft 8 in (1.727 m) performer. Nothing is powered. The performer's pelvis drives the
root, and springs, friction, gravity and inertia do the rest. Numbers here come from `cad/geometry.py` (the single
dimensional spec) and the physics results in `results/`. `docs/physics.md` explains why each element exists.

## Architecture

```text
 harness plate ── hip mount ──(ball 1)── V1 ──(ball 2)── V2 ── … ── V8 ── tip adapter ── 200 mm foam tip
                   │  arms                 │ fins              │ fins
                   └── 3 springs ──► cap-1 ears    └── 3 springs ──► cap-2 ears   …
 central 6 mm cord: stopper knot in a Ø22 mm pocket on the hip mount's front face → through every ball centre → tip compression spring
```

- **8 ball-and-socket joints** at 150 mm pitch: 1200 mm articulated, plus a 200 mm flexible foam tip = 1400 mm.
- **Taper:** envelope D(u) = 70 + 120(1 − u)^1.3 mm (190 → 70 mm). The frame (skin former) sits inside a foam
  skin 20 → 4 mm thick.
- **Ball** (on the parent) radius = 0.15 D, clamped 17–28 mm. The **socket seat** is part of the next vertebra's
  frame; the **bolted cap** captures the ball. This is the README's "two-piece bolted socket".
- **Angular stops** are an elliptical cone cut in the cap mouth: yaw limit × pitch limit (pitch = 0.7 × yaw),
  progressive 8° → 28°, with a 0.8 mm felt/rubber pad.
- **Roll key:** a screw whose head is captured inside the ball protrudes 3 mm from the dorsal pole into a
  meridional slot shared by seat and cap. The slot is long in pitch, the screw spins freely about its own axis in
  yaw, and the slot width limits roll to ±7°.
- **Spring spine:** three extension springs per joint (dorsal + left + right).
  - Parent end: a hole 4 mm from the distal fin edge of the previous vertebra (or a hip-mount arm).
  - Child end: an **ear on the socket cap, 5 mm proximal of the pivot**.
  - The dorsal spring carries the tail's weight moment; the lateral pair gives the yaw centring that makes the tail
    swing back.
- **Central cord** through every ball centre. It preloads the seats, sets joint friction and holds the chain
  together if a part fails. It is **not** a bending element: at the ball centres its length does not change with
  bending.
- **Frame:** socket housing + spine tube + four longitudinal fins (dorsal, ventral, left, right) with 45° diamond
  windows, a mid-length skin ring and a distal base ring.

### Why the child spring anchor is on the cap (twist stability)

A tensioned spring whose two anchors straddle a ball joint has a geometric stiffness in the yaw–roll plane of
roughly

    K_yaw,roll ≈ (T/ℓ) · [ (a_c² − a_p·a_c)  −a_c·w ;  −a_c·w  w² ]

Here T is the spring tension, ℓ its length, w its radial offset, and a_p and a_c the axial positions of the parent
and child anchors (distances measured distally from the pivot, so the parent anchor sits at −a_p).

- The determinant is −a_p·a_c·w² (T/ℓ)². If the child anchor is **distal** of the pivot (a_c > 0), the matrix is
  indefinite: a saddle. When roll is free, the heavily preloaded dorsal spring (up to 150 N at the root) then acts
  as a **negative** yaw spring of −T·a_p·a_c/ℓ.
- This showed up in the linearised model as a negative-frequency twist mode, and in the time domain as the tail
  slowly corkscrewing away from centre after a hip snap. That's the README's "uncontrolled twisting".
- Moving the child anchor 5 mm *proximal* of the pivot (a_c < 0, on the cap) flips the sign. The same springs then
  centre the joint, and the lowest mode became stable with no extra hardware.
- `docs/physics.md` has the numbers; the spring design routine keeps a linear-stability guard.

## Performer fit (5 ft 8 in)

| Quantity | Value |
|---|---|
| Pelvis (sacrum) height | 0.55 × 1727 ≈ 950 mm |
| Harness plate | 120–128 mm behind the pelvis centre, 190 × 150 mm, M6 slots on a 150 × 100 mm pattern + one 50 mm webbing slot, hex lightening holes |
| Joint 1 centre | 200 mm behind the pelvis centre |
| Root pitch | tail leaves the hip 15° nose-down, then droops 1.5° per joint |
| Rest tip height | ≈ 0.4 m above the floor (`results/data/study_metrics.json`, `min_tip_height`) |
| Tail length / stature | 1400 / 1727 = 0.81 (classic suitmation proportion) |

The load path is harness plate → hip mount → ball 1. No load goes into the costume foam. At rest the harness
carries about 25 N and a ~10 N·m pitch moment. It should be a rigid hip plate or backpack frame with a waist belt,
not soft foam.

## Parts per vertebra

| Printed | Hardware |
|---|---|
| `body_i` (frame + seat), `cap_i`, `ball_(i+1)` left/right halves (tip adapter for i = 8) | 8 × M4 × 16 + nylocks, 1 roll-key screw, 3 springs, felt liner |

A backstage repair of a broken ball or cap is: remove 4 cap bolts, unhook 3 springs, slack the cord at the tip,
swap the part. No glue is structural.

## Strength

`docs/tables/strength.md` (generated from the as-built simulation of every standard motion) gives:

| Element | Worst case | Capacity | Safety factor |
|---|---|---|---|
| Ball necks (hollow PETG tubes, cord bore Ø8, layers along the axis in the clamshell halves) | J1: 6.4 N·m = peak ball moment 4.4 N·m + 59 N lateral × neck length | 42.8 N·m at 20 MPa | ≥ 4.9 on every joint |
| Cap ears (10 mm PETG, out-of-plane load) | J1 dorsal spring: 218 N peak → 15 MPa | 45 MPa UTS | 3.0 |
| Fin anchor holes | Bossed to fin + 4 mm | — | — |
| Axial seat compression | ≤ 281 N → < 1 MPa on the neck | — | negligible |

Not covered by simulation: someone stepping on the tail, or a hard wall strike. Those are what drop tests 7–8 in
`docs/test_plan.md` are for. If the J1 ear or a root neck cracks there:
- print the J1–J3 ball halves and caps at 100 % infill (already recommended), or
- split the J1 dorsal spring into two springs on two ears.
