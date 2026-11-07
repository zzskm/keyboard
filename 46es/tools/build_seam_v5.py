"""Build the v5 production CAD from the fixed v4 baseline.

The r2 cover layers have flat faces. Keep the raised v5 Z 19 top, existing
three-piece outline, keycap clearance, and magnet seats, with one flat face
per piece. Integral mount seats support the switch plate from underneath.

Run from the repository root with python 46es/tools/build_seam_v5.py.
Use --probe to build into guide/.cache/v5 without replacing the current CAD.
"""
# SOURCE OF TRUTH - Edit this file. Do NOT hand-edit generated .sc files.
# Regenerate outputs with: python tools/build_seam_v5.py (and export scripts as needed)
import argparse
import copy
import hashlib
import json
import math
from pathlib import Path
import subprocess
import sys
import zipfile

import ezdxf
from shapely.geometry import LineString, Point, Polygon
from shapely.ops import polygonize, unary_union

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

FRONT_MOUNT = 'MOUNT_H03_SO6_MIN_V2'
SEAT_ROOT_Z = 1.5

# KS-3X1 drawing XY, with conservative cylindrical guides and rectangular contacts.
# Both reference pin families extend to Z 2.7 at the v5 switch seat (Z 11.3).
MX_GUIDES = ((0.0, 1.95), (-5.08, 0.875), (5.08, 0.875))
MX_CONTACTS = ((-3.81, 2.54), (2.54, 5.08))
MX_CONTACT_SIZE = (1.15, 0.5)
MX_PIN_DEPTH_FROM_SEAT = 8.6
MOUNT_PIN_CLEARANCE = 0.4

LEFT_MOUNT = 'MOUNT_L_PAIR_V3'
RIGHT_MOUNT = 'MOUNT_R_PAIR_V3'
REAR_MOUNT = 'MOUNT_H02_SO3_MIN_V2'
PLATE_SUPPORT_MOUNTS = {
    LEFT_MOUNT: 'PLATE_L_SPLIT_V1',
    RIGHT_MOUNT: 'PLATE_R_SPLIT_V1',
    REAR_MOUNT: 'PLATE_L_SPLIT_V1',
    FRONT_MOUNT: 'PLATE_R_SPLIT_V1',
}


def right_rail_x(y):
    """Centre of the rail through SO5 and SO4 in assembly coordinates."""
    return 278.519 + (250.42 - 278.519) * (y - 6.52) / (89.007 - 6.52)


def mount_outline_profiles():
    """Plan profiles at the frame datum, outside the retained hardware bores."""
    def rectangle(x0, y0, x1, y1):
        return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]

    # Each T uses a straight rail through the two M3 pods and a single branch
    # to an offset case M2. The open steps in the join polygons leave the
    # existing case M2 pockets and their bearing faces in place.
    return (
        (LEFT_MOUNT, 'L', [
            [(1.15, 9.6), (10.9, 9.6), (10.9, 61.55), (21.9, 61.55),
             (21.9, 71.15), (10.9, 71.15), (10.9, 84.65), (1.15, 84.65),
             (1.15, 41.8), (7.3, 41.8), (7.3, 34.5), (1.15, 34.5)],
        ], [
            rectangle(-2, 9.6, 1.15, 32.85),
            rectangle(-2, 43.35, 1.15, 84.65),
            rectangle(10.9, 9.6, 32, 61.55),
            rectangle(10.9, 71.15, 32, 84.65),
        ]),
        (RIGHT_MOUNT, 'R', [
            [(right_rail_x(9.6) - 5.3, 9.6), (right_rail_x(9.6) + 5.7, 9.6),
             (right_rail_x(22.05) + 5.7, 22.05), (283.8, 22.05),
             (283.8, 34.7), (277.9, 34.7), (277.9, 43.4),
             (right_rail_x(43.4) + 5.7, 43.4), (right_rail_x(63.0) + 5.7, 63.0),
             (256.9, 63.0), (256.9, 70.4), (right_rail_x(70.4) + 5.7, 70.4),
             (right_rail_x(85.5) + 5.7, 85.5), (right_rail_x(85.5) - 5.3, 85.5)],
        ], [
            [(243, 9.6), (right_rail_x(9.6) - 5.3, 9.6),
             (right_rail_x(85.5) - 5.3, 85.5), (243, 85.5)],
            [(right_rail_x(9.6) + 5.7, 9.6), (287, 9.6), (287, 22.05),
             (right_rail_x(22.05) + 5.7, 22.05)],
            [(right_rail_x(43.4) + 5.7, 43.4), (287, 43.4), (287, 85.5),
             (right_rail_x(85.5) + 5.7, 85.5), (right_rail_x(71.85) + 5.7, 71.85),
             (264.65, 71.85), (264.65, 63.0), (right_rail_x(63.0) + 5.7, 63.0)],
            # Keep the H06 pod inside the measured PSD60 wall (X 285.307).
            rectangle(285.05, 33, 287, 43.4),
        ]),
        (REAR_MOUNT, 'REAR', [
            # Straight line from the H02 shoulder to the SO3 pod.
            [(131.6, 51.4), (133.65, 51.4), (135.05, 84.65), (132.0, 84.65)],
        ], []),
    )


def polygons_for_sketch(geometry):
    """Return closed 2D rings for SolidCraft's nested profile detection."""
    if geometry.is_empty:
        return []
    shapes = list(geometry.geoms) if hasattr(geometry, 'geoms') else [geometry]
    rings = []
    for shape in shapes:
        if shape.geom_type != 'Polygon' or shape.area <= 1e-8:
            continue
        rings.append([[float(x), float(y)] for x, y in list(shape.exterior.coords)[:-1]])
        rings.extend([[float(x), float(y)] for x, y in list(ring.coords)[:-1]]
                     for ring in shape.interiors)
    return rings


def mount_cadcraft_profiles():
    """Read the checked-in lightweight CAD and the saved v5 body footprints."""
    dxf_path = ROOT / 'model/mounts_cadcraft_phase1.dxf'
    basis_path = ROOT / 'model/mounts_cadcraft_phase1_basis.json'
    basis = json.loads(basis_path.read_text(encoding='utf-8'))
    if sha(dxf_path) != basis['source_dxf_sha256']:
        raise ValueError('CADCraft DXF changed; refresh mounts_cadcraft_phase1_basis.json first')

    drawing = ezdxf.readfile(dxf_path)
    entities = list(drawing.modelspace())

    def line_outline(layers, xmin, xmax):
        lines = []
        for entity in entities:
            if entity.dxftype() != 'LINE' or entity.dxf.layer not in layers:
                continue
            start, end = entity.dxf.start, entity.dxf.end
            line = LineString([(start.x, start.y), (end.x, end.y)])
            if xmin <= line.bounds[0] and line.bounds[2] <= xmax:
                lines.append(line)
        profiles = list(polygonize(unary_union(lines)))
        outline = unary_union(profiles)
        if outline.geom_type != 'Polygon' or not outline.is_valid:
            raise ValueError(f'CADCraft outline is not one closed polygon: {layers}')
        return outline

    outlines = {
        'L': line_outline({'0', 'L_OUTLINE'}, -5, 40),
        'FRONT': line_outline({'0'}, 120, 200),
    }
    outlines['FRONT'] = outlines['FRONT'].buffer(-0.1, join_style='mitre')
    # The CADCraft top shoulder is just under the 1 mm MJF wall limit after
    # the clip inset. Raise this one straight edge by 0.15 mm; the H03 head
    # bearing and other datum faces stay fixed.
    front_top = max(y for _, y in outlines['FRONT'].exterior.coords)
    outlines['FRONT'] = Polygon([
        (x, y + 0.15 if abs(y - front_top) < 1e-6 else y)
        for x, y in outlines['FRONT'].exterior.coords
    ])
    # The L clip shares three snapped perimeter lines with the legacy BRep.
    # Exact coincidence makes SolidCraft retry the Boolean and produces
    # non-manifold STL edges. Move only those clip-mask vertices to the next
    # 0.5 mm snap outside the existing body; the mount's datum faces stay fixed.
    outlines['L'] = Polygon([
        (11.0 if abs(x - 10.9) < 0.001 else
         3.5 if abs(x - 3.41887) < 0.001 else x, y)
        for x, y in outlines['L'].exterior.coords
    ])
    if not outlines['L'].is_valid:
        raise ValueError('Adjusted CADCraft L outline is invalid')
    for suffix, layer in [('R', 'R_OUTLINE'), ('REAR', 'REAR_OUTLINE')]:
        matches = [entity for entity in entities
                   if entity.dxftype() == 'LWPOLYLINE' and entity.dxf.layer == layer]
        if len(matches) != 1 or not matches[0].closed:
            raise ValueError(f'CADCraft layer {layer} must have one closed outline')
        outlines[suffix] = Polygon(matches[0].get_points('xy'))
        if not outlines[suffix].is_valid:
            raise ValueError(f'CADCraft outline is invalid: {layer}')
        if suffix == 'R':
            # Keep the clip clear of legacy rails and curved BRep edges.
            outlines[suffix] = outlines[suffix].buffer(-0.1, join_style='mitre')
        elif suffix == 'REAR':
            outlines[suffix] = outlines[suffix].buffer(-0.1, join_style='mitre')

    supports = {suffix: [] for suffix in ('L', 'R', 'REAR', 'FRONT')}
    for entity in entities:
        if entity.dxftype() != 'LWPOLYLINE' or entity.dxf.layer != '0' or not entity.closed:
            continue
        polygon = Polygon(entity.get_points('xy'))
        x0, y0, x1, y1 = polygon.bounds
        if x1 < 40:
            supports['L'].append(polygon)
        elif x0 > 240:
            supports['R'].append(polygon)
        elif x0 > 120 and x1 < 200:
            supports['FRONT'].append(polygon)
    rear_seats = [entity for entity in entities
                  if entity.dxftype() == 'LWPOLYLINE' and entity.dxf.layer == 'REAR_PLATE_SEATS']
    rear_shims = [entity for entity in entities
                  if entity.dxftype() == 'LWPOLYLINE' and entity.dxf.layer == 'REAR_SHIM']
    if len(rear_seats) != 1 or len(rear_shims) != 1:
        raise ValueError('CADCraft Rear plate and shim support profiles are missing')
    supports['REAR'] = [Polygon(rear_seats[0].get_points('xy'))]
    # The plate has a downturned inner lip along the left edge. Keep the
    # bearing pads clear of its measured footprint while retaining the datum.
    inner_lip_clearance = Polygon([(1.7, -10), (300, -10), (300, 110), (1.7, 110)])
    supports['L'] = [shape.intersection(inner_lip_clearance) for shape in supports['L']]
    for suffix, count in [('L', 2), ('R', 2), ('REAR', 1), ('FRONT', 2)]:
        if len(supports[suffix]) != count or any(not shape.is_valid for shape in supports[suffix]):
            raise ValueError(f'CADCraft {suffix} supports must contain {count} valid profiles')
    supports['L'].sort(key=lambda shape: shape.bounds[1])
    supports['R'].sort(key=lambda shape: -shape.bounds[3])
    supports['FRONT'].sort(key=lambda shape: shape.bounds[0])
    # This CADCraft pad is a snapped rectangle; preserve that bounding profile
    # and model its nut clearance as a separate cylindrical Boolean.
    x0, y0, x1, y1 = supports['FRONT'][0].bounds
    supports['FRONT'][0] = Polygon([(x0, y0), (x1, y0), (x1, y1), (x0, y1)])

    mount_names = {'L': LEFT_MOUNT, 'R': RIGHT_MOUNT,
                   'REAR': REAR_MOUNT, 'FRONT': 'MOUNT_H03_SO6_MIN_V2'}
    relief_layers = {suffix: f'{suffix}_RELIEFS' for suffix in outlines}
    reliefs = {suffix: unary_union([
        Polygon(entity.get_points('xy')) for entity in entities
        if entity.dxftype() == 'LWPOLYLINE' and entity.dxf.layer == relief_layers[suffix]
    ]) for suffix in outlines}
    clip_outlines = dict(outlines)
    for suffix in ('R', 'REAR', 'FRONT'):
        old_footprint = unary_union([Polygon(points)
                                     for points in basis['outline_sections'][suffix]['polygons']])
        old_outer = Polygon(old_footprint.exterior.coords)
        safe_region = old_outer.buffer(-0.15, join_style='round').simplify(
            0.08, preserve_topology=True).buffer(0)
        clip_outlines[suffix] = outlines[suffix].intersection(safe_region)
        if clip_outlines[suffix].geom_type != 'Polygon' or not clip_outlines[suffix].is_valid:
            raise ValueError(f'CADCraft {suffix} clip must remain one valid polygon inside the legacy outline')

    additions = {}
    for suffix, outline in outlines.items():
        saved = basis['outline_sections'][suffix]['polygons']
        old_footprint = unary_union([Polygon(points) for points in saved])
        overlap = 0.2 if suffix in {'R', 'REAR', 'FRONT'} else 0.02
        addition = outline.difference(old_footprint).buffer(overlap).intersection(outline)
        addition = addition.difference(reliefs[suffix]).buffer(0)
        addition = addition.simplify(0.08, preserve_topology=True).buffer(0)
        parts = list(addition.geoms) if hasattr(addition, 'geoms') else [addition]
        additions[suffix] = unary_union([part for i, part in enumerate(parts, 1)
                                          if part.geom_type == 'Polygon' and part.area > (20.0 if suffix == 'R' else 10.0)])

    keys = load_keys(.693, .667)
    key46 = keys[45]
    switch46 = Polygon(rect(key46['x'], key46['y'], 13.98, 13.98, key46['rot']))
    key11 = keys[10]
    switch11 = Polygon(rect(key11['x'], key11['y'], 16.5, 16.5, key11['rot']))
    return dict(outlines=outlines, clip_outlines=clip_outlines, supports=supports, additions=additions,
                rear_shim=Polygon(rear_shims[0].get_points('xy')),
                switch11=switch11, switch46=switch46,
                nut_clearance=Point(139.5, 6.6).buffer(2.55, quad_segs=24),
                mount_names=mount_names)


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

    # Phase 1-B: MOUNT_L_PAIR_V3 / MOUNT_R_PAIR_V3 T자 단순화 — 불필요 WEB 형상 제거
    # Phase 1-C: MOUNT_H03_SO6_MIN_V2 앞/하단 정리 — 두 WEB 제거
    # Phase 1-D: MOUNT_H02_SO3_MIN_V2 뒤/상단 개선 — WEB 제거
    for web_name in (
        'WEB_MOUNT_H05_SO1_MIN_V2_EXTRUDE',
        'WEB_MOUNT_H06_SO5_MIN_V2_0_EXTRUDE',
        'WEB_MOUNT_H03_SO6_MIN_V2_0_EXTRUDE',
        'WEB_MOUNT_H03_SO6_MIN_V2_1_EXTRUDE',
        'WEB_MOUNT_H02_SO3_MIN_V2_0_EXTRUDE',
    ):
        web = next(f for f in doc['features'] if f.get('name') == web_name)
        web['suppressed'] = True

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

    frame_plane = dict(type='origin', name='XY')
    for mount, suffix, rails, trims in mount_outline_profiles():
        for i, polygon in enumerate(rails, 1):
            name = f'MOUNT_OUTLINE_{suffix}_RAIL_{i}_V5'
            sk = sketch(f'SK_{name}', frame_plane, [polygon])
            feature('extrude', name, sketch=sk, profiles=dict(type='all'),
                    extent=dict(convention='total_distance', direction='positive',
                                distance='TBD_frame_T'),
                    operation='join', targets=[mount])
        for i, polygon in enumerate(trims, 1):
            name = f'MOUNT_OUTLINE_{suffix}_TRIM_{i}_V5'
            sk = sketch(f'SK_{name}', frame_plane, [polygon])
            feature('extrude', name, sketch=sk, profiles=dict(type='all'),
                    extent=dict(convention='total_distance', direction='positive', distance='5'),
                    operation='cut', targets=[mount])

    cadcraft = mount_cadcraft_profiles()
    basis_path = ROOT / 'model/mounts_cadcraft_phase1_basis.json'
    basis = json.loads(basis_path.read_text(encoding='utf-8'))
    if basis['basis_model_sha256'] != '214fd0b5177c33c5fd5ec65036e8af159e74a5ac4ce52e487582ebfdc3b66cc6':
        raise ValueError('CADCraft profiles were based on a different pre-CADCraft v5 model')

    for suffix, outline in cadcraft['clip_outlines'].items():
        mount = cadcraft['mount_names'][suffix]
        # L/R source bodies have tiny z offsets near their frame faces. Let
        # intersection cutters pass 0.1 mm beyond both faces to avoid coplanar
        # Boolean caps that tessellate as detached or non-manifold STL facets.
        overrun_clip = suffix in {'L', 'R', 'REAR', 'FRONT'}
        clip_plane = (dict(type='offset', base=frame_plane, distance='-0.1')
                      if overrun_clip else frame_plane)
        clip_overrun = 'TBD_frame_T + 0.2' if overrun_clip else 'TBD_frame_T'
        outline_sketch = sketch(f'SK_MOUNT_CADCRAFT_{suffix}_CLIP_V6', clip_plane,
                                polygons_for_sketch(outline))
        feature('extrude', f'MOUNT_CADCRAFT_{suffix}_CLIP_V6', sketch=outline_sketch,
                profiles=dict(type='all'),
                extent=dict(convention='total_distance', direction='positive', distance=clip_overrun),
                operation='intersect', targets=[mount])

        additions = cadcraft['additions'][suffix]
        parts = list(additions.geoms) if hasattr(additions, 'geoms') else [additions]
        start_z = SEAT_ROOT_Z if suffix == 'REAR' else 0.0
        addition_plane = dict(type='offset', base=frame_plane, distance=str(start_z))
        for i, part in enumerate(parts, 1):
            addition_sketch = sketch(f'SK_MOUNT_CADCRAFT_{suffix}_FILL_{i}_V6', addition_plane,
                                     polygons_for_sketch(part))
            feature('extrude', f'MOUNT_CADCRAFT_{suffix}_FILL_{i}_V6', sketch=addition_sketch,
                    profiles=dict(type='all'),
                    extent=dict(convention='total_distance', direction='positive',
                                distance=f'TBD_frame_T - {start_z}'),
                    operation='join', targets=[mount])

    seat_plane = dict(type='offset', base=frame_plane, distance=str(SEAT_ROOT_Z))
    support_indices = {suffix: 0 for suffix in cadcraft['supports']}
    for suffix, support_shapes in cadcraft['supports'].items():
        mount = cadcraft['mount_names'][suffix]
        for support_shape in support_shapes:
            support_indices[suffix] += 1
            index = support_indices[suffix]
            if suffix == 'FRONT' and index == 1:
                support_shape = support_shape.difference(cadcraft['nut_clearance'])
            name = f'MOUNT_CADCRAFT_{suffix}_SUPPORT_{index}_V6'
            support_sketch = sketch(f'SK_{name}', seat_plane, polygons_for_sketch(support_shape))
            if suffix == 'FRONT' and index == 1:
                x0, y0, x1, y1 = cadcraft['supports'][suffix][index - 1].bounds
                feature('box', f'{name}_BBOX', corner=[x0, y0, str(SEAT_ROOT_Z)],
                        length=str(x1 - x0), width=str(y1 - y0),
                        height=f'v4_plate_top_Z - TBD_plate_T - {SEAT_ROOT_Z}',
                        operation='join', participants=[mount])
                feature('cylinder', f'{name}_NUT_CLEARANCE', axis=[0., 0., 1.],
                        base=[139.5, 6.6, str(SEAT_ROOT_Z)],
                        height=f'v4_plate_top_Z - TBD_plate_T - {SEAT_ROOT_Z}',
                        radius='2.55', operation='cut', participants=[mount])
                continue
            if suffix == 'R' and index == 2:
                continue  # This profile produces no geometry change in the SolidCraft body.
            feature('extrude', name, sketch=support_sketch, profiles=dict(type='all'),
                    extent=dict(convention='total_distance', direction='positive',
                                distance=f'v4_plate_top_Z - TBD_plate_T - {SEAT_ROOT_Z}'),
                    operation='join', targets=[mount])

    right_support_collision = cadcraft['supports']['R'][1].intersection(cadcraft['switch46']).buffer(0.15)
    if not right_support_collision.is_empty and right_support_collision.area > 0.01:
        clearance_plane = dict(type='offset', base=frame_plane, distance=str(SEAT_ROOT_Z))
        clearance_sketch = sketch('SK_MOUNT_CADCRAFT_R_SUPPORT_SWITCH_CLEARANCE_V6', clearance_plane,
                                  polygons_for_sketch(right_support_collision))
        feature('extrude', 'MOUNT_CADCRAFT_R_SUPPORT_SWITCH_CLEARANCE_V6',
                sketch=clearance_sketch, profiles=dict(type='all'),
                extent=dict(convention='total_distance', direction='positive', distance='6.5'),
                operation='cut', targets=[RIGHT_MOUNT])

    left_support_collision = cadcraft['supports']['L'][1].intersection(
        cadcraft['switch11'].buffer(0.15, quad_segs=1, join_style='mitre'))
    if not left_support_collision.is_empty and left_support_collision.area > 0.01:
        switch_bottom = 'TBD_frame_T + TBD_standoff_H - 3'
        clearance_plane = dict(type='offset', base=frame_plane, distance=f'{switch_bottom} - 0.05')
        clearance_sketch = sketch('SK_MOUNT_CADCRAFT_L_SWITCH11_BODY_CLEARANCE_V6', clearance_plane,
                                  polygons_for_sketch(left_support_collision))
        feature('extrude', 'MOUNT_CADCRAFT_L_SWITCH11_BODY_CLEARANCE_V6',
                sketch=clearance_sketch, profiles=dict(type='all'),
                extent=dict(convention='total_distance', direction='positive',
                            distance=f'v4_plate_top_Z - TBD_plate_T - ({switch_bottom}) + 0.1'),
                operation='cut', targets=[LEFT_MOUNT])

    shim_plane = dict(type='offset', base=frame_plane, distance='2.5')
    shim_sketch = sketch('SK_MOUNT_CADCRAFT_REAR_SHIM_V6', shim_plane,
                         polygons_for_sketch(cadcraft['rear_shim']))
    feature('extrude', 'MOUNT_CADCRAFT_REAR_SHIM_V6', sketch=shim_sketch, profiles=dict(type='all'),
            extent=dict(convention='total_distance', direction='positive', distance='0.8'),
            operation='join', targets=[REAR_MOUNT])

    # Open the pin recesses to the rail edges. Keep a continuous 2.1 mm floor.
    reliefs = (
        (LEFT_MOUNT, '10', (8.5, 53.55), (12.5, 58.35)),
        (LEFT_MOUNT, '11', (9.5, 72.55), (12.5, 75.5)),
        (RIGHT_MOUNT, '33_GUIDE', (246.0, 72.55), (252.3, 75.5)),
        (RIGHT_MOUNT, '33_CONTACT', (246.0, 78.1), (249.2, 79.85)),
        (RIGHT_MOUNT, '46_GUIDES', (274.25, 18.5), (277.25, 21.5)),
        (RIGHT_MOUNT, '46_CONTACT', (264.0, 24.05), (274.0, 25.85)),
    )
    floor = f'v4_plate_top_Z - TBD_upper_plate_T - {MX_PIN_DEPTH_FROM_SEAT} - 0.6'
    for mount, index, (x, y), (x_max, y_max) in reliefs:
        feature('box', f'MOUNT_SWITCH_RELIEF_{index}_V5', corner=[x, y, floor],
                length=str(round(x_max - x, 3)), width=str(round(y_max - y, 3)),
                height=f'TBD_frame_T + 0.05 - ({floor})',
                operation='cut', participants=[mount])

    # The key 18 guide and contact share one opening. Angle its inside edge
    # away from the H04 head recess and step out to reach the contact.
    relief_plane = dict(type='offset', base=frame_plane, distance=floor)
    key18 = sketch('SK_MOUNT_SWITCH_RELIEF_18_V5', relief_plane, [
        [(262.55, 61.5), (273.0, 61.5), (273.0, 66.35), (264.1, 66.35),
         (264.1, 64.45), (263.14, 64.45), (262.55, 63.3)],
    ])
    feature('extrude', 'MOUNT_SWITCH_RELIEF_18_V5', sketch=key18, profiles=dict(type='all'),
            extent=dict(convention='total_distance', direction='positive',
                        distance=f'TBD_frame_T + 0.05 - ({floor})'),
            operation='cut', targets=[RIGHT_MOUNT])

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
    (CACHE / f'eval_{pending.stem}_{sha(pending)[:16]}.json').write_bytes(report.read_bytes())
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
