"""Build the v5 production CAD from v4 without touching v4.

v5 (2026-11-06, user request):
  1. two-level cover (2nd pass, plan docs/v5-plan-two-level-cover-2026-11-06.md):
     - base top Z 16.1 = plate top 13 + magnet 2 + pocket clearance 0.1 + 1.0 skin over the lower-leg magnet
       pockets (rim reference Z 14 -> +2.1);
     - a collar around every key window rises to Z 19.0 = keycap skirt bottom at rest (switch seat 11.3 + 6.0,
       r2 based) + 1.7 skirt cover (rim +5.0); collar width 1.5 beyond the 1.0 key margin;
     - built as one extrude cut (COVER_DROP_V5) from Z 19 down to 16.1 of the sketch regions outside the
       46 "window + collar" rectangles; trapped pockets between collars narrower than 2.0 stay at full height.
     The cover keeps its underside (plate contact Z 13), lip, locating bosses and the six boss magnets;
     only the top grows: TBD_cover_T 2 -> 6 (1st pass: flat Z 18, TBD_cover_T 5; snapshot model/review_v5/flat_Z18).
  2. one magnet pair at the tip of each lower leg of the left/right C-shaped covers (user: lower legs only).
     cover pocket + plate pocket, Ø3x2 like the existing six. The plate rabbet is filled locally (pad)
     and the cover lip is relieved there, so both pockets keep >= 1 mm walls.
  4. upper plate layer 2.0 -> 1.7 (user 2026-11-06): the switch seat rises 0.3 (Z 11 -> 11.3), so a keycap
     bottoms out 0.3 further above the plate top than on r2 (r2: 2T upper plate, almost no play but works).
  3. key margin: every keycap footprint (actual width) grown by v5_key_margin is cut out of the cover,
     added to the r2 window (the window never shrinks). Key layout, switch and keycap heights unchanged.

Run from the repository: python tools/build_seam_v5.py            (writes model/46es_mount_seam_v5.sc)
                         python tools/build_seam_v5.py --probe    (builds into guide/.cache/v5 only, prints checks)
                         python tools/build_seam_v5.py --flat     (1st-pass flat cover, guide/.cache/v5/v5_flat.sc only)
"""
import argparse
import copy
import hashlib
import json
import math
from pathlib import Path
import subprocess
import sys
import zipfile

from make_key_dxf import load_keys, rect

ROOT = Path(__file__).resolve().parents[1]
CLI = Path('C:/Program Files/SolidCraft/solidcraft-cli.exe')
SOURCE = ROOT / 'model/46es_mount_seam_v4.sc'
OUTPUT = ROOT / 'model/46es_mount_seam_v5.sc'
CACHE = ROOT / 'guide/.cache/v5'
KEY_MARGIN = 1.0
COLLAR_W = 1.5            # v5_collar_W: window edge -> collar outer face
CAP_1U = 18.05
# Drop-region raster (plan §2-2): the sketch holds one big rectangle and the 46 window+collar rectangles; the
# regions of "big rectangle minus the union of the key rectangles" are cut down to the base. Trapped pockets
# between collars are cut only when their inscribed width is >= 2 * DROP_MIN_HALF_WIDTH (no dust grooves).
DROP_STEP = 0.05
DROP_BOX = (-2.0, 288.0, -2.0, 97.0)
DROP_MIN_HALF_WIDTH = 1.0
# Leg-end magnet pairs (lower legs only, user 2026-11-06). Chosen on a 0.05 mm raster so that
# cover pocket Ø3.2 and plate pocket Ø3.3 keep >= 1.2 mm to the v5 window, the 16.5 openings
# and the part edges, as close to the leg tip as that allows.
LEG_MAGNETS = {'L': (94.0, 2.5, 'PLATE_L_SPLIT_V1', 'COVER_L_DRAFT_TBD'),
               'R': (167.7, 2.5, 'PLATE_R_SPLIT_V1', 'COVER_R_DRAFT_TBD')}
COVERS = ['COVER_L_DRAFT_TBD', 'COVER_T_DRAFT_TBD', 'COVER_R_DRAFT_TBD']


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(*args):
    result = subprocess.run([str(CLI), *map(str, args)], capture_output=True)
    if result.returncode:
        raise RuntimeError(result.stderr.decode('utf-8', errors='replace')[-5000:])


def overlap(a, b):
    """Separating-axis test for two convex polygons."""
    for poly in (a, b):
        for i in range(len(poly)):
            (x1, y1), (x2, y2) = poly[i], poly[(i + 1) % len(poly)]
            nx, ny = y1 - y2, x2 - x1
            pa = [nx * x + ny * y for x, y in a]
            pb = [nx * x + ny * y for x, y in b]
            if max(pa) <= min(pb) + 1e-9 or max(pb) <= min(pa) + 1e-9:
                return False
    return True


def key_rects(keys, m):
    """Keycap footprints (actual widths) grown by m on every side."""
    return [rect(k['x'], k['y'], CAP_1U + (k['w_u'] - 1) * 19.05 + 2 * m, CAP_1U + 2 * m, k['rot']) for k in keys]


def margin_groups(keys, m=KEY_MARGIN):
    """Grown keycap rectangles, split into groups whose members do not overlap (one sketch each)."""
    groups = []
    for r in key_rects(keys, m):
        for g in groups:
            if not any(overlap(r, o) for o in g):
                g.append(r)
                break
        else:
            groups.append([r])
    return groups


def drop_regions(keys, m=KEY_MARGIN + COLLAR_W, step=DROP_STEP, box=DROP_BOX, min_half_width=DROP_MIN_HALF_WIDTH):
    """Connected components of (big rectangle minus the union of the window+collar rectangles) on a raster.

    Each component gets one interior pick point (the point farthest from any boundary). The outer component
    (touching the big rectangle) is always selected; a trapped component only when its inscribed half-width
    is >= min_half_width. Raster slivers (one cell wide along the edge of a rotated rectangle) are reported
    but never selected.
    """
    import numpy as np
    from scipy import ndimage
    x0, x1, y0, y1 = box
    xs = np.arange(x0, x1 + step / 2, step)
    ys = np.arange(y0, y1 + step / 2, step)
    X, Y = np.meshgrid(xs, ys)
    inside = np.zeros(X.shape, bool)
    for k in keys:
        w = CAP_1U + (k['w_u'] - 1) * 19.05 + 2 * m
        h = CAP_1U + 2 * m
        a = math.radians(k['rot'])
        c, s = math.cos(a), math.sin(a)
        dx, dy = X - k['x'], Y - k['y']
        u, v = dx * c + dy * s, -dx * s + dy * c
        inside |= (np.abs(u) <= w / 2) & (np.abs(v) <= h / 2)
    labels, n = ndimage.label(~inside)          # 4-connectivity
    border = set(np.unique(np.concatenate([labels[0], labels[-1], labels[:, 0], labels[:, -1]]))) - {0}
    objects = ndimage.find_objects(labels, n)
    regions = []
    for lab in range(1, n + 1):
        comp = labels == lab
        padded = np.pad(comp, 1)                 # the raster border counts as a boundary for the pick point
        dist = ndimage.distance_transform_edt(padded)[1:-1, 1:-1] * step
        j, i = np.unravel_index(int(np.argmax(dist)), dist.shape)
        sl = objects[lab - 1]
        outer = lab in border
        half = float(dist.max())
        regions.append(dict(
            point=[round(float(xs[i]), 3), round(float(ys[j]), 3)], outer=outer,
            area_mm2=round(float(comp.sum()) * step * step, 3), inscribed_half_width_mm=round(half, 3),
            bbox=[round(float(xs[sl[1].start]), 2), round(float(ys[sl[0].start]), 2),
                  round(float(xs[sl[1].stop - 1]), 2), round(float(ys[sl[0].stop - 1]), 2)],
            selected=bool(outer or half >= min_half_width)))
    assert sum(r['outer'] for r in regions) == 1, 'the outer region must be one connected band'
    return regions


# ------------------------------------------------------------------------------------ BRep top-level audit
def horizontal_faces(solid):
    """(z, signed plan area) of every horizontal planar face of a cached SolidCraft solid; +area = normal +Z.

    The cache stores loops clockwise when seen along the outward normal, so the shoelace sum is negated.
    """
    sys.path.insert(0, str(ROOT / 'inspection/scripts'))
    from read_sc_cache import curve_points
    out = []
    for shell in solid['shells']:
        for face in shell['faces']:
            sf = face['surface']
            if sf['kind'] != 'plane_through':
                continue
            a, u, v = sf['origin'], sf['u_point'], sf['v_point']
            if abs(u[2] - a[2]) + abs(v[2] - a[2]) > 1e-7:
                continue
            area = 0.0
            for loop in face['loops']:
                for edge in loop:
                    pts = curve_points(shell['edges'][edge['edge']]['curve'])
                    if not edge['forward']:
                        pts = pts[::-1]
                    area += sum(p[0] * q[1] - q[0] * p[1] for p, q in zip(pts, pts[1:])) / 2
            out.append((a[2], -area))
    return out


def top_levels(model, bodies=COVERS, tol=1e-4):
    """Per body: {Z: area} of the upward (+Z) horizontal faces, Z rounded to 1e-4."""
    sys.path.insert(0, str(ROOT / 'inspection/scripts'))
    from verify_minimal_v2 import live_shapes
    shapes = live_shapes(model)
    levels = {}
    for name in bodies:
        acc = {}
        for solid in shapes[name]:
            for z, area in horizontal_faces(solid):
                if area > tol:
                    key = round(z, 4)
                    acc[key] = acc.get(key, 0.0) + area
        levels[name] = {z: round(a, 3) for z, a in sorted(acc.items())}
    return levels


def build(flat=False, probe=False):
    CACHE.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(SOURCE) as archive:
        doc = json.loads(archive.read('document.json'))
        container = archive.read('container.json')
    params = {p['name']: p for p in doc['params']}

    def new_param(name, expr, comment, unit='mm', before=None):
        p = dict(name=name, expr=str(expr), comment=comment, model=False, unit=unit)
        index = len(doc['params']) if before is None else doc['params'].index(params[before])
        doc['params'].insert(index, p)
        params[name] = p

    # --- 1. cover height: two levels (plan §2-1) ------------------------------------------------------
    new_param('v5_rim_ref_Z', 14, '[v5 설계 기준 2026-11-06] 케이스 테두리 상단 Z. PSD60 1차 실측 M05 rim_F/rim_B 14(캘리퍼 대략값)를 '
              '커버 높이 비교 기준으로만 쓴다(형상은 자석 적층에서 유도). 케이스 형상(REF_WIL_*/REF_PSD_*)은 바꾸지 않는다',
              before='TBD_cover_T')
    new_param('v5_legmag_skin', 1.0, '[v5 2차 2026-11-06] 아래 다리 자석 포켓(윗면 Z 15.1) 위에 남기는 최소 살. 8001 레진 벽 규칙 ≥ 1.0',
              before='TBD_cover_T')
    new_param('v5_cover_base_Z', 'v5_cover_top_Z' if flat else
              'v4_plate_top_Z + TBD_magnet_T + TBD_magnet_clr + v5_legmag_skin',
              '[v5 2차 유도값] 커버 바닥(창 둘레 턱 밖) 윗면 Z = plate 윗면 13 + 자석 2 + 포켓 여유 0.1 + 살 1.0 = 16.1 (테두리 14 + 2.1). '
              '테두리가 아니라 다리 자석 적층에서 유도한다' + (' — --flat: 평판형이라 턱 윗면과 같다' if flat else ''),
              before='TBD_cover_T')
    new_param('v5_keycap_bottom_above_seat', 6.0, '[v5 2차 r2 근거 2026-11-06] 쉴 때 키캡 스커트 밑면 − 스위치 착좌면. r2: 2T upper plate 위에서 '
              '키캡을 끝까지 누르면 유격이 거의 없다 → 바닥에서 착좌 + 약 2, 쉴 때 + 약 6. r2 실측(upper plate 윗면 → 스커트 밑면 g)으로 '
              '확정: 2 + g', before='TBD_cover_T')
    new_param('v5_keycap_bottom_rest_Z', 'v4_plate_top_Z - TBD_upper_plate_T + v5_keycap_bottom_above_seat',
              '[v5 2차 유도값] 쉴 때 키캡 스커트 밑면 Z = 착좌 11.3 + 6.0 = 17.3', before='TBD_cover_T')
    new_param('v5_skirt_cover_H', 1.7, '[v5 2차 사용자 결정 2026-11-06] 턱이 쉴 때 키캡 옆면(스커트)을 덮는 높이. r2 약 3.0, v5 1차(평판 Z 18) 0.7. '
              '대안 1.2(턱 Z 18.5) / 0.7(Z 18)', before='TBD_cover_T')
    new_param('v5_cover_top_Z', 'v5_keycap_bottom_rest_Z + v5_skirt_cover_H',
              '[v5 2차 유도값] 창 둘레 턱(collar) 윗면 Z = 17.3 + 1.7 = 19.0 (테두리 14 + 5.0). v5 1차: 테두리 + 4 = 18',
              before='TBD_cover_T')
    new_param('v5_collar_W', COLLAR_W, '[v5 2차 사용자 결정 2026-11-06] 창 가장자리(키캡 + v5_key_margin)에서 턱 바깥면까지 폭. 레진 벽 ≥ 1.0. '
              '베젤이 이보다 좁은 앞·뒤 7곳에서는 턱이 커버 바깥면까지 찬다. SK36_COVER_DROP_V5 사각형은 이 값으로 만든 고정 숫자'
              '(tools/build_seam_v5.py에서 재생성)', before='TBD_cover_T')
    new_param('v5_cover_top_above_rim', 'v5_cover_top_Z - v5_rim_ref_Z', '[v5 2차 보고용] 턱 윗면 − 테두리 = 5.0', before='TBD_cover_T')
    new_param('v5_cover_base_above_rim', 'v5_cover_base_Z - v5_rim_ref_Z', '[v5 2차 보고용] 바닥 윗면 − 테두리 = 2.1', before='TBD_cover_T')
    cover_t = params['TBD_cover_T']
    cover_t['expr'] = 'v5_cover_top_Z - (TBD_frame_T + TBD_standoff_H + TBD_plate_T)'
    cover_t['comment'] = ('[v5 2차 2026-11-06] 커버 전체 높이(턱 윗면 Z 19 − plate 윗면 Z 13) = 6. 밑면·립·보스·자석은 그대로, 위로만 두꺼워짐'
                          '(v4: 2, v5 1차 평판: 5). 창 둘레 턱 밖은 COVER_DROP_V5로 v5_cover_base_Z(16.1)까지 깎는다. r2 실물은 5T+2T 2층')
    # --- 4. upper plate layer ------------------------------------------------------------------------
    upper = params['TBD_upper_plate_T']
    assert upper['expr'] == '2 mm', upper['expr']
    upper['expr'] = '1.7 mm'
    upper['comment'] = ('[v5 사용자 결정 2026-11-06] upper plate 층 두께 1.7(v4: 2 = r2 P3 2T). r2는 키캡을 끼우면 유격이 거의 없지만 '
                        '작동한다(사용자 확인) → 출력 공차를 감수하지 않도록 0.3 얇게. 스위치 착좌 Z 11 → 11.3, 14.0 홀 층 1.5 유지, '
                        '아래 릴리프 TBD_sw_notch_H 1.5 → 1.8')
    # Assumed switch envelopes (v4 features 242-244) were fixed to the v4 seat Z 11; make them follow the seat.
    by_id = {f['id']: f for f in doc['features']}
    seat_shift = '(2 - TBD_upper_plate_T)'
    for fid, name, key, old, new in [
            (242, 'REF_SWITCH_LOWER_PINS_BOUND_ASSUMED', 'start_offset', '-3.3', f'-3.3 + {seat_shift}'),
            (243, 'REF_SWITCH_LATCH_BOUND_ASSUMED', 'start_offset', None, seat_shift),
            (244, 'REF_SWITCH_UPPER_BOUND_ASSUMED', 'start_offset', '-2', '-TBD_upper_plate_T')]:
        f = by_id[fid]
        assert f['name'] == name and f['extent'].get(key) == old, (name, f['extent'])
        f['extent'][key] = new
    # --- 3. key margin (documentation parameter; sketch rectangles are fixed numbers) -----------
    new_param('v5_key_margin', KEY_MARGIN, '[v5 사용자 목표 2026-11-06] 키캡(실제 폭, 바닥 외곽) ↔ 커버 창 최소 여유. '
              'SK35_COVER_KEY_MARGIN_V5_* 사각형은 이 값으로 만든 고정 숫자(tools/build_seam_v5.py에서 재생성)')
    # --- 2. leg magnets ------------------------------------------------------------------------------
    new_param('v5_legmag_plate_clr', 0.15, '[v5 설계 후보] plate 쪽 다리 자석 포켓 반경 여유(Ø3.3). MJF ±0.3: 빡빡하면 Ø3.3 드릴로 손질, '
              '헐거우면 에폭시로 채움(plate 재출력 없음)')
    new_param('v5_legpad_L', 8, '[v5 설계 후보] 다리 자석 자리에서 plate 가장자리 단차(rabbet)를 메우는 받침 길이(X)')
    new_param('v5_lip_relief_clr', 0.3, '[v5 설계 후보] 받침 양끝 ↔ 커버 립 절단 끝 여유(X, 편측)')
    for s, (x, y, plate, cover) in LEG_MAGNETS.items():
        new_param(f'v5_legmag_{s}_X', x, f'[v5 2026-11-06] {s} 커버 아래 다리 끝 자석 쌍 X(래스터로 고른 고정값: 벽 ≥ 1.2)')
        new_param(f'v5_legmag_{s}_Y', y, f'[v5 2026-11-06] {s} 커버 아래 다리 끝 자석 쌍 Y(앞 가장자리 쪽)')

    def feature(kind, name, **kwargs):
        fid = doc['next_id']; doc['next_id'] += 1
        doc['features'].append(dict(id=fid, type=kind, name=name, suppressed=False, **kwargs))
        return fid

    def sketch(name, plane, polygons):
        points = [dict(id='origin', pos=[0., 0.], fixed=True)]
        curves = []
        for poly in polygons:
            first = len(points)
            for x, y in poly:
                points.append(dict(id=f'p{len(points)}', pos=[x, y], fixed=True))
            for j in range(len(poly)):
                curves.append(dict(id=f'l{len(curves) + 1}', type='line', construction=False,
                                   a=first + j, b=first + (j + 1) % len(poly)))
        return feature('sketch', name, plane=plane,
                       sketch=dict(points=points, curves=curves, constraints=[],
                                   counters=dict(p=len(points), l=len(curves))))

    top_plane = dict(type='offset', base=dict(type='origin', name='XY'),
                     distance='TBD_frame_T + TBD_standoff_H + TBD_plate_T + TBD_cover_T')
    keys = load_keys(.693, .667)
    groups = margin_groups(keys)
    for i, group in enumerate(groups, 1):
        sk = sketch(f'SK35_COVER_KEY_MARGIN_V5_{i}', top_plane, group)
        feature('extrude', f'COVER_KEY_MARGIN_V5_{i}', sketch=sk, profiles=dict(type='all'),
                extent=dict(convention='total_distance', direction='negative',
                            distance='TBD_cover_T + TBD_cover_lip_H + 0.5'),
                operation='cut', targets=list(COVERS))

    front_plate = '-TBD_pcb0_dy + TBD_plate_gap'
    for s, (x, y, plate, cover) in LEG_MAGNETS.items():
        X, Y = f'v5_legmag_{s}_X', f'v5_legmag_{s}_Y'
        # plate: fill the rabbet under the leg tip (local support), then the pocket
        feature('box', f'PLATE_LEGPAD_{s}_V5', corner=[f'{X} - v5_legpad_L/2', front_plate,
                                                      'v4_plate_top_Z - TBD_cover_lip_H - 0.05'],
                length='v5_legpad_L', width='TBD_cover_wall + TBD_cover_lip_clr + 0.05',
                height='TBD_cover_lip_H + 0.05', operation='join', participants=[plate])
        feature('box', f'COVER_LIP_RELIEF_{s}_V5', corner=[f'{X} - v5_legpad_L/2 - v5_lip_relief_clr',
                                                          '-TBD_pcb0_dy + TBD_cover_gap - 1',
                                                          'v4_plate_top_Z - TBD_cover_lip_H - 0.5'],
                length='v5_legpad_L + 2*v5_lip_relief_clr', width='TBD_cover_wall + 1.5',
                height='TBD_cover_lip_H + 0.5', operation='cut', participants=[cover])
        feature('cylinder', f'COVER_LEGMAG_{s}_V5', axis=[0., 0., 1.], base=[X, Y, 'v4_plate_top_Z - 1'],
                height='1 + TBD_magnet_T + TBD_magnet_clr', radius='(TBD_magnet_D + 2*TBD_magnet_clr) / 2',
                operation='cut', participants=[cover])
        feature('cylinder', f'PLATE_LEGMAG_{s}_V5', axis=[0., 0., 1.],
                base=[X, Y, 'v4_plate_top_Z - TBD_magnet_T - TBD_magnet_clr'],
                height='TBD_magnet_T + TBD_magnet_clr + 1', radius='(TBD_magnet_D + 2*v5_legmag_plate_clr) / 2',
                operation='cut', participants=[plate])
        for side, z in [('COVER', 'v4_plate_top_Z + TBD_magnet_clr'),
                        ('PLATE', 'v4_plate_top_Z - TBD_magnet_clr - TBD_magnet_T')]:
            name = f'REF_LEGMAG_{s}_{side}'
            feature('cylinder', name, axis=[0., 0., 1.], base=[X, Y, z], height='TBD_magnet_T',
                    radius='TBD_magnet_D / 2', operation='new_body', body_names=[name])
            doc['appearances']['bodies'][name] = copy.deepcopy(doc['appearances']['bodies'].get(
                'REF_SO1_MAGNET', dict(name='Custom', color=[167, 174, 181], opacity=1.0)))

    # --- 1b. two-level cover: one sketch (big rectangle + 46 window+collar rectangles), region-pick cut ---------
    regions = None
    if not flat:
        regions = drop_regions(keys)
        x0, x1, y0, y1 = DROP_BOX
        big = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
        sketch('SK36_COVER_DROP_V5', top_plane, [big] + key_rects(keys, KEY_MARGIN + COLLAR_W))
        doc['name'] = ('46es seam v5 - two-level cover (base Z 16.1 / collar Z 19), lower-leg magnet pairs, '
                       '1 mm key margin, upper plate 1.7')
    else:
        doc['name'] = '46es seam v5 flat (1st pass shape: cover top Z 19 flat), lower-leg magnet pairs, 1 mm key margin, upper plate 1.7'
    seed = CACHE / ('seed_v5_flat.sc' if flat else 'seed_v5.sc')
    with zipfile.ZipFile(seed, 'w', zipfile.ZIP_DEFLATED) as archive:
        archive.writestr('document.json', json.dumps(doc, ensure_ascii=False))
        archive.writestr('container.json', container)
    pending = CACHE / ('v5_flat.sc' if flat else 'v5.sc')
    if flat:
        run('run', '--in', seed, '--save', pending, '--quiet')
    else:
        # The point picks are turned into stored curve selections by the extrude command itself, so the cut is
        # added through a command script on top of the seed design (document.json has no point-pick form).
        picks = [dict(point=r['point']) for r in regions if r['selected']]
        script = [dict(command='solid.extrude', params=dict(
            name='COVER_DROP_V5', sketch='SK36_COVER_DROP_V5', profiles=picks, exact_regions=True,
            operation='cut', targets=list(COVERS), direction='negative', start_offset=0.5,
            distance='v5_cover_top_Z - v5_cover_base_Z + 0.5'))]
        script_path = CACHE / 'drop_v5.json'
        script_path.write_text(json.dumps(script), encoding='utf-8')
        run('run', script_path, '--in', seed, '--save', pending, '--quiet')
    report = CACHE / ('eval_v5_flat.json' if flat else 'eval_v5.json')
    run('eval', '--in', pending, '--json-out', report)
    evaluated = json.loads(report.read_text(encoding='utf-8'))
    failed = [f for f in evaluated['timeline'] if f.get('error')]
    assert not failed, failed
    values = {p['name']: p['value'] for p in evaluated['params'] if p.get('value') is not None}
    bodies = {b['name']: b for b in evaluated['bodies']}
    top_z, base_z = values['v5_cover_top_Z'], values['v5_cover_base_Z']
    info = dict(model=str(pending if (flat or probe) else OUTPUT), flat=flat, source_sha=sha(SOURCE),
                bodies=evaluated['body_count'], margin_sketches=len(groups), timeline=len(evaluated['timeline']),
                params=len(doc['params']), cover_top_Z=top_z, cover_base_Z=base_z, cover_T=values['TBD_cover_T'],
                covers={n: dict(volume_mm3=round(bodies[n]['volume_mm3'], 3), z=[round(bodies[n]['bbox']['min'][2], 4),
                                                                                round(bodies[n]['bbox']['max'][2], 4)])
                        for n in COVERS})
    for n in COVERS:
        assert abs(bodies[n]['bbox']['max'][2] - top_z) < 1e-6, (n, bodies[n]['bbox'])
    if not flat:
        # probe (b): the upward faces of each cover sit at exactly two levels, collar top and base top
        levels = top_levels(pending)
        for n, lv in levels.items():
            assert set(lv) == {round(base_z, 4), round(top_z, 4)}, (n, lv)
        info.update(drop_regions=regions, drop_picks=len([r for r in regions if r['selected']]),
                    unselected_regions=[r for r in regions if not r['selected']], cover_levels=levels,
                    drop_depth=round(top_z - base_z, 4))
        if not probe:
            pending.replace(OUTPUT)
            info['output_sha'] = sha(OUTPUT)
    (CACHE / ('build_v5_flat.json' if flat else ('probe_v5.json' if probe else 'build_v5.json'))).write_text(
        json.dumps(info, indent=1, ensure_ascii=False), encoding='utf-8')
    print(json.dumps({k: v for k, v in info.items() if k != 'drop_regions'}, ensure_ascii=False, indent=1))
    return info


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--flat', action='store_true', help='1st-pass flat cover into guide/.cache/v5/v5_flat.sc only')
    ap.add_argument('--probe', action='store_true', help='build into guide/.cache/v5/v5.sc only and print the checks')
    a = ap.parse_args()
    build(flat=a.flat, probe=a.probe)
