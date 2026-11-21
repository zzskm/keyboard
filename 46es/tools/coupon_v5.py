"""Order-1 test coupons built from the current parameters: the consolidated MJF master coupon (v5 plate row C switch
holes, M2/M3/counterbore/leg magnet pockets, realistic Ø8 SO insert bosses with 5 mm depth + SO4-clipped wall, and
three integrated front-seam R pockets S1/S2/S3) and the boss tab (cover boss, magnet pockets, cover name engraving
and a 1.1 mm thin-bezel test rib, 8001 resin). build_seam_v5.py puts them into model/ctrl_trials_v5.sc.

2026-11-20 (decision, docs/design.md): consolidated order-1 coupons from 9 to 8 parts while expanding test coverage:
  - Dropped unused rows A (r2 latch notch) and B (flat top) from the B coupon, keeping row C (v5 plate layers).
  - Integrated 3 front-seam R pockets (S1: fit 0.15 / nut AF 4.0, S2: 0.25 / 4.2, S3: 0.35 / 4.4) along the +Y edge
    of the B coupon, tested against the single standalone SEAM_COUPON_L tab (dropping separate SEAM_COUPON_1/2).
  - Replaced flat 4 mm insert holes with 4 protruding Ø8.0 bosses (total height 8 mm, hole depth 5 mm = 4 insert + 1
    melt relief over Ø3.4 bore), with the nominal Ø4.2 boss clipped on one side to 1.56 mm wall (matching mount SO4).
  - Extended boss_tab to 30 x 38 mm with a through window leaving a 1.1 x 18 x 6 mm thin-bezel test rib.
"""
import math

import cover_pattern_v5
import mounts_v5
import seam_v5

COUPON, TAB = 'SW_HOLE_SAMPLE', 'BOSS_TAB_SAMPLE'
BODIES = (COUPON, TAB)
COUPON_AT = (0.0, -300.0)          # coupon corner (chamfered orientation corner) in the trials model
TAB_AT = (160.0, -300.0)
POCKET = 16.5                      # upper switch opening (r2 P3), as build_seam_v5.switch_openings
COLUMNS = 7
CHAMFER = 3.0
ROW_C_Y = 12.0                     # Y centre of row C switch holes from the coupon corner
ROW_D_Y = 26.5                     # Y centre of row D hardware & SO insert bosses from the coupon corner
COUPON_W = 43.5                    # coupon width Y: row C + row D + integrated seam-R pockets on +Y edge
BOSS_PROTRUSION = 3.0              # SO insert boss protrusion below Z=0 (total Z -3..5 = 8 mm, matching mounts)
SO4_WALL = 1.56                    # mount SO4 minimum boss wall (reproduced on the nominal Ø4.2 boss #1)
SO4_CLIP_INDEX = 1                 # index in ROW_D['INSERT'] for the nominal Ø4.2 boss
# Row D: (name, X of each feature from the coupon corner); diameters come from the SMP_* parameters below
ROW_D = dict(M2=(7.0, 13.0, 19.0, 25.0), M3=(32.0, 39.0, 46.0, 53.0), CB=(62.0, 71.0, 80.0),
             INSERT=(90.0, 100.0, 110.0, 120.0), LEGMAG=(129.0, 134.5, 140.0))
# Integrated front-seam R pockets along the +Y edge (y_local = COUPON_W), rotated -90 deg CW so seam face is +Y edge.
# Tested against the single standalone SEAM_COUPON_L piece. Left-to-right from chamfered corner: S1, S2, S3.
SEAM_R_U0 = {'S1': 20.0, 'S2': 65.0, 'S3': 110.0}
TAB_SIZE_X = 30.0
TAB_SIZE_Y = 38.0                  # extended from 30 to host the 1.1 mm thin-bezel test window
TAB_FLAT = (7.0, 15.0, 23.0)       # flat magnet pockets, X from the tab corner, at Y 6
TAB_FLAT_Y = 6.0
TAB_RIB_W = 1.1                    # v5_cover_silhouette_min_rail: thin-bezel rib width along +Y edge
TAB_WIN_X = (6.0, 24.0)            # 18 mm wide through-window (approx 1u span)
TAB_WIN_H = 4.5                    # window depth in Y (y = 32.4 .. 36.9, leaving 1.1 mm rib at 36.9 .. 38.0)
# Cover name on the tab's cosmetic face: (scale, centre from the tab corner). Scale 1 is the cover_L engraving.
TAB_TEXT = {'X1': (1.0, (15.0, 23.5)), 'X1_6': (1.6, (15.0, 11.0))}
TEXT_EDGE = 1.0
COLOR = [143, 191, 106]

PARAMS = [
    # name, expression, comment
    ('SMP_pitch', 'TBD_sw_pitch', '[쿠폰 2026-11-10] B 쿠폰 열 간격 = 키 간격'),
    ('SMP_margin', '6 mm', '[쿠폰] B 쿠폰 좌우 가장자리 ↔ 첫 열 칸 경계'),
    ('SMP_L', f'{COLUMNS} * SMP_pitch + 2 * SMP_margin', '[쿠폰] B 쿠폰 길이 X'),
    ('SMP_W', f'{COUPON_W:g} mm', '[쿠폰 2026-11-20] B 쿠폰 폭 Y(행 C + 행 D 보스 + +Y 이음 R 포켓 3종)'),
    ('SMP_T', 'TBD_plate_T', '[쿠폰 2026-11-10] B 쿠폰 판 두께 = plate 두께(옛 10은 FDM 최소 크기. MJF는 5×5×5)'),
    ('SMP_upper', 'TBD_upper_plate_T', '[쿠폰] 행 C 상부 16.5 개구 층 = v5 upper plate 층'),
    ('SMP_ledge', 'TBD_sw_ledge_T', '[쿠폰] 홀 층(걸쇠가 걸리는 남김) 두께'),
    ('SMP_hole_step', '0.1 mm', '[쿠폰] 스위치 홀 단계'),
    ('SMP_hole_min', 'TBD_sw_hole - 3 * SMP_hole_step', '[쿠폰] 열 0 홀. 열 3이 TBD_sw_hole'),
    ('SMP_pocket', f'{POCKET:g} mm', '[쿠폰] 행 C 상부/아래 개구 = r2 P3 16.5'),
    ('SMP_m2_step', '0.2 mm', '[쿠폰] 행 D M2 구멍 단계'),
    ('SMP_m2_min', 'split_M2_clear_D - 2 * SMP_m2_step', '[쿠폰] 행 D M2 구멍 첫 값. 셋째가 split_M2_clear_D'),
    ('SMP_m3_step', '0.2 mm', '[쿠폰] 행 D M3 관통 단계'),
    ('SMP_m3_min', 'TBD_so_screw_D + TBD_so_clr - 2 * SMP_m3_step', '[쿠폰] 행 D M3 관통 첫 값. 셋째가 plate·mount M3 구멍'),
    ('SMP_cb_step', '0.2 mm', '[쿠폰] 행 D 카운터보어 단계'),
    ('SMP_cb_min', 'TBD_so_head_D - SMP_cb_step', '[쿠폰] 행 D 카운터보어 첫 값. 둘째가 plate 카운터보어(보스 편측 여유 0.2/0.3/0.4)'),
    ('SMP_ins_step', '0.2 mm', '[쿠폰 2026-11-12] 행 D SO 인서트 열압입 구멍 단계'),
    ('SMP_ins_min', 'v5_so_insert_hole_D - SMP_ins_step', '[쿠폰 2026-11-20] 행 D 인서트 구멍 첫 값. 둘째가 mount 보스 구멍(Ø8 보스, 깊이 5 = 인서트 4 + 여유 1, SO4 살 1.56 재현)'),
    ('SMP_legmag_step', '0.1 mm', '[쿠폰] 행 D plate 다리 자석 포켓 단계'),
    ('SMP_legmag_min', 'TBD_magnet_D + 2 * v5_legmag_plate_clr - SMP_legmag_step',
     '[쿠폰 2026-11-10] 행 D plate 다리 자석 포켓(MJF) 첫 값. 둘째가 plate 포켓 Ø3.3'),
    ('SMP_tab', f'{TAB_SIZE_X:g} mm', '[쿠폰] 보스 탭 폭 X'),
    ('SMP_tab_Y', f'{TAB_SIZE_Y:g} mm', '[쿠폰 2026-11-20] 보스 탭 깊이 Y(1.1 mm 얇은 베젤 살 시험 창 포함)'),
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


def _seam_to_coupon(px, py, u0):
    """Map plate seam coordinates (px, py) to coupon XY by -90 deg CW rotation onto the +Y edge (y_local = COUPON_W)."""
    X, Y = COUPON_AT
    return (_num(X + u0 + (py - seam_v5.TAB_Y[0])),
            _num(Y + COUPON_W - (px - seam_v5.R_EDGE_X)))


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
    """The two consolidated coupon bodies, after the other trials."""
    X, Y = (_num(v) for v in COUPON_AT)
    col = lambda c: f'{X} + SMP_margin + SMP_pitch * {c + 0.5}'
    hole = lambda c: f'(SMP_hole_min + {c} * SMP_hole_step)'
    plane = lambda z: dict(type='offset', base=dict(type='origin', name='XY'), distance=str(z))
    cut_ext = lambda d: dict(convention='total_distance', direction='positive', distance=str(d))

    def box(name, cx, cy, sx, sy, z0, h, op='cut', body=COUPON, **extra):
        feature('box', name, corner=[f'({cx}) - ({sx}) / 2', f'({cy}) - ({sy}) / 2', z0], length=sx, width=sy,
                height=h, operation=op, participants=[body], **extra)

    def cyl(name, x, y, d, z0, h, body=COUPON, op='cut'):
        feature('cylinder', name, axis=[0.0, 0.0, 1.0], base=[x, y, z0], height=h, radius=f'({d}) / 2',
                operation=op, participants=[body])

    feature('box', 'SMP_BASE', corner=[X, Y, 0.0], length='SMP_L', width='SMP_W', height='SMP_T',
            operation='new_body', body_names=[COUPON])
    doc['appearances']['bodies'][COUPON] = dict(name='Custom', color=COLOR, opacity=1.0)

    # Row C only: exact v5 plate layers (16.5 upper 1.7, hole ledge 1.5, 16.5 relief 1.8)
    row_c_y = _num(Y + ROW_C_Y)
    for c in range(COLUMNS):
        box(f'SMP_HOLE_C{c}', col(c), row_c_y, hole(c), hole(c), -1.0, 'SMP_T + 2')
        box(f'SMP_UPPER_C{c}', col(c), row_c_y, 'SMP_pocket', 'SMP_pocket', 'SMP_T - SMP_upper', 'SMP_upper + 1')
        box(f'SMP_RELIEF_C{c}', col(c), row_c_y, 'SMP_pocket', 'SMP_pocket', -1.0, 'SMP_T - SMP_upper - SMP_ledge + 1')

    # Row D: M2, M3, counterbores, realistic Ø8 SO insert bosses (Z -3..5, depth 5), plate leg magnet pockets
    y_d = _num(Y + ROW_D_Y)
    for i, x in enumerate(ROW_D['M2']):
        cyl(f'SMP_M2_{i}', X + x, y_d, f'SMP_m2_min + {i} * SMP_m2_step', -1.0, 'SMP_T + 2')
    for i, x in enumerate(ROW_D['M3']):
        cyl(f'SMP_M3_{i}', X + x, y_d, f'SMP_m3_min + {i} * SMP_m3_step', -1.0, 'SMP_T + 2')
    for i, x in enumerate(ROW_D['CB']):          # plate counterbore from the top over the M3 hole
        cyl(f'SMP_CB_{i}', X + x, y_d, f'SMP_cb_min + {i} * SMP_cb_step', 'SMP_T - TBD_so_cb_D', 'TBD_so_cb_D + 1')
        cyl(f'SMP_CB_HOLE_{i}', X + x, y_d, 'TBD_so_screw_D + TBD_so_clr', -1.0, 'SMP_T + 2')
    for i, x in enumerate(ROW_D['INSERT']):      # SO insert: Ø8 boss protruding 3 mm below plate, 5 mm deep hole + M3 bore
        cyl(f'SMP_INS_BOSS_{i}', X + x, y_d, 'v5_so_boss_D', -BOSS_PROTRUSION, f'{BOSS_PROTRUSION:g} + 0.5', op='join')
        if i == SO4_CLIP_INDEX:
            # Clip -Y side of the nominal Ø4.2 boss to reproduce mount SO4's 1.56 mm minimum wall
            clip_d = mounts_v5.INSERT_HOLE_D / 2 + SO4_WALL
            feature('box', f'SMP_INS_BOSS_SO4_CLIP_{i}',
                    corner=[_num(X + x - 5.0), _num(y_d - clip_d - 2.0), -BOSS_PROTRUSION - 0.5],
                    length='10', width='2', height=f'{BOSS_PROTRUSION + 0.5:g}', operation='cut', participants=[COUPON])
        cyl(f'SMP_INSERT_{i}', X + x, y_d, f'SMP_ins_min + {i} * SMP_ins_step',
            -BOSS_PROTRUSION - 0.5, 'v5_so_insert_hole_depth + 0.5')
        cyl(f'SMP_INSERT_BORE_{i}', X + x, y_d, 'TBD_so_screw_D + TBD_so_clr',
            -BOSS_PROTRUSION - 0.5, f'SMP_T + {BOSS_PROTRUSION + 1.0:g}')
    for i, x in enumerate(ROW_D['LEGMAG']):      # plate leg magnet pocket, from the plate top
        cyl(f'SMP_LEGMAG_{i}', X + x, y_d, f'SMP_legmag_min + {i} * SMP_legmag_step',
            'SMP_T - TBD_magnet_T - TBD_magnet_clr', 'TBD_magnet_T + TBD_magnet_clr + 1')

    # Integrated front-seam R pockets (S1, S2, S3) along the +Y edge, mating with SEAM_COUPON_L
    for name, u0 in SEAM_R_U0.items():
        variant = seam_v5.VARIANTS[name]
        _, pocket = seam_v5.outlines(variant)
        pocket_rot = [_seam_to_coupon(px, py, u0) for px, py in pocket]
        sk = sketch(f'SK_SMP_SEAM_{name}_POCKET', plane(f'SMP_T - {variant.tab_T:g}'), [pocket_rot])
        feature('extrude', f'SMP_SEAM_{name}_POCKET', sketch=sk, profiles=dict(type='all'),
                extent=cut_ext(variant.tab_T + 1.0), operation='cut', targets=[COUPON])
        sx, sy = _seam_to_coupon(*variant.screw, u0)
        cyl(f'SMP_SEAM_{name}_M2', sx, sy, str(seam_v5.M2_CLEAR_D), -1.0, 'SMP_T + 2')
        hex_rot = [_seam_to_coupon(px, py, u0) for px, py in seam_v5.hexagon(*variant.screw, variant.nut_AF)]
        sk = sketch(f'SK_SMP_SEAM_{name}_NUT', plane(-0.5), [hex_rot])
        feature('extrude', f'SMP_SEAM_{name}_NUT', sketch=sk, profiles=dict(type='all'),
                extent=cut_ext(0.5 + variant.nut_D), operation='cut', targets=[COUPON])

    c = CHAMFER                                   # orientation mark: column 0 corner (S1 is left, S3 is right)
    sk = sketch('SK_SMP_CORNER', plane(-0.5), [[(X - 1, Y - 1), (X + c + 1, Y - 1), (X - 1, Y + c + 1)]])
    feature('extrude', 'SMP_CORNER', sketch=sk, profiles=dict(type='all'),
            extent=cut_ext('SMP_T + 1'), operation='cut', targets=[COUPON])

    # boss tab: a piece of cover, boss side up as modelled (printed as modelled, cosmetic face down)
    TX, TY = (_num(v) for v in TAB_AT)
    centre = (TX + TAB_SIZE_X / 2, TY + TAB_SIZE_X / 2)
    feature('box', 'SMP_TAB_BASE', corner=[TX, TY, 0.0], length='SMP_tab', width='SMP_tab_Y', height='SMP_tab_T',
            operation='new_body', body_names=[TAB])
    doc['appearances']['bodies'][TAB] = dict(name='Custom', color=[200, 220, 235], opacity=0.6)
    cyl('SMP_TAB_BOSS', *centre, 'TBD_cover_boss_D', 'SMP_tab_T', 'TBD_cover_boss_H', body=TAB, op='join')
    cyl('SMP_TAB_BOSS_MAGNET', *centre, 'TBD_magnet_D + 2 * TBD_magnet_clr',
        'SMP_tab_T + TBD_cover_boss_H - TBD_magnet_T - TBD_magnet_clr', 'TBD_magnet_T + TBD_magnet_clr + 1', body=TAB)
    for i, x in enumerate(TAB_FLAT):
        cyl(f'SMP_TAB_MAG_{i}', TX + x, TY + TAB_FLAT_Y, f'SMP_magf_min + {i} * SMP_magf_step',
            'SMP_tab_T - TBD_magnet_T - TBD_magnet_clr', 'TBD_magnet_T + TBD_magnet_clr + 1', body=TAB)
    # Thin-bezel test window along +Y edge: leaves a 1.1 mm x 18 mm x 6 mm rib matching cover_L/T/R minimum bezel
    win_y0 = _num(TY + TAB_SIZE_Y - TAB_RIB_W - TAB_WIN_H)
    feature('box', 'SMP_TAB_BEZEL_WINDOW', corner=[_num(TX + TAB_WIN_X[0]), win_y0, -1.0],
            length=str(_num(TAB_WIN_X[1] - TAB_WIN_X[0])), width=str(TAB_WIN_H), height='SMP_tab_T + 2',
            operation='cut', participants=[TAB])
    for name, shape in tab_texts().items():
        loops, outers, n = [], [], 0
        for outer, islands in cover_pattern_v5._loops(shape):
            outers.append([f'l{n + j + 1}' for j in range(len(outer))])
            for loop in [outer, *islands]:
                loops.append(loop)
                n += len(loop)
        sk = sketch(f'SK_SMP_TAB_TEXT_{name}', plane(0), loops)
        feature('extrude', f'SMP_TAB_TEXT_{name}', sketch=sk, profiles=dict(type='curves', loops=outers),
                extent=cut_ext(cover_pattern_v5.DEPTH), operation='cut', targets=[TAB])


def _circle_segment_area(r, d):
    """Area of circular segment cut off at distance d from centre (0 <= d <= r)."""
    return r * r * math.acos(d / r) - d * math.sqrt(r * r - d * d)


def expected(values):
    """{body: (volume, (x0, y0, z0, x1, y1, z1))} from the evaluated parameters."""
    from shapely.geometry import Polygon, box as sbox
    v = values
    p, m, T = v['SMP_pitch'], v['SMP_margin'], v['SMP_T']
    L, W = COLUMNS * p + 2 * m, v['SMP_W']
    disc = lambda d: math.pi * d * d / 4
    vol = L * W * T
    # Corner chamfer
    vol -= CHAMFER * CHAMFER / 2 * T
    # Row C switch holes (7 columns)
    for c in range(COLUMNS):
        s = v['SMP_hole_min'] + c * v['SMP_hole_step']
        vol -= s * s * T + (POCKET * POCKET - s * s) * (T - v['SMP_ledge'])
    # Row D: M2, M3, CB, LEGMAG
    bore = v['TBD_so_screw_D'] + v['TBD_so_clr']
    vol -= sum(disc(v['SMP_m2_min'] + i * v['SMP_m2_step']) * T for i in range(len(ROW_D['M2'])))
    vol -= sum(disc(v['SMP_m3_min'] + i * v['SMP_m3_step']) * T for i in range(len(ROW_D['M3'])))
    for i in range(len(ROW_D['CB'])):
        cb = v['TBD_so_cb_D']
        vol -= disc(v['SMP_cb_min'] + i * v['SMP_cb_step']) * cb + disc(bore) * (T - cb)
    # Row D: 4 protruding Ø8 SO insert bosses (Z -3..0) with 5 mm hole (Z -3..2) and Ø3.4 bore (Z 2..5)
    boss_r = v['v5_so_boss_D'] / 2
    ins_depth = v['v5_so_insert_hole_depth']
    for i in range(len(ROW_D['INSERT'])):
        d_ins = v['SMP_ins_min'] + i * v['SMP_ins_step']
        boss_area = disc(v['v5_so_boss_D'])
        if i == SO4_CLIP_INDEX:
            boss_area -= _circle_segment_area(boss_r, mounts_v5.INSERT_HOLE_D / 2 + SO4_WALL)
        vol += boss_area * BOSS_PROTRUSION
        vol -= disc(d_ins) * ins_depth + disc(bore) * (T + BOSS_PROTRUSION - ins_depth)
    mag_h = v['TBD_magnet_T'] + v['TBD_magnet_clr']
    vol -= sum(disc(v['SMP_legmag_min'] + i * v['SMP_legmag_step']) * mag_h for i in range(len(ROW_D['LEGMAG'])))
    # 3 integrated front-seam R pockets along +Y edge
    x, y = COUPON_AT
    blank = sbox(x, y, x + L, y + W)
    for name, u0 in SEAM_R_U0.items():
        variant = seam_v5.VARIANTS[name]
        _, pocket = seam_v5.outlines(variant)
        pocket_in = Polygon([_seam_to_coupon(px, py, u0) for px, py in pocket]).intersection(blank)
        hex_area = Polygon([_seam_to_coupon(px, py, u0) for px, py in seam_v5.hexagon(*variant.screw, variant.nut_AF)]).area
        vol -= pocket_in.area * variant.tab_T
        vol -= disc(seam_v5.M2_CLEAR_D) * (variant.floor - variant.nut_D)
        vol -= hex_area * variant.nut_D
    out = {COUPON: (vol, (x, y, -BOSS_PROTRUSION, x + L, y + W, T))}

    t, H = v['SMP_tab_T'], v['TBD_cover_boss_H']
    tvol = TAB_SIZE_X * TAB_SIZE_Y * t + disc(v['TBD_cover_boss_D']) * H
    tvol -= disc(v['TBD_magnet_D'] + 2 * v['TBD_magnet_clr']) * mag_h
    tvol -= sum(disc(v['SMP_magf_min'] + i * v['SMP_magf_step']) * mag_h for i in range(len(TAB_FLAT)))
    tvol -= (TAB_WIN_X[1] - TAB_WIN_X[0]) * TAB_WIN_H * t
    tvol -= sum(Polygon(o, i).area for s in tab_texts().values() for o, i in cover_pattern_v5._loops(s)) * cover_pattern_v5.DEPTH
    tx, ty = TAB_AT
    out[TAB] = (tvol, (tx, ty, 0.0, tx + TAB_SIZE_X, ty + TAB_SIZE_Y, t + H))
    return out


def walls(values):
    """Plan-view material left between neighbouring features (mm); every one must keep the MJF / resin wall."""
    v = values
    p, m = v['SMP_pitch'], v['SMP_margin']
    L, W = COLUMNS * p + 2 * m, v['SMP_W']
    largest = dict(M2=v['SMP_m2_min'] + 3 * v['SMP_m2_step'], M3=v['SMP_m3_min'] + 3 * v['SMP_m3_step'],
                   CB=v['SMP_cb_min'] + 2 * v['SMP_cb_step'], INSERT=v['v5_so_boss_D'],
                   LEGMAG=v['SMP_legmag_min'] + 2 * v['SMP_legmag_step'])
    xs = sorted((x, largest[k] / 2) for k, row in ROW_D.items() for x in row)
    seam_inward = seam_v5.TAB_END_X + seam_v5.PRODUCTION.end_gap - seam_v5.R_EDGE_X
    seam_nut_wall = min(variant.screw[0] - variant.nut_AF / 2 - seam_v5.R_EDGE_X
                        for variant in seam_v5.VARIANTS.values())
    out = dict(
        row_D_between=round(min(b[0] - b[1] - a[0] - a[1] for a, b in zip(xs, xs[1:])), 3),
        row_D_ends=round(min(xs[0][0] - xs[0][1], L - xs[-1][0] - xs[-1][1]), 3),
        row_D_to_row_C=round((ROW_D_Y - max(r for _, r in xs)) - (ROW_C_Y + POCKET / 2), 3),
        row_D_to_seam=round((W - seam_inward) - (ROW_D_Y + max(r for _, r in xs)), 3),
        row_C_front=round(ROW_C_Y - POCKET / 2, 3),
        switch_cells=round(p - POCKET, 3),
        ledge=v['SMP_ledge'],
        under_counterbore=round(v['SMP_T'] - v['TBD_so_cb_D'], 3),
        over_leg_magnet=round(v['SMP_T'] - v['TBD_magnet_T'] - v['TBD_magnet_clr'], 3),
        over_insert=round(v['SMP_T'] + BOSS_PROTRUSION - v['v5_so_insert_hole_depth'], 3),
        insert_boss_wall=round(min((v['v5_so_boss_D'] - (v['SMP_ins_min'] + 3 * v['SMP_ins_step'])) / 2, SO4_WALL), 3),
        seam_nut_to_edge=round(seam_nut_wall, 3),
        boss_magnet_wall=round((v['TBD_cover_boss_D'] - v['TBD_magnet_D'] - 2 * v['TBD_magnet_clr']) / 2, 3),
        tab_bezel_rib=round(TAB_RIB_W, 3),
    )
    from shapely.geometry import box
    tx, ty = TAB_AT
    tab = box(tx, ty, tx + TAB_SIZE_X, ty + TAB_SIZE_Y)
    out['text_to_tab_edge'] = round(min(tab.exterior.distance(s) for s in tab_texts().values()), 3)
    return out


def check(evaluated, production_values):
    """Both coupons are closed single bodies with the volume and box of their parameters; the parameters follow the
    production model; walls keep the material limits. Returns the report."""
    values = {q['name']: q['value'] for q in evaluated['params'] if q.get('value') is not None}
    for name in ('TBD_plate_T', 'TBD_upper_plate_T', 'TBD_sw_ledge_T', 'TBD_sw_hole', 'TBD_so_cb_D', 'TBD_so_head_D',
                 'TBD_cover_boss_D', 'TBD_cover_T', 'TBD_magnet_D', 'v5_legmag_plate_clr', 'v5_so_insert_hole_D',
                 'v5_so_insert_H', 'v5_so_boss_D', 'v5_so_insert_hole_depth'):
        assert abs(values[name] - production_values[name]) < 1e-9, (name, values[name], production_values[name])
    assert abs(values['SMP_ins_min'] + values['SMP_ins_step'] - mounts_v5.INSERT_HOLE_D) < 1e-9, 'insert row is stale'
    assert abs(values['SMP_T'] - values['SMP_upper'] - values['SMP_ledge'] - production_values['TBD_sw_notch_H']) < 1e-9
    assert abs(TAB_RIB_W - production_values['v5_cover_silhouette_min_rail']) < 1e-9
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
    assert min(v for k, v in w.items() if k not in ('boss_magnet_wall', 'text_to_tab_edge', 'tab_bezel_rib')) >= 1.0 - 1e-9, w
    assert w['boss_magnet_wall'] >= 0.8 - 1e-9 and w['tab_bezel_rib'] >= 0.8 - 1e-9 and w['text_to_tab_edge'] >= TEXT_EDGE, w
    report['walls_mm'] = w
    report['ranges'] = dict(
        hole=[round(values['SMP_hole_min'] + i * values['SMP_hole_step'], 3) for i in range(COLUMNS)],
        m2=[round(values['SMP_m2_min'] + i * values['SMP_m2_step'], 3) for i in range(len(ROW_D['M2']))],
        m3=[round(values['SMP_m3_min'] + i * values['SMP_m3_step'], 3) for i in range(len(ROW_D['M3']))],
        counterbore=[round(values['SMP_cb_min'] + i * values['SMP_cb_step'], 3) for i in range(len(ROW_D['CB']))],
        insert_hole=[round(values['SMP_ins_min'] + i * values['SMP_ins_step'], 3) for i in range(len(ROW_D['INSERT']))],
        plate_leg_magnet=[round(values['SMP_legmag_min'] + i * values['SMP_legmag_step'], 3) for i in range(len(ROW_D['LEGMAG']))],
        seam_R_fit=[v.fit for v in seam_v5.VARIANTS.values()],
        seam_R_nut_AF=[v.nut_AF for v in seam_v5.VARIANTS.values()],
        tab_flat_magnet=[round(values['SMP_magf_min'] + i * values['SMP_magf_step'], 3) for i in range(len(TAB_FLAT))],
        tab_bezel_rib_mm=TAB_RIB_W,
        tab_text_stroke=[round(cover_pattern_v5.stroke() * s, 3) for s, _ in TAB_TEXT.values()],
        tab_text_rib=[round(cover_pattern_v5.rib() * s, 3) for s, _ in TAB_TEXT.values()])
    return report
