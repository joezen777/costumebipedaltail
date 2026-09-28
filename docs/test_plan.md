# 4-joint physical test section (README section 21)

**Build:** hip mount + vertebrae 1–4 (with caps, balls 1–4 and their springs) + `test_ballast_plate` on
vertebra 4's distal flange. STLs are collected in `cad/stl/test_section/`; the assembly is in
`cad/freecad/output/test_section_4joint.step`. Articulated length is 600 mm, using the full-scale root joints.

**Ballast:** vertebrae 5–8 and the foam tip are replaced by an M8 threaded rod through the ballast plate, carrying
steel washers:
- total **625 g**, with the washer stack centred **~290 mm beyond the joint-5 ball centre**;
- this gives the same distal mass and first moment of mass, so joints 1–4 see full-tail static loads;
- the simulated response with and without ballast is in `results/figures/test_section_hip_snap.png` and
  `results/data/test_section_metrics.json`.

## Simulated predictions for the test section (compare against the filmed hip snap)

| 30° hip snap in 0.35 s | Lag | Overshoot | Swing-backs | Settling | 45° turn overshoot | Walk tip/hip ratio |
|---|---|---|---|---|---|---|
| 4 joints + 625 g ballast rod | 32.1° | 11.9° | 1 | 1.2 s | 35.5° | 1.88 |
| 4 joints, no ballast | 27.9° | 27.3° | 1 | 0.8 s | 29.6° | 1.34 |
| Full 8-joint tail, as built (for reference) | 38.6° | 10.3° | 1 | 1.9 s | 28.7° | 1.61 |

With ballast, the test section reproduces the full tail's character, so tuning the liner and springs on it
carries over.

## Measurements, and what each one calibrates in `tailsim`

| # | Test | Method | Model parameter | Pass criterion |
|---|---|---|---|---|
| 1 | Rest droop | Mount the hip plate on a rigid fixture; measure the vertebra-4 end height | Dorsal spring T0 per joint | Within ±15 mm of the model's rest pose |
| 2 | Breakaway torque per joint | Spring scale on the vertebra-4 end, pulled sideways slowly; record the force at first motion, with and without the cord | Seat μ (`mu`), `friction_radius_factor` | Within ±30 % of `μ·R·N` from the model; adjust `mu` |
| 3 | Yaw stiffness | Force vs lateral deflection at the V4 end (5 points, both directions) | Lateral spring k, preload margin | Slope within ±20 % of `stiffness_at_rest()` |
| 4 | Twist check | Twist V4 by hand ±5° about its axis and release | Twist-mode stability (cap-ear anchors) | Returns to centre; no slow corkscrew drift |
| 5 | Pluck test | Deflect V4 end 100 mm sideways, release, film at 120 fps from above | Viscous `visc` and μ | Number of visible swings and decay within ±1 swing of the simulation |
| 6 | Hip snap | Rotate the fixture 30° in ~0.35 s by hand against a stop; film from above | Whole model | Lag/overshoot trace matches `test_section` simulation shape |
| 7 | Stop impact | Drop test: release from full yaw against the stop 20 times | Stop pads, neck strength | No cracking; pads intact |
| 8 | Floor strike | Swing the V4 end into a padded floor 20 times | Neck + cap-lip strength | No cracking; cord keeps the chain intact |
| 9 | Worn-by-performer | Harness on the performer; walk, turn, crouch | Harness load path | No hot spots; tail clears legs and floor |

After tests 2–5, update the corresponding `TailParams` values and re-run `experiments/run_suite.py` before
printing vertebrae 5–8.
