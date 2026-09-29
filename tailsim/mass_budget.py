"""Moving-mass budget per vertebra from the exported CAD (cad/stl/parts.json).

segment i = body_i + cap_i (two printed halves) + ball_(i+1) halves (or tip adapter) + hardware
            + springs of joint i+1 anchored on it (half of each) + foam/skin.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# hardware masses (g), commodity steel parts
M4_SHCS_16 = 2.4
M4_NYLOCK = 1.1
M3_SCREW = 0.9
ROLL_PIN = {4: 2.0, 3: 0.9}
FELT_LINER = 3.0          # g per seat
FOAM_DENSITY = 30.0       # kg/m^3 upholstery foam (EVA ~ 60)
SKIN_AREAL = 0.30         # kg/m^2 spandex + latex/silicone paint


def spring_mass(k_n_per_mm, T_n):
    """Rough steel extension spring mass for a load T and rate k (g)."""
    return 2.0 + 0.10 * T_n + 0.5 * k_n_per_mm


def budget(cad=None, spring_table=None, parts_json=ROOT / "cad" / "stl" / "parts.json"):
    from cad import geometry as g
    cad = cad or g.CadParams()
    parts = json.loads(Path(parts_json).read_text())
    n = cad.joint_count
    L = g.spacing(cad) / 1000
    rows = []
    for i in range(1, n + 1):
        cap = (parts[f"cap_{i}_a"]["mass_g"] + parts[f"cap_{i}_b"]["mass_g"]) if f"cap_{i}_a" in parts else parts[f"cap_{i}"]["mass_g"]
        printed = parts[f"body_{i}"]["mass_g"] + cap
        if i < n:
            printed += parts[f"ball_{i+1}_left"]["mass_g"] + parts[f"ball_{i+1}_right"]["mass_g"]
        else:
            printed += parts["tip_adapter"]["mass_g"]
        hardware = 4 * (M4_SHCS_16 + M4_NYLOCK) + FELT_LINER
        if i < n:
            hardware += 4 * (M4_SHCS_16 + M4_NYLOCK) + ROLL_PIN[int(g.pin_spec(cad, i + 1)[0])]
        else:
            hardware += 4 * M3_SCREW + 8.0          # tip spring, washers, cord lock
        springs = 0.0
        if spring_table:
            for s in spring_table:
                if s["joint"] in (i - 1, i):         # half of each spring on either side
                    springs += 0.5 * spring_mass(s["k"] / 1000, s["T0"])
        R, Rf = g.D(cad, i) / 2000, g.RF(cad, i) / 1000
        foam = math.pi * (R * R - Rf * Rf) * L * FOAM_DENSITY * 1000
        skin = math.pi * 2 * R * L * SKIN_AREAL * 1000
        rows.append(dict(i=i, printed_g=printed, hardware_g=hardware, springs_g=springs, foam_g=foam, skin_g=skin,
                         total_g=printed + hardware + springs + foam + skin))
    return rows
