"""CAD consistency: OpenSCAD formulas == cad/geometry.py; printable-part limits."""
import json
import subprocess
import unittest
from pathlib import Path

from cad import geometry as g

ROOT = Path(__file__).resolve().parents[1]
SCAD = ROOT / "cad" / "openscad" / "suit_tail.scad"


class TestCad(unittest.TestCase):
    def test_geometry_checks_pass(self):
        failed = [c for c in g.checks(g.CadParams()) if not c[1]]
        self.assertEqual(failed, [])

    def test_openscad_matches_python_spec(self):
        self._compare(SCAD, g.CadParams())

    def test_gojira_variant_matches_python_spec(self):
        pj = ROOT / "cad" / "variants" / "gojira.json"
        p = g.CadParams(**json.loads(pj.read_text()))
        self.assertEqual([c for c in g.checks(p) if not c[1]], [])
        self._compare(ROOT / "cad" / "openscad" / "suit_tail_gojira.scad", p)

    def _compare(self, scad, p):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            echo = Path(td) / "dims.echo"
            out = subprocess.run(["openscad", "-o", str(echo), "-D", 'PART="none"', str(scad)], capture_output=True, text=True)
            text = (echo.read_text() if echo.exists() else "") + out.stdout + out.stderr
        rows = [l.split('"')[1].split(",")[1:] for l in text.splitlines() if "DIMS," in l]
        self.assertEqual(len(rows), p.joint_count, text[-500:])
        keys = ("D", "RF", "RB", "RS", "RN", "beta_y", "beta_p", "cap_h", "DF", "body_len", "spring_arm")
        for r, s in zip(rows, g.summary(p)):
            vals = [float(x) for x in r[1:]]
            for k, v in zip(keys, vals):
                self.assertAlmostEqual(v, s[k], places=3, msg=f"joint {s['i']} {k}")

    def test_exported_parts_fit_printer_and_sit_on_bed(self):
        files = [ROOT / "cad" / "stl" / n for n in ("parts.json", "parts_gojira.json")]
        if not any(f.exists() for f in files):
            self.skipTest("run cad/export_stl.py first")
        for pj in files:
            if not pj.exists():
                continue
            for name, st in json.loads(pj.read_text()).items():
                self.assertTrue(all(x <= 200.0 for x in st["bbox_mm"]), f"{pj.name}:{name} {st['bbox_mm']}")
                self.assertTrue(st["on_bed"], f"{pj.name}:{name}")


if __name__ == "__main__":
    unittest.main()
