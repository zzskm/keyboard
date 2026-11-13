"""Assembly model of 46sp as built: the existing plywood case with the r3 acrylic cheeks, the print plate and cover.

Bodies (left half in the STEP frame, the right half placed RIGHT_DX to the user's right):
  case     - left: side walls, front block and back blocks of source/46sp_r3_left.step (its acrylic plates and
             its older f3d cheeks are removed). Right: the same mirrored, the blocks stretched to the right
             width (inner 150 -> plate 158) and the walls moved out by 12; its inner back block is the
             unrecessed one (no USB outlet, user 2026-11-13).
  cheeks   - r3 DWG 229E/22A0 (and 22B6/22CB for the right outer end), 5T, outer face on the wall pocket bottom.
  bones    - the 6 mm tie bars of dxf/46sp_bone.dxf in the bottom grooves and the two slanted slots.
  plate, cover - from tools/build_plate_cover.py.
  switches, keycaps - stand-ins for the clearance check and the pictures: top housing 15.6 square, 6.6 high;
             keycap 18.2 square, 8 high, its bottom 2.6 above the plate (bottomed out) to 6.6 + 8 (at rest).

    python 46sp/tools/build_assembly.py            # writes model/46sp-assembly.sc, checks, renders images/assembly-*.png
"""

import argparse
import json
import math
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory

from shapely.geometry import Polygon

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_plate_cover as bpc  # noqa: E402

ROOT = bpc.ROOT
OUTPUT = ROOT / "model/46sp-assembly.sc"
IMAGES = ROOT / "images"
CLI = bpc.CLI_DEFAULT

RIGHT_DX = -(75.0 + 30.0 + 87.0)        # right half's origin: 30 mm gap, to the user's right (-X)
CHEEK_IN = {"L": 63.0, "R": 75.0}        # |X| of the cheek's inner face: flush with the blocks (the 5T cheek
                                         # needs a 5 deep wall pocket; the STEP's is 4, for its older 4 mm cheek)
BONE_L = {"L": 134.0, "R": 158.0}        # dxf/46sp_bone.dxf
CHEEK_T = bpc.CHEEK_T
BONE_T = 6.0
SIDE_TO_STEP = (0.62, -15.0)             # dxf/46sp_side.dxf (x, y) -> STEP (Y, Z): offsets
BONE_SLOTS = [  # slanted bone slots in dxf/46sp_side.dxf (rotated 6.2 x 20.5 rectangles)
    [(166.44, 36.7), (156.76, 40.22), (151.97, 41.97), (149.85, 36.14), (154.64, 34.4), (164.32, 30.87),
     (169.11, 29.13), (171.23, 34.96)],
    [(29.43, 59.78), (28.11, 64.71), (22.12, 63.1), (23.44, 58.17), (24.82, 53.06), (26.14, 48.13),
     (32.13, 49.73), (30.81, 54.66)],
]
GROOVE_DEPTH = 10.49
HOUSING, HOUSING_H = 15.6, 6.6
CAP, CAP_TOP, CAP_H, CAP_REST, TRAVEL = 18.2, 12.7, 8.0, 6.6, 4.0   # generic MX keycap, tapered sides

STEP_BODIES = {"plates": ["본체1", "본체1 (2)", "본체1 (3)"], "cheeks": ["본체1 (4)", "본체1 (5)"],
               "wall_out": "본체1 (6)", "wall_in": "본체1 (7)", "front": "본체1 (8)",
               "back_out": "본체1 (9)", "back_in": "본체1 (10)"}


class Names:
    """Renames the bodies each command creates by reading the run's results is not possible up front, so every
    body is made with an explicit name (body_name / copies renamed through body.rename of the known '(2)')."""


def case_left(r):
    r.c("solid.remove", bodies=STEP_BODIES["plates"] + STEP_BODIES["cheeks"])
    for key, new in (("wall_out", "Wall_L_out"), ("wall_in", "Wall_L_in"), ("front", "Front_L"),
                     ("back_out", "Back_L_out"), ("back_in", "Back_L_in")):
        r.c("body.rename", body=STEP_BODIES[key], name=new)


def case_right(r):
    """Copies of the left case bodies, mirrored about YZ (the right half's inner side is +X), stretched."""
    srcs = [("Wall_L_out", "Wall_R_out"), ("Wall_L_in", "Wall_R_in"), ("Front_L", "Front_R"),
            ("Back_L_out", "Back_R_out"), ("Back_L_out", "Back_R_in")]
    for src, new in srcs:
        r.c("solid.move", bodies=[src], translate=[0, 0, 0], copy=True)
        r.c("body.rename", body=f"{src} (2)", name=f"{new}_tmp")
    for _, new in srcs[:4]:                             # Back_R_in stays unmirrored: it is the left outer block
        r.c("solid.mirror", bodies=[f"{new}_tmp"], plane="YZ")
        r.c("solid.remove", bodies=[f"{new}_tmp"])
        r.c("body.rename", body=f"{new}_tmp (2)", name=new)
    r.c("body.rename", body="Back_R_in_tmp", name="Back_R_in")
    k = 75.0 / 63.0
    r.c("solid.scale", bodies=["Front_R", "Back_R_out", "Back_R_in"], factors=[k, 1, 1], origin=[0, 0, 0])
    r.c("solid.move", bodies=["Wall_R_out"], translate=[-12, 0, 0])   # mirrored outer wall is at -X
    r.c("solid.move", bodies=["Wall_R_in"], translate=[12, 0, 0])


def cheeks(r, half, get):
    four_out = bpc.to_step(get("229E")[:-1] if get("229E")[0] == get("229E")[-1] else get("229E"))
    four_slot = bpc.to_step(get("22A0")[:-1])
    thumb_out = bpc.to_step(get("22B6"), bpc.RIGHT_CHEEK_SHIFT)
    thumb_slot = bpc.to_step(get("22CB"), bpc.RIGHT_CHEEK_SHIFT)
    p = CHEEK_IN[half]
    sides = {"L": [("out", p, four_out, four_slot), ("in", -p - CHEEK_T, four_out, four_slot)],
             "R": [("in", p, four_out, four_slot), ("out", -p - CHEEK_T, thumb_out, thumb_slot)]}[half]
    for tag, x0, outline, slot in sides:
        name = f"Cheek_{half}_{tag}"
        r.sketch(f"{name}_Sk", bpc.yz_plane(x0), [bpc.clean(outline), bpc.clean(slot)])
        r.c("solid.extrude", sketch=f"{name}_Sk", distance=CHEEK_T, operation="new", name=name, body_name=name)


def bones(r, half):
    L = BONE_L[half]
    for i, (g0, g1) in enumerate(bpc.BONE_GROOVES_Y):
        c = (g0 + g1) / 2
        r.c("solid.box", length=L, width=BONE_T, height=10.0, corner=[-L / 2, c - BONE_T / 2, GROOVE_DEPTH - 10.0],
            operation="new", name=f"Bone_{half}_bottom{i}", body_name=f"Bone_{half}_bottom{i}")
    for i, slot in enumerate(BONE_SLOTS):
        poly = Polygon([(x + SIDE_TO_STEP[0], y + SIDE_TO_STEP[1]) for x, y in slot]).buffer(-0.1, join_style=2)
        name = f"Bone_{half}_slant{i}"
        r.sketch(f"{name}_Sk", bpc.yz_plane(-L / 2), [bpc.ring(poly)])
        r.c("solid.extrude", sketch=f"{name}_Sk", distance=L, operation="new", name=name, body_name=name)


def switches(r, half, sec, keys):
    rows = {i: row for i, row in enumerate(sec["rows4"])}
    rows["T"] = sec["thumb_row"]
    for rk, row in rows.items():
        ks = [(x, s) for k, x, s in keys if k == rk]
        if not ks:
            continue
        taper = -math.degrees(math.atan((CAP - CAP_TOP) / 2 / CAP_H))
        for kind, size, lift, h, tp in (
                ("Switch", HOUSING, bpc.PLATE_T, HOUSING_H, None),
                # the path of the keycap's bottom edge when pressed, then the keycap at rest
                ("Keycap", CAP, bpc.PLATE_T + CAP_REST - TRAVEL, TRAVEL, None),
                ("Keycap", CAP, bpc.PLATE_T + CAP_REST, CAP_H, taper)):
            name = f"{kind}_{half}_row{rk}" + ("_top" if tp else "")
            r.sketch(f"{name}_Sk", bpc.row_plane(row, lift), [bpc.rect(x, s, size, size) for x, s in ks])
            extra = {"taper": tp} if tp else {}
            r.c("solid.extrude", sketch=f"{name}_Sk", distance=h, operation="new", name=name,
                body_names=[f"{name}_{j}" for j in range(len(ks))], **extra)


def recipe():
    get = bpc.drawing()
    sec = bpc.sections(get)
    keys = bpc.key_list(get)
    r = bpc.Recipe()
    case_left(r)
    case_right(r)
    groups = {"case": [], "cheeks": [], "bones": [], "plate": [], "cover": [], "switches": [], "keycaps": []}
    for half in ("L", "R"):
        start = len(r.cmds)
        cheeks(r, half, get)
        bones(r, half)
        bpc.build_plate(r, half, sec, keys[half])
        bpc.build_cover(r, half)
        switches(r, half, sec, keys[half])
        made = [c["params"].get("body_name") or c["params"].get("body_names") for c in r.cmds[start:]
                if c["command"] in ("solid.extrude", "solid.box")]
        names = [n for m in made if m for n in (m if isinstance(m, list) else [m])]
        groups["case"] += [f"{w}_{half}_{s}" for w in ("Wall",) for s in ("out", "in")] + \
            [f"Front_{half}", f"Back_{half}_out", f"Back_{half}_in"]
        for n in names:
            key = ("cheeks" if n.startswith("Cheek") else "bones" if n.startswith("Bone") else
                   "plate" if n.startswith("Plate") else "cover" if n.startswith("Cover") else
                   "switches" if n.startswith("Switch") else "keycaps")
            groups[key].append(n)
    right = [n for g in groups.values() for n in g if "_R" in n]
    r.c("solid.move", bodies=right, translate=[RIGHT_DX, 0, 0])
    return r, groups


def run(cmds, extra_args=(), save=None):
    with TemporaryDirectory() as work:
        path, out = Path(work) / "a.json", Path(work) / "o.json"
        path.write_text(json.dumps(cmds), encoding="utf-8")
        argv = [CLI, "run", str(path), "--in", str(bpc.CASE_STEP), "--results", "--json-out", str(out)]
        if save:
            argv += ["--save", str(save)]
        subprocess.run(argv + list(extra_args), check=True, stdout=subprocess.DEVNULL)
        return json.loads(out.read_text(encoding="utf-8"))


def snapshot(work, cmds, out, camera, bodies=(), section=None, size=(1600, 1000)):
    """Start one render; `work` is a folder that outlives the process (the script file is read from it)."""
    path = Path(work) / f"{out.stem}.json"
    path.write_text(json.dumps(cmds), encoding="utf-8")
    argv = [CLI, "snapshot", str(path), "--in", str(bpc.CASE_STEP), "--out", str(out), "--camera",
            json.dumps(camera), "--width", str(size[0]), "--height", str(size[1]), "--no-grid", "--no-axes"]
    for b in bodies:
        argv += ["--body", b]
    if section:
        argv += ["--section", section]
    return subprocess.Popen(argv, stdout=subprocess.DEVNULL)


COLORS = {"case": "#b08a62", "cheeks": "#2a2a2a", "bones": "#8a6a48", "plate": "#3d4f7a", "cover": "#4a6fa8",
          "switches": "#c8c8c8", "keycaps": "#e8e4da"}


def view(r, groups, hide=(), right=True, extra=()):
    """Commands and --body looks for one picture: hidden groups (and the right half) are removed, not made
    see-through, so they leave no outlines."""
    gone = [n for g, ns in groups.items() for n in ns if g in hide or (not right and "_R" in n)]
    cmds = r.cmds + list(extra) + ([{"command": "solid.remove", "params": {"bodies": gone}}] if gone else [])
    looks = [f"{n}:color={COLORS[g]}" for g, ns in groups.items() for n in ns if n not in gone]
    return cmds, looks


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--no-images", action="store_true")
    args = ap.parse_args()
    r, groups = recipe()

    everything = [n for g in groups.values() for n in g]
    res = run(r.cmds + [{"command": "inspect.measure", "params": {}},
                        {"command": "inspect.interference", "params": {"bodies": everything}}], save=OUTPUT)
    OUTPUT.with_suffix(".sc.bak").unlink(missing_ok=True)
    bodies = {b["name"]: b for b in res[-2]["bodies"]}
    missing = [n for n in everything if n not in bodies]
    group_of = {n: g for g, ns in groups.items() for n in ns}
    allowed = {frozenset(("switches", "keycaps")), frozenset(("plate", "switches"))}
    hard, soft, real = [], [], []
    for x in res[-1]["interferences"]:
        ga, gb = group_of.get(x["a"], "?"), group_of.get(x["b"], "?")
        if frozenset((ga, gb)) in allowed or (ga == gb and ga in ("case",)):
            continue
        a_, b_ = x["a"], x["b"]
        same = lambda n: (n.rsplit("_", 1)[0].replace("_top", ""), n.rsplit("_", 1)[1])
        if a_.startswith("Keycap") and b_.startswith("Keycap") and same(a_) == same(b_):
            continue                                    # a keycap's own two pieces
        item = (a_, b_, x["volume_mm3"], [round(v, 1) for v in x["bbox"]["min"] + x["bbox"]["max"]])
        pair = {ga, gb}
        if "bones" in pair or pair == {"cheeks", "case"}:
            soft.append(item)                           # case parts the STEP draws differently from the real ones
        elif "case" in pair:
            real.append(item)                           # plate, switch or keycap against the plywood: see on the real case
        else:
            hard.append(item)
    print(f"{len(bodies)} bodies; missing {missing}")
    for a, b, v, bb in hard:
        print(f"OVERLAP {a} / {b}: {v:.2f} mm3 bbox {bb}")
    for a, b, v, bb in real:
        print(f"CHECK ON THE REAL CASE {a} / {b}: {v:.2f} mm3 bbox {bb}")
    for a, b, v, bb in soft:
        print(f"STEP vs real (bone slots read from the side drawing, 4 mm wall pocket) {a} / {b}: {v:.2f} mm3")
    if missing or hard:
        raise SystemExit("check failed")
    print("clear: plate in the cheek slots, keycaps (bottomed out) clear of cheeks, walls and each other")

    if args.no_images:
        return
    IMAGES.mkdir(exist_ok=True)
    L = lambda ns: [n for n in ns if "_L" in n]
    gl = {g: L(ns) for g, ns in groups.items()}
    front_iso = {"target": [RIGHT_DX / 2, 100, 25], "yaw": 3.14159 - 0.35, "pitch": 0.6, "distance": 520}
    half_iso = {"target": [0, 100, 25], "yaw": 3.14159 - 0.6, "pitch": 0.55, "distance": 330}
    explode = [{"command": "solid.move", "params": {"bodies": ["Wall_L_out"], "translate": [70, 0, 0]}},
               {"command": "solid.move", "params": {"bodies": ["Cheek_L_out"], "translate": [35, 0, 0]}},
               {"command": "solid.move", "params": {"bodies": ["Wall_L_in"], "translate": [-70, 0, 0]}},
               {"command": "solid.move", "params": {"bodies": ["Cheek_L_in"], "translate": [-35, 0, 0]}},
               {"command": "solid.move", "params": {"bodies": gl["cover"], "translate": [0, 0, -45]}},
               {"command": "solid.move", "params": {"bodies": gl["plate"] + gl["switches"] + gl["keycaps"],
                                                    "translate": [0, 0, 45]}}]
    work_dir = TemporaryDirectory()
    work = work_dir.name
    slide = [{"command": "solid.move", "params": {"bodies": ["Cheek_L_out"], "translate": [18, 0, 0]}},
             {"command": "solid.move", "params": {"bodies": ["Cheek_L_in"], "translate": [-18, 0, 0]}}]
    shots = [
        ("assembly-both", dict(), front_iso, None, (1600, 1000)),
        ("assembly-explode-left", dict(right=False, extra=explode),
         {"target": [0, 100, 30], "yaw": 3.14159 - 0.6, "pitch": 0.45, "distance": 480}, None, (1600, 1000)),
        ("assembly-step-switches", dict(right=False, hide=("case", "cheeks", "bones", "cover", "keycaps")),
         half_iso, None, (1600, 1000)),
        ("assembly-step-cheeks", dict(right=False, hide=("case", "bones", "cover", "keycaps"), extra=slide),
         half_iso, None, (1600, 1000)),
        ("assembly-step-case", dict(right=False, hide=("keycaps", "cover"), extra=explode[:2]),
         {"target": [20, 100, 25], "yaw": 3.14159 - 0.7, "pitch": 0.55, "distance": 400}, None, (1600, 1000)),
        ("assembly-section", dict(right=False),
         {"target": [0, 103, 30], "yaw": -1.5707963, "pitch": 0, "distance": 260}, "x=-40", (1600, 800)),
        ("assembly-bottom", dict(),
         {"target": [RIGHT_DX / 2, 103, 0], "yaw": 3.14159, "pitch": -1.5707963, "distance": 560}, None, (1600, 1000)),
    ]
    jobs = []
    for name, opts, cam, sect, size in shots:
        cmds, lk = view(r, groups, **opts)
        jobs.append(snapshot(work, cmds, IMAGES / f"{name}.png", cam, lk, section=sect, size=size))
    for j in jobs:
        j.wait()
    work_dir.cleanup()
    if any(j.returncode for j in jobs):
        raise SystemExit("a render failed")
    print("images: " + ", ".join(p.name for p in sorted(IMAGES.glob("assembly-*.png"))))


if __name__ == "__main__":
    main()
