# Physics prototype: model, validation and findings

The question from the brief:

> When a human performer turns their hips, does this mechanism produce the exaggerated but physically believable
> secondary tail movement of traditional practical creature suits?

**Short answer: yes, but only with passive centring springs across each joint.**

A friction-only ball chain cannot swing back. The "no springs" run never follows the hip: it ends 33° off the
hip's heading and drags on the floor when crouching.

With the spring spine designed here, and the **as-built masses from the exported CAD**, the tail's response to a
30° hip snap in 0.35 s is:

| Metric | As built | README intent |
|---|---|---|
| Maximum tip lag behind the hip | 38.6° (tip first swings the *other* way as the root is carried sideways) | "tail mass lags behind" |
| Tip overshoot after the hip stops | 10.3° (34 %) | "tip overshoots" |
| Visible swing-back / oscillations | 1 | 1–2 decreasing oscillations |
| Settling (within 2°) | 1.9 s | settles |
| Residual offset | 0.0° | — |
| 45° dramatic turn overshoot | 28.7° | "tip swings noticeably" |
| Walking tip/hip yaw ratio (1.5 / 2.0 steps/s) | 1.61 / 1.27, no stop hits | visible but restrained |
| Crouch (−150 mm, 10°) | no floor contact, no binding | — |

Animations: `results/animations/as_built_*.gif`. Joint-yaw waterfall showing the wave travelling root → tip:
`results/figures/as_built_hip_snap_waterfall.png`. Tuning knobs, from the same-hardware study
(`docs/tables/hardware.md`):
- **The seat liner (friction) is the main knob.** PTFE instead of felt gives a whippy 41° overshoot with two
  oscillations; dry PETG gives 20°.
- **Cord preload barely matters** on built hardware (5 → 40 N changes overshoot by 0.4°).
- **Removing the roll key halves the swing.** The energy leaks into twisting.

## 1. Model (MuJoCo 3.13, `tailsim/`)

| Element | Representation |
|---|---|
| Pelvis | Kinematic "hip block" (80 kg, 6 DOF) driven along the prescribed path by a stiff PD servo with feed-forward (tracking error < 0.06°) |
| Vertebrae | 8 separate rigid bodies, each with its own mass, centre of mass (optionally offset below the axis) and a thick-tube inertia from the taper |
| Ball joint | Three serial hinges yaw → pitch → roll at the ball centre, each with its own soft limit (TPU/felt stop, 12 ms time constant) |
| Ball friction | Coulomb `frictionloss` on each hinge = μ · R_ball · \|F_ball\|. F_ball is recomputed every 2 ms from the actual ball reaction: the distal subtree's inertial and gravity load plus every tension crossing that joint (cord + springs) |
| Viscous damping | Small, scaled by distal inertia (felt/grease) |
| Central cord | Spatial tendon through every ball centre; tension-only spring/damper: T = max(0, T0 + k ΔL + c dL/dt) |
| Spring spine | Per joint, one dorsal and two lateral tension-only springs between the real CAD anchor points |
| Foam tip | Compliant 2-DOF body (0.6 N·m/rad) with soft floor contact |
| Floor | Plane at z = 0, soft contact, μ = 0.6 |

The geometry (ball radii, anchor positions and spring arms) is imported from `cad/geometry.py`, so the simulated
tail is the printable one.

## 2. Findings that changed the design

### 2.1 Friction alone cannot give the swing-back; a restoring stiffness is required

- A ball chain with only friction and stops has no preferred heading. After a hip snap it coasts until friction
  stops it, or until it slams into its stops.
- The "tip overshoots → tail swings back → 1–2 decaying oscillations" sequence in the README is the signature of a
  **spring–mass** system. Something has to store energy when the tail bends and return it.
- A cord through the ball centres can't do this, because its length does not change when a joint bends. The
  `naive_no_springs` configuration shows the result: the tail never swings back. It drifts, hangs on its stops and
  keeps whatever offset friction leaves it with. (Numbers in `docs/tables/study.md`.)

So each joint gets three tension-only extension springs:
- **Dorsal:** preloaded to carry the tail's weight moment.
- **Left and right:** an antagonistic pair giving yaw centring.

### 2.2 The dorsal spring must hold the tail up

The tail's weight moment at the root is ~9 N·m. Friction torque (μ·R·N ≈ 1 N·m) can't hold it, so without
support the tail sags onto its pitch stops. Once it rests on a stop, that stop's friction brakes the yaw swing.

The dorsal spring preload is set so that its generalized force cancels the gravity bias at the rest pose,
`T0 = −qfrc_bias / (dL/dq)`. This gives 147 N at joint 1, falling to ~9 N at joint 8.

### 2.3 Spring stiffness must beat the friction dead band

A Coulomb joint with a centring spring K stops anywhere within ±τ_f / K of centre. The springs are sized to the
larger of:

- an inertia rule, K = (2π · 0.7 Hz)² · I_distal
- a friction rule, K = τ_f / 3.5° (with τ_f from the static ball load, which includes the springs' own preload,
  hence the iteration)

The first attempt used only the inertia rule. After a hip snap the tail stuck 40° off-centre: at the tip the
friction torque was several times the spring torque.

### 2.4 Twist stability decides where the springs attach (the key CAD change)

A preloaded spring crossing a pivot has geometric stiffness. With the child anchor *distal* of the pivot, the
yaw–roll stiffness matrix of the joint is indefinite, with determinant −a_p·a_c·w²·(T/ℓ)². With roll free, the
150 N dorsal spring then acts as a negative yaw spring.

- **Linearised model:** the lowest mode of the whole tail was −0.28 Hz, i.e. statically unstable.
- **Time domain:** after the hip snap the tail kept corkscrewing slowly away from centre (tip heading 25° → 17° over
  4 s while roll crept to its ±7° stops). That's the README's "uncontrolled twisting".
- **Fix:** move the child anchor to an ear on the socket cap, 5 mm *proximal* of the pivot. The saddle becomes
  positive-definite, and the same springs now centre in both yaw and roll. The lowest mode of the reference design
  is +0.30 Hz.
- **Guard:** `TailSim._design_springs` also stiffens the lateral pair until the lowest linear mode is above
  0.1 Hz. It needed no extra stiffening for the reference design.

### 2.5 COM offset (gravity bias) helps roll, not yaw

- τ = m·g·r·sin θ acts about the **roll** axis. For yaw it only helps through the 15° root pitch.
- **Design study, 0 → 50 mm:**
  - The lowest (twist) mode stiffens from 0.18 to 0.31 Hz.
  - Snap overshoot grows from 1.4° to 4.9°, and the tail settles cleaner (residual 0.5° → 0°).
- **Same hardware, 0 / 15 / 30 mm:** overshoot 9.2° / 10.3° / 11.2°, settling 2.1 / 1.9 / 1.7 s.
- So a modest offset does help natural settling and twist resistance, but it is a secondary knob.
- 15 mm is the reference (ballast low in the frame, e.g. a steel washer on the ventral fin). 50 mm buys little and
  adds mass.

### 2.5a The roll key

- **Roll free vs roll key** (`roll_free_vs_roll_key.gif`, same hardware): the hip-snap overshoot drops from 10.3°
  to 5.7° and the turn overshoot from 28.7° to 11.2°. Roll reaches 9.7°.
- In the design study, D with unrestricted roll loses its overshoot entirely.
- Energy that should swing the tail goes into twisting the chain, so keeping roll at ±7° with the key is worth it.

### 2.6 The cord's job is retention, not motion

In a rigid-socket model a centred cord stores no bending energy. Its only effect is seat compression, and
therefore friction.

- **Same built tail** (`hardware.md`): cord preload 5 → 40 N changes the hip-snap overshoot only from 10.4° to
  10.0° and the turn overshoot from 29.0° to 26.8°. The ~150 N dorsal and ~15–20 N lateral spring tensions already
  dominate the ball load.
- **Design study** (`study.md`), where the springs are re-sized for each preload: higher preload leads to stiffer
  springs and *more* overshoot (0.8° → 10.6°).
- **Recommendation:** set the cord for retention only (5–10 N, slack taken up) and tune motion with the liner and
  springs. `min_seat_compression` stays positive in every test, so no ball ever lifts off its seat.

### 2.7 Walking vs. snap: frequency placement

- Pelvis yaw in walking repeats once per **stride**, i.e. at half the step rate (0.75–1.0 Hz for 1.5–2.0 steps/s).
- The tail's first swing mode sits below that, so walking drives it above resonance. Tip heading amplitude is
  1.3–1.8× the hip's in every spring configuration (no stop hits). A hip snap, being a transient, gets the full lag
  and overshoot.
- With the README-literal input (yaw at the full 1.75 Hz step rate) the tail barely follows (ratio ≈ 0.9).
- HIGH friction is the exception. There the springs are sized stiff enough to beat the friction, and walking whip
  rises to 2.7–3.1×.

### 2.7a Other study results (`docs/tables/study.md`)

- **Joint count:**
  - 10 joints scores slightly better than 8 (4.2° overshoot, turn 22.6°).
  - 6 joints is heavier-looking and more swingy (12° overshoot, turn 35°).
  - 12 joints begins to look snake-like and the tip hangs lower (crouch tip 0.33 m).
  - 8 is kept for part count.
- **Progressive vs uniform limits:** uniform ±16.9° limits (A–C) give 10–14° snap overshoot versus 2.7° for the
  progressive 8 → 28° set (D, README masses). The stiff root reins in the swing and keeps the bend near the tip.
- **Mass taper:** uniform 250 g segments overshoot 14° and walk with less tip motion. The README's aggressive
  taper gives a heavier-root, looser-tip look.

### 2.8 Mass budget: the distal end is heavier than the README guess

The printed + hardware + foam/skin mass per segment (`docs/tables/mass_budget.md`) is about 12 % over the README at
the root (507 vs 450 g) but 1.5–2.8× heavier toward the tip. The total is ~2.55 kg against the README's 2.0 kg. Two floors cause this:
- the minimum practical ball (Ø34 mm) with M4 bolts;
- two-line fins on a 150 mm segment.

The `cad_masses` / `as_built` configurations re-run every test with these masses, so the prototype is judged on its
real inertia. The heavier tip turns out to *help* the theatrical look: overshoot 2.7° → 10.3° and a clear
swing-back. Loads rise ~10 %, still within the strength margins (`docs/tables/strength.md`).

## 3. Validation (`tests/test_physics.py`, all passing)

1. **Static support:** with the dorsal springs sized from the gravity bias, the settled rest pose moves < 0.5° in
   pitch.
2. **Ball load:** the joint-1 ball force from MuJoCo's `cfrc_int` equals a hand vector sum (distal weight + spring
   and cord tensions) within 2 %.
3. **Energy:** with friction and damping removed and a rigid base, total energy (kinetic + gravity + spring + foam
   tip) changes by exactly the work of the soft limit constraints (within 1 % of the input kick). Every
   non-constraint force is conservative.
4. **Modal check:** the small-motion modes of the linearised model (spring geometry, gravity and foam tip) are
   compared with the time-domain simulation, each mode excited on its own from a settled equilibrium. Measured
   frequencies agree within 5 % for the two lowest stable modes.
5. **Time-step convergence:** hip-snap tip heading at dt = 0.5 ms vs 0.25 ms agrees within 1.5°.
6. **Hip tracking:** the prescribed pelvis path is followed within 0.2° during the 45° turn.
7. **Tension-only:** cord and spring tensions never go negative.
8. **Gravity bias:** the roll restoring torque equals −m·g·r·sin θ·cos(tilt) within 8 %.

These checks cover the model as written. They do not validate the friction law, spring rates or foam behaviour
of real parts. That is what the 4-joint test section is for (`docs/test_plan.md`).

## 4. Reproduce

```bash
python3 -m venv ~/.venvs/costumebipedaltail && ~/.venvs/costumebipedaltail/bin/pip install -r requirements.txt
PYTHONPATH=. ~/.venvs/costumebipedaltail/bin/python -m unittest -v tests.test_physics tests.test_cad
PYTHONPATH=. ~/.venvs/costumebipedaltail/bin/python experiments/sweep.py stage3      # tuning sweep
PYTHONPATH=. ~/.venvs/costumebipedaltail/bin/python experiments/run_suite.py         # study, plots, animations, CSV
PYTHONPATH=. ~/.venvs/costumebipedaltail/bin/python experiments/make_tables.py       # docs/tables/*.md
```
