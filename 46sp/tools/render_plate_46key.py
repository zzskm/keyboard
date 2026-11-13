"""Render r3 vs 46-key plate outlines and openings to a PNG (changed openings highlighted)."""
import sys
import ezdxf
from PIL import Image, ImageDraw, ImageFont

r3, new, out = sys.argv[1:4]
PLATES = ["1384", "138C", "23BE", "132E", "1695", "1696", "23DC", "1771", "178A"]
THUMB_SHIFT = -10.0


def load(path):
    m = ezdxf.readfile(path).modelspace()
    ents = {e.dxf.handle: [(float(x), float(y)) for x, y in e.get_points("xy")] for e in m.query("LWPOLYLINE")}
    outlines = {h: ents[h] for h in PLATES}
    holes = []
    for h, pts in ents.items():
        xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
        if abs(max(xs) - min(xs) - 14) < 0.03 and abs(max(ys) - min(ys) - 14) < 0.03:
            holes.append((round((max(xs) + min(xs)) / 2, 2), round((max(ys) + min(ys)) / 2, 2)))
    return outlines, set(holes)


o_old, h_old = load(r3)
o_new, h_new = load(new)
S, X0, Y1, PAD = 6.0, 5.0, 255.0, 40
W = int((347 - X0) * S) + 2 * PAD
H = int((Y1 - 128) * S) + 2 * PAD + 40
img = Image.new("RGB", (W, H), "white")
d = ImageDraw.Draw(img)


def tr(x, y, shift=0.0):
    return (PAD + (x + shift - X0) * S, PAD + (Y1 - y) * S)


def shift_of(x, y):
    # the thumb plate is drawn 10 mm right of its place; show it in assembly X
    return THUMB_SHIFT if (x > 262 and y < 184) else 0.0


for h in PLATES:
    sh = THUMB_SHIFT if h == "178A" else 0.0
    d.line([tr(x, y, sh) for x, y in o_old[h] + o_old[h][:1]], fill=(230, 150, 150), width=2)
    d.line([tr(x, y, sh) for x, y in o_new[h] + o_new[h][:1]], fill=(0, 0, 0), width=2)
for (x, y) in h_old | h_new:
    sh = shift_of(x, y)
    a, b = tr(x - 7, y + 7, sh), tr(x + 7, y - 7, sh)
    if (x, y) in h_new and (x, y) in h_old:
        d.rectangle([a, b], outline=(80, 80, 80), width=2)
    elif (x, y) in h_new:
        d.rectangle([a, b], outline=(0, 110, 230), fill=(205, 225, 250), width=3)
    else:
        d.rectangle([a, b], outline=(220, 40, 40), width=3)
        d.line([a, b], fill=(220, 40, 40), width=2); d.line([(a[0], b[1]), (b[0], a[1])], fill=(220, 40, 40), width=2)
try:
    font = ImageFont.truetype("malgun.ttf", 22)
except OSError:
    font = ImageFont.load_default()
d.text((PAD, H - 50), "black: 46-key plate   blue: new opening   red X: removed opening   pink: r3 outline (notches removed)   thumb plate shown at assembly X (-10 mm)",
       fill=(0, 0, 0), font=font)
img.save(out)
print(out, W, H, len(h_old), len(h_new))
