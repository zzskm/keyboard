"""Order-1 test coupons built from the current parameters: the B coupon (switch holes, screw seats, standoff hex
pockets and plate leg magnet pockets, MJF) and the boss tab (cover boss, magnet pockets and the cover name engraving,
8001 resin). build_seam_v5.py puts them into model/ctrl_trials_v5.sc (trials_document).

2026-11-10: until then both were the hand-made model/samples/46es_sw_hole_sample.sc, whose only link to the design was
SMP_upper = TBD_upper_plate_T. It was 10 thick (the JLC3DP FDM minimum part size 30 x 30 x 10; MJF and SLA allow
5 x 5 x 5 or 10 x 2 x 2), so row C had 6.8 mm of 16.5 relief under the hole layer where the plate has 1.8; its boss
was 5.8 where the cover boss is 5.4 (magnet pocket wall 1.3 against 1.1); the hex pocket range 4.8-5.4 ended at the
design value 5.4. Now:
  - B coupon: TBD_plate_T thick with the plate's layers; every range is centred on the design value through
    parameter expressions (SMP_* in the trials document), plus the plate leg magnet pocket in MJF.
  - Boss tab: TBD_cover_T thick with the production boss and pockets, and the cover name on its cosmetic face (the
    face printed down, as the cover top) at the production stroke 0.4 and at twice the size (stroke 0.8, the JLC3DP
    engraving minimum for SLA), read mirrored in the model so it reads right from that face.
The hex pockets and the engraving are fixed-number sketches (the hexagon of tools/mounts_v5.py, the letters of
tools/cover_pattern_v5.py); check() compares the evaluated bodies with volumes and boxes computed from the evaluated
parameters.
"""
import math

import cover_pattern_v5
import mounts_v5

COUPON, TAB = 'SW_HOLE_SAMPLE', 'BOSS_TAB_SAMPLE'
BODIES = (COUPON, TAB)
COUPON_AT = (0.0, -300.0)          # coupon corner (chamfered orientation corner) in the trials model
TAB_AT = (160.0, -300.0)
POCKET = 16.5                      # upper switch opening (r2 P3), as build_seam_v5.switch_openings
COLUMNS = 7
NOTCH_H = 1.5                      # row A latch notch height under the hole layer (r2-style plate, not the v5 plate)
CHAMFER = 3.0
# Row D: (name, X of each feature from the coupon corner); diameters come from the SMP_* parameters below
ROW_D = dict(M2=(7.0, 13.0, 19.0, 25.0), M3=(32.0, 39.0, 46.0, 53.0), CB=(62.0, 71.0, 80.0),
             HEX=(90.0, 99.0, 108.0, 117.0), LEGMAG=(126.0, 132.0, 138.0))
HEX_STEP = 0.2
HEX_AF = tuple(round(mounts_v5.SO_HEX_AF + HEX_STEP * (i - 1), 6) for i in range(len(ROW_D['HEX'])))   # 5.2 .. 5.8
TAB_SIZE = 30.0
TAB_FLAT = (7.0, 15.0, 23.0)       # flat magnet pockets, X from the tab corner, at Y 6
TAB_FLAT_Y = 6.0
# Cover name on the tab's cosmetic face: (scale, centre from the tab corner). Scale 1 is the cover_L engraving.
TAB_TEXT = {'X1': (1.0, (15.0, 23.5)), 'X2': (2.0, (15.0, 11.0))}
TEXT_EDGE = 1.0
COLOR = [143, 191, 106]

PARAMS = [
    # name, expression, comment
    ('SMP_pitch', 'TBD_sw_pitch', '[쿠폰 2026-11-10] B 쿠폰 열·행 간격 = 키 간격'),
    ('SMP_margin', '6 mm', '[쿠폰] B 쿠폰 가장자리 ↔ 첫 열·행 칸 경계'),
    ('SMP_rowD', '5 mm', '[쿠폰] 행 D(나사·포켓) 띠 추가 폭'),
    ('SMP_L', f'{COLUMNS} * SMP_pitch + 2 * SMP_margin', '[쿠폰] B 쿠폰 길이 X'),
    ('SMP_W', '3 * SMP_pitch + 2 * SMP_margin + SMP_rowD', '[쿠폰] B 쿠폰 폭 Y'),
    ('SMP_T', 'TBD_plate_T', '[쿠폰 2026-11-10] B 쿠폰 두께 = plate 두께(옛 10은 FDM 최소 크기. MJF는 5×5×5)'),
    ('SMP_upper', 'TBD_upper_plate_T', '[쿠폰] 행 C 상부 16.5 개구 층 = v5 upper plate 층'),
    ('SMP_ledge', 'TBD_sw_ledge_T', '[쿠폰] 홀 층(걸쇠가 걸리는 남김) 두께'),
    ('SMP_hole_step', '0.1 mm', '[쿠폰] 스위치 홀 단계'),
    ('SMP_hole_min', 'TBD_sw_hole - 3 * SMP_hole_step', '[쿠폰] 열 0 홀. 열 3이 TBD_sw_hole'),
    ('SMP_notch_D', 'TBD_sw_relief_W', '[쿠폰] 행 A 걸쇠 노치 편측 깊이'),
    ('SMP_notch_L', 'TBD_sw_notch_L', '[쿠폰] 행 A 걸쇠 노치 길이'),
    ('SMP_notch_H', f'{NOTCH_H:g} mm', '[쿠폰] 행 A 걸쇠 노치 높이(홀 층 바로 아래)'),
    ('SMP_pocket', f'{POCKET:g} mm', '[쿠폰] 행 B 아래 포켓·행 C 상부/아래 개구 = r2 P3 16.5'),
    ('SMP_m2_step', '0.2 mm', '[쿠폰] 행 D M2 구멍 단계'),
    ('SMP_m2_min', 'split_M2_clear_D - 2 * SMP_m2_step', '[쿠폰] 행 D M2 구멍 첫 값. 셋째가 split_M2_clear_D'),
    ('SMP_m3_step', '0.2 mm', '[쿠폰] 행 D M3 관통 단계'),
    ('SMP_m3_min', 'TBD_so_screw_D + TBD_so_clr - 2 * SMP_m3_step', '[쿠폰] 행 D M3 관통 첫 값. 셋째가 plate·mount M3 구멍'),
    ('SMP_cb_step', '0.2 mm', '[쿠폰] 행 D 카운터보어 단계'),
    ('SMP_cb_min', 'TBD_so_head_D - SMP_cb_step', '[쿠폰] 행 D 카운터보어 첫 값. 둘째가 plate 카운터보어(보스 편측 여유 0.2/0.3/0.4)'),
    ('SMP_hex_step', f'{HEX_STEP:g} mm', '[쿠폰] 행 D 육각 포켓 맞변 단계(스케치는 고정 숫자, coupon_v5.HEX_AF)'),
    ('SMP_hex_min', 'TBD_so_AF + TBD_so_pocket_clr - SMP_hex_step', '[쿠폰] 행 D 육각 포켓 첫 맞변. 둘째가 mount 포켓'),
    ('SMP_legmag_step', '0.1 mm', '[쿠폰] 행 D plate 다리 자석 포켓 단계'),
    ('SMP_legmag_min', 'TBD_magnet_D + 2 * v5_legmag_plate_clr - SMP_legmag_step',
     '[쿠폰 2026-11-10] 행 D plate 다리 자석 포켓(MJF) 첫 값. 둘째가 plate 포켓 Ø3.3'),
    ('SMP_tab', f'{TAB_SIZE:g} mm', '[쿠폰] 보스 탭 한 변'),
    ('SMP_tab_T', 'TBD_cover_T', '[쿠폰 2026-11-10] 보스 탭 두께 = 커버 두께(옛 10은 FDM 최소 크기)'),
    ('SMP_magf_step', '0.1 mm', '[쿠폰] 보스 탭 평면 자석 포켓 단계'),
    ('SMP_magf_min', 'TBD_magnet_D + 2 * TBD_magnet_clr', '[쿠폰] 보스 탭 평면 자석 포켓 첫 값 = 커버 다리 자석 포켓'),
]


def add_params(doc):
    names = {p['name'] for p in doc['params']}
    for name, expr, comment in PARAMS:
        assert name not in names, name
        doc['params'].append(dict(name=name, expr=expr, comment=comment, model=False, unit='mm'))


def _num(x):
    return round(float(x), 6)


def text_shape(scale, centre):
    """The cover name scaled about its centre, mirrored in X (it is read from the face printed down), at `centre`
    in the trials model."""
    from shapely.affinity import scale as shapely_scale, translate
    shape = cover_pattern_v5.text_shape()
    cx, cy = cover_pattern_v5.TEXT_AT
    shape = shapely_scale(shape, -scale, scale, origin=(cx, cy))
    return translate(shape, centre[0] - cx, centre[1] - cy)


def tab_texts():
    x0, y0 = TAB_AT
    return {name: text_shape(scale, (x0 + c[0], y0 + c[1])) for name, (scale, c) in TAB_TEXT.items()}


def emit(feature, sketch, doc):
    """The two coupon bodies, after the other trials."""
    X, Y = (_num(v) for v in COUPON_AT)
    col = lambda c: f'{X} + SMP_margin + SMP_pitch * {c + 0.5}'
    row = lambda r: f'{Y} + SMP_margin + SMP_pitch * {r + 0.5}'
    hole = lambda c: f'(SMP_hole_min + {c} * SMP_hole_step)'
    plane = lambda z: dict(type='offset', base=dict(type='origin', name='XY'), distance=str(z))

    def box(name, cx, cy, sx, sy, z0, h, op='cut', body=COUPON, **extra):
        feature('box', name, corner=[f'({cx}) - ({sx}) / 2', f'({cy}) - ({sy}) / 2', z0], length=sx, width=sy,
                height=h, operation=op, participants=[body], **extra)

    def cyl(name, x, y, d, z0, h, body=COUPON, op='cut'):
        feature('cylinder', name, axis=[0.0, 0.0, 1.0], base=[x, y, z0], height=h, radius=f'({d}) / 2',
                operation=op, participants=[body])

    feature('box', 'SMP_BASE', corner=[X, Y, 0.0], length='SMP_L', width='SMP_W', height='SMP_T',
            operation='new_body', body_names=[COUPON])
    doc['appearances']['bodies'][COUPON] = dict(name='Custom', color=COLOR, opacity=1.0)
    for c in range(COLUMNS):
        for r, tag in enumerate('ABC'):
            box(f'SMP_HOLE_{tag}{c}', col(c), row(r), hole(c), hole(c), -1.0, 'SMP_T + 2')
        # row A: r2-style 1.5 plate, latch notches under the hole layer on the four sides
        notch = f'{hole(c)} + 2 * SMP_notch_D'
        z = 'SMP_T - SMP_ledge - SMP_notch_H'
        box(f'SMP_NOTCH_X_A{c}', col(c), row(0), notch, 'SMP_notch_L', z, 'SMP_notch_H')
        box(f'SMP_NOTCH_Y_A{c}', col(c), row(0), 'SMP_notch_L', notch, z, 'SMP_notch_H')
        # row B: hole layer on top, the whole underside open to 16.5
        box(f'SMP_POCKET_B{c}', col(c), row(1), 'SMP_pocket', 'SMP_pocket', -1.0, 'SMP_T - SMP_ledge + 1')
        # row C: the v5 plate layers: 16.5 upper opening, hole layer, 16.5 relief to the underside
        box(f'SMP_UPPER_C{c}', col(c), row(2), 'SMP_pocket', 'SMP_pocket', 'SMP_T - SMP_upper', 'SMP_upper + 1')
        box(f'SMP_RELIEF_C{c}', col(c), row(2), 'SMP_pocket', 'SMP_pocket', -1.0, 'SMP_T - SMP_upper - SMP_ledge + 1')
    y = f'{Y} + SMP_W - SMP_margin'
    for i, x in enumerate(ROW_D['M2']):
        cyl(f'SMP_M2_{i}', X + x, y, f'SMP_m2_min + {i} * SMP_m2_step', -1.0, 'SMP_T + 2')
    for i, x in enumerate(ROW_D['M3']):
        cyl(f'SMP_M3_{i}', X + x, y, f'SMP_m3_min + {i} * SMP_m3_step', -1.0, 'SMP_T + 2')
    for i, x in enumerate(ROW_D['CB']):          # plate counterbore from the top over the M3 hole
        cyl(f'SMP_CB_{i}', X + x, y, f'SMP_cb_min + {i} * SMP_cb_step', 'SMP_T - TBD_so_cb_D', 'TBD_so_cb_D + 1')
        cyl(f'SMP_CB_HOLE_{i}', X + x, y, 'TBD_so_screw_D + TBD_so_clr', -1.0, 'SMP_T + 2')
    y_hex = _num(Y + 3 * 19.05 + 2 * 6 + 5 - 6)   # SMP_W - SMP_margin as a number (checked in check())
    rings = [[(round(px, 6), round(py, 6)) for px, py in mounts_v5.hexagon((X + x, y_hex), af).exterior.coords[:-1]]
             for x, af in zip(ROW_D['HEX'], HEX_AF)]
    sk = sketch('SK_SMP_HEX_POCKETS', plane(-0.5), rings)       # mount pocket: from the face the standoff enters
    feature('extrude', 'SMP_HEX_POCKETS', sketch=sk, profiles=dict(type='all'),
            extent=dict(convention='total_distance', direction='positive', distance='0.5 + TBD_so_pocket_D'),
            operation='cut', targets=[COUPON])
    for i, x in enumerate(ROW_D['HEX']):
        cyl(f'SMP_HEX_HOLE_{i}', X + x, y, 'TBD_so_screw_D + TBD_so_clr', -1.0, 'SMP_T + 2')
    for i, x in enumerate(ROW_D['LEGMAG']):      # plate leg magnet pocket, from the plate top
        cyl(f'SMP_LEGMAG_{i}', X + x, y, f'SMP_legmag_min + {i} * SMP_legmag_step',
            'SMP_T - TBD_magnet_T - TBD_magnet_clr', 'TBD_magnet_T + TBD_magnet_clr + 1')
    c = CHAMFER                                   # orientation mark: column 0 corner
    sk = sketch('SK_SMP_CORNER', plane(-0.5), [[(X - 1, Y - 1), (X + c + 1, Y - 1), (X - 1, Y + c + 1)]])
    feature('extrude', 'SMP_CORNER', sketch=sk, profiles=dict(type='all'),
            extent=dict(convention='total_distance', direction='positive', distance='SMP_T + 1'),
            operation='cut', targets=[COUPON])

    # boss tab: a piece of cover, boss side up as modelled (printed as modelled, cosmetic face down)
    TX, TY = (_num(v) for v in TAB_AT)
    centre = (TX + TAB_SIZE / 2, TY + TAB_SIZE / 2)
    feature('box', 'SMP_TAB_BASE', corner=[TX, TY, 0.0], length='SMP_tab', width='SMP_tab', height='SMP_tab_T',
            operation='new_body', body_names=[TAB])
    doc['appearances']['bodies'][TAB] = dict(name='Custom', color=[200, 220, 235], opacity=0.6)
    cyl('SMP_TAB_BOSS', *centre, 'TBD_cover_boss_D', 'SMP_tab_T', 'TBD_cover_boss_H', body=TAB, op='join')
    cyl('SMP_TAB_BOSS_MAGNET', *centre, 'TBD_magnet_D + 2 * TBD_magnet_clr',
        'SMP_tab_T + TBD_cover_boss_H - TBD_magnet_T - TBD_magnet_clr', 'TBD_magnet_T + TBD_magnet_clr + 1', body=TAB)
    for i, x in enumerate(TAB_FLAT):
        cyl(f'SMP_TAB_MAG_{i}', TX + x, TY + TAB_FLAT_Y, f'SMP_magf_min + {i} * SMP_magf_step',
            'SMP_tab_T - TBD_magnet_T - TBD_magnet_clr', 'TBD_magnet_T + TBD_magnet_clr + 1', body=TAB)
    for name, shape in tab_texts().items():
        loops, outers, n = [], [], 0
        for outer, islands in cover_pattern_v5._loops(shape):
            outers.append([f'l{n + j + 1}' for j in range(len(outer))])
            for loop in [outer, *islands]:
                loops.append(loop)
                n += len(loop)
        sk = sketch(f'SK_SMP_TAB_TEXT_{name}', plane(0), loops)
        feature('extrude', f'SMP_TAB_TEXT_{name}', sketch=sk, profiles=dict(type='curves', loops=outers),
                extent=dict(convention='total_distance', direction='positive', distance=str(cover_pattern_v5.DEPTH)),
                operation='cut', targets=[TAB])


def expected(values):
    """{body: (volume, (x0, y0, z0, x1, y1, z1))} from the evaluated parameters."""
    from shapely.geometry import Polygon
    v = values
    p, m, T = v['SMP_pitch'], v['SMP_margin'], v['SMP_T']
    L, W = COLUMNS * p + 2 * m, 3 * p + 2 * m + v['SMP_rowD']
    disc = lambda d: math.pi * d * d / 4
    cut = CHAMFER * CHAMFER / 2 * T
    for c in range(COLUMNS):
        s = v['SMP_hole_min'] + c * v['SMP_hole_step']
        cut += 3 * s * s * T                                               # rows A, B, C through holes
        cut += 4 * v['SMP_notch_D'] * v['SMP_notch_L'] * v['SMP_notch_H']   # row A notches outside the hole
        cut += 2 * (POCKET * POCKET - s * s) * (T - v['SMP_ledge'])         # row B pocket; row C upper + relief
    bore = v['TBD_so_screw_D'] + v['TBD_so_clr']
    cut += sum(disc(v['SMP_m2_min'] + i * v['SMP_m2_step']) * T for i in range(len(ROW_D['M2'])))
    cut += sum(disc(v['SMP_m3_min'] + i * v['SMP_m3_step']) * T for i in range(len(ROW_D['M3'])))
    for i in range(len(ROW_D['CB'])):
        cb = v['TBD_so_cb_D']
        cut += disc(v['SMP_cb_min'] + i * v['SMP_cb_step']) * cb + disc(bore) * (T - cb)
    for af in HEX_AF:
        depth = v['TBD_so_pocket_D']
        cut += math.sqrt(3) / 2 * af * af * depth + disc(bore) * (T - depth)
    mag_h = v['TBD_magnet_T'] + v['TBD_magnet_clr']
    cut += sum(disc(v['SMP_legmag_min'] + i * v['SMP_legmag_step']) * mag_h for i in range(len(ROW_D['LEGMAG'])))
    x, y = COUPON_AT
    out = {COUPON: (L * W * T - cut, (x, y, 0.0, x + L, y + W, T))}

    t, H = v['SMP_tab_T'], v['TBD_cover_boss_H']
    vol = TAB_SIZE * TAB_SIZE * t + disc(v['TBD_cover_boss_D']) * H
    vol -= disc(v['TBD_magnet_D'] + 2 * v['TBD_magnet_clr']) * mag_h
    vol -= sum(disc(v['SMP_magf_min'] + i * v['SMP_magf_step']) * mag_h for i in range(len(TAB_FLAT)))
    vol -= sum(Polygon(o, i).area for s in tab_texts().values() for o, i in cover_pattern_v5._loops(s)) * cover_pattern_v5.DEPTH
    x, y = TAB_AT
    out[TAB] = (vol, (x, y, 0.0, x + TAB_SIZE, y + TAB_SIZE, t + H))
    return out


def walls(values):
    """Plan-view material left between neighbouring features (mm); every one must keep the MJF / resin wall."""
    v = values
    p, m = v['SMP_pitch'], v['SMP_margin']
    W = 3 * p + 2 * m + v['SMP_rowD']
    largest = dict(M2=v['SMP_m2_min'] + 3 * v['SMP_m2_step'], M3=v['SMP_m3_min'] + 3 * v['SMP_m3_step'],
                   CB=v['SMP_cb_min'] + 2 * v['SMP_cb_step'], HEX=2 * max(HEX_AF) / math.sqrt(3),
                   LEGMAG=v['SMP_legmag_min'] + 2 * v['SMP_legmag_step'])
    xs = sorted((x, largest[k] / 2) for k, row in ROW_D.items() for x in row)
    out = dict(row_D_between=round(min(b[0] - b[1] - a[0] - a[1] for a, b in zip(xs, xs[1:])), 3),
               row_D_ends=round(min(xs[0][0] - xs[0][1], COLUMNS * p + 2 * m - xs[-1][0] - xs[-1][1]), 3),
               row_D_back=round(m - max(r for _, r in xs), 3),
               row_D_to_row_C=round((W - m) - max(r for _, r in xs) - (m + 3 * p - (p - POCKET) / 2), 3),
               switch_cells=round(p - POCKET, 3),
               notch_cells=round(p - (v['SMP_hole_min'] + 6 * v['SMP_hole_step'] + 2 * v['SMP_notch_D']), 3),
               ledge=v['SMP_ledge'],
               under_counterbore=round(v['SMP_T'] - v['TBD_so_cb_D'], 3),
               over_leg_magnet=round(v['SMP_T'] - v['TBD_magnet_T'] - v['TBD_magnet_clr'], 3),
               boss_magnet_wall=round((v['TBD_cover_boss_D'] - v['TBD_magnet_D'] - 2 * v['TBD_magnet_clr']) / 2, 3))
    from shapely.geometry import box
    x, y = TAB_AT
    tab = box(x, y, x + TAB_SIZE, y + TAB_SIZE)
    out['text_to_tab_edge'] = round(min(tab.exterior.distance(s) for s in tab_texts().values()), 3)
    return out


def check(evaluated, production_values):
    """Both coupons are closed single bodies with the volume and box of their parameters; the parameters follow the
    production model; walls keep the material limits. Returns the report."""
    values = {q['name']: q['value'] for q in evaluated['params'] if q.get('value') is not None}
    for name in ('TBD_plate_T', 'TBD_upper_plate_T', 'TBD_sw_ledge_T', 'TBD_sw_hole', 'TBD_so_cb_D', 'TBD_so_head_D',
                 'TBD_cover_boss_D', 'TBD_cover_T', 'TBD_magnet_D', 'v5_legmag_plate_clr', 'TBD_so_pocket_D'):
        assert abs(values[name] - production_values[name]) < 1e-9, (name, values[name], production_values[name])
    assert abs(values['SMP_hex_min'] + values['SMP_hex_step'] - mounts_v5.SO_HEX_AF) < 1e-9, 'hex sketch is stale'
    assert abs(values['SMP_hex_step'] - HEX_STEP) < 1e-9
    assert abs(values['SMP_W'] - values['SMP_margin'] - (3 * 19.05 + 2 * 6 + 5 - 6)) < 1e-9, 'hex row Y is stale'
    assert abs(values['SMP_T'] - values['SMP_upper'] - values['SMP_ledge'] - production_values['TBD_sw_notch_H']) < 1e-9
    bodies = {b['name']: b for b in evaluated['bodies']}
    report = {}
    for name, (volume, bbox) in expected(values).items():
        b = bodies[name]
        got = tuple(b['bbox']['min']) + tuple(b['bbox']['max'])
        assert b['closed'] and all(abs(g - e) < 1e-4 for g, e in zip(got, bbox)), (name, got, bbox)
        assert abs(b['volume_mm3'] - volume) / volume < 1e-4, (name, b['volume_mm3'], volume)
        report[name] = dict(volume_mm3=round(b['volume_mm3'], 3), expected_mm3=round(volume, 3),
                            size=[round(bbox[k + 3] - bbox[k], 3) for k in range(3)])
    w = walls(values)
    assert min(v for k, v in w.items() if k not in ('boss_magnet_wall', 'text_to_tab_edge')) >= 1.0 - 1e-9, w
    assert w['boss_magnet_wall'] >= 0.8 - 1e-9 and w['text_to_tab_edge'] >= TEXT_EDGE, w
    report['walls_mm'] = w
    report['ranges'] = dict(
        hole=[round(values['SMP_hole_min'] + i * values['SMP_hole_step'], 3) for i in range(COLUMNS)],
        m2=[round(values['SMP_m2_min'] + i * values['SMP_m2_step'], 3) for i in range(len(ROW_D['M2']))],
        m3=[round(values['SMP_m3_min'] + i * values['SMP_m3_step'], 3) for i in range(len(ROW_D['M3']))],
        counterbore=[round(values['SMP_cb_min'] + i * values['SMP_cb_step'], 3) for i in range(len(ROW_D['CB']))],
        hex_AF=list(HEX_AF),
        plate_leg_magnet=[round(values['SMP_legmag_min'] + i * values['SMP_legmag_step'], 3) for i in range(len(ROW_D['LEGMAG']))],
        tab_flat_magnet=[round(values['SMP_magf_min'] + i * values['SMP_magf_step'], 3) for i in range(len(TAB_FLAT))],
        tab_text_stroke=[round(cover_pattern_v5.TEXT_STROKE * s, 3) for s, _ in TAB_TEXT.values()])
    return report
