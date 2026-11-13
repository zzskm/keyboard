"""Make the 46-key plate set from the r3 drawing without changing the plywood case.

Reads `source/46sp_plate_r3.converted.dxf` and writes `source/46sp_plate_46key.dxf`
(same entities, same plate outlines except two rib notches per row on the right
rows 1-2) and `model/46key-switches.json`. It then checks the result and prints a report.

Changes against r3 (45 openings -> 46):
  - L_R2: the outer opening (X 37.225) is removed -> 5 keys.
  - R_R0, R_R1: the 6th opening (X 296.09, after the 7 mm rib passage) is replaced by
    two openings at a uniform 19.05 pitch after the 5th key (X 280.78, 299.83) -> 7 keys.
    The rib notches at X 278.25 and 305.62 on these two rows sit under the new
    openings, so they are removed (the plate edge is made straight there).
Plate lengths stay as r3, so the plates still sit in the existing cheek slots.
"""

import argparse
import json
from pathlib import Path

import ezdxf
from shapely.geometry import Polygon, box
from shapely.ops import unary_union

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "source/46sp_plate_r3.converted.dxf"
OUTPUT = ROOT / "source/46sp_plate_46key.dxf"
SWITCHES = ROOT / "model/46key-switches.json"

U = 19.05
HOLE = 14.0
CAP = 18.2            # keycap bottom width (MX profile caps are 18.0-18.2)
CHEEK_T = 4.0         # cheek (keypad_side) thickness in 46sp_r3_left.step: X 63..67
THUMB_SHIFT = -10.0   # 178A is drawn 10 mm right of where it sits (ends 265/284.75/337 = R3 255, R2 274.75, R0 327)

PLATES = {  # name: (outline handle, r3 openings, 46-key openings)
    "L_R0": ("1384", 6, 6), "L_R1": ("138C", 6, 6), "L_R2": ("23BE", 6, 5), "L_R3": ("132E", 3, 3),
    "R_R0": ("1695", 6, 7), "R_R1": ("1696", 6, 7), "R_R2": ("23DC", 5, 5), "R_R3": ("1771", 3, 3),
    "R_Thumb": ("178A", 4, 4),
}
REMOVE_X = {"L_R2": [37.225], "R_R0": [296.09], "R_R1": [296.09]}
ADD_X = {"R_R0": [261.725 + U, 261.725 + 2 * U], "R_R1": [261.725 + U, 261.725 + 2 * U]}
DROP_NOTCH_X = {"R_R0": [277.4, 279.1, 304.77, 306.47], "R_R1": [277.4, 279.1, 304.77, 306.47]}


CHEEK_ENDS = {15, 148, 170, 327}
RIB_ENDS = {"L_R3", "R_R3", "R_Thumb"}


def notch_x(outline):
    """Centre X of each 1.7 mm rib notch: two vertical 1.65 mm sides 1.7 apart."""
    pts = list(outline.exterior.coords)
    sides = sorted(round(a[0], 3) for a, b in zip(pts, pts[1:])
                   if abs(a[0] - b[0]) < 1e-6 and 1.6 < abs(a[1] - b[1]) < 1.7)
    found = set()
    for a in sides:
        for b in sides:
            if abs(b - a - 1.7) < 0.01:
                found.add(round((a + b) / 2, 3))
    return sorted(found)


def poly(entity):
    pts = [(float(x), float(y)) for x, y in entity.get_points("xy")]
    if pts[0] == pts[-1]:
        pts = pts[:-1]
    return Polygon(pts)


def straighten(points, drop_x):
    """Remove the notch vertices whose X is in drop_x (each notch is 4 points on one edge)."""
    keep = [p for p in points if not any(abs(p[0] - x) < 0.006 for x in drop_x)]
    removed = len(points) - len(keep)
    if removed == 0 or removed % (2 * len(drop_x)):  # 2 points per notch side, per plate edge
        raise ValueError(f"removed {removed} points, not whole notches")
    return keep


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", type=Path, default=OUTPUT)
    args = parser.parse_args()

    doc = ezdxf.readfile(SOURCE)
    msp = doc.modelspace()
    ents = {e.dxf.handle: e for e in msp.query("LWPOLYLINE")}
    holes = {h: e for h, e in ents.items()
             if all(abs(s - HOLE) < 0.03 for s in (lambda b: (b[2] - b[0], b[3] - b[1]))(poly(e).bounds))}

    report, switches, problems = [], [], []
    for name, (handle, r3_count, count) in PLATES.items():
        outline_e = ents[handle]
        mine = sorted((h for h in holes if poly(outline_e).contains(poly(holes[h]))),
                      key=lambda h: poly(holes[h]).centroid.x)
        if len(mine) != r3_count:
            raise ValueError(f"{name}: r3 has {len(mine)} openings, expected {r3_count}")
        y = poly(holes[mine[0]]).centroid.y
        for x in REMOVE_X.get(name, []):
            h = next(h for h in mine if abs(poly(holes[h]).centroid.x - x) < 0.01)
            msp.delete_entity(holes[h])
            mine.remove(h)
        for x in ADD_X.get(name, []):
            e = msp.add_lwpolyline([(x - HOLE / 2, y + HOLE / 2), (x + HOLE / 2, y + HOLE / 2),
                                    (x + HOLE / 2, y - HOLE / 2), (x - HOLE / 2, y - HOLE / 2)],
                                   close=True, dxfattribs={"layer": "0", "color": 3})
            holes[e.dxf.handle] = e
            mine.append(e.dxf.handle)
        if name in DROP_NOTCH_X:
            pts = straighten([tuple(p) for p in outline_e.get_points("xy")], DROP_NOTCH_X[name])
            outline_e.set_points(pts, format="xy")
            outline_e.closed = True
        mine.sort(key=lambda h: poly(holes[h]).centroid.x)

        outline = poly(outline_e)
        cut = [poly(holes[h]) for h in mine]
        xs = [round(c.centroid.x, 3) for c in cut]
        shift = THUMB_SHIFT if name == "R_Thumb" else 0.0
        for h, c in zip(mine, cut):
            switches.append({"plate": name, "handle": h, "x_mm": round(c.centroid.x, 5),
                             "y_mm": round(c.centroid.y, 5), "x_assembly_mm": round(c.centroid.x + shift, 5)})

        # checks
        if len(cut) != count:
            problems.append(f"{name}: {len(cut)} openings, expected {count}")
        if not outline.is_valid:
            problems.append(f"{name}: outline invalid")
        for c in cut:
            if not outline.contains(c):
                problems.append(f"{name}: opening at {c.centroid.x:.2f} leaves the plate")
        edge_web = min(outline.exterior.distance(c) for c in cut)
        hole_web = min((a.distance(b) for i, a in enumerate(cut) for b in cut[i + 1:]), default=None)
        pitch = min((b - a for a, b in zip(xs, xs[1:]) if b - a > 1), default=None)
        # keycap to cheek: only the plate ends that go into a cheek slot (assembly X 15/148, 170/327)
        x0, x1 = outline.bounds[0] + shift, outline.bounds[2] + shift
        lo_cap = min(xs) + shift - CAP / 2 - (x0 + CHEEK_T) if round(x0) in CHEEK_ENDS else None
        hi_cap = (x1 - CHEEK_T) - (max(xs) + shift + CAP / 2) if round(x1) in CHEEK_ENDS else None
        for gap in (lo_cap, hi_cap):
            if gap is not None and gap < 1.0:
                problems.append(f"{name}: keycap {gap:.2f} mm from the cheek")
        # rib notches: a rib that runs on under the plate must miss every opening in X.
        # On the thumb rows the ribs stop at the back-edge notch (as in r3), so they are only listed.
        notches = notch_x(outline)
        rib_clear = min((abs(n - c.centroid.x) - HOLE / 2 - 0.85 for n in notches for c in cut), default=None)
        if name not in RIB_ENDS and rib_clear is not None and rib_clear < 0.5:
            problems.append(f"{name}: a rib notch is {rib_clear:.2f} mm from an opening in X")
        report.append((name, len(cut), xs, edge_web, hole_web, pitch, lo_cap, hi_cap,
                       [round(n + shift, 2) for n in notches], rib_clear))

    total = sum(r[1] for r in report)
    if total != 46:
        problems.append(f"total {total} openings, expected 46")
    doc.saveas(args.out)
    SWITCHES.write_text(json.dumps(switches, indent=2) + "\n", encoding="utf-8")

    print(f"wrote {args.out.relative_to(ROOT.parent)} and {SWITCHES.relative_to(ROOT.parent)}")
    f = lambda v: "-" if v is None else f"{v:.2f}"
    print("plate     n  web edge/hole  pitch  cap-cheek lo/hi  notch-clear  key X (drawing) | rib notch X (assembly)")
    for name, n, xs, ew, hw, p, lo, hi, nx, rc in report:
        print(f"{name:8} {n:2}  {f(ew):>5} / {f(hw):>5}  {f(p):>5}  {f(lo):>6} / {f(hi):>6}  {f(rc):>6}  {xs} | {nx}")
    print(f"total {total}")
    if problems:
        raise SystemExit("FAIL\n  " + "\n  ".join(problems))
    print("OK")


if __name__ == "__main__":
    main()
