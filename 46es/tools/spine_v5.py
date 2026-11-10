"""The seam spine (PLATE_SPINE_V1): the MJF bar under the plate seam that four M2 screws clamp to both plate halves.

Moved out of model/seam_v5_base.json into code on 2026-11-10 (plan 4-5, step 2). The features are the base's, in the
same order and with the same expressions; they now run after the base timeline instead of between the plate features.
The spine is only ever touched by its own features, so its BRep, and every other body's, stayed identical (checked
with build_seam_v5.py --probe against the committed CAD and the order-2 export hashes).

What stays in the base: the plate side of the joint (the seats PLATE_SPINE_*_SEAT and the M2 clearance/head holes
SPINE_M2_*_CLEAR/_HEAD cut into the plates). SPINE_M2_1/2_CLEAR used to cut the plates and the spine in one feature;
the base keeps the plate cut and the spine gets SPINE_M2_1/2_SPINE_CLEAR here, as screws 3 and 4 already had.

Plan positions are fixed numbers, as in the base. They sit on split_center_X 130.881 (asserted after evaluation by
check()); the expressions follow the parameters for sizes and heights only.
"""
import math

BODY = 'PLATE_SPINE_V1'
CENTER_X = 130.881                    # split_center_X (REF_SO_dX6 - TBD_pcb0_dx) the fixed positions below are drawn on
STEM_Y0, STEM_W = 42.0, 41            # stem from the front screw pair to the rear pads
FRONT_PAD = (-9, 38.0, 18, 8)         # (dX from centre, Y, length X, width Y) of the pads under the plate seats
REAR_PAD = (-15, 79.0, 30, 8)
PAD_Z = 5.0
# Switch housing guards: the spine is trimmed where switches 1 and 23 (rotated thumb blocks) hang below the plate.
SWITCH_GUARDS = {
    'SK_SPINE_SWITCH_GUARD_1': [(103.25533828024227, 43.138860540007535), (121.41544117402405, 39.60889412554139),
                                (124.9454075884902, 57.76899701932316), (106.78530469470842, 61.298963433789304)],
    'SK_SPINE_SWITCH_GUARD_23': [(140.34754741313074, 39.60889412554141), (158.5076503069125, 43.138860540007514),
                                 (154.97768389244638, 61.29896343378928), (136.81758099866462, 57.76899701932318)],
}
GUARD_Z, GUARD_H = 3, 7
SO3_RELIEF_D = 6.8                    # around the SO3 standoff below the spine
# M2 screws through plate and spine, nut under the spine: (name, X, Y, spine clearance feature height)
SCREWS = [('SPINE_M2_1', 126.381, 42.0, 10), ('SPINE_M2_2', 135.381, 42.0, 10),
          ('SPINE_M2_3', 121.881, 83.0, 5), ('SPINE_M2_4', 142.881, 83.0, 5)]
SCREW_Z = 4.0
NUT_Z = 5
NUT_AF = 4.4                          # split_nut_AF (M2 nut across flats 4 + clearance); only for the stored pos
WIRE_NOTCH_Y = (49, 64, 72)           # wiring grooves across the spine bottom
WIRE_NOTCH_L = 6
# MJF: open the nut 4 pocket to the spine edge so the pocket has no 0.3 mm skin (MJF 2026-11-06)
NUT4_OPEN = dict(corner=[144.2, 81.9, 4.9], length='2.3', width='2.2', height='1.9')


def plane(z):
    return dict(base=dict(name='XY', type='origin'), distance=str(z), type='offset')


def polygon_sketch(points):
    pts = [dict(fixed=True, id='origin', pos=[0.0, 0.0])]
    pts += [dict(fixed=False, id=f'p{i}', pos=[x, y]) for i, (x, y) in enumerate(points, 1)]
    n = len(points)
    curves = [dict(a=i, b=i % n + 1, construction=False, fixed=True, id=f'l{i}', type='line') for i in range(1, n + 1)]
    return dict(constraints=[], counters=dict(l=n), curves=curves, points=pts)


def hex_sketch(x, y):
    """Hex nut pocket, across flats split_nut_AF, corners follow the parameter."""
    pts = [dict(fixed=True, id='origin', pos=[0.0, 0.0])]
    for i in range(6):
        a = 60 * i
        pts.append(dict(exprs=dict(x=f'{x:g}+split_nut_AF/sqrt(3)*cos({a} deg)', y=f'{y:g}+split_nut_AF/sqrt(3)*sin({a} deg)'),
                        fixed=True, id=f'p{i + 1}',
                        pos=[x + NUT_AF / math.sqrt(3) * math.cos(math.radians(a)), y + NUT_AF / math.sqrt(3) * math.sin(math.radians(a))]))
    curves = [dict(a=i, b=i % 6 + 1, construction=False, fixed=True, id=f'l{i}', type='line') for i in range(1, 7)]
    return dict(constraints=[], counters=dict(l=6, p=6), curves=curves, points=pts)


def emit(feature):
    """Append the spine to the timeline through build_seam_v5.helpers' feature()."""
    def cut_extrude(name, sketch_id, distance):
        feature('extrude', name, extent=dict(convention='total_distance', direction='positive', distance=str(distance)),
                operation='cut', profiles=dict(type='all'), sketch=sketch_id, targets=[BODY])

    seat = 'split_spine_seat_D'
    feature('box', 'SPINE_STEM_V1', body_names=[BODY], operation='new_body',
            corner=['split_center_X - split_spine_W/2', STEM_Y0, 'split_spine_bottom_Z'],
            length='split_spine_W', width=str(STEM_W), height=f'8 + {seat} - split_spine_bottom_Z')
    for name, (dx, y, length, width) in (('SPINE_FRONT_PAD', FRONT_PAD), ('SPINE_REAR_PAD', REAR_PAD)):
        feature('box', name, operation='join', participants=[BODY], corner=[f'split_center_X - {-dx}', y, PAD_Z],
                length=str(length), width=str(width), height=f'3 + {seat}')
    for name, points in SWITCH_GUARDS.items():
        sk = feature('sketch', name, plane=plane(GUARD_Z), sketch=polygon_sketch(points))
        cut_extrude(name.replace('SK_SPINE_SWITCH_GUARD', 'SPINE_TRIM_SWITCH'), sk, GUARD_H)
    feature('cylinder', 'SPINE_SO3_RELIEF', axis=[0.0, 0.0, 1.0], base=['split_center_X', 'REF_SO_dY3 - TBD_pcb0_dy', 3.0],
            height='6', operation='cut', participants=[BODY], radius=f'({SO3_RELIEF_D:g} mm) / 2')
    for name, x, y, h in SCREWS:
        feature('cylinder', f'{name}_SPINE_CLEAR', axis=[0.0, 0.0, 1.0], base=[x, y, SCREW_Z], height=str(h),
                operation='cut', participants=[BODY], radius='(split_M2_clear_D) / 2')
        sk = feature('sketch', f'{name}_NUT_SK', plane=plane(NUT_Z), sketch=hex_sketch(x, y))
        cut_extrude(f'{name}_NUT', sk, 'split_nut_depth')
    for i, y in enumerate(WIRE_NOTCH_Y, 1):
        feature('box', f'SPINE_WIRE_NOTCH_{i}_V4', operation='cut', participants=[BODY],
                corner=[f'split_center_X - {WIRE_NOTCH_L / 2:g}', f'{y} - spine_wire_W/2', 'split_spine_bottom_Z - 0.5'],
                length=str(WIRE_NOTCH_L), width='spine_wire_W', height='spine_wire_H + 0.5')
    feature('box', 'SPINE_M2_4_NUT_OPEN_MJF', operation='cut', participants=[BODY], **NUT4_OPEN)


def check(values):
    """The fixed plan positions were drawn on split_center_X 130.881 and the nut corners' stored positions on split_nut_AF."""
    assert abs(values['split_center_X'] - CENTER_X) < 1e-9, values['split_center_X']
    assert abs(values['split_nut_AF'] - NUT_AF) < 1e-9, values['split_nut_AF']
