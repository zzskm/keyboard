"""Validate the measured case proxy, OEM/MX placement and preserved print CAD."""
import hashlib
import json
import math
from pathlib import Path
import subprocess

from verify_minimal_v2 import live_shapes

ROOT = Path(__file__).resolve().parents[2]
CLI = 'C:/Program Files/SolidCraft/solidcraft-cli.exe'


def main():
    manifest = json.loads((ROOT / 'model/assembly_reference.json').read_text(encoding='utf-8'))
    report = ROOT / 'guide/.cache/reference/eval.json'
    model = ROOT / 'model/46es_assembly_review.sc'
    assert hashlib.sha256(model.read_bytes()).hexdigest() == manifest['output_sha']
    assert hashlib.sha256((ROOT / 'model/46es_mount_seam_v4.sc').read_bytes()).hexdigest() == manifest['source_sha']
    # The generator already evaluates the just-written model. Reuse that report
    # while it is current; regenerate it when running this check without the cache.
    if not report.exists() or report.stat().st_mtime < model.stat().st_mtime:
        subprocess.run([CLI, 'eval', '--in', str(model), '--json-out', str(report)],
                       check=True, capture_output=True)
    ev = json.loads(report.read_text(encoding='utf-8'))
    assert not [f for f in ev['timeline'] if f.get('error')]
    bodies = {b['name']: b for b in ev['bodies']}
    for prefix, count in [('REF_MX_LOWER',46), ('REF_MX_GUIDE',138), ('REF_MX_UPPER',46), ('REF_MX_STEM',46),
                          ('REF_MX_CONTACT',92), ('REF_KEYCAP_OEM_',46)]:
        selected = [b for n,b in bodies.items() if n.startswith(prefix)]
        assert len(selected) == count, (prefix,len(selected))
        assert all(b['closed'] for b in selected), prefix
    params = {p['name']: p['value'] for p in ev['params']}
    for name, value in [('in_W',286),('in_D',96),('support_H',5.5),('rim_F',14),('rim_B',14),
                        ('out_W',320),('out_D',115)]:
        assert abs(params['REF_PSD_'+name]-value) < 1e-6, name
    case = bodies['REF_HOUSING_PSD60_MEASURED']['bbox']
    assert abs(case['max'][0]-case['min'][0]-320) < 1e-6
    assert abs(case['max'][1]-case['min'][1]-115) < 1e-6
    assert abs(case['max'][2]-14) < 1e-6
    cover_top = max(bodies[n]['bbox']['max'][2] for n in bodies if n.startswith('COVER_'))
    assert abs(cover_top-15) < 1e-6
    # Explicit cap names bind width/rotation/profile to the original key centers.
    for i,k in enumerate(manifest['keys'],1):
        assert k['oem_row'] in (1,2,3,4,5)
        b = bodies[f'REF_KEYCAP_OEM_{i:02}']['bbox']
        assert abs(b['min'][2]-15.2) < .01
        assert b['max'][2] > 23
        a = math.radians(k['rot'])
        expected_x = (18.05+(k['w_u']-1)*19.05)*abs(math.cos(a)) + 18.05*abs(math.sin(a))
        assert abs(b['max'][0]-b['min'][0]-expected_x) < .01, i
    # Compare native BRep records, not just approximate volumes or output meshes.
    old = live_shapes(ROOT / 'model/46es_mount_seam_v4.sc')
    new = live_shapes(ROOT / 'model/46es_assembly_review.sc')
    spec = json.loads((ROOT / 'guide/guide_v4.json').read_text(encoding='utf-8'))
    printed = next(s for s in spec['sections'] if s['type']=='parts')['printed']
    unchanged = [p['bodies'][0] for p in printed]
    assert all(old[n] == new[n] for n in unchanged), 'production CAD changed'
    result = dict(ok=True, preserved_printed_bodies=len(unchanged), switches=46, keycaps=46,
                  case_inner_mm=[286,96], support_to_rim_mm=[14,14], cover_above_rim_mm=round(cover_top-14,6),
                  approximate_right_edge_overlap_mm=round(bodies['PLATE_R_SPLIT_V1']['bbox']['max'][0]-(286-.693),6),
                  source_sha=manifest['source_sha'], model_sha=manifest['output_sha'])
    (ROOT / 'inspection/data/assembly-reference-verification.json').write_text(
        json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
