"""Build the 46sp print model (plate and case for each half) from the r3 drawing.

The row profile comes from the r3 cheek slot (22A0): each row plate's cross-section is
copied, and neighbouring rows are joined where their bottom lines meet. Key positions
along X and along each row come from the r3 plates, changed to the 46-key layout:
left row 3 loses its outer key, right rows 1-2 get seven keys at 1u, and the right
cross sits on rows 3 (up) and 4 (left, down, right).

World axes: X to the right (r3 drawing X), Y to the back, Z up. Z = 0 is the case floor
underside. Every length is in mm.
"""

import argparse
import json
import math
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory

import ezdxf

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "source/46sp_plate_r3.converted.dxf"
OUTPUT = ROOT / "model/46sp-print.sc"
CLI_DEFAULT = r"C:\Program Files\SolidCraft\solidcraft-cli.exe"

U = 19.05                # key pitch
PLATE_T = 5.0            # plate thickness (r3: 5T)
LATCH_T = 1.5            # switch latch layer at the plate top
HOLE = 14.0              # switch hole (46es coupon start value)
RELIEF = 16.5            # clip relief under the latch layer (46es)
PLATE_BOTTOM_MIN_Z = 10.0  # lowest point of the plate underside (switch pins + diodes + wires)
TILT_DEG = 0.0           # turn of the whole profile about X; + lifts the back
WALL = 2.0
FLOOR = 2.0

# Plate legs: vertical columns under the plate with a stock brass insert (D5 x 4) in the
# lower end; a stock M3x10 button head goes up through a floor pad of the case into it.
LEG_D, LEG_BOTTOM_Z, INSERT_HOLE_D, INSERT_HOLE_DEPTH, PILOT_D, PILOT_DEPTH = 7.5, 4.2, 4.2, 5.0, 3.0, 4.0
PAD_D, PAD_TOP_Z, CB_D, CB_DEPTH, SCREW_D, SCREW_L = 11.0, 4.0, 6.4, 2.0, 3.4, 10.0
LEG_CLEAR = 0.3

# RP2040-Zero (23.5 x 18 PCB, USB-C on a short edge) and a 3.5 mm panel jack.
MCU_L, MCU_W, MCU_GAP, MCU_WALL_T, MCU_WALL_H, MCU_BACK_GAP = 23.5, 18.0, 0.2, 1.2, 2.0, 1.0
USB_OPEN_W, USB_OPEN_H, USB_CENTER_ABOVE_FLOOR = 11.0, 6.5, 3.4
JACK_D, JACK_FROM_BACK, JACK_ABOVE_FLOOR = 6.2, 6.5, 5.5

ROW_HANDLES = ["1384", "138C", "23BE", "132E", "1695", "1696", "23DC", "1771", "178A"]
CHEEK_SLOT = "22A0"
# Plate bottom segments in the cheek slot, from the back row to the thumb row.
SLOT_ROWS = [(2, 3), (4, 5), (6, 7), (8, 9)]   # vertex indices of 22A0 (lower boundary)

# legs: (x, ("line", row)) = under that row's key line. Legs stand only where no switch is
# beside them across X (outer margins, the empty outer end of left row 3, gaps in the thumb rows).
HALVES = {
    "L": dict(x=(15.0, 148.0),
              legs=[(23.5, ("line", 0)), (23.5, ("line", 1)), (40, ("line", 2)), (48, ("line", 3)),
                    (105, ("line", 3)), (137, ("line", 3))],
              mcu_x=120.0, jack_wall="+x"),
    "R": dict(x=(170.0, 337.0),
              legs=[(178, ("line", 3)), (261.5, ("line", 3)), (281.5, ("line", 2)), (320, ("line", 0)),
                    (320, ("line", 1)), (320, ("line", 2))],
              mcu_x=200.0, jack_wall="-x"),
}


# ---------------------------------------------------------------- geometry
def sub(a, b): return (a[0] - b[0], a[1] - b[1])
def add(a, b): return (a[0] + b[0], a[1] + b[1])
def mul(a, k): return (a[0] * k, a[1] * k)
def unit(a):
    n = math.hypot(*a)
    return (a[0] / n, a[1] / n)


def line_meet(p, d, q, e):
    """Intersection of lines p + s d and q + t e."""
    den = d[0] * e[1] - d[1] * e[0]
    s = ((q[0] - p[0]) * e[1] - (q[1] - p[1]) * e[0]) / den
    return add(p, mul(d, s))


def read_drawing():
    doc = ezdxf.readfile(SOURCE)
    get = lambda h: [(float(x), float(y)) for x, y in doc.entitydb.get(h).get_points("xy")]
    holes = []
    for e in doc.modelspace().query("LWPOLYLINE"):
        pts = [(float(x), float(y)) for x, y in e.get_points("xy")]
        xs, ys = [p[0] for p in pts], [p[1] for p in pts]
        if abs(max(xs) - min(xs) - 14) < 0.03 and abs(max(ys) - min(ys) - 14) < 0.03:
            holes.append(((max(xs) + min(xs)) / 2, (max(ys) + min(ys)) / 2))
    return get, holes


def profile(slot):
    """Rows in the YZ plane (start = r3 back edge, unit direction t to the front, upward normal n)
    and the plate band outline: bottom chain and top chain, both ends cut vertical."""
    rows = []
    for i, j in SLOT_ROWS:
        (u0, v0), (u1, v1) = slot[i], slot[j]
        rows.append([(-u0, v0), (-u1, v1)])            # Y = -u puts the back row at high Y
    tilt = math.radians(TILT_DEG)
    rot = lambda p: (p[0] * math.cos(tilt) - p[1] * math.sin(tilt),
                     p[0] * math.sin(tilt) + p[1] * math.cos(tilt))
    out = []
    for s, e in ([rot(p) for p in r] for r in rows):
        t = unit(sub(e, s))
        n = (t[1], -t[0]) if -t[0] > 0 else (-t[1], t[0])
        out.append(dict(start=s, end=e, t=t, n=n))
    up = lambda r: add(r["start"], mul(r["n"], PLATE_T))
    bottom = [out[0]["start"]]
    top = [line_meet(up(out[0]), out[0]["t"], out[0]["start"], (0.0, 1.0))]   # vertical back end
    for a, b in zip(out, out[1:]):
        bottom.append(line_meet(a["start"], a["t"], b["start"], b["t"]))
        top.append(line_meet(up(a), a["t"], up(b), b["t"]))
    bottom.append(out[-1]["end"])
    top.append(line_meet(up(out[-1]), out[-1]["t"], out[-1]["end"], (0.0, 1.0)))
    dy = -bottom[-1][0]                                   # front end of the thumb row at Y = 0
    dz = PLATE_BOTTOM_MIN_Z - min(p[1] for p in bottom)
    sh = lambda p: (p[0] + dy, p[1] + dz)
    for r in out:
        r["start"], r["end"] = sh(r["start"]), sh(r["end"])
    return out, [sh(p) for p in bottom], [sh(p) for p in top]


def bottom_z(bottom, y):
    """Plate underside height at Y (the underside does not depend on X)."""
    for (y0, z0), (y1, z1) in zip(bottom, bottom[1:]):
        if min(y0, y1) - 1e-9 <= y <= max(y0, y1) + 1e-9:
            return z0 + (z1 - z0) * (y - y0) / (y1 - y0)
    raise ValueError(f"Y {y} outside the plate")


def keys(get, holes):
    """Per half: list of (row index, x, offset along the row from its r3 back edge)."""
    def strip(h):
        pts = get(h)
        xs, ys = [p[0] for p in pts], [p[1] for p in pts]
        return min(xs), max(xs), min(ys), max(ys)

    def in_strip(h):
        x0, x1, y0, y1 = strip(h)
        return sorted((x, y) for x, y in holes if x0 < x < x1 and y0 < y < y1)

    out = {"L": [], "R": []}
    for half, handles in (("L", ROW_HANDLES[0:4]), ("R", ROW_HANDLES[4:8])):
        for row, h in enumerate(handles):
            ytop = strip(h)[3]
            ks = [(x, ytop - y) for x, y in in_strip(h)]
            if half == "L" and row == 2:
                ks = ks[1:]                                       # no outer key on row 3
            if half == "R" and row in (0, 1):
                ks = ks[:5] + [(ks[0][0] + U * c, ks[0][1]) for c in (5, 6)]
            out[half] += [(row, x, s) for x, s in ks]
    cross = in_strip("178A")                  # the top key joins row 3, the other three row 4
    up = max(cross, key=lambda p: p[1])
    s2 = next(s for r, x, s in out["R"] if r == 2)
    s3 = next(s for r, x, s in out["R"] if r == 3)
    out["R"].append((2, up[0], s2))
    out["R"] += [(3, x, s3) for x, y in cross if (x, y) != up]
    assert len(out["L"]) == 20 and len(out["R"]) == 26, (len(out["L"]), len(out["R"]))
    return out


# ---------------------------------------------------------------- recipe
def dxf_lines(loops):
    tags = ["0", "SECTION", "2", "ENTITIES"]
    for loop in loops:
        for (x0, y0), (x1, y1) in zip(loop, loop[1:] + loop[:1]):
            tags += ["0", "LINE", "8", "0", "10", f"{x0:.6f}", "20", f"{y0:.6f}",
                     "11", f"{x1:.6f}", "21", f"{y1:.6f}"]
    return "\n".join(tags + ["0", "ENDSEC", "0", "EOF", ""])


class Recipe:
    def __init__(self):
        self.cmds = []

    def c(self, command, **params):
        self.cmds.append({"command": command, "params": params})

    def sketch(self, name, plane, loops):
        self.c("sketch.create", name=name, plane=plane)
        self.c("sketch.insert_dxf", text=dxf_lines(loops))
        n = sum(len(l) for l in loops)
        self.c("sketch.constraint.fix", entities=[f"l{i}" for i in range(1, n + 1)], fixed=True)
        self.c("sketch.solve")
        self.c("sketch.finish")


def rect(cx, cy, w, h):
    return [(cx - w / 2, cy - h / 2), (cx + w / 2, cy - h / 2),
            (cx + w / 2, cy + h / 2), (cx - w / 2, cy + h / 2)]


def yz_plane(x):
    return {"origin": [x, 0, 0], "x_dir": [0, 1, 0], "y_dir": [0, 0, 1]}


def row_plane(row, lift):
    """Sketch plane on a row surface: sketch x = world X, sketch y = back along the row."""
    o = add(row["start"], mul(row["n"], lift))
    back = mul(row["t"], -1)
    return {"origin": [0, o[0], o[1]], "x_dir": [1, 0, 0], "y_dir": [0, back[0], back[1]]}


def leg_points(cfg, rows, bottom, key_list):
    out = []
    for x, (kind, k) in cfg["legs"]:
        if kind == "line":
            s = next(s for r, xx, s in key_list if r == k)
            y = add(rows[k]["start"], mul(rows[k]["t"], s))[0]
        else:
            y = bottom[k + 1][0]
        out.append((x, y))
    return out


def build_half(r, half, cfg, rows, bottom, top, key_list):
    x0, x1 = cfg["x"]
    plate, case = f"Plate_{half}", f"Case_{half}"
    yb, yf = bottom[0][0], bottom[-1][0]
    legs = leg_points(cfg, rows, bottom, key_list)

    # plate: band, legs, then switch holes and clip reliefs (one sketch per row), then insert holes
    r.sketch(f"{plate}_Section", yz_plane(x0), [bottom + top[::-1]])
    r.c("solid.extrude", sketch=f"{plate}_Section", distance=x1 - x0, operation="new",
        name=f"{plate}_Band", body_name=plate)
    for k, (x, y) in enumerate(legs):
        r.c("solid.cylinder", diameter=LEG_D, height=bottom_z(bottom, y) + 2 - LEG_BOTTOM_Z,
            base=[x, y, LEG_BOTTOM_Z], axis="Z", operation="join", targets=[plate], name=f"{plate}_Leg{k}")
    for i, row in enumerate(rows):
        ks = [(x, s) for ri, x, s in key_list if ri == i]
        r.sketch(f"{plate}_Holes{i}", row_plane(row, PLATE_T), [rect(x, -s, HOLE, HOLE) for x, s in ks])
        r.c("solid.extrude", sketch=f"{plate}_Holes{i}", distance=PLATE_T + 1, direction="negative",
            start_offset=0.5, operation="cut", targets=[plate], name=f"{plate}_HoleCut{i}")
        r.sketch(f"{plate}_Relief{i}", row_plane(row, 0), [rect(x, -s, RELIEF, RELIEF) for x, s in ks])
        r.c("solid.extrude", sketch=f"{plate}_Relief{i}", distance=PLATE_T - LATCH_T + 0.5,
            start_offset=-0.5, operation="cut", targets=[plate], name=f"{plate}_ReliefCut{i}")
    for k, (x, y) in enumerate(legs):
        r.c("solid.cylinder", diameter=INSERT_HOLE_D, height=INSERT_HOLE_DEPTH + 0.5,
            base=[x, y, LEG_BOTTOM_Z - 0.5], axis="Z", operation="cut", targets=[plate],
            name=f"{plate}_InsertHole{k}")
        r.c("solid.cylinder", diameter=PILOT_D, height=PILOT_DEPTH,
            base=[x, y, LEG_BOTTOM_Z + INSERT_HOLE_DEPTH - 0.01], axis="Z", operation="cut",
            targets=[plate], name=f"{plate}_Pilot{k}")

    # case: block under the plate, cavity, floor pads with counterbored screw holes
    r.sketch(f"{case}_Section", yz_plane(x0), [[(yb, 0.0)] + bottom + [(yf, 0.0)]])
    r.c("solid.extrude", sketch=f"{case}_Section", distance=x1 - x0, operation="new",
        name=f"{case}_Block", body_name=case)
    zhi = max(p[1] for p in top) + 20
    r.sketch(f"{case}_CavitySection", yz_plane(x0 + WALL),
             [[(yb - WALL, FLOOR), (yf + WALL, FLOOR), (yf + WALL, zhi), (yb - WALL, zhi)]])
    r.c("solid.extrude", sketch=f"{case}_CavitySection", distance=x1 - x0 - 2 * WALL, operation="cut",
        targets=[case], name=f"{case}_Cavity")
    for k, (x, y) in enumerate(legs):
        r.c("solid.cylinder", diameter=PAD_D, height=PAD_TOP_Z - FLOOR + 0.01, base=[x, y, FLOOR - 0.01],
            axis="Z", operation="join", targets=[case], name=f"{case}_Pad{k}")
        r.c("solid.cylinder", diameter=CB_D, height=CB_DEPTH + 0.5, base=[x, y, -0.5], axis="Z",
            operation="cut", targets=[case], name=f"{case}_Counterbore{k}")
        r.c("solid.cylinder", diameter=SCREW_D, height=PAD_TOP_Z + 1, base=[x, y, -0.5], axis="Z",
            operation="cut", targets=[case], name=f"{case}_ScrewHole{k}")

    # RP2040-Zero cradle at the back wall, USB-C through the back wall
    mx = cfg["mcu_x"]
    inner_back = yb - WALL
    pcb_back = inner_back - MCU_BACK_GAP
    py0 = pcb_back - MCU_W - MCU_GAP
    gx0, gx1 = mx - MCU_L / 2 - MCU_GAP, mx + MCU_L / 2 + MCU_GAP
    t = MCU_WALL_T
    for name, (cx0, cx1, cy0, cy1) in {
            "Left": (gx0 - t, gx0, py0 - t, inner_back), "Right": (gx1, gx1 + t, py0 - t, inner_back),
            "Front": (gx0 - t, gx1 + t, py0 - t, py0)}.items():
        r.c("solid.box", length=cx1 - cx0, width=cy1 - cy0 + 0.01, height=MCU_WALL_H + 0.01,
            corner=[cx0, cy0, FLOOR - 0.01], operation="join", targets=[case], name=f"{case}_Cradle{name}")
    r.c("solid.box", length=USB_OPEN_W, width=WALL + 2, height=USB_OPEN_H,
        corner=[mx - USB_OPEN_W / 2, inner_back - 1, FLOOR + USB_CENTER_ABOVE_FLOOR - USB_OPEN_H / 2],
        operation="cut", targets=[case], name=f"{case}_UsbOpening")

    # 3.5 mm jack through the inner side wall, near the back
    jx = x1 - WALL - 1 if cfg["jack_wall"] == "+x" else x0 - 1
    jack = (jx, yb - JACK_FROM_BACK, FLOOR + JACK_ABOVE_FLOOR)
    r.c("solid.cylinder", diameter=JACK_D, height=WALL + 2, base=list(jack), axis="X", operation="cut",
        targets=[case], name=f"{case}_JackHole")
    return dict(legs=legs, mcu=(gx0 - t, gx1 + t, py0 - t, inner_back), jack=jack)


# ---------------------------------------------------------------- checks
def area(poly):
    return 0.5 * abs(sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(poly, poly[1:] + poly[:1])))


def leg_volume_below(bottom, y, z0, d, n=2000):
    """Leg volume between z0 and the plate underside, by a midpoint rule across the circle."""
    rr, total = d / 2, 0.0
    for i in range(n):
        yy = y - rr + (i + 0.5) * d / n
        chord = 2 * math.sqrt(max(rr * rr - (yy - y) ** 2, 0))
        total += chord * (bottom_z(bottom, yy) - z0) * d / n
    return total


def expected_plate_volume(bottom, top, x0, x1, nkeys, legs):
    per_key = HOLE ** 2 * PLATE_T + (RELIEF ** 2 - HOLE ** 2) * (PLATE_T - LATCH_T)
    per_leg_hole = math.pi / 4 * (INSERT_HOLE_D ** 2 * INSERT_HOLE_DEPTH + PILOT_D ** 2 * PILOT_DEPTH)
    v = area(bottom + top[::-1]) * (x1 - x0) - nkeys * per_key
    for x, y in legs:
        v += leg_volume_below(bottom, y, LEG_BOTTOM_Z, LEG_D) - per_leg_hole
    return v


def keepout(row, s, depth):
    """Switch keep-out cross-section in (Y, Z): the hole outline from the plate top down `depth`."""
    c = add(add(row["start"], mul(row["t"], s)), mul(row["n"], PLATE_T))
    return [add(add(c, mul(row["t"], ds)), mul(row["n"], dn))
            for ds, dn in ((-HOLE / 2, 0), (HOLE / 2, 0), (HOLE / 2, -depth), (-HOLE / 2, -depth))]


def check(rows, bottom, key_list, info, cfg, half):
    """Keep-outs (hole outline down to pins + diodes + wires) against the floor, legs, cradle, jack."""
    from shapely.geometry import Polygon, box
    depth = PLATE_T + 3.3 + 3.0
    x0, x1 = cfg["x"]
    yb, yf = bottom[0][0], bottom[-1][0]
    problems = []
    lr = LEG_D / 2 + LEG_CLEAR
    for x, y in info["legs"]:
        if not (x0 + WALL + lr <= x <= x1 - WALL - lr and yf + WALL + lr <= y <= yb - WALL - lr):
            problems.append(f"{half} leg x{x:.1f} y{y:.1f}: closer than {LEG_CLEAR} to a wall")
        if LEG_BOTTOM_Z + INSERT_HOLE_DEPTH + PILOT_DEPTH > bottom_z(bottom, y) + PLATE_T - 1.0:
            problems.append(f"{half} leg x{x:.1f}: pilot within 1 mm of the plate top")
    gx0, gx1, gy0, gy1 = info["mcu"]
    jx, jy, jz = info["jack"]
    for ri, x, s in key_list:
        ko = Polygon(keepout(rows[ri], s, depth))
        if ko.bounds[1] < FLOOR + 0.5:
            problems.append(f"{half} key x{x:.1f} row{ri + 1}: keep-out reaches Z {ko.bounds[1]:.2f}")
        rel = Polygon(keepout(rows[ri], s, PLATE_T)).buffer((RELIEF - HOLE) / 2, join_style=2)
        for lx, ly in info["legs"]:
            if abs(lx - x) < HOLE / 2 + LEG_D / 2 + LEG_CLEAR and ko.intersects(
                    box(ly - lr, LEG_BOTTOM_Z, ly + lr, 99)):
                problems.append(f"{half} key x{x:.1f} row{ri + 1}: leg at x{lx}")
            if abs(lx - x) < RELIEF / 2 + LEG_D / 2 and rel.intersects(
                    box(ly - LEG_D / 2, 0, ly + LEG_D / 2, 99)):
                problems.append(f"{half} key x{x:.1f} row{ri + 1}: leg reaches the relief pocket")
        if x + HOLE / 2 > gx0 and x - HOLE / 2 < gx1 and ko.intersects(box(gy0, 0, gy1, FLOOR + 1.6 + 3.3)):
            problems.append(f"{half} key x{x:.1f} row{ri + 1}: keep-out over the controller")
        if abs(x - jx) < HOLE / 2 + 15 and ko.intersects(box(jy - 4, jz - 4, jy + 4, jz + 4)):
            problems.append(f"{half} key x{x:.1f} row{ri + 1}: keep-out at the jack")
    return problems


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--cli", default=CLI_DEFAULT)
    ap.add_argument("--out", type=Path, default=OUTPUT)
    ap.add_argument("--recipe", type=Path, help="also write the command list here")
    args = ap.parse_args()

    get, holes = read_drawing()
    rows, bottom, top = profile(get(CHEEK_SLOT))
    key_lists = keys(get, holes)

    r = Recipe()
    expected, problems = {}, []
    for half, cfg in HALVES.items():
        info = build_half(r, half, cfg, rows, bottom, top, key_lists[half])
        expected[f"Plate_{half}"] = expected_plate_volume(bottom, top, *cfg["x"], len(key_lists[half]),
                                                          info["legs"])
        problems += check(rows, bottom, key_lists[half], info, cfg, half)

    print("plate underside (Y, Z):", [(round(y, 2), round(z, 2)) for y, z in bottom])
    print("plate top       (Y, Z):", [(round(y, 2), round(z, 2)) for y, z in top])
    for i, row in enumerate(rows):
        print(f"row {i + 1}: surface tilt {math.degrees(math.atan2(-row['n'][0], row['n'][1])):+.2f} deg "
              f"(+ = back edge higher)")
    if args.recipe:
        args.recipe.write_text(json.dumps(r.cmds), encoding="utf-8")
    with TemporaryDirectory() as work:
        recipe, design, meas = (Path(work) / n for n in ("build.json", args.out.name, "measure.json"))
        recipe.write_text(json.dumps(r.cmds), encoding="utf-8")
        subprocess.run([args.cli, "run", str(recipe), "--save", str(design), "--json-out", str(meas)],
                       check=True)
        result = json.loads(meas.read_text(encoding="utf-8"))
        bodies = {b["name"]: b for b in result["bodies"]}
        args.out.write_bytes(design.read_bytes())

    ok = set(bodies) == {"Plate_L", "Plate_R", "Case_L", "Case_R"}
    for name, b in sorted(bodies.items()):
        line = f"{name}: closed={b.get('closed')} volume={b['volume_mm3']:.1f} mm3"
        if name in expected:
            line += f" (expected {expected[name]:.1f})"
            ok &= math.isclose(b["volume_mm3"], expected[name], rel_tol=2e-4)
        ok &= bool(b.get("closed"))
        print(line, "bbox", b.get("bbox"))
    for p in problems:
        print("CLEARANCE:", p)
    if not ok or problems:
        raise SystemExit("check failed")
    print(f"{args.out.name}: 4 closed bodies, volumes and clearances pass")


if __name__ == "__main__":
    main()
