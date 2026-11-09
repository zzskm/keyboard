"""Build the v5 production CAD from the fixed v4 baseline.

The r2 cover layers have flat faces. Keep the raised v5 Z 19 top, existing
three-piece outline, keycap clearance, and magnet seats, with one flat face
per piece. The four mounts are extruded directly from the CADCraft drawing
(tools/mounts_v5.py); the v4 frame/mask/pair chain and the reference-only
switch envelopes and Wilmore housing are suppressed in the production model.

Run from the repository root with python 46es/tools/build_seam_v5.py.
  --probe   build into guide/.cache/v5 without replacing the current CAD
  --mounts  build only the four mounts into guide/.cache/v5/mounts_v5.sc from a
            parameter-only document and check their sections (seconds, for mount iteration)
"""
# SOURCE OF TRUTH - Edit this file. Do NOT hand-edit generated .sc files.
# Regenerate outputs with: python tools/build_seam_v5.py (and export scripts as needed)
import argparse
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time
import zipfile

from make_key_dxf import load_keys, rect
from mounts_v5 import (MOUNTS, LEFT_MOUNT, RIGHT_MOUNT, REAR_MOUNT, FRONT_MOUNT, PLATE_SUPPORT_MOUNTS,  # noqa: F401
                       MX_GUIDES, MX_CONTACTS, MX_CONTACT_SIZE, MX_PIN_DEPTH_FROM_SEAT, MOUNT_PIN_CLEARANCE,
                       PAD_ROOT_Z, PAD_TOP_Z, SHIM_TOP_Z, SO_ANCHORS, PLATE_FLANGE_INNER,
                       profiles as mount_profiles, expected_sections, expected_volume, emit as emit_mounts)

ROOT = Path(__file__).resolve().parents[1]
CLI = Path('C:/Program Files/SolidCraft/solidcraft-cli.exe')
SOURCE = ROOT / 'model/baselines/seam_v4.sc'
OUTPUT = ROOT / 'model/46es_mount_seam_v5.sc'
CACHE = ROOT / 'guide/.cache/v5'
MOUNTS_ONLY = CACHE / 'mounts_v5.sc'
KEY_MARGIN = 1.0
LEGMAG_SKIN_MIN = 1.3
CAP_1U = 18.05
SEAT_ROOT_Z = PAD_ROOT_Z
# Leg-end magnet pairs (lower legs only, user 2026-11-06). Chosen on a 0.05 mm raster so that
# cover pocket Ø3.2 and plate pocket Ø3.3 keep >= 1.2 mm to the v5 window, the 16.5 openings
# and the part edges, as close to the leg tip as that allows.
LEG_MAGNETS = {'L': (94.0, 2.5, 'PLATE_L_SPLIT_V1', 'COVER_L_DRAFT_TBD'),
               'R': (167.7, 2.5, 'PLATE_R_SPLIT_V1', 'COVER_R_DRAFT_TBD')}
COVERS = ['COVER_L_DRAFT_TBD', 'COVER_T_DRAFT_TBD', 'COVER_R_DRAFT_TBD']

# v4 bodies that only existed to carve the old mounts; every feature touching them is suppressed.
LEGACY_MOUNT_BODIES = ('MOUNT_R_SPLIT_V1', 'MOUNT_L_SPLIT_V1', 'MOUNT_H01_SO2_MIN_V2', 'MOUNT_H02_SO3_MIN_V2',
                       'MOUNT_H03_SO6_MIN_V2', 'MOUNT_H04_SO4_MIN_V2', 'MOUNT_L_PAIR_V3', 'MOUNT_R_PAIR_V3',
                       'MASK_MOUNT_')
# Reference-only solids (not printed, not used by the production checks). The review model
# (tools/build_assembly_reference_v5.py) re-enables the housing features with measured PSD60 values.
REFERENCE_FEATURES = {7: 'HOUSING_OUTER_REF_WIL', 8: 'HOUSING_CAVITY_TBD', 10: 'HOUSING_POSTS_CAND',
                      11: 'HOUSING_USB_CUT_TBD', 242: 'REF_SWITCH_LOWER_PINS_BOUND_ASSUMED',
                      243: 'REF_SWITCH_LATCH_BOUND_ASSUMED', 244: 'REF_SWITCH_UPPER_BOUND_ASSUMED'}
REMOVED_BODIES = {'REF_HOUSING_WILMORE_NOT_PSD60', 'REF_SW_ASSUMED_01'} | {f'REF_SW_ASSUMED_01 ({i})' for i in range(2, 47)}


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
            if abs(u[2] - a[2]) + abs(v[2] - a[2]) > 5e-5:
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


# ------------------------------------------------------------------------------------ document helpers
def read_source():
    with zipfile.ZipFile(SOURCE) as archive:
        return json.loads(archive.read('document.json')), archive.read('container.json')


def helpers(doc):
    """feature()/sketch() closures that append native timeline features to doc."""
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
                points.append(dict(id=f'p{len(points)}', pos=[float(x), float(y)], fixed=True))
            for j in range(len(poly)):
                curves.append(dict(id=f'l{len(curves) + 1}', type='line', construction=False,
                                   a=first + j, b=first + (j + 1) % len(poly)))
        return feature('sketch', name, plane=plane,
                       sketch=dict(points=points, curves=curves, constraints=[],
                                   counters=dict(p=len(points), l=len(curves))))

    return feature, sketch


def write_seed(doc, container, path):
    with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED) as archive:
        archive.writestr('document.json', json.dumps(doc, ensure_ascii=False))
        archive.writestr('container.json', container)


def evaluate(seed, pending):
    """run + eval through the CLI; returns the evaluation and the wall time of the run."""
    started = time.perf_counter()
    run('run', '--in', seed, '--save', pending, '--quiet')
    elapsed = time.perf_counter() - started
    report = pending.with_name(f'eval_{pending.stem}.json')
    run('eval', '--in', pending, '--json-out', report)
    evaluated = json.loads(report.read_text(encoding='utf-8'))
    failed = [f for f in evaluated['timeline'] if f.get('error')]
    assert not failed, failed
    (CACHE / f'eval_{pending.stem}_{sha(pending)[:16]}.json').write_bytes(report.read_bytes())
    return evaluated, elapsed


def strip_legacy(doc):
    """Suppress the v4 mount chain and the reference-only solids; returns the suppressed feature names."""
    def legacy(body):
        return isinstance(body, str) and body.startswith(LEGACY_MOUNT_BODIES)

    suppressed = []
    for f in doc['features']:
        if f.get('suppressed'):
            continue
        refs = set()
        for key in ('targets', 'participants', 'body_names', 'bodies', 'tools'):
            if isinstance(f.get(key), list):
                refs |= set(f[key])
        refs |= {f[key] for key in ('target', 'body') if isinstance(f.get(key), str)}
        if not any(legacy(b) for b in refs):
            continue
        others = {b for b in refs if not legacy(b)}
        if others:
            # shared feature: keep it for the other bodies (the ring/lap hardware removal)
            assert f['type'] == 'remove', (f['id'], f['name'], others)
            f['bodies'] = [b for b in f['bodies'] if not legacy(b)]
            continue
        f['suppressed'] = True
        suppressed.append(f['name'])
    by_id = {f['id']: f for f in doc['features']}
    for fid, name in REFERENCE_FEATURES.items():
        assert by_id[fid]['name'] == name, (fid, by_id[fid]['name'])
        by_id[fid]['suppressed'] = True
        suppressed.append(name)
    return suppressed


def check_mounts(evaluated, mounts):
    """Every mount is one closed body whose volume and box follow the drawing and the parameters."""
    bodies = {b['name']: b for b in evaluated['bodies']}
    values = {p['name']: p['value'] for p in evaluated['params'] if p.get('value') is not None}
    for name, (_, anchor, _) in SO_ANCHORS.items():
        index = name[2]
        evaluated_anchor = (values[f'REF_SO_dX{index}'] - values['TBD_pcb0_dx'], values[f'REF_SO_dY{index}'] - values['TBD_pcb0_dy'])
        assert all(abs(a - b) < 1e-6 for a, b in zip(anchor, evaluated_anchor)), (name, anchor, evaluated_anchor)
    assert abs(values['v4_plate_top_Z'] - values['TBD_plate_T'] - PAD_TOP_Z) < 1e-9
    assert abs(values['split_spine_bottom_Z'] - values['split_support_gap'] - SHIM_TOP_Z) < 1e-9
    assert abs(values['split_flange_W'] - 2.0) < 1e-9 and abs(values['split_flange_H'] - 3.0) < 1e-9
    assert abs(-values['TBD_pcb0_dx'] + values['TBD_plate_gap'] + values['split_flange_W'] - PLATE_FLANGE_INNER[0]) < 1e-9
    report = {}
    for suffix, profile in mounts.items():
        body = bodies[profile['mount']]
        expected = expected_volume(profile)
        x0, y0, x1, y1 = profile['outline'].bounds
        box_ok = all(abs(a - b) < 0.01 for a, b in zip(body['bbox']['min'][:2] + body['bbox']['max'][:2], (x0, y0, x1, y1)))
        top = PAD_TOP_Z if profile['pads'] else values['TBD_frame_T']
        assert body['closed'] and box_ok and abs(body['bbox']['min'][2]) < 1e-6 and abs(body['bbox']['max'][2] - top) < 1e-6, body
        assert abs(body['volume_mm3'] - expected) / expected < 0.002, (profile['mount'], body['volume_mm3'], expected)
        report[profile['mount']] = dict(volume_mm3=round(body['volume_mm3'], 3), expected_mm3=round(expected, 3),
                                        bbox=body['bbox'])
    return report


def build(probe=False):
    CACHE.mkdir(parents=True, exist_ok=True)
    doc, container = read_source()
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
    # They are suppressed in the production model (strip_legacy) and stay suppressed in the review model.
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

    feature, sketch = helpers(doc)
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

    # Phase 2: CTRL bracket/gate simplification — remove lips, stop and stop finger
    # for simpler, straighter Pro Micro insertion/removal and USB/cable clearance.
    for ctrl_name in (
        'CTRL_LIP_F_LOW_SPLIT_V1',
        'CTRL_LIP_F_UP_SPLIT_V1',
        'CTRL_LIP_B_LOW_SPLIT_V1',
        'CTRL_LIP_B_UP_SPLIT_V1',
        'CTRL_STOP_SPLIT_V1',
        'CTRL_GATE_STOP_FINGER',
    ):
        ctrl = next(f for f in doc['features'] if f.get('name') == ctrl_name)
        ctrl['suppressed'] = True

    # Mounts: the v4 frame → split → mask → pair chain is suppressed; the four bodies are
    # rebuilt under their existing names straight from the CADCraft drawing.
    suppressed = strip_legacy(doc)
    mounts = mount_profiles()
    emit_mounts(feature, sketch, mounts)

    doc['name'] = '46es seam v5 - flat cover, drawing-built mounts and direct plate supports'
    seed = CACHE / 'seed_v5.sc'
    write_seed(doc, container, seed)
    pending = CACHE / 'v5.sc'
    evaluated, elapsed = evaluate(seed, pending)
    values = {p['name']: p['value'] for p in evaluated['params'] if p.get('value') is not None}
    bodies = {b['name']: b for b in evaluated['bodies']}
    assert not REMOVED_BODIES & set(bodies), REMOVED_BODIES & set(bodies)
    top_z = values['v5_cover_top_Z']
    assert values['v5_legmag_skin'] >= values['v5_legmag_skin_min']
    levels = top_levels(pending)
    for name, faces in levels.items():
        assert set(faces) == {round(top_z, 4)}, (name, faces)
        assert abs(bodies[name]['bbox']['max'][2] - top_z) < 1e-6, name
    mount_report = check_mounts(evaluated, mounts)
    active = sum(1 for f in evaluated['timeline'] if not f.get('suppressed'))
    info = dict(model=str(pending if probe else OUTPUT), source_sha=sha(SOURCE),
                bodies=evaluated['body_count'], timeline=len(evaluated['timeline']), active_features=active,
                suppressed_legacy=len(suppressed), run_seconds=round(elapsed, 1),
                evaluation_ms=round(sum(f.get('ms', 0) for f in evaluated['timeline'])),
                cover_top_Z=top_z, cover_T=values['TBD_cover_T'], cover_levels=levels, mounts=mount_report)
    if not probe:
        pending.replace(OUTPUT)
        info['output_sha'] = sha(OUTPUT)
    (CACHE / ('probe_v5.json' if probe else 'build_v5.json')).write_text(
        json.dumps(info, indent=1, ensure_ascii=False), encoding='utf-8')
    print(json.dumps(info, ensure_ascii=False, indent=1))
    return info


def build_mounts():
    """Fast loop for mount work: the four mounts alone, from a parameter-only copy of the v4 document."""
    sys.path.insert(0, str(ROOT / 'inspection/scripts'))
    from mesh_section import read_stl, compare
    CACHE.mkdir(parents=True, exist_ok=True)
    doc, container = read_source()
    doc['features'] = []
    doc['next_id'] = 1
    doc['visibility'] = {key: [] for key in doc['visibility']}
    doc['appearances'] = {'bodies': {}}
    doc['name'] = '46es v5 mounts only - drawing check'
    upper = next(p for p in doc['params'] if p['name'] == 'TBD_upper_plate_T')
    upper['expr'] = '1.7 mm'                     # the pin relief floor follows the v5 seat
    feature, sketch = helpers(doc)
    mounts = mount_profiles()
    emit_mounts(feature, sketch, mounts)
    seed = CACHE / 'seed_mounts_v5.sc'
    write_seed(doc, container, seed)
    evaluated, elapsed = evaluate(seed, MOUNTS_ONLY)
    report = check_mounts(evaluated, mounts)
    stl_dir = CACHE / 'mounts_stl'
    stl_dir.mkdir(exist_ok=True)
    script = [dict(command='file.export_stl', params=dict(path=str(stl_dir / f'{suffix}.stl'), bodies=[p['mount']], quality='fine'))
              for suffix, p in mounts.items()]
    (CACHE / 'mounts_export.json').write_text(json.dumps(script), encoding='utf-8')
    run('run', str(CACHE / 'mounts_export.json'), '--in', MOUNTS_ONLY, '--quiet')
    sections = {}
    for suffix, p in mounts.items():
        sections[p['mount']] = compare(read_stl(stl_dir / f'{suffix}.stl'), expected_sections(p))
    ok = all(level['ok'] for body in sections.values() for level in body.values())
    warnings = [f['name'] for f in evaluated['timeline'] if f.get('warning')]
    info = dict(model=str(MOUNTS_ONLY), features=len(evaluated['timeline']), run_seconds=round(elapsed, 2),
                evaluation_ms=round(sum(f.get('ms', 0) for f in evaluated['timeline'])), warnings=warnings,
                bodies=report, sections=sections, sections_ok=ok)
    (CACHE / 'mounts_v5.json').write_text(json.dumps(info, indent=1, ensure_ascii=False), encoding='utf-8')
    print(json.dumps(info, ensure_ascii=False, indent=1))
    assert ok, 'mount sections differ from the drawing'
    return info


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--probe', action='store_true', help='build into guide/.cache/v5/v5.sc only and print the checks')
    ap.add_argument('--mounts', action='store_true', help='build and check only the four mounts (guide/.cache/v5/mounts_v5.sc)')
    a = ap.parse_args()
    build_mounts() if a.mounts else build(probe=a.probe)
