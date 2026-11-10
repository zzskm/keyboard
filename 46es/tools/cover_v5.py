"""The three cover pieces' base shape: outline slab, edge lip, the r2 P4 cut that splits it into L/T/R, magnet bosses.

Moved out of model/seam_v5_base.json into code on 2026-11-10 (plan 4-5, step 2). The features are the base's, in the
same order, with the same expressions and the same stored sketch coordinates; they now run after the base timeline.
Only cover features touch the cover bodies, so every body's BRep stayed identical (checked with build_seam_v5.py
--probe against the committed CAD and the order-2 export hashes).

build_seam_v5.py then cuts the silhouette window, the leg magnet pockets and the lip reliefs into these bodies.

The outline is the base's constrained corner rectangle (it follows the case parameters); the split cut is fixed
numbers as the r2-era sketch stored them. Both are copied exactly, last digits and constraint order included,
because a different solve or a rounded value rebuilds the covers with different BRep bytes.
"""

COVER_L, COVER_T, COVER_R = 'COVER_L_DRAFT_TBD', 'COVER_T_DRAFT_TBD', 'COVER_R_DRAFT_TBD'
PLATE_TOP = 'TBD_frame_T + TBD_standoff_H + TBD_plate_T'   # cover underside Z

# Outline: the r2-era corner-rectangle sketch SK30_COVER_DRAFT_TBD reduced to its outline. Two corner points follow
# the case parameters, the four lines stay horizontal/vertical through them, four arcs of radius TBD_cover_R (base
# model parameter d45) are tangent and equal. The solver places it at X -0.393 / 285.388, Y -0.367 / 94.967; the
# stored positions are the unsolved start values. Point and curve order and the constraints are the base's (the
# constraints address them by index).
OUTLINE_POINTS = [
    ('origin', None, (0.0, 0.0)),
    ('corner1', ('TBD_cover_gap - TBD_pcb0_dx', 'TBD_cover_gap - TBD_pcb0_dy'), (-0.39999999999999997, -0.3)),
    ('corner2', ('TBD_case_in_W - TBD_pcb0_dx - TBD_cover_gap', 'TBD_case_in_D - TBD_pcb0_dy - TBD_cover_gap'), (285.4, 94.9)),
    ('p5', None, (2.1, -0.3)), ('p6', None, (-0.39999999999999997, 2.2)), ('a1.center', None, (2.1, 2.2)),
    ('p7', None, (282.9, -0.3)), ('p8', None, (285.4, 2.200000000000003)), ('a2.center', None, (282.9, 2.2)),
    ('p9', None, (285.4, 92.4)), ('p10', None, (282.9, 94.9)), ('a3.center', None, (282.9, 92.4)),
    ('p11', None, (2.1000000000000227, 94.9)), ('p12', None, (-0.39999999999999997, 92.4)), ('a4.center', None, (2.1, 92.4)),
]
OUTLINE_CURVES = [('l1', 3, 6), ('l2', 7, 9), ('l3', 10, 12), ('l4', 13, 4),
                  ('a1', 4, 3, 5), ('a2', 6, 7, 8), ('a3', 9, 10, 11), ('a4', 12, 13, 14)]
OUTLINE_CONSTRAINTS = [
    dict(id='k1', l=0, type='horizontal'), dict(id='k2', l=2, type='horizontal'),
    dict(id='k3', l=1, type='vertical'), dict(id='k4', l=3, type='vertical'),
    dict(c=0, id='k5', p=1, type='point_on_curve'), dict(c=3, id='k6', p=1, type='point_on_curve'),
    dict(a=0, b=4, id='k7', type='tangent'), dict(a=3, b=4, id='k8', type='tangent'),
    dict(c=4, id='k9', param='d45', type='radius', value=2.5),
    dict(a=0, b=5, id='k10', type='tangent'), dict(a=1, b=5, id='k11', type='tangent'), dict(a=4, b=5, id='k12', type='equal'),
    dict(c=1, id='k13', p=2, type='point_on_curve'), dict(c=2, id='k14', p=2, type='point_on_curve'),
    dict(a=1, b=6, id='k15', type='tangent'), dict(a=2, b=6, id='k16', type='tangent'), dict(a=4, b=6, id='k17', type='equal'),
    dict(a=2, b=7, id='k18', type='tangent'), dict(a=3, b=7, id='k19', type='tangent'), dict(a=4, b=7, id='k20', type='equal'),
]

# r2 P4 window outlines left and right of the centre piece. Cutting them through the slab leaves three bodies:
# L (the remainder keeps the name), T and R. The silhouette window later replaces the key openings.
SPLIT_CUTS = [
    [(68.23719, 95.133), (67.763028, 90.621651), (45.57334, 91.784563), (45.205813, 84.771729), (26.18192, 85.768729),
     (26.18192, 82.77284), (7.00102, 83.76984), (5.007, 45.721654), (24.030892, 44.724655), (23.19089, 28.696451),
     (20.205683, 28.696451), (19.21686, 9.828577), (52.521155, 8.083173), (52.888716, 15.096664), (71.912609, 14.099664),
     (71.241107, 10.269195), (101.487521, 4.389888), (100.504561, -0.667), (100.504561, -3.667), (117.638797, -3.667),
     (117.638797, -0.667), (121.632661, 19.879647), (117.997711, 20.58621), (128.902558, 76.686793),
     (108.088247, 80.732686), (108.549698, 83.646172), (86.551018, 87.130421), (87.392122, 95.133),
     (87.392122, 98.133), (68.23719, 98.133)],
    [(174.176011, 95.133), (175.017116, 87.130421), (153.018436, 83.646172), (153.485693, 80.696031),
     (132.859956, 76.686793), (143.764803, 20.58621), (141.129854, 20.074027), (145.161501, -0.667),
     (145.161501, -3.667), (157.439305, -3.667), (157.439305, -0.667), (156.59552, 3.673899), (182.166146, 8.644325),
     (181.707415, 11.004289), (200.61542, 13.3259), (200.451027, 14.664774), (223.213426, 15.857701),
     (224.074473, 6.015885), (243.051982, 7.676202), (243.466958, 2.933), (262.444467, 4.593317),
     (262.029491, 9.336519), (281.007, 10.996836), (279.346666, 29.974544), (260.369157, 28.314227),
     (259.123799, 42.548733), (256.738358, 42.340034), (256.157, 53.433), (281.007, 53.433), (281.007, 91.533),
     (257.157, 91.533), (257.157, 83.90557), (235.543222, 82.77284), (235.386214, 85.768729), (216.362321, 84.771729),
     (215.994794, 91.784563), (193.805106, 90.621651), (193.330944, 95.133), (193.330944, 98.133), (174.176011, 98.133)],
]

# Names of the two pieces the split cut makes, in the order the cut returns them when it runs after the base timeline
# (between the plate features, as in the base, the order was T, R). The order is the kernel's, not ours: check()
# fails the build if a piece ends up under the wrong name.
SPLIT_NAMES = [COVER_R, COVER_T]
# Plan X range each piece must fall in (centre piece between the two split cuts).
PIECE_X = {COVER_L: (-1, 102), COVER_T: (86, 176), COVER_R: (156, 286)}

# Magnet bosses over the standoffs, in timeline order, and the piece each belongs to.
BOSSES = [(1, COVER_L), (2, COVER_L), (3, COVER_T), (6, COVER_T), (4, COVER_R), (5, COVER_R)]
# Edge lip: (name, corner X, corner Y, length X, width Y) around the inside of the outline.
LIPS = [
    ('COVER_LIP_L', '-TBD_pcb0_dx + TBD_cover_gap', '-TBD_pcb0_dy + TBD_cover_gap + TBD_cover_R',
     'TBD_cover_wall', 'TBD_case_in_D - 2*TBD_cover_gap - 2*TBD_cover_R'),
    ('COVER_LIP_R', 'TBD_case_in_W - TBD_pcb0_dx - TBD_cover_gap - TBD_cover_wall', '-TBD_pcb0_dy + TBD_cover_gap + TBD_cover_R',
     'TBD_cover_wall', 'TBD_case_in_D - 2*TBD_cover_gap - 2*TBD_cover_R'),
    ('COVER_LIP_F', '-TBD_pcb0_dx + TBD_cover_gap + TBD_cover_R', '-TBD_pcb0_dy + TBD_cover_gap',
     'TBD_case_in_W - 2*TBD_cover_gap - 2*TBD_cover_R', 'TBD_cover_wall'),
    ('COVER_LIP_B', '-TBD_pcb0_dx + TBD_cover_gap + TBD_cover_R', 'TBD_case_in_D - TBD_pcb0_dy - TBD_cover_gap - TBD_cover_wall',
     'TBD_case_in_W - 2*TBD_cover_gap - 2*TBD_cover_R', 'TBD_cover_wall'),
]


def plane(distance):
    return dict(base=dict(name='XY', type='origin'), distance=distance, type='offset')


def outline_sketch():
    pts = []
    for name, exprs, pos in OUTLINE_POINTS:
        point = dict(fixed=exprs is not None or name == 'origin', id=name, pos=list(pos))
        if exprs:
            point['exprs'] = dict(x=exprs[0], y=exprs[1])
        pts.append(point)
    curves = [dict(a=c[1], b=c[2], **({'c': c[3]} if len(c) > 3 else {}), construction=False, id=c[0],
                   type='arc' if len(c) > 3 else 'line') for c in OUTLINE_CURVES]
    return dict(constraints=[dict(c) for c in OUTLINE_CONSTRAINTS], counters=dict(a=4, corner=2, k=20, l=4),
                curves=curves, points=pts)


def polygons_sketch(polygons):
    """Closed polylines from fixed points (fix constraints, as the base stored them)."""
    pts, curves = [dict(fixed=True, id='origin', pos=[0.0, 0.0])], []
    for poly in polygons:
        first = len(pts)
        pts += [dict(fixed=False, id=f'p{first + j}', pos=list(p)) for j, p in enumerate(poly)]
        curves += [dict(a=first + j, b=first + (j + 1) % len(poly), construction=False, id=f'l{first + j}', type='line')
                   for j in range(len(poly))]
    n = len(pts) - 1
    constraints = [dict(id=f'k{i}', p=i, type='fix') for i in range(1, n + 1)]
    return dict(constraints=constraints, counters=dict(k=n, l=n, p=n), curves=curves, points=pts)


def emit(feature):
    """Append the cover pieces to the timeline through build_seam_v5.helpers' feature()."""
    sk = feature('sketch', 'SK30_COVER_DRAFT_TBD', plane=plane(PLATE_TOP), sketch=outline_sketch())
    feature('extrude', 'COVER_DRAFT_TBD', body_names=[COVER_L], operation='new_body', sketch=sk,
            extent=dict(convention='total_distance', direction='positive', distance='TBD_cover_T'),
            profiles=dict(type='curves', loops=[['l1', 'a2', 'l2', 'a3', 'l3', 'a4', 'l4', 'a1']]))
    for name, x, y, length, width in LIPS:
        feature('box', name, operation='join', participants=[COVER_L], corner=[x, y, f'{PLATE_TOP} - TBD_cover_lip_H'],
                length=length, width=width, height='TBD_cover_lip_H')
    sk = feature('sketch', 'SK34_COVER_WINDOWS_REF_r2_P4_NOT_FOR_PRODUCTION', plane=plane(f'{PLATE_TOP} + TBD_cover_T'),
                 sketch=polygons_sketch(SPLIT_CUTS))
    feature('extrude', 'COVER_WINDOWS_REF_r2_P4', body_names=SPLIT_NAMES, operation='cut', sketch=sk,
            extent=dict(convention='total_distance', direction='negative', distance='TBD_cover_T + TBD_cover_lip_H'),
            profiles=dict(type='all'), targets=[COVER_L])
    so = lambda i: [f'REF_SO_dX{i} - TBD_pcb0_dx', f'REF_SO_dY{i} - TBD_pcb0_dy']
    for i, body in BOSSES:
        feature('cylinder', f'COVER_BOSS_SO{i}', axis=[0.0, 0.0, 1.0], base=so(i) + [f'{PLATE_TOP} - TBD_cover_boss_H'],
                height='TBD_cover_boss_H', operation='join', participants=[body], radius='(TBD_cover_boss_D) / 2')
    for i, body in BOSSES:
        feature('cylinder', f'COVER_MAGNET_SO{i}', axis=[0.0, 0.0, 1.0],
                base=so(i) + [f'{PLATE_TOP} - TBD_cover_boss_H - 1'], height='TBD_magnet_T + TBD_magnet_clr + 1',
                operation='cut', participants=[body], radius='(TBD_magnet_D + 2*TBD_magnet_clr) / 2')


def check(bodies):
    """Each piece is one closed body in its own X range (the split cut's name order is the kernel's)."""
    for name, (x0, x1) in PIECE_X.items():
        b = bodies[name]
        assert b['closed'] and x0 <= b['bbox']['min'][0] and b['bbox']['max'][0] <= x1, (name, b['bbox'])
