"""Export the v5 parts that changed (review only, assembly coordinates) and the v5 parameter CSV.

python tools/export_seam_v5_review.py
  -> model/review_v5/46es_v5_<part>_REVIEW_ONLY.stl/.step (5 parts) + 46es_v5_changed_REVIEW_ONLY.step
  -> model/parameters_seam_v5.csv
  -> inspection/data/seam-v5-exports.json (file hashes, CAD volumes)
  -> inspection/data/seam-v5-thin-wall.json (MJF/resin minimum wall scan of the STLs)
Not an order set: print orientation and order folders stay with print_v4 until the user approves v5.
"""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
CLI = 'C:/Program Files/SolidCraft/solidcraft-cli.exe'
MODEL = ROOT / 'model/46es_mount_seam_v5.sc'
OUT = ROOT / 'model/review_v5'
PARTS = {'cover_L': ('COVER_L_DRAFT_TBD', '8001 레진 투명', 0.8),
         'cover_T': ('COVER_T_DRAFT_TBD', '8001 레진 투명', 0.8),
         'cover_R': ('COVER_R_DRAFT_TBD', '8001 레진 투명', 0.8),
         'plate_L': ('PLATE_L_SPLIT_V1', 'MJF PA12S-HP 검정', 1.0),
         'plate_R': ('PLATE_R_SPLIT_V1', 'MJF PA12S-HP 검정', 1.0)}
MAGNETS = ['REF_LEGMAG_L_COVER', 'REF_LEGMAG_L_PLATE', 'REF_LEGMAG_R_COVER', 'REF_LEGMAG_R_PLATE']


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    # plate files must not change in the 2nd pass (two-level cover touches the covers only): remember their hashes
    before = {part: {ext: sha(OUT / f'46es_v5_{part}_REVIEW_ONLY{ext}') for ext in ('.stl', '.step')
                     if (OUT / f'46es_v5_{part}_REVIEW_ONLY{ext}').exists()} for part in ('plate_L', 'plate_R')}
    script = []
    for part, (body, _, _) in PARTS.items():
        stem = OUT / f'46es_v5_{part}_REVIEW_ONLY'
        script.append(dict(command='file.export_stl', params=dict(path=str(stem) + '.stl', bodies=[body], quality='fine')))
        script.append(dict(command='file.export_step', params=dict(path=str(stem) + '.step', bodies=[body])))
    script.append(dict(command='file.export_step', params=dict(
        path=str(OUT / '46es_v5_changed_REVIEW_ONLY.step'), bodies=[b for b, _, _ in PARTS.values()] + MAGNETS)))
    script.append(dict(command='parameters.export', params=dict(path=str(ROOT / 'model/parameters_seam_v5.csv'),
                                                                 format='csv')))
    cache = ROOT / 'guide/.cache/v5'
    cache.mkdir(parents=True, exist_ok=True)
    (cache / 'export.json').write_text(json.dumps(script), encoding='utf-8')
    subprocess.run([CLI, 'run', str(cache / 'export.json'), '--in', str(MODEL), '--quiet'], check=True)
    ev = cache / 'eval_v5_export.json'
    subprocess.run([CLI, 'eval', '--in', str(MODEL), '--json-out', str(ev)], check=True, capture_output=True)
    bodies = {b['name']: b for b in json.loads(ev.read_text(encoding='utf-8'))['bodies']}
    files = []
    for part, (body, material, wall) in PARTS.items():
        stem = OUT / f'46es_v5_{part}_REVIEW_ONLY'
        files.append(dict(file=stem.name, body=body, material=material, wall_limit_mm=wall,
                          cad_volume_mm3=round(bodies[body]['volume_mm3'], 3),
                          bbox=bodies[body]['bbox'], stl_sha256=sha(stem.with_suffix('.stl')),
                          step_sha256=sha(stem.with_suffix('.step'))))
    plates_unchanged = {part: {ext: before[part].get(ext) == sha(OUT / f'46es_v5_{part}_REVIEW_ONLY{ext}')
                               for ext in ('.stl', '.step')} for part in before}
    record = dict(model=MODEL.name, model_sha=sha(MODEL), parts=files, plate_files_unchanged_since_previous_export=plates_unchanged,
                  combined_step=dict(file='46es_v5_changed_REVIEW_ONLY.step',
                                     sha256=sha(OUT / '46es_v5_changed_REVIEW_ONLY.step')),
                  csv_sha256=sha(ROOT / 'model/parameters_seam_v5.csv'))
    (ROOT / 'inspection/data/seam-v5-exports.json').write_text(json.dumps(record, indent=1, ensure_ascii=False),
                                                              encoding='utf-8')
    scan = ROOT / 'inspection/scripts/thin_wall_scan.py'
    subprocess.run([sys.executable, '-I', str(scan), '--limit', '0.8', '--warn', '1.5', '--json',
                    str(ROOT / 'inspection/data/seam-v5-thin-wall.json'),
                    *[str(OUT / (f['file'] + '.stl')) for f in files]], check=True)
    print(json.dumps(dict(ok=True, parts=[f['file'] for f in files]), ensure_ascii=False))


if __name__ == '__main__':
    main()
