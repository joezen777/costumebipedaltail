"""Preview renders of the 1:8 figurine with the 1:8 tail kit slid to three levels (from the STLs).

    PYTHONPATH=. ~/.venvs/costumebipedaltail/bin/python cad/render_figurine.py
Output: cad/stl/figurine_1to8_resin/preview_*.png
"""
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCAD = ROOT / "cad" / "openscad" / "figurine_1to8.scad"
OUT = ROOT / "cad" / "stl" / "figurine_1to8_resin"
FIG = OUT.as_posix()

SCENE = f'''include <{SCAD.as_posix()}>
FIG = "none";
KIT_DIR = "{(ROOT / "cad" / "stl" / "replica_1to8_resin").as_posix()}/";
module fig(dz) {{
    color("Wheat") import("{FIG}/20_figure_body.stl");
    color("DimGray") import("{FIG}/22_display_base.stl");
    translate(HEAD_POS) {{ color("WhiteSmoke") import("{FIG}/21_protogen_head.stl"); color("Black") translate([0.02, 0, 0]) visor(); }}
    kit_tail(dz);
}}
'''
# name, body of the scene, camera (tx,ty,tz,rx,ry,rz,dist), image size
VIEWS = [
    ("preview_levels_side", "translate([0, -110, 0]) fig(-16); fig(0); translate([0, 110, 0]) fig(36);",
     "-30,0,-20,90,0,0,640", "1800,1100"),
    ("preview_back_3q", "fig(0);", "-20,0,0,72,0,235,540", "1000,1300"),
    ("preview_head", "translate(-HEAD_POS) fig(0);", "6,0,12,78,0,40,130", "1000,1000"),
    ("preview_slot_empty", f'color("Wheat") import("{FIG}/20_figure_body.stl");',
     "-15,0,15,70,0,215,170", "1000,1000"),
]


def main():
    with tempfile.TemporaryDirectory() as td:
        for name, body, cam, size in VIEWS:
            f = Path(td) / f"{name}.scad"
            f.write_text(SCENE + body)
            r = subprocess.run(["openscad", "-o", str(OUT / f"{name}.png"), f"--imgsize={size}", f"--camera={cam}",
                                "--colorscheme=Tomorrow", "--projection=p", str(f)], capture_output=True, text=True,
                               cwd=SCAD.parent)
            print(name, r.returncode, [l for l in r.stderr.splitlines() if "ERROR" in l or "WARNING" in l][:3])


if __name__ == "__main__":
    main()
