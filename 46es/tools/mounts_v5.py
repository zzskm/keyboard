"""The four v5 mounts, built directly from the CADCraft drawing.

model/mounts_cadcraft_phase1.dxf is the plan-view source: outlines and plate
pads are extruded as drawn (the Rear spine shim was removed on 2026-11-11;
the spine bears on the Rear frame top, spine_v5.py). Fastener holes, SO
insert bosses and head recesses follow the document parameters at the
GH60/SO anchors; the drawing's hole layers are checked against them.

SO1-SO6 since 2026-11-12: a printed boss (Z 1.5-8) with a heat-set M3 insert
from the stock (round brass, OD 5 x 4) replaces the brass hex standoff, its
1 mm hex pocket in the frame and the lower M3 screw. The upper M3 (stock black
M3x10 button head) runs through the plate, the insert and the frame bore.
Pin reliefs
are derived from the switch layout (make_key_dxf) and the KS-3X1 pin
positions, so a changed outline gets its reliefs recomputed.

Used by tools/build_seam_v5.py (feature emission) and
inspection/scripts/verify_seam_v5.py (expected section profiles).
"""
import math
from pathlib import Path

import ezdxf
from shapely.geometry import LineString, Point, Polygon, box
from shapely.ops import polygonize, unary_union

from make_key_dxf import load_keys, rect
import seam_v5

ROOT = Path(__file__).resolve().parents[1]
DRAWING = ROOT / 'model/mounts_cadcraft_phase1.dxf'

LEFT_MOUNT = 'MOUNT_L_PAIR_V3'
RIGHT_MOUNT = 'MOUNT_R_PAIR_V3'
REAR_MOUNT = 'MOUNT_H02_SO3_MIN_V2'
FRONT_MOUNT = 'MOUNT_H03_SO6_MIN_V2'
MOUNTS = {'L': LEFT_MOUNT, 'R': RIGHT_MOUNT, 'REAR': REAR_MOUNT, 'FRONT': FRONT_MOUNT}
PLATE_SUPPORT_MOUNTS = {
    LEFT_MOUNT: 'PLATE_L_SPLIT_V1',
    RIGHT_MOUNT: 'PLATE_R_SPLIT_V1',
    REAR_MOUNT: 'PLATE_L_SPLIT_V1',
    FRONT_MOUNT: 'PLATE_R_SPLIT_V1',
}

# Document values the drawing is checked against (parameters_seam_v5.csv).
FRAME_T = 3.0
PAD_TOP_Z = 8.0                    # plate_top_Z - TBD_plate_T
PAD_ROOT_Z = 1.5                   # pads start inside the frame
SO_BORE_D = 3.4                    # TBD_so_screw_D + TBD_so_clr
SO_POCKET_Z = 2.0                  # band boundary kept from the hex pocket era: the case head recesses start here too
INSERT_D, INSERT_H = 5.0, 4.0      # v5_so_insert_D, v5_so_insert_H: stock round brass M3 insert (PURCHASE.md)
INSERT_HOLE_D = 4.2                # v5_so_insert_hole_D: heat-set hole; the B coupon row D tries 4.0-4.6
BOSS_D = 8.0                       # v5_so_boss_D: printed boss around the insert, inside the AF 8.5 land
BOSS_WALL_MIN = 1.2                # insert hole to the boss edge where the outline or a plate flange clips the boss
CASE_SLOT_W = 2.4                  # TBD_case_screw_D + TBD_case_screw_clr
CASE_HEAD_W = 4.4                  # TBD_case_head_D + TBD_case_head_clr
CASE_HEAD_Z = 2.0                  # TBD_frame_T - TBD_case_head_H
CASE_ADJUST = 1.0                  # TBD_case_adjust (slot half straight length)
LAND_AF = 8.5                      # octagonal keep-clear zone around each SO boss
SEAM_NUT_CLEARANCE = (seam_v5.PRODUCTION.screw, seam_v5.FRONT_PAD_HOLE_R)   # seam_M2_X/Y; nut bottom and screw tip above the Front pad
# Downturned plate flanges (PLATE_FLANGE_*: split_flange_W 2.0 wide, Z 5-8) run along the plate edges; pads keep
# PAD_FLANGE_CLEARANCE to their inner faces so the plate can seat. Inner faces: x -0.393+2 / 285.388-2, y -0.367+2 / 94.967-2.
PLATE_FLANGE_INNER = (1.607, 1.633, 283.388, 92.967)
PAD_FLANGE_CLEARANCE = 0.3
SWITCH_BODY_Z = 4.95               # TBD_frame_T + TBD_standoff_H - 3 - 0.05: nothing above this under a switch body
SWITCH_BODY_CLR = 0.15
MIN_WALL = 1.0                     # MJF
# Document parameters of the SO insert bosses (added by build_seam_v5.py to the production and mount-only models)
PARAMS = [
    ('v5_so_insert_D', f'{INSERT_D:g} mm', '[보유품 2026-11-12] SO 열압입 인서트 외경. 원형 황동 M3 인서트 20개(외경 Ø5 × 높이 4, '
     'PURCHASE.md) 중 6개. 2026-11-12 이전의 황동 육각 지지대(길이 6, 맞변 5)와 아래 M3×5를 대신한다'),
    ('v5_so_insert_H', f'{INSERT_H:g} mm', '[보유품 2026-11-12] SO 인서트 높이. 보스 윗면(plate 밑면)과 같은 높이로 넣는다'),
    ('v5_so_insert_hole_D', f'{INSERT_HOLE_D:g} mm', '[설계 후보 2026-11-12] SO 인서트 열압입 구멍. 외경 5 인서트의 일반 권장 4.0–4.4 중간. '
     'MJF 출력 편차는 주문 1 B 쿠폰 행 D(4.0/4.2/4.4/4.6)와 mount 4개로 확인'),
    ('v5_so_boss_D', f'{BOSS_D:g} mm', '[설계 2026-11-12] SO 인서트 보스 지름(Z 1.5–8). AF 8.5 팔각 보존 구역 안. 외곽선·plate 플랜지에 걸리면 잘리고, '
     f'그때도 구멍까지 살 {BOSS_WALL_MIN:g} 이상'),
    ('v5_so_insert_hole_depth', 'plate_top_Z - TBD_plate_T - TBD_frame_T', '[유도값 2026-11-12] 인서트 구멍 깊이 = 보스 윗면 Z 8 − 프레임 윗면 Z 3 = 5. '
     '인서트 4 + 녹은 수지 자리 1. 아래 프레임에는 M3 관통 Ø3.4'),
]

# KS-3X1 drawing XY, with conservative cylindrical guides and rectangular contacts.
# Both reference pin families extend to Z 2.7 at the v5 switch seat (Z 11.3).
MX_GUIDES = ((0.0, 1.95), (-5.08, 0.875), (5.08, 0.875))
MX_CONTACTS = ((-3.81, 2.54), (2.54, 5.08))
MX_CONTACT_SIZE = (1.15, 0.5)
MX_PIN_DEPTH_FROM_SEAT = 8.6
MOUNT_PIN_CLEARANCE = 0.4
RELIEF_FLOOR_Z = 2.1               # plate_top_Z - TBD_upper_plate_T - 8.6 - 0.6
RELIEF_MARGIN = 0.6                # pin footprint to pocket wall (clearance 0.4 + 0.2)

# Plate half each SO boss carries (the counterbores: L has SO1, SO2, SO3, SO6; R has SO4, SO5)
SO_PLATES = {'SO1': 'PLATE_L_SPLIT_V1', 'SO2': 'PLATE_L_SPLIT_V1', 'SO3': 'PLATE_L_SPLIT_V1',
             'SO4': 'PLATE_R_SPLIT_V1', 'SO5': 'PLATE_R_SPLIT_V1', 'SO6': 'PLATE_L_SPLIT_V1'}
# name -> (mount, numeric anchor, X/Y parameter expressions)
SO_ANCHORS = {
    'SO1': ('L', (6.494, 6.520), ('REF_SO_dX1 - TBD_pcb0_dx', 'REF_SO_dY1 - TBD_pcb0_dy')),
    'SO2': ('L', (6.494, 87.945), ('REF_SO_dX2 - TBD_pcb0_dx', 'REF_SO_dY2 - TBD_pcb0_dy')),
    'SO3': ('REAR', (130.881, 87.945), ('REF_SO_dX3 - TBD_pcb0_dx', 'REF_SO_dY3 - TBD_pcb0_dy')),
    'SO4': ('R', (250.420, 89.007), ('REF_SO_dX4 - TBD_pcb0_dx', 'REF_SO_dY4 - TBD_pcb0_dy')),
    'SO5': ('R', (278.519, 6.520), ('REF_SO_dX5 - TBD_pcb0_dx', 'REF_SO_dY5 - TBD_pcb0_dy')),
    'SO6': ('FRONT', (130.881, 6.520), ('REF_SO_dX6 - TBD_pcb0_dx', 'REF_SO_dY6 - TBD_pcb0_dy')),
}
# name -> (mount, numeric anchor, slot axis, half straight length, head recess)
# H05 keeps the shorter v4 slot (0.9) next to the left edge and has no head recess
# (a 4.4 recess would leave 0.36 mm to the edge); its head sits on the frame top.
CASE_ANCHORS = {
    'H01': ('L', (25.1993, 66.6992), 'X', 1.0, True),
    'H05': ('L', (3.70934, 38.0988), 'X', 0.9, False),
    'H02': ('REAR', (128.2, 47.6), 'Y', 1.0, True),
    'H03': ('FRONT', (190.4994, 9.3993), 'Y', 1.0, True),
    'H04': ('R', (260.0499, 66.6992), 'Y', 1.0, True),
    'H06': ('R', (281.29076, 38.0988), 'Y', 1.0, True),
}


def ring(geometry):
    """Closed rings (outer first) of a polygon, for SolidCraft sketches."""
    shapes = list(geometry.geoms) if hasattr(geometry, 'geoms') else [geometry]
    rings = []
    for shape in shapes:
        if shape.geom_type != 'Polygon' or shape.area <= 1e-8:
            continue
        rings.append([(float(x), float(y)) for x, y in list(shape.exterior.coords)[:-1]])
        rings.extend([(float(x), float(y)) for x, y in list(hole.coords)[:-1]] for hole in shape.interiors)
    return rings


def parts(geometry):
    if geometry.is_empty:
        return []
    shapes = list(geometry.geoms) if hasattr(geometry, 'geoms') else [geometry]
    return [s for s in shapes if s.geom_type == 'Polygon' and s.area > 1e-8]


def clean(geometry):
    """Drop zero-area slivers that Boolean differences leave along shared edges."""
    return unary_union([s for s in parts(geometry.buffer(0)) if s.area > 1e-6])


def hexagon(center, across_flats):
    """Regular hexagon with flats parallel to X (vertices on the X axis), as SK11 drew it."""
    cx, cy = center
    radius = across_flats / math.sqrt(3)
    return Polygon([(cx + radius * math.cos(math.radians(a)), cy + radius * math.sin(math.radians(a)))
                    for a in range(0, 360, 60)])


def octagon(center, across_flats):
    cx, cy = center
    radius = across_flats / 2 / math.cos(math.radians(22.5))
    return Polygon([(cx + radius * math.cos(math.radians(a)), cy + radius * math.sin(math.radians(a)))
                    for a in range(0, 360, 45)])


def slot(center, axis, half_straight, width):
    """Stadium along X or Y: straight length 2*half_straight, semicircle radius width/2."""
    cx, cy = center
    ends = [(cx - half_straight, cy), (cx + half_straight, cy)] if axis == 'X' else \
           [(cx, cy - half_straight), (cx, cy + half_straight)]
    return LineString(ends).buffer(width / 2, quad_segs=32)


def flange_keep():
    """Plan area that stays PAD_FLANGE_CLEARANCE inside the plate's downturned flanges (pads and SO bosses)."""
    x0, y0, x1, y1 = PLATE_FLANGE_INNER
    c = PAD_FLANGE_CLEARANCE
    return box(x0 + c, y0 + c, x1 - c, y1 - c)


def read_drawing(path=DRAWING):
    """Outlines, pads and the hole/relief layers of the CADCraft drawing."""
    entities = list(ezdxf.readfile(path).modelspace())

    def polylines(layer):
        matches = [e for e in entities if e.dxftype() == 'LWPOLYLINE' and e.dxf.layer == layer]
        if not all(e.closed for e in matches):
            raise ValueError(f'drawing layer {layer} has an open polyline')
        return [Polygon(e.get_points('xy')) for e in matches]

    def line_outline(layers, xmin, xmax):
        lines = []
        for e in entities:
            if e.dxftype() == 'LINE' and e.dxf.layer in layers:
                line = LineString([(e.dxf.start.x, e.dxf.start.y), (e.dxf.end.x, e.dxf.end.y)])
                if xmin <= line.bounds[0] and line.bounds[2] <= xmax:
                    lines.append(line)
        outline = unary_union(list(polygonize(unary_union(lines))))
        if outline.geom_type != 'Polygon' or not outline.is_valid:
            raise ValueError(f'drawing lines on {layers} in X {xmin}..{xmax} are not one closed outline')
        return outline

    def single(layer):
        shapes = polylines(layer)
        if len(shapes) != 1:
            raise ValueError(f'drawing layer {layer} must hold exactly one closed polyline')
        return shapes[0]

    outlines = {
        'L': line_outline({'0', 'L_OUTLINE'}, -5, 40),
        'FRONT': line_outline({'0'}, 120, 200),
        'R': single('R_OUTLINE'),
        'REAR': single('REAR_OUTLINE'),
    }
    for suffix, outline in outlines.items():
        outlines[suffix] = outline.simplify(0.001)      # drop collinear construction vertices
        if not outlines[suffix].is_valid or outlines[suffix].interiors:
            raise ValueError(f'{suffix} outline is invalid or has holes')
    layer0 = [Polygon(e.get_points('xy')) for e in entities
              if e.dxftype() == 'LWPOLYLINE' and e.dxf.layer == '0' and e.closed]
    pads = {
        'L': sorted([p for p in layer0 if p.bounds[2] < 40], key=lambda p: p.bounds[1]),
        'FRONT': sorted([p for p in layer0 if 120 < p.bounds[0] < 200], key=lambda p: p.bounds[0]),
        'R': sorted([p for p in layer0 if p.bounds[0] > 240], key=lambda p: -p.bounds[3]),
        'REAR': [single('REAR_PLATE_SEATS')],
    }
    for suffix, count in [('L', 2), ('R', 2), ('REAR', 1), ('FRONT', 2)]:
        if len(pads[suffix]) != count or any(not p.is_valid for p in pads[suffix]):
            raise ValueError(f'{suffix} must have {count} valid plate pad profiles')
    # Pads are drawn to the rail edges; keep them clear of the plate's downturned flanges.
    keep = flange_keep()
    pads = {suffix: [clean(p.intersection(keep)) for p in shapes] for suffix, shapes in pads.items()}
    return dict(
        outlines=outlines, pads=pads,
        octagons={name: p for p in polylines('L_SO_SUPPORT_OCTAGON')
                  for name, (_, anchor, _) in SO_ANCHORS.items() if p.centroid.distance(Point(anchor)) < 0.01},
        holes={s: polylines(f'{s}_THROUGH_HOLES') for s in MOUNTS},
        recesses={s: polylines(f'{s}_HEAD_RECESSES') for s in MOUNTS},
        reliefs={s: polylines(f'{s}_RELIEFS') for s in MOUNTS},
    )


def check_drawing(drawing):
    """The drawing's hole layers must show the parametric fasteners; everything must sit inside its outline."""
    outlines = drawing['outlines']
    if set(drawing['octagons']) != set(SO_ANCHORS):
        raise ValueError('L_SO_SUPPORT_OCTAGON must hold one octagon per SO anchor')
    for name, shape in drawing['octagons'].items():
        if abs(2 * shape.boundary.distance(Point(SO_ANCHORS[name][1])) - LAND_AF) > 0.005:
            raise ValueError(f'{name} octagon is not AF {LAND_AF} around its anchor')
    expected = {s: [] for s in MOUNTS}
    for name, (suffix, anchor, _) in SO_ANCHORS.items():
        expected[suffix].append(('hole', name, Point(anchor).buffer(SO_BORE_D / 2, quad_segs=32)))
    for name, (suffix, anchor, axis, half, head) in CASE_ANCHORS.items():
        expected[suffix].append(('hole', name, slot(anchor, axis, half, CASE_SLOT_W)))
        if head:
            expected[suffix].append(('recess', name, slot(anchor, axis, half, CASE_HEAD_W)))
    for suffix, items in expected.items():
        drawn = {'hole': list(drawing['holes'][suffix]), 'recess': list(drawing['recesses'][suffix])}
        for kind, name, shape in items:
            match = min(drawn[kind], key=lambda p: p.centroid.distance(shape.centroid), default=None)
            # a clipped recess (H06 meets the outline) moves its centroid; its profile is still checked below
            if match is None or match.centroid.distance(shape.centroid) > (0.02 if kind == 'hole' else 0.3):
                raise ValueError(f'drawing {suffix}_{kind.upper()} layer has no profile at {name}')
            drawn[kind].remove(match)
            # A recess may be clipped by the outline (H06); a hole may not.
            if not shape.buffer(0.03).covers(match) or (kind == 'hole' and match.area < 0.97 * shape.area):
                raise ValueError(f'drawing {name} {kind} differs from the parametric fastener')
            if not outlines[suffix].covers(match):
                raise ValueError(f'drawing {name} {kind} leaves the {suffix} outline')
        if drawn['hole'] or drawn['recess']:
            raise ValueError(f'drawing {suffix} has fastener profiles without an anchor')
    for suffix, pads in drawing['pads'].items():
        for pad in pads:
            if pad.difference(outlines[suffix]).area > 1e-6:
                raise ValueError(f'{suffix} plate pad leaves the outline')


def switch_pins():
    """Per key: body (13.98 square) and pin footprints at the frame level."""
    keys = load_keys(.693, .667)
    out = []
    for index, key in enumerate(keys, 1):
        angle = math.radians(key['rot'])
        c, s = math.cos(angle), math.sin(angle)
        pins = [Point(key['x'] + x * c, key['y'] + x * s).buffer(r, quad_segs=16) for x, r in MX_GUIDES]
        pins += [Polygon(rect(key['x'], key['y'], *MX_CONTACT_SIZE, key['rot'], off=offset)) for offset in MX_CONTACTS]
        body = Polygon(rect(key['x'], key['y'], 13.98, 13.98, key['rot']))
        out.append(dict(index=index, body=body, pins=pins))
    return out


def pin_reliefs(outline, pads, keepouts, merge_into, keys):
    """Pockets (floor RELIEF_FLOOR_Z) around every switch pin that reaches the outline.

    One axis-aligned pocket per key around its intruding pins plus RELIEF_MARGIN. A pocket
    closer than MIN_WALL to the outline is opened through that edge (no thin wall, no
    powder trap); one closer than MIN_WALL to a case head recess is joined to it with a
    MIN_WALL closing (tangent fillets, no feather edge). Pins whose clearance only grazes
    the body get a round scallop instead of a box. Pockets stay MIN_WALL from the hex
    pockets and never lie under a plate pad.
    """
    reliefs = {}
    for key in keys:
        pins = [p for p in key['pins'] if p.buffer(MOUNT_PIN_CLEARANCE).intersects(outline)]
        if not pins:
            continue
        need = unary_union([p.buffer(MOUNT_PIN_CLEARANCE) for p in pins]).intersection(outline)
        if need.buffer(-MIN_WALL / 2).is_empty:
            # the clearance zone reaches less than MIN_WALL into the body: a box would leave a
            # hair-width slit in the side face, a scallop meets it at an obtuse angle
            pocket = unary_union([p.buffer(MOUNT_PIN_CLEARANCE + RELIEF_MARGIN, quad_segs=32) for p in pins])
            reliefs[key['index']] = finish_relief(pocket, outline, pads, merge_into, key, pins)
            continue
        x0, y0, x1, y1 = unary_union(pins).bounds
        x0, y0, x1, y1 = x0 - RELIEF_MARGIN, y0 - RELIEF_MARGIN, x1 + RELIEF_MARGIN, y1 + RELIEF_MARGIN
        for side in range(4):
            edge = [LineString([(x0, y0), (x0, y1)]), LineString([(x1, y0), (x1, y1)]),
                    LineString([(x0, y0), (x1, y0)]), LineString([(x0, y1), (x1, y1)])][side]
            inside = edge.intersection(outline)
            if inside.is_empty or inside.length < 1e-6:
                continue                       # this side already lies outside the body
            # test the core of the strip beyond this side; slanted outline edges at the ends are not walls
            ix0, iy0, ix1, iy1 = inside.bounds
            ix0, iy0, ix1, iy1 = ix0 + MIN_WALL, iy0 + MIN_WALL, ix1 - MIN_WALL, iy1 - MIN_WALL
            if (side < 2 and iy1 <= iy0) or (side >= 2 and ix1 <= ix0):
                continue
            strip = [box(x0 - MIN_WALL, iy0, x0, iy1), box(x1, iy0, x1 + MIN_WALL, iy1),
                     box(ix0, y0 - MIN_WALL, ix1, y0), box(ix0, y1, ix1, y1 + MIN_WALL)][side]
            if not outline.covers(strip):
                x0, x1, y0, y1 = (x0 - 3 if side == 0 else x0, x1 + 3 if side == 1 else x1,
                                  y0 - 3 if side == 2 else y0, y1 + 3 if side == 3 else y1)
        pocket = max(parts(box(x0, y0, x1, y1).difference(unary_union(keepouts)).buffer(0)), key=lambda p: p.area)
        reliefs[key['index']] = finish_relief(pocket, outline, pads, merge_into, key, pins)
    return reliefs


def finish_relief(pocket, outline, pads, merge_into, key, pins):
    """Common checks and the head-recess join for one pin relief pocket."""
    for pin in pins:
        if not pocket.buffer(1e-6).covers(pin.buffer(MOUNT_PIN_CLEARANCE).intersection(outline)):
            raise ValueError(f'key {key["index"]} pin clearance is blocked by a hex pocket keep-out')
    # A pocket closer than MIN_WALL to a case head recess joins it: a closing by MIN_WALL fills the
    # gap with fillets tangent to both, where a plain union would leave a knife-edge of material.
    for head in merge_into:
        if pocket.distance(head) < MIN_WALL - 1e-6:
            pocket = unary_union([pocket, head]).buffer(MIN_WALL, quad_segs=16).buffer(-MIN_WALL, quad_segs=16)
    if any(pocket.intersection(pad).area > 1e-6 for pad in pads):
        raise ValueError(f'key {key["index"]} pins lie under a plate pad')
    return pocket


def feather_edges(material, cuts, limit=MIN_WALL - 0.02, min_area=0.15, min_extent=1.5):
    """Material thinner than `limit` next to one of `cuts`: knife-edges the generator must not leave.

    A morphological opening by limit/2 drops everything thinner than `limit`; what it drops at an
    ordinary convex corner is tiny (0.054 mm2 at 90 deg), so only larger or longer remnants that
    touch a cut count. The drawing's own acute corners away from cuts are the designer's choice.
    """
    thin = material.difference(material.buffer(-limit / 2).buffer(limit / 2 + 1e-3))
    found = []
    for part in parts(thin):
        x0, y0, x1, y1 = part.bounds
        if part.area <= min_area and max(x1 - x0, y1 - y0) <= min_extent:
            continue
        if part.buffer(-0.05).is_empty:
            continue                           # nowhere thicker than 0.1 mm: offset reconstruction noise
        if any(part.distance(cut) < 1e-3 for cut in cuts):
            found.append(part)
    return found


def profiles(drawing=None):
    """Everything the generator extrudes, as plan geometry per mount, plus expected sections."""
    drawing = drawing or read_drawing()
    check_drawing(drawing)
    keys = switch_pins()
    out = {}
    for suffix, mount in MOUNTS.items():
        outline = drawing['outlines'][suffix]
        pads = drawing['pads'][suffix]
        so = {name: anchor for name, (s, anchor, _) in SO_ANCHORS.items() if s == suffix}
        case = {name: (anchor, axis, half, head) for name, (s, anchor, axis, half, head) in CASE_ANCHORS.items() if s == suffix}
        bores = {name: Point(a).buffer(SO_BORE_D / 2, quad_segs=48) for name, a in so.items()}
        inserts = {name: Point(a).buffer(INSERT_HOLE_D / 2, quad_segs=48) for name, a in so.items()}
        lands = {name: octagon(a, LAND_AF).intersection(outline) for name, a in so.items()}
        bosses = {name: clean(Point(a).buffer(BOSS_D / 2, quad_segs=48).intersection(outline).intersection(flange_keep()))
                  for name, a in so.items()}
        slots = {name: slot(a, axis, half, CASE_SLOT_W) for name, (a, axis, half, _) in case.items()}
        heads = {name: slot(a, axis, half, CASE_HEAD_W) for name, (a, axis, half, head) in case.items() if head}
        reliefs = pin_reliefs(outline, pads, list(bosses.values()), list(heads.values()), keys)
        for name, boss in bosses.items():
            wall = inserts[name].boundary.distance(boss.boundary)
            if boss.geom_type != 'Polygon' or wall < BOSS_WALL_MIN - 1e-6:
                raise ValueError(f'{name} boss: insert hole wall {wall:.3f} < {BOSS_WALL_MIN}')
            if not lands[name].buffer(1e-6).covers(boss):
                raise ValueError(f'{name} boss leaves its AF {LAND_AF} land')
            hit = [k['index'] for k in keys if boss.intersects(k['body'].buffer(SWITCH_BODY_CLR, join_style='mitre'))]
            if hit:
                raise ValueError(f'{name} boss meets switch bodies {hit}')
        # Switch bodies above SWITCH_BODY_Z: cut the pads where a 13.98 housing (+0.15) overlaps.
        nut = None
        if suffix == 'FRONT':
            (nx, ny), nr = SEAM_NUT_CLEARANCE
            nut = Point(nx, ny).buffer(nr, quad_segs=48)
            if not pads[0].intersects(nut):
                raise ValueError('the Front seam nut clearance misses pad 1')
        clearances = {}
        for i, pad in enumerate(pads, 1):
            for key in keys:
                hit = pad.intersection(key['body'].buffer(SWITCH_BODY_CLR, join_style='mitre'))
                if hit.area > 0.01:
                    # take slivers thinner than MIN_WALL left beside the cut along with it
                    thin = [r for r in parts(pad.difference(hit)) if r.buffer(-MIN_WALL / 2).is_empty]
                    clearances[(i, key['index'])] = unary_union([hit, *thin]).buffer(0)
        for name, land in lands.items():
            blockers = list(reliefs.values()) + list(heads.values()) + list(slots.values()) + ([nut] if nut else [])
            if any(land.intersection(b).area > 1e-6 for b in blockers):
                raise ValueError(f'{name} land (AF {LAND_AF}) is cut by a relief, case fastener or nut clearance')
        # Every pocket and hole keeps an MJF wall to the outline; a thinner spot is a drawing problem.
        for name, shape in {**heads, **slots, **bores}.items():
            wall = shape.boundary.distance(outline.boundary)
            if wall < MIN_WALL - 1e-6:
                raise ValueError(f'{suffix} {name}: wall to the outline is {wall:.3f} < {MIN_WALL}; widen the drawing there')
        out[suffix] = dict(mount=mount, outline=outline, pads=pads, bores=bores, inserts=inserts, bosses=bosses,
                           lands=lands, slots=slots, heads=heads, reliefs=reliefs, clearances=clearances, nut=nut)
        # No knife-edge of material next to anything the generator cuts, in any Z band.
        cuts = [*bores.values(), *inserts.values(), *slots.values(), *heads.values(), *reliefs.values(),
                *clearances.values(), *([nut] if nut else [])]
        for z0, z1, shape in layers(out[suffix]):
            for part in feather_edges(shape, cuts):
                x, y = part.representative_point().coords[0]
                raise ValueError(f'{suffix}: material thinner than {MIN_WALL} mm next to a cut near '
                                 f'({x:.2f}, {y:.2f}) in Z {z0}-{z1} ({part.area:.3f} mm2)')
    return out


def layers(profile):
    """Plan material of one mount per prismatic Z band: [(z0, z1, polygon), ...]."""
    outline, pads = profile['outline'], unary_union(profile['pads'])
    through = unary_union(list(profile['bores'].values()) + list(profile['slots'].values()))
    pockets = unary_union(list(profile['heads'].values()))
    reliefs = unary_union(list(profile['reliefs'].values())) if profile['reliefs'] else Polygon()
    clearances = unary_union(list(profile['clearances'].values())) if profile['clearances'] else Polygon()
    nut = profile['nut'] or Polygon()
    bosses = unary_union(list(profile['bosses'].values())) if profile['bosses'] else Polygon()
    inserts = unary_union(list(profile['inserts'].values())) if profile['inserts'] else Polygon()
    frame = outline.difference(through)
    frame_nut = frame.difference(nut)                       # the nut clearance starts at PAD_ROOT_Z
    frame_cut = frame_nut.difference(pockets)
    frame_relieved = frame_cut.difference(reliefs)
    # above the frame: plate pads and SO insert bosses; the insert holes run from the frame top to the plate
    pads_cut = pads.union(bosses).difference(through).difference(pockets).difference(nut).difference(inserts)
    return [(z0, z1, clean(shape)) for z0, z1, shape in (
        (0.0, PAD_ROOT_Z, frame),
        (PAD_ROOT_Z, SO_POCKET_Z, frame_nut),
        (SO_POCKET_Z, RELIEF_FLOOR_Z, frame_cut),
        (RELIEF_FLOOR_Z, FRAME_T, frame_relieved),
        (FRAME_T, SWITCH_BODY_Z, pads_cut),
        (SWITCH_BODY_Z, PAD_TOP_Z, pads_cut.difference(clearances)),
    )]


def expected_sections(profile):
    """Plan section of one mount at heights between the horizontal faces: {z: polygon}."""
    bands = layers(profile)
    return {z: next(shape for z0, z1, shape in bands if z0 < z < z1) for z in (1.0, 2.5, 3.6, 6.0)}


def expected_volume(profile):
    return sum((z1 - z0) * shape.area for z0, z1, shape in layers(profile))


def emit(feature, sketch, profile_set):
    """Append the mount features to a document through the generator's feature()/sketch() helpers."""
    xy = dict(type='origin', name='XY')

    def plane(z):
        return dict(type='offset', base=xy, distance=str(z))

    def extrude(name, sk, distance, operation, mount, new=False):
        options = dict(body_names=[mount]) if new else dict(targets=[mount])
        feature('extrude', name, sketch=sk, profiles=dict(type='all'),
                extent=dict(convention='total_distance', direction='positive', distance=distance),
                operation=operation, **options)

    def cylinder(name, center, z, height, radius, mount):
        feature('cylinder', name, axis=[0., 0., 1.], base=[center[0], center[1], z], height=height,
                radius=radius, operation='cut', participants=[mount])

    def stadium(name, anchor_expr, axis, half, width_expr, z, height, mount):
        x, y = anchor_expr
        along, across = (f'2*{half}', width_expr) if axis == 'X' else (width_expr, f'2*{half}')
        corner = ([f'{x} - {half}', f'{y} - ({width_expr})/2', z] if axis == 'X'
                  else [f'{x} - ({width_expr})/2', f'{y} - {half}', z])
        feature('box', name, corner=corner, length=along, width=across, height=height,
                operation='cut', participants=[mount])
        for end, sign in (('A', '-'), ('B', '+')):
            center = ([f'{x} {sign} {half}', y] if axis == 'X' else [x, f'{y} {sign} {half}'])
            cylinder(f'{name}_{end}', center, z, height, f'({width_expr})/2', mount)

    for suffix, p in profile_set.items():
        mount = p['mount']
        sk = sketch(f'SK_MOUNT_{suffix}_FRAME', xy, ring(p['outline']))
        extrude(f'MOUNT_{suffix}_FRAME', sk, 'TBD_frame_T', 'new_body', mount, new=True)
        for i, pad in enumerate(p['pads'], 1):
            sk = sketch(f'SK_MOUNT_{suffix}_PAD_{i}', plane(PAD_ROOT_Z), ring(pad))
            extrude(f'MOUNT_{suffix}_PAD_{i}', sk, f'plate_top_Z - TBD_plate_T - {PAD_ROOT_Z}', 'join', mount)
        for name, boss in p['bosses'].items():
            sk = sketch(f'SK_MOUNT_{suffix}_{name}_BOSS', plane(PAD_ROOT_Z), ring(boss))
            extrude(f'MOUNT_{suffix}_{name}_BOSS', sk, f'plate_top_Z - TBD_plate_T - {PAD_ROOT_Z}', 'join', mount)
        for (i, key), hit in p['clearances'].items():
            sk = sketch(f'SK_MOUNT_{suffix}_PAD_{i}_SWITCH_{key}', plane('TBD_frame_T + TBD_standoff_H - 3 - 0.05'),
                        ring(hit))
            extrude(f'MOUNT_{suffix}_PAD_{i}_SWITCH_{key}', sk,
                    'plate_top_Z - TBD_plate_T - (TBD_frame_T + TBD_standoff_H - 3) + 0.1', 'cut', mount)
        if p['nut'] is not None:
            cylinder(f'MOUNT_{suffix}_SEAM_NUT_CLEARANCE', ('seam_M2_X', 'seam_M2_Y'), str(PAD_ROOT_Z),
                     f'plate_top_Z - TBD_plate_T - {PAD_ROOT_Z}', str(SEAM_NUT_CLEARANCE[1]), mount)
        for name in p['bores']:
            _, _, expr = SO_ANCHORS[name]
            cylinder(f'MOUNT_{suffix}_{name}_BORE', expr, -1.0, 'plate_top_Z - TBD_plate_T + 2',
                     '(TBD_so_screw_D + TBD_so_clr) / 2', mount)
            cylinder(f'MOUNT_{suffix}_{name}_INSERT', expr, 'TBD_frame_T', 'v5_so_insert_hole_depth + 0.1',
                     '(v5_so_insert_hole_D) / 2', mount)
        for name, (anchor, axis, half, head) in ((n, v[1:]) for n, v in CASE_ANCHORS.items() if v[0] == suffix):
            expr = (f'CAND_{name}_X', f'CAND_{name}_Y')
            half_expr = 'TBD_case_adjust' if half == CASE_ADJUST else str(half)
            stadium(f'MOUNT_{suffix}_{name}_SLOT', expr, axis, half_expr, 'TBD_case_screw_D + TBD_case_screw_clr',
                    -1.0, 'plate_top_Z - TBD_plate_T + 2', mount)
            if head:
                stadium(f'MOUNT_{suffix}_{name}_HEAD', expr, axis, half_expr, 'TBD_case_head_D + TBD_case_head_clr',
                        'TBD_frame_T - TBD_case_head_H',
                        'plate_top_Z - TBD_plate_T - (TBD_frame_T - TBD_case_head_H) + 0.1', mount)
        floor = f'plate_top_Z - TBD_upper_plate_T - {MX_PIN_DEPTH_FROM_SEAT} - 0.6'
        for key, pocket in p['reliefs'].items():
            sk = sketch(f'SK_MOUNT_{suffix}_PIN_RELIEF_{key}', plane(floor), ring(pocket.simplify(0.01)))
            extrude(f'MOUNT_{suffix}_PIN_RELIEF_{key}', sk, f'TBD_frame_T + 0.05 - ({floor})', 'cut', mount)
