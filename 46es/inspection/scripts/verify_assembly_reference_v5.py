"""Verify cover and controller placement in the v5 assembly reference."""
import json
import math
from pathlib import Path
import subprocess
import sys

from cad_model import live_shapes

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
from build_seam_v5 import MOUNT_PIN_CLEARANCE, PLATE_SUPPORT_MOUNTS, REAR_BOSS_X, REAR_FEET, top_levels  # noqa: E402
import ctrl_v5  # noqa: E402
BRACKET = ctrl_v5.BODY

from common import CLI, sha, write_json  # noqa: E402
MODEL = ROOT / 'model/46es_assembly_review_v5.sc'
SOURCE = ROOT / 'model/46es_mount_seam_v5.sc'
CACHE = ROOT / 'guide/.cache/reference_v5'
COVERS = ['COVER_L_DRAFT_TBD', 'COVER_T_DRAFT_TBD', 'COVER_R_DRAFT_TBD']
HOUSING = 'REF_HOUSING_PSD60_MEASURED'
BOSSES = [f'REF_PSD_REAR_BOSS_{i}' for i in range(1, len(REAR_BOSS_X) + 1)]   # photo estimates, assumed top Z 0
PLATES = ['PLATE_L_SPLIT_V1', 'PLATE_R_SPLIT_V1']
CAPS = [f'REF_KEYCAP_OEM_{i:02}' for i in range(1, 47)]
PRESS = 4.0
TARGET = 1.0            # keycap <-> cover (rest and pressed)
TARGET_CASE = 2.6       # keycap <-> case inner wall (plan §4)
TARGET_PLATE = 0.25     # pressed 4 mm keycap bottom <-> plate top (expected 0.3 = seat + 6.0 - 4 - 13 + ...)
TOL = 1e-4


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
                          ('REF_MX_CONTACT', 92), ('REF_KEYCAP_OEM_', 46), ('REF_LEGMAG_', 4), ('REF_PSD_REAR_BOSS_', 4)]:
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
    # Confirm all three cover top faces share the same plane.
    cover_top = max(bodies[n]['bbox']['max'][2] for n in COVERS)
    assert all(abs(bodies[n]['bbox']['max'][2] - cover_top) < 1e-6 for n in COVERS)
    protrusion = cover_top - rim
    assert abs(protrusion - params['v5_cover_top_above_rim']) < 1e-6 and abs(protrusion - 5.0) < 1e-6, protrusion
    levels = top_levels(MODEL)
    for n, lv in levels.items():
        assert set(lv) == {round(cover_top, 4)}, (n, lv)
    design = {k: round(params['CASE_V5_' + k], 3) for k in
              ('rim_Z', 'in_W_design', 'in_W_min', 'in_D_design', 'in_D_min', 'keycap_wall_min')}
    # production bodies identical to the v5 source
    old, new = live_shapes(SOURCE), live_shapes(MODEL)
    common = [n for n in old if n in new]
    # the production model already drops the Wilmore stand-in and the old switch placeholders (features 242-244)
    gone = set(old) - set(new)
    assert gone == set(), gone
    assert all(old[n] == new[n] for n in common), 'production CAD changed in the review copy'

    controller = [name for name in bodies if name.startswith('REF_PROMICRO_')]
    pcb = bodies['REF_PROMICRO_PCB']['bbox']
    assert all(bodies[name]['closed'] for name in controller)
    assert all(abs(pcb['min'][i] - params['TBD_ctrl_' + axis]) < TOL and
               abs(pcb['max'][i] - pcb['min'][i] - params['TBD_ctrl_' + size]) < TOL
               for i, (axis, size) in enumerate([('X', 'L'), ('Y', 'W')]))
    for face, bound in [('COMPONENT', 'min'), ('SOLDER', 'max')]:
        pads = [bodies[name] for name in controller if name.startswith(f'REF_PROMICRO_PADS_{face}_')]
        assert len(pads) == 24, (face, len(pads))
        plane = params['TBD_ctrl_pcb_Z'] + (params['REF_ctrl_pcb_T'] if face == 'SOLDER' else 0)
        assert all(abs(pad['bbox'][bound][2] - plane) < TOL for pad in pads), face
        for pad in pads:
            lo, hi = pad['bbox']['min'], pad['bbox']['max']
            disc_volume = math.pi * ((hi[0] - lo[0]) / 2)**2 * (hi[2] - lo[2])
            assert pad['volume_mm3'] < 0.8 * disc_volume, pad['name']
    # the reference board is drawn from tools/ctrl_v5.py; its evaluated bodies sit where the bracket checks assume
    frame = ctrl_v5.frame()
    for name, ((x, y), (length, width), depth) in ctrl_v5.COMPONENTS.items():
        box = bodies[f'REF_PROMICRO_{name}']['bbox']
        assert all(abs(a - b) < TOL for a, b in zip(box['min'][:2] + box['max'][:2],
                   (frame['x0'] + x, frame['y0'] + y, frame['x0'] + x + length, frame['y0'] + y + width))), name
        assert abs(box['min'][2] - (frame['zc'] - depth)) < TOL, name
    centers = sorted((round((b['bbox']['min'][0] + b['bbox']['max'][0]) / 2, 4), round((b['bbox']['min'][1] + b['bbox']['max'][1]) / 2, 4))
                     for n, b in bodies.items() if n.startswith('REF_PROMICRO_PADS_COMPONENT_'))
    expected = sorted((round(p['center'][0], 4), round(p['center'][1], 4)) for p in ctrl_v5.pads())
    assert len(centers) == len(expected) == 24
    assert all(abs(a[0] - b[0]) < 1e-3 and abs(a[1] - b[1]) < 1e-3 for a, b in zip(centers, expected)), 'pad layout'
    assert bodies['REF_PROMICRO_USB']['bbox']['min'][0] < pcb['min'][0]
    assert bodies['REF_PROMICRO_MCU']['bbox']['min'][2] < pcb['min'][2]

    script = [dict(command='inspect.clearance', params=dict(bodies=CAPS, against=COVERS + [HOUSING], clearance=3, nearest=2)),
              dict(command='inspect.clearance', params=dict(bodies=CAPS, against=PLATES, clearance=6, nearest=1)),
              dict(command='solid.move', params=dict(bodies=CAPS, translate=[0, 0, -PRESS], copy=True)),
              dict(command='inspect.clearance', params=dict(bodies=[c + ' (2)' for c in CAPS], against=COVERS + [HOUSING],
                                                          clearance=3, nearest=2)),
              dict(command='inspect.clearance', params=dict(bodies=[c + ' (2)' for c in CAPS], against=PLATES, clearance=2, nearest=1))]
    script.append(dict(command='inspect.clearance', params=dict(
        bodies=controller, against=[BRACKET], clearance=0.1, min_volume=0.000001)))
    mounts = sorted(PLATE_SUPPORT_MOUNTS)
    pins = [n for n in bodies if n.startswith(('REF_MX_GUIDE', 'REF_MX_CONTACT'))]
    pin_search_radius = 1.0
    script.extend(dict(command='inspect.clearance', params=dict(
        bodies=[mount], against=pins, clearance=pin_search_radius, min_volume=0.000001))
        for mount in mounts)
    # The production clearance pass uses the legacy case stand-in. Check the
    # mounts against the measured PSD60 proxy and the populated review model.
    mount_obstacles = [HOUSING, *BOSSES, *controller,
                       *[n for n in bodies if n.startswith('REF_MX_LOWER')]]
    script.append(dict(command='inspect.clearance', params=dict(
        bodies=mounts, against=mount_obstacles, min_volume=0.000001)))
    # Switch legs that reach the Pro Micro: the K1 +x and K23 -x PCB pegs of the 5-pin switches overlap the board's
    # back corners (they are clipped in assembly, tools/ctrl_v5.py CLIPPED_PEGS). Everything else must clear the
    # board, and the bracket must clear every switch part except those two pegs, and the case.
    switch_parts = [n for n in bodies if n.startswith(('REF_MX_LOWER', 'REF_MX_GUIDE', 'REF_MX_CONTACT'))]
    script.append(dict(command='inspect.clearance', params=dict(
        bodies=['REF_PROMICRO_PCB'], against=switch_parts, min_volume=0.000001)))
    script.append(dict(command='inspect.clearance', params=dict(
        bodies=[BRACKET], against=switch_parts + [HOUSING], clearance=0.3, min_volume=0.000001)))
    # Rear feet over the rear-wall bosses: no overlap, and each foot's nearest boss is its own at the design gap.
    script.append(dict(command='inspect.clearance', params=dict(
        bodies=PLATES, against=BOSSES, clearance=1.0, min_volume=0.000001)))
    # Mounts on the bosses (touching is reported as a near pair at distance 0; overlaps fail mount_fit above).
    script.append(dict(command='inspect.clearance', params=dict(
        bodies=mounts, against=BOSSES, clearance=1.0, min_volume=0.000001)))
    write_json(CACHE / 'keycap_check.json', script, indent=None)
    out = CACHE / 'keycap_check_out.json'
    subprocess.run([CLI, 'run', str(CACHE / 'keycap_check.json'), '--in', str(MODEL), '--results', '--json-out', str(out)],
                   check=True, capture_output=True)
    rest, rest_plate, moved, pressed, pressed_plate, controller_fit, *mount_checks = json.loads(out.read_text(encoding='utf-8'))
    *pin_checks, mount_fit, peg_fit, bracket_fit, feet_fit, boss_mounts = mount_checks
    pcb_box = bodies['REF_PROMICRO_PCB']['bbox']

    def corner_peg(name):
        lo, hi = bodies[name]['bbox']['min'], bodies[name]['bbox']['max']
        return name.startswith('REF_MX_GUIDE') and hi[0] - lo[0] < 2.0 and lo[1] > pcb_box['max'][1] - 1.5
    pegs = sorted({n for o in peg_fit['overlaps'] for n in (o['a'], o['b']) if n != 'REF_PROMICRO_PCB'})
    assert len(pegs) == 2 and all(corner_peg(n) for n in pegs), peg_fit['overlaps']
    assert not peg_fit['unchecked'], peg_fit
    peg_overlap = {n: dict(x=[round(bodies[n]['bbox']['min'][0], 2), round(bodies[n]['bbox']['max'][0], 2)],
                           tip_Z=round(bodies[n]['bbox']['min'][2], 3),
                           depth_into_pcb_mm=round(pcb_box['max'][2] - bodies[n]['bbox']['min'][2], 3)) for n in pegs}
    bracket_hits = [o for o in bracket_fit['overlaps'] if not ({o['a'], o['b']} & set(pegs))]
    assert not bracket_hits and not bracket_fit['unchecked'], bracket_hits
    bracket_near = sorted(((n['distance_mm'], n['b'] if n['a'] == BRACKET else n['a']) for n in bracket_fit['near']
                           if not ({n['a'], n['b']} & set(pegs))), key=lambda x: x[0])[:5]
    assert len(pin_checks) == len(mounts)
    assert not mount_fit['overlaps'] and not mount_fit['unchecked'], mount_fit
    pin_fit = {}
    for mount, result in zip(mounts, pin_checks):
        assert not result['overlaps'] and not result['unchecked'], (mount, result)
        closest = min(result['near'], key=lambda pair: pair['distance_mm'], default=None)
        distance = closest['distance_mm'] if closest else pin_search_radius
        assert distance >= MOUNT_PIN_CLEARANCE - TOL, (mount, closest)
        reference = None
        if closest:
            reference = closest['b'] if closest['a'] == mount else closest['a']
        pin_fit[mount] = dict(pairs_checked=result['pairs_checked'],
                              min_distance_mm=round(distance, 4) if closest else None,
                              closest_reference=reference)
    assert len(moved['bodies']) >= 46
    assert not controller_fit['overlaps'] and not controller_fit['unchecked'], controller_fit
    assert not feet_fit['overlaps'] and not feet_fit['unchecked'], feet_fit
    gap = params['v5_rear_foot_gap']
    feet = {}
    for i, (_, plate) in REAR_FEET.items():
        boss = BOSSES[i - 1]
        near = [n['distance_mm'] for n in feet_fit['near'] if {n['a'], n['b']} == {plate, boss}]
        assert near and abs(min(near) - gap) < 1e-3, (i, near, gap)
        feet[i] = dict(plate=plate, boss=boss, gap_mm=round(min(near), 4))
    unfooted = [b for b in BOSSES if b not in {BOSSES[i - 1] for i in REAR_FEET}]
    assert not [n for n in feet_fit['near'] if {n['a'], n['b']} & set(unfooted)], 'a plate reaches a boss without a foot'
    assert not boss_mounts['overlaps'] and not boss_mounts['unchecked'], boss_mounts
    boss_contacts = sorted((round(n['distance_mm'], 4), *sorted((n['a'], n['b']))) for n in boss_mounts['near'])
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
        controller=dict(bodies=len(controller), pads_per_face=24, socket_side='-X',
                        component_face='-Z', solder_face='+Z', bracket_overlap_count=0,
                        switch_pegs_into_pcb=peg_overlap,
                        bracket_switch_case_min=[[round(d, 3), n] for d, n in bracket_near],
                        note='The two corner pegs (K1 +x, K23 -x) are clipped in assembly; the bracket is checked '
                             'against every other switch part and the case with a 0.3 mm search radius.'),
        ok=True,
        mount_review_fit=dict(overlaps=0, unchecked=0, pairs_checked=mount_fit['pairs_checked'],
                              rear_boss_within_1mm=[list(c) for c in boss_contacts]),
        rear_feet=dict(gap_target_mm=gap, feet=feet, bosses_without_foot=unfooted,
                       note='Boss X, diameter and top are photo estimates / an assumption (M22, not measured); the gap '
                            'is filled with a shim or pad at trial assembly.'),
        mount_switch_pin_fit=dict(target_mm=MOUNT_PIN_CLEARANCE, search_radius_mm=pin_search_radius,
                                  mounts=pin_fit),
        model_sha=manifest['output_sha'], source_sha=manifest['source_sha'],
        rim_Z=rim, cover_top_Z=cover_top, cover_above_rim_mm=round(protrusion, 6),
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
    write_json(ROOT / 'inspection/data/assembly-reference-v5-verification.json', result, indent=2)
    print(json.dumps(result, indent=1, ensure_ascii=False))


if __name__ == '__main__':
    main()
