"""Audit the flat v5 cover, plate supports, baseline BRep, and current print exports.

Run with python -B 46es/inspection/scripts/verify_seam_v5.py.
Writes inspection/data/seam-v5-verification.json and seam-v5-clearance.json.
"""
import csv, hashlib, json, math, subprocess, sys
from pathlib import Path
from cad_model import ROOT, live_shapes, document
from check_stl import check

sys.path.insert(0, str(ROOT / 'tools'))
from make_key_dxf import load_keys, rect  # noqa: E402
from build_seam_v5 import (COVERS, PLATE_SUPPORT_MOUNTS, SEAT_ROOT_Z,  # noqa: E402
                           horizontal_faces, mount_cadcraft_profiles, top_levels)

CLI = 'C:/Program Files/SolidCraft/solidcraft-cli.exe'
V4 = ROOT / 'model/baselines/seam_v4.sc'
V5 = ROOT / 'model/46es_mount_seam_v5.sc'
FLAT = ROOT / 'model/baselines/flat_Z18.sc'      # 1st pass, flat cover top Z 18 (plan §5-0)
V4_SHA = '606d1bd91b191c67b2abdc4c054704c905bcb63d6ad89c783263a3cd4f018d2b'
FLAT_SHA = '66a2ec87687415a81eec83dbb7ff6d15b1d810af2780a78cc6d699d214a3e43d'
SWITCH_BOUNDS = {'REF_SW_ASSUMED_01'} | {f'REF_SW_ASSUMED_01 ({i})' for i in range(2, 47)}  # follow the 1.7 seat
CHANGED = SWITCH_BOUNDS | set(PLATE_SUPPORT_MOUNTS) | {'PLATE_L_SPLIT_V1', 'PLATE_R_SPLIT_V1', 'COVER_L_DRAFT_TBD', 'COVER_T_DRAFT_TBD', 'COVER_R_DRAFT_TBD', 'CTRL_BRACKET_SPLIT_V1', 'CTRL_GATE_SPLIT_V1'}
# Copies of the plates made before the v5 features (seam coupon, order 1). TBD_upper_plate_T sits before the copy in
# the timeline, so they are re-evaluated; the coupon box holds no switch opening, so volume and box must equal v4.
DERIVED = {'SEAM_COUPON_L_V4', 'SEAM_COUPON_R_V4'}
ADDED = {'REF_LEGMAG_L_COVER', 'REF_LEGMAG_L_PLATE', 'REF_LEGMAG_R_COVER', 'REF_LEGMAG_R_PLATE'}
NEW_PARAMS = {'v5_rim_ref_Z', 'v5_legmag_skin', 'v5_legmag_skin_min', 'v5_keycap_bottom_above_seat', 'v5_keycap_bottom_rest_Z',
              'v5_skirt_cover_H', 'v5_cover_top_Z', 'v5_cover_top_above_rim',
              'v5_key_margin', 'v5_legmag_plate_clr', 'v5_legpad_L', 'v5_lip_relief_clr',
              'v5_legmag_L_X', 'v5_legmag_L_Y', 'v5_legmag_R_X', 'v5_legmag_R_Y'}
CHANGED_PARAMS = {'TBD_cover_T', 'TBD_upper_plate_T'}
MOUNT_SCREW_INTERFACE = ('REF_SO2_M3_LOWER', 'MOUNT_L_PAIR_V3')
CACHE = ROOT / 'guide/.cache/v5'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def cli_results(script, model, name):
    path = CACHE / f'{name}.json'
    out = CACHE / f'{name}_out.json'
    path.write_text(json.dumps(script), encoding='utf-8')
    subprocess.run([CLI, 'run', str(path), '--in', str(model), '--results', '--json-out', str(out)],
                   check=True, capture_output=True)
    return json.loads(out.read_text(encoding='utf-8'))


def clearance_candidates(bodies, moving, against, clearance, skip_pairs=()):
    """Build exact-check commands only for body pairs whose AABBs can be this close."""
    def bbox_gap(a, b):
        aa, bb = bodies[a]['bbox'], bodies[b]['bbox']
        return [max(aa['min'][k] - bb['max'][k], bb['min'][k] - aa['max'][k], 0.0)
                for k in range(3)]

    groups, skipped = {}, []
    skip_pairs = {frozenset(pair) for pair in skip_pairs}
    total = 0
    for i, a in enumerate(moving):
        candidates = []
        targets = against if against is not None else moving[i + 1:]
        for b in targets:
            if a == b:
                continue
            total += 1
            if frozenset((a, b)) in skip_pairs:
                skipped.append((a, b))
                continue
            if max(bbox_gap(a, b)) <= clearance + 1e-9:
                candidates.append(b)
        if candidates:
            groups[a] = candidates
    commands = [dict(command='inspect.clearance', params=dict(
        bodies=[a], against=targets, clearance=clearance)) for a, targets in groups.items()]
    return commands, total, sum(map(len, groups.values())), skipped


def merge_clearance_results(results):
    overlaps = [item for result in results for item in result['overlaps']]
    unchecked = [item for result in results for item in result['unchecked']]
    contacts = sorted({f"{item['a']} | {item['b']}"
                       for result in results for item in result['near']
                       if item['distance_mm'] < 1e-6})
    return dict(overlaps=overlaps, unchecked=unchecked, contacts=contacts,
                pairs_checked=sum(r['pairs_checked'] for r in results),
                pairs_reused=sum(r['pairs_reused'] for r in results),
                pairs_pruned=sum(r['pairs_pruned'] for r in results))


def mount_screw_section_commands():
    commands, inspect_offsets = [], []
    for index, z in enumerate((0.5, 1.5, 2.5, 3.5, 4.5), 1):
        name = f'SK_MOUNT_L_CLEARANCE_Z{index}'
        commands.extend((
            dict(command='sketch.create', params=dict(name=name, plane='XY', offset=str(z))),
            dict(command='sketch.fit_curves_to_section', params=dict(body='MOUNT_L_PAIR_V3')),
            dict(command='sketch.inspect', params=dict(sketch=name)),
            dict(command='sketch.finish', params={}),
        ))
        inspect_offsets.append(len(commands) - 2)
    return commands, inspect_offsets


def section_loops(sketch):
    edges = [(curve['start_at'], curve['end_at']) for curve in sketch['curves'] if curve['type'] == 'line']
    unused = set(range(len(edges)))
    loops = []
    while unused:
        index = unused.pop()
        start = edges[index][0]
        points = [start, edges[index][1]]
        while math.dist(points[-1], start) > 1e-4:
            found = None
            for candidate in unused:
                a, b = edges[candidate]
                if math.dist(a, points[-1]) < 1e-4:
                    found = candidate, b
                    break
                if math.dist(b, points[-1]) < 1e-4:
                    found = candidate, a
                    break
            if found is None:
                break
            unused.remove(found[0])
            points.append(found[1])
        if len(points) > 3 and math.dist(points[-1], start) < 1e-4:
            loops.append(points[:-1])
    return loops


def point_segment_distance(point, a, b):
    dx, dy = b[0] - a[0], b[1] - a[1]
    t = max(0.0, min(1.0, ((point[0] - a[0]) * dx + (point[1] - a[1]) * dy) / (dx * dx + dy * dy)))
    return math.hypot(point[0] - a[0] - t * dx, point[1] - a[1] - t * dy)


def verify_mount_screw_interface(section_sketches):
    center, shaft_radius = (6.494, 87.945), 1.5
    features = {f['name']: f for f in document(V5)['features']}
    shaft = features['REF_SO2_M3_LOWER']
    head = features['REF_SO2_M3_LOWER_HEAD_JOIN']
    assert math.dist(shaft['base'], [*center, 0.0]) < 1e-6 and shaft['height'] == '5' and shaft['radius'] == '(3 mm) / 2'
    assert shaft['axis'] == [0.0, 0.0, 1.0]
    assert math.dist(head['base'], [*center, -1.65]) < 1e-6 and head['height'] == '1.65' and head['radius'] == '2.85'
    assert len(section_sketches) == 5

    shaft_hole_radii = []
    for section in section_sketches[:2]:
        circles = [curve for curve in section['curves'] if curve['type'] == 'circle'
                   and math.dist(curve['center_at'], center) < 1e-3]
        assert len(circles) == 1 and abs(circles[0]['radius'] - 1.7) < 0.002, circles
        shaft_hole_radii.append(circles[0]['radius'])

    counterbore = section_loops(section_sketches[2])
    local = [loop for loop in counterbore if inside(center, loop)
             and max(math.dist(center, p) for p in loop) < 4.0]
    assert len(local) == 1, [(len(loop), loop[:4]) for loop in counterbore]
    counterbore_min_radius = min(point_segment_distance(center, a, b)
                                  for loop in local for a, b in zip(loop, loop[1:] + loop[:1]))
    assert counterbore_min_radius >= shaft_radius + 0.5, counterbore_min_radius

    upper_clearances = []
    for section in section_sketches[3:]:
        loops = section_loops(section)
        assert all(not inside(center, loop) for loop in loops), 'screw axis unexpectedly lies in mount section'
        distances = [point_segment_distance(center, a, b) for loop in loops
                     for a, b in zip(loop, loop[1:] + loop[:1])]
        clearance = min(distances) - shaft_radius
        assert clearance >= 0.5, clearance
        upper_clearances.append(clearance)
    return dict(pair=list(MOUNT_SCREW_INTERFACE), center_mm=list(center), shaft_radius_mm=shaft_radius,
                shaft_z_mm=[0.0, 5.0], head_radius_mm=2.85, head_top_z_mm=0.0,
                shaft_hole_radii_mm=shaft_hole_radii,
                shaft_radial_clearances_mm=[r - shaft_radius for r in shaft_hole_radii],
                counterbore_min_radius_mm=counterbore_min_radius,
                counterbore_radial_clearance_mm=counterbore_min_radius - shaft_radius,
                upper_section_z_mm=[3.5, 4.5], upper_radial_clearances_mm=upper_clearances,
                check='SolidCraft XY sections + source fastener cylinders; exact overlap boolean returns no result')


# ---------------------------------------------------------------- planar geometry (leg magnet walls)
def dxf_polygons(path):
    lines = path.read_text().splitlines()
    segs, i = [], 0
    while i < len(lines) - 1:
        if lines[i].strip() == '0' and lines[i + 1].strip() == 'LINE':
            d, j = {}, i + 2
            while j < len(lines) - 1 and lines[j].strip() != '0':
                if lines[j].strip() in ('10', '20', '11', '21'):
                    d[lines[j].strip()] = float(lines[j + 1])
                j += 2
            segs.append(((d['10'], d['20']), (d['11'], d['21'])))
            i = j
        else:
            i += 1
    polys = []
    while segs:
        a, b = segs.pop(0)
        poly = [a, b]
        while True:
            for k, (c, e) in enumerate(segs):
                if math.dist(c, poly[-1]) < 1e-6:
                    poly.append(e); segs.pop(k); break
                if math.dist(e, poly[-1]) < 1e-6:
                    poly.append(c); segs.pop(k); break
            else:
                break
        polys.append(poly[:-1])
    return polys


def inside(p, poly):
    x, y = p
    c = False
    for i in range(len(poly)):
        (x1, y1), (x2, y2) = poly[i], poly[(i + 1) % len(poly)]
        if (y1 > y) != (y2 > y) and x < x1 + (y - y1) * (x2 - x1) / (y2 - y1):
            c = not c
    return c


def edge_distance(p, poly):
    best = 1e9
    for i in range(len(poly)):
        (ax, ay), (bx, by) = poly[i], poly[(i + 1) % len(poly)]
        dx, dy = bx - ax, by - ay
        t = max(0, min(1, ((p[0] - ax) * dx + (p[1] - ay) * dy) / (dx * dx + dy * dy)))
        best = min(best, math.hypot(p[0] - ax - t * dx, p[1] - ay - t * dy))
    return best


def leg_magnet_walls(params):
    derived = ROOT / 'inspection/derived'
    windows = dxf_polygons(derived / 'REF_r2_cover_windows_P4_gh60.dxf')
    keys = load_keys(.693, .667)
    m = params['v5_key_margin']
    grown = [rect(k['x'], k['y'], 18.05 + (k['w_u'] - 1) * 19.05 + 2 * m, 18.05 + 2 * m, k['rot']) for k in keys]
    openings = dxf_polygons(derived / 'REF_r2_keys_sq16p5_gh60.dxf')
    edge_y = -params['TBD_pcb0_dy'] + params['TBD_plate_gap']
    r_cover = (params['TBD_magnet_D'] + 2 * params['TBD_magnet_clr']) / 2
    r_plate = (params['TBD_magnet_D'] + 2 * params['v5_legmag_plate_clr']) / 2
    out = {}
    for s in 'LR':
        p = (params[f'v5_legmag_{s}_X'], params[f'v5_legmag_{s}_Y'])
        cut = windows + grown
        assert not any(inside(p, q) for q in cut), s
        out[s] = dict(center=p,
                      cover_pocket_D=2 * r_cover, plate_pocket_D=2 * r_plate,
                      cover_wall_to_window_mm=round(min(edge_distance(p, q) for q in cut) - r_cover, 3),
                      cover_wall_to_outer_edge_mm=round(p[1] - edge_y - r_cover, 3),
                      cover_top_skin_mm=round(params['v5_legmag_skin'], 3),
                      plate_wall_to_switch_opening_mm=round(min(edge_distance(p, q) for q in openings) - r_plate, 3),
                      plate_wall_to_front_edge_mm=round(p[1] - edge_y - r_plate, 3),
                      plate_wall_to_pad_end_mm=round(params['v5_legpad_L'] / 2 - r_plate, 3),
                      plate_floor_mm=round(params['v4_plate_top_Z'] - params['TBD_magnet_T'] - params['TBD_magnet_clr']
                                           - (params['TBD_frame_T'] + params['TBD_standoff_H']), 3),
                      magnet_gap_mm=round(2 * params['TBD_magnet_clr'], 3))
        assert min(v for k, v in out[s].items() if k.endswith('_mm') and k != 'magnet_gap_mm') >= 1.0, out[s]
    return out


def cover_levels(params, bodies, flat_bodies):
    """Check the single top plane and the unchanged XY shape against the flat baseline."""
    top = params['v5_cover_top_Z']
    levels = top_levels(V5)
    flat_levels = top_levels(FLAT)
    for name in COVERS:
        area = flat_levels[name][18.0]
        assert set(flat_levels[name]) == {18.0}, flat_levels[name]
        assert levels[name] == {round(top, 4): area}, (name, levels[name])
        expected = flat_bodies[name]['volume_mm3'] + area * (top - 18.0)
        actual = bodies[name]['volume_mm3']
        assert abs(actual - expected) / expected < 0.001, (name, actual, expected)
    assert params['v5_legmag_skin'] >= params['v5_legmag_skin_min']
    return levels


def support_contact_plan(params):
    """Build bearing probes so contacts and assembly clearances share one CLI model load."""
    z = params['v4_plate_top_Z'] - params['TBD_plate_T']
    mounts = sorted(PLATE_SUPPORT_MOUNTS)
    plates = sorted(set(PLATE_SUPPORT_MOUNTS.values()))
    commands = [dict(command='inspect.clearance', params=dict(
        bodies=mounts, against=plates, clearance=0.01, min_volume=0.000001))]
    probes = {}
    cadcraft = mount_cadcraft_profiles()
    support_number = 0
    for suffix, shapes_for_mount in cadcraft['supports'].items():
        mount = cadcraft['mount_names'][suffix]
        plate = PLATE_SUPPORT_MOUNTS[mount]
        for index, support in enumerate(shapes_for_mount, 1):
            if suffix == 'R' and index == 2:
                continue  # SolidCraft reports this face as part of the existing rail.
            if suffix == 'R' and index == 2:
                support = support.difference(cadcraft['switch46'].buffer(0.15))
            if suffix == 'L' and index == 2:
                support = support.difference(cadcraft['switch11'].buffer(0.15, quad_segs=1, join_style='mitre'))
            if suffix == 'FRONT' and index == 1:
                support = support.difference(cadcraft['nut_clearance'])
            support_number += 1
            feature_name = f'MOUNT_CADCRAFT_{suffix}_SUPPORT_{index}_V6'
            probe_name = f'SEAT_PROBE_{support_number}'
            commands.append(dict(command='solid.extrude', params=dict(
                name=probe_name, body_name=probe_name,
                sketch=f'SK_{feature_name}', profiles='all',
                start_offset=z - SEAT_ROOT_Z - 0.05, distance=0.1, operation='new')))
            probes[probe_name] = (mount, plate, support.area, feature_name)
    commands.append(dict(command='inspect.clearance', params=dict(
        bodies=list(probes), against=plates, clearance=0.01, min_volume=0.000001)))
    return dict(commands=commands, probes=probes, mounts=mounts, plates=plates, z=z)


def support_contacts(params, shapes, plan, results):
    """Confirm the CADCraft bearing faces, without solid overlap."""
    probes, mounts, plates, z = plan['probes'], plan['mounts'], plan['plates'], plan['z']
    contact, bearing = results[0], results[-1]
    assert not contact['overlaps'] and not contact['unchecked'], contact
    assert not bearing['unchecked'], bearing
    contacts = {frozenset((p['a'], p['b'])) for p in contact['near'] if p['distance_mm'] < 1e-6}
    volumes = {frozenset((p['a'], p['b'])): p['volume_mm3'] for p in bearing['overlaps']}
    # Identical curved side faces make the probe/mount Boolean ambiguous.
    # Read the upward bearing faces directly, and use the probes on the plate side.
    for mount in mounts:
        expected = sorted(area for owner, _, area, _ in probes.values() if owner == mount)
        faces = sorted(area for solid in shapes[mount] for height, area in horizontal_faces(solid)
                       if abs(height - z) < 5e-4 and area > 1e-6)
        assert len(faces) == len(expected), (mount, faces, expected)
        area_tol = 0.02 if mount == 'MOUNT_H03_SO6_MIN_V2' else 0.001
        assert all(abs(a - b) < area_tol for a, b in zip(faces, expected)), (mount, faces, expected)
    seats = []
    for probe, (mount, plate, area, feature_name) in probes.items():
        assert frozenset((mount, plate)) in contacts, (mount, plate, contact)
        volume = volumes[frozenset((probe, plate))]
        contact_area = volume / 0.05
        assert contact_area >= area * 0.5, (probe, plate, area, contact_area)
        seats.append(dict(mount=mount, target=plate, feature=feature_name, top_Z=z,
                          profile_area_mm2=round(area, 3), contact_area_mm2=round(contact_area, 3)))
    return seats


# ---------------------------------------------------------------- order-2 print set (3rd pass, tools/export_print_v5.py)
PRINT_V5 = ROOT / 'model/print_v5/order2'
PRINT_SET_FILES = {'46es_v5_plate_L', '46es_v5_plate_R', '46es_v5_spine', '46es_v5_ctrl_bracket', '46es_v5_ctrl_gate',
                   '46es_v5_cover_L', '46es_v5_cover_T', '46es_v5_cover_R'}
SAME_AS_V4 = {'46es_v5_spine': 'PLATE_SPINE_V1'}
MJF_MAX = (370.0, 276.0)


def check_print_set(bodies, v4_bodies):
    """print_v5/order2 STL/STEP files: hashes as recorded, one component, no open edges, volume = CAD, MJF 1.0 / resin 0.8
    walls, box on the bed and inside the MJF build volume; the spine keeps the v4 volume."""
    parts = json.loads((ROOT / 'inspection/data/seam-v5-print-set.json').read_text(encoding='utf-8'))
    thin = {t['file']: t for t in json.loads((ROOT / 'inspection/data/seam-v5-mjf-thin-wall.json').read_text(encoding='utf-8'))['parts']}
    assert {p['file'] for p in parts} == PRINT_SET_FILES == set(thin), (set(thin), {p['file'] for p in parts})
    out = []
    for p in parts:
        stl = PRINT_V5 / (p['file'] + '.stl')
        step = stl.with_suffix('.step')
        assert sha(stl) == p['stl_sha256'] and sha(step) == p['step_sha256'], p['file']
        t = thin[p['file']]
        assert t['stl_sha256'] == p['stl_sha256'], ('thin-wall scan is of another STL', p['file'])
        limit = 0.8 if p['material'].startswith('8001') else 1.0
        assert t['wall_min_mm'] is None or t['wall_min_mm'] >= limit - 1e-3, (p['file'], t['wall_min_mm'])
        assert abs(p['cad_volume_mm3'] - bodies[p['body']]['volume_mm3']) < 1e-3, p['file']
        if p['file'] in SAME_AS_V4:
            assert abs(p['cad_volume_mm3'] - v4_bodies[SAME_AS_V4[p['file']]]['volume_mm3']) < 1e-3, p['file']
        m = check(str(stl))
        assert len(m['components']) == 1 and m['bad_edge_count'] == 0, p['file']
        c = m['components'][0]
        rel = abs(c['signed_volume'] - p['cad_volume_mm3']) / p['cad_volume_mm3']
        assert rel < 0.001, (p['file'], rel)
        size = [c['bbox']['max'][k] - c['bbox']['min'][k] for k in range(3)]
        assert sorted(size[:2], reverse=True)[0] <= MJF_MAX[0] and sorted(size[:2])[0] <= MJF_MAX[1] and abs(c['bbox']['min'][2]) < 1e-4, p['file']
        out.append(dict(file=p['file'], material=p['material'], flip=p['print_flip_about_X'], volume_cm3=round(p['cad_volume_mm3'] / 1000, 3),
                        size=[round(s, 2) for s in size], wall_min_mm=t['wall_min_mm'], rel=round(rel, 6)))
    return out


def main():
    assert sha(V4) == V4_SHA, 'v4 changed'
    assert sha(FLAT) == FLAT_SHA, 'the flat Z 18 snapshot changed'
    v4, v5 = document(V4), document(V5)
    for prefix in ['SK22', 'SK24', 'SK25', 'SK34']:
        a = next(f for f in v4['features'] if f['name'].startswith(prefix))
        b = next(f for f in v5['features'] if f['name'].startswith(prefix))
        assert a == b, prefix
    p4 = {p['name']: p['expr'] for p in v4['params'] if not p['model']}
    p5 = {p['name']: p['expr'] for p in v5['params'] if not p['model']}
    assert set(p5) - set(p4) == NEW_PARAMS and not set(p4) - set(p5), (set(p5) - set(p4)) ^ NEW_PARAMS
    assert {n for n in p4 if p4[n] != p5[n]} == CHANGED_PARAMS
    rows = {r['name']: r for r in csv.DictReader((ROOT / 'model/parameters_seam_v5.csv').open(encoding='utf-8-sig'))}
    assert {n: r['expression'] for n, r in rows.items()} == p5, 'CSV differs from the model'
    assert all(f['name'] != 'COVER_DROP_V5' for f in v5['features'])

    old, new = live_shapes(V4), live_shapes(V5)
    assert set(new) - set(old) == ADDED and not set(old) - set(new)
    same = [n for n in old if n not in CHANGED | DERIVED]
    assert all(old[n] == new[n] for n in same), 'an untouched body changed'
    assert all(old[n] != new[n] for n in CHANGED)
    for n in CHANGED | ADDED:
        assert len(new[n]) == 1 and len(new[n][0]['shells']) == 1, n

    ev_path = CACHE / 'eval_v5_export.json'
    if not ev_path.exists() or ev_path.stat().st_mtime < V5.stat().st_mtime:
        subprocess.run([CLI, 'eval', '--in', str(V5), '--json-out', str(ev_path)], check=True, capture_output=True)
    ev = json.loads(ev_path.read_text(encoding='utf-8'))
    errors = [t['name'] for t in ev['timeline'] if t.get('error')]
    warnings = [t['name'] for t in ev['timeline'] if t.get('warning')]
    dof = [s['name'] for s in ev['sketches'] if s.get('dof') != 0]
    expected_warning = lambda name: name == 'HOUSING_POSTS_CAND' or name.startswith('MOUNT_CADCRAFT_')
    assert not errors and not dof and all(expected_warning(name) for name in warnings), (errors, dof, warnings)
    bodies = {b['name']: b for b in ev['bodies']}
    params = {p['name']: p['value'] for p in ev['params'] if p.get('value') is not None}
    covers = [n for n in bodies if n.startswith('COVER_')]
    assert sorted(covers) == sorted(COVERS)
    cover_lo = params['v4_plate_top_Z'] - params['TBD_cover_boss_H']
    cover_hi = params['v5_cover_top_Z']
    for n in covers:
        lo, hi = bodies[n]['bbox']['min'][2], bodies[n]['bbox']['max'][2]
        assert abs(hi - cover_hi) < 1e-6 and abs(lo - cover_lo) < 1e-6, n
    assert abs(params['TBD_cover_T'] - 6) < 1e-9 and abs(params['v5_cover_top_Z'] - 19) < 1e-9
    assert abs(params['v5_legmag_skin'] - 3.9) < 1e-9
    assert abs(params['v5_keycap_bottom_rest_Z'] - 17.3) < 1e-9
    walls = leg_magnet_walls(params)
    v4_eval_path = CACHE / f'eval-baseline-{V4_SHA[:16]}.json'
    if not v4_eval_path.exists():
        subprocess.run([CLI, 'eval', '--in', str(V4), '--json-out', str(v4_eval_path)], check=True, capture_output=True)
    v4_eval = json.loads(v4_eval_path.read_text(encoding='utf-8'))
    v4_bodies = {b['name']: b for b in v4_eval['bodies']}
    for n in DERIVED:
        assert abs(bodies[n]['volume_mm3'] - v4_bodies[n]['volume_mm3']) < 1e-3, n
        assert all(abs(bodies[n]['bbox'][k][i] - v4_bodies[n]['bbox'][k][i]) < 1e-6 for k in ('min', 'max') for i in range(3)), n
    flat_eval = CACHE / 'eval_v5_flat_Z18.json'
    if not flat_eval.exists():
        subprocess.run([CLI, 'eval', '--in', str(FLAT), '--json-out', str(flat_eval)], check=True, capture_output=True)
    flat_bodies = {b['name']: b for b in json.loads(flat_eval.read_text(encoding='utf-8'))['bodies']}
    flat_shapes = live_shapes(FLAT)
    for n in ('PLATE_L_SPLIT_V1', 'PLATE_R_SPLIT_V1'):   # the 2nd pass touches the covers only
        assert abs(bodies[n]['volume_mm3'] - flat_bodies[n]['volume_mm3']) < 1e-6, n
        assert flat_shapes[n] == new[n], n
    levels = cover_levels(params, bodies, flat_bodies)
    support_plan = support_contact_plan(params)

    # clearance of the changed/added bodies: against the 106 untouched bodies and among themselves
    moving = sorted(CHANGED | ADDED)
    others = sorted(n for n in bodies if n not in CHANGED | ADDED)
    clearance, clearance_batches = {}, []
    for key, group, against in (('changed_vs_unchanged', moving, others), ('among_changed', moving, None)):
        skip = [MOUNT_SCREW_INTERFACE] if key == 'changed_vs_unchanged' else []
        commands, total_pairs, candidate_pairs, skipped = clearance_candidates(bodies, group, against, 0.01, skip)
        clearance_batches.append((key, commands, total_pairs, candidate_pairs, skipped))
        if key == 'changed_vs_unchanged':
            assert len(skipped) == 1 and frozenset(skipped[0]) == frozenset(MOUNT_SCREW_INTERFACE), skipped
        clearance[key] = dict(total_pairs=total_pairs, candidate_pairs=candidate_pairs,
                              pairs_pruned_by_bbox=total_pairs-candidate_pairs,
                              intentionally_checked_by_sections=skipped)
    section_commands, section_offsets = mount_screw_section_commands()
    clearance_commands = [command for _, commands, _, _, _ in clearance_batches for command in commands]
    clearance_start = len(support_plan['commands'])
    section_start = clearance_start + len(clearance_commands)
    all_results = cli_results(support_plan['commands'] + clearance_commands + section_commands,
                              V5, 'seam_v5_contacts_and_clearance')
    seats = support_contacts(params, new, support_plan, all_results[:clearance_start])
    result_offset = clearance_start
    for key, commands, total_pairs, candidate_pairs, skipped in clearance_batches:
        command_count = len(commands)
        merged = merge_clearance_results(all_results[result_offset:result_offset+command_count])
        result_offset += command_count
        assert merged['overlaps'] == [] and merged['unchecked'] == [], (key, merged['overlaps'], merged['unchecked'])
        clearance[key].update(merged)
    sections = [all_results[section_start+offset] for offset in section_offsets]
    clearance['mount_screw_interface'] = verify_mount_screw_interface(sections)
    (ROOT / 'inspection/data/seam-v5-clearance.json').write_text(json.dumps(clearance, indent=1), encoding='utf-8')

    print_set = check_print_set(bodies, v4_bodies)

    exports = json.loads((ROOT / 'inspection/data/seam-v5-exports.json').read_text(encoding='utf-8'))
    assert exports['model_sha'] == sha(V5), 'exports are of another model'
    thin = {Path(t['file']).stem if 'file' in t else t: t for t in
            json.loads((ROOT / 'inspection/data/seam-v5-thin-wall.json').read_text(encoding='utf-8'))['parts']}
    parts = []
    for p in exports['parts']:
        stl = ROOT / 'model/review_v5' / (p['file'] + '.stl')
        assert sha(stl) == p['stl_sha256'] and sha(stl.with_suffix('.step')) == p['step_sha256'], p['file']
        mesh = check(str(stl))
        assert len(mesh['components']) == 1 and mesh['bad_edge_count'] == 0, p['file']
        rel = abs(mesh['components'][0]['signed_volume'] - p['cad_volume_mm3']) / p['cad_volume_mm3']
        assert rel < 0.0001, (p['file'], rel)
        t = thin[p['file']]
        assert t['stl_sha256'] == p['stl_sha256']
        assert t['wall_min_mm'] is None or t['wall_min_mm'] >= p['wall_limit_mm'] - 1e-3, (p['file'], t['wall_min_mm'])
        if p['body'] in COVERS:   # resin covers: every wall >= 1.0 (material rule), wedge tips excluded by wall_min_mm
            assert t['wall_min_mm'] is None or t['wall_min_mm'] >= 1.0 - 1e-3, (p['file'], t['wall_min_mm'])
        parts.append(dict(file=p['file'], material=p['material'], volume_cm3=round(p['cad_volume_mm3'] / 1000, 2),
                          v4_volume_cm3=None, flat_Z18_volume_cm3=round(flat_bodies[p['body']]['volume_mm3'] / 1000, 2),
                          wall_min_mm=t['wall_min_mm'], min_mm=t.get('min_mm'), stl_volume_rel_err=round(rel, 6)))
    v4_vol = {b['name']: b['volume_mm3'] for b in v4_eval['bodies']}
    for part, p in zip(parts, exports['parts']):
        part['v4_volume_cm3'] = round(v4_vol[p['body']] / 1000, 2)
    clearance_summary = {k: dict(overlaps=len(clearance[k]['overlaps']), contacts=len(clearance[k]['contacts']),
                                 unchecked=len(clearance[k]['unchecked']))
                         for k in ('changed_vs_unchanged', 'among_changed')}
    result = dict(ok=True, v4_sha=V4_SHA, v5_sha=sha(V5), flat_Z18_sha=FLAT_SHA, print_set=print_set, bodies=len(new), untouched_bodies_exact=len(same),
                  derived_same_volume_box=sorted(DERIVED), plates_same_as_flat_Z18=True,
                  changed=sorted(CHANGED), added=sorted(ADDED), timeline=len(ev['timeline']), sketches=len(ev['sketches']),
                  params=len(p5), new_params=sorted(NEW_PARAMS), changed_params={n: p5[n] for n in CHANGED_PARAMS},
                  cover_Z=[cover_lo, cover_hi], cover_T=params['TBD_cover_T'], cover_levels=levels,
                  plate_supports=seats,
                  leg_magnets=walls,
                  clearance=clearance_summary, mount_screw_interface=clearance['mount_screw_interface'],
                  plate_files_unchanged=exports.get('plate_files_unchanged_since_previous_export'), parts=parts)
    (ROOT / 'inspection/data/seam-v5-verification.json').write_text(json.dumps(result, indent=1, ensure_ascii=False),
                                                                    encoding='utf-8')
    print(json.dumps(result, indent=1, ensure_ascii=False))


if __name__ == '__main__':
    main()
