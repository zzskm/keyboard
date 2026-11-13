"""Build the 46sp print parts that go into the existing plywood case: a plate and a bottom cover per half.

Plate: one MJF piece per half in place of the r3 acrylic row strips (and their ribs). Its cross-section is the
r3 cheek slot (22A0 for the 4-row ends, 22CB for the right outer end: rows 1-2 and the 15 deg thumb plane) shrunk
by 0.25 mm all round, so it is 5.0 thick in the 5.5 slot and both ends slide into the existing acrylic cheeks.
Holes, clip reliefs (46es values) and key positions follow the 46-key drawing (tools/plate_46key.py). The left
plate carries the logo `kb46sp/26` (46es style, Xifiction) engraved in the empty outer end of row 4.

Cover: a flat plate under the case bottom (Z = 0), fixed with countersunk wood screws into the side walls and the
front block, clear of the bone bar grooves.

Coordinates are those of source/46sp_r3_left.step: X across the half (0 = middle of the plate, +X = the user's left), Y to the front
(0 = back face), Z up (0 = case bottom). The right half uses the same frame for its own case; its case width
comes from the right bone bars (158) because there is no right STEP yet.

    python 46sp/tools/build_plate_cover.py            # ~1 min, writes model/46sp-plate-cover.sc and the STLs
    python 46sp/tools/build_plate_cover.py --check-case   # also checks the left parts against the case STEP
    python 46sp/tools/build_plate_cover.py --font Xifiction.ttf   # rewrite the logo glyph outlines first
"""

import argparse
import json
import math
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory

import ezdxf
from shapely import affinity
from shapely.geometry import LineString, MultiPoint, Polygon, box
from shapely.ops import split, unary_union

ROOT = Path(__file__).resolve().parents[1]
DRAWING = ROOT / "source/46sp_plate_r3.converted.dxf"
SWITCHES = ROOT / "model/46key-switches.json"
CASE_STEP = ROOT / "source/46sp_r3_left.step"
FONT_DATA = ROOT / "tools/plate_logo_xifiction.json"
OUTPUT = ROOT / "model/46sp-plate-cover.sc"
PRINT_DIR = ROOT / "model/print"
CLI_DEFAULT = r"C:\Program Files\SolidCraft\solidcraft-cli.exe"

# r3 drawing -> STEP (Y, Z): the cheek 229E turned -13 deg about the drawing origin and moved; this matches the
# STEP cheek section at X 65 and puts the three STEP acrylic plates wholly inside the slot (checked 2026-11-13).
DRAW_TURN, DRAW_DY, DRAW_DZ = -13.0, 9.7206, -26.1899
RIGHT_CHEEK_SHIFT = 157.83 - 16.12   # 22B6/22CB are drawn this far right of 229E/22A0

SLOT_CLEAR = 0.25        # per side: 5.5 slot -> 5.0 plate
PLATE_T = 5.0
LATCH_T = 1.5
HOLE = 14.0
RELIEF = 16.5
CAP = 18.2

HALVES = {               # plate ends (drawing X), drawing X of the plate middle, case half width, screws
    "L": dict(x=(15.0, 148.0), mid=81.5, case_half=75.0, wall_x=69.0),
    "R": dict(x=(170.0, 327.0), mid=248.5, case_half=87.0, wall_x=81.0),
}
R_SPANS = (255.0, 274.75)
SPAN_OVERLAP = 0.3  # right plate: rows 1-4 up to R3's end, rows 1-3 + lower thumb up to R2's end, then thumb

LOGO_TEXT = "kb46sp/26"
LOGO_HEIGHT = 4.0        # glyph cell (font units 0..1600): stroke 1.0, narrowest rib 0.5
LOGO_DEPTH = 0.8
LOGO_ROW, LOGO_X = 3, (24.0, 61.0)     # left row 4, between the first keycap (X 22.5) and the cheek (62.5)
CURVE_SEGMENTS = 6

COVER_T = 3.0
COVER_Y = (4.0, 205.0)   # inside the rounded bottom edges of the back and front faces
COVER_SIDE_IN = 0.3      # cover sides this far inside the case sides
SCREW_D, CS_D, CS_ANGLE = 3.4, 6.6, 90.0     # wood screw 3 mm countersunk
SCREWS_Y_WALL, SCREW_FRONT = (45.0, 125.0), (162.0, 0.47)   # (Y, X as a share of the inner half width)
BONE_GROOVES_Y = [(14.72, 20.93), (178.64, 184.84), (189.84, 196.04)]


# ---------------------------------------------------------------- drawing
def drawing():
    doc = ezdxf.readfile(DRAWING)
    return lambda h: [(float(x), float(y)) for x, y in doc.entitydb.get(h).get_points("xy")]


def to_step(points, shift=0.0):
    out = []
    a = math.radians(DRAW_TURN)
    for x, y in points:
        x -= shift
        out.append((x * math.cos(a) - y * math.sin(a) + DRAW_DY, x * math.sin(a) + y * math.cos(a) + DRAW_DZ))
    return out


def rows_of(slot, pairs):
    """Rows from the slot's lower chain: back point (bottom of the plate), unit t to the front, upward unit n."""
    out = []
    for i, j in pairs:
        b, e = slot[i], slot[j]
        L = math.dist(b, e)
        t = ((e[0] - b[0]) / L, (e[1] - b[1]) / L)
        n = (-t[1], t[0]) if t[0] > 0 else (t[1], -t[0])
        bottom = (b[0] + n[0] * SLOT_CLEAR, b[1] + n[1] * SLOT_CLEAR)
        out.append(dict(back=bottom, t=t, n=n, length=L))
    return out


def at(row, s, lift):
    return (row["back"][0] + row["t"][0] * s + row["n"][0] * lift,
            row["back"][1] + row["t"][1] * s + row["n"][1] * lift)


def sections(get):
    """Plate cross-sections in STEP (Y, Z) and the rows they carry."""
    s4 = to_step(get("22A0")[:-1])
    st = to_step(get("22CB"), RIGHT_CHEEK_SHIFT)
    four = Polygon(s4).buffer(-SLOT_CLEAR, join_style=2)
    thumb = Polygon(st).buffer(-SLOT_CLEAR, join_style=2)
    rows4 = rows_of(s4, [(2, 3), (4, 5), (6, 7), (8, 9)])
    rowst = rows_of(st, [(3, 4), (5, 6), (7, 8)])
    for a, b in zip(rows4[:2], rowst[:2]):           # rows 1-2 are the same in both cheeks
        assert math.dist(a["back"], b["back"]) < 0.02 and abs(a["length"] - b["length"]) < 0.02

    # The right plate is joined from pieces that each keep a polygon's own corners where they meet another piece
    # (a join of nearly coincident faces is refused): rows 1-4 to R3's end, rows 1-3 to R2's end, the thumb
    # plane's lower part (from 20.9 back from its front... i.e. s >= 20.9) from R3's end out, rows 1-2 and the
    # thumb plane's upper part from R2's end out, and two hull pieces that bridge the steps between them.
    r1, r2, r3, tp = rows4[1], rows4[2], rows4[3], rowst[2]
    corner = lambda g, p: min(g.exterior.coords, key=lambda q: math.dist(q, p))
    def thumb_part(s0, s1):
        cuts = [LineString([at(tp, s, -3), at(tp, s, PLATE_T + 3)]) for s in (s0, s1)]
        g = thumb
        for c in cuts:
            g = next(q for q in split(g, c).geoms if q.contains(Polygon([at(tp, (s0 + s1) / 2, 1),
                     at(tp, (s0 + s1) / 2 + 0.5, 1), at(tp, (s0 + s1) / 2 + 0.5, 2)])))
        return g
    s_lo = 183.1 - 162.2                                  # the thumb plate's lower part starts this far from its back
    rows13 = Polygon(walk(four, at(r3, 0, PLATE_T), at(r2, r2["length"], 0)))
    rows12 = Polygon(walk(four, at(r2, 0, PLATE_T), at(r1, r1["length"], 0)))
    lower = thumb_part(s_lo, tp["length"] + 5)
    upper = thumb_part(0.5, s_lo + 1.0)
    # upper and lower overlap by 1 mm; each gets the other's corners on its top and bottom edges, so the
    # coplanar faces they share have the same vertices (a vertex inside the other's edge is refused)
    upper, lower = with_points(upper, lower.exterior.coords), with_points(lower, upper.exterior.coords)
    # the step between row 3's front and the thumb plane's lower part: the quadrilateral on their own corners
    bridge = Polygon([corner(rows13, at(r2, r2["length"], 0)), corner(rows13, at(r3, 0, PLATE_T)),
                      corner(lower, at(tp, s_lo, PLATE_T)), corner(lower, at(tp, s_lo, 0))])
    assert bridge.is_valid and bridge.area > 0, "step"
    # the joint between row 2 and the thumb plane, as a (non-convex) polygon on both pieces' own corners and lines,
    # reaching 0.5 into row 2 and 1.0 into the thumb piece so the join has volume on both sides
    link = Polygon([at(r1, r1["length"] - 0.5, PLATE_T), corner(rows12, at(r2, 0, PLATE_T)),
                    corner(upper, at(tp, 0.5, PLATE_T)), at(tp, 1.5, PLATE_T), at(tp, 1.5, 0),
                    corner(upper, at(tp, 0.5, 0)), corner(rows12, at(r1, r1["length"], 0)),
                    at(r1, r1["length"] - 0.5, 0)])
    assert link.is_valid, "link"
    a, b = R_SPANS
    lap = SPAN_OVERLAP
    pieces = {"L": [("Rows1to4", four, None, None, 0)],
              "R": [("Rows1to4", four, None, a, 0), ("Rows1to3", rows13, a, b, lap), ("ThumbLower", lower, a, None, lap),
                    ("Step", bridge, a, b, 0), ("Rows1to2", rows12, b, None, 0), ("ThumbUpper", upper, b, None, 0),
                    ("Link", link, b, None, 0)]}   # this order and these laps are the ones the kernel joins
    outer_end = unary_union([rows12, upper, lower, link])
    assert outer_end.geom_type == "Polygon" and outer_end.symmetric_difference(thumb).area < 0.5,         outer_end.symmetric_difference(thumb).area
    return dict(pieces=pieces, rows4=rows4, thumb_row=tp, thumb_lower_s=s_lo)


def with_points(poly, points, tol=1e-6):
    """poly with each of `points` that lies on one of its edges (not at a vertex) inserted into that edge."""
    ring = list(poly.exterior.coords)[:-1]
    for q in points:
        for i in range(len(ring)):
            a, b = ring[i], ring[(i + 1) % len(ring)]
            if min(math.dist(q, a), math.dist(q, b)) < 1e-4:
                continue
            if LineString([a, b]).distance(Polygon([q, (q[0] + 1e-9, q[1]), (q[0], q[1] + 1e-9)]).centroid) < tol:
                ring.insert(i + 1, tuple(q))
                break
    return Polygon(ring)


def walk(poly, start, end):
    """The ring of poly from its vertex nearest `start` to its vertex nearest `end`, going the way that does not
    pass the vertex furthest to the front (largest Y): used to keep rows 1-3 and drop row 4."""
    pts = list(poly.exterior.coords)[:-1]
    i0 = min(range(len(pts)), key=lambda i: math.dist(pts[i], start))
    i1 = min(range(len(pts)), key=lambda i: math.dist(pts[i], end))
    front = max(range(len(pts)), key=lambda i: pts[i][0])
    for step in (1, -1):
        out, i = [pts[i0]], i0
        while i != i1:
            i = (i + step) % len(pts)
            out.append(pts[i])
        if pts[front] not in out:
            return out
    raise ValueError("no way round")


def local_x(half, x):
    """Drawing X (seen from above, X to the right, Y to the back) -> STEP X. The STEP has Y to the front, so the
    drawing is turned 180 deg about Z: the user's right is -X (the left half's outer end is at +X)."""
    return HALVES[half]["mid"] - x


def key_list(get):
    """Per half: (row key, local X, s from the row's back edge). Row keys: 0-3 (4-row section) or 'T'."""
    strips = {}
    for name, h in {"L_R0": "1384", "L_R1": "138C", "L_R2": "23BE", "L_R3": "132E", "R_R0": "1695",
                    "R_R1": "1696", "R_R2": "23DC", "R_R3": "1771", "R_Thumb": "178A"}.items():
        strips[name] = max(y for _, y in get(h))
    out = {"L": [], "R": []}
    for k in json.loads(SWITCHES.read_text(encoding="utf-8")):
        half = k["plate"][0]
        row = "T" if k["plate"] == "R_Thumb" else int(k["plate"][-1])
        out[half].append((row, local_x(half, k["x_assembly_mm"]), strips[k["plate"]] - k["y_mm"]))
    assert len(out["L"]) == 20 and len(out["R"]) == 26
    return out


# ---------------------------------------------------------------- logo
def write_font_data(ttf):
    from fontTools.pens.basePen import BasePen
    from fontTools.ttLib import TTFont

    class Pen(BasePen):
        def __init__(self, gs):
            super().__init__(gs)
            self.rings, self.ring = [], []

        def _moveTo(self, p):
            self.ring = [p]

        def _lineTo(self, p):
            self.ring.append(p)

        def _qCurveToOne(self, a, b):
            p0 = self.ring[-1]
            for i in range(1, CURVE_SEGMENTS + 1):
                t = i / CURVE_SEGMENTS
                self.ring.append(tuple((1 - t) ** 2 * p0[j] + 2 * (1 - t) * t * a[j] + t * t * b[j] for j in (0, 1)))

        def _curveToOne(self, a, b, c):
            raise ValueError("cubic outline: expected a TrueType font")

        def _closePath(self):
            ring = [(round(x, 2), round(y, 2)) for x, y in self.ring]
            self.rings.append([list(q) for i, q in enumerate(ring) if q != ring[i - 1]])
            self.ring = []

    f = TTFont(ttf)
    names = {r.nameID: r.toUnicode() for r in f["name"].names if r.platformID == 3}
    gs, cmap = f.getGlyphSet(), f.getBestCmap()
    glyphs = {}
    for ch in sorted(set(LOGO_TEXT)):
        g = gs[cmap[ord(ch)]]
        pen = Pen(gs)
        g.draw(pen)
        xs = [x for r in pen.rings for x, _ in r]
        glyphs[ch] = dict(name=cmap[ord(ch)], advance=g.width, xmin=min(xs), xmax=max(xs), contours=pen.rings)
    FONT_DATA.write_text(json.dumps(dict(
        font=names.get(4), version=names.get(5), license=names.get(0), units_per_em=f["head"].unitsPerEm,
        source='https://www.dafont.com/xifiction.font (Nowak.tv, "Free for personal use")',
        cell_height=1600, stroke=400, rib=200,
        note=f"Outlines of the glyphs in {LOGO_TEXT!r} only, curves flattened. Rewrite with "
             "python 46sp/tools/build_plate_cover.py --font <Xifiction.ttf>", glyphs=glyphs), indent=1) + "\n",
        encoding="utf-8")


def logo_shape(cx, cy):
    """The logo in sketch coordinates (x = world X, y = s along the row, to the front), centred on (cx, cy),
    reading upright for someone at the front of the keyboard."""
    data = json.loads(FONT_DATA.read_text(encoding="utf-8"))
    k = LOGO_HEIGHT / data["cell_height"]
    adv = [data["glyphs"][c]["advance"] for c in LOGO_TEXT]
    left, right = data["glyphs"][LOGO_TEXT[0]]["xmin"], sum(adv[:-1]) + data["glyphs"][LOGO_TEXT[-1]]["xmax"]
    x0 = cx + (left + right) / 2 * k        # the text runs to -X (the reader's right) and its top to -s (the back)
    parts, pen = [], 0.0
    for ch, a in zip(LOGO_TEXT, adv):
        g = Polygon()
        for ring in data["glyphs"][ch]["contours"]:
            g = g.symmetric_difference(Polygon([(x0 - (pen + u) * k, cy + LOGO_HEIGHT / 2 - v * k) for u, v in ring]))
        parts.append(g)
        pen += a
    return unary_union(parts)


def loops_of(shape):
    out = []
    for g in getattr(shape, "geoms", [shape]):
        g = g.simplify(1e-3)
        out.append(list(g.exterior.coords)[:-1])
        out += [list(i.coords)[:-1] for i in g.interiors]
    return out


# ---------------------------------------------------------------- recipe
def dxf_lines(loops):
    tags = ["0", "SECTION", "2", "ENTITIES"]
    for loop in loops:
        for (x0, y0), (x1, y1) in zip(loop, loop[1:] + loop[:1]):
            tags += ["0", "LINE", "8", "0", "10", f"{x0:.6f}", "20", f"{y0:.6f}", "11", f"{x1:.6f}", "21", f"{y1:.6f}"]
    return "\n".join(tags + ["0", "ENDSEC", "0", "EOF", ""])


def clean(loop, tol=0.01):
    """Drop points closer than tol to the previous one (insert_dxf merges them)."""
    pts = list(loop)
    out = []
    for p in pts:
        if not out or math.dist(p, out[-1]) >= tol:
            out.append(p)
    if math.dist(out[0], out[-1]) < tol:
        out.pop()
    return out


class Recipe:
    def __init__(self):
        self.cmds = []

    def c(self, command, **params):
        self.cmds.append({"command": command, "params": params})

    def sketch(self, name, plane, loops):
        loops = [clean(l) for l in loops]
        self.c("sketch.create", name=name, plane=plane)
        self.c("sketch.insert_dxf", text=dxf_lines(loops))
        self.c("sketch.constraint.fix", entities=[f"l{i}" for i in range(1, sum(map(len, loops)) + 1)], fixed=True)
        self.c("sketch.solve")
        self.c("sketch.finish")


def yz_plane(x):
    return {"origin": [x, 0, 0], "x_dir": [0, 1, 0], "y_dir": [0, 0, 1]}


def row_plane(row, lift):
    """Sketch x = world X, sketch y = s along the row (to the front); the normal points up out of the plate."""
    o = at(row, 0, lift)
    return {"origin": [0, o[0], o[1]], "x_dir": [1, 0, 0], "y_dir": [0, row["t"][0], row["t"][1]]}


def rect(cx, cy, w, h):
    return [(cx - w / 2, cy - h / 2), (cx + w / 2, cy - h / 2), (cx + w / 2, cy + h / 2), (cx - w / 2, cy + h / 2)]


def ring(poly):
    return list(poly.exterior.coords)[:-1]


def build_plate(r, half, sec, keys):
    cfg = HALVES[half]
    name = f"Plate_{half}"
    placed = []
    for i, (tag, poly, d0, d1, lap) in enumerate(sec["pieces"][half]):
        d0 = cfg["x"][0] if d0 is None else d0 - lap      # drawing X; lap: reach this far into the span before
        d1 = cfg["x"][1] if d1 is None else d1
        u0, u1 = local_x(half, d1), local_x(half, d0)
        r.sketch(f"{name}_{tag}", yz_plane(u0), [ring(poly)])
        r.c("solid.extrude", sketch=f"{name}_{tag}", distance=u1 - u0, operation="new" if i == 0 else "join",
            targets=None if i == 0 else [name], name=f"{name}_{tag}Extrude", body_name=name if i == 0 else None)
        placed.append((poly, u0, u1))
    cuts = sorted({u for _, u0, u1 in placed for u in (u0, u1)})
    volume = sum(unary_union([p for p, u0, u1 in placed if u0 <= c0 and c1 <= u1]).area * (c1 - c0)
                 for c0, c1 in zip(cuts, cuts[1:]))
    rows = {i: row for i, row in enumerate(sec["rows4"])}
    rows["T"] = sec["thumb_row"]
    per_key = HOLE ** 2 * PLATE_T + (RELIEF ** 2 - HOLE ** 2) * (PLATE_T - LATCH_T)
    for rk, row in rows.items():
        ks = [(x, s) for k, x, s in keys if k == rk]
        if not ks:
            continue
        tag = f"{name}_Row{rk}"
        r.sketch(f"{tag}_Holes", row_plane(row, PLATE_T), [rect(x, s, HOLE, HOLE) for x, s in ks])
        r.c("solid.extrude", sketch=f"{tag}_Holes", distance=PLATE_T + 2, direction="negative", start_offset=1.0,
            operation="cut", targets=[name], name=f"{tag}_HoleCut")
        r.sketch(f"{tag}_Relief", row_plane(row, 0), [rect(x, s, RELIEF, RELIEF) for x, s in ks])
        r.c("solid.extrude", sketch=f"{tag}_Relief", distance=PLATE_T - LATCH_T + 0.5, start_offset=-0.5,
            operation="cut", targets=[name], name=f"{tag}_ReliefCut")
        volume -= per_key * len(ks)
    logo = None
    if half == "L":
        row = rows[LOGO_ROW]
        logo = logo_shape(sum(LOGO_X) / 2, row["length"] / 2)
        b = logo.bounds
        assert LOGO_X[0] <= b[0] and b[2] <= LOGO_X[1] and 1.5 <= b[1] and b[3] <= row["length"] - 1.5, b
        r.sketch(f"{name}_Logo", row_plane(row, PLATE_T), loops_of(logo))
        r.c("solid.extrude", sketch=f"{name}_Logo", distance=LOGO_DEPTH + 0.5, direction="negative",
            start_offset=0.5, operation="cut", targets=[name], name=f"{name}_LogoCut")
        volume -= logo.area * LOGO_DEPTH
    return volume, logo


def build_cover(r, half):
    cfg = HALVES[half]
    name = f"Cover_{half}"
    w = cfg["case_half"] - COVER_SIDE_IN
    r.c("solid.box", length=2 * w, width=COVER_Y[1] - COVER_Y[0], height=COVER_T,
        corner=[-w, COVER_Y[0], -COVER_T], operation="new", name=f"{name}_Plate", body_name=name)
    inner = cfg["case_half"] - 12.0
    screws = [(sx * cfg["wall_x"], y) for y in SCREWS_Y_WALL for sx in (-1, 1)]
    screws += [(sx * SCREW_FRONT[1] * inner, SCREW_FRONT[0]) for sx in (-1, 1)]
    for k, (x, y) in enumerate(screws):
        r.c("solid.hole", position=[x, y, -COVER_T], direction=[0, 0, 1], diameter=SCREW_D, type="countersink",
            cs_diameter=CS_D, cs_angle=CS_ANGLE, targets=[name], name=f"{name}_Screw{k}")
    cs_depth = (CS_D - SCREW_D) / 2 / math.tan(math.radians(CS_ANGLE / 2))
    per = math.pi / 4 * SCREW_D ** 2 * COVER_T + math.pi / 12 * cs_depth * (CS_D ** 2 + CS_D * SCREW_D + SCREW_D ** 2) \
        - math.pi / 4 * SCREW_D ** 2 * cs_depth
    return 2 * w * (COVER_Y[1] - COVER_Y[0]) * COVER_T - per * len(screws), screws


# ---------------------------------------------------------------- checks
def plan_checks(sec, keys, half, logo, screws):
    """Keycap to cheek, relief to plate edge, screws clear of the grooves (2D, before the CAD run)."""
    cfg = HALVES[half]
    x0, x1 = sorted(local_x(half, x) for x in cfg["x"])
    problems = []
    for rk, x, s in keys:
        row = sec["thumb_row"] if rk == "T" else sec["rows4"][rk]
        if not (x0 + 4 + 1.0 <= x - CAP / 2 and x + CAP / 2 <= x1 - 4 - 1.0):
            problems.append(f"{half} key X {x:.2f}: keycap within 1 mm of a cheek")
        if not (1.5 <= s - RELIEF / 2 and s + RELIEF / 2 <= row["length"] - 1.5):
            problems.append(f"{half} key X {x:.2f}: relief within 1.5 mm of the row ends (s {s:.2f})")
        if logo is not None and rk == LOGO_ROW and logo.distance(box(x - RELIEF / 2, s - RELIEF / 2,
                                                                       x + RELIEF / 2, s + RELIEF / 2)) < 1.5:
            problems.append(f"{half} logo within 1.5 mm of the key at X {x:.2f}")
    for x, y in screws:
        for g0, g1 in BONE_GROOVES_Y:
            if g0 - CS_D / 2 - 1 < y < g1 + CS_D / 2 + 1:
                problems.append(f"{half} screw at Y {y}: on a bone groove")
    return problems


def run(cli, cmds, out_sc=None, extra=(), step_in=None):
    with TemporaryDirectory() as work:
        recipe, meas = Path(work) / "build.json", Path(work) / "measure.json"
        recipe.write_text(json.dumps(cmds), encoding="utf-8")
        argv = [cli, "run", str(recipe), "--json-out", str(meas), "--results"]
        if step_in:
            argv += ["--in", str(step_in)]
        if out_sc:
            argv += ["--save", str(out_sc)]
        subprocess.run(argv + list(extra), check=True, stdout=subprocess.DEVNULL)
        return json.loads(meas.read_text(encoding="utf-8"))


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--cli", default=CLI_DEFAULT)
    ap.add_argument("--font", type=Path, help="Xifiction.ttf: rewrite the logo glyph outlines first")
    ap.add_argument("--check-case", action="store_true", help="interference of the left parts with the case STEP")
    args = ap.parse_args()
    if args.font:
        write_font_data(args.font)

    get = drawing()
    sec = sections(get)
    keys = key_list(get)
    r = Recipe()
    expected, problems, logo_l = {}, [], None
    for half in HALVES:
        expected[f"Plate_{half}"], logo = build_plate(r, half, sec, keys[half])
        expected[f"Cover_{half}"], screws = build_cover(r, half)
        problems += plan_checks(sec, keys[half], half, logo, screws)
        logo_l = logo or logo_l

    PRINT_DIR.mkdir(parents=True, exist_ok=True)
    exports = [{"command": "file.export_stl", "params": {"path": (PRINT_DIR / f"46sp_{b}.stl").as_posix(),
                                                        "bodies": [b], "quality": "fine"}} for b in expected]
    exports.append({"command": "file.export_step", "params": {"path": (PRINT_DIR / "46sp_plate_cover.step").as_posix(),
                                                              "bodies": list(expected)}})
    result = run(args.cli, r.cmds + exports + [{"command": "inspect.measure", "params": {}}], out_sc=OUTPUT)
    bodies = {b["name"]: b for b in result[-1]["bodies"]}          # --results: one entry per step
    ok = set(bodies) == set(expected)
    for name in expected:
        b = bodies[name]
        good = bool(b.get("closed")) and math.isclose(b["volume_mm3"], expected[name], rel_tol=2e-4)
        ok &= good
        print(f"{name}: closed={b.get('closed')} volume {b['volume_mm3']:.1f} (expected {expected[name]:.1f})"
              f" bbox {[round(v, 2) for v in b['bbox']['min'] + b['bbox']['max']]}")
    print(f"logo {LOGO_TEXT!r}: {logo_l.bounds[2] - logo_l.bounds[0]:.2f} x {logo_l.bounds[3] - logo_l.bounds[1]:.2f}"
          f" mm, area {logo_l.area:.1f} mm2, stroke {LOGO_HEIGHT / 4:.2f}, rib {LOGO_HEIGHT / 8:.2f}, depth {LOGO_DEPTH}")

    if args.check_case:
        left = Recipe()
        build_plate(left, "L", sec, keys["L"])
        build_cover(left, "L")
        # STEP bodies: (4)(5) acrylic cheeks, (6)(7) side walls, (8) front block, (9)(10) back blocks.
        # The STEP cheek slot is the f3d one (about 3.5 wide, rows 26.86/19.05/19.05/26.86), not the r3 DWG slot
        # the plate follows (5.5, rows 28.05/20.9/20.9/26.05), so the tongues overlap it; that is reported apart.
        cheeks = {"본체1 (4)", "본체1 (5)"}
        case = sorted(cheeks) + ["본체1 (6)", "본체1 (7)", "본체1 (8)", "본체1 (9)", "본체1 (10)"]
        check = left.cmds + [{"command": "inspect.interference", "params": {"bodies": ["Plate_L", "Cover_L"] + case}}]
        res = run(args.cli, check, step_in=CASE_STEP)
        inter = [x for x in res[-1]["interferences"]
                 if {x["a"], x["b"]} & {"Plate_L", "Cover_L"} and not {x["a"], x["b"]} <= {"Plate_L", "Cover_L"}]
        for x in inter:
            other = x["b"] if x["a"] in ("Plate_L", "Cover_L") else x["a"]
            kind = "STEP cheek (f3d slot)" if other in cheeks else "case"
            print(f"overlap {x['a']} / {other} [{kind}]: {x['volume_mm3']:.1f} mm3, X "
                  f"{x['bbox']['min'][0]:.2f}..{x['bbox']['max'][0]:.2f}")
        hard = [x for x in inter if not ({x["a"], x["b"]} & cheeks)]
        if hard:
            problems.append(f"{len(hard)} overlaps with the side walls or blocks")
        else:
            print("case check: Plate_L and Cover_L clear of the side walls and the front and back blocks")

    for p in problems:
        print("PROBLEM:", p)
    if not ok or problems:
        raise SystemExit("check failed")
    print(f"{OUTPUT.name}: 4 closed bodies, volumes match; STL/STEP in {PRINT_DIR.relative_to(ROOT.parent)}")


if __name__ == "__main__":
    main()
