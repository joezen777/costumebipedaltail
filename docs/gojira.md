> **Superseded** by the client's Barney revision ([barney.md](barney.md)). The Gojira CAD, STLs and renders were removed; the mechanism comparison below is kept because the approved mechanics came from it.

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

## Final design as built (regenerated CAD, 10 joints)

The CAD was regenerated for this shape: `cad/variants/gojira.json`, `cad/openscad/suit_tail_gojira.scad`.

- **Exact CAD anchors:** the physics model was re-run with the CAD's spring anchor positions (parent anchors in the
  parent's own frame, as the fin holes are) and the wedge-flange neck lengths.
- **Raised design curve:** that made the tail settle ~2.5 cm lower, so the design low point was raised from 12 to
  14.5 cm on the centreline.
- **Real masses:** the tail was then simulated with the moving masses measured from the exported STLs, hardware and
  foam skin. That is **3.3 kg, against 2.2 kg assumed**, and heavier toward the tip; see
  [tables/gojira_mass_budget.md](tables/gojira_mass_budget.md).
- **Springs re-sized:** the springs were re-sized for those masses.
- **Geometry:** root pitch is 55°. The upward rest bends, printed as wedge flanges, are
  -2.4°, -2.9°, -3.6°, -4.4°, -5.5°, -7.0°, -8.8°, -10.5°, -11.6°.

| Test (as built) | Result |
|---|---|
| Rest (standing) | skin **8.6 cm** above the floor |
| 30° hip snap | lag 38.2°, overshoot 26.1°, 2 swing-backs, settles in 4.5 s; min clearance 3.3 cm |
| Jerk left (30° in 0.25 s) | lag 38.8°, overshoot 27.1° |
| 45° dramatic turn | overshoot 48.2°; foam brushes the floor at 1.8 N at the extreme of the swing |
| Walking 1.5 / 2.0 steps/s | tip/hip 1.08 / 0.85; min clearance 5.7 cm |
| Crouch (−150 mm, 10°) | min clearance 1.4 cm |
| Side step 300 mm | min clearance 3.5 cm |
| Bending over 45° | tail rises clear; peak hip moment 24.5 N·m |
| Jump (25 cm) | brief floor touch on the landing knee-bend, 26 N; hip moment 20.8 N·m |

What the extra mass changes:
- **More theatrical swing:** two swing-backs instead of one, and a larger overshoot.
- **Stronger springs:** the root dorsal springs need ~240 N at rest (two heavy springs in parallel at joints 1–4;
  see [tables/gojira_springs.md](tables/gojira_springs.md)).
- **Thicker cap ears:** 16 mm on the root caps. Every checked element keeps SF ≥ 3
  ([tables/gojira_strength.md](tables/gojira_strength.md)).

If the swing reads as too loose on the 4-joint prototype:
- first go from felt to a rubber seat liner, which adds friction;
- then lighten the distal vertebrae (two perimeters, 10 % infill), since they carry most of the excess mass.

Build files (the Gojira tail is the one to print):

| What | Where |
|---|---|
| Print-ready STLs, full tail (10 joints) | `cad/stl/gojira/`; list with sizes and masses in [tables/gojira_parts.md](tables/gojira_parts.md) |
| 4-joint prototype kit (joints 1–4 + ballast plate) | `cad/stl/gojira_test_section/` |
| OpenSCAD (parametric; generated variant file) | `cad/openscad/suit_tail_gojira.scad` (includes `suit_tail.scad`) |
| FreeCAD + STEP | `cad/freecad/output/suit_tail_gojira.FCStd/.step`, `test_section_4joint_gojira.FCStd/.step` |
| Springs, strength, mass | [tables/gojira_springs.md](tables/gojira_springs.md), [tables/gojira_strength.md](tables/gojira_strength.md), [tables/gojira_mass_budget.md](tables/gojira_mass_budget.md) |
| CAD renders (real parts; five simulated poses) | `results/cad_renders_gojira/` |

Printing notes specific to this variant:
- **Hip mount:** the root boss leaves the plate at 55°, so print it plate-down **with tree supports under the boss**.
  It is the only part that needs supports.
- **Ball halves:** each carries its joint's rest-bend wedge. Keep each ball with its joint number; they are not
  interchangeable.
- **Joint count:** there are 10 joints, so 10 caps, 10 bodies and 20 ball halves.

The finalist comparison above was computed with the first shape (12 cm design low point, 2.2 kg). Its conclusions
(rigid hinges are unsafe on landing, and the tube and stop-held chains fail the hover) do not depend on those
changes.

## Simulated photos

`results/pose_renders/` holds the physics-accurate renders. The tail shape at each instant comes from the simulation
of the recommended design; the performer mannequin is posed from the simulated pelvis motion.
`results/simulated_photos/` holds photoreal versions: Z-Image Turbo image-to-image at partial denoise, which keeps
the simulated geometry and camera.

| Pose (instant) | Physics render / photo / CAD render | Tail state (as built) |
|---|---|---|
| Standing still | `1_standing` | skin 8.6 cm above the floor |
| Bending over (pelvis pitched 45°, 3 s) | `2_bending_over` | tail rises as a counterbalance, 56 cm clear |
| Turning (45° in 0.5 s; largest sideways tail deflection) | `3_turning` | hips at 44°, tail at −9°: ~52° of lag |
| Jerk to the left (30° in 0.25 s) | `4_jerk_left` | hips at 30°, tail at −8° |
| Jump, 50 ms before landing | `5_jump_before_landing` | pelvis 10 cm above standing height, tail 23 cm clear |

The files are in `results/pose_renders/`, `results/simulated_photos/` (Z-Image Turbo image-to-image of the physics
render, denoise 0.55) and `results/cad_renders_gojira/` (the real exported STLs articulated with the simulated joint
angles).
