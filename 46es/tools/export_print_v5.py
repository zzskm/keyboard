"""Export the v5 print sets listed in tools/parts_v5.py into model/print_v5/<order>/ in print orientation.

python tools/export_print_v5.py                   both orders
python tools/export_print_v5.py --order order1    one order (order1 = test parts, order2 = main set)
  -> model/print_v5/<order>/46es_v5_<part>.stl    (binary STL in print orientation: flipped about X where the table
                                                   says so, box at 0,0,0)
  -> model/print_v5/<order>/46es_v5_<part>.step   (assembly coordinates, for checking)
  -> inspection/data/seam-v5-print-set.json, seam-v5-trial-print-set.json     (hashes, sizes, CAD/STL volumes and
                                                   the source CAD hash of every part)
  -> inspection/data/seam-v5-mjf-thin-wall.json, seam-v5-trial-thin-wall.json (thin wall scan, assembly coordinates)

One CLI run per source CAD exports every selected part of it (plan 3-6): opening the v5 model costs about 20 s,
the exports milliseconds. build_seam_v5.py adds the same export commands to the call that saves each model it
builds (.cache/v5/export/<model>/, valid while the model keeps the hash in its manifest), so right after a build the
exporter opens no model built by it. The CLI timings of every run go to .cache/print_v5/export-timings.json.

A part whose body has the same shape digest (cad_model.shape_digests, recorded as shape_sha256) as in the current
record, and whose files and wall scan still match that record, is kept as it is (plan 3-4): only its source_sha256 is
updated. So a rebuild that reproduces the bodies, or a change to one mount, re-exports and re-scans only what changed;
a source whose parts are all kept is not opened. --force re-exports everything (after editing this exporter or the STL
scripts it calls). Each order is replaced as a whole (publish()).
"""
import argparse
import json
from pathlib import Path
from shutil import copyfile, rmtree
import subprocess
import sys
from tempfile import TemporaryDirectory

from common import ROOT, CLI, sha, write_json
sys.path.insert(0, str(ROOT / 'inspection/scripts'))
from orient_print_stl import orient  # noqa: E402
from check_stl import check  # noqa: E402
from cad_eval_cache import evaluation  # noqa: E402
from cad_model import shape_digests  # noqa: E402
from parts_v5 import PARTS, ORDERS, WALL_SCAN  # noqa: E402
import cover_pattern_v5  # noqa: E402

CACHE = ROOT / '.cache/print_v5'
PREBUILT = ROOT / '.cache/v5/export'
MJF_MAX = (370.0, 276.0, 360.0)


def raw_files(part, folder):
    """Where one export run leaves a part: the unoriented STL and the final-named STEP (its header holds the name)."""
    return folder / 'raw' / f'{part.order}_{part.name}.stl', folder / part.order / (part.file + '.step')


def export_commands(source, folder, orders=tuple(ORDERS), only=None):
    """CLI commands exporting every part of `source` in `orders` (or just `only`) into `folder`; makes the subfolders."""
    commands = []
    for part in PARTS:
        if part.source == source and part.order in orders and (only is None or part in only):
            stl, step = raw_files(part, folder)
            stl.parent.mkdir(parents=True, exist_ok=True)
            step.parent.mkdir(parents=True, exist_ok=True)
            commands.append(dict(command='file.export_stl', params=dict(path=str(stl), bodies=[part.body], quality='fine')))
            commands.append(dict(command='file.export_step', params=dict(path=str(step), bodies=[part.body])))
    return commands


def prebuilt_dir(source):
    return PREBUILT / Path(source).stem


def prebuild(source, pending):
    """Fresh folder and commands for build_seam_v5.py: it runs them right after saving `pending` (to become `source`),
    then calls seal_prebuilt(source, pending)."""
    folder = prebuilt_dir(source)
    rmtree(folder, ignore_errors=True)
    return export_commands(source, folder)


def seal_prebuilt(source, pending):
    folder = prebuilt_dir(source)
    write_json(folder / 'manifest.json', dict(source_sha256=sha(pending), commands=export_commands(source, folder)))


def prebuilt(source, digest):
    """The build's export folder for `source` if it was made from these bytes with the current commands."""
    folder = prebuilt_dir(source)
    try:
        manifest = json.loads((folder / 'manifest.json').read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return None
    if manifest.get('source_sha256') != digest or manifest.get('commands') != export_commands(source, folder):
        return None
    files = [path for part in PARTS if part.source == source for path in raw_files(part, folder)]
    return folder if all(path.is_file() for path in files) else None


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--order', nargs='+', choices=list(ORDERS), default=list(ORDERS), help='orders to export (default both)')
    parser.add_argument('--force', action='store_true', help='re-export parts whose shape is unchanged too')
    args = parser.parse_args()
    orders = [o for o in ORDERS if o in args.order]
    CACHE.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(dir=CACHE, prefix='print_v5_') as scratch:
        export(orders, Path(scratch), args.force)


def kept_parts(selected, digests):
    """Parts that need no export: same body shape, mapping and files as the committed record, wall scan current.
    Returns {part: (record row, wall scan row)}."""
    kept = {}
    for order in dict.fromkeys(p.order for p in selected):
        paths = ORDERS[order]
        try:
            rows = {r['file']: r for r in json.loads(paths['record'].read_text(encoding='utf-8'))}
            scans = {t['file']: t for t in json.loads(paths['wall'].read_text(encoding='utf-8'))['parts']}
        except (OSError, ValueError, KeyError):
            continue
        for part in (p for p in selected if p.order == order):
            row, scan = rows.get(part.file), scans.get(part.file)
            if (row and scan and row.get('shape_sha256') == digests[part.source].get(part.body)
                    and (row['body'], row['material'], row['print_flip_about_X']) == (part.body, part.material, part.flip)
                    and scan['stl_sha256'] == row['stl_sha256']
                    and all((part.folder / (part.file + ext)).is_file() and sha(part.folder / (part.file + ext)) == row[key]
                            for ext, key in (('.stl', 'stl_sha256'), ('.step', 'step_sha256')))):
                kept[part] = (row, scan)
    return kept


def export(orders, scratch, force=False):
    selected = [p for p in PARTS if p.order in orders]
    sources = list(dict.fromkeys(p.source for p in selected))
    input_hashes = {source: sha(source) for source in sources}
    digests = {source: shape_digests(source) for source in sources}
    kept = {} if force else kept_parts(selected, digests)
    folders, bodies, timings = {}, {}, {}
    for source in sources:
        fresh = [p for p in selected if p.source == source and p not in kept]
        if not fresh:
            timings[source.name] = 'all parts kept (shape unchanged)'
            continue
        folder = prebuilt(source, input_hashes[source])
        if folder is None:
            folder = scratch / source.stem
            command_path = scratch / (source.stem + '_export.json')
            write_json(command_path, export_commands(source, folder, orders, fresh), indent=None)
            timing = scratch / (source.stem + '_timings.json')
            subprocess.run([str(CLI), 'run', str(command_path), '--in', str(source), '--quiet', '--timings', '--profile',
                            '--json-out', str(timing)], check=True)
            timings[source.name] = json.loads(timing.read_text(encoding='utf-8'))
        else:
            timings[source.name] = 'exported by build_seam_v5.py'
        folders[source] = folder
        evaluated, _ = evaluation(source, CLI)
        errors = [f['name'] for f in evaluated['timeline'] if f.get('error')]
        if errors:
            raise ValueError(f'{source.name}: timeline errors: {errors}')
        bodies[source] = {b['name']: b for b in evaluated['bodies']}
    write_json(CACHE / 'export-timings.json', timings)
    results = {}
    for order in orders:
        parts = [p for p in selected if p.order == order]
        results[order] = export_order(order, parts, folders, bodies, input_hashes, digests, kept, scratch)
    print(json.dumps(dict(ok=True, source_sha={str(p.relative_to(ROOT)): digest for p, digest in input_hashes.items()},
                          kept=sorted(f'{p.order}/{p.name}' for p in kept), **results), indent=1, ensure_ascii=False))


def diagnose(part, *meshes):
    diagnostics = CACHE / 'print_diagnostics'
    diagnostics.mkdir(parents=True, exist_ok=True)
    for label, path in meshes:
        copyfile(path, diagnostics / f'{part.order}_{part.name}_{label}.stl')


def export_order(order, parts, folders, bodies, input_hashes, digests, kept, scratch):
    out_dir = scratch / order
    out_dir.mkdir()
    records = []
    for part in parts:
        if part in kept:
            row = dict(kept[part][0], source_sha256=input_hashes[part.source])
            row.setdefault('shape_sha256', digests[part.source][part.body])
            records.append(row)
            continue
        raw_path, step = raw_files(part, folders[part.source])
        stl = out_dir / (part.file + '.stl')
        copyfile(step, stl.with_suffix('.step'))
        raw_mesh = check(str(raw_path))
        if len(raw_mesh['components']) != 1 or raw_mesh['bad_edge_count'] != 0:
            diagnose(part, ('raw', raw_path))
            raise AssertionError((part.file, 'SolidCraft raw STL', len(raw_mesh['components']), raw_mesh['bad_edge_count']))
        orient(str(raw_path), str(stl), part.flip)
        m = check(str(stl))
        if len(m['components']) != 1 or m['bad_edge_count'] != 0:
            diagnose(part, ('raw', raw_path), ('oriented', stl))
            raise AssertionError((part.file, 'oriented STL', len(m['components']), m['bad_edge_count']))
        c = m['components'][0]
        cad = bodies[part.source][part.body]['volume_mm3']
        rel = abs(c['signed_volume'] - cad) / cad
        assert rel < 0.001, (part.file, rel)
        size = [c['bbox']['max'][k] - c['bbox']['min'][k] for k in range(3)]
        assert all(s <= lim for s, lim in zip(sorted(size[:2], reverse=True), MJF_MAX[:2])) and size[2] <= MJF_MAX[2], (part.file, size)
        assert abs(c['bbox']['min'][2]) < 1e-4, (part.file, c['bbox']['min'])
        records.append(dict(order=order, file=part.file, body=part.body, material=part.material, print_flip_about_X=part.flip,
                            cad_volume_mm3=round(cad, 4), stl_triangles=m['triangles'], stl_components=1, stl_bad_edges=0,
                            stl_volume_mm3=round(c['signed_volume'], 4), stl_rel_volume_error=round(rel, 6),
                            print_bbox_mm=[round(s, 3) for s in size], bed_zmin=round(c['bbox']['min'][2], 4),
                            stl_sha256=sha(stl), step_sha256=sha(stl.with_suffix('.step')),
                            source_sha256=input_hashes[part.source], shape_sha256=digests[part.source][part.body]))
    paths = ORDERS[order]
    record_path = out_dir / paths['record'].name
    write_json(record_path, records)
    thin = out_dir / paths['wall'].name
    scan = {p.file: kept[p][1] for p in parts if p in kept}
    fresh = [r for p, r in zip(parts, records) if p not in kept]
    if not fresh:
        report = json.loads(paths['wall'].read_text(encoding='utf-8'))     # header (thresholds, spacing) as committed
    else:
        # The scan maps each STL back to assembly coordinates by its body's box: give it the bodies of its sources.
        ev_path = out_dir / 'bodies.json'
        write_json(ev_path, {'bodies': [b for source in dict.fromkeys(p.source for p in parts if p not in kept)
                                        for b in bodies[source].values()]}, indent=None)
        subprocess.run([sys.executable, '-I', str(ROOT / 'inspection/scripts/thin_wall_scan.py'),
                        '--limit', str(WALL_SCAN['limit']), '--warn', str(WALL_SCAN['warn']),
                        '--json', str(thin), '--map', str(record_path), str(ev_path),
                        '--exclude', str(write_engravings(out_dir / 'engravings.json')),
                        *[str(out_dir / (r['file'] + '.stl')) for r in fresh]], check=True, capture_output=True)
        report = json.loads(thin.read_text(encoding='utf-8'))
        scan.update({t['file']: t for t in report['parts']})
    report['parts'] = [scan[p.file] for p in parts]
    # thin_wall_scan.py's own format (indent 1, no final newline), so a merged scan reads like a full one
    thin.write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding='utf-8', newline='\n')
    rows = []
    for part, r in zip(parts, records):
        t = scan[r['file']]
        wall = t['wall_min_mm']
        if wall is not None and wall < part.wall_limit - 0.001:
            raise ValueError(f"{r['file']}: wall {wall} mm is below {part.wall_limit} mm")
        rib = t.get('excluded_wall_min_mm')
        if rib is not None and rib < cover_pattern_v5.rib() - 0.02:
            raise ValueError(f"{r['file']}: engraved name rib {rib} mm is below the font rib {cover_pattern_v5.rib()} mm")
        rows.append(dict(file=r['file'], material=r['material'], volume_cm3=round(r['cad_volume_mm3'] / 1000, 2),
                         size=r['print_bbox_mm'], wall_min_mm=t['wall_min_mm'], min_mm=t['min_mm']))
    folder = ROOT / 'model/print_v5' / order
    folder.mkdir(parents=True, exist_ok=True)
    targets = {out_dir / (r['file'] + extension): folder / (r['file'] + extension)
               for p, r in zip(parts, records) if p not in kept for extension in ('.step', '.stl')}
    targets[thin] = paths['wall']
    targets[record_path] = paths['record']
    publish(order, scratch, targets, {p.source: input_hashes[p.source] for p in parts})
    return rows


def write_engravings(path):
    """thin_wall_scan.py --exclude regions: the engraved cover name and its boss tab copies. Its ribs are the font's
    (cover_pattern_v5.rib(), 0.25 at the production size), below the resin wall on purpose (user 2026-11-11); export
    checks them against that rib instead of the material wall."""
    import coupon_v5
    regions = {'46es_v5_cover_L': [dict(name='L_name', xy=list(cover_pattern_v5.text_shape().bounds), face='top',
                                        depth=cover_pattern_v5.DEPTH)],
               '46es_v5_boss_tab': [dict(name=f'tab_text_{k}', xy=list(shape.bounds), face='bottom',
                                         depth=cover_pattern_v5.DEPTH) for k, shape in coupon_v5.tab_texts().items()]}
    write_json(path, regions)
    return path


def publish(order, scratch, targets, input_hashes):
    """Replace one validated set and restore any files replaced before an I/O error."""
    lock = CACHE / f'{order}.publishing'
    lock.mkdir()
    try:
        backups = scratch / f'previous_{order}'
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
