"""Validate the v5 assembly review model: case reference kept, two-level cover above the rim (base +2.1, collar
+5.0), keycap clearance at rest and pressed 4 mm (cover windows, case inner wall), pressed cap vs plate top
(0.3), CASE_V5 design requirement vs measured PSD60.

Run from the repository: python -B inspection/scripts/verify_assembly_reference_v5.py
Writes inspection/data/assembly-reference-v5-verification.json.
"""
import hashlib
import json
import math
from pathlib import Path
import subprocess
import sys

from verify_minimal_v2 import live_shapes

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
from build_seam_v5 import top_levels  # noqa: E402

CLI = 'C:/Program Files/SolidCraft/solidcraft-cli.exe'
MODEL = ROOT / 'model/46es_assembly_review_v5.sc'
SOURCE = ROOT / 'model/46es_mount_seam_v5.sc'
CACHE = ROOT / 'guide/.cache/reference_v5'
COVERS = ['COVER_L_DRAFT_TBD', 'COVER_T_DRAFT_TBD', 'COVER_R_DRAFT_TBD']
HOUSING = 'REF_HOUSING_PSD60_MEASURED'
PLATES = ['PLATE_L_SPLIT_V1', 'PLATE_R_SPLIT_V1']
CAPS = [f'REF_KEYCAP_OEM_{i:02}' for i in range(1, 47)]
PRESS = 4.0
TARGET = 1.0            # keycap <-> cover (rest and pressed)
TARGET_CASE = 2.6       # keycap <-> case inner wall (plan §4)
TARGET_PLATE = 0.25     # pressed 4 mm keycap bottom <-> plate top (expected 0.3 = seat + 6.0 - 4 - 13 + ...)
TOL = 1e-4


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def per_key(result, bodies_from, suffix=''):
    """Smallest distance of each keycap to the cover pieces and to the case, from inspect.clearance near/nearest."""
    out = {}
    for n in result['near']:
        cap, other = (n['a'], n['b']) if n['a'].startswith('REF_KEYCAP') else (n['b'], n['a'])
        i = int(cap.replace(suffix, '')[-2:])
        kind = 'case' if other == HOUSING else 'cover'
        cur = out.setdefault(i, {})
        if n['distance_mm'] < cur.get(kind, (1e9,))[0]:
            cur[kind] = (n['distance_mm'], other, [round(v, 2) for v in n['from']])
    return out


def main():
    manifest = json.loads((ROOT / 'model/assembly_reference_v5.json').read_text(encoding='utf-8'))
    assert sha(MODEL) == manifest['output_sha'] and sha(SOURCE) == manifest['source_sha'], 'stale review model'
    report = CACHE / 'eval.json'
    if not report.exists() or report.stat().st_mtime < MODEL.stat().st_mtime:
        subprocess.run([CLI, 'eval', '--in', str(MODEL), '--json-out', str(report)], check=True, capture_output=True)
    ev = json.loads(report.read_text(encoding='utf-8'))
    assert not [f for f in ev['timeline'] if f.get('error')]
    bodies = {b['name']: b for b in ev['bodies']}
    for prefix, count in [('REF_MX_LOWER', 46), ('REF_MX_GUIDE', 138), ('REF_MX_UPPER', 46), ('REF_MX_STEM', 46),
                          ('REF_MX_CONTACT', 92), ('REF_KEYCAP_OEM_', 46), ('REF_LEGMAG_', 4)]:
        selected = [b for n, b in bodies.items() if n.startswith(prefix)]
        assert len(selected) == count and all(b['closed'] for b in selected), prefix
    params = {p['name']: p['value'] for p in ev['params'] if p.get('value') is not None}
    # measured reference kept exactly as in the v4 review model
    for name, value in [('in_W', 286), ('in_D', 96), ('support_H', 5.5), ('rim_F', 14), ('rim_B', 14),
                        ('out_W', 320), ('out_D', 115), ('post_D', 5)]:
        assert abs(params['REF_PSD_' + name] - value) < 1e-6, name
    case = bodies[HOUSING]['bbox']
    rim = case['max'][2]
    assert abs(rim - 14) < 1e-6
    # two-level cover: collar top from the body boxes, base level from the upward faces of the covers
    cover_top = max(bodies[n]['bbox']['max'][2] for n in COVERS)
    assert all(abs(bodies[n]['bbox']['max'][2] - cover_top) < 1e-6 for n in COVERS)
    protrusion = cover_top - rim
    assert abs(protrusion - params['v5_cover_top_above_rim']) < 1e-6 and abs(protrusion - 5.0) < 1e-6, protrusion
    cover_base = params['v5_cover_base_Z']
    base_above_rim = cover_base - rim
    assert abs(base_above_rim - params['v5_cover_base_above_rim']) < 1e-6 and abs(base_above_rim - 2.1) < 1e-6, base_above_rim
    levels = top_levels(MODEL)
    for n, lv in levels.items():
        assert set(lv) == {round(cover_base, 4), round(cover_top, 4)}, (n, lv)
    design = {k: round(params['CASE_V5_' + k], 3) for k in
              ('rim_Z', 'in_W_design', 'in_W_min', 'in_D_design', 'in_D_min', 'keycap_wall_min')}
    # production bodies identical to the v5 source
    old, new = live_shapes(SOURCE), live_shapes(MODEL)
    common = [n for n in old if n in new]
    # the generator replaces the Wilmore stand-in and suppresses the old switch placeholders (features 242-244)
    gone = set(old) - set(new)
    assert gone == {'REF_HOUSING_WILMORE_NOT_PSD60'} | {n for n in old if n.startswith('REF_SW_ASSUMED_')}, gone
    assert all(old[n] == new[n] for n in common), 'production CAD changed in the review copy'

    script = [dict(command='inspect.clearance', params=dict(bodies=CAPS, against=COVERS + [HOUSING], clearance=3, nearest=2)),
              dict(command='inspect.clearance', params=dict(bodies=CAPS, against=PLATES, clearance=6, nearest=1)),
              dict(command='solid.move', params=dict(bodies=CAPS, translate=[0, 0, -PRESS], copy=True)),
              dict(command='inspect.clearance', params=dict(bodies=[c + ' (2)' for c in CAPS], against=COVERS + [HOUSING],
                                                          clearance=3, nearest=2)),
              dict(command='inspect.clearance', params=dict(bodies=[c + ' (2)' for c in CAPS], against=PLATES, clearance=2, nearest=1))]
    (CACHE / 'keycap_check.json').write_text(json.dumps(script), encoding='utf-8')
    out = CACHE / 'keycap_check_out.json'
    subprocess.run([CLI, 'run', str(CACHE / 'keycap_check.json'), '--in', str(MODEL), '--results', '--json-out', str(out)],
                   check=True, capture_output=True)
    rest, rest_plate, moved, pressed, pressed_plate = json.loads(out.read_text(encoding='utf-8'))
    assert len(moved['bodies']) >= 46
    states = {}
    for label, res, suffix in [('rest', rest, ''), ('pressed_4mm', pressed, ' (2)')]:
        assert res['overlaps'] == [] and res['unchecked'] == [], (label, res['overlaps'])
        keys = per_key(res, CAPS, suffix)
        cover_min = min(v['cover'][0] for v in keys.values() if 'cover' in v)
        case_near = [v['case'][0] for v in keys.values() if 'case' in v]
        states[label] = dict(
            cover_min_mm=round(cover_min, 4), keys_within_3mm_of_cover=len([k for k in keys.values() if 'cover' in k]),
            case_min_mm=round(min(case_near), 4) if case_near else None,
            closest=sorted(([i, round(v['cover'][0], 3), v['cover'][1]] for i, v in keys.items() if 'cover' in v),
                           key=lambda x: x[1])[:8])
        assert cover_min >= TARGET - TOL, (label, cover_min)
        assert not case_near or min(case_near) >= TARGET_CASE - TOL, (label, case_near)
    # pressed 4 mm: the cap bottom must stay above the plate top (real check since the 2nd pass; was excluded before)
    assert rest_plate['overlaps'] == [] and pressed_plate['overlaps'] == [] and pressed_plate['unchecked'] == [], pressed_plate['overlaps']
    plate_dist = [n['distance_mm'] for n in pressed_plate['near']]
    assert len(plate_dist) >= 46, len(plate_dist)
    plate_min = min(plate_dist)
    assert plate_min >= TARGET_PLATE - TOL, plate_min
    lowest_cap = min(bodies[c]['bbox']['min'][2] for c in CAPS)
    plate_top = max(bodies[p]['bbox']['max'][2] for p in PLATES)
    assert abs(lowest_cap - manifest['keycap_bottom_rest_Z']) < 1e-6 and abs(lowest_cap - params['v5_keycap_bottom_rest_Z']) < 1e-6
    assert abs(plate_min - (lowest_cap - PRESS - plate_top)) < 1e-3, (plate_min, lowest_cap - PRESS - plate_top)
    right_edge = max(bodies[p]['bbox']['max'][0] for p in PLATES + COVERS)
    result = dict(
        ok=True, model_sha=manifest['output_sha'], source_sha=manifest['source_sha'],
        rim_Z=rim, cover_top_Z=cover_top, cover_above_rim_mm=round(protrusion, 6),
        cover_base_Z=cover_base, cover_base_above_rim_mm=round(base_above_rim, 6),
        cover_levels={n: {str(z): a for z, a in lv.items()} for n, lv in levels.items()},
        keycap=dict(target_mm=TARGET, case_target_mm=TARGET_CASE, press_mm=PRESS, **states,
                    cap_bottom_rest_Z=round(lowest_cap, 3), cap_bottom_above_seat_mm=manifest['keycap_bottom_above_seat'],
                    cap_bottom_above_rim_mm=round(lowest_cap - rim, 3),
                    skirt_cover_rest_mm=round(cover_top - lowest_cap, 3),
                    skirt_cover_pressed_mm=round(cover_top - (lowest_cap - PRESS), 3),
                    note='Clearance measured on exact faces: flat OEM reference caps (actual widths, rotations) '
                         'against the three cover pieces and the measured PSD60 case. Cap skirt bottom at rest = switch '
                         'seat + 6.0 (r2 based; to be confirmed by the r2 measurement, plan §11-1).'),
        pressed_vs_plate=dict(
            overlapping_caps=0, min_distance_mm=round(plate_min, 4), target_mm=TARGET_PLATE,
            cap_bottom_rest_Z=round(lowest_cap, 3), plate_top_Z=plate_top,
            travel_to_plate_mm=round(lowest_cap - plate_top, 3),
            note=(f'Reference caps: bottom Z {lowest_cap:.2f} = seat Z {manifest["switch_seat_Z"]:.2f} + {manifest["keycap_bottom_above_seat"]:.1f} '
                  f'(r2 based: on a 2T upper plate a fully pressed cap has almost no play -> about seat + 2 at bottom-out, '
                  f'about seat + 6 at rest). Pressed 4 mm they stop {plate_min:.2f} above the plate top (Z {plate_top:.0f}); '
                  f'v5 upper layer 1.7 provides that 0.3 over r2. Real check since the 2nd pass (2026-11-06).')),
        case=dict(measured=dict(in_W=params['REF_PSD_in_W'], in_D=params['REF_PSD_in_D'], rim=params['REF_PSD_rim_F']),
                  v5_design=design,
                  right_edge_X=right_edge, wall_X=round(params['REF_PSD_in_W'] - params['REF_PSD_pcb0_dx'], 3),
                  right_edge_overlap_mm=round(right_edge - (params['REF_PSD_in_W'] - params['REF_PSD_pcb0_dx']), 3),
                  centred_gap_each_side_mm=round((params['REF_PSD_in_W'] - design['in_W_min']) / 2, 3),
                  depth_gap_each_side_mm=round((params['REF_PSD_in_D'] - design['in_D_min']) / 2, 3)),
    )
    (ROOT / 'inspection/data/assembly-reference-v5-verification.json').write_text(
        json.dumps(result, indent=2, ensure_ascii=False), encoding='utf-8')
    print(json.dumps(result, indent=1, ensure_ascii=False))


if __name__ == '__main__':
    main()
