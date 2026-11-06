"""Build the v5 production CAD from the fixed v4 baseline.

The r2 cover layers have flat faces. Keep the raised v5 Z 19 top, existing
three-piece outline, keycap clearance, and magnet seats, with one flat face
per piece. Integral mount seats support the switch plate from underneath.

Run from the repository root with python 46es/tools/build_seam_v5.py.
Use --probe to build into guide/.cache/v5 without replacing the current CAD.
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
SOURCE = ROOT / 'model/baselines/seam_v4.sc'
OUTPUT = ROOT / 'model/46es_mount_seam_v5.sc'
CACHE = ROOT / 'guide/.cache/v5'
KEY_MARGIN = 1.0
LEGMAG_SKIN_MIN = 1.3
CAP_1U = 18.05
# Leg-end magnet pairs (lower legs only, user 2026-11-06). Chosen on a 0.05 mm raster so that
# cover pocket Ø3.2 and plate pocket Ø3.3 keep >= 1.2 mm to the v5 window, the 16.5 openings
# and the part edges, as close to the leg tip as that allows.
LEG_MAGNETS = {'L': (94.0, 2.5, 'PLATE_L_SPLIT_V1', 'COVER_L_DRAFT_TBD'),
               'R': (167.7, 2.5, 'PLATE_R_SPLIT_V1', 'COVER_R_DRAFT_TBD')}
COVERS = ['COVER_L_DRAFT_TBD', 'COVER_T_DRAFT_TBD', 'COVER_R_DRAFT_TBD']

# The two left seats flare toward the outside of the SO1/SO2 bosses.
# The other seats follow the mount rails with tangent round ends, clear of the hardware.
PLATE_SUPPORTS = [
    # mount, bearing body, end centres (XY), end radii (mm)
    ('MOUNT_L_PAIR_V3', 'PLATE_L_SPLIT_V1', (6.35, 12.55), (5.6, 23.65), 2.7, 2.25),
    ('MOUNT_L_PAIR_V3', 'PLATE_L_SPLIT_V1', (5.55, 82.55), (5.1, 74.65), 2.35, 2.1),
    ('MOUNT_R_PAIR_V3', 'PLATE_R_SPLIT_V1', (281, 24.5), (280.85, 33.65), 2.0, 2.0),
    ('MOUNT_R_PAIR_V3', 'PLATE_R_SPLIT_V1', (257, 71.85), (256.65, 77.2), 2.0, 2.0),
    ('MOUNT_H02_SO3_MIN_V2', 'PLATE_L_SPLIT_V1', (126.1, 51.5), (126.1, 54.5), 2.0, 2.0),
    ('MOUNT_H03_SO6_MIN_V2', 'PLATE_R_SPLIT_V1', (175.2, 8.15), (184.55, 8.8), 2.7, 2.7),
    ('MOUNT_H03_SO6_MIN_V2', 'PLATE_R_SPLIT_V1', (143.95, 6.5), (152.1, 6.5), 2.1, 2.1),
]
SEAT_ROOT_Z = 1.5


def seat_sketch_name(index):
    return f'SK37_MOUNT_PLATE_SEAT_{index}_V5'


def rounded_seat(a, b, ra, rb):
    """Sketch the convex hull of two round ends, with two common tangents."""
    dx, dy = b[0] - a[0], b[1] - a[1]
    axis = math.atan2(dy, dx)
    tangent = math.acos((ra - rb) / math.hypot(dx, dy))

    def point(center, radius, angle):
        return [center[0] + radius * math.cos(axis + angle),
                center[1] + radius * math.sin(axis + angle)]

    # Split the end arcs so every arc travels less than 180 degrees.
    boundary = [point(a, ra, -tangent), point(b, rb, -tangent), point(b, rb, 0),
                point(b, rb, tangent), point(a, ra, tangent), point(a, ra, math.pi)]
    points = [dict(id='origin', pos=[0., 0.], fixed=True)]
    points += [dict(id=f'p{i}', pos=xy, fixed=True) for i, xy in enumerate([*boundary, a, b], 1)]
    curves = [
        dict(id='l1', type='line', a=1, b=2, construction=False),
        dict(id='a1', type='arc', a=2, b=3, c=8, construction=False),
        dict(id='a2', type='arc', a=3, b=4, c=8, construction=False),
        dict(id='l2', type='line', a=4, b=5, construction=False),
        dict(id='a3', type='arc', a=5, b=6, c=7, construction=False),
        dict(id='a4', type='arc', a=6, b=1, c=7, construction=False),
    ]
    polygon_area = sum(x * v - y * u for (x, y), (u, v)
                       in zip(boundary, boundary[1:] + boundary[:1])) / 2
    segment_area = rb**2 * (tangent - math.sin(tangent))
    end_angle = math.pi - tangent
    segment_area += ra**2 * (end_angle - math.sin(end_angle))
    sketch = dict(points=points, curves=curves, constraints=[], counters=dict(p=len(points), l=2, a=4))
    return sketch, polygon_area + segment_area


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
    from cad_model import live_shapes
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


def build(probe=False):
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

    new_param('v5_rim_ref_Z', 14, 'Approximate PSD60 rim height for comparison only', before='TBD_cover_T')
    new_param('v5_legmag_skin_min', LEGMAG_SKIN_MIN, 'Minimum resin skin above the leg magnet pocket',
              before='TBD_cover_T')
    new_param('v5_keycap_bottom_above_seat', 6.0, '[v5 2차 r2 근거 2026-11-06] 쉴 때 키캡 스커트 밑면 − 스위치 착좌면. r2: 2T upper plate 위에서 '
              '키캡을 끝까지 누르면 유격이 거의 없다 → 바닥에서 착좌 + 약 2, 쉴 때 + 약 6. r2 실측(upper plate 윗면 → 스커트 밑면 g)으로 '
              '확정: 2 + g', before='TBD_cover_T')
    new_param('v5_keycap_bottom_rest_Z', 'v4_plate_top_Z - TBD_upper_plate_T + v5_keycap_bottom_above_seat',
              '[v5 2차 유도값] 쉴 때 키캡 스커트 밑면 Z = 착좌 11.3 + 6.0 = 17.3', before='TBD_cover_T')
    new_param('v5_skirt_cover_H', 1.7, '[v5 2차 사용자 결정 2026-11-06] 턱이 쉴 때 키캡 옆면(스커트)을 덮는 높이. r2 약 3.0, v5 1차(평판 Z 18) 0.7. '
              '대안 1.2(턱 Z 18.5) / 0.7(Z 18)', before='TBD_cover_T')
    new_param('v5_cover_top_Z', 'v5_keycap_bottom_rest_Z + v5_skirt_cover_H',
              'Single flat cover top at Z 19', before='TBD_cover_T')
    new_param('v5_cover_top_above_rim', 'v5_cover_top_Z - v5_rim_ref_Z',
              'Flat cover top minus approximate rim height', before='TBD_cover_T')
    new_param('v5_legmag_skin', 'v5_cover_top_Z - v4_plate_top_Z - TBD_magnet_T - TBD_magnet_clr',
              'Actual material over the lower leg magnet pocket', before='TBD_cover_T')
    cover_t = params['TBD_cover_T']
    cover_t['expr'] = 'v5_cover_top_Z - (TBD_frame_T + TBD_standoff_H + TBD_plate_T)'
    cover_t['comment'] = 'Flat cover thickness from the plate top to Z 19'
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

    seat_plane = dict(type='offset', base=dict(type='origin', name='XY'), distance=str(SEAT_ROOT_Z))
    for i, (mount, _, a, b, ra, rb) in enumerate(PLATE_SUPPORTS, 1):
        profile, _ = rounded_seat(a, b, ra, rb)
        sk = feature('sketch', seat_sketch_name(i), plane=seat_plane, sketch=profile)
        feature('extrude', f'MOUNT_PLATE_SEAT_{i}_V5', sketch=sk, profiles=dict(type='all'),
                extent=dict(convention='total_distance', direction='positive',
                            distance=f'v4_plate_top_Z - TBD_plate_T - {SEAT_ROOT_Z}'),
                operation='join', targets=[mount])

    doc['name'] = '46es seam v5 - flat cover and direct plate supports'
    seed = CACHE / 'seed_v5.sc'
    with zipfile.ZipFile(seed, 'w', zipfile.ZIP_DEFLATED) as archive:
        archive.writestr('document.json', json.dumps(doc, ensure_ascii=False))
        archive.writestr('container.json', container)
    pending = CACHE / 'v5.sc'
    run('run', '--in', seed, '--save', pending, '--quiet')
    report = CACHE / 'eval_v5.json'
    run('eval', '--in', pending, '--json-out', report)
    evaluated = json.loads(report.read_text(encoding='utf-8'))
    failed = [f for f in evaluated['timeline'] if f.get('error')]
    assert not failed, failed
    values = {p['name']: p['value'] for p in evaluated['params'] if p.get('value') is not None}
    bodies = {b['name']: b for b in evaluated['bodies']}
    top_z = values['v5_cover_top_Z']
    assert values['v5_legmag_skin'] >= values['v5_legmag_skin_min']
    levels = top_levels(pending)
    for name, faces in levels.items():
        assert set(faces) == {round(top_z, 4)}, (name, faces)
        assert abs(bodies[name]['bbox']['max'][2] - top_z) < 1e-6, name
    info = dict(model=str(pending if probe else OUTPUT), source_sha=sha(SOURCE),
                bodies=evaluated['body_count'], timeline=len(evaluated['timeline']),
                cover_top_Z=top_z, cover_T=values['TBD_cover_T'], cover_levels=levels)
    if not probe:
        pending.replace(OUTPUT)
        info['output_sha'] = sha(OUTPUT)
    (CACHE / ('probe_v5.json' if probe else 'build_v5.json')).write_text(
        json.dumps(info, indent=1, ensure_ascii=False), encoding='utf-8')
    print(json.dumps(info, ensure_ascii=False, indent=1))
    return info


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--probe', action='store_true', help='build into guide/.cache/v5/v5.sc only and print the checks')
    a = ap.parse_args()
    build(probe=a.probe)
