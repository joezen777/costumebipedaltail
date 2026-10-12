"""Revision-3 parts (one-piece balls, keyed caps, clips): exported, printable, and the mesh assembly check passed.

    PYTHONPATH=. python -m unittest tests.test_assembly_rev3
(the full check is `PYTHONPATH=. python cad/check_assembly_rev3.py`, logged to results/data/assembly_rev3_check.txt)
"""
import json
import unittest
from pathlib import Path

import trimesh

from cad.make_variant import BALL_ACCESS

ROOT = Path(__file__).resolve().parents[1]
STL = ROOT / "cad" / "stl" / "barney"


class TestAssemblyRev3(unittest.TestCase):
    def test_new_parts_exported_closed_on_bed(self):
        names = ["lobe_clip"] + [f"ball_{i}" for i in range(1, 7)] + [f"cap_key_{i}_{s}" for i in range(1, 7) for s in "vd"] \
            + [f"flange_clip_{i}" for i in range(2, 7)]
        for n in names:
            m = trimesh.load(STL / f"{n}.stl")
            self.assertTrue(m.is_watertight, n)
            self.assertEqual(len(m.split(only_watertight=False)), 1, n)
            self.assertAlmostEqual(m.bounds[0][2], 0.0, places=2)
            self.assertLessEqual(max(m.extents), 200.0)
        self.assertFalse(list(STL.glob("ball_*_left.stl")), "stale clamshell halves")

    def test_access_list_and_check_log(self):
        self.assertEqual(sum(len(a) for a in BALL_ACCESS["barney"]), 16)
        log = (ROOT / "results" / "data" / "assembly_rev3_check.txt").read_text().strip().splitlines()
        self.assertEqual(log[-1].strip(), "ALL OK")
        self.assertFalse([l for l in log if l.startswith("FAIL")])
        parts = json.loads((ROOT / "cad" / "stl" / "parts_barney.json").read_text())
        self.assertFalse([k for k in parts if k.endswith("_left") or k.endswith("_right")])


if __name__ == "__main__":
    unittest.main()
