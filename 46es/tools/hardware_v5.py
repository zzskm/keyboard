"""Reference hardware drawn in the production CAD: M2 screws and nuts at the spine, M3 standoff screws and magnets,
PSD60 case screws. Hidden bodies for the guide and the clearance checks, never printed.

Moved out of model/seam_v5_base.json into code on 2026-11-10 (plan 4-5, step 3). The features are the base's, in
the same order and with the same expressions; they now run after the base timeline. Only their own features touch
these bodies, so every body's BRep stayed identical (build_seam_v5.py --refresh-record against the committed CAD).
The same day the base lost the REF_M2_LAP_1..4 chain (20 features) and MIN_V2_REMOVE_RING_AND_LAP_HARDWARE, which
created four lap screws with nuts and deleted them again.

Positions are the base's fixed numbers, some carrying the float noise of their v4 evaluation (6.494000000000001);
they are kept bit for bit. REF_M2_PLATE_1/2 (bracket B screws) come from ctrl_v5.
"""
import math

# M2 screws through the plate halves and the spine (spine_v5.SCREWS), nut under the spine: REF_M2_PLATE_3..6
SPINE_SCREWS = [(3, 126.381, 42.0), (4, 135.381, 42.0), (5, 121.881, 83.0), (6, 142.881, 83.0)]
SPINE_SCREW_L = 6
SPINE_NUT_Z, SPINE_NUT_H, SPINE_NUT_AF = 5.2, 1.6, 4
# M3 standoff screws (upper from the plate, lower from the case floor) and the magnet above each standoff
STANDOFFS = [(1, 6.494000000000001, 6.5200000000000005), (2, 6.494000000000001, 87.945), (3, 130.881, 87.945),
             (4, 250.42, 89.007), (5, 278.519, 6.5200000000000005), (6, 130.881, 6.5200000000000005)]
M3_UPPER_Z, M3_UPPER_L, M3_LOWER_L, M3_HEAD_H, M3_HEAD_R = 5.5, 4, 5, 1.65, 2.85
MAGNET_Z = 11.6
# PSD60 case screws H01..H06: (index, X, Y, shank bottom Z); H05 sits 1 mm higher
CASE_SCREWS = [(1, 25.1993, 66.6992, -3.0), (2, 128.2, 47.6, -3.0), (3, 190.4994, 9.3993, -3.0),
               (4, 260.0499, 66.6992, -3.0), (5, 3.70934, 38.0988, -2.0), (6, 281.29076, 38.0988, -3.0)]
CASE_SCREW_L, CASE_HEAD_H = 5, 1.3
Z_AXIS = [0.0, 0.0, 1.0]


def hex_sketch(x, y, across_flats):
    """Fixed hexagon with a vertex on +X, point ids as the app writes a closed polyline."""
    r = across_flats / math.sqrt(3)
    ids = ['l1.start'] + [f'l{i}.end' for i in range(1, 6)]
    points = [dict(fixed=True, id='origin', pos=[0.0, 0.0])]
    points += [dict(fixed=False, id=ids[i], pos=[x + r * math.cos(math.radians(60 * i)), y + r * math.sin(math.radians(60 * i))])
               for i in range(6)]
    curves = [dict(a=i, b=i % 6 + 1, construction=False, fixed=True, id=f'l{i}', type='line') for i in range(1, 7)]
    return dict(constraints=[], counters=dict(l=6), curves=curves, points=points)


def emit(feature):
    """Append the reference hardware to the timeline through build_seam_v5.helpers' feature()."""
    def screw(name, x, y, z, length, radius, head_z, head_h, head_r):
        feature('cylinder', name, axis=Z_AXIS, base=[x, y, z], body_names=[name], height=str(length),
                operation='new_body', radius=radius)
        feature('cylinder', f'{name}_HEAD_JOIN', axis=Z_AXIS, base=[x, y, head_z], height=head_h, operation='join',
                participants=[name], radius=head_r)

    for i, x, y in SPINE_SCREWS:
        name = f'REF_M2_PLATE_{i}'
        screw(name, x, y, f'split_M2_plate_seat_Z-{SPINE_SCREW_L}', SPINE_SCREW_L, '(2 mm) / 2',
              'split_M2_plate_seat_Z', '1.1', '(4 mm) / 2')
        sk = feature('sketch', f'{name}_NUT_SK', sketch=hex_sketch(x, y, SPINE_NUT_AF),
                     plane=dict(base=dict(name='XY', type='origin'), distance=str(SPINE_NUT_Z), type='offset'))
        feature('extrude', f'{name}_NUT_HEX', body_names=[f'{name}_NUT'], operation='new_body', profiles=dict(type='all'),
                extent=dict(convention='total_distance', direction='positive', distance=str(SPINE_NUT_H)), sketch=sk)
        feature('cylinder', f'{name}_NUT_THREAD_VOID', axis=Z_AXIS, base=[x, y, SPINE_NUT_Z - 0.2], height='2',
                operation='cut', participants=[f'{name}_NUT'], radius='(2 mm) / 2')
    for i, x, y in STANDOFFS:
        screw(f'REF_SO{i}_M3_UPPER', x, y, M3_UPPER_Z, M3_UPPER_L, '(3 mm) / 2',
              M3_UPPER_Z + M3_UPPER_L, str(M3_HEAD_H), str(M3_HEAD_R))
        screw(f'REF_SO{i}_M3_LOWER', x, y, 0.0, M3_LOWER_L, '(3 mm) / 2', -M3_HEAD_H, str(M3_HEAD_H), str(M3_HEAD_R))
        feature('cylinder', f'REF_SO{i}_MAGNET', axis=Z_AXIS, base=[x, y, MAGNET_Z], body_names=[f'REF_SO{i}_MAGNET'],
                height='TBD_magnet_T', operation='new_body', radius='TBD_magnet_D / 2')
    for i, x, y, z in CASE_SCREWS:
        screw(f'REF_CASE_H{i:02d}_M2', x, y, z, CASE_SCREW_L, '(2 mm) / 2', z + CASE_SCREW_L, str(CASE_HEAD_H),
              '(3.8 mm) / 2')
