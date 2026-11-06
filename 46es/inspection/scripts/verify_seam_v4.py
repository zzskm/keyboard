"""Read-only v4 audit: v3 kept, exact BRep of untouched bodies, CSV, health, clearance, print-set STL files,
MJF PA12 minimum wall (2026-11-05).

Run from the repository: python -B 46es/inspection/scripts/verify_seam_v4.py
"""
import csv, hashlib, json
from verify_minimal_v2 import ROOT, live_shapes, document
from check_stl import check

V3 = ROOT / 'model/46es_mount_side_pairs_v3.sc'
V4 = ROOT / 'model/46es_mount_seam_v4.sc'
CHANGED = {'PLATE_L_SPLIT_V1', 'PLATE_R_SPLIT_V1', 'PLATE_SPINE_V1',
           # MJF PA12 (2026-11-05): magnet Ø4 -> Ø3 (covers and magnet stand-ins), H02 support ledge trim
           'COVER_L_DRAFT_TBD', 'COVER_T_DRAFT_TBD', 'COVER_R_DRAFT_TBD', 'MOUNT_H02_SO3_MIN_V2'} | {
           f'REF_SO{i}_MAGNET' for i in range(1, 7)}
ADDED = {'REF_M2_SEAM_FRONT', 'REF_M2_SEAM_FRONT_NUT', 'SEAM_COUPON_L_V4', 'SEAM_COUPON_R_V4',
         'REF_M2_SEAM_COUPON', 'REF_M2_SEAM_COUPON_NUT'}
NEW_PARAMS = {'v4_plate_top_Z', 'seam_tab_T', 'seam_M2_X', 'seam_M2_Y', 'seam_cb_D', 'seam_nut_D',
              'spine_wire_W', 'spine_wire_H'}
MJF_PARAMS = {'TBD_magnet_D': '3'}  # v3 parameters whose expression the MJF change set on purpose
SAMPLES = ROOT / 'model/samples/46es_sw_hole_sample.sc'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    assert sha(V3) == '04538a672f0160896743c1e6d94a44cd301591da00abbb18146be4245bd8d4b0', 'v3 changed'
    v3, v4 = document(V3), document(V4)
    for prefix in ['SK22', 'SK24', 'SK25', 'SK34']:
        a = next(f for f in v3['features'] if f['name'].startswith(prefix))
        b = next(f for f in v4['features'] if f['name'].startswith(prefix))
        assert a == b, prefix
    p3 = {p['name']: p['expr'] for p in v3['params'] if not p['model']}
    p4 = {p['name']: p['expr'] for p in v4['params'] if not p['model']}
    assert set(p4) - set(p3) == NEW_PARAMS and not set(p3) - set(p4)
    assert all(p4[n] == e for n, e in MJF_PARAMS.items())
    assert all(p3[n] == p4[n] for n in p3 if n not in MJF_PARAMS), 'v3 parameter expression changed'
    rows = {r['name']: r for r in csv.DictReader((ROOT / 'model/parameters_seam_v4.csv').open(encoding='utf-8-sig'))}
    assert len(rows) == len(p4) == 195 and {n: r['expression'] for n, r in rows.items()} == p4
    gh60 = [n for n in rows if n.startswith('CAND_H')]
    assert len(gh60) == 12 and all(rows[n]['comment'].startswith('[GH60 채택 2026-11-05]') for n in gh60)

    old, new = live_shapes(V3), live_shapes(V4)
    assert len(old) == 105 and len(new) == 111
    assert set(new) - set(old) == ADDED and not set(old) - set(new)
    same = [n for n in old if n not in CHANGED]
    assert all(old[n] == new[n] for n in same), 'an untouched body changed'
    assert all(old[n] != new[n] for n in CHANGED)
    for n in CHANGED | ADDED:
        assert len(new[n]) == 1 and len(new[n][0]['shells']) == 1, n

    health = json.loads((ROOT / 'inspection/data/seam-v4-health.json').read_text(encoding='utf-8'))
    assert (health['bodies'], health['timeline_items'], health['sketches']) == (111, 428, 64)
    assert health['dof_nonzero'] == [] and health['errors'] == [] and health['warnings'] == ['HOUSING_POSTS_CAND']
    clear = json.loads((ROOT / 'inspection/data/seam-v4-clearance.json').read_text(encoding='utf-8'))
    for k in ('changed_vs_unchanged', 'among_changed'):
        assert clear[k]['overlaps'] == [] and clear[k]['unchecked'] == [], k

    smp = {p['name']: p['expr'] for p in document(SAMPLES)['params'] if not p['model']}
    assert smp['SMP_mag_D'] == '3.2' and smp['SMP_magf_min'] == '3.2', 'boss tab magnet pockets not Ø3'

    parts = json.loads((ROOT / 'inspection/data/seam-v4-print-set.json').read_text(encoding='utf-8'))
    thin = json.loads((ROOT / 'inspection/data/seam-v4-mjf-thin-wall.json').read_text(encoding='utf-8'))
    thin = {t['file']: t for t in thin['parts']}
    assert set(thin) == {p['file'] for p in parts}
    for p in parts:
        t = thin[p['file']]
        assert t['stl_sha256'] == p['stl_sha256'], ('thin-wall scan is of another STL', p['file'])
        assert t['wall_min_mm'] is None or t['wall_min_mm'] >= 0.999, ('wall under MJF 1.0', p['file'], t['wall_min_mm'])
    assert len(parts) == 16
    out = []
    for p in parts:
        stl = ROOT / 'model/print_v4' / p['order'] / (p['file'] + '.stl')
        step = stl.with_suffix('.step')
        assert sha(stl) == p['stl_sha256'] and sha(step) == p['step_sha256'], p['file']
        m = check(str(stl))
        assert len(m['components']) == 1 and m['bad_edge_count'] == 0, p['file']
        c = m['components'][0]
        rel = abs(c['signed_volume'] - p['cad_volume_mm3']) / p['cad_volume_mm3']
        assert rel < 0.001, (p['file'], rel)
        size = [c['bbox']['max'][k] - c['bbox']['min'][k] for k in range(3)]
        assert size[0] <= 250 and size[1] <= 250 and abs(c['bbox']['min'][2]) < 1e-4, p['file']
        out.append(dict(file=p['file'], order=p['order'], flip=p['print_flip_about_X'], rel=round(rel, 6),
                        size=[round(s, 2) for s in size]))
    print(json.dumps(dict(ok=True, untouched_bodies_exact=len(same), changed=sorted(CHANGED), added=sorted(ADDED),
                          thinnest_wall_mm=min(t['wall_min_mm'] for t in thin.values() if t['wall_min_mm'] is not None),
                          params=len(p4), parts=out), indent=1, ensure_ascii=False))


if __name__ == '__main__':
    main()
