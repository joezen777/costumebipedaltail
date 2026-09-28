"""Render README section 23 CAD views to results/cad_renders/ (OpenSCAD preview)."""
import subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT.parent / "results" / "cad_renders"
V = ROOT / "openscad" / "render_views.scad"
S = ROOT / "openscad" / "suit_tail.scad"

# name, scad, defines, camera (tx,ty,tz,rx,ry,rz,dist)
VIEWS = [
    ("side_neutral_with_actor", V, {"VIEW": '"neutral"'}, "-550,0,-50,90,0,0,4300"),
    ("top_neutral", V, {"VIEW": '"neutral"', "SHOW_ACTOR": "false"}, "-750,0,-250,0,0,0,2600"),
    ("top_moderate_turn", V, {"VIEW": '"turn"', "SHOW_ACTOR": "true"}, "-650,-250,-250,0,0,0,3000"),
    ("top_max_curvature_limit_cones", V, {"VIEW": '"max"', "SHOW_ACTOR": "false"}, "-550,-450,-250,0,0,0,3000"),
    ("iso_max_curvature", V, {"VIEW": '"max"', "SHOW_ACTOR": "true"}, "-550,-350,-250,60,0,210,4200"),
    ("iso_cord_path", V, {"VIEW": '"cord"', "SHOW_ACTOR": "false"}, "-700,0,-250,65,0,215,2400"),
    ("iso_test_section_4joint", V, {"VIEW": '"test_section"', "SHOW_ACTOR": "false"}, "-450,0,-120,65,0,215,1500"),
    ("exploded_vertebra_2", V, {"VIEW": '"exploded"', "INDEX": "2", "SHOW_ACTOR": "false"}, "30,0,0,65,0,20,700"),
    ("section_joint_1", S, {"PART": '"section"', "INDEX": "1"}, "40,0,0,90,0,180,420"),
    ("section_joint_5", S, {"PART": '"section"', "INDEX": "5"}, "40,0,0,90,0,180,300"),
    ("ball_joint_2", S, {"PART": '"ball"', "INDEX": "2"}, "0,0,0,60,0,30,220"),
    ("socket_cap_joint_2", S, {"PART": '"socket"', "INDEX": "2"}, "0,0,0,60,0,210,300"),
    ("vertebra_1", S, {"PART": '"vertebra"', "INDEX": "1"}, "60,0,0,60,0,210,520"),
    ("hip_mount", S, {"PART": '"hip_mount"'}, "-150,0,0,65,0,230,520"),
]


def render(v):
    name, scad, defs, cam = v
    OUT.mkdir(parents=True, exist_ok=True)
    cmd = ["openscad", "-o", str(OUT / f"{name}.png"), "--imgsize=1600,1000", f"--camera={cam}",
           "--colorscheme=Tomorrow", "--projection=p"]
    for k, val in defs.items():
        cmd += ["-D", f"{k}={val}"]
    cmd.append(str(scad))
    r = subprocess.run(cmd, capture_output=True, text=True, cwd=scad.parent)
    return name, r.returncode, "\n".join(l for l in r.stderr.splitlines() if "WARNING" in l or "ERROR" in l)[:300]


if __name__ == "__main__":
    with ThreadPoolExecutor(2) as ex:
        for name, rc, msg in ex.map(render, VIEWS):
            print(name, "ok" if rc == 0 else f"rc={rc}", msg)
