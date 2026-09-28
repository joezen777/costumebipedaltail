"""Photoreal "simulated photos" from the physics pose renders via ComfyUI + Z-Image Turbo (img2img).

The MuJoCo renders (experiments/pose_renders.py) fix the performer pose and the simulated tail
shape; img2img at partial denoise adds photographic realism while keeping that geometry.
Requires ComfyUI running at 127.0.0.1:8188 (start with ~/comfyuiinstall.sh).

    python experiments/photoreal.py [--denoise 0.55 0.65] [--seeds 2]
"""
import argparse
import json
import time
import urllib.request
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "results" / "pose_renders"
OUT = ROOT / "results" / "simulated_photos"
URL = "http://127.0.0.1:8188"

BASE = ("Behind-the-scenes photograph on a film studio soundstage: a performer wearing a full-body friendly "
        "cartoon dinosaur costume, soft rounded shapes, green plush-like skin with a pale belly, small rounded dorsal "
        "bumps. A short, very thick tapered dinosaur tail attached at the lower back on a lumbar support belt, shaped like a "
        "reverse sigmoid: it starts level out from the lower back, curves smoothly down, then flattens out so its "
        "rounded end sticks straight out behind at knee height, clear of the floor. Practical costume, 35mm film still, soft studio key light, realistic, detailed. ")
POSES = {
    "1_standing": "The dinosaur stands still and upright, arms held forward, tail at rest behind it.",
    "2_bending_over": "The dinosaur bends forward deeply at the hips, torso leaning down, the short tail lifted up behind it as a counterbalance.",
    "3_turning": "The dinosaur turns its hips sharply toward its left; the thick tail lags behind, still pointing the old direction, swinging around.",
    "4_jerk_left": "The dinosaur jerks its hips abruptly to the left; the short tail swings behind, lagging and curving sideways.",
    "5_jump_before_landing": "The dinosaur is mid-air at the end of a jump, feet a few centimetres above the floor just before landing, tail bouncing behind it.",
}


def _post(path, data, headers):
    req = urllib.request.Request(URL + path, data=data, headers=headers)
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())


def upload(path: Path):
    boundary = uuid.uuid4().hex
    body = (f"--{boundary}\r\nContent-Disposition: form-data; name=\"image\"; filename=\"{path.name}\"\r\n"
            f"Content-Type: image/png\r\n\r\n").encode() + path.read_bytes() + \
           f"\r\n--{boundary}\r\nContent-Disposition: form-data; name=\"overwrite\"\r\n\r\ntrue\r\n--{boundary}--\r\n".encode()
    return _post("/upload/image", body, {"Content-Type": f"multipart/form-data; boundary={boundary}"})["name"]


def workflow(image_name, prompt, denoise, seed):
    return {
        "1": {"class_type": "UNETLoader", "inputs": {"unet_name": "z_image_turbo_bf16.safetensors", "weight_dtype": "default"}},
        "2": {"class_type": "CLIPLoader", "inputs": {"clip_name": "qwen_3_4b.safetensors", "type": "lumina2", "device": "default"}},
        "3": {"class_type": "VAELoader", "inputs": {"vae_name": "ae.safetensors"}},
        "4": {"class_type": "ModelSamplingAuraFlow", "inputs": {"shift": 3, "model": ["1", 0]}},
        "5": {"class_type": "CLIPTextEncode", "inputs": {"text": prompt, "clip": ["2", 0]}},
        "6": {"class_type": "ConditioningZeroOut", "inputs": {"conditioning": ["5", 0]}},
        "7": {"class_type": "LoadImage", "inputs": {"image": image_name}},
        "8": {"class_type": "VAEEncode", "inputs": {"pixels": ["7", 0], "vae": ["3", 0]}},
        "9": {"class_type": "KSampler", "inputs": {"seed": seed, "steps": 8, "cfg": 1, "sampler_name": "res_multistep",
                                                   "scheduler": "simple", "denoise": denoise, "model": ["4", 0],
                                                   "positive": ["5", 0], "negative": ["6", 0], "latent_image": ["8", 0]}},
        "10": {"class_type": "VAEDecode", "inputs": {"samples": ["9", 0], "vae": ["3", 0]}},
        "11": {"class_type": "SaveImage", "inputs": {"filename_prefix": "suit_tail/photo", "images": ["10", 0]}},
    }


def run(wf):
    pid = _post("/prompt", json.dumps({"prompt": wf, "client_id": "suit-tail"}).encode(),
                {"Content-Type": "application/json"})["prompt_id"]
    while True:
        with urllib.request.urlopen(f"{URL}/history/{pid}", timeout=30) as r:
            h = json.loads(r.read())
        if pid in h and h[pid].get("outputs"):
            img = h[pid]["outputs"]["11"]["images"][0]
            q = f"/view?filename={img['filename']}&subfolder={img['subfolder']}&type={img['type']}"
            with urllib.request.urlopen(URL + q, timeout=60) as r:
                return r.read()
        if pid in h and h[pid].get("status", {}).get("status_str") == "error":
            raise RuntimeError(json.dumps(h[pid]["status"])[:800])
        time.sleep(1.0)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--denoise", type=float, nargs="+", default=[0.55, 0.65])
    ap.add_argument("--seeds", type=int, default=2)
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    meta = {}
    for name, extra in POSES.items():
        src = SRC / f"{name}.png"
        up = upload(src)
        for dn in a.denoise:
            for k in range(a.seeds):
                seed = 1000 + 17 * k
                out = OUT / f"{name}__dn{int(dn*100)}_s{k}.png"
                out.write_bytes(run(workflow(up, BASE + extra, dn, seed)))
                meta[out.name] = dict(source=src.name, denoise=dn, seed=seed, prompt=BASE + extra)
                print(out.name, flush=True)
    (OUT / "generation.json").write_text(json.dumps(meta, indent=1))


if __name__ == "__main__":
    main()
