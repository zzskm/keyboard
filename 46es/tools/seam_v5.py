"""Front seam between the plate halves: a half-lap tab on plate L over a pocket in plate R, one M2 screw from above
and a nut in the underside of R. Also the order-1 seam coupons, built by the same code: two double-ended pieces that
test both variants (COUPON_PIECES).

2026-11-10 (decision, docs/design.md): the v4 dovetail tab with a shallow nut pocket open to the seam face became a
straight half-lap with a locating hook and a closed press-fit nut pocket.
  - The tab drops in from above (straight walls). Its long sides locate in Y and limit in-plane rotation, the hook
    shoulder at the far end limits spreading in X; both with `fit` clearance per side. The tab end has `end_gap`.
  - The dovetail's 0.15 side clearance sat on slanted faces that could wedge; the plate is never trimmed, so a tight
    print had no fix. No switch opening lies within 5 mm of the pocket (5.72), so the tab could grow.
  - The nut sits in a hexagonal pocket closed on all sides (>= 1.0 wall to the seam face of R), deep enough to hold
    it by its flats; the floor above it keeps >= 1.0. It is pressed in (screw pull-in) and pushed out with the screw.
    A side-insert slot would need 1.0 + 1.8 + 1.0 = 3.8 of material where R has TBD_plate_T - tab_T = 2.6.
2026-11-11 (decision): the screw is a common ISO 7380 M2x5 button head (head 3.5-3.8 x 1.3) instead of the
low-head NBK SSH-M2-5 (4 x 1.1), which is hard to buy; the counterbore went 1.2 -> 1.4 so the head top stays
at Z 12.9 (0.1 under the cover) and the tab keeps MIN_WALL under the head.
2026-11-16 (decision): order 1 is held to 10 uploads. The three coupon pairs (S0 v4 dovetail control, S1, S2) became
two pieces, each with an R-type pocket end and an L-type tab end: piece 1 = S2 pocket + S1 tab, piece 2 = S1 pocket +
S2 tab. Piece 1 then piece 2 (left to right) tests S1, piece 2 then piece 1 tests S2. The S0 control was dropped: the
dovetail was replaced for its slanted faces and open pocket, and its result could not bring it back.

The numbers here are the source; the seam_* parameters of the document are documentation and are checked against
them after evaluation (build_seam_v5.check_seam). Features are fixed numbers, as for the mounts and the bracket.
"""
from dataclasses import dataclass, replace
import math

PLATE_BOTTOM_Z, PLATE_TOP_Z = 8.0, 13.0      # TBD_frame_T + TBD_standoff_H, plate_top_Z (checked after evaluation)
SPLIT_FRONT_X = 136.881                       # split_center_X + split_SO_bypass: the seam line for Y < 11
SPLIT_GAP = 0.5                               # split_plate_gap
SPLIT_LINE = [(136.881, -2.0), (136.881, 11.0), (130.881, 16.0), (130.881, 82.5), (136.881, 83.5), (136.881, 97.0)]
L_EDGE_X, R_EDGE_X = SPLIT_FRONT_X - SPLIT_GAP / 2, SPLIT_FRONT_X + SPLIT_GAP / 2
TAB_ROOT_X = 136.3                            # tab sketch starts inside plate L
POCKET_X0 = 137.0                             # pocket sketch starts in the seam gap
TAB_Y = (3.0, 10.2)                           # tab neck sides
NECK_END_X, TAB_END_X, HOOK_Y = 144.2, 147.4, 2.4   # hook: the last 3.2 mm of the tab is 2.4 wider towards +Y
RABBET_INNER_Y = 1.933                        # -TBD_pcb0_dy + TBD_plate_gap + TBD_cover_wall + TBD_cover_lip_clr
COVER_LIP_H = 1.0                             # TBD_cover_lip_H
M2_CLEAR_D, M2_HEAD_D = 2.4, 4.4              # split_M2_clear_D, split_M2_head_D
SCREW_L, SCREW_HEAD_H = 5.0, 1.3              # ISO 7380 M2x5 button head: k 1.3, dk 3.5 (max 3.8)
SCREW_HEAD_D = 3.8
NUT_AF, NUT_H = 4.0, 1.6                      # DIN 934 M2: across flats 4.0 (3.82-4.0), height 1.6
REF_NUT_AF = 3.9                              # reference nut drawn inside its tolerance so it clears a 4.0 pocket
MIN_WALL = 1.0
FRONT_PAD_HOLE_R = 2.55                       # mounts_v5: clearance in Front pad 1 for the nut bottom and screw tip


@dataclass(frozen=True)
class Seam:
    tab_T: float = 2.4               # tab thickness from the plate top = pocket depth
    fit: float = 0.15                # locating clearance per side (tab sides, hook shoulder)
    end_gap: float = 0.3             # tab end and hook outer faces: not locating
    screw: tuple = (140.4, 6.6)      # M2 axis
    cb_D: float = 1.4                # head counterbore in the tab (head top = PLATE_TOP_Z - cb_D + SCREW_HEAD_H)
    nut_AF: float = 4.0              # nut pocket across flats (press fit on a 4.0 nut)
    nut_D: float = 1.3               # nut pocket depth from the plate underside

    @property
    def floor(self):
        """R material under the pocket."""
        return PLATE_TOP_Z - PLATE_BOTTOM_Z - self.tab_T


PRODUCTION = Seam()
# Order-1 coupon variants. S2 widens the locating clearance and the nut pocket by one step each; the lap fit (hand
# insertion) and the nut fit (press, shake) are read separately.
VARIANTS = {'S1': PRODUCTION, 'S2': replace(PRODUCTION, fit=0.25, nut_AF=4.2)}
COUPON_BOX = (118.0, -0.367, 154.0, 21.2)     # blank before the split: plate front edge to behind the seam bend
# The pocket end of a piece sits this far left of its tab end, so the R blank's right edge (COUPON_BOX x1) meets the
# L blank's left edge (x0): one straight piece, pocket end at -X, tab end at +X.
POCKET_END_DX = COUPON_BOX[0] - COUPON_BOX[2]
# body: (pocket variant, tab variant, offset of the tab end from the plate position)
COUPON_PIECES = {'SEAM_COUPON_1': ('S2', 'S1', (0.0, -60.0)),
                 'SEAM_COUPON_2': ('S1', 'S2', (60.0, -60.0))}
COUPON_COLOR = [143, 191, 106]


def coupon_ends(body):
    """((pocket variant, offset), (tab variant, offset)) of one coupon piece."""
    pocket, tab, (dx, dy) = COUPON_PIECES[body]
    return (pocket, (dx + POCKET_END_DX, dy)), (tab, (dx, dy))


def outlines(seam):
    """(tab, pocket) plan polygons at the plate position."""
    (y0, y1), f, e = TAB_Y, seam.fit, seam.end_gap
    tab = [(TAB_ROOT_X, y0), (TAB_END_X, y0), (TAB_END_X, y1 + HOOK_Y), (NECK_END_X, y1 + HOOK_Y), (NECK_END_X, y1),
           (TAB_ROOT_X, y1)]
    pocket = [(POCKET_X0, y0 - f), (TAB_END_X + e, y0 - f), (TAB_END_X + e, y1 + HOOK_Y + e),
              (NECK_END_X - f, y1 + HOOK_Y + e), (NECK_END_X - f, y1 + f), (POCKET_X0, y1 + f)]
    return tab, pocket


def hexagon(x, y, across_flats):
    """Flats square to X (a vertex at 30 degrees), as the v4 pocket."""
    r = across_flats / math.sqrt(3)
    return [(x + r * math.cos(math.radians(30 + 60 * i)), y + r * math.sin(math.radians(30 + 60 * i))) for i in range(6)]


def check(seam, openings=()):
    """Walls and clearances of one variant from its numbers; raises on a production rule, returns the report.
    `openings`: shapely polygons of the 16.5 switch openings (plate position)."""
    from shapely.geometry import Point, Polygon
    tab, pocket = (Polygon(p) for p in outlines(seam))
    sx, sy = seam.screw
    head = Point(sx, sy).buffer(M2_HEAD_D / 2, quad_segs=32)
    report = dict(
        fit=seam.fit, screw=list(seam.screw),
        tab_under_head=round(seam.tab_T - seam.cb_D, 3),
        floor_under_pocket=round(seam.floor, 3),
        floor_over_nut=round(seam.floor - seam.nut_D, 3),
        nut_below_plate=round(NUT_H - seam.nut_D, 3),
        counterbore_wall=round(tab.exterior.distance(head), 3),
        nut_wall_to_seam_face=round(sx - seam.nut_AF / 2 - R_EDGE_X, 3),
        nut_pocket_minus_nut=round(seam.nut_AF - NUT_AF, 3),
        screw_tip_Z=round(PLATE_TOP_Z - seam.cb_D - SCREW_L, 3),
        nut_Z=[round(PLATE_BOTTOM_Z + seam.nut_D - NUT_H, 3), round(PLATE_BOTTOM_Z + seam.nut_D, 3)],
        pocket_to_switch_opening=round(min((pocket.distance(o) for o in openings), default=float('inf')), 3),
        tab_plan_area=round(tab.area, 2))
    assert tab.contains(head), (seam, 'counterbore leaves the tab')
    report['head_top_Z'] = round(PLATE_TOP_Z - seam.cb_D + SCREW_HEAD_H, 3)
    assert report['head_top_Z'] <= PLATE_TOP_Z - 0.1 + 1e-9 and SCREW_HEAD_D < M2_HEAD_D, (seam, report)
    assert pocket.buffer(1e-9).contains(tab.intersection(Polygon([(R_EDGE_X, -5), (200, -5), (200, 30), (R_EDGE_X, 30)]))), \
        (seam, 'tab outside its pocket')
    assert report['nut_below_plate'] >= 0 and report['nut_Z'][0] > report['screw_tip_Z'], (seam, report)   # full thread
    assert NUT_AF / math.sqrt(3) + 0.15 <= FRONT_PAD_HOLE_R, 'the nut corners do not clear the Front pad hole'
    thin = {k: report[k] for k in ('tab_under_head', 'floor_over_nut', 'counterbore_wall', 'nut_wall_to_seam_face',
                                   'pocket_to_switch_opening') if report[k] < MIN_WALL - 1e-9}
    assert not thin, (seam, thin)
    assert HOOK_Y >= 2 * MIN_WALL and TAB_END_X - NECK_END_X >= 2 * MIN_WALL
    report['hook'] = dict(shoulder_X=NECK_END_X, depth_Y=HOOK_Y, length_X=round(TAB_END_X - NECK_END_X, 3))
    return report


def expected_volumes(seam):
    """Volume the seam adds to plate L and removes from plate R is not closed-form (rabbet, counterbores); the
    coupon check compares the two bodies' plan boxes instead. Kept for the tab alone."""
    from shapely.geometry import Polygon
    tab, _ = outlines(seam)
    return Polygon(tab).area * seam.tab_T


def emit(feature, sketch, seam=PRODUCTION, left='PLATE_L_SPLIT_V1', right='PLATE_R_SPLIT_V1', offset=(0.0, 0.0),
         tag='', references=True):
    """Seam features on the two bodies. `left` (tab side) or `right` (pocket side) may be None for a coupon end that
    carries one side only. `tag` keeps feature names unique per coupon end; `references` adds the reference screw
    and nut (production only)."""
    dx, dy = offset
    move = lambda poly: [(round(x + dx, 6), round(y + dy, 6)) for x, y in poly]
    plane = lambda z: dict(type='offset', base=dict(type='origin', name='XY'), distance=str(z))
    cut = lambda distance: dict(convention='total_distance', direction='positive', distance=str(distance))
    tab, pocket = outlines(seam)
    sx, sy = seam.screw[0] + dx, seam.screw[1] + dy
    lap_Z = round(PLATE_TOP_Z - seam.tab_T, 6)
    name = lambda base: f'{base}{tag}'

    if right:
        sk = sketch(name('SK_SEAM_FRONT_POCKET'), plane(lap_Z), [move(pocket)])
        feature('extrude', name('SEAM_FRONT_POCKET_R'), sketch=sk, profiles=dict(type='all'), extent=cut(seam.tab_T + 1),
                operation='cut', targets=[right])
    if left:
        sk = sketch(name('SK_SEAM_FRONT_TAB'), plane(lap_Z), [move(tab)])
        feature('extrude', name('SEAM_FRONT_TAB_L'), sketch=sk, profiles=dict(type='all'), extent=cut(seam.tab_T),
                operation='join', targets=[left])
    feature('cylinder', name('SEAM_FRONT_M2_CLEAR'), axis=[0.0, 0.0, 1.0], base=[sx, sy, PLATE_BOTTOM_Z - 1],
            height=str(PLATE_TOP_Z - PLATE_BOTTOM_Z + 2), radius=str(M2_CLEAR_D / 2), operation='cut',
            participants=[b for b in (left, right) if b])
    if left:
        feature('cylinder', name('SEAM_FRONT_M2_HEAD'), axis=[0.0, 0.0, 1.0], base=[sx, sy, round(PLATE_TOP_Z - seam.cb_D, 6)],
                height='2', radius=str(M2_HEAD_D / 2), operation='cut', participants=[left])
    if right:
        sk = sketch(name('SK_SEAM_FRONT_NUT'), plane(PLATE_BOTTOM_Z - 0.5), [hexagon(sx, sy, seam.nut_AF)])
        feature('extrude', name('SEAM_FRONT_NUT_POCKET_R'), sketch=sk, profiles=dict(type='all'), extent=cut(0.5 + seam.nut_D),
                operation='cut', targets=[right])
        # The strip between the cover lip rabbet and the pocket would be a 0.9 mm fin above the rabbet floor: remove it.
        front = min(y for _, y in pocket)
        end = max(x for x, _ in pocket)
        feature('box', name('SEAM_FRONT_RABBET_MERGE_R'), corner=[POCKET_X0 + dx, 1.7 + dy, PLATE_TOP_Z - COVER_LIP_H],
                length=str(round(end - POCKET_X0, 6)), width=str(round(front + 0.75 - 1.7, 6)), height=str(COVER_LIP_H + 0.5),
                operation='cut', participants=[right])
    if not references:
        return
    screw, nut = 'REF_M2_SEAM_FRONT', 'REF_M2_SEAM_FRONT_NUT'
    seat = round(PLATE_TOP_Z - seam.cb_D, 6)
    feature('cylinder', screw, axis=[0.0, 0.0, 1.0], base=[sx, sy, seat - SCREW_L], body_names=[screw],
            height=str(SCREW_L), operation='new_body', radius='(2 mm) / 2')
    feature('cylinder', f'{screw}_HEAD_JOIN', axis=[0.0, 0.0, 1.0], base=[sx, sy, seat], height=str(SCREW_HEAD_H),
            operation='join', participants=[screw], radius=f'({SCREW_HEAD_D:g} mm) / 2')
    nut_Z = round(PLATE_BOTTOM_Z + seam.nut_D - NUT_H, 6)
    sk = sketch(f'{nut}_SK', plane(nut_Z), [hexagon(sx, sy, REF_NUT_AF)])
    feature('extrude', f'{nut}_HEX', sketch=sk, profiles=dict(type='all'), extent=cut(NUT_H), operation='new_body',
            body_names=[nut])
    feature('cylinder', f'{nut}_THREAD_VOID', axis=[0.0, 0.0, 1.0], base=[sx, sy, nut_Z - 0.2], height='2',
            operation='cut', participants=[nut], radius='(2 mm) / 2')


def coupon_blank(body):
    """Plan polygon of one coupon piece: the R part of the coupon box (split along the plate seam line with the seam
    gap) at the pocket end, joined edge to edge with the L part at the tab end."""
    from shapely.geometry import LineString, box
    from shapely.affinity import translate
    from shapely.ops import unary_union
    x0, y0, x1, y1 = COUPON_BOX
    gap = LineString(SPLIT_LINE).buffer(SPLIT_GAP / 2, cap_style='flat', join_style='mitre')
    left, right = sorted(box(x0, y0, x1, y1).difference(gap).geoms, key=lambda g: g.bounds[0])
    (_, pocket_at), (_, tab_at) = coupon_ends(body)
    piece = unary_union([translate(right, *pocket_at), translate(left, *tab_at)]).simplify(1e-9)
    assert piece.geom_type == 'Polygon' and not piece.interiors, piece.geom_type
    return [(round(x, 6), round(y, 6)) for x, y in piece.exterior.coords[:-1]]


def coupon_box(body):
    """Expected bounding box (x0, y0, z0, x1, y1, z1) of one coupon piece."""
    (_, (px, _)), (_, (tx, ty)) = coupon_ends(body)
    _, y0, _, y1 = COUPON_BOX
    return (SPLIT_LINE[2][0] + SPLIT_GAP / 2 + px, y0 + ty, PLATE_BOTTOM_Z, TAB_END_X + tx, y1 + ty, PLATE_TOP_Z)


def emit_coupons(feature, sketch, doc):
    """The two coupon pieces: flat blanks of the plate thickness with the front cover-lip rabbet, then the seam
    features of the plate at each end (pocket side at -X, tab side at +X; no flanges, switch layers or standoff
    counterbore)."""
    plane = dict(type='offset', base=dict(type='origin', name='XY'), distance=str(PLATE_BOTTOM_Z))
    for body in COUPON_PIECES:
        sk = sketch(f'SK_{body}', plane, [coupon_blank(body)])
        feature('extrude', f'{body}_BLANK', sketch=sk, profiles=dict(type='all'),
                extent=dict(convention='total_distance', direction='positive', distance=str(PLATE_TOP_Z - PLATE_BOTTOM_Z)),
                operation='new_body', body_names=[body])
        doc['appearances']['bodies'][body] = dict(name='Custom', color=COUPON_COLOR, opacity=1.0)
        x0, y0, x1, _, _, _ = coupon_box(body)
        feature('box', f'{body}_RABBET', corner=[round(x0 - 1, 6), round(y0 - 1, 6), PLATE_TOP_Z - COVER_LIP_H],
                length=str(round(x1 - x0 + 2, 6)), width=str(round(RABBET_INNER_Y - COUPON_BOX[1] + 1, 6)),
                height=str(COVER_LIP_H + 1), operation='cut', participants=[body])
        (pocket, pocket_at), (tab, tab_at) = coupon_ends(body)
        emit(feature, sketch, VARIANTS[pocket], left=None, right=body, offset=pocket_at, tag=f'_{body[-1]}P', references=False)
        emit(feature, sketch, VARIANTS[tab], left=body, right=None, offset=tab_at, tag=f'_{body[-1]}T', references=False)
