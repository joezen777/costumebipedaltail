"""TPU strap stand-ins for the Barney springs: targets met, printable, fit-checked, calibration round-trips.

    PYTHONPATH=. python -m unittest tests.test_tpu_bands
"""
import json
import unittest
from pathlib import Path

import trimesh

from cad.tpu_bands import (COUPON_GAUGE, EYE_RATIO, MATERIALS, Material, OUT, coupon, fit_material)

ROOT = Path(__file__).resolve().parents[1]


class TestTpuBands(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.straps = json.loads((OUT / "straps.json").read_text())["straps"]

    def test_every_spring_has_a_strap_meeting_its_targets(self):
        self.assertEqual(len(self.straps), 18)
        for s in self.straps:
            self.assertAlmostEqual(s["T0_pair"], s["T0_target"], delta=0.01 * s["T0_target"], msg=s["name"])
            tol = 0.15 if s["capped"] else 0.02
            self.assertLessEqual(abs(s["k_pair"] / s["k_target"] - 1), tol, s["name"])
            self.assertLessEqual(s["T_stop_pair"], s["T_stop_spring"] * 1.02, s["name"])   # never over the springs
            self.assertLess(s["P_print"], s["span"], s["name"])
            self.assertLessEqual(s["eps"], MATERIALS[s["material"]].eps_max + 1e-9, s["name"])

    def test_stls_are_single_closed_bodies_on_the_bed(self):
        files = sorted(OUT.glob("*/*.stl"))
        self.assertGreaterEqual(len(files), 18 + 2)
        for f in files:
            m = trimesh.load(f)
            self.assertTrue(m.is_watertight, f.name)
            self.assertEqual(len(m.split(only_watertight=False)), 1, f.name)
            self.assertAlmostEqual(m.bounds[0][2], 0.0, places=4)
            self.assertLess(max(m.extents), 200, f.name)

    def test_calibration_fit_recovers_a_known_material(self):
        true = Material("tpu65a", "neo", E0=6.0, set_frac=0.04, eps_max=0.8)
        cp = coupon("tpu65a")
        A, R = cp.w * cp.t, cp.R_eye
        L0 = cp.P_print + true.set_frac * COUPON_GAUGE
        pts = [[kg, (L0 - 2 * R) * (1 + true.strain(kg * 9.81 / A)) + 2 * R * (1 + true.strain(kg * 9.81 / A / EYE_RATIO))]
               for kg in (0, 0.5, 1, 1.5, 2)]
        fit = fit_material(MATERIALS["tpu65a"], {"width": cp.w, "thickness": cp.t, "points": pts})
        self.assertAlmostEqual(fit.E0, 6.0, delta=0.05)
        self.assertAlmostEqual(fit.set_frac, 0.04, delta=0.005)


if __name__ == "__main__":
    unittest.main()
