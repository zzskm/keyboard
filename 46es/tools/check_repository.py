"""Check current 46es references, CAD snapshots and print files without SolidCraft.

Run from any directory: python -B 46es/tools/check_repository.py
The CAD kernel, fresh thin-wall scans and the browser are separate checks.
"""
import ast
import csv
import json
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'inspection/scripts'))
sys.path.insert(0, str(ROOT / 'guide'))
from cad_model import document, live_shapes
from check_stl import check
from build_guide import expand
from common import sha


def require(condition, message):
    if not condition:
        raise ValueError(message)


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def source_checks():
    # The index defines the intended commit. Run after git add, including deletions.
    paths = subprocess.check_output(['git', '-C', str(ROOT), 'ls-files', '-z']).decode().split('\0')
    for rel in filter(None, paths):
        path = ROOT / rel
        require(path.is_file(), f'tracked file is missing: {rel}')
        require(not rel.endswith(('.bak', '.tmp', '.sc~')), f'backup file tracked: {rel}')
        if path.suffix == '.py':
            ast.parse(path.read_text(encoding='utf-8'), filename=rel)
        elif path.suffix == '.json':
            read(path)
        elif path.suffix == '.md':
            text = path.read_text(encoding='utf-8')
            for target in re.findall(r'\]\(([^\s)]+)(?:\s+"[^"]*")?\)', text):
                link = urlsplit(target.strip('<>'))
                if link.scheme or link.netloc or not link.path:
                    continue
                dest = (path.parent / unquote(link.path)).resolve()
                require(dest.exists(), f'{rel}: broken link {target}')
    return len(list(filter(None, paths)))


def build_checks():
    """The committed production CAD was generated from the committed generator inputs (model/seam_v5_build.json)."""
    from build_seam_v5 import BUILD_RECORD, OUTPUT, TRIALS_OUTPUT, build_record
    require(BUILD_RECORD.is_file(), 'missing build record: run python 46es/tools/build_seam_v5.py')
    recorded, current = read(BUILD_RECORD), build_record()
    stale = sorted(rel for rel in set(recorded['inputs']) | set(current['inputs'])
                   if recorded['inputs'].get(rel) != current['inputs'].get(rel))
    require(not stale, f'CAD not regenerated after input change: {", ".join(stale)} (run python 46es/tools/build_seam_v5.py)')
    for key, path in (('output', OUTPUT), ('trials_output', TRIALS_OUTPUT)):
        require(recorded.get(key) == current[key] and sha(path) == recorded.get(key + '_sha'),
                f'{current[key]} differs from its build record (hand edit or partial regeneration)')


def model_checks():
    from verify_seam_v5 import V4, V5, FLAT, V4_SHA, FLAT_SHA, CHANGED, DERIVED, ADDED, REMOVED, PLATE_L_GATE_RELIEF_MM3
    from build_seam_v5 import REAR_FEET
    require(sha(V4) == V4_SHA, 'v4 baseline changed')
    require(sha(FLAT) == FLAT_SHA, 'flat baseline changed')
    doc = document(V5)
    params = {p['name']: p['expr'] for p in doc['params'] if not p['model']}
    with (ROOT / 'model/parameters_seam_v5.csv').open(encoding='utf-8-sig') as f:
        rows = {r['name']: r['expression'] for r in csv.DictReader(f)}
    require(params == rows, 'current parameter CSV differs from CAD')
    baseline, current = map(live_shapes, (V4, V5))
    require(set(current) - set(baseline) == ADDED and set(baseline) - set(current) == REMOVED, 'CAD body set changed')
    same = [n for n in baseline if n in current and n not in CHANGED | DERIVED]
    require(all(baseline[n] == current[n] for n in same), 'untouched CAD body differs')
    # Phase 2 (2026-11-09) moved PLATE_L's two bracket screw holes and filled its gate reliefs; the rear feet
    # (2026-11-09) add material below the rear flanges of both plates. verify_seam_v5 compares the evaluated solids
    # against the flat snapshot; its record is tied to this V5 below (v5_sha).
    seam = read(ROOT / 'inspection/data/seam-v5-verification.json')
    deltas = seam.get('plate_delta_from_flat_Z18', {})
    for plate, extra in (('PLATE_L_SPLIT_V1', PLATE_L_GATE_RELIEF_MM3), ('PLATE_R_SPLIT_V1', 0.0)):
        d = deltas.get(plate, {})
        feet = sum(1 for _, p in REAR_FEET.values() if p == plate)
        require(d.get('feet') == feet and abs(d.get('delta_mm3', 0) - extra - feet * d.get('foot_mm3', 0)) < 0.05,
                f'{plate} differs from regression baseline beyond the phase 2 change and the rear feet')
    sample = ROOT / 'model/samples/46es_sw_hole_sample.sc'
    sample_params = {p['name']: p['expr'] for p in document(sample)['params']}
    require(sample_params['SMP_upper'] == params['TBD_upper_plate_T'] == '1.7 mm', 'trial row C differs from plate')
    ref = read(ROOT / 'model/assembly_reference_v5.json')
    inputs = {'source_sha': V5, 'output_sha': ROOT / 'model/46es_assembly_review_v5.sc',
              'generator_sha': ROOT / ref['generator'],
              'measurement_sha': ROOT / 'model/measurements/2026-11-04T111846Z.json',
              'trials_sha': ROOT / 'model/ctrl_trials_v5.sc'}
    for key, path in inputs.items():
        require(sha(path) == ref[key], f'stale assembly reference: {key}')
    review = live_shapes(inputs['output_sha'])
    for record, key, expected in [('seam-v5-verification.json', 'v5_sha', sha(V5)),
                                  ('assembly-reference-v5-verification.json', 'source_sha', sha(V5)),
                                  ('assembly-reference-v5-verification.json', 'model_sha', ref['output_sha'])]:
        require(read(ROOT / 'inspection/data' / record)[key] == expected, f'stale model report: {record}')
    return current, live_shapes(sample), review, len(same)


def guide_checks(names):
    spec = read(ROOT / 'guide/guide_v5.json')
    for key in ('model', 'measurements', 'reference_manifest', 'interactive'):
        require((ROOT / 'guide' / spec[key]).is_file(), f'guide path missing: {key}')
    config = read(ROOT / 'guide' / spec['interactive'])
    for label, patterns in spec['groups'].items():
        expand(patterns, names, spec['groups'], label)
    for render in spec['renders']:
        expand(render['show'], names, spec['groups'], render['id'])
        if render.get('hide'):
            expand(render['hide'], names, spec['groups'], render['id'])
    source = next(s for s in spec['sections'] if s['type'] == 'parts')
    ids = [p['bodies'][0] for p in source['printed']] + [p['id'] for p in source['hardware']] + [p['id'] for p in config['references']]
    require(len(ids) == len(set(ids)), 'duplicate guide part ID')
    for p in source['printed'] + config['references']:
        if p['bodies']:
            expand(p['bodies'], names, spec['groups'], 'part')
    for patterns in config['hardware_bodies'].values():
        if patterns:
            expand(patterns, names, spec['groups'], 'hardware')
    assembly = next(s for s in spec['sections'] if s['type'] == 'assembly')
    steps = [s['id'] for phase in assembly['phases'] for s in phase['steps']]
    require(len(steps) == len(set(steps)) and set(steps) == set(config['steps']), 'guide step mismatch')
    for key, step in config['steps'].items():
        require(set(step['focus']) <= set(step['show']), f'invisible focus: {key}')
        require(set(step['show'] + step['focus'] + list(step['needs'])) <= set(ids), f'unknown guide part: {key}')
    return len(steps)


def print_checks(current, sample):
    from export_print_v5 import MODEL, SAMPLE, TRIALS, PARTS, TRIAL_PARTS, source_of
    shapes = {MODEL: current, SAMPLE: sample, TRIALS: live_shapes(TRIALS)}
    hashes = {path: sha(path) for path in shapes}
    for order, record, wall, expected in [
        ('order1', 'seam-v5-trial-print-set.json', 'seam-v5-trial-thin-wall.json', TRIAL_PARTS),
        ('order2', 'seam-v5-print-set.json', 'seam-v5-mjf-thin-wall.json', PARTS),
    ]:
        parts = read(ROOT / 'inspection/data' / record)
        scans = {x['file']: x for x in read(ROOT / 'inspection/data' / wall)['parts']}
        expected_files = {'46es_v5_' + name for name in expected}
        require(len(parts) == len(expected_files) and {p['file'] for p in parts} == set(scans) == expected_files, f'incomplete {order}')
        folder = ROOT / 'model/print_v5' / order
        require({p.stem for p in folder.glob('*.stl')} == {p.stem for p in folder.glob('*.step')} == expected_files, f'unlisted output: {order}')
        for p in parts:
            name = p['file']
            body, material, flip = expected[name.removeprefix('46es_v5_')]
            require((p['body'], p['material'], p['print_flip_about_X']) == (body, material, flip), f'wrong print mapping: {name}')
            source = source_of(body)
            require(body in shapes[source], f'CAD body missing: {body} in {source.name}')
            require(p.get('source_sha256') == hashes[source], f'stale {order} CAD source: {name}')
            for ext, key in [('.stl', 'stl_sha256'), ('.step', 'step_sha256')]:
                require(sha(folder / (name + ext)) == p[key], f'output hash differs: {name}{ext}')
            scan = scans[name]
            require(scan['stl_sha256'] == p['stl_sha256'], f'stale wall scan: {name}')
            limit = .8 if material.startswith('8001') else 1.0
            require(scan['wall_min_mm'] is None or scan['wall_min_mm'] >= limit - .001, f'thin wall: {name}')
            mesh = check(str(folder / (name + '.stl')))
            require(len(mesh['components']) == 1 and mesh['bad_edge_count'] == 0, f'invalid mesh: {name}')
            comp = mesh['components'][0]
            require(abs(comp['signed_volume'] - p['cad_volume_mm3']) / p['cad_volume_mm3'] < .001, f'volume differs: {name}')
            size = [comp['bbox']['max'][i] - comp['bbox']['min'][i] for i in range(3)]
            require(all(abs(x-y) < .002 for x,y in zip(size,p['print_bbox_mm'])), f'bounds differ: {name}')
            require(abs(comp['bbox']['min'][2]) < .0001, f'not on print bed: {name}')
    return len(PARTS) + len(TRIAL_PARTS)


def main():
    count = source_checks()
    build_checks()
    current, sample, review, unchanged = model_checks()
    steps = guide_checks(list(review))
    prints = print_checks(current, sample)
    print(f'OK: {count} tracked files; links/JSON/Python; {unchanged} unchanged CAD bodies; {steps} guide steps; {prints} print meshes')
    print('SolidCraft re-evaluation, fresh wall scans and browser interaction were not run.')


if __name__ == '__main__':
    main()
