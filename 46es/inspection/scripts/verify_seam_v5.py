"""Audit the flat v5 cover, drawing-built mounts, plate supports, the v5 baseline and current print exports.

Run with python -B 46es/inspection/scripts/verify_seam_v5.py [--accept].
Writes inspection/data/seam-v5-verification.json and seam-v5-clearance.json.

inspection/data/seam-v5-baseline.json is the expected state of the production and trial models: every body's shape
fingerprint (cad_model.shape_digest) with its volume and box, and every design parameter's expression (plan 4-2/4-3,
replacing the v4 and flat Z 18 snapshot models). A run fails when anything differs from it. After an intended design
change, --accept prints the differences, writes the new baseline and verifies; the printed differences go into the
commit message (AGENTS.md §5).
"""
import argparse, csv, json, math, subprocess, sys
from pathlib import Path

from shapely.geometry import LineString, Point
from shapely.ops import unary_union
from cad_model import ROOT, live_shapes, document, shape_digest
from check_stl import check

sys.path.insert(0, str(ROOT / 'tools'))
from make_key_dxf import load_keys, rect  # noqa: E402
from build_seam_v5 import (COVERS, PLATE_SUPPORT_MOUNTS, SEAT_ROOT_Z, REAR_RESTS, REAR_REST_BODY, REAR_REST_TRIALS,  # noqa: E402
                           seam_coupon_bodies,
                           horizontal_faces, top_levels, cover_windows)
import ctrl_v5  # noqa: E402
from common import CLI, sha, fingerprints, write_json  # noqa: E402
from cad_eval_cache import evaluation  # noqa: E402
from mounts_v5 import SO_ANCHORS, LAND_AF, MIN_WALL, profiles as mount_profiles, expected_sections, expected_volume, layers  # noqa: E402
from mesh_section import read_stl, align, compare, section  # noqa: E402
from parts_v5 import ORDERS, WALL_SCAN, by_file, mount_part  # noqa: E402

V5 = ROOT / 'model/46es_mount_seam_v5.sc'
TRIALS = ROOT / 'model/ctrl_trials_v5.sc'
BASELINE = ROOT / 'inspection/data/seam-v5-baseline.json'
# Recorded with their fingerprints (common.fingerprint) so check_repository.py and pipeline.py --status can tell
# that this verifier or what it read changed after the run (plan 2-3).
VERIFY_INPUTS = ('inspection/scripts/verify_seam_v5.py', 'tools/parts_v5.py', 'model/46es_mount_seam_v5.sc', 'model/ctrl_trials_v5.sc',
                 'model/parameters_seam_v5.csv', 'inspection/data/seam-v5-baseline.json', 'inspection/data/seam-v5-print-set.json',
                 'inspection/data/seam-v5-mjf-thin-wall.json', 'inspection/data/seam-v5-trial-print-set.json')
# Bodies the v5 generator builds or cuts (drawing-built mounts, snap bracket and its plate screws, leg magnets, rear
# rest blocks, cover windows): their clearance is checked against every other body and among themselves.
GENERATED = set(PLATE_SUPPORT_MOUNTS) | {'PLATE_L_SPLIT_V1', 'PLATE_R_SPLIT_V1', 'COVER_L_DRAFT_TBD', 'COVER_T_DRAFT_TBD',
                                         'COVER_R_DRAFT_TBD', 'CTRL_BRACKET_SPLIT_V1', 'REF_M2_PLATE_1', 'REF_M2_PLATE_2',
                                         'REF_M2_PLATE_1_NUT', 'REF_M2_PLATE_2_NUT', 'REF_LEGMAG_L_COVER',
                                         'REF_LEGMAG_L_PLATE', 'REF_LEGMAG_R_COVER', 'REF_LEGMAG_R_PLATE',
                                         *(REAR_REST_BODY.format(i) for i in REAR_RESTS),
                                         'REF_M2_SEAM_FRONT', 'REF_M2_SEAM_FRONT_NUT'}
MOUNT_SCREW_INTERFACE = ('REF_SO2_M3_LOWER', 'MOUNT_L_PAIR_V3')
CACHE = ROOT / '.cache/v5'


# ---------------------------------------------------------------- baseline (expected state, --accept)
def snapshot(evaluated, model):
    """{body: shape fingerprint, volume, box} of one model."""
    shapes = live_shapes(model)
    bodies = {b['name']: b for b in evaluated['bodies']}
    assert set(shapes) == set(bodies), set(shapes) ^ set(bodies)
    return {n: dict(shape_sha256=shape_digest(shapes[n]), volume_mm3=round(bodies[n]['volume_mm3'], 3),
                    bbox=[[round(v, 4) for v in bodies[n]['bbox'][k]] for k in ('min', 'max')])
            for n in sorted(shapes)}


def baseline_now(ev, trials_ev, params):
    """params: the design parameters' expressions; values: what they evaluate to, so a value that changes through
    another parameter (cover thickness, keycap rest Z) shows in the differences too."""
    unit = lambda p: math.degrees(p['value']) if p['unit'] == 'deg' else p['value']     # as the CSV shows them
    values = {p['name']: round(unit(p), 6) for p in ev['params'] if p['name'] in params and p.get('value') is not None}
    return dict(about='Expected v5 state: verify_seam_v5.py fails on any difference; --accept rewrites this file and '
                      'prints the differences for the commit message. check_repository.py compares the fingerprints.',
                bodies=snapshot(ev, V5), trials=snapshot(trials_ev, TRIALS), params=dict(sorted(params.items())),
                values=dict(sorted(values.items())))


def baseline_diff(old, new):
    """Readable differences between two baselines."""
    out = []
    for section in ('bodies', 'trials'):
        a, b = old.get(section, {}), new[section]
        out += [f'{section}: added {n} ({b[n]["volume_mm3"]} mm3)' for n in sorted(set(b) - set(a))]
        out += [f'{section}: removed {n} ({a[n]["volume_mm3"]} mm3)' for n in sorted(set(a) - set(b))]
        for n in sorted(set(a) & set(b)):
            if a[n]['shape_sha256'] != b[n]['shape_sha256']:
                dv = round(b[n]['volume_mm3'] - a[n]['volume_mm3'], 3)
                box = '' if a[n]['bbox'] == b[n]['bbox'] else f', box {a[n]["bbox"]} -> {b[n]["bbox"]}'
                out.append(f'{section}: changed {n}: volume {a[n]["volume_mm3"]} -> {b[n]["volume_mm3"]} mm3 ({dv:+}){box}')
    for section, label in (('params', 'param'), ('values', 'value')):
        a, b = old.get(section, {}), new[section]
        out += [f'{label} added {n} = {b[n]}' for n in sorted(set(b) - set(a))]
        out += [f'{label} removed {n} (was {a[n]})' for n in sorted(set(a) - set(b))]
        out += [f'{label} {n}: {a[n]} -> {b[n]}' for n in sorted(set(a) & set(b)) if a[n] != b[n]]
    return out


def check_baseline(ev, trials_ev, params, accept):
    now = baseline_now(ev, trials_ev, params)
    old = json.loads(BASELINE.read_text(encoding='utf-8')) if BASELINE.is_file() else {}
    diff = baseline_diff(old, now)
    if accept:
        print('\n'.join(['baseline differences (put them in the commit message):'] + (diff or ['none'])))
        write_json(BASELINE, now)
    else:
        assert not diff, ('the model differs from inspection/data/seam-v5-baseline.json; after an intended change run '
                          'verify_seam_v5.py --accept and record the differences in the commit message:\n' + '\n'.join(diff))
    return now


def cli_results(script, model, name):
    path = CACHE / f'{name}.json'
    out = CACHE / f'{name}_out.json'
    write_json(path, script, indent=None)
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
        cut = windows + grown + cover_windows()      # r2 windows, per-key margin, silhouette window (2026-11-10)
        assert not any(inside(p, q) for q in cut), s
        out[s] = dict(center=p,
                      cover_pocket_D=2 * r_cover, plate_pocket_D=2 * r_plate,
                      cover_wall_to_window_mm=round(min(edge_distance(p, q) for q in cut) - r_cover, 3),
                      cover_wall_to_outer_edge_mm=round(p[1] - edge_y - r_cover, 3),
                      cover_top_skin_mm=round(params['v5_legmag_skin'], 3),
                      plate_wall_to_switch_opening_mm=round(min(edge_distance(p, q) for q in openings) - r_plate, 3),
                      plate_wall_to_front_edge_mm=round(p[1] - edge_y - r_plate, 3),
                      plate_wall_to_pad_end_mm=round(params['v5_legpad_L'] / 2 - r_plate, 3),
                      plate_floor_mm=round(params['plate_top_Z'] - params['TBD_magnet_T'] - params['TBD_magnet_clr']
                                           - (params['TBD_frame_T'] + params['TBD_standoff_H']), 3),
                      magnet_gap_mm=round(2 * params['TBD_magnet_clr'], 3))
        assert min(v for k, v in out[s].items() if k.endswith('_mm') and k != 'magnet_gap_mm') >= 1.0, out[s]
    return out


def cover_levels(params, bodies):
    """Each cover has one flat top plane at v5_cover_top_Z. Keycap clearance is checked by verify_assembly_reference_v5."""
    top = params['v5_cover_top_Z']
    levels = top_levels(V5)
    out = {}
    for name in COVERS:
        assert set(levels[name]) == {round(top, 4)}, (name, levels[name])
        out[name] = dict(top_Z=top, top_area_mm2=levels[name][round(top, 4)],
                         volume_mm3=round(bodies[name]['volume_mm3'], 3))
    assert params['v5_legmag_skin'] >= params['v5_legmag_skin_min']
    return out


def verify_mounts(bodies):
    """Each printed mount equals the drawing: sections of the order-1 STL at four heights, the AF 8.5 keep-clear
    land around every hex pocket, the hex pocket wall, and the evaluated volume against the layered profile."""
    out = {}
    for suffix, profile in mount_profiles().items():
        mount = profile['mount']
        part = mount_part(mount)
        stl = part.folder / (part.file + '.stl')
        tris = align(read_stl(stl), profile['outline'].bounds)
        sections = compare(tris, expected_sections(profile))
        assert all(level['ok'] for level in sections.values()), (mount, sections)
        top = section(tris, 2.95)
        lands = {}
        for name, land in profile['lands'].items():
            zone = land.difference(profile['hexes'][name].buffer(0.02)).difference(profile['bores'][name])
            assert top.buffer(0.02).covers(zone), (name, 'the octagonal land is cut')
            cuts = list(profile['reliefs'].values()) + list(profile['heads'].values()) + list(profile['slots'].values())
            wall = min([profile['hexes'][name].boundary.distance(profile['outline'].boundary)]
                       + [profile['hexes'][name].distance(c) for c in cuts])
            assert wall >= MIN_WALL - 1e-6, (name, wall)
            lands[name] = dict(center=list(SO_ANCHORS[name][1]), across_flats_mm=LAND_AF,
                               land_area_mm2=round(land.area, 3), hex_pocket_wall_min_mm=round(wall, 3))
        expected = expected_volume(profile)
        assert abs(bodies[mount]['volume_mm3'] - expected) / expected < 0.002, (mount, bodies[mount]['volume_mm3'], expected)
        reliefs = {str(k): [round(v, 3) for v in r.bounds] for k, r in profile['reliefs'].items()}
        out[mount] = dict(stl=stl.name, sections={str(z): v for z, v in sections.items()}, lands=lands,
                          pin_reliefs=reliefs, plate_pads=len(profile['pads']),
                          volume_mm3=round(bodies[mount]['volume_mm3'], 3), layered_volume_mm3=round(expected, 3))
    return out


def support_contact_plan(params):
    """Build bearing probes so contacts and assembly clearances share one CLI model load."""
    z = params['plate_top_Z'] - params['TBD_plate_T']
    mounts = sorted(PLATE_SUPPORT_MOUNTS)
    plates = sorted(set(PLATE_SUPPORT_MOUNTS.values()))
    commands = [dict(command='inspect.clearance', params=dict(
        bodies=mounts, against=plates, clearance=0.01, min_volume=0.000001))]
    probes = {}
    support_number = 0
    for suffix, profile in mount_profiles().items():
        mount = profile['mount']
        plate = PLATE_SUPPORT_MOUNTS[mount]
        top = layers(profile)[-1][2]                      # pad tops: pads minus fasteners, nut and switch bodies
        for index, pad in enumerate(profile['pads'], 1):
            support_number += 1
            feature_name = f'MOUNT_{suffix}_PAD_{index}'
            probe_name = f'SEAT_PROBE_{support_number}'
            commands.append(dict(command='solid.extrude', params=dict(
                name=probe_name, body_name=probe_name,
                sketch=f'SK_{feature_name}', profiles='all',
                start_offset=z - SEAT_ROOT_Z - 0.05, distance=0.1, operation='new')))
            probes[probe_name] = (mount, plate, pad.intersection(top).area, feature_name)
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
        assert all(abs(a - b) < 0.01 for a, b in zip(faces, expected)), (mount, faces, expected)
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
MJF_MAX = (370.0, 276.0)


def check_print_set(bodies):
    """print_v5/order2 STL/STEP files: hashes as recorded, one component, no open edges, volume = CAD, MJF 1.0 / resin 0.8
    walls, box on the bed and inside the MJF build volume."""
    expected = by_file('order2')
    parts = json.loads(ORDERS['order2']['record'].read_text(encoding='utf-8'))
    thin = {t['file']: t for t in json.loads(ORDERS['order2']['wall'].read_text(encoding='utf-8'))['parts']}
    assert {p['file'] for p in parts} == set(expected) == set(thin), (set(thin), {p['file'] for p in parts})
    out = []
    for p in parts:
        part = expected[p['file']]
        stl = part.folder / (p['file'] + '.stl')
        step = stl.with_suffix('.step')
        assert sha(stl) == p['stl_sha256'] and sha(step) == p['step_sha256'], p['file']
        t = thin[p['file']]
        assert t['stl_sha256'] == p['stl_sha256'], ('thin-wall scan is of another STL', p['file'])
        assert t['wall_min_mm'] is None or t['wall_min_mm'] >= part.wall_limit - 1e-3, (p['file'], t['wall_min_mm'])
        assert abs(p['cad_volume_mm3'] - bodies[p['body']]['volume_mm3']) < 1e-3, p['file']
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


def main(accept=False):
    v5 = document(V5)
    p5 = {p['name']: p['expr'] for p in v5['params'] if not p['model']}
    rows = {r['name']: r for r in csv.DictReader((ROOT / 'model/parameters_seam_v5.csv').open(encoding='utf-8-sig'))}
    assert {n: r['expression'] for n, r in rows.items()} == p5, 'CSV differs from the model'
    assert all(f['name'] != 'COVER_DROP_V5' for f in v5['features'])

    new = live_shapes(V5)
    for n in GENERATED:
        assert len(new[n]) == 1 and len(new[n][0]['shells']) == 1, n
    trials = live_shapes(TRIALS)       # snap trials A/C and rear rest variants: their own model (build_seam_v5.trials_document)
    assert (set(trials) == set(ctrl_v5.TRIALS) | set(REAR_REST_TRIALS) | set(seam_coupon_bodies())
            and not set(trials) & set(new)), set(trials)
    assert all(len(s) == 1 and len(s[0]['shells']) == 1 for s in trials.values())

    ev, _ = evaluation(V5)
    baseline = check_baseline(ev, evaluation(TRIALS)[0], p5, accept)
    errors = [t['name'] for t in ev['timeline'] if t.get('error')]
    warnings = [t['name'] for t in ev['timeline'] if t.get('warning')]
    dof = [s['name'] for s in ev['sketches'] if s.get('dof') != 0]
    assert not errors and not dof and not warnings, (errors, dof, warnings)
    bodies = {b['name']: b for b in ev['bodies']}
    params = {p['name']: p['value'] for p in ev['params'] if p.get('value') is not None}
    covers = [n for n in bodies if n.startswith('COVER_')]
    assert sorted(covers) == sorted(COVERS)
    cover_lo = params['plate_top_Z'] - params['TBD_cover_boss_H']
    cover_hi = params['v5_cover_top_Z']
    for n in covers:
        lo, hi = bodies[n]['bbox']['min'][2], bodies[n]['bbox']['max'][2]
        assert abs(hi - cover_hi) < 1e-6 and abs(lo - cover_lo) < 1e-6, n
    # current values (cover T 6, top Z 19, skin 3.9, keycap rest Z 17.3) are pinned by the baseline's `values`
    walls = leg_magnet_walls(params)
    # Rear rest blocks: the plates end at the rear flange bottom (no foot) and each block spans pad top -> flange bottom,
    # touching its plate's flange (the contact shows in the clearance pass below).
    flange_bottom = params['plate_top_Z'] - params['TBD_plate_T'] - params['split_flange_H']
    rest_bottom = params['v5_rear_boss_top_Z'] + params['v5_rear_rest_gap']
    for plate in ('PLATE_L_SPLIT_V1', 'PLATE_R_SPLIT_V1'):
        assert abs(bodies[plate]['bbox']['min'][2] - flange_bottom) < 1e-6, (plate, bodies[plate]['bbox'])
    for i in REAR_RESTS:
        box = bodies[REAR_REST_BODY.format(i)]['bbox']
        assert abs(box['min'][2] - rest_bottom) < 1e-6 and abs(box['max'][2] - flange_bottom) < 1e-6, (i, box)
        assert abs(box['max'][2] - box['min'][2] - params['v5_rear_rest_H']) < 1e-6, (i, box)
    levels = cover_levels(params, bodies)
    support_plan = support_contact_plan(params)

    # clearance of the generated bodies: against every other body and among themselves
    moving = sorted(GENERATED)
    others = sorted(n for n in bodies if n not in GENERATED)
    clearance, clearance_batches = {}, []
    for key, group, against in (('generated_vs_rest', moving, others), ('among_generated', moving, None)):
        skip = [MOUNT_SCREW_INTERFACE] if key == 'generated_vs_rest' else []
        commands, total_pairs, candidate_pairs, skipped = clearance_candidates(bodies, group, against, 0.01, skip)
        clearance_batches.append((key, commands, total_pairs, candidate_pairs, skipped))
        if key == 'generated_vs_rest':
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
    write_json(ROOT / 'inspection/data/seam-v5-clearance.json', clearance)
    touching = {frozenset(c.split(' | ')) for k in ('generated_vs_rest', 'among_generated') for c in clearance[k]['contacts']}
    rest_contacts = {REAR_REST_BODY.format(i): plate for i, (_, plate) in REAR_RESTS.items()}
    for rest, plate in rest_contacts.items():
        assert frozenset((rest, plate)) in touching, (rest, plate, 'the flange does not sit on the rest block')

    print_set = check_print_set(bodies)

    # Covers and plates from the order-2 print set (model/review_v5 was abolished 2026-11-10: it exported and scanned
    # the same bodies a second time). Resin covers: every wall >= 1.0 (material rule), wedge tips excluded by wall_min_mm.
    by_body = {p['body']: p for p in json.loads((ROOT / 'inspection/data/seam-v5-print-set.json').read_text(encoding='utf-8'))}
    walls_by_file = {r['file']: r for r in print_set}
    parts = []
    for body in COVERS + ['PLATE_L_SPLIT_V1', 'PLATE_R_SPLIT_V1']:
        p = by_body[body]
        wall = walls_by_file[p['file']]['wall_min_mm']
        if body in COVERS:
            assert wall is None or wall >= WALL_SCAN['limit'] - 1e-3, (p['file'], wall)
        parts.append(dict(file=p['file'], material=p['material'], volume_cm3=round(p['cad_volume_mm3'] / 1000, 2),
                          wall_min_mm=wall, stl_volume_rel_err=walls_by_file[p['file']]['rel']))
    clearance_summary = {k: dict(overlaps=len(clearance[k]['overlaps']), contacts=len(clearance[k]['contacts']),
                                 unchecked=len(clearance[k]['unchecked']))
                         for k in ('generated_vs_rest', 'among_generated')}
    result = dict(ok=True, inputs=fingerprints(VERIFY_INPUTS), v5_sha=sha(V5), baseline_sha=sha(BASELINE),
                  baseline_bodies=len(baseline['bodies']) + len(baseline['trials']), print_set=print_set, bodies=len(new),
                  timeline_active=sum(1 for t in ev['timeline'] if not t.get('suppressed')), rear_rest_Z=[rest_bottom, flange_bottom], rear_rest_contacts=rest_contacts,
                  generated=sorted(GENERATED), timeline=len(ev['timeline']), sketches=len(ev['sketches']), params=len(p5),
                  cover_Z=[cover_lo, cover_hi], cover_T=params['TBD_cover_T'], cover_levels=levels,
                  plate_supports=seats, mounts=verify_mounts(bodies), leg_magnets=walls,
                  clearance=clearance_summary, mount_screw_interface=clearance['mount_screw_interface'],
                  parts=parts)
    write_json(ROOT / 'inspection/data/seam-v5-verification.json', result)
    print(json.dumps(result, indent=1, ensure_ascii=False))


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--accept', action='store_true',
                    help='after an intended design change: print the differences from the baseline, rewrite it, verify')
    main(ap.parse_args().accept)
