"""B coupon row C: SMP_upper 2 -> 1.7 (= v5 TBD_upper_plate_T), re-export order 1 files (plan §8, 2026-11-06).

python tools/update_sw_hole_coupon_upper.py
  -> model/samples/46es_sw_hole_sample.sc            (SMP_upper 1.7, everything else unchanged)
  -> model/print_v4/order1/46es_v4_sw_hole_coupon.stl/.step   (STL: hole face down, tools/orient_print_stl.py --flip)
  -> model/print_v4/order1/46es_v4_boss_tab.stl/.step         (same body, re-exported; STL must hash the same)
  -> inspection/data/seam-v4-print-set.json          (coupon + boss tab entries refreshed)
  -> inspection/data/seam-v4-mjf-thin-wall.json      (refreshed for the two order-1 files)
  -> guide/.cache/v5/coupon_upper_1p7.json           (hand calculation vs CAD)
The file names stay v4 (the coupon is still the order-1 test piece); only row C's upper layer follows v5.
Row C's lower relief is open up to the hole-layer bottom, so the coupon volume does not change: the 1.5 hole
layer just moves up by 0.3 (Z 6.5-8.0 -> 6.8-8.3). bbox unchanged.
"""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
CLI = 'C:/Program Files/SolidCraft/solidcraft-cli.exe'
SAMPLE = ROOT / 'model/samples/46es_sw_hole_sample.sc'
ORDER1 = ROOT / 'model/print_v4/order1'
CACHE = ROOT / 'guide/.cache/v5'
PRINT_SET = ROOT / 'inspection/data/seam-v4-print-set.json'
THIN = ROOT / 'inspection/data/seam-v4-mjf-thin-wall.json'
NEW_UPPER = 1.7
FILES = {'46es_v4_sw_hole_coupon': ('SW_HOLE_SAMPLE', True), '46es_v4_boss_tab': ('BOSS_TAB_SAMPLE', False)}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(*args):
    r = subprocess.run([CLI, *map(str, args)], capture_output=True)
    if r.returncode:
        raise RuntimeError(r.stderr.decode('utf-8', errors='replace')[-4000:])


def evaluate(model, out):
    run('eval', '--in', model, '--json-out', out)
    return json.loads(out.read_text(encoding='utf-8'))


def main():
    CACHE.mkdir(parents=True, exist_ok=True)
    sys.path.insert(0, str(ROOT / 'inspection/scripts'))
    from check_stl import check
    before = evaluate(SAMPLE, CACHE / 'coupon_eval_before.json')
    vol0 = {b['name']: b for b in before['bodies']}
    with zipfile.ZipFile(SAMPLE) as z:
        doc = json.loads(z.read('document.json'))
        container = z.read('container.json')
    p = next(p for p in doc['params'] if p['name'] == 'SMP_upper')
    assert p['expr'] == '2 mm', p['expr']
    p['expr'] = f'{NEW_UPPER} mm'
    p['comment'] = ('행 C upper plate 층 깊이(16.5 개구) = TBD_upper_plate_T. [v5 사용자 확정 2026-11-06] 2 → 1.7: 행 C는 v5 plate 3층'
                    '(위 1.7 / 가운데 1.5 홀 / 아래 개방)을 plate와 같은 출력 방향(상면 베드)으로 재현. 파일 이름은 v4 유지')
    cells = [f['name'] for f in doc['features'] if f['name'].startswith('UPPER_C')]
    seed = CACHE / 'coupon_seed.sc'
    with zipfile.ZipFile(seed, 'w', zipfile.ZIP_DEFLATED) as z:
        z.writestr('document.json', json.dumps(doc, ensure_ascii=False))
        z.writestr('container.json', container)
    pending = CACHE / 'coupon_pending.sc'
    run('run', '--in', seed, '--save', pending, '--quiet')
    after = evaluate(pending, CACHE / 'coupon_eval_after.json')
    assert not [t for t in after['timeline'] if t.get('error')]
    vol1 = {b['name']: b for b in after['bodies']}
    values = {q['name']: q['value'] for q in after['params'] if q.get('value') is not None}
    assert abs(values['SMP_upper'] - NEW_UPPER) < 1e-9
    # hand calculation: the row C column holds only the 1.5 hole-layer ring (16.5^2 - h^2) at any upper depth
    expected = {'SW_HOLE_SAMPLE': vol0['SW_HOLE_SAMPLE']['volume_mm3'], 'BOSS_TAB_SAMPLE': vol0['BOSS_TAB_SAMPLE']['volume_mm3']}
    for n, v in expected.items():
        assert abs(vol1[n]['volume_mm3'] - v) < 1e-3, (n, vol1[n]['volume_mm3'], v)
        for k in ('min', 'max'):
            assert all(abs(a - b) < 1e-6 for a, b in zip(vol1[n]['bbox'][k], vol0[n]['bbox'][k])), n
    # row C levels moved up by 0.3: hole-layer top Z = T - upper, bottom Z = T - upper - ledge
    sys.path.insert(0, str(ROOT / 'tools'))
    from build_seam_v5 import horizontal_faces
    from verify_minimal_v2 import live_shapes
    faces = horizontal_faces(live_shapes(pending)['SW_HOLE_SAMPLE'][0])
    zs = sorted({round(z, 4) for z, a in faces})
    hole_top, hole_bot = values['SMP_T'] - NEW_UPPER, values['SMP_T'] - NEW_UPPER - values['SMP_ledge']
    assert round(hole_top, 4) in zs and round(hole_bot, 4) in zs, (hole_top, hole_bot, zs)
    assert 8.0 not in zs, zs   # the old row C hole-layer top is gone (6.5 stays: counterbore floors of row D)
    pending.replace(SAMPLE)
    # exports: STL (fine) to a temp file, then print orientation; STEP in model coordinates
    old = {f: {ext: sha(ORDER1 / f'{f}{ext}') for ext in ('.stl', '.step')} for f in FILES}
    script = []
    for f, (body, flip) in FILES.items():
        script.append(dict(command='file.export_stl', params=dict(path=str(CACHE / f'{f}_raw.stl'), bodies=[body], quality='fine')))
        script.append(dict(command='file.export_step', params=dict(path=str(ORDER1 / f'{f}.step'), bodies=[body])))
    (CACHE / 'coupon_export.json').write_text(json.dumps(script), encoding='utf-8')
    run('run', CACHE / 'coupon_export.json', '--in', SAMPLE, '--quiet')
    records = json.loads(PRINT_SET.read_text(encoding='utf-8'))
    by_file = {r['file']: r for r in records}
    report = dict(sample_sha=sha(SAMPLE), SMP_upper=NEW_UPPER, row_C_cells=len(cells), hole_layer_Z=[round(hole_bot, 4), round(hole_top, 4)],
                  volumes={n: dict(before=round(vol0[n]['volume_mm3'], 4), after=round(vol1[n]['volume_mm3'], 4)) for n in expected},
                  files={})
    for f, (body, flip) in FILES.items():
        raw, stl = CACHE / f'{f}_raw.stl', ORDER1 / f'{f}.stl'
        subprocess.run([sys.executable, '-I', str(ROOT / 'tools/orient_print_stl.py'), str(raw), str(stl)] + (['--flip'] if flip else []),
                       check=True, capture_output=True)
        mesh = check(str(stl))
        assert len(mesh['components']) == 1 and mesh['bad_edge_count'] == 0, f
        comp = mesh['components'][0]
        rec = by_file[f]
        assert rec['body'] == body and rec['print_flip_about_X'] == flip
        rec.update(cad_volume_mm3=round(vol1[body]['volume_mm3'], 4), stl_triangles=mesh['triangles'], stl_components=1, stl_bad_edges=0,
                   stl_volume_mm3=round(comp['signed_volume'], 4),
                   stl_rel_volume_error=round(abs(comp['signed_volume'] - vol1[body]['volume_mm3']) / vol1[body]['volume_mm3'], 6),
                   stl_sha256=sha(stl), step_sha256=sha(ORDER1 / f'{f}.step'))
        rec['print_bbox_mm'] = [round(comp['bbox']['max'][i] - comp['bbox']['min'][i], 3) for i in range(3)]
        rec['bed_zmin'] = round(comp['bbox']['min'][2], 6)
        report['files'][f] = dict(stl_sha_before=old[f]['.stl'], stl_sha_after=rec['stl_sha256'], stl_changed=old[f]['.stl'] != rec['stl_sha256'],
                                  step_sha_before=old[f]['.step'], step_sha_after=rec['step_sha256'],
                                  stl_volume_mm3=rec['stl_volume_mm3'], rel_err=rec['stl_rel_volume_error'], print_bbox_mm=rec['print_bbox_mm'])
    PRINT_SET.write_text(json.dumps(records, indent=1, ensure_ascii=False), encoding='utf-8')
    # thin-wall record: rescan the two order-1 files and splice them into the v4 MJF record
    thin_out = CACHE / 'coupon_thin.json'
    subprocess.run([sys.executable, '-I', str(ROOT / 'inspection/scripts/thin_wall_scan.py'), '--limit', '1.0', '--warn', '1.5',
                    '--json', str(thin_out), *[str(ORDER1 / f'{f}.stl') for f in FILES]], check=True, capture_output=True)
    scanned = {Path(t['file']).stem: t for t in json.loads(thin_out.read_text(encoding='utf-8'))['parts']}
    thin = json.loads(THIN.read_text(encoding='utf-8'))
    for i, t in enumerate(thin['parts']):
        stem = Path(t['file']).stem
        if stem in scanned:
            new = dict(scanned[stem]); new['file'] = t['file']
            thin['parts'][i] = new
            report['files'][stem]['wall_min_mm'] = new['wall_min_mm']
            report['files'][stem]['min_mm'] = new.get('min_mm')
    THIN.write_text(json.dumps(thin, indent=1, ensure_ascii=False), encoding='utf-8')
    (CACHE / 'coupon_upper_1p7.json').write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding='utf-8')
    print(json.dumps(report, indent=1, ensure_ascii=False))


if __name__ == '__main__':
    main()
