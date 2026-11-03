"""Switch-opening and feature registration analysis for 46es_r2 DWG (read-only).

Uses the raw CADCraft entity dump. For the 1.5T plate (P2) and 2T Astel layer (P3)
it extracts every square opening: centre, side, rotation. It also lists hex
cut-outs / circles relative to each panel's lower-left corner so features can be
compared across layers and against the public GH60 coordinates.
"""
import json, math, sys, collections

sys.stdout.reconfigure(encoding="utf-8")
SRC, OUT = sys.argv[1], sys.argv[2]
d = json.loads(open(SRC, encoding="utf-8").readline())
ents = d["entities"]

PANELS = {  # lower-left corners of panel outer bbox, from analyze_geom.py
    "P0_acryl2T": (19.632, 683.348, 306.032, 779.148),
    "P1_acryl5T": (21.628, 555.060, 308.028, 650.860),
    "P2_extr1p5T": (20.891, 419.049, 307.291, 514.849),
    "P3_astel2T": (19.834, 288.607, 306.234, 384.407),
    "P4_smoke5T": (17.932, 163.161, 304.332, 258.961),   # 3 pieces, combined bbox
    "P5_astel2T": (21.966, 28.456, 308.366, 124.256),    # 3 pieces, combined bbox
}


def panel_of(x, y):
    for k, (x0, y0, x1, y1) in PANELS.items():
        if x0 - 1 <= x <= x1 + 1 and y0 - 1 <= y <= y1 + 1:
            return k
    return None


def rel(k, x, y):
    return (x - PANELS[k][0], y - PANELS[k][1])

# ---------- closed polylines: classify
squares = collections.defaultdict(list)
hexes = collections.defaultdict(list)
others = collections.defaultdict(list)
for e in ents:
    g = e["geometry"]
    if g["type"] != "lwPolyline" or not g["closed"]:
        continue
    V = [(v["p"]["x"], v["p"]["y"]) for v in g["vertices"]]
    bul = [v["bulge"] for v in g["vertices"]]
    # drop duplicated closing vertex
    while len(V) > 3 and math.hypot(V[-1][0] - V[0][0], V[-1][1] - V[0][1]) < 1e-6:
        V.pop(); bul.pop()
    n = len(V)
    cx = sum(p[0] for p in V) / n; cy = sum(p[1] for p in V) / n
    k = panel_of(cx, cy)
    edges = [math.hypot(V[(i + 1) % n][0] - V[i][0], V[(i + 1) % n][1] - V[i][1]) for i in range(n)]
    if n == 4 and all(abs(b) < 1e-12 for b in bul):
        ang = math.degrees(math.atan2(V[1][1] - V[0][1], V[1][0] - V[0][0]))
        ang = ((ang + 45) % 90) - 45
        squares[k].append(dict(h=e["handle"], cx=cx, cy=cy, side=sum(edges) / 4, side_min=min(edges), side_max=max(edges), rot=ang, col=e["color"]))
    elif n == 6 and all(abs(b) < 1e-12 for b in bul):
        xs = [p[0] for p in V]; ys = [p[1] for p in V]
        hexes[k].append(dict(h=e["handle"], cx=cx, cy=cy, edge=sum(edges) / 6, w=max(xs) - min(xs), hgt=max(ys) - min(ys)))
    else:
        others[k].append(dict(h=e["handle"], n=n, cx=cx, cy=cy, edges=[round(x, 3) for x in edges], bulges=[round(b, 4) for b in bul], V=[(round(p[0], 4), round(p[1], 4)) for p in V]))

circles = collections.defaultdict(list)
for e in ents:
    g = e["geometry"]
    if g["type"] == "circle":
        k = panel_of(g["center"]["x"], g["center"]["y"])
        circles[k].append(dict(h=e["handle"], cx=g["center"]["x"], cy=g["center"]["y"], r=g["radius"]))

arcs = collections.defaultdict(list)
for e in ents:
    g = e["geometry"]
    if g["type"] == "arc":
        k = panel_of(g["center"]["x"], g["center"]["y"])
        arcs[k].append(dict(h=e["handle"], cx=g["center"]["x"], cy=g["center"]["y"], r=g["radius"], a0=math.degrees(g["start"]), a1=math.degrees(g["end"])))
# bulge arcs in open polylines (R2.25 notches) – centre from bulge
for e in ents:
    g = e["geometry"]
    if g["type"] != "lwPolyline":
        continue
    vs = g["vertices"]; n = len(vs)
    for i in range(n if g["closed"] else n - 1):
        b = vs[i]["bulge"]
        if abs(b) < 1e-12:
            continue
        p0 = (vs[i]["p"]["x"], vs[i]["p"]["y"]); p1 = (vs[(i + 1) % n]["p"]["x"], vs[(i + 1) % n]["p"]["y"])
        th = 4 * math.atan(b)
        ch = math.hypot(p1[0] - p0[0], p1[1] - p0[1])
        r = ch / (2 * math.sin(abs(th) / 2))
        mx, my = (p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2
        dist = r * math.cos(abs(th) / 2)
        ux, uy = (p1[0] - p0[0]) / ch, (p1[1] - p0[1]) / ch
        # centre to the left of chord for positive bulge (CCW)
        sgn = 1 if b > 0 else -1
        if abs(th) > math.pi:
            dist = -dist
        cxx, cyy = mx - uy * dist * sgn, my + ux * dist * sgn
        k = panel_of(cxx, cyy)
        arcs[k].append(dict(h=e["handle"], cx=cxx, cy=cyy, r=r, sweep=math.degrees(th), from_bulge=True))

res = {}
for k in PANELS:
    sq = squares.get(k, [])
    res[k] = dict(
        squares=[dict(**s, rx=rel(k, s["cx"], s["cy"])[0], ry=rel(k, s["cx"], s["cy"])[1]) for s in sq],
        hexes=[dict(**h, rx=rel(k, h["cx"], h["cy"])[0], ry=rel(k, h["cx"], h["cy"])[1]) for h in hexes.get(k, [])],
        circles=[dict(**c, rx=rel(k, c["cx"], c["cy"])[0], ry=rel(k, c["cx"], c["cy"])[1]) for c in circles.get(k, [])],
        arcs=[dict(**a, rx=rel(k, a["cx"], a["cy"])[0], ry=rel(k, a["cx"], a["cy"])[1]) for a in arcs.get(k, [])],
        others=others.get(k, []),
    )
json.dump(res, open(OUT, "w", encoding="utf-8"), indent=1, ensure_ascii=False)

for k, r in res.items():
    print(f"\n== {k}: squares={len(r['squares'])} hexes={len(r['hexes'])} circles={len(r['circles'])} arcs={len(r['arcs'])} other_closed={len(r['others'])}")
    if r["squares"]:
        sides = collections.Counter(round(s["side"], 3) for s in r["squares"])
        rots = collections.Counter(round(s["rot"], 2) for s in r["squares"])
        print("   side:", dict(sides), " max side dev:", round(max(s['side_max'] - s['side_min'] for s in r['squares']), 5))
        print("   rotations(deg):", sorted(rots.items()))
    for h in r["hexes"]:
        print(f"   hex  rel=({h['rx']:.3f},{h['ry']:.3f}) edge={h['edge']:.4f} AFlat={min(h['w'],h['hgt']):.4f} ACorner={max(h['w'],h['hgt']):.4f}")
    for c in r["circles"]:
        print(f"   circ rel=({c['rx']:.3f},{c['ry']:.3f}) D={2*c['r']:.4f}")
    for a in r["arcs"]:
        print(f"   arc  rel=({a['rx']:.3f},{a['ry']:.3f}) R={a['r']:.4f} {'bulge sweep=%.1f' % a['sweep'] if a.get('from_bulge') else 'ARC %.1f..%.1f' % (a['a0'], a['a1'])}")
    for o in r["others"]:
        print(f"   other closed n={o['n']} c=({o['cx']:.3f},{o['cy']:.3f}) edges={o['edges'][:12]} bulges={[b for b in o['bulges'] if b][:6]}")

# ---------- layer registration: compare square centres P2 vs P3 (relative coords)
def match(a, b):
    out = []
    for s in a:
        t = min(b, key=lambda t: math.hypot(t["rx"] - s["rx"], t["ry"] - s["ry"]))
        out.append((s, t, math.hypot(t["rx"] - s["rx"], t["ry"] - s["ry"]), t["rot"] - s["rot"]))
    return out

m = match(res["P2_extr1p5T"]["squares"], res["P3_astel2T"]["squares"])
print("\nP2(14) vs P3(16.5) square centre offsets (relative to each panel LL): max=%.4f mean=%.4f, rot diff max=%.4f" % (
    max(x[2] for x in m), sum(x[2] for x in m) / len(m), max(abs(x[3]) for x in m)))

# nearest-neighbour pitch on P2
sq = res["P2_extr1p5T"]["squares"]
nn = []
for s in sq:
    dists = sorted(math.hypot(t["cx"] - s["cx"], t["cy"] - s["cy"]) for t in sq if t is not s)
    nn.append(dists[0])
print("P2 nearest-neighbour centre distance: min=%.3f max=%.3f" % (min(nn), max(nn)))
print("   histogram:", sorted(collections.Counter(round(x, 2) for x in nn).items()))

# list P2 squares sorted (relative)
print("\nP2 square openings (rel to panel LL), sorted by x:")
for s in sorted(sq, key=lambda s: (s["rx"])):
    print(f"   ({s['rx']:8.3f},{s['ry']:7.3f}) rot={s['rot']:+6.2f} side={s['side']:.4f} h={s['h']}")
