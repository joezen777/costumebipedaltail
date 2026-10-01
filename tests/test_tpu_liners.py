"""TPU felt substitutes and washers: printable, closed, flat-to-sphere stretch small, washer count covers the build.

    PYTHONPATH=. python -m unittest tests.test_tpu_liners
(the slower mesh stop check is `PYTHONPATH=. python cad/check_tpu_liners.py`)
"""
import json
import unittest

import trimesh

from cad import geometry as g
from cad.tpu_liners import OUT, cfg, liner_strain


class TestTpuLiners(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.info = json.loads((OUT / "liners.json").read_text())
        cls.c = cfg()

    def test_all_stls_closed_on_bed_and_fit_the_bed(self):
        files = sorted(OUT.glob("**/*.stl"))
        self.assertEqual(len(files), 6 + 6 + len(self.info["plates"]))
        for f in files:
            m = trimesh.load(f)
            self.assertTrue(m.is_watertight, f.name)
            self.assertAlmostEqual(m.bounds[0][2], 0.0, places=4)
            self.assertLessEqual(max(m.extents[:2]), 200.0, f.name)

    def test_liner_flat_pattern_stretches_under_3_percent_when_fitted(self):
        for i in range(1, self.c.joint_count + 1):
            self.assertLess(liner_strain(self.c, i), 0.03)

    def test_rings_land_before_petg(self):
        for r in self.info["rows"]:
            self.assertLessEqual(max(r["stops8"]), g.yaw_lim(self.c, r["joint"]) + 1e-6)
            for st, p in zip(r["stops8"], r["petg8"]):
                if p is not None:
                    self.assertLessEqual(st, p - 1.0)

    def test_washer_sheet_covers_every_m4_bolt_plus_spares(self):
        w = self.info["washers"]
        self.assertEqual(w["cap"] + w["flange"], 8 * self.c.joint_count)
        self.assertGreaterEqual(w["with_spares"], 1.1 * w["total"])
        sheet = [p for p in self.info["plates"] if p[0].startswith("plate_washers")]
        self.assertEqual(sum(n for _, n in sheet), w["with_spares"])


if __name__ == "__main__":
    unittest.main()
