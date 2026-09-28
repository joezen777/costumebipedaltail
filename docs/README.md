# Passive suitmation tail: documentation index

Brief: [brief.md](brief.md) (original design brief). Results overview: [../README.md](../README.md). Environment rules: `../AGENTS.md`.

| Document | Contents |
|---|---|
| [physics.md](physics.md) | Simulation model, the design findings it produced, validation tests, how to reproduce |
| [design.md](design.md) | Mechanical architecture, twist-stable spring geometry, performer fit (5 ft 8 in), strength approach |
| [printing.md](printing.md) | 1.2 mm nozzle settings, print orientation per part, material choice (PETG vs PLA/TPU vs resin), hardware list, assembly |
| [test_plan.md](test_plan.md) | 4-joint physical prototype: build, ballast, measurements that calibrate the model |
| [tables/study.md](tables/study.md) | Every configuration on identical hip inputs (README §27 A–D plus ablations) |
| [tables/hardware.md](tables/hardware.md) | The *same built tail* with cord preload, friction liner, COM and roll key changed |
| [tables/springs.md](tables/springs.md) | Spring schedule: rate, preload, installed length per joint |
| [tables/strength.md](tables/strength.md) | Peak simulated loads vs printed-section capacity |
| [tables/mass_budget.md](tables/mass_budget.md) | Moving mass per segment from the exported CAD vs the README targets |

## Where the files are

| Path | What |
|---|---|
| `tailsim/` | MuJoCo physics package (parameters, model builder, simulator, metrics, plots, linear modes, mass budget) |
| `tests/` | `test_physics.py` (8 physics validation tests), `test_cad.py` (OpenSCAD ⇄ Python spec, printability) |
| `experiments/` | `sweep.py` (tuning), `run_suite.py` (study + media), `make_tables.py` (docs tables) |
| `cad/geometry.py` | Single dimensional spec shared by physics, OpenSCAD test and FreeCAD |
| `cad/openscad/suit_tail.scad` | Parametric OpenSCAD model (README §20 modules and PART views, plus print-oriented parts) |
| `cad/freecad/build_tail.py` | Parametric FreeCAD model (`createVertebra(index, parameters)`), writes FCStd + STEP |
| `cad/freecad/output/` | `suit_tail.FCStd/.step`, `test_section_4joint.FCStd/.step` |
| `cad/stl/full/`, `cad/stl/test_section/` | Print-ready STLs; `cad/stl/parts.json` = sizes, volumes, masses |
| `results/figures/`, `results/animations/`, `results/cad_renders/` | Plots, GIF/MP4 animations, CAD views |
| `results/data/` | Metrics JSON, per-timestep CSVs (`csv/`), mass budget |
