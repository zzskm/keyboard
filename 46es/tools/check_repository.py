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
from cad_model import document, live_shapes, shape_digest
from check_stl import check
from build_guide import expand
from common import sha, changed_inputs

VERIFICATION_RECORDS = ('inspection/data/seam-v5-verification.json',
                        'inspection/data/assembly-reference-v5-verification.json')
LFS_POINTER = b'version https://git-lfs.github.com/spec/'   # model/*.sc checked out without Git LFS (.gitattributes)


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
        if path.suffix == '.sc':
            with path.open('rb') as f:
                head = f.read(len(LFS_POINTER))
            require(head != LFS_POINTER, f'{rel} is a Git LFS pointer, not the CAD: run git lfs install && git lfs pull')
        elif path.suffix == '.py':
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
    from build_seam_v5 import stale_reasons
    stale = stale_reasons()
    require(not stale, 'CAD does not match its build record (python 46es/tools/pipeline.py --status): ' + '; '.join(stale))


def verifier_checks():
    """Each verification record names the verifier and the files it read; a verifier edited after its last run
    (or an input replaced) leaves an `ok` that no longer describes the current code (AGENTS.md §6)."""
    for record in VERIFICATION_RECORDS:
        inputs = read(ROOT / record).get('inputs')
        require(inputs, f'{record} has no input fingerprints: rerun its verifier')
        changed = changed_inputs(inputs)
        require(not changed, f'stale {record}: changed since the verifier ran: {", ".join(changed)}')


def model_checks():
    from verify_seam_v5 import V5, TRIALS, BASELINE
    doc = document(V5)
    params = {p['name']: p['expr'] for p in doc['params'] if not p['model']}
    with (ROOT / 'model/parameters_seam_v5.csv').open(encoding='utf-8-sig') as f:
        table = list(csv.DictReader(f))
    rows = {r['name']: r['expression'] for r in table}
    require(params == rows, 'current parameter CSV differs from CAD')
    # The v5 baseline (verify_seam_v5.py --accept) holds every body's shape fingerprint and every design parameter
    # with its value; the CSV's value column (written by the build from the evaluated model) must agree.
    baseline = read(BASELINE)
    require(params == baseline['params'], 'CAD parameters differ from inspection/data/seam-v5-baseline.json')
    values = {r['name']: float(r['value']) for r in table if r['value'] not in ('', None)}
    differ = sorted(n for n, v in values.items() if n in baseline['values'] and abs(v - baseline['values'][n]) > 1e-4)
    require(set(values) == set(baseline['values']) and not differ,
            f'parameter values differ from the v5 baseline: {differ or sorted(set(values) ^ set(baseline["values"]))}')
    current, trials = live_shapes(V5), live_shapes(TRIALS)
    for shapes, expected in ((current, baseline['bodies']), (trials, baseline['trials'])):
        require(set(shapes) == set(expected), f'CAD body set differs from the v5 baseline: {sorted(set(shapes) ^ set(expected))}')
        differ = sorted(n for n in shapes if shape_digest(shapes[n]) != expected[n]['shape_sha256'])
        require(not differ, f'CAD bodies differ from the v5 baseline (verify_seam_v5.py --accept): {differ}')
    coupon_params = {p['name']: p['expr'] for p in document(TRIALS)['params']}
    require(params['TBD_upper_plate_T'] == '1.7 mm' and coupon_params['SMP_upper'] == 'TBD_upper_plate_T'
            and coupon_params['SMP_T'] == 'TBD_plate_T', 'B coupon row C does not follow the plate layers')
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
    return current, review, len(current) + len(trials)


def printed_checks(printed):
    """The guide's printed-part table against tools/parts_v5.py: the same bodies (the B coupon and the boss tab are
    in the guide's trial table instead), the orders named in each note, and the STL orientation."""
    from parts_v5 import PARTS, SAME_PRINT
    from coupon_v5 import BODIES as COUPONS
    registry = {}
    for part in PARTS:
        if part.body not in COUPONS:
            registry.setdefault(part.body, []).append(part)
    guide = {body: p for p in printed for body in p['bodies']}
    for copy, original in SAME_PRINT.items():        # shown beside the part whose file prints them
        require(guide.get(copy) is guide.get(original) is not None, f'guide printed parts: {copy} is not listed with {original}')
        del guide[copy]
    require(set(guide) == set(registry), f'guide printed parts differ from tools/parts_v5.py: {sorted(set(guide) ^ set(registry))}')
    for body, parts in registry.items():
        entry = guide[body]
        orders = {f'주문 {part.order[-1]}' for part in parts}
        named = {f'주문 {n}' for n in '12' if f'주문 {n}' in entry['note']}
        require(named == orders, f'guide order differs from tools/parts_v5.py: {body} {sorted(named)} vs {sorted(orders)}')
        flips = {part.flip for part in parts}
        upright = 'STL은 밑면이 아래' in entry['orient']
        flipped = any(f'STL은 {face}이 아래' in entry['orient'] for face in ('윗면', '지붕'))
        require(len(flips) == 1 and upright != flipped and flipped in flips,
                f'guide STL orientation differs from tools/parts_v5.py: {body}')


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
    printed_checks(source['printed'])
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


def print_checks(current):
    from parts_v5 import MODEL, TRIALS, PARTS, ORDERS, by_file
    shapes = {MODEL: current, TRIALS: live_shapes(TRIALS)}
    hashes = {path: sha(path) for path in shapes}
    for order, paths in ORDERS.items():
        parts = read(paths['record'])
        scans = {x['file']: x for x in read(paths['wall'])['parts']}
        expected = by_file(order)
        require([p['file'] for p in parts] == list(expected) and set(scans) == set(expected), f'incomplete {order}')
        folder = ROOT / 'model/print_v5' / order
        require({p.stem for p in folder.glob('*.stl')} == {p.stem for p in folder.glob('*.step')} == set(expected), f'unlisted output: {order}')
        for p in parts:
            name = p['file']
            part = expected[name]
            require((p['body'], p['material'], p['print_flip_about_X']) == (part.body, part.material, part.flip), f'wrong print mapping: {name}')
            source = part.source
            require(part.body in shapes[source], f'CAD body missing: {part.body} in {source.name}')
            require(p.get('source_sha256') == hashes[source], f'stale {order} CAD source: {name}')
            require(p.get('shape_sha256') == shape_digest(shapes[source][part.body]), f'stale {order} body shape: {name}')
            for ext, key in [('.stl', 'stl_sha256'), ('.step', 'step_sha256')]:
                require(sha(folder / (name + ext)) == p[key], f'output hash differs: {name}{ext}')
            scan = scans[name]
            require(scan['stl_sha256'] == p['stl_sha256'], f'stale wall scan: {name}')
            require(scan['wall_min_mm'] is None or scan['wall_min_mm'] >= part.wall_limit - .001, f'thin wall: {name}')
            mesh = check(str(folder / (name + '.stl')))
            require(len(mesh['components']) == 1 and mesh['bad_edge_count'] == 0, f'invalid mesh: {name}')
            comp = mesh['components'][0]
            require(abs(comp['signed_volume'] - p['cad_volume_mm3']) / p['cad_volume_mm3'] < .001, f'volume differs: {name}')
            size = [comp['bbox']['max'][i] - comp['bbox']['min'][i] for i in range(3)]
            require(all(abs(x-y) < .002 for x,y in zip(size,p['print_bbox_mm'])), f'bounds differ: {name}')
            require(abs(comp['bbox']['min'][2]) < .0001, f'not on print bed: {name}')
    return len(PARTS)


def numbers(text):
    return re.findall(r'\d+(?:\.\d+)?', text)


def shown(expected, text):
    """`expected` appears in `text` as written to the precision shown (13 → '13', 95.334 → '95.33' or '95.334')."""
    for n in numbers(text):
        places = len(n.partition('.')[2])
        if abs(float(n) - expected) <= 0.5 * 10 ** -places + 1e-6:
            return True
    return False


def table_rows(text, heading):
    """Cells of the table rows under one `## heading` (up to the next heading)."""
    section = text.split(f'\n## {heading}', 1)[1].split('\n#', 1)[0]
    return [[c.strip() for c in line.strip().strip('|').split('|')] for line in section.splitlines()
            if line.startswith('|') and not set(line) <= set('|-: ')]


def print_readme_checks():
    """model/print_v5/README.md part tables (plan 4-4): the measured cells (size, order-2 volume and minimum wall) are
    written by tools/doc_tables.py from the records and must be current; the material column follows parts_v5.py."""
    import doc_tables
    from parts_v5 import RESIN, by_file
    text = (ROOT / 'model/print_v5/README.md').read_text(encoding='utf-8')
    for order, heading in doc_tables.HEADINGS.items():
        registry = by_file(order)
        rows = table_rows(text, heading)
        header, rows = rows[0], rows[1:]
        col = {name: next(i for i, h in enumerate(header) if name in h) for name in ('파일', '재료')}
        for row in rows:
            for file in doc_tables.row_files(row[col['파일']]):
                require(('투명' in row[col['재료']]) == (registry[file].material == RESIN), f'print_v5/README.md {file}: material')
    try:
        return doc_tables.check()
    except AssertionError as e:
        require(False, str(e))


# docs/design.md 「현행 치수」: row label -> the values its text must show (expressions over the baseline values;
# OUTLINE_X/Y are the plate halves' combined extent). A row not listed here is prose the check does not read.
DESIGN_ROWS = {
    'plate 상면': ['plate_top_Z'],
    '스위치 상부 개구': ['TBD_upper_plate_T', 'TBD_sw_notch_H'],
    '스위치 착좌': ['plate_top_Z - TBD_upper_plate_T', 'TBD_sw_hole'],
    '커버 윗면 / 본체 두께': ['v5_cover_top_Z', 'TBD_cover_T'],
    'mount–plate 접촉면': ['plate_top_Z - TBD_plate_T'],
    '뒤 받침 블록': ['v5_rear_rest_L', 'v5_rear_rest_W', 'v5_rear_rest_H', 'v5_rear_rest_gap',
                    *[f'v5_rear_rest_{i}_X {s} v5_rear_rest_L / 2' for i in (1, 2, 3) for s in '-+']],
    '커버 다리 자석 포켓 위 살': ['v5_legmag_skin'],
    '커버 창 윤곽': ['v5_cover_silhouette_cell', 'v5_cover_silhouette_min_rail'],
    '참고 키캡 밑면': ['v5_keycap_bottom_above_seat', 'v5_keycap_bottom_rest_Z'],
    '케이스 테두리': ['v5_rim_ref_Z', 'v5_cover_top_above_rim'],
    'plate·커버 전체 외곽': ['OUTLINE_X', 'OUTLINE_Y'],
    '자석': ['TBD_magnet_D', 'TBD_magnet_T'],
    '다리 자석 포켓': ['TBD_magnet_D + 2 * TBD_magnet_clr', 'TBD_magnet_D + 2 * v5_legmag_plate_clr',
                  'v5_legmag_L_X', 'v5_legmag_R_X', 'v5_legmag_L_Y', 'v5_legmag_R_Y'],
}


def design_checks():
    """docs/design.md 「현행 치수」 numbers against the v5 baseline (plan 4-4)."""
    from verify_seam_v5 import BASELINE
    baseline = read(BASELINE)
    plates = [baseline['bodies'][n]['bbox'] for n in ('PLATE_L_SPLIT_V1', 'PLATE_R_SPLIT_V1')]
    values = dict(baseline['values'],
                  OUTLINE_X=max(b[1][0] for b in plates) - min(b[0][0] for b in plates),
                  OUTLINE_Y=max(b[1][1] for b in plates) - min(b[0][1] for b in plates))
    rows = {r[0]: r[1] for r in table_rows((ROOT / 'docs/design.md').read_text(encoding='utf-8'), '현행 치수')[1:]}
    for label, expressions in DESIGN_ROWS.items():
        row = next((k for k in rows if k.startswith(label)), None)
        require(row, f'design.md 현행 치수: no row {label}')
        for expression in expressions:
            value = eval(expression, {'__builtins__': {}}, values)
            require(shown(value, rows[row]), f'design.md 현행 치수 「{row}」 does not show {expression} = {value:g}')
    return sum(map(len, DESIGN_ROWS.values()))


def main():
    count = source_checks()
    build_checks()
    verifier_checks()
    current, review, unchanged = model_checks()
    steps = guide_checks(list(review))
    prints = print_checks(current)
    doc_numbers = print_readme_checks() + design_checks()
    print(f'OK: {count} tracked files; links/JSON/Python; {unchanged} CAD bodies as in the v5 baseline; {steps} guide steps; '
          f'{prints} print meshes; {doc_numbers} document numbers')
    print('SolidCraft re-evaluation, fresh wall scans and browser interaction were not run.')


if __name__ == '__main__':
    main()
