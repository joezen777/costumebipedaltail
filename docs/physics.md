# Physics prototype: model, validation and findings

The question from the brief:

> When a human performer turns their hips, does this mechanism produce the exaggerated but physically believable
> secondary tail movement of traditional practical creature suits?

**Short answer: yes, but only with passive centring springs across each joint.** A friction-only ball chain
(README configurations A–D taken literally) cannot swing back. With a spring spine the tail:
- lags ~40° behind a 30° hip snap,
- catches up,
- overshoots by 5–10°,
- makes one visible return swing,
- settles in about 1 s.

Ordinary walking gives a restrained 1.7–2× tip sway. The rest of this document explains the model, the findings
that shaped the CAD, and how the model was checked.

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
- **COM sweep (0, 15, 30, 50 mm):**
  - Linear analysis: the offset raises the twist-mode frequency (0.12 → 0.34 Hz before the anchor fix).
  - Time domain: it slightly reduces overshoot and adds a little residual offset.
- A modest 15 mm is the reference. There is no benefit in going to 50 mm; see `docs/tables/study.md`.

### 2.6 The cord's job is retention, not motion

In a rigid-socket model a centred cord stores no bending energy. Its only mechanical effect is seat compression,
which adds friction. Raising the preload from 5 to 40 N monotonically adds friction and deadens the tail
(`study_preload_hip_snap.png`). Keep the preload low (5–10 N): enough to keep the balls seated and take up slack.
The joint-load output (`min_seat_compression`) confirms the seats never unload during the tests. The springs keep
every ball in compression.

### 2.7 Walking vs. snap: frequency placement

- Pelvis yaw in walking repeats once per **stride**, i.e. at half the step rate (0.75–1.0 Hz for 1.5–2.0 steps/s).
- The tail's first swing mode sits below that, so walking drives it above resonance. The tip heading amplitude is
  1.7–2× the hip's (visible but restrained, no stop hits). A hip snap, being a transient, gets the full lag and
  overshoot.
- The README-literal case (yaw at the full 1.75 Hz step rate) is also run (`walk_1.75Hz_literal`).

### 2.8 Mass budget: the distal end is heavier than the README guess

The printed + hardware + foam/skin mass per segment (`docs/tables/mass_budget.md`) matches the README at the root
(~475 vs 450 g) but is 1.5–2.8× heavier toward the tip. Two floors cause this:
- the minimum practical ball (Ø34 mm) with M4 bolts;
- two-line fins on a 150 mm segment.

The `cad_masses` configuration re-runs every test with these masses (row "reference, CAD masses" in
`docs/tables/study.md`), so the prototype is judged on its real inertia.

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
