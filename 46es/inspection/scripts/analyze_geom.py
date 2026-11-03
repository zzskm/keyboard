"""Analyse CADCraft entity dump of 46es_r2_keyboard.dwg (read-only).

Chains LINE / ARC / open LWPOLYLINE segments into closed loops, groups loops
into panels, and reports outlines, openings, holes and text labels.
Output: JSON summary + console report. Never touches the source DWG.
"""
import json, math, sys, collections, re

sys.stdout.reconfigure(encoding="utf-8")
SRC, OUT = sys.argv[1], sys.argv[2]
TOL = 1e-3

d = json.loads(open(SRC, encoding="utf-8").readline())
ents = d["entities"]


def P(p):
    return (p["x"], p["y"])


def arc_pts(c, r, a0, a1, n=24):
    # degrees, CCW from a0 to a1
    while a1 <= a0:
        a1 += 360
    return [(c[0] + r * math.cos(math.radians(a0 + (a1 - a0) * i / n)),
             c[1] + r * math.sin(math.radians(a0 + (a1 - a0) * i / n))) for i in range(n + 1)]


def bulge_pts(p0, p1, b, n=12):
    if abs(b) < 1e-12:
        return [p0, p1]
    th = 4 * math.atan(b)
    dx, dy = p1[0] - p0[0], p1[1] - p0[1]
    ch = math.hypot(dx, dy)
    r = ch / (2 * math.sin(th / 2))
    mx, my = (p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2
    h = r * math.cos(th / 2)
    nx, ny = -dy / ch, dx / ch
    cx, cy = mx + nx * h, my + ny * h
    a0 = math.atan2(p0[1] - cy, p0[0] - cx)
    pts = [(cx + abs(r) * math.cos(a0 + th * i / n), cy + abs(r) * math.sin(a0 + th * i / n)) for i in range(n + 1)]
    # fix direction sign via radius sign
    if math.hypot(pts[0][0] - p0[0], pts[0][1] - p0[1]) > 1e-6:
        a0 = math.atan2(p0[1] - cy, p0[0] - cx)
    return pts


def bulge_radius(p0, p1, b):
    th = 4 * math.atan(abs(b))
    ch = math.hypot(p1[0] - p0[0], p1[1] - p0[1])
    return ch / (2 * math.sin(th / 2)), math.degrees(th)


def mtext_plain(s):
    s = re.sub(r"\{\\f[^;]*;", "", s)
    s = s.replace("\\P", " / ").replace("{", "").replace("}", "")
    return s


segs = []      # open pieces: dict(handle, pts, color)
closed = []    # already-closed loops
circles = []
texts = []
arc_radii = collections.Counter()
for e in ents:
    g = e["geometry"]
    t = g["type"]
    col = e["color"]
    if t == "line":
        segs.append(dict(h=e["handle"], pts=[P(g["a"]), P(g["b"])], col=col, kind="line"))
    elif t == "arc":
        # CADCraft arc: start/end angles (assume degrees; verify)
        c = P(g["center"])
        a0, a1 = g["start"], g["end"]
        if abs(a0) <= 2 * math.pi + 1e-9 and abs(a1) <= 2 * math.pi + 1e-9 and max(abs(a0), abs(a1)) > 0:
            unit = "rad?"
        pts = arc_pts(c, g["radius"], math.degrees(a0), math.degrees(a1))
        segs.append(dict(h=e["handle"], pts=pts, col=col, kind="arc", r=g["radius"], c=c, raw=(a0, a1)))
        arc_radii[round(g["radius"], 4)] += 1
    elif t == "lwPolyline":
        vs = g["vertices"]
        pts = []
        rads = []
        n = len(vs)
        rng = range(n) if g["closed"] else range(n - 1)
        for i in rng:
            p0 = P(vs[i]["p"]); p1 = P(vs[(i + 1) % n]["p"]); b = vs[i]["bulge"]
            if abs(b) > 1e-12:
                r, sweep = bulge_radius(p0, p1, b)
                rads.append((round(r, 4), round(sweep, 2)))
                seg = bulge_pts(p0, p1, b)
            else:
                seg = [p0, p1]
            pts.extend(seg if not pts else seg[1:])
        item = dict(h=e["handle"], pts=pts, col=col, kind="lwpoly", nv=n, closed=g["closed"], bulges=rads)
        for r, sw in rads:
            arc_radii[r] += 1
        if g["closed"]:
            closed.append(item)
        else:
            segs.append(item)
    elif t == "circle":
        circles.append(dict(h=e["handle"], c=P(g["center"]), r=g["radius"], col=col))
    elif t == "mText":
        texts.append(dict(h=e["handle"], txt=mtext_plain(g["contents"]), raw=g["contents"], at=P(g["insert"]), col=col, height=g["height"]))

# ---- chain open segments into loops
def key(p):
    return (round(p[0] / TOL), round(p[1] / TOL))

ends = collections.defaultdict(list)
for i, s in enumerate(segs):
    ends[key(s["pts"][0])].append((i, 0))
    ends[key(s["pts"][-1])].append((i, 1))
deg = collections.Counter({k: len(v) for k, v in ends.items()})
bad_nodes = {k: v for k, v in deg.items() if v != 2}

used = [False] * len(segs)
loops = []
open_chains = []
for i in range(len(segs)):
    if used[i]:
        continue
    used[i] = True
    chain = list(segs[i]["pts"])
    members = [segs[i]["h"]]
    cols = {segs[i]["col"]}
    radii = list(segs[i].get("bulges", [])) + ([(round(segs[i]["r"], 4), None)] if segs[i]["kind"] == "arc" else [])
    progressed = True
    while progressed:
        progressed = False
        k = key(chain[-1])
        for j, end in ends[k]:
            if used[j]:
                continue
            used[j] = True
            p = segs[j]["pts"] if end == 0 else segs[j]["pts"][::-1]
            chain.extend(p[1:])
            members.append(segs[j]["h"]); cols.add(segs[j]["col"])
            radii += list(segs[j].get("bulges", [])) + ([(round(segs[j]["r"], 4), None)] if segs[j]["kind"] == "arc" else [])
            progressed = True
            break
        if key(chain[-1]) == key(chain[0]) and len(members) > 1:
            break
    # try extend backwards too
    progressed = True
    while progressed and key(chain[-1]) != key(chain[0]):
        progressed = False
        k = key(chain[0])
        for j, end in ends[k]:
            if used[j]:
                continue
            used[j] = True
            p = segs[j]["pts"] if end == 1 else segs[j]["pts"][::-1]
            chain = p[:-1] + chain
            members.append(segs[j]["h"]); cols.add(segs[j]["col"])
            radii += list(segs[j].get("bulges", []))
            progressed = True
            break
    item = dict(pts=chain, members=members, cols=sorted(cols), radii=radii)
    (loops if key(chain[-1]) == key(chain[0]) else open_chains).append(item)

for c in closed:
    loops.append(dict(pts=c["pts"], members=[c["h"]], cols=[c["col"]], radii=c["bulges"], native_closed=True))


def bbox(pts):
    xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
    return [min(xs), min(ys), max(xs), max(ys)]


def area(pts):
    a = 0
    for i in range(len(pts) - 1):
        a += pts[i][0] * pts[i + 1][1] - pts[i + 1][0] * pts[i][1]
    return abs(a) / 2

for L in loops:
    L["bbox"] = bbox(L["pts"]); L["area"] = area(L["pts"])
    L["w"] = L["bbox"][2] - L["bbox"][0]; L["h"] = L["bbox"][3] - L["bbox"][1]
    L["cx"] = (L["bbox"][0] + L["bbox"][2]) / 2; L["cy"] = (L["bbox"][1] + L["bbox"][3]) / 2

loops.sort(key=lambda L: -L["area"])

# ---- panels = loops not contained in a bigger loop's bbox
def inside(b, B, eps=1e-6):
    return b[0] >= B[0] - eps and b[1] >= B[1] - eps and b[2] <= B[2] + eps and b[3] <= B[3] + eps

outers = []
for L in loops:
    if not any(inside(L["bbox"], O["bbox"]) for O in outers):
        outers.append(L)
for L in loops:
    L["parent"] = None
    if L in outers:
        continue
    cands = [i for i, O in enumerate(outers) if inside(L["bbox"], O["bbox"])]
    L["parent"] = min(cands, key=lambda i: outers[i]["area"]) if cands else None
for C in circles:
    cands = [i for i, O in enumerate(outers) if O["bbox"][0] <= C["c"][0] <= O["bbox"][2] and O["bbox"][1] <= C["c"][1] <= O["bbox"][3]]
    C["parent"] = min(cands, key=lambda i: outers[i]["area"]) if cands else None
for T in texts:
    # label sits left of panel; associate by y-range overlap / nearest
    best = min(range(len(outers)), key=lambda i: abs(T["at"][1] - outers[i]["cy"]))
    T["panel_guess"] = best

summary = dict(
    entity_count=len(ents),
    open_segments=len(segs), native_closed=len(closed),
    loops=len(loops), open_chains=len(open_chains),
    bad_nodes=len(bad_nodes),
    arc_radii=sorted(((r, n) for r, n in arc_radii.items())),
    panels=[], texts=texts, circles=circles,
    open_chain_detail=[dict(members=o["members"], bbox=bbox(o["pts"]), start=o["pts"][0], end=o["pts"][-1]) for o in open_chains],
)
for i, O in enumerate(sorted(range(len(outers)), key=lambda k: -outers[k]["cy"])):
    pass

order = sorted(range(len(outers)), key=lambda k: -outers[k]["cy"])
for rank, i in enumerate(order):
    O = outers[i]
    kids = [L for L in loops if L.get("parent") == i]
    cs = [C for C in circles if C.get("parent") == i]
    ts = [T["txt"] for T in texts if T["panel_guess"] == i]
    sq = [L for L in kids if 13.5 <= L["w"] <= 14.5 and 13.5 <= L["h"] <= 14.5]
    other = [L for L in kids if L not in sq]
    summary["panels"].append(dict(
        rank=rank, idx=i, bbox=O["bbox"], w=O["w"], h=O["h"], colors=O["cols"], outline_members=len(O["members"]),
        outline_radii=collections.Counter(r for r, _ in O["radii"]).most_common(),
        labels=ts, n_children=len(kids), n_sq14=len(sq),
        sq14=[dict(cx=L["cx"], cy=L["cy"], w=L["w"], h=L["h"], members=len(L["members"]), radii=collections.Counter(r for r, _ in L["radii"]).most_common()) for L in sq],
        others=[dict(cx=L["cx"], cy=L["cy"], w=L["w"], h=L["h"], area=L["area"], cols=L["cols"], members=len(L["members"]), radii=collections.Counter(r for r, _ in L["radii"]).most_common()) for L in other],
        circles=[dict(cx=C["c"][0], cy=C["c"][1], r=C["r"], col=C["col"]) for C in cs],
    ))
orphan_c = [C for C in circles if C["parent"] is None]
summary["orphan_circles"] = orphan_c

json.dump(summary, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)

print(f"entities={len(ents)} open_segs={len(segs)} native_closed={len(closed)} loops={len(loops)} open_chains={len(open_chains)} non-2-degree nodes={len(bad_nodes)}")
print("arc/bulge radii:", summary["arc_radii"])
print("texts:")
for T in texts:
    print(f"  {T['h']} col={T['col']} at=({T['at'][0]:.2f},{T['at'][1]:.2f}) h={T['height']} -> {T['txt']!r}")
for p in summary["panels"]:
    b = p["bbox"]
    print(f"\nPANEL rank{p['rank']} bbox=({b[0]:.3f},{b[1]:.3f})-({b[2]:.3f},{b[3]:.3f}) W={p['w']:.3f} H={p['h']:.3f} col={p['colors']} outline_pieces={p['outline_members']} R={p['outline_radii']}")
    print(f"   labels={p['labels']} children={p['n_children']} sq14={p['n_sq14']} circles={len(p['circles'])}")
    for o in sorted(p["others"], key=lambda o: (-o["cy"], o["cx"])):
        print(f"   other: c=({o['cx']:.3f},{o['cy']:.3f}) {o['w']:.3f}x{o['h']:.3f} A={o['area']:.1f} pieces={o['members']} R={o['radii']}")
    for c in p["circles"]:
        print(f"   circle: c=({c['cx']:.3f},{c['cy']:.3f}) r={c['r']:.4f} D={2*c['r']:.4f}")
if orphan_c:
    print("orphan circles:", [(round(c['c'][0],3), round(c['c'][1],3), c['r']) for c in orphan_c])
for o in summary["open_chain_detail"]:
    print("OPEN CHAIN:", o)
