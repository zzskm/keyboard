"""Export the v5 order-2 print set (plate L/R, spine, controller bracket + gate, cover L/T/R) from
model/46es_mount_seam_v5.sc into model/print_v5/order2/ in print orientation, like print_v4/order2.

python tools/export_print_v5.py
  -> model/print_v5/order2/46es_v5_<part>.stl   (binary STL, print orientation: flipped about X, box at 0,0,0)
  -> model/print_v5/order2/46es_v5_<part>.step  (assembly coordinates, for checking)
  -> inspection/data/seam-v5-print-set.json     (same schema as seam-v4-print-set.json)
  -> inspection/data/seam-v5-mjf-thin-wall.json (thin wall scan, mapped back to assembly coordinates)

Order 1 (mount x4, seam coupons, B coupon row C 1.7, boss tab) is unchanged between v4 and v5: its files stay
in model/print_v4/order1/. Spine, bracket and gate are identical bodies in v4 and v5 (verify_seam_v5 proves the
BRep equality); they are exported again here only so that order 2 is one folder.
"""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'inspection/scripts'))
from orient_print_stl import orient  # noqa: E402
from check_stl import check  # noqa: E402

CLI = 'C:/Program Files/SolidCraft/solidcraft-cli.exe'
MODEL = ROOT / 'model/46es_mount_seam_v5.sc'
OUT = ROOT / 'model/print_v5/order2'
CACHE = ROOT / 'guide/.cache/v5'
# file stem -> (body, material, flip about X for printing); all order-2 parts print top face down (print_v4 README)
PARTS = {
    'plate_L': ('PLATE_L_SPLIT_V1', 'MJF PA12S-HP 검정', True),
    'plate_R': ('PLATE_R_SPLIT_V1', 'MJF PA12S-HP 검정', True),
    'spine': ('PLATE_SPINE_V1', 'MJF PA12S-HP 검정', True),
    'ctrl_bracket': ('CTRL_BRACKET_SPLIT_V1', 'MJF PA12S-HP 검정', True),
    'ctrl_gate': ('CTRL_GATE_SPLIT_V1', 'MJF PA12S-HP 검정', True),
    'cover_L': ('COVER_L_DRAFT_TBD', '8001 레진 투명', True),
    'cover_T': ('COVER_T_DRAFT_TBD', '8001 레진 투명', True),
    'cover_R': ('COVER_R_DRAFT_TBD', '8001 레진 투명', True),
}
MJF_MAX = (370.0, 276.0, 360.0)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    raw = CACHE / 'print_v5_raw'
    raw.mkdir(parents=True, exist_ok=True)
    script = []
    for part, (body, _, _) in PARTS.items():
        script.append(dict(command='file.export_stl', params=dict(path=str(raw / f'{part}.stl'), bodies=[body], quality='fine')))
        script.append(dict(command='file.export_step', params=dict(path=str(OUT / f'46es_v5_{part}.step'), bodies=[body])))
    (CACHE / 'export_print_v5.json').write_text(json.dumps(script), encoding='utf-8')
    subprocess.run([CLI, 'run', str(CACHE / 'export_print_v5.json'), '--in', str(MODEL), '--quiet'], check=True)
    ev_path = CACHE / 'eval_v5_export.json'
    if not ev_path.exists() or ev_path.stat().st_mtime < MODEL.stat().st_mtime:
        subprocess.run([CLI, 'eval', '--in', str(MODEL), '--json-out', str(ev_path)], check=True, capture_output=True)
    bodies = {b['name']: b for b in json.loads(ev_path.read_text(encoding='utf-8'))['bodies']}
    records = []
    for part, (body, material, flip) in PARTS.items():
        stl = OUT / f'46es_v5_{part}.stl'
        orient(str(raw / f'{part}.stl'), str(stl), flip)
        m = check(str(stl))
        assert len(m['components']) == 1 and m['bad_edge_count'] == 0, (part, len(m['components']), m['bad_edge_count'])
        c = m['components'][0]
        cad = bodies[body]['volume_mm3']
        rel = abs(c['signed_volume'] - cad) / cad
        assert rel < 0.001, (part, rel)
        size = [c['bbox']['max'][k] - c['bbox']['min'][k] for k in range(3)]
        assert all(s <= lim for s, lim in zip(sorted(size[:2], reverse=True), MJF_MAX[:2])) and size[2] <= MJF_MAX[2], (part, size)
        assert abs(c['bbox']['min'][2]) < 1e-4, (part, c['bbox']['min'])
        records.append(dict(order='order2', file=stl.stem, body=body, material=material, print_flip_about_X=flip,
                            cad_volume_mm3=round(cad, 4), stl_triangles=m['triangles'], stl_components=1, stl_bad_edges=0,
                            stl_volume_mm3=round(c['signed_volume'], 4), stl_rel_volume_error=round(rel, 6),
                            print_bbox_mm=[round(s, 3) for s in size], bed_zmin=round(c['bbox']['min'][2], 4),
                            stl_sha256=sha(stl), step_sha256=sha(OUT / f'46es_v5_{part}.step')))
    record_path = ROOT / 'inspection/data/seam-v5-print-set.json'
    record_path.write_text(json.dumps(records, indent=1, ensure_ascii=False), encoding='utf-8')
    thin = ROOT / 'inspection/data/seam-v5-mjf-thin-wall.json'
    subprocess.run([sys.executable, '-I', str(ROOT / 'inspection/scripts/thin_wall_scan.py'), '--limit', '1.0', '--warn', '1.5',
                    '--json', str(thin), '--map', str(record_path), str(ev_path),
                    *[str(OUT / (r['file'] + '.stl')) for r in records]], check=True, capture_output=True)
    scan = {t['file']: t for t in json.loads(thin.read_text(encoding='utf-8'))['parts']}
    rows = []
    for r in records:
        t = scan[r['file']]
        rows.append(dict(file=r['file'], material=r['material'], volume_cm3=round(r['cad_volume_mm3'] / 1000, 2),
                         size=r['print_bbox_mm'], wall_min_mm=t['wall_min_mm'], min_mm=t['min_mm']))
    print(json.dumps(dict(ok=True, model_sha=sha(MODEL), parts=rows), indent=1, ensure_ascii=False))


if __name__ == '__main__':
    main()
