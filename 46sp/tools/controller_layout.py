"""Plan (top view) of where the two Pro Micros go, as a DXF and a PNG, for discussion.

Seen from above with the user at the bottom: drawing X to the user's right, drawing Y to the back.
STEP frame -> drawing: x = -X, y = -Y (the STEP has +X to the user's left and +Y to the front).

    python 46sp/tools/controller_layout.py   # writes model/controller-layout.dxf, images/controller-layout.png
"""

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
# proposals, in each half's STEP frame (X: + = user's left)
LEFT_BOARD = dict(x=-50.0, y0=3.5)          # in the back block's inner half, USB-C out of the back face
RIGHT_BOARD = dict(x=55.0, y0=40.0)         # on the cover, inner side, under rows 1-2


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
        out.append(("BLOCK", rect(half, -i, i, CASE_Y[0], BACK_BLOCK_Y), "뒤 블록", to_d(half, 38 if half == "L" else 0, 13)))
        out.append(("BLOCK", rect(half, -i, i, FRONT_BLOCK_Y, CASE_Y[1]), "앞 블록", to_d(half, 0, 175)))
        out.append(("PLATE", rect(half, -i - 3.5, i + 3.5, *PLATE_Y), "plate(키 자리)", to_d(half, 0, 95)))
        sx = -1 if half == "L" else 1          # inner wall: left case -X, right case +X
        out.append(("AUX", rect(half, sx * i, sx * a, 40, 52), None, None))
    b = LEFT_BOARD
    out.append(("BOARD", rect("L", b["x"] - BOARD_W / 2, b["x"] + BOARD_W / 2, b["y0"], b["y0"] + BOARD_L),
                "왼쪽 Pro Micro\n뒤 블록 주머니에 밀어 넣음\nUSB-C(초록) → 뒷면 구멍", to_d("L", b["x"] + 12, b["y0"] + 8)))
    out.append(("USB", rect("L", b["x"] - 4.5, b["x"] + 4.5, b["y0"] - 1.0, b["y0"] + 6.3), None, None))
    b = RIGHT_BOARD
    out.append(("BOARD", rect("R", b["x"] - BOARD_W / 2, b["x"] + BOARD_W / 2, b["y0"], b["y0"] + BOARD_L),
                "오른쪽 Pro Micro\nplate 밑, cover 위 받침\n(cover와 한 몸 출력)", to_d("R", b["x"] - 12, b["y0"] + 10)))
    return out


def write_dxf(items):
    doc = ezdxf.new("R2010", setup=True)
    colors = {"CASE": 7, "BLOCK": 8, "PLATE": 5, "BOARD": 1, "USB": 3, "AUX": 6, "TEXT": 7}
    for name, c in colors.items():
        doc.layers.add(name, color=c)
    msp = doc.modelspace()
    for layer, pts, label, at in items:
        if pts:
            msp.add_lwpolyline(pts, close=True, dxfattribs={"layer": layer})
        if label:
            msp.add_mtext(label.replace("\n", "\\P"), dxfattribs={"layer": "TEXT", "char_height": 3.5,
                                                                  "insert": (at[0], at[1]), "attachment_point": 5})
    msp.add_mtext("위에서 본 배치(사용자는 아래쪽). 왼쪽 반쪽 | 오른쪽 반쪽", dxfattribs={
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
            "USB": (40, 160, 60), "AUX": (170, 60, 170)}
    order = ["CASE", "BLOCK", "PLATE", "BOARD", "USB", "AUX"]
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
            anchor = ("ra" if x < W / 2 else "la") if lay == "BOARD" else "ma"
            d.multiline_text((x, y), label, font=g, fill=col, anchor=anchor,
                             align={"ra": "right", "la": "left"}.get(anchor, "center"))
    d.text((pad, 15), "위에서 본 배치 (키보드 앞에 앉은 시점, 위쪽이 뒤). 빨강: Pro Micro, 초록: USB-C, "
           "보라: AUX 구멍(안쪽 측벽, 위치는 짐작)", font=f, fill=(30, 30, 30))
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
