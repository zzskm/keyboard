"""Write one r2 panel (by bbox) from the CADCraft entity dump to a minimal ASCII DXF
(LINE/ARC/CIRCLE only), translated by (dx, dy). Reference geometry only."""
import json, math, sys
SRC, OUT = sys.argv[1], sys.argv[2]
x0, y0, x1, y1, dx, dy = map(float, sys.argv[3:9])
d = json.loads(open(SRC, encoding="utf-8").readline())
def inside(p): return x0 - 0.01 <= p[0] <= x1 + 0.01 and y0 - 0.01 <= p[1] <= y1 + 0.01
out = ["0", "SECTION", "2", "HEADER", "9", "$INSUNITS", "70", "4", "0", "ENDSEC", "0", "SECTION", "2", "ENTITIES"]
n = dict(LINE=0, ARC=0, CIRCLE=0)
def line(a, b):
    out.extend(["0", "LINE", "8", "REF_r2_P2", "10", f"{a[0]+dx:.6f}", "20", f"{a[1]+dy:.6f}", "30", "0", "11", f"{b[0]+dx:.6f}", "21", f"{b[1]+dy:.6f}", "31", "0"]); n["LINE"] += 1
def arc(c, r, a0, a1):
    out.extend(["0", "ARC", "8", "REF_r2_P2", "10", f"{c[0]+dx:.6f}", "20", f"{c[1]+dy:.6f}", "30", "0", "40", f"{r:.6f}", "50", f"{a0:.6f}", "51", f"{a1:.6f}"]); n["ARC"] += 1
for e in d["entities"]:
    g = e["geometry"]; t = g["type"]
    if t == "line":
        a, b = (g["a"]["x"], g["a"]["y"]), (g["b"]["x"], g["b"]["y"])
        if inside(a) and inside(b): line(a, b)
    elif t == "circle":
        c = (g["center"]["x"], g["center"]["y"])
        if inside(c):
            out.extend(["0", "CIRCLE", "8", "REF_r2_P2", "10", f"{c[0]+dx:.6f}", "20", f"{c[1]+dy:.6f}", "30", "0", "40", f"{g['radius']:.6f}"]); n["CIRCLE"] += 1
    elif t == "arc":
        c = (g["center"]["x"], g["center"]["y"])
        if inside(c): arc(c, g["radius"], math.degrees(g["start"]), math.degrees(g["end"]))
    elif t == "lwPolyline":
        vs = g["vertices"]; m = len(vs)
        pts = [(v["p"]["x"], v["p"]["y"]) for v in vs]
        if not all(inside(p) for p in pts): continue
        for i in range(m if g["closed"] else m - 1):
            p0, p1, b = pts[i], pts[(i + 1) % m], vs[i]["bulge"]
            if math.hypot(p1[0]-p0[0], p1[1]-p0[1]) < 1e-9: continue
            if abs(b) < 1e-12: line(p0, p1); continue
            th = 4 * math.atan(b); ch = math.hypot(p1[0]-p0[0], p1[1]-p0[1])
            r = ch / (2 * math.sin(abs(th) / 2))
            mx, my = (p0[0]+p1[0])/2, (p0[1]+p1[1])/2
            h = r * math.cos(abs(th) / 2); ux, uy = (p1[0]-p0[0])/ch, (p1[1]-p0[1])/ch
            s = 1 if b > 0 else -1
            c = (mx - uy * h * s, my + ux * h * s)
            a0 = math.degrees(math.atan2(p0[1]-c[1], p0[0]-c[0])); a1 = math.degrees(math.atan2(p1[1]-c[1], p1[0]-c[0]))
            if b < 0: a0, a1 = a1, a0
            arc(c, r, a0 % 360, a1 % 360)
out += ["0", "ENDSEC", "0", "EOF"]
open(OUT, "w", encoding="ascii", newline="\r\n").write("\n".join(out) + "\n")
print(n)
