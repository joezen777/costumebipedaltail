# Gojira profile ("x² + 1"): which tail is cheapest and simplest?

**Target shape.**
- The tail leaves the hips pointing down, sweeps to a low point just *above* the floor (it hovers, never drags),
  and the tip curls slightly back up.
- Rest centreline follows z = c + a(x − x_v)² with c = 0.12 m, i.e. about 8–9 cm skin clearance at the low point.
- Solver: `tailsim/shape.py`.

**Length.**
- A 1.4 m tail can't make this curve from a 0.95 m hip. It would have to leave the hip at 68° and bend 27–45° per
  joint near the tip.
- The brief's long option works: **1.5 m articulated (10 joints × 150 mm) + 0.3 m foam tip = 1.8 m**.
  - The tail leaves the hip at 58°.
  - Every joint bend is ≤ 16°.
  - Heels clear the root at normal stride.

## Candidates (same shape, same masses, same hip inputs)

`experiments/gojira_compare.py`, `experiments/gojira_final.py`, and `results/data/gojira_final.json`:

| Mechanism | Snap lag (°) | Snap overshoot (°) | Swing-backs | Settle (s) | Turn overshoot (°) | Walk tip/hip (1.5 / 2.0 steps/s) | Rest clearance (cm) | Worst clearance: walk, turn, crouch (cm) | **Jump landing: floor force / hip moment** | Peak hip moment in snaps (N·m) |
|---|---|---|---|---|---|---|---|---|---|---|
| **Ball chain + spring spine** (this repo's design, reshaped) | 34.3 | 13.8 | 1 | 3.0 | 38.8 | 0.97 / 0.69 | 8.9 | −0.5 (foam brush, 0.8 N) | **20 N / 13 N·m** | 10 |
| Gate hinges, 60° tilt, damping grease | 25.3 | 16.5 | 2 | 3.1 | 22.6 | 1.25 / 0.67 | 9.0 | 5.8 | **861 N / 669 N·m** | 24 |
| Gate hinges, 45° tilt, damping grease | 28.8 | 18.9 | 2 | 4.8 | 26.6 | 1.08 / 0.65 | 9.0 | 5.8 | **842 N / 663 N·m** | 20 |
| Elastic spine (pre-cambered tube), 0.7 Hz | 32.4 | 0 | 1 | 0.0 | 0 | 3.26 / 0.57 | 9.0 | −3.4 (drags) | 46 N / 13 N·m | 11 |
| Elastic spine, 1.0 Hz | 32.6 | 0 | 1 | 1.4 | 22.6 | 1.01 / 1.89 | 9.0 | −2.9 (drags) | 46 N / 13 N·m | 11 |
| Ball chain resting on its pitch stops, lateral springs only | 33.1 | 0 | – | – | 0 | – | −0.2 (lies on floor) | – | – | – |
| Ball chain on pitch stops, no springs | 32.6 | 0 | – | – | 0 | – | −0.2 | – | – | – |

The jump is a counter-movement jump: the pelvis rises 25 cm, then drops 13 cm into a knee bend on landing.

### What each result means

- **Ball chain on its stops** (the cheapest articulated idea: no dorsal springs; the curve is set by stop angles).
  Stop friction freezes the yaw swing (it ends 29–38° off-centre) and the tail sags onto the floor. Rejected.
- **Gate hinges** (yaw-only hinge per joint, axis leaning back so gravity self-centres it like a self-closing gate;
  no springs, no cord, no roll key). This is the *cheapest and simplest* mechanism, and it swings well. It holds
  the curve rigidly, so clearance never changes.
  - **Rejected on safety:** being rigid in pitch, it cannot give when the tail meets the floor. A landing from a
    small jump drives the low point into the floor with **~860 N**, levering **~670 N·m** into the performer's
    pelvis. That is an injury-level load.
  - A stumble or fast crouch does the same.
  - Pitch compliance is not optional for a tail that hovers this close to the floor.
- **Elastic spine** (pre-cambered tube, e.g. twin stacked PEX, inside foam; no printed joints). Cheap and compliant.
  But with bending stiffness distributed along the length it cannot both hold the hover and swing freely: the low
  section brushes or drags, and floor friction kills the overshoot.
- **Ball chain + spring spine** is the only candidate that meets every requirement:
  - hovers at rest and in all tests (a 0.8 N foam brush in the most violent 45° turn only);
  - lags, overshoots and swings back once;
  - takes a jump landing gently (20 N, 13 N·m), because the dorsal springs let the tail ride up on contact.

## Recommendation: the optimal solution

**The ball-and-socket + spring-spine tail, reshaped to the Gojira profile**, with these simplifications (all
supported by the same-hardware study, `docs/tables/hardware.md`):

| Item | Decision | Why |
|---|---|---|
| Length / joints | 1.5 m, 10 joints at 150 mm, + 0.3 m foam tip | Needed to make the x² + 1 curve from a 0.95 m hip |
| Rest curve | Built into the parts: each ball flange printed on a **wedge** equal to that joint's rest bend (58° root, then −3 … −16° upward bends) | Springs then only carry weight about the designed curve, and stops stay centred |
| Springs | Keep dorsal + left/right per joint | Dorsal: holds the hover *and* is the pitch compliance that makes landings safe. Lateral: the swing-back |
| Spring anchors | Child end on cap ears, proximal of the pivot | Twist stability (docs/physics.md §2.4) |
| Seat liner | Felt (μ ≈ 0.25) | Main tuning knob; PTFE is too whippy |
| Central cord | Keep, but at only 5 N | Preload has almost no effect on motion; the cord is cheap retention insurance |
| COM ballast | Omit | Only a secondary effect |
| Roll key | Keep (one screw per joint) | Removing it halves the swing |

**Rough hardware cost** (commodity prices, excluding the foam skin):
- **Recommended ball chain:** ~$120–180.
  - Printed PETG: ~2.8 kg, ~$60.
  - Screws and nuts: ~$20.
  - 30 extension springs: ~$40–80 (the two root dorsal springs are the heavy ones).
  - Cord, felt: ~$10.
- **Gate-hinge chain:** would be roughly half that.
- **Elastic tube spine:** about a quarter.

The ball chain costs more, and the extra buys the pitch compliance the hovering Gojira tail needs.

## Simulated photos

`results/pose_renders/` holds the physics-accurate renders. The tail shape at each instant comes from the simulation
of the recommended design; the performer mannequin is posed from the simulated pelvis motion.
`results/simulated_photos/` holds photoreal versions: Z-Image Turbo image-to-image at partial denoise, which keeps
the simulated geometry and camera.

| Pose (instant) | Physics render | Tail state |
|---|---|---|
| Standing still (rest) | `1_standing.png` | Low point 8.9 cm above the floor |
| Bending over (pelvis pitched 45°, 3 s) | `2_bending_over.png` | Tail rises as a counterbalance, 62 cm clear |
| Turning (45° in 0.5 s; instant of largest sideways tail deflection) | `3_turning.png` | Hips at 44°, tail still at −5°: ~49° of lag |
| Jerk to the left (30° in 0.25 s; largest sideways deflection) | `4_jerk_left.png` | Hips at 30°, tail at −5° |
| Jump, 50 ms before landing | `5_jump_before_landing.png` | Pelvis 10 cm above standing height, tail 22 cm clear |
