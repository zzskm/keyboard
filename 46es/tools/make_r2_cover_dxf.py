"""r2 DWG P4(5T)/P5(2T) 3조각 커버 윤곽 → 커버 창 2개 DXF (고정 숫자, 참고용).

사용자 결정(2026-11-04): 커버 창은 아크릴 r2 버전(DWG 맨 아래 5T·2T 판) 형상을 그대로 쓴다.
r2 커버는 왼쪽 L형·가운데 T형·오른쪽 조각 3개이고, 조각 사이 두 창이 판 위·아래 변까지 열려 있다.
여기서는 조각 경계 폴리라인 4개(좌 조각 오른변, T 좌변, T 우변, 우 조각 왼변)를 읽어
창 2개를 닫힌 다각형(판 변 바깥으로 ext 만큼 연장)으로 만들고 GH60 기준점 좌표(r2 − (dx, dy))로 옮겨 LINE만으로 쓴다.

입력: inspection/derived/46es_r2_keyboard_modelspace.dxf (CADCraft 모델 공간 덤프, 판 6장이 세로로 배치)
      판은 Y 범위로 고른다(P4 5T: 150~270, P5 2T: 20~135). 두 판의 조각 윤곽은 같다(검사에서 확인).
사용: python -I tools/make_r2_cover_dxf.py <out.dxf> [dx dy ext band]
      기본 dx dy = 0.693 0.667 (TBD_pcb0_dx/dy, Wilmore 대용값), ext = 3, band = P4
"""
import math
import sys
from collections import defaultdict

SRC = r"D:\work\keyboard\46es\inspection\derived\46es_r2_keyboard_modelspace.dxf"
BANDS = {"P4": (150.0, 270.0), "P5": (20.0, 135.0)}
PLATE_W, PLATE_D = 286.4, 95.8


def read_entities(path):
    lines = open(path, encoding="utf-8", errors="replace").read().splitlines()
    i = 0
    while i < len(lines) - 3:
        if lines[i].strip() == "0" and lines[i + 1].strip() == "SECTION" and lines[i + 3].strip() == "ENTITIES":
            i += 4
            break
        i += 2
    ents, cur = [], None
    while i < len(lines) - 1:
        code, val = lines[i].strip(), lines[i + 1].rstrip("\r")
        i += 2
        if code == "0":
            if cur:
                ents.append(cur)
            if val == "ENDSEC":
                break
            cur = {"type": val, "codes": defaultdict(list)}
        elif cur is not None:
            cur["codes"][code].append(val)
    return ents


def plate_polylines(ents, band):
    """band 안의 열린 LWPOLYLINE(조각 경계)과 판 외곽 bbox를 돌려준다. 좌표는 판 좌하단 기준."""
    y0, y1 = BANDS[band]
    polys, xs, ys = [], [], []
    for e in ents:
        c = e["codes"]
        if e["type"] == "LWPOLYLINE":
            pts = list(zip(map(float, c["10"]), map(float, c["20"])))
            if not (y0 <= min(p[1] for p in pts) and max(p[1] for p in pts) <= y1):
                continue
            closed = int(c.get("70", ["0"])[0]) & 1
            xs += [p[0] for p in pts]
            ys += [p[1] for p in pts]
            if not closed and len(pts) > 2:
                polys.append(pts)
        elif e["type"] == "LINE":
            a = (float(c["10"][0]), float(c["20"][0]))
            b = (float(c["11"][0]), float(c["21"][0]))
            if y0 <= min(a[1], b[1]) and max(a[1], b[1]) <= y1:
                xs += [a[0], b[0]]
                ys += [a[1], b[1]]
    ox, oy = min(xs), min(ys)
    w, d = max(xs) - ox, max(ys) - oy
    assert abs(w - PLATE_W) < 0.01 and abs(d - PLATE_D) < 0.01, (w, d)
    out = []
    for pts in polys:
        pts = [(x - ox, y - oy) for x, y in pts]
        # 위(y=95.8)에서 시작해 아래(y=0)에서 끝나도록 방향을 맞춘다
        if pts[0][1] < pts[-1][1]:
            pts.reverse()
        assert abs(pts[0][1] - PLATE_D) < 0.01 and abs(pts[-1][1]) < 0.01, (pts[0], pts[-1])
        out.append(pts)
    out.sort(key=lambda p: p[0][0])  # 위쪽 끝 X 순: 좌 조각 오른변, T 좌변, T 우변, 우 조각 왼변
    assert len(out) == 4, len(out)
    return out


def windows(polys, ext):
    """조각 경계 4개 → 닫힌 창 다각형 2개(판 변 바깥 ext 까지 연장). 반시계/시계 무관."""
    wins = []
    for a, b in ((polys[0], polys[1]), (polys[2], polys[3])):
        poly = list(a)  # 위 → 아래 (왼쪽 경계)
        poly += [(a[-1][0], -ext), (b[-1][0], -ext)]  # 아래 변 바깥
        poly += list(reversed(b))  # 아래 → 위 (오른쪽 경계)
        poly += [(b[0][0], PLATE_D + ext), (a[0][0], PLATE_D + ext)]  # 위 변 바깥
        # 중복 점 제거
        clean = [poly[0]]
        for p in poly[1:]:
            if math.hypot(p[0] - clean[-1][0], p[1] - clean[-1][1]) > 1e-6:
                clean.append(p)
        if math.hypot(clean[0][0] - clean[-1][0], clean[0][1] - clean[-1][1]) < 1e-6:
            clean.pop()
        wins.append(clean)
    return wins


def write_dxf(path, wins, dx, dy, layer="REF_r2_COVER_P4"):
    out = ["0", "SECTION", "2", "HEADER", "9", "$INSUNITS", "70", "4", "0", "ENDSEC", "0", "SECTION", "2", "ENTITIES"]
    n = 0
    for poly in wins:
        m = len(poly)
        for i in range(m):
            a, b = poly[i], poly[(i + 1) % m]
            out += ["0", "LINE", "8", layer,
                    "10", f"{a[0] - dx:.6f}", "20", f"{a[1] - dy:.6f}", "30", "0",
                    "11", f"{b[0] - dx:.6f}", "21", f"{b[1] - dy:.6f}", "31", "0"]
            n += 1
    out += ["0", "ENDSEC", "0", "EOF"]
    open(path, "w", encoding="ascii", newline="\r\n").write("\n".join(out) + "\n")
    return n


def poly_area(poly):
    s = 0.0
    for i in range(len(poly)):
        x0, y0 = poly[i]
        x1, y1 = poly[(i + 1) % len(poly)]
        s += x0 * y1 - x1 * y0
    return abs(s) / 2


if __name__ == "__main__":
    out = sys.argv[1]
    dx = float(sys.argv[2]) if len(sys.argv) > 2 else 0.693
    dy = float(sys.argv[3]) if len(sys.argv) > 3 else 0.667
    ext = float(sys.argv[4]) if len(sys.argv) > 4 else 3.0
    band = sys.argv[5] if len(sys.argv) > 5 else "P4"
    ents = read_entities(SRC)
    polys = plate_polylines(ents, band)
    if band == "P4":  # P5와 같은지 확인
        p5 = plate_polylines(ents, "P5")
        dmax = max(math.hypot(a[0] - b[0], a[1] - b[1]) for pa, pb in zip(polys, p5) for a, b in zip(pa, pb))
        print("P4 vs P5 piece outlines: %d/%d polylines, max vertex diff %.4f" % (len(polys), len(p5), dmax))
    wins = windows(polys, ext)
    n = write_dxf(out, wins, dx, dy)
    for k, w in enumerate(wins):
        xs = [p[0] - dx for p in w]
        ys = [p[1] - dy for p in w]
        print("window %d: %d vertices, x %.3f..%.3f, y %.3f..%.3f (ext %.1f incl.), area %.1f mm2" % (
            k + 1, len(w), min(xs), max(xs), min(ys), max(ys), ext, poly_area(w)))
    print("wrote", out, "LINE", n)
