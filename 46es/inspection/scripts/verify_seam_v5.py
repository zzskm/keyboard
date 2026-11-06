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
from build_seam_v5 import top_levels, COVERS, PLATE_SUPPORTS  # noqa: E402

CLI = 'C:/Program Files/SolidCraft/solidcraft-cli.exe'
V4 = ROOT / 'model/baselines/seam_v4.sc'
V5 = ROOT / 'model/46es_mount_seam_v5.sc'
FLAT = ROOT / 'model/baselines/flat_Z18.sc'      # 1st pass, flat cover top Z 18 (plan §5-0)
V4_SHA = '606d1bd91b191c67b2abdc4c054704c905bcb63d6ad89c783263a3cd4f018d2b'
FLAT_SHA = '66a2ec87687415a81eec83dbb7ff6d15b1d810af2780a78cc6d699d214a3e43d'
SWITCH_BOUNDS = {'REF_SW_ASSUMED_01'} | {f'REF_SW_ASSUMED_01 ({i})' for i in range(2, 47)}  # follow the 1.7 seat
CHANGED = SWITCH_BOUNDS | {seat[0] for seat in PLATE_SUPPORTS} | {'PLATE_L_SPLIT_V1', 'PLATE_R_SPLIT_V1', 'COVER_L_DRAFT_TBD', 'COVER_T_DRAFT_TBD', 'COVER_R_DRAFT_TBD'}
# Copies of the plates made before the v5 features (seam coupon, order 1). TBD_upper_plate_T sits before the copy in
# the timeline, so they are re-evaluated; the coupon box holds no switch opening, so volume and box must equal v4.
DERIVED = {'SEAM_COUPON_L_V4', 'SEAM_COUPON_R_V4'}
ADDED = {'REF_LEGMAG_L_COVER', 'REF_LEGMAG_L_PLATE', 'REF_LEGMAG_R_COVER', 'REF_LEGMAG_R_PLATE'}
NEW_PARAMS = {'v5_rim_ref_Z', 'v5_legmag_skin', 'v5_legmag_skin_min', 'v5_keycap_bottom_above_seat', 'v5_keycap_bottom_rest_Z',
              'v5_skirt_cover_H', 'v5_cover_top_Z', 'v5_cover_top_above_rim',
              'v5_key_margin', 'v5_legmag_plate_clr', 'v5_legpad_L', 'v5_lip_relief_clr',
              'v5_legmag_L_X', 'v5_legmag_L_Y', 'v5_legmag_R_X', 'v5_legmag_R_Y'}
CHANGED_PARAMS = {'TBD_cover_T', 'TBD_upper_plate_T'}
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


def support_contacts(params):
    """Confirm the complete rectangular bearing faces, without solid overlap."""
    z = params['v4_plate_top_Z'] - params['TBD_plate_T']
    mounts = sorted({seat[0] for seat in PLATE_SUPPORTS})
    plates = sorted({seat[1] for seat in PLATE_SUPPORTS})
    commands = [dict(command='inspect.clearance', params=dict(
        bodies=mounts, against=plates, clearance=0.01, min_volume=0.000001))]
    probes = {}
    for i, (mount, plate, x, y, length, width) in enumerate(PLATE_SUPPORTS, 1):
        name = f'SEAT_PROBE_{i}'
        commands.append(dict(command='solid.box', params=dict(
            name=name, body_name=name, corner=[x, y, z - 0.05],
            length=length, width=width, height=0.1, operation='new')))
        probes[name] = (mount, plate, x, y, length * width)
    commands.append(dict(command='inspect.clearance', params=dict(
        bodies=list(probes), against=mounts + plates, clearance=0.01, min_volume=0.000001)))
    results = cli_results(commands, V5, 'plate_support_contacts')
    contact, bearing = results[0], results[-1]
    assert not contact['overlaps'] and not contact['unchecked'], contact
    assert not bearing['unchecked'], bearing
    contacts = {frozenset((p['a'], p['b'])) for p in contact['near'] if p['distance_mm'] < 1e-6}
    volumes = {frozenset((p['a'], p['b'])): p['volume_mm3'] for p in bearing['overlaps']}
    seats = []
    for probe, (mount, plate, x, y, area) in probes.items():
        assert frozenset((mount, plate)) in contacts, (mount, plate, contact)
        for target in (mount, plate):
            volume = volumes[frozenset((probe, target))]
            assert abs(volume - area * 0.05) < 0.001, (probe, target, volume)
        seats.append(dict(mount=mount, target=plate, corner_xy=[x, y], top_Z=z,
                          seat_area_mm2=area))
    return seats


# ---------------------------------------------------------------- order-2 print set (3rd pass, tools/export_print_v5.py)
PRINT_V5 = ROOT / 'model/print_v5/order2'
PRINT_SET_FILES = {'46es_v5_plate_L', '46es_v5_plate_R', '46es_v5_spine', '46es_v5_ctrl_bracket', '46es_v5_ctrl_gate',
                   '46es_v5_cover_L', '46es_v5_cover_T', '46es_v5_cover_R'}
SAME_AS_V4 = {'46es_v5_spine': 'PLATE_SPINE_V1', '46es_v5_ctrl_bracket': 'CTRL_BRACKET_SPLIT_V1', '46es_v5_ctrl_gate': 'CTRL_GATE_SPLIT_V1'}
MJF_MAX = (370.0, 276.0)


def check_print_set(bodies, v4_bodies):
    """print_v5/order2 STL/STEP files: hashes as recorded, one component, no open edges, volume = CAD, MJF 1.0 / resin 0.8
    walls, box on the bed and inside the MJF build volume; spine, bracket and gate keep the v4 volumes."""
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
    assert not errors and not dof and warnings == ['HOUSING_POSTS_CAND'], (errors, dof, warnings)
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
    seats = support_contacts(params)

    # clearance of the changed/added bodies: against the 106 untouched bodies and among themselves
    moving = sorted(CHANGED | ADDED)
    others = sorted(n for n in bodies if n not in CHANGED | ADDED)
    res = cli_results([dict(command='inspect.clearance', params=dict(bodies=moving, against=others, clearance=0.01)),
                       dict(command='inspect.clearance', params=dict(bodies=moving, clearance=0.01))], V5, 'clearance_v5')
    clearance = {}
    for key, r in zip(('changed_vs_unchanged', 'among_changed'), res):
        clearance[key] = dict(overlaps=r['overlaps'], unchecked=r['unchecked'], pairs_checked=r['pairs_checked'],
                              contacts=sorted({f"{n['a']} | {n['b']}" for n in r['near'] if n['distance_mm'] < 1e-6}))
        assert r['overlaps'] == [] and r['unchecked'] == [], (key, r['overlaps'], r['unchecked'])
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
    result = dict(ok=True, v4_sha=V4_SHA, v5_sha=sha(V5), flat_Z18_sha=FLAT_SHA, print_set=print_set, bodies=len(new), untouched_bodies_exact=len(same),
                  derived_same_volume_box=sorted(DERIVED), plates_same_as_flat_Z18=True,
                  changed=sorted(CHANGED), added=sorted(ADDED), timeline=len(ev['timeline']), sketches=len(ev['sketches']),
                  params=len(p5), new_params=sorted(NEW_PARAMS), changed_params={n: p5[n] for n in CHANGED_PARAMS},
                  cover_Z=[cover_lo, cover_hi], cover_T=params['TBD_cover_T'], cover_levels=levels,
                  plate_supports=seats,
                  leg_magnets=walls,
                  clearance={k: dict(overlaps=len(v['overlaps']), contacts=len(v['contacts'])) for k, v in clearance.items()},
                  plate_files_unchanged=exports.get('plate_files_unchanged_since_previous_export'), parts=parts)
    (ROOT / 'inspection/data/seam-v5-verification.json').write_text(json.dumps(result, indent=1, ensure_ascii=False),
                                                                    encoding='utf-8')
    print(json.dumps(result, indent=1, ensure_ascii=False))


if __name__ == '__main__':
    main()
