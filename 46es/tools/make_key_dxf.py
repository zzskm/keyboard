"""46es 키 위치 DXF 생성기 — r2 DWG P3 개구부 중심·회전각 → SolidCraft 스케치용 DXF.

입력: inspection/data/features_by_panel.json 의 P3_astel2T.squares (46개, rx/ry = r2 판 좌하단 기준, rot = deg)
출력(모두 GH60 기준점 좌표 = r2 좌표 − (dx, dy)):
  sq <side>      : 키마다 정사각형(스위치 홀·키 창 템플릿)
  notch <hole> <relief> <len> : 키마다 걸쇠 노치 십자형 (가로 (hole+2·relief)×len ∪ 세로 len×(hole+2·relief))
  cover <keycap1u> <gap> <min_rail> : (구) 열 단위 창 + 단독 키 창. 2026-11-04 후반에 silhouette 로 대체
  silhouette <cell> <close_r> <min_rail> : 키 블록 실루엣 창(좌·우 블록 2개). 키마다 cell 사각형(폭 u 키는
                                      ENVELOPE_U/WIDTHS_U 의 u·pitch − (pitch − cell))을 합치고 반지름 close_r 닫힘으로 틈을 메운 뒤
                                      가장자리 안쪽 min_rail 로 잘라 외곽선을 뽑는다. 블록 안에는 베젤이 없다

사용 예:
  python -I tools/make_key_dxf.py sq 14 0.693 0.667 out.dxf
  python -I tools/make_key_dxf.py notch 14 1.0 8 0.693 0.667 out.dxf
  python -I tools/make_key_dxf.py cover 18 1 1.6 0.693 0.667 out.dxf

키캡 폭(u) 표 WIDTHS_U 는 **미확정**이다(펌웨어 JSON 의 1.25/1.75/2u 를 P3 바닥 행 오프셋으로 추정, M17 대조 필요).
DXF 는 LINE 엔티티만 쓴다(SolidCraft sketch.insert_dxf 가 닫힌 윤곽으로 인식).
"""
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FEATURES = ROOT / "inspection" / "data" / "features_by_panel.json"
PITCH = 19.05

# (rx, ry) → 실제 키캡 폭(u). 표에 없으면 1u. (plate·노치에는 영향 없음, 커버 창 외곽선에만 씀)
# 사용자 확인(2026-11-04): 맨 아랫줄은 왼쪽부터 1.25u · 1u · 2.25u · 2u · 1u · 1u.
# (펌웨어 JSON 의 1.75u 표기와 다르며, 현물 기준은 사용자 확인값. 화살표 4키는 별도 1u)
WIDTHS_U = {
    (37.061, 19.135): 1.25,   # 아랫줄 1: rot −3, 맨 왼쪽
    (63.592, 24.777): 1.0,    # 아랫줄 2: rot −3
    (97.127, 15.742): 2.25,   # 아랫줄 3: rot −11, 왼손 썸키
    (162.342, 15.026): 2.0,   # 아랫줄 4: rot +11, 오른손 썸키
    (190.694, 22.286): 1.0,   # 아랫줄 5: rot +7
    (210.158, 25.342): 1.0,   # 아랫줄 6: rot +3
    (269.775, 82.675): 1.0,   # PgUp: rot 0, 우상단
    (269.775, 63.625): 1.0,   # PgDn: rot 0
}

# 커버 창이 수용할 폭(u) — 키캡 보유 상황에 따라 바뀔 수 있는 키(사용자 요청 2026-11-04: PgUp·PgDn, 맨 아랫줄 1~6).
# 창은 이 폭(envelope)으로 그리고, 실제 키캡은 그 안에 스위치 중심 대칭으로 앉는다(키캡이 작으면 둘레로 plate 가 보임).
# 기본 = 실제 폭 + ENVELOPE_DU. PgUp·PgDn 은 오른쪽 베젤 최소 살(1.6) 때문에 1.5u 가 상한.
ENVELOPE_DU = 0.5
ENVELOPE_U = {
    (37.061, 19.135): 1.25 + ENVELOPE_DU,
    (63.592, 24.777): 1.0 + ENVELOPE_DU,
    (97.127, 15.742): 2.25 + ENVELOPE_DU,
    (162.342, 15.026): 2.0 + ENVELOPE_DU,
    (190.694, 22.286): 1.0 + ENVELOPE_DU,
    (210.158, 25.342): 1.0 + ENVELOPE_DU,
    (269.775, 82.675): 1.5,
    (269.775, 63.625): 1.5,
}


def load_keys(dx, dy):
    data = json.load(open(FEATURES, encoding="utf-8-sig"))
    keys = []
    for q in data["P3_astel2T"]["squares"]:
        rx, ry, rot = q["rx"], q["ry"], q["rot"]
        w_u, env_u = 1.0, None
        for (kx, ky), wu in WIDTHS_U.items():
            if abs(kx - rx) < 0.01 and abs(ky - ry) < 0.01:
                w_u = wu
        for (kx, ky), eu in ENVELOPE_U.items():
            if abs(kx - rx) < 0.01 and abs(ky - ry) < 0.01:
                env_u = eu
        keys.append({"x": rx - dx, "y": ry - dy, "rot": rot, "w_u": w_u,
                     "env_u": env_u if env_u is not None else w_u})
    return keys


def rot_pt(px, py, cx, cy, deg):
    a = math.radians(deg)
    c, s = math.cos(a), math.sin(a)
    return (cx + px * c - py * s, cy + px * s + py * c)


def rect(cx, cy, w, h, deg, off=(0.0, 0.0)):
    """중심 (cx,cy)에서 회전 좌표계로 off 만큼 옮긴 w×h 사각형의 꼭짓점 4개."""
    ox, oy = off
    pts = [(-w / 2, -h / 2), (w / 2, -h / 2), (w / 2, h / 2), (-w / 2, h / 2)]
    return [rot_pt(px + ox, py + oy, cx, cy, deg) for px, py in pts]


def cross(cx, cy, w_long, w_short, deg):
    """가로 w_long×w_short ∪ 세로 w_short×w_long 십자형 12각형."""
    a, b = w_long / 2, w_short / 2
    pts = [(-a, -b), (-b, -b), (-b, -a), (b, -a), (b, -b), (a, -b),
           (a, b), (b, b), (b, a), (-b, a), (-b, b), (-a, b)]
    return [rot_pt(px, py, cx, cy, deg) for px, py in pts]


def dxf(polys, layer):
    out = ["0", "SECTION", "2", "HEADER", "9", "$INSUNITS", "70", "4", "0", "ENDSEC",
           "0", "SECTION", "2", "ENTITIES"]
    for poly in polys:
        n = len(poly)
        for i in range(n):
            x0, y0 = poly[i]
            x1, y1 = poly[(i + 1) % n]
            out += ["0", "LINE", "8", layer, "10", f"{x0:.4f}", "20", f"{y0:.4f}", "30", "0",
                    "11", f"{x1:.4f}", "21", f"{y1:.4f}", "31", "0"]
    out += ["0", "ENDSEC", "0", "EOF"]
    return "\n".join(out) + "\n"


def columns(keys, tol=4.0):
    """같은 회전각 안에서 열선(회전 좌표계 수직 오프셋)이 tol 이내인 키를 한 열로 묶는다.
    1u 가 아닌 키와 열선에서 떨어진 키는 단독."""
    groups = {}
    for k in keys:
        groups.setdefault(round(k["rot"], 3), []).append(k)
    cols, singles = [], []
    for rot, ks in groups.items():
        a = math.radians(rot)
        # 열 방향 d = (−sin, cos) (키 열은 Y 방향), 수직 p = (cos, sin)
        for k in ks:
            k["_p"] = k["x"] * math.cos(a) + k["y"] * math.sin(a)
            k["_d"] = -k["x"] * math.sin(a) + k["y"] * math.cos(a)
        ks = sorted(ks, key=lambda k: k["_p"])
        cur = []
        for k in ks:
            if cur and abs(k["_p"] - cur[-1]["_p"]) > tol:
                cols.append(cur)
                cur = []
            cur.append(k)
        if cur:
            cols.append(cur)
    # 열 안에서 1u 가 아닌 키, 또는 열선 평균에서 1.5 이상 벗어난 키는 단독으로 뺀다
    final_cols = []
    for col in cols:
        ones = [k for k in col if k["w_u"] == 1.0]
        if len(ones) >= 2:
            pm = sum(k["_p"] for k in ones) / len(ones)
            keep = [k for k in ones if abs(k["_p"] - pm) <= 1.5]
            rest = [k for k in col if k not in keep]
            if len(keep) >= 2:
                final_cols.append(keep)
                singles += rest
                continue
        singles += col
    return final_cols, singles


def cover_polys(keys, cap1u, gap, min_rail, edge):
    """edge = (xmin, xmax, ymin, ymax) 커버 외곽(GH60 좌표). 창이 가장자리에 min_rail 미만으로 다가가면
    그쪽으로 연장해 개방한다."""
    cols, singles = columns(keys)
    polys, notes = [], []
    cap_h = cap1u

    def extend(pts, deg):
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        ex = [0.0, 0.0, 0.0, 0.0]  # xmin, xmax, ymin, ymax 방향 연장량
        if xs and min(xs) - edge[0] < min_rail:
            ex[0] = (min(xs) - edge[0]) + 2
        if max(xs) > edge[1] - min_rail:
            ex[1] = (edge[1] - max(xs)) + 2
        if min(ys) - edge[2] < min_rail:
            ex[2] = (min(ys) - edge[2]) + 2
        if max(ys) > edge[3] - min_rail:
            ex[3] = (edge[3] - max(ys)) + 2
        return ex

    for col in cols:
        rot = col[0]["rot"]
        ds = [k["_d"] for k in col]
        n = len(col)
        span = max(ds) - min(ds)  # 열 길이 (중심 간)
        cx = sum(k["x"] for k in col) / n
        cy = sum(k["y"] for k in col) / n
        w = cap1u + 2 * gap
        h = span + cap_h + 2 * gap
        pts = rect(cx, cy, w, h, rot)
        ex = extend(pts, rot)
        if ex[3]:
            # 뒤쪽 개방: 회전 사각형의 뒤 변(점 2, 3)을 열 방향으로 밀어 가장자리 밖으로 보낸다
            a = math.radians(rot)
            rail = edge[3] - max(p[1] for p in pts)
            t = ex[3] / math.cos(a)
            d = (-math.sin(a), math.cos(a))
            pts = [pts[0], pts[1], (pts[2][0] + d[0] * t, pts[2][1] + d[1] * t),
                   (pts[3][0] + d[0] * t, pts[3][1] + d[1] * t)]
            notes.append(f"col rot={rot:+.0f} n={n} x~{cx:.1f}: opened to back edge (rail {rail:.2f} < {min_rail})")
        elif any(ex):
            notes.append(f"col rot={rot:+.0f} n={n} x~{cx:.1f}: near edge ex={ex} (not handled)")
        polys.append(pts)
    for k in singles:
        w = k["w_u"] * PITCH - (PITCH - cap1u) + 2 * gap
        pts = rect(k["x"], k["y"], w, cap_h + 2 * gap, k["rot"])
        polys.append(pts)
    return polys, cols, singles, notes


def silhouette_polys(keys, cell, close_r, min_rail, edge, res=0.1):
    """키 블록 실루엣 창. 키마다 cell×(cell) (폭 u 키는 u·pitch − (pitch − cell)) 회전 사각형을 래스터로 합치고,
    반지름 close_r 닫힘(팽창→침식)으로 좁은 틈·쐐기를 메운 뒤, 가장자리 안쪽 min_rail 사각형으로 잘라
    연결 성분(보통 좌·우 블록 2개)마다 외곽선을 추출해 Douglas–Peucker 로 단순화한다. (numpy + scipy.ndimage)"""
    import numpy as np
    from scipy import ndimage

    x0, x1, y0, y1 = edge
    xs = np.arange(x0 - 2, x1 + 2, res)
    ys = np.arange(y0 - 2, y1 + 2, res)
    # 좌·우 블록(회전각 부호)을 따로 닫아야 가운데 리브가 남는다. 0° 열은 오른쪽 블록
    blocks = [[k for k in keys if k["rot"] < 0], [k for k in keys if k["rot"] >= 0]]
    r = close_r / res

    def closing(B):
        # 원판 닫힘 = 팽창(빈 곳까지 거리 ≤ r) 뒤 침식(팽창 결과의 빈 곳까지 거리 > r). 거리 변환이라 빠르다.
        # 배열 밖을 '빈 곳'으로 치도록 r+2 픽셀 패딩을 두르고 계산한 뒤 잘라낸다(안 그러면 배열 가장자리에서 침식이 안 됨)
        p = int(r) + 2
        Bp = np.pad(B, p)
        D = ndimage.distance_transform_edt(~Bp) <= r
        E = ndimage.distance_transform_edt(D) > r
        return E[p:-p, p:-p]

    U = np.zeros((len(ys), len(xs)), dtype=bool)
    for block in blocks:
        Ub = closing(_raster_cells(block, cell, xs, ys, res))
        Ub = ndimage.binary_fill_holes(Ub)  # 창 안의 베젤 섬 제거
        U |= Ub
    # 가장자리 안쪽 min_rail 로 자른다
    X, Y = np.meshgrid(xs, ys)
    U &= (X >= x0 + min_rail) & (X <= x1 - min_rail) & (Y >= y0 + min_rail) & (Y <= y1 - min_rail)
    labels, n = ndimage.label(U)
    polys = []
    for lab in range(1, n + 1):
        M = labels == lab
        if M.sum() * res * res < 50:
            continue
        polys.append(_trace_boundary(M, xs, ys, res, tol=0.15))
    return polys, U, res


def _raster_cells(keys, cell, xs, ys, res):
    import numpy as np
    U = np.zeros((len(ys), len(xs)), dtype=bool)
    for k in keys:
        w = k["env_u"] * PITCH - (PITCH - cell)  # 창은 수용 폭(envelope) 기준
        pts = rect(k["x"], k["y"], w, cell, k["rot"])
        n = len(pts)
        area = sum(pts[i][0] * pts[(i + 1) % n][1] - pts[(i + 1) % n][0] * pts[i][1] for i in range(n))
        sgn = 1 if area > 0 else -1
        # 키 하나의 경계 상자 안에서만 계산
        jx0 = max(0, int((min(p[0] for p in pts) - xs[0]) / res) - 1)
        jx1 = min(len(xs), int((max(p[0] for p in pts) - xs[0]) / res) + 2)
        iy0 = max(0, int((min(p[1] for p in pts) - ys[0]) / res) - 1)
        iy1 = min(len(ys), int((max(p[1] for p in pts) - ys[0]) / res) + 2)
        Xs, Ys = np.meshgrid(xs[jx0:jx1], ys[iy0:iy1])
        m = np.ones(Xs.shape, dtype=bool)
        for i in range(n):
            (ax, ay), (bx, by) = pts[i], pts[(i + 1) % n]
            m &= sgn * ((bx - ax) * (Ys - ay) - (by - ay) * (Xs - ax)) >= 0
        U[iy0:iy1, jx0:jx1] |= m
    return U


def _trace_boundary(M, xs, ys, res, tol):
    """채워진 픽셀과 빈 픽셀 사이의 격자 변을 모아 바깥 고리를 따라간 뒤 DP 단순화."""
    import numpy as np
    H, W = M.shape
    P = np.zeros((H + 2, W + 2), dtype=bool)
    P[1:-1, 1:-1] = M
    edges = {}

    def add(a, b):
        edges.setdefault(a, []).append(b)
        edges.setdefault(b, []).append(a)

    # 격자 꼭짓점 (i, j) = 패딩 픽셀 (i, j)의 왼쪽 아래 모서리.
    # 수평 변: 픽셀 행 i와 i+1이 다르면 격자선 y=i+1 위, x는 j…j+1
    dv = P[1:, :] != P[:-1, :]
    for i, j in zip(*np.nonzero(dv)):
        add((i + 1, j), (i + 1, j + 1))
    # 수직 변: 픽셀 열 j와 j+1이 다르면 격자선 x=j+1 위, y는 i…i+1
    dh = P[:, 1:] != P[:, :-1]
    for i, j in zip(*np.nonzero(dh)):
        add((i, j + 1), (i + 1, j + 1))
    # 가장 큰 고리(바깥 윤곽) 추적
    seen = set()
    best = []
    for start in edges:
        if start in seen:
            continue
        loop = [start]
        seen.add(start)
        prev, cur = None, start
        while True:
            nbrs = [p for p in edges[cur] if p != prev]
            if not nbrs:
                break
            nxt = nbrs[0]
            if nxt == start:
                break
            loop.append(nxt)
            seen.add(nxt)
            prev, cur = cur, nxt
        if len(loop) > len(best):
            best = loop
    pts = [(xs[0] - res / 2 + (j - 1) * res, ys[0] - res / 2 + (i - 1) * res) for i, j in best]
    return _dp(pts, tol)


def _dp(pts, tol):
    """닫힌 폴리라인 Douglas–Peucker. 가장 먼 두 점으로 둘로 갈라 각각 단순화한다."""
    import math

    def dp_open(p):
        if len(p) < 3:
            return p
        (ax, ay), (bx, by) = p[0], p[-1]
        L = math.hypot(bx - ax, by - ay) or 1e-9
        dmax, idx = 0, 0
        for i in range(1, len(p) - 1):
            d = abs((bx - ax) * (ay - p[i][1]) - (ax - p[i][0]) * (by - ay)) / L
            if d > dmax:
                dmax, idx = d, i
        if dmax > tol:
            return dp_open(p[:idx + 1])[:-1] + dp_open(p[idx:])
        return [p[0], p[-1]]

    n = len(pts)
    i0 = 0
    i1 = max(range(n), key=lambda i: (pts[i][0] - pts[0][0]) ** 2 + (pts[i][1] - pts[0][1]) ** 2)
    a = dp_open(pts[i0:i1 + 1])
    b = dp_open(pts[i1:] + pts[:1])
    out = a[:-1] + b[:-1]
    return out


def main(argv):
    mode = argv[0]
    if mode == "sq":
        side, dx, dy, out = float(argv[1]), float(argv[2]), float(argv[3]), argv[4]
        keys = load_keys(dx, dy)
        polys = [rect(k["x"], k["y"], side, side, k["rot"]) for k in keys]
        Path(out).write_text(dxf(polys, "REF_r2_keys"), encoding="ascii")
        print(f"{len(polys)} squares {side} -> {out}")
    elif mode == "notch":
        hole, relief, length = float(argv[1]), float(argv[2]), float(argv[3])
        dx, dy, out = float(argv[4]), float(argv[5]), argv[6]
        keys = load_keys(dx, dy)
        polys = [cross(k["x"], k["y"], hole + 2 * relief, length, k["rot"]) for k in keys]
        Path(out).write_text(dxf(polys, "REF_r2_notch"), encoding="ascii")
        print(f"{len(polys)} crosses {hole + 2 * relief}x{length} -> {out}")
    elif mode == "cover":
        cap1u, gap, min_rail = float(argv[1]), float(argv[2]), float(argv[3])
        dx, dy, out = float(argv[4]), float(argv[5]), argv[6]
        # 커버 외곽: 하우징 내측(Wilmore 대용) − 간격 0.3. 인자로 바꾸려면 아래 네 값을 수정
        in_w, in_d, gap_c = 286.381, 95.934, 0.3
        edge = (-dx + gap_c, in_w - dx - gap_c, -dy + gap_c, in_d - dy - gap_c)
        keys = load_keys(dx, dy)
        polys, cols, singles, notes = cover_polys(keys, cap1u, gap, min_rail, edge)
        Path(out).write_text(dxf(polys, "REF_r2_cover"), encoding="ascii")
        print(f"{len(cols)} column windows + {len(singles)} single windows -> {out}")
        for c in cols:
            print(f"  col rot={c[0]['rot']:+5.1f} n={len(c)} x~{sum(k['x'] for k in c)/len(c):7.2f}")
        for k in singles:
            print(f"  single rot={k['rot']:+5.1f} ({k['x']:7.2f},{k['y']:6.2f}) w={k['w_u']}u")
        for n in notes:
            print("  NOTE", n)
    elif mode == "silhouette":
        cell, close_r, min_rail = float(argv[1]), float(argv[2]), float(argv[3])
        dx, dy, out = float(argv[4]), float(argv[5]), argv[6]
        in_w, in_d, gap_c = 286.381, 95.934, 0.3
        edge = (-dx + gap_c, in_w - dx - gap_c, -dy + gap_c, in_d - dy - gap_c)
        keys = load_keys(dx, dy)
        polys, U, res = silhouette_polys(keys, cell, close_r, min_rail, edge)
        Path(out).write_text(dxf(polys, "REF_r2_cover_sil"), encoding="ascii")
        area = float(U.sum()) * res * res
        print(f"{len(polys)} silhouette windows -> {out}; window area {area:.1f} mm2 (raster {res})")
        for p in polys:
            xs_ = [q[0] for q in p]
            ys_ = [q[1] for q in p]
            print(f"  {len(p)} vertices, x {min(xs_):.2f}..{max(xs_):.2f}, y {min(ys_):.2f}..{max(ys_):.2f}")
    else:
        print(__doc__)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
