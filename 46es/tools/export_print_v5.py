"""Export the v5 order-2 print set (plate L/R, spine, controller bracket, cover L/T/R) from
model/46es_mount_seam_v5.sc into model/print_v5/order2/ in print orientation, with both current order sets under print_v5.

python tools/export_print_v5.py
  -> model/print_v5/order2/46es_v5_<part>.stl   (binary STL, print orientation: flipped about X, box at 0,0,0)
  -> model/print_v5/order2/46es_v5_<part>.step  (assembly coordinates, for checking)
  -> inspection/data/seam-v5-print-set.json     (hashes, dimensions and CAD/STL volumes)
  -> inspection/data/seam-v5-mjf-thin-wall.json (thin wall scan, mapped back to assembly coordinates)

Use --trial to export the four mounts, four test coupons and the three snap brackets (A/B/C) in model/print_v5/order1/.
Both order sets record the source CAD hash for every part.
"""
import argparse
import json
from pathlib import Path
from shutil import copyfile
import subprocess
import sys
from tempfile import TemporaryDirectory

from common import ROOT, CLI, sha, write_json
sys.path.insert(0, str(ROOT / 'inspection/scripts'))
from orient_print_stl import orient  # noqa: E402
from check_stl import check  # noqa: E402
from cad_eval_cache import evaluation  # noqa: E402

MODEL = ROOT / 'model/46es_mount_seam_v5.sc'
CACHE = ROOT / '.cache/print_v5'
# file stem -> (body, material, flip about X for printing); all order-2 parts print top face down (print_v5 README)
PARTS = {
    'plate_L': ('PLATE_L_SPLIT_V1', 'MJF PA12S-HP 검정', True),
    'plate_R': ('PLATE_R_SPLIT_V1', 'MJF PA12S-HP 검정', True),
    'spine': ('PLATE_SPINE_V1', 'MJF PA12S-HP 검정', True),
    'ctrl_bracket': ('CTRL_BRACKET_SPLIT_V1', 'MJF PA12S-HP 검정', True),
    'cover_L': ('COVER_L_DRAFT_TBD', '8001 레진 투명', True),
    'cover_T': ('COVER_T_DRAFT_TBD', '8001 레진 투명', True),
    'cover_R': ('COVER_R_DRAFT_TBD', '8001 레진 투명', True),
}
TRIAL_PARTS = {
    'sw_hole_coupon': ('SW_HOLE_SAMPLE', 'MJF PA12S-HP 검정', True),
    'boss_tab': ('BOSS_TAB_SAMPLE', '8001 레진 투명', False),
    'seam_coupon_L': ('SEAM_COUPON_L_V4', 'MJF PA12S-HP 검정', True),
    'seam_coupon_R': ('SEAM_COUPON_R_V4', 'MJF PA12S-HP 검정', True),
    'mount_L': ('MOUNT_L_PAIR_V3', 'MJF PA12S-HP 검정', False),
    'mount_R': ('MOUNT_R_PAIR_V3', 'MJF PA12S-HP 검정', False),
    'mount_H02_SO3': ('MOUNT_H02_SO3_MIN_V2', 'MJF PA12S-HP 검정', False),
    'mount_H03_SO6': ('MOUNT_H03_SO6_MIN_V2', 'MJF PA12S-HP 검정', False),
    # snap bracket engagement trial (tools/ctrl_v5.py TRIALS): B = production, A shallower, C deeper
    'ctrl_bracket': ('CTRL_BRACKET_SPLIT_V1', 'MJF PA12S-HP 검정', True),
    'ctrl_snap_A': ('CTRL_SNAP_TRIAL_A', 'MJF PA12S-HP 검정', True),
    'ctrl_snap_C': ('CTRL_SNAP_TRIAL_C', 'MJF PA12S-HP 검정', True),
}
SAMPLE = ROOT / 'model/samples/46es_sw_hole_sample.sc'
MJF_MAX = (370.0, 276.0, 360.0)


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--trial', action='store_true', help='export the eleven order-1 test parts')
    args = parser.parse_args()
    parts = TRIAL_PARTS if args.trial else PARTS
    order = 'order1' if args.trial else 'order2'
    out = ROOT / 'model/print_v5' / order
    out.mkdir(parents=True, exist_ok=True)
    sources = {MODEL: {k: v for k, v in parts.items() if v[0] not in ('SW_HOLE_SAMPLE', 'BOSS_TAB_SAMPLE')}}
    if args.trial:
        from cad_model import document
        upper = next(p['expr'] for p in document(SAMPLE)['params'] if p['name'] == 'SMP_upper')
        if upper != '1.7 mm':
            raise ValueError(f'trial row C must match v5 upper layer 1.7 mm, got {upper}')
        sources[SAMPLE] = {k: v for k, v in parts.items() if v[0] in ('SW_HOLE_SAMPLE', 'BOSS_TAB_SAMPLE')}
    CACHE.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(dir=CACHE, prefix=f'print_v5_{order}_') as scratch:
        export(parts, order, sources, out, Path(scratch))


def export(parts, order, sources, out, scratch):
    trial = order == 'order1'
    raw = scratch / 'raw'
    raw.mkdir()
    input_hashes = {path: sha(path) for path in sources}
    body_sources = {body: source for source, mapped in sources.items()
                    for body, _, _ in mapped.values()}
    bodies = {}
    for source, source_parts in sources.items():
        script = []
        for part, (body, _, _) in source_parts.items():
            script.append(dict(command='file.export_stl', params=dict(path=str(raw / f'{part}.stl'), bodies=[body], quality='fine')))
            script.append(dict(command='file.export_step', params=dict(path=str(scratch / f'46es_v5_{part}.step'), bodies=[body])))
        command_path = raw / (source.stem + '_export.json')
        write_json(command_path, script, indent=None)
        subprocess.run([str(CLI), 'run', str(command_path), '--in', str(source), '--quiet'], check=True)
        ev_path = raw / (source.stem + '_eval.json')
        evaluated, _ = evaluation(source, ROOT / 'guide/.cache/v5', CLI)
        write_json(ev_path, evaluated, indent=None)
        errors = [f['name'] for f in evaluated['timeline'] if f.get('error')]
        if errors:
            raise ValueError(f'{source.name}: timeline errors: {errors}')
        bodies.update({b['name']: b for b in evaluated['bodies']})
    # Both source models use assembly coordinates; combine their non-overlapping body names for mapping.
    ev_path = raw / 'eval.json'
    write_json(ev_path, {'bodies': list(bodies.values())}, indent=None)
    records = []
    for part, (body, material, flip) in parts.items():
        stl = scratch / f'46es_v5_{part}.stl'
        raw_path = raw / f'{part}.stl'
        raw_mesh = check(str(raw_path))
        if len(raw_mesh['components']) != 1 or raw_mesh['bad_edge_count'] != 0:
            diagnostics = ROOT / 'guide/.cache/v5/print_diagnostics'
            diagnostics.mkdir(parents=True, exist_ok=True)
            copyfile(raw_path, diagnostics / f'{part}_raw.stl')
            raise AssertionError((part, 'SolidCraft raw STL', len(raw_mesh['components']), raw_mesh['bad_edge_count']))
        orient(str(raw_path), str(stl), flip)
        m = check(str(stl))
        if len(m['components']) != 1 or m['bad_edge_count'] != 0:
            diagnostics = ROOT / 'guide/.cache/v5/print_diagnostics'
            diagnostics.mkdir(parents=True, exist_ok=True)
            copyfile(raw_path, diagnostics / f'{part}_raw.stl')
            copyfile(stl, diagnostics / f'{part}_oriented.stl')
            raise AssertionError((part, 'oriented STL', len(m['components']), m['bad_edge_count']))
        c = m['components'][0]
        cad = bodies[body]['volume_mm3']
        rel = abs(c['signed_volume'] - cad) / cad
        assert rel < 0.001, (part, rel)
        size = [c['bbox']['max'][k] - c['bbox']['min'][k] for k in range(3)]
        assert all(s <= lim for s, lim in zip(sorted(size[:2], reverse=True), MJF_MAX[:2])) and size[2] <= MJF_MAX[2], (part, size)
        assert abs(c['bbox']['min'][2]) < 1e-4, (part, c['bbox']['min'])
        records.append(dict(order=order, file=stl.stem, body=body, material=material, print_flip_about_X=flip,
                            cad_volume_mm3=round(cad, 4), stl_triangles=m['triangles'], stl_components=1, stl_bad_edges=0,
                            stl_volume_mm3=round(c['signed_volume'], 4), stl_rel_volume_error=round(rel, 6),
                            print_bbox_mm=[round(s, 3) for s in size], bed_zmin=round(c['bbox']['min'][2], 4),
                            stl_sha256=sha(stl), step_sha256=sha(stl.with_suffix('.step'))))
    for row in records:
        row['source_sha256'] = input_hashes[body_sources[row['body']]]
    record_path = scratch / ('seam-v5-trial-print-set.json' if trial else 'seam-v5-print-set.json')
    write_json(record_path, records)
    thin = scratch / ('seam-v5-trial-thin-wall.json' if trial else 'seam-v5-mjf-thin-wall.json')
    subprocess.run([sys.executable, '-I', str(ROOT / 'inspection/scripts/thin_wall_scan.py'), '--limit', '1.0', '--warn', '1.5',
                    '--json', str(thin), '--map', str(record_path), str(ev_path),
                    *[str(scratch / (r['file'] + '.stl')) for r in records]], check=True, capture_output=True)
    scan = {t['file']: t for t in json.loads(thin.read_text(encoding='utf-8'))['parts']}
    rows = []
    for r in records:
        t = scan[r['file']]
        wall = t['wall_min_mm']
        limit = 0.8 if r['material'].startswith('8001') else 1.0
        if wall is not None and wall < limit - 0.001:
            raise ValueError(f"{r['file']}: wall {wall} mm is below {limit} mm")
        rows.append(dict(file=r['file'], material=r['material'], volume_cm3=round(r['cad_volume_mm3'] / 1000, 2),
                         size=r['print_bbox_mm'], wall_min_mm=t['wall_min_mm'], min_mm=t['min_mm']))
    targets = {scratch / (row['file'] + extension): out / (row['file'] + extension)
               for row in records for extension in ('.step', '.stl')}
    for path in (thin, record_path):
        targets[path] = ROOT / 'inspection/data' / path.name
    publish(order, scratch, targets, input_hashes)
    print(json.dumps(dict(ok=True, source_sha={str(p.relative_to(ROOT)): digest for p, digest in input_hashes.items()},
                          parts=rows), indent=1, ensure_ascii=False))


def publish(order, scratch, targets, input_hashes):
    """Replace one validated set and restore any files replaced before an I/O error."""
    lock = CACHE / f'{order}.publishing'
    lock.mkdir()
    try:
        backups = scratch / 'previous'
        backups.mkdir()
        existing = set()
        for destination in targets.values():
            if destination.exists():
                copyfile(destination, backups / destination.name)
                existing.add(destination)
        if any(sha(path) != digest for path, digest in input_hashes.items()):
            raise ValueError('print sources changed during export')

        replaced = []
        try:
            for source, destination in targets.items():
                source.replace(destination)
                replaced.append(destination)
        except (OSError, KeyboardInterrupt):
            for destination in reversed(replaced):
                if destination in existing:
                    (backups / destination.name).replace(destination)
                else:
                    destination.unlink()
            raise
    finally:
        lock.rmdir()


if __name__ == '__main__':
    main()
