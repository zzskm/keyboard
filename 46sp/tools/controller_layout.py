"""Plan (top view) of where the two Pro Micros and the AUX jacks go, as a DXF and a PNG.\n\nBoth real cases have two openings in the back face (photos 2026-11-15, images/real-back.jpg): one near the\nouter end (USB-C shaped) and one near the inner end. Each half uses them the same way: the Pro Micro slides\ninto the back block at the outer end with its USB-C in the outer opening, the AUX jack sits in the inner\nopening, and the left-right cable runs across the rear centre. Positions are read from the photos (+-2 mm).\n\nSeen from above with the user at the bottom: drawing X to the user's right, drawing Y to the back.\nSTEP frame -> drawing: x = -X, y = -Y (the STEP has +X to the user's left and +Y to the front).\n\n    python 46sp/tools/controller_layout.py   # writes model/controller-layout.dxf, images/controller-layout.png\n"""

from pathlib import Path

import ezdxf
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
DXF = ROOT / "model/controller-layout.dxf"
PNG = ROOT / "images/controller-layout.png"

GAP = 30.0
HALVES = {  # STEP-frame numbers: outer half width, inner half width (between the walls)
    "L": dict(half=75.0, inner=63.0, ox=0.0),
    "R": dict(half=87.0, inner=75.0, ox=75.0 + GAP + 87.0),
}
CASE_Y = (0.65, 206.04)           # back face .. front face
BACK_BLOCK_Y, FRONT_BLOCK_Y = 31.0, 143.75   # inside faces of the back and front blocks at the floor
PLATE_Y = (48.05, 140.62)         # plate seen from above
BOARD_L, BOARD_W = 33.0, 18.0     # Pro Micro
# in each half's STEP frame (X: + = user's left). Openings: centre about 21 mm in from the case's outer
# corner, i.e. 9 mm in from the wall's inner face (a 6-ply pocket against the wall), about 30 mm above the floor.
OPENING_IN = 9.0
POCKET_DEPTH = 26.0               # dxf/46sp_inside_bw_b split layers
JACK_L, JACK_W = 14.0, 6.0        # PJ-320A class body; the owned jack is not measured yet


def ends(half):
    """(outer X, inner X) of the opening centres; the left case's outer wall is +X, the right case's is -X."""
    i = HALVES[half]["inner"] - OPENING_IN
    return (i, -i) if half == "L" else (-i, i)


def to_d(half, X, Y):
    h = HALVES[half]
    return (-X + h["ox"], -Y)


def rect(half, x0, x1, y0, y1):
    pts = [to_d(half, x, y) for x, y in ((x0, y0), (x1, y0), (x1, y1), (x0, y1))]
    return pts + pts[:1]


def shapes():
    """(layer, points, label, label point) in drawing coordinates."""
    out = []
    for half, h in HALVES.items():
        a, i = h["half"], h["inner"]
        out.append(("CASE", rect(half, -a, a, *CASE_Y), None, None))
        out.append(("CASE", rect(half, -a, -i, *CASE_Y), None, None))            # walls
        out.append(("CASE", rect(half, i, a, *CASE_Y), None, None))
        out.append(("BLOCK", rect(half, -i, i, CASE_Y[0], BACK_BLOCK_Y), "뒤 블록", to_d(half, 0, 13)))
        out.append(("BLOCK", rect(half, -i, i, FRONT_BLOCK_Y, CASE_Y[1]), "앞 블록", to_d(half, 0, 175)))
        out.append(("PLATE", rect(half, -i - 3.5, i + 3.5, *PLATE_Y), "plate(키 자리)", to_d(half, 0, 95)))
        xo, xi = ends(half)
        out.append(("BOARD", rect(half, xo - BOARD_W / 2, xo + BOARD_W / 2, CASE_Y[0] + 1.0, CASE_Y[0] + 1.0 + BOARD_L),
                    "Pro Micro\n뒤 블록 주머니(깊이 26)\nUSB-C → 바깥쪽 구멍", to_d(half, 0.55 * xo, 60)))
        out.append(("USB", rect(half, xo - 4.5, xo + 4.5, CASE_Y[0], CASE_Y[0] + 7.0), None, None))
        out.append(("AUX", rect(half, xi - JACK_W / 2, xi + JACK_W / 2, CASE_Y[0], CASE_Y[0] + JACK_L),
                    "AUX 잭(안쪽 구멍)", to_d(half, 0.6 * xi, 38)))
        out.append(("WIRE", rect(half, min(xo, xi) + 9, max(xo, xi) - 3, BACK_BLOCK_Y - 3.0, BACK_BLOCK_Y - 1.0),
                    "배선 홈(뒤 블록 안쪽 면)", to_d(half, 0, BACK_BLOCK_Y - 9)))
    return out


def write_dxf(items):
    doc = ezdxf.new("R2010", setup=True)
    colors = {"CASE": 7, "BLOCK": 8, "PLATE": 5, "BOARD": 1, "USB": 3, "AUX": 6, "WIRE": 4, "TEXT": 7}
    for name, c in colors.items():
        doc.layers.add(name, color=c)
    msp = doc.modelspace()
    for layer, pts, label, at in items:
        if pts:
            msp.add_lwpolyline(pts, close=True, dxfattribs={"layer": layer})
        if label:
            msp.add_mtext(label.replace("\n", "\\P"), dxfattribs={"layer": "TEXT", "char_height": 3.5,
                                                                  "insert": (at[0], at[1]), "attachment_point": 5})
    msp.add_mtext("위에서 본 배치(사용자는 아래쪽). 왼쪽 반쪽 | 오른쪽 반쪽. 두 case 모두 뒷면 구멍 2개", dxfattribs={
        "layer": "TEXT", "char_height": 4, "insert": (-80, 12), "attachment_point": 7})
    DXF.parent.mkdir(exist_ok=True)
    doc.saveas(DXF)


def write_png(items):
    xs = [p[0] for _, pts, _, _ in items if pts for p in pts]
    ys = [p[1] for _, pts, _, _ in items if pts for p in pts]
    S, pad = 4.0, 60
    W = int((max(xs) - min(xs)) * S) + 2 * pad
    H = int((max(ys) - min(ys)) * S) + 2 * pad + 60
    im = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(im)
    tr = lambda p: (pad + (p[0] - min(xs)) * S, pad + 40 + (max(ys) - p[1]) * S)
    fill = {"CASE": (222, 196, 160), "BLOCK": (190, 160, 120), "PLATE": (170, 185, 220), "BOARD": (220, 40, 40),
            "USB": (40, 160, 60), "AUX": (170, 60, 170), "WIRE": (60, 120, 200)}
    order = ["CASE", "BLOCK", "PLATE", "WIRE", "BOARD", "USB", "AUX"]
    for layer in order:
        for lay, pts, _, _ in items:
            if lay == layer and pts:
                d.polygon([tr(p) for p in pts], fill=fill[layer], outline=(60, 60, 60))
    f = ImageFont.truetype("malgunbd.ttf", 22)
    g = ImageFont.truetype("malgun.ttf", 18)
    for lay, _, label, at in items:
        if label:
            x, y = tr(at)
            col = (200, 20, 20) if lay == "BOARD" else (130, 40, 130) if lay == "AUX" else (30, 30, 30)
            d.multiline_text((x, y), label, font=g, fill=col, anchor="ma", align="center")
    d.text((pad, 15), "위에서 본 배치 (키보드 앞에 앉은 시점, 위쪽이 뒤). 빨강: Pro Micro, 초록: USB-C, "
           "보라: AUX 잭. 좌우 케이블은 뒤 가운데로 건넌다", font=f, fill=(30, 30, 30))
    for half, name in (("L", "왼쪽 반쪽"), ("R", "오른쪽 반쪽")):
        x, y = tr(to_d(half, 0, CASE_Y[1] + 4))
        d.text((x, y), name, font=f, fill=(30, 30, 30), anchor="ma")
    im.save(PNG)


def main():
    items = shapes()
    write_dxf(items)
    write_png(items)
    print(f"wrote {DXF.relative_to(ROOT.parent)} and {PNG.relative_to(ROOT.parent)}")


if __name__ == "__main__":
    main()
