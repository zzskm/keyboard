"""Assembly diagrams (SVG) drawn from the generator sources instead of by hand.

Geometry comes from the same modules that build the CAD: the Pro Micro frame, pads and snap bracket from
tools/ctrl_v5.py, switch positions and pins from tools/mounts_v5.py (make_key_dxf), mount outlines from the
mount drawing, plate/spine extents from the evaluated review model. The matrix comes from
firmware/46es_kbfirmware.json and guide/matrix_v5.json (switch number -> firmware key).

Views use the guide's conventions: "bottom" = the module turned over about X as on the bench
(+X right, front -Y at the top); "top" = seen from above (+X right, back +Y at the top).
"""
import html
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / 'tools'))

import ctrl_v5 as c  # noqa: E402
from make_key_dxf import load_keys, rect  # noqa: E402
from mounts_v5 import MX_GUIDES, profiles as mount_profiles  # noqa: E402

FONT = "IBM Plex Sans KR, Malgun Gothic, Apple SD Gothic Neo, Noto Sans KR, sans-serif"
MONO = "IBM Plex Mono, Consolas, Menlo, monospace"
ROW_COLORS = ('#d55e00', '#0072b2', '#009e73', '#cc79a7')       # Okabe-Ito: R0..R3
COL_INK, COL_SOFT = '#334155', '#e2e8f0'
INK, MUTED, RULE = '#1a2128', '#56626e', '#c9d1d9'
PLATE, PLATE_EDGE = '#eef1ee', '#9aa49f'
RISK, RISK_SOFT = '#ae352e', '#f6dedb'
BOARD, PAD_GOLD = '#24564a', '#d9a640'
ACCENT = '#0e6a75'
SPINE_GROOVES_Y = (49.0, 64.0, 72.0)     # spine underside wire grooves (v4 CAD; the guide text cites the same Y)
LEGENDS = {'BSPC': '⌫', 'PGUP': 'PgUp', 'PGDN': 'PgDn', 'SCLN': ';', 'QUOT': "'", 'COMM': ',', 'DOT': '.', 'SLSH': '/',
           'ESC': 'Esc', 'TAB': 'Tab', 'LCTL': 'Ctrl', 'LGUI': 'Win', 'RALT': 'AltGr', 'UP': '↑', 'LEFT': '←',
           'DOWN': '↓', 'RGHT': '→', 'SPC': 'Spc'}


def esc(s):
    return html.escape(str(s), quote=True)


def svg(width, height, body, label):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width:.0f} {height:.0f}" width="{width:.0f}" '
            f'height="{height:.0f}" role="img" aria-label="{esc(label)}" font-family="{FONT}">'
            f'<rect width="100%" height="100%" fill="#ffffff"/>{body}</svg>\n')


def text(x, y, s, size=14, fill=INK, anchor='middle', weight=400, mono=False, extra=''):
    family = f' font-family="{MONO}"' if mono else ''
    return (f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" fill="{fill}" text-anchor="{anchor}" '
            f'font-weight="{weight}" dominant-baseline="middle"{family}{extra}>{esc(s)}</text>')


def poly(points, fill='none', stroke='none', width=1.0, extra=''):
    pts = ' '.join(f'{x:.1f},{y:.1f}' for x, y in points)
    return f'<polygon points="{pts}" fill="{fill}" stroke="{stroke}" stroke-width="{width}"{extra}/>'


def line(points, stroke=INK, width=2.0, extra=''):
    pts = ' '.join(f'{x:.1f},{y:.1f}' for x, y in points)
    return (f'<polyline points="{pts}" fill="none" stroke="{stroke}" stroke-width="{width}" stroke-linecap="round" '
            f'stroke-linejoin="round"{extra}/>')


def box(x0, y0, x1, y1, **kw):
    return poly([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], **kw)


def chip(x, y, s, fill, ink='#ffffff', w=40, h=22, size=13):
    return (f'<rect x="{x - w / 2:.1f}" y="{y - h / 2:.1f}" width="{w}" height="{h}" rx="5" fill="{fill}"/>'
            + text(x, y + .5, s, size, ink, weight=700, mono=True))


def arrow(x0, y0, x1, y1, color=ACCENT, width=3.0, head=10):
    a = math.atan2(y1 - y0, x1 - x0)
    tip = [(x1, y1), (x1 - head * math.cos(a - .45), y1 - head * math.sin(a - .45)),
           (x1 - head * math.cos(a + .45), y1 - head * math.sin(a + .45))]
    back = (x1 - head * .7 * math.cos(a), y1 - head * .7 * math.sin(a))
    return line([(x0, y0), back], color, width) + poly(tip, fill=color)


HATCH = ('<defs><pattern id="hatch" width="7" height="7" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">'
         f'<line x1="0" y1="0" x2="0" y2="7" stroke="{RISK}" stroke-width="1.4" opacity=".55"/></pattern>'
         '<pattern id="empty" width="8" height="8" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">'
         f'<line x1="0" y1="0" x2="0" y2="8" stroke="{RULE}" stroke-width="2"/></pattern></defs>')


# ------------------------------------------------------------------ data
def legend(code):
    kid, fields = code['id'], code['fields']
    if kid in ('SFT_T()', 'ALT_T()'):
        inner = legend(fields[0])
        return f"{inner}/{'⇧' if kid.startswith('SFT') else 'Alt'}"
    if kid == 'LT()':
        return f'{legend(fields[1])}/L{fields[0]}'
    if kid == 'MO()':
        return f'MO{fields[0]}'
    name = kid.removeprefix('KC_')
    return LEGENDS.get(name, name)


def load(ctx):
    fw = json.loads((ROOT / 'firmware/46es_kbfirmware.json').read_text(encoding='utf-8-sig'))['keyboard']
    mapping = json.loads((HERE / 'matrix_v5.json').read_text(encoding='utf-8'))
    fkeys = {k['id']: k for k in fw['keys']}
    keys = load_keys(.693, .667)
    s2k = {int(s): k for s, k in mapping['switch_to_key'].items()}
    if sorted(s2k) != list(range(1, len(keys) + 1)) or sorted(s2k.values()) != sorted(fkeys):
        raise SystemExit('diagrams: matrix_v5.json must map every CAD switch to one firmware key')
    out = []
    for n, key in enumerate(keys, 1):
        f = fkeys[s2k[n]]
        out.append(dict(n=n, x=key['x'], y=key['y'], rot=key['rot'], w=key['w_u'], row=f['row'], col=f['col'],
                        legend=legend(f['keycodes'][0]), fw_w=f['state']['w'],
                        uncertain=mapping['uncertain'].get(str(n))))
    for k in out:
        if k['w'] in (1.25, 2.0) and k['fw_w'] != k['w']:
            raise SystemExit(f"diagrams: switch {k['n']} is {k['w']}u but firmware key is {k['fw_w']}u")
    for r in range(3):   # the alpha rows run left to right in CAD X, half by half
        cols = [k['col'] for k in sorted((k for k in out if k['row'] == r), key=lambda k: k['x'])]
        if cols != sorted(cols):
            raise SystemExit(f'diagrams: firmware row {r} is out of X order on the plate: {cols}')
    # the CAD this page shows must be the one the generator modules describe
    for name, value in [('TBD_ctrl_X', c.PCB_X), ('TBD_ctrl_Y', c.PCB_Y), ('ctrl5_hook_e', c.HOOK_E)]:
        if name in ctx.params and abs(ctx.params[name] - value) > 1e-3:
            raise SystemExit(f'diagrams: {name} is {ctx.params[name]} in the review CAD but {value} in ctrl_v5.py')
    pins = fw['pins']
    role = {name: f'R{i}' for i, name in enumerate(pins['row'])} | {name: f'C{i}' for i, name in enumerate(pins['col'])}
    return out, pins, role


def pad_side_name(side):
    # Component side faces -Z and USB points -X: the TX0 header (pin-out row 0) is then on the +Y edge.
    return ('RAW', 1) if side < 0 else ('TX', 0)


def pad_table(role):
    rows = []
    for side in (-1, 1):
        label, index = pad_side_name(side)
        y = c.PCB_Y + c.PAD_EDGE if side < 0 else c.PCB_Y + c.PCB_W - c.PAD_EDGE
        for n, name in enumerate(c.PINOUT[index], 1):
            rows.append(dict(side=side, header=label, n=n, name=name, role=role.get(name),
                             x=c.PCB_X + c.PAD_X0 + c.PAD_PITCH * (n - 1), y=y))
    return rows


def role_color(r):
    return ROW_COLORS[int(r[1:])] if r and r.startswith('R') else COL_INK


def greedy_path(points):
    best = None
    for start in range(len(points)):
        left, path = list(range(len(points))), []
        cur = left.pop(start)
        path.append(cur)
        total = 0.0
        while left:
            nxt = min(left, key=lambda j: math.dist(points[cur], points[j]))
            total += math.dist(points[cur], points[nxt])
            left.remove(nxt)
            path.append(nxt)
            cur = nxt
        if best is None or total < best[0]:
            best = (total, path)
    return [points[i] for i in best[1]]


# ------------------------------------------------------------------ wiring map
def wiring_map(ctx, keys, pins, role):
    plates = [ctx.bodies[n]['bbox'] for n in ('PLATE_L_SPLIT_V1', 'PLATE_R_SPLIT_V1')]
    spine = ctx.bodies['PLATE_SPINE_V1']['bbox']
    x_lo = min(b['min'][0] for b in plates) - 6
    x_hi = max(b['max'][0] for b in plates) + 6
    y_lo = min(b['min'][1] for b in plates) - 6
    y_hi = max(b['max'][1] for b in plates) + 6
    S, top = 4.0, 8.0
    W = (x_hi - x_lo) * S

    def P(x, y):        # bottom view: front (-Y) up, +X right
        return ((x - x_lo) * S, top + (y - y_lo) * S)

    def shape(geom, **kw):
        return poly([P(*p) for p in list(geom.exterior.coords)[:-1]], **kw)

    body = [HATCH]
    for b in plates:
        body.append(box(*P(b['min'][0], b['min'][1]), *P(b['max'][0], b['max'][1]), fill=PLATE, stroke=PLATE_EDGE,
                        width=1.5))
    seam = ctx.params.get('split_center_X', (plates[0]['max'][0] + plates[1]['min'][0]) / 2)
    body.append(line([P(seam, y_lo + 4), P(seam, y_hi - 4)], PLATE_EDGE, 1.5, ' stroke-dasharray="6 5"'))
    for suffix, prof in mount_profiles().items():
        name = prof['mount']
        if name in ctx.bodies:
            bb = ctx.bodies[name]['bbox']
            ox0, oy0, ox1, oy1 = prof['outline'].bounds
            if max(abs(ox0 - bb['min'][0]), abs(oy0 - bb['min'][1]), abs(ox1 - bb['max'][0]), abs(oy1 - bb['max'][1])) > .8:
                raise SystemExit(f'diagrams: mount outline {suffix} does not match {name} in the review CAD')
        body.append(shape(prof['outline'], fill='url(#hatch)', stroke=RISK, width=1.2, extra=' stroke-opacity=".7"'))
    body.append(box(*P(spine['min'][0], spine['min'][1]), *P(spine['max'][0], spine['max'][1]), fill='#d7dcd8',
                    stroke=PLATE_EDGE, width=1))
    half = ctx.params.get('spine_wire_W', 3.0) / 2
    for gy in SPINE_GROOVES_Y:
        body.append(box(*P(spine['min'][0] - 1.5, gy - half), *P(spine['max'][0] + 1.5, gy + half), fill=ACCENT))
    f = c.frame()
    body.append(box(*P(f['x0'], f['y0']), *P(f['x1'], f['y1']), fill=BOARD, stroke='#10302a', width=1.5))
    body.append(box(*P(f['x0'] - .75, f['yc'] - 3.8), *P(f['x0'] + 5.4, f['yc'] + 3.8), fill='#b9c2c9'))
    for pad in pad_table(role):
        cx, cy = P(pad['x'], pad['y'])
        color = role_color(pad['role']) if pad['role'] else '#8b949c'
        body.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{3.6 if pad["role"] else 2.6}" fill="{color}" '
                    f'stroke="#ffffff" stroke-width="1"/>')
    for label, y in (('RAW', f['y0'] + 3.4), ('TX', f['y1'] - 3.4)):
        hx, hy = P(f['x0'] + 7.0, y)
        body.append(text(hx, hy, label, 11, '#ffffff', 'start', 700))

    def beside(k, ox, oy):      # a point in the key's own frame, so wires pass beside its labels
        a = math.radians(k['rot'])
        return k['x'] + ox * math.cos(a) - oy * math.sin(a), k['y'] + ox * math.sin(a) + oy * math.cos(a)

    # wires: rows per plate half (solid, below the labels), columns (dashed, left of the labels)
    for r in range(4):
        for half_keys in ([k for k in keys if k['row'] == r and k['x'] < seam], [k for k in keys if k['row'] == r and k['x'] >= seam]):
            if len(half_keys) > 1:
                body.append(line([P(*p) for p in greedy_path([beside(k, 0, 5.3) for k in half_keys])],
                                 ROW_COLORS[r], 4.0, ' opacity=".9"'))
    for col in range(12):
        ck = [k for k in keys if k['col'] == col]
        if len(ck) > 1:
            body.append(line([P(*p) for p in greedy_path([beside(k, -5.0, 0) for k in ck])], COL_INK, 2.0,
                             ' stroke-dasharray="5 4" opacity=".8"'))
    for k in keys:
        corners = [P(*p) for p in rect(k['x'], k['y'], 13.98, 13.98, k['rot'])]
        color = ROW_COLORS[k['row']]
        body.append(poly(corners, fill=color, stroke=color, width=1.5, extra=' fill-opacity=".16"'))
        cx, cy = P(k['x'], k['y'])
        body.append(text(cx, cy - 6, k['legend'], 15 if len(k['legend']) < 4 else 12, INK, weight=700))
        body.append(text(cx, cy + 12, f"C{k['col']}", 11, COL_INK, mono=True))
        if k['uncertain']:
            body.append(f'<circle cx="{cx + 20:.1f}" cy="{cy - 20:.1f}" r="9" fill="{RISK}"/>'
                        + text(cx + 20, cy - 19.5, '?', 13, '#ffffff', weight=700))
    map_h = top + (y_hi - y_lo) * S
    # legend strip
    y = map_h + 26
    pads = {p['name']: p for p in pad_table(role)}
    items = []
    for i, name in enumerate(pins['row']):
        items.append((f'R{i}', ROW_COLORS[i], f"{name} · {pads[name]['header']} {pads[name]['n']}"))
    for i, name in enumerate(pins['col']):
        items.append((f'C{i}', COL_INK, f"{name} · {pads[name]['header']} {pads[name]['n']}"))
    per_row = 8
    cell = W / per_row
    for i, (tag, color, desc) in enumerate(items):
        gx = 14 + (i % per_row) * cell
        gy = y + (i // per_row) * 30
        body.append(chip(gx + 20, gy, tag, color))
        body.append(text(gx + 46, gy, desc, 12, INK, 'start', mono=True))
    y += 3 * 30 + 6
    marks = [(box(14, y - 9, 38, y + 9, fill='url(#hatch)', stroke=RISK, width=1.2), 'mount 자리 · 배선이 지나면 안 됨'),
             (box(14, y - 4, 38, y + 4, fill=ACCENT), f'spine 배선 홈 Y {" · ".join(f"{g:.0f}" for g in SPINE_GROOVES_Y)} · 행 선이 이음을 건너는 곳'),
             (line([(14, y), (38, y)], ROW_COLORS[0], 4), '실선 = 행 선(색), 점선 = 열 선(C 번호)')]
    for i, (mark, desc) in enumerate(marks):
        gx = 14 + i * (W / 3)
        body.append(f'<g transform="translate({gx - 14:.1f},0)">{mark}</g>')
        body.append(text(gx + 32, y, desc, 12, INK, 'start'))
    y += 28
    body.append(f'<circle cx="26" cy="{y:.1f}" r="9" fill="{RISK}"/>' + text(26, y + .5, '?', 13, '#ffffff', weight=700))
    body.append(text(44, y, 'Esc·Tab 두 키의 순서는 펌웨어 배치도로 정해지지 않는다. r2 실물 배선과 대조한다.', 12, INK, 'start'))
    return svg(W, y + 20, ''.join(body), 'plate 아랫면 배선 지도: 행·열과 Pro Micro 핀')


# ------------------------------------------------------------------ Pro Micro pin map
def pinmap(view, role):
    S, mx, band = 20.0, 34.0, 88.0
    W = c.PCB_L * S + 2 * mx
    H = c.PCB_W * S + 2 * band

    def P(x, y):
        u = (x - c.PCB_X) * S + mx
        v = (y - c.PCB_Y) if view == 'component' else (c.PCB_Y + c.PCB_W - y)
        return u, band + v * S

    body = [box(*P(c.PCB_X, c.PCB_Y), *P(c.PCB_X + c.PCB_L, c.PCB_Y + c.PCB_W), fill=BOARD, stroke='#10302a', width=2)]
    if view == 'component':
        for name, ((x, y), (l, w), _) in c.COMPONENTS.items():
            fill = '#c3cbd2' if name in ('USB', 'CRYSTAL') else '#3b4148'
            body.append(box(*P(c.PCB_X + x, c.PCB_Y + y), *P(c.PCB_X + x + l, c.PCB_Y + y + w), fill=fill, stroke='#20262b', width=1))
        (mx0, my0), side, _ = c.MCU
        cx, cy = P(c.PCB_X + mx0, c.PCB_Y + my0)
        r = side / math.sqrt(2) * S
        body.append(poly([(cx, cy - r), (cx + r, cy), (cx, cy + r), (cx - r, cy)], fill='#15181b'))
        body.append(text(cx, cy, '칩', 13, '#c3cbd2'))
    else:
        (x, y), (l, w), _ = c.COMPONENTS['USB']
        body.append(box(*P(c.PCB_X + x, c.PCB_Y + y), *P(c.PCB_X + x + l, c.PCB_Y + y + w), stroke='#c3cbd2', width=1.5,
                        extra=' stroke-dasharray="5 4"'))
        ux, uy = P(c.PCB_X + 2.3, c.PCB_Y + 9)
        body.append(text(ux, uy, 'USB(반대면)', 11, '#c3cbd2'))
    for pad in pad_table(role):
        cx, cy = P(pad['x'], pad['y'])
        r = pad['role']
        ring = role_color(r) if r else '#8b949c'
        body.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{c.PAD_R * S:.1f}" fill="{PAD_GOLD}" stroke="{ring}" '
                    f'stroke-width="{4 if r else 1.5}"/>'
                    f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{.48 * S:.1f}" fill="#ffffff"/>')
        outward = -1 if cy < band + c.PCB_W * S / 2 else 1
        inner = cy - outward * 28
        body.append(text(cx, inner, pad['n'], 12, '#cfe3dc', mono=True))
        name_y = cy + outward * 36
        body.append(text(cx, name_y, pad['name'], 13, INK if r or pad['name'] in ('RST', 'GND') else '#9aa3ab',
                         weight=600, mono=True))
        if r:
            body.append(chip(cx, cy + outward * 62, r, role_color(r)))
        elif pad['name'] == 'RST':
            body.append(chip(cx, cy + outward * 62, '리셋', '#ffffff', RISK, 40, 22, 12)
                        .replace('fill="#ffffff"/>', f'fill="#ffffff" stroke="{RISK}"/>', 1))
    for side in (-1, 1):
        header, _ = pad_side_name(side)
        y = c.PCB_Y + c.PAD_EDGE if side < 0 else c.PCB_Y + c.PCB_W - c.PAD_EDGE
        hx, hy = P(c.PCB_X + 1.25, y)
        body.append(text(hx, hy, header, 13, '#ffffff', weight=700))
    # edge hints in the same view as the 3D/2D drawings
    edge_top, edge_bottom = (('앞(케이스 앞)', '뒤') if view == 'component' else ('뒤', '앞(케이스 앞)'))
    body.append(text(mx, 14, f'↑ {edge_top}', 11, MUTED, 'start'))
    body.append(text(mx, H - 12, f'↓ {edge_bottom}', 11, MUTED, 'start'))
    face = '부품면(케이스 바닥 쪽)' if view == 'component' else '납땜면(plate 쪽 · 전선을 붙이는 면)'
    return svg(W, H, ''.join(body), f'Pro Micro {face} 핀 배치')


# ------------------------------------------------------------------ diode
def diode():
    W, H = 620, 250
    b = []
    b.append(line([(70, 40), (70, 210)], COL_INK, 5, ' stroke-dasharray="9 6"'))
    b.append(text(70, 228, '열 선(C)', 13, COL_INK, weight=600))
    b.append(line([(70, 110), (160, 110)], INK, 3))
    b.append(box(160, 80, 250, 140, fill='#f3f5f1', stroke=INK, width=2))
    b.append(text(205, 110, '스위치', 14, INK, weight=600))
    b.append(f'<circle cx="160" cy="110" r="5" fill="{PAD_GOLD}"/><circle cx="250" cy="110" r="5" fill="{PAD_GOLD}"/>')
    b.append(line([(250, 110), (320, 110)], INK, 3))
    # diode body with cathode band on the row side
    b.append('<rect x="320" y="96" width="110" height="28" rx="12" fill="#d6913a"/>')
    b.append('<rect x="404" y="96" width="16" height="28" fill="#1a1a1a"/>')
    b.append(line([(430, 110), (510, 110)], INK, 3))
    b.append(line([(510, 40), (510, 210)], ROW_COLORS[1], 6))
    b.append(text(510, 228, '행 선(R)', 13, ROW_COLORS[1], weight=600))
    b.append(arrow(412, 62, 412, 92, RISK, 3, 10))
    b.append(text(412, 48, '검은 띠 = 행 쪽', 14, RISK, weight=700))
    b.append(arrow(110, 160, 470, 160, ACCENT, 2.5, 10))
    b.append(text(290, 182, '전류: 열 → 스위치 → 다이오드 → 행 (COL2ROW)', 13, ACCENT, weight=600))
    return svg(W, H, ''.join(b), '다이오드 방향: 띠가 행 쪽')


# ------------------------------------------------------------------ snap bracket
def snap_panels():
    f = c.frame()
    x0, x1, y0, y1 = f['x0'], f['x1'], f['y0'], f['y1']
    zc, zs = f['zc'], f['zs']
    S = 13.0
    out = []

    # ① side view X-Z, module upside down on the bench (plate at the bottom)
    X0, X1, Z0, Z1 = 109.0, 152.0, -3.0, 10.0

    def P(x, z):
        return (x - X0) * S + 10, (z - Z0) * S + 30

    def bench(parts, tilt=0.0):
        b = []
        b.append(box(*P(X0 + 1, 8.0), *P(X1 - 1, 10.0), fill=PLATE, stroke=PLATE_EDGE, width=1.5))
        b.append(text(P(X0 + 2, 9)[0], P(X0 + 2, 9)[1], 'plate (아래가 스위치)', 11, MUTED, 'start'))
        b.append(box(*P(c.SHOULDER_X0, c.ROOF_Z), *P(x1 + c.CLR + c.WALL, c.ROOF_TOP), fill='#9aa0a8'))
        b.append(box(*P(c.BLOCK_X0, c.SUPPORT_Z), *P(c.BLOCK_X1, c.ROOF_Z), fill='#9aa0a8'))
        b.append(box(*P(x1 + c.CLR, c.TAB_Z), *P(x1 + c.CLR + c.WALL, c.ROOF_TOP), fill='#9aa0a8'))
        b.append(box(*P(x1 - c.END_D, c.CATCH_Z - c.LIP_FLAT), *P(x1 + c.CLR, c.CATCH_Z), fill='#7c838c'))
        b.append(box(*P(x1 - c.END_D, c.SUPPORT_Z), *P(x1 + c.CLR, c.ROOF_Z), fill='#9aa0a8'))
        b.append(box(*P(c.SHOULDER_X0, c.LOW_Z), *P(x0 - c.CLR, c.ROOF_Z), fill='#9aa0a8'))
        b.append(box(*P(c.ARM_FREE_X, c.TAB_Z), *P(c.ARM_ROOT_X, c.ROOF_Z), stroke='#5f6770', width=1.5,
                     extra=' stroke-dasharray="5 4"'))
        # board and its parts, rotated about the +X end under the lip
        px, pz = x1 - .9, (zc + zs) / 2
        a = math.radians(tilt)

        def R(x, z):
            dx, dz = x - px, z - pz
            return P(px + dx * math.cos(a) - dz * math.sin(a), pz + dx * math.sin(a) + dz * math.cos(a))

        b.append(poly([R(x0, zc), R(x1, zc), R(x1, zs), R(x0, zs)], fill=BOARD, stroke='#10302a', width=1.5))
        for name, ((x, _), (l, _), depth) in c.COMPONENTS.items():
            fill = '#c3cbd2' if name in ('USB', 'CRYSTAL') else '#3b4148'
            b.append(poly([R(x0 + x, zc - depth), R(x0 + x + l, zc - depth), R(x0 + x + l, zc), R(x0 + x, zc)], fill=fill))
        (mxx, _), side, depth = c.MCU
        half = side / math.sqrt(2)
        b.append(poly([R(x0 + mxx - half, zc - depth), R(x0 + mxx + half, zc - depth), R(x0 + mxx + half, zc), R(x0 + mxx - half, zc)], fill='#15181b'))
        b.extend(parts(P, R))
        return b

    def first(P, R):
        b = [arrow(*P(x0 + 10, -2.2), *P(x1 - 5, -1.1), ACCENT, 3, 11),
             text(P(x0 + 12, -2.6)[0], P(x0 + 12, -2.6)[1] - 4, '+X 끝을 끝 립 아래로', 14, ACCENT, 'start', 700)]
        lx, lz = P(x1 - .3, c.CATCH_Z - c.LIP_FLAT)
        b.append(text(lx, lz - 12, '끝 립', 12, INK, 'end', 600))
        return b

    def second(P, R):
        b = [arrow(*P(x0 + 2.5, -3.0), *P(x0 + 2.5, -.6), ACCENT, 3.5, 12),
             text(P(x0 + 4.5, -2.4)[0], P(x0 + 4.5, -2.4)[1], 'USB 쪽을 눌러 딸깍', 14, ACCENT, 'start', 700)]
        ax, az = P(c.ARM_ROOT_X + .6, c.SUPPORT_Z + 1.2)
        b.append(text(ax, az, '← 점선: 양옆 암', 11, MUTED, 'start'))
        return b

    W1, H1 = (X1 - X0) * S + 20, (Z1 - Z0) * S + 40
    out.append((svg(W1, H1, ''.join(bench(first, tilt=8.0)), '스냅 끼우기 1: +X 끝을 끝 립 아래로'),
                '① 모듈을 뒤집어 놓고 +X 끝을 기울여 끝 립 아래로 넣는다(측면).'))
    out.append((svg(W1, H1, ''.join(bench(second)), '스냅 끼우기 2: USB 쪽을 누른다'),
                '② USB 쪽을 누르면 양옆 암이 벌어졌다가 PCB 긴 변 위로 걸린다.'))

    # ③ section Y-Z near the arm lips: the arm flexes out and snaps back over the board edge
    Y0, Y1 = y0 - 5.0, y1 + 5.0
    S2 = 13.0

    def Q(y, z):
        return (y - Y0) * S2 + 10, (z - Z0) * S2 + 30

    b = [box(*Q(Y0 + .5, 8.0), *Q(Y1 - .5, 10.0), fill=PLATE, stroke=PLATE_EDGE, width=1.5),
         box(*Q(y0 - 3.8, c.ROOF_Z), *Q(y1 + 3.8, c.ROOF_TOP), fill='#9aa0a8')]
    for sgn, edge in ((-1, y0), (1, y1)):
        inner = edge + sgn * c.CLR
        arm = (inner, inner + sgn * c.ARM_T_TIP)
        rail = (arm[1] + sgn * c.STOP_GAP, arm[1] + sgn * (c.STOP_GAP + 1.2))
        b.append(box(*Q(min(rail), c.LOW_Z), *Q(max(rail), c.ROOF_Z), fill='#c6cbd1'))
        b.append(box(*Q(min(arm), c.TAB_Z), *Q(max(arm), c.ROOF_Z - .6), fill='#9aa0a8'))
        tip = edge - sgn * c.HOOK_E
        b.append(poly([Q(inner, c.CATCH_Z), Q(tip, c.CATCH_Z), Q(tip, c.CATCH_Z - c.LIP_FLAT + .45),
                       Q(inner, c.CATCH_Z - c.LIP_FLAT - .45)], fill='#7c838c'))
        flex = sgn * (c.HOOK_E + c.CLR)
        b.append(box(*Q(min(arm) + flex, c.TAB_Z), *Q(max(arm) + flex, c.ROOF_Z - .6), stroke='#5f6770', width=1.5,
                     extra=' stroke-dasharray="4 4"'))
        b.append(arrow(*Q((arm[0] + arm[1]) / 2, 3.0), *Q((arm[0] + arm[1]) / 2 + flex * 1.8, 3.0), RISK, 2.5, 8))
        b.append(box(*Q(edge - sgn * 1.5 if sgn > 0 else edge, c.SUPPORT_Z), *Q(edge if sgn > 0 else edge + 1.5, c.ROOF_Z),
                     fill='#9aa0a8'))
    b.append(box(*Q(y0, zc), *Q(y1, zs), fill=BOARD, stroke='#10302a', width=1.5))
    lx, lz = Q(y0 + .2, c.CATCH_Z - c.LIP_FLAT)
    b.append(text(lx + 4, lz - 16, f'걸림 {c.HOOK_E:g}', 13, INK, 'start', 700))
    mx_, mz_ = Q((y0 + y1) / 2, zc - 1.6)
    b.append(text(mx_, mz_, '부품면(위로)', 12, INK))
    b.append(text(Q((y0 + y1) / 2, 9.0)[0], Q((y0 + y1) / 2, 9.0)[1], 'plate', 11, MUTED))
    W3, H3 = (Y1 - Y0) * S2 + 20, (Z1 - Z0) * S2 + 40
    out.append((svg(W3, H3, ''.join(b), '스냅 단면: 암이 벌어졌다가 걸린다'),
                f'단면. 점선은 끼울 때 벌어진 암(바깥으로 {c.HOOK_E + c.CLR:.1f}), 립은 PCB 가장자리를 {c.HOOK_E:g} 덮는다.'))

    # ④ bench view (module upside down): release and the two pegs to clip
    BX0, BX1, BY0, BY1 = 101.0, 156.0, 6.0, 42.0
    S4 = 11.0

    def T(x, y):
        return (x - BX0) * S4 + 10, (y - BY0) * S4 + 10

    b = [HATCH]
    for key in load_keys(.693, .667):
        if not (BX0 - 8 < key['x'] < BX1 + 8 and BY0 - 8 < key['y'] < BY1 + 8):
            continue
        b.append(poly([T(*p) for p in rect(key['x'], key['y'], 13.98, 13.98, key['rot'])], fill='#f1f2ee', stroke='#a6ada9', width=1.2))
    reach = c.CLR + c.ARM_T_TIP + c.STOP_GAP + 1.2
    b.append(box(*T(c.SHOULDER_X0, y0 - reach), *T(c.BLOCK_X1, y1 + reach), fill='#d1d5da'))
    b.append(box(*T(c.BLOCK_X1, f['yc'] - c.STRIP_HALF), *T(x1 + c.CLR + c.WALL, f['yc'] + c.STRIP_HALF), fill='#d1d5da'))
    b.append(box(*T(x0, y0), *T(x1, y1), fill=BOARD, stroke='#10302a', width=1.5))
    (ux, uy), (ul, uw), _ = c.COMPONENTS['USB']
    b.append(box(*T(x0 + ux, y0 + uy), *T(x0 + ux + ul, y0 + uy + uw), fill='#c3cbd2'))
    for sgn, edge in ((-1, y0), (1, y1)):
        inner = edge + sgn * c.CLR
        b.append(box(*T(c.ARM_FREE_X, inner), *T(c.ARM_ROOT_X, inner + sgn * c.ARM_T_TIP), fill='#7c838c'))
        b.append(box(*T(c.ARM_FREE_X, edge - sgn * c.HOOK_E), *T(c.ARM_FREE_X + c.LIP_L, inner), fill='#5f6770'))
        sx, sy = T(c.ARM_FREE_X + 1.2, inner + sgn * c.ARM_T_TIP)
        b.append(arrow(sx, sy, sx, sy + sgn * 34, RISK, 3, 10))
    b.append(text(*T(c.ARM_FREE_X + 3.0, y0 - 4.6), '① 암 끝을 바깥으로', 13, RISK, 'start', 700))
    b.append(arrow(*T(x0 + 6, f['yc']), *T(x0 - 8, f['yc']), ACCENT, 3.5, 12))
    b.append(text(*T(x0 - 2, f['yc'] - 2.6), '② USB 쪽을 들고 −X로', 13, ACCENT, 'end', 700))
    for n, side in sorted(c.CLIPPED_PEGS):
        key = load_keys(.693, .667)[n - 1]
        a = math.radians(key['rot'])
        for gx, r in MX_GUIDES[1:]:
            px, py = key['x'] + gx * math.cos(a), key['y'] + gx * math.sin(a)
            cut = (gx > 0) == (side > 0)
            cx, cy = T(px, py)
            b.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r * S4:.1f}" fill="{RISK if cut else "#a6ada9"}"/>')
            if cut:
                b.append(text(cx + (-14 if n == 1 else 14), cy + 30, f'✂ {n}번 다리', 13, RISK, 'end' if n == 1 else 'start', 700))
    W4, H4 = (BX1 - BX0) * S4 + 20, (BY1 - BY0) * S4 + 20
    out.append((svg(W4, H4, ''.join(b), '스냅 빼기와 자를 스위치 다리'),
                '모듈을 뒤집은 상태. 빼기: 양옆 암 끝을 벌리고 USB 쪽을 들어 −X로. 빨간 점은 처음 끼우기 전에 자르는 1·23번 스위치 다리.'))
    return out


# ------------------------------------------------------------------ magnets
def magnet_panels():
    def panel(n, title, parts, caption):
        b = [text(16, 22, n, 18, ACCENT, 'start', 700), text(44, 22, title, 14, INK, 'start', 700)] + parts
        return svg(300, 210, ''.join(b), title), caption

    def plate():
        return [box(30, 150, 270, 176, fill=PLATE, stroke=PLATE_EDGE, width=1.5),
                box(130, 136, 170, 150, fill='#dfe4df', stroke=PLATE_EDGE, width=1.5),
                text(150, 190, 'plate 앞 가장자리 받침', 11, MUTED)]

    def magnet(y, mark=False):
        out = [f'<rect x="133" y="{y}" width="34" height="16" rx="3" fill="#7d8790" stroke="#4a525a" stroke-width="1.5"/>']
        if mark:
            out.append(f'<circle cx="150" cy="{y + 8}" r="4" fill="{RISK}"/>')
        return out

    one = plate() + magnet(134) + [
        text(150, 66, '에폭시로 먼저 붙인다', 12, INK), text(150, 86, 'L·R 두 곳 모두 같은 극이 위', 12, INK),
        arrow(150, 98, 150, 128, ACCENT, 2.5, 9)]
    two = plate() + magnet(134) + magnet(117, True) + [
        text(150, 66, '짝 자석을 그 위에 붙인 채', 12, INK), text(150, 86, '윗면에 점을 찍는다', 12, RISK, weight=700)]
    three = [box(40, 58, 260, 86, fill='#cfe0f3', stroke='#3f7fd0', width=1.5), box(132, 86, 168, 104, fill='#ffffff', stroke='#3f7fd0', width=1.5),
             text(150, 46, '커버 L·R 아래 다리 끝(포켓이 아래)', 11, MUTED)] + magnet(87, True) + [
        arrow(150, 146, 150, 110, ACCENT, 2.5, 9),
        text(150, 166, '점 찍은 면이 포켓 바닥으로', 12, RISK, weight=700), text(150, 186, '= 맞붙던 면이 plate를 향한다', 12, INK)]
    return [panel('①', 'plate 쪽', one, '① plate 받침 포켓 2곳에 먼저 붙인다(같은 극이 위).'),
            panel('②', '짝 표시', two, '② 짝 자석을 붙여 둔 채 윗면에 점을 찍는다.'),
            panel('③', '커버 쪽', three, '③ 점 찍은 면이 포켓 바닥으로 가게 커버 다리 끝에 붙인다. 보스 자석 6개는 극성 무관.')]


# ------------------------------------------------------------------ electrical test
def test_grid(keys, pins):
    cw, ch, left, top = 58, 42, 96, 70
    grid = {(k['row'], k['col']): k for k in keys}
    W = left + 12 * cw + 20
    b = [HATCH]
    for j, name in enumerate(pins['col']):
        x = left + j * cw + cw / 2
        b.append(chip(x, 24, f'C{j}', COL_INK, w=40))
        b.append(text(x, 50, name, 12, MUTED, mono=True))
    for i, name in enumerate(pins['row']):
        y = top + i * ch + ch / 2
        b.append(chip(28, y, f'R{i}', ROW_COLORS[i], w=40))
        b.append(text(70, y, name, 12, MUTED, mono=True))
        for j in range(12):
            x = left + j * cw
            k = grid.get((i, j))
            if k:
                b.append(box(x + 2, top + i * ch + 2, x + cw - 2, top + (i + 1) * ch - 2, fill=ROW_COLORS[i], stroke=ROW_COLORS[i],
                             width=1, extra=' fill-opacity=".14"'))
                b.append(text(x + cw / 2, y - 5, k['legend'], 14 if len(k['legend']) < 5 else 11, INK, weight=700))
                b.append(text(x + cw / 2, y + 12, f"{k['n']}번", 10, MUTED))
            else:
                b.append(box(x + 2, top + i * ch + 2, x + cw - 2, top + (i + 1) * ch - 2, fill='url(#empty)'))
    y = top + 4 * ch + 34
    b.append(text(16, y, '증상으로 찾기', 14, INK, 'start', 700))
    y += 18
    cases = [('한 칸만 안 됨', '그 스위치·다이오드 납땜', {(1, 2)}),
             ('한 행 전체', '그 행 핀 패드·행 선', {(1, j) for j in range(5)}),
             ('한 열 전체', '그 열 핀 패드·열 선', {(i, 2) for i in range(4)}),
             ('누른 키 외에 다른 키도', '다이오드 방향·빠진 다이오드', {(1, 2), (2, 3)})]
    gw = (W - 20) / 4
    for n, (title, cause, cells) in enumerate(cases):
        gx = 14 + n * gw
        for i in range(4):
            for j in range(5):
                on = (i, j) in cells
                b.append(box(gx + j * 18, y + i * 14, gx + j * 18 + 15, y + i * 14 + 11, fill=RISK if on else '#e3e7eb'))
        b.append(text(gx, y + 72, title, 13, INK, 'start', 700))
        b.append(text(gx, y + 92, f'→ {cause}', 12, MUTED, 'start'))
    return svg(W, y + 110, ''.join(b), '전기 시험표: 4행 × 12열')


# ------------------------------------------------------------------ keycaps
def keycap_map(keys):
    xs = [k['x'] for k in keys]
    ys = [k['y'] for k in keys]
    x_lo, x_hi, y_lo, y_hi = min(xs) - 22, max(xs) + 22, min(ys) - 14, max(ys) + 14
    S = 3.0

    def P(x, y):
        return (x - x_lo) * S, (y_hi - y) * S + 10

    b = []
    for k in keys:
        width = 18.05 + (k['w'] - 1) * 19.05
        wide = k['w'] != 1.0
        b.append(poly([P(*p) for p in rect(k['x'], k['y'], width, 18.05, k['rot'])], fill='#f4d9b8' if wide else '#f1f2ee',
                      stroke='#b0723a' if wide else '#a6ada9', width=1.5 if wide else 1))
        if wide:
            cx, cy = P(k['x'], k['y'])
            b.append(text(cx, cy, f"{k['w']:g}u", 14, '#7a4513', weight=700))
    count = {}
    for k in keys:
        count[k['w']] = count.get(k['w'], 0) + 1
    summary = ' · '.join(f'{w:g}u × {n}' for w, n in sorted(count.items()))
    H = (y_hi - y_lo) * S + 20
    b.append(text(12, H + 8, f'위에서 본 키캡 폭: {summary} · 스태빌라이저 없음', 13, INK, 'start', 600))
    return svg((x_hi - x_lo) * S, H + 24, ''.join(b), '키캡 폭 배치')


# ------------------------------------------------------------------ build
def build(out, ctx):
    """Write every diagram to OUT/img/diagrams and return {id: [{path, caption, width, height, wide}]}."""
    keys, pins, role = load(ctx)
    folder = out / 'img' / 'diagrams'
    folder.mkdir(parents=True, exist_ok=True)
    groups = {
        'magnet-polarity': magnet_panels(),
        'snap': snap_panels(),
        'wiring-map': [(wiring_map(ctx, keys, pins, role),
                        '아랫면 배선 지도(모듈을 뒤집은 상태). 같은 색 키를 한 행 선으로, 같은 C 번호를 한 열 선으로 잇는다.')],
        'pinmap': [(pinmap('solder', role), '납땜면(plate 쪽) — 전선을 붙이는 면. 패드 5–12번 양쪽 16곳만 쓴다.'),
                   (pinmap('component', role), '부품면(케이스 바닥 쪽) — 브래킷에 끼운 뒤 보이는 면. RST를 GND에 두 번 대면 기록 모드.')],
        'diode': [(diode(), '다이오드는 검은 띠가 행 선 쪽(펌웨어 COL2ROW).')],
        'test-grid': [(test_grid(keys, pins), '키를 하나씩 눌러 표의 칸을 지운다. 빈 칸(빗금)은 키가 없는 자리.')],
        'keycaps': [(keycap_map(keys), '폭이 다른 키캡 3개의 자리(위에서 봄).')],
    }
    result = {}
    for gid, panels in groups.items():
        items = []
        for i, (content, caption) in enumerate(panels, 1):
            name = f'{gid}-{i}.svg' if len(panels) > 1 else f'{gid}.svg'
            (folder / name).write_text(content, encoding='utf-8', newline='\n')
            head = content.split('>', 1)[0]
            w = float(head.split('width="')[1].split('"')[0])
            h = float(head.split('height="')[1].split('"')[0])
            items.append(dict(path=f'img/diagrams/{name}', caption=caption, width=round(w), height=round(h),
                              wide=gid in ('wiring-map', 'test-grid', 'keycaps')))
        result[gid] = items
    for p in folder.glob('*.svg'):
        if not any(p.name == Path(item['path']).name for items in result.values() for item in items):
            p.unlink()
    return result
