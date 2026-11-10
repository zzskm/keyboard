"""Decoration on the cover top (user 2026-11-10): the name engraved small on the left piece.

TEXT in a square single-stroke face drawn here (no font file): every letter is straight strokes on a GLYPH_W x
TEXT_HEIGHT cell, square corners and flat ends, all the same height, the e as three bars. Strokes are TEXT_STROKE wide; with
bars half a height apart the rib between them is TEXT_HEIGHT / 2 - TEXT_STROKE, which the resin wall rule (1.0)
keeps from going smaller; letters are TEXT_GAP apart (rib TEXT_GAP - TEXT_STROKE). It sits on L at the top of the left block beside the key
window (place picked by the user on a screenshot), centred on TEXT_AT.

It is cut v5_cover_pattern_depth down from the top (Z 19 -> 18), a blind pocket, nothing goes through. The loops are
fixed numbers in the sketch, regenerated from these constants (like the window outline). A groove is
(outer loop, [island loops]); the cut leaves the islands standing.
"""
from cover_v5 import COVER_L, SPLIT_CUTS

DEPTH = 1.0            # engraving depth (parameter v5_cover_pattern_depth)
TEXT = '46es'
TEXT_HEIGHT = 2.8      # letter height on the stroke centre lines (rib between bars 2.8 / 2 - 0.4 = 1.0)
TEXT_STROKE = 0.4
GLYPH_W = 1.5          # letter width on the stroke centre lines
TEXT_GAP = 1.5         # gap between letters (rib 1.1); the name is 4 x 1.5 + 3 x 1.5 + stroke = 10.9 wide
TEXT_AT = (11.0, 40.5)  # centre of the text box: L left block (X -0.4..22, Y 29..45), under its rear edge
TEXT_EDGE = 1.0        # full-height wall kept from the text to the cover edge and window
# Cover outline: the case inner size minus the cover gap, corner radius TBD_cover_R (cover_v5 outline sketch).
CASE_IN, PCB0, COVER_GAP, COVER_R_CORNER = (286.381, 95.934), (0.693, 0.667), 0.3, 2.5


def top_face(windows):
    """Plan polygon of the cover top face: outline minus the split cut and the silhouette window."""
    from shapely.geometry import Polygon, box
    from shapely.ops import unary_union
    x0, y0 = COVER_GAP - PCB0[0], COVER_GAP - PCB0[1]
    x1, y1 = CASE_IN[0] - PCB0[0] - COVER_GAP, CASE_IN[1] - PCB0[1] - COVER_GAP
    outline = box(x0, y0, x1, y1).buffer(-COVER_R_CORNER).buffer(COVER_R_CORNER)
    cut = unary_union([Polygon(p) for p in SPLIT_CUTS] + [Polygon(p) for p in windows])
    return outline.difference(cut), cut


def glyphs():
    """Square single-stroke letters on a GLYPH_W x TEXT_HEIGHT cell, in units of TEXT_HEIGHT: {char: [polyline]}."""
    w = GLYPH_W / TEXT_HEIGHT
    return {
        '4': [[(0, 1), (0, 0.5), (w, 0.5)], [(w, 1), (w, 0)]],
        '6': [[(w, 1), (0, 1), (0, 0), (w, 0), (w, 0.5), (0, 0.5)]],
        'e': [[(0, 1), (w, 1)], [(0, 0.5), (w, 0.5)], [(0, 0), (w, 0)]],
        's': [[(w, 1), (0, 1), (0, 0.5), (w, 0.5), (w, 0), (0, 0)]],
    }


def text_shape():
    """The name as one shapely geometry: stroke centre lines scaled to TEXT_HEIGHT, widened to TEXT_STROKE with
    mitred corners and square ends."""
    from shapely.geometry import LineString
    from shapely.ops import unary_union
    table = glyphs()
    width = GLYPH_W * len(TEXT) + TEXT_GAP * (len(TEXT) - 1)
    x0, y0 = TEXT_AT[0] - width / 2, TEXT_AT[1] - TEXT_HEIGHT / 2
    lines = [LineString([(x0 + i * (GLYPH_W + TEXT_GAP) + u * TEXT_HEIGHT, y0 + v * TEXT_HEIGHT) for u, v in st])
             for i, ch in enumerate(TEXT) for st in table[ch]]
    return unary_union([ln.buffer(TEXT_STROKE / 2, cap_style=3, join_style=2) for ln in lines])


def _loops(shape):
    def ring(r):
        return [(round(x, 4), round(y, 4)) for x, y in r.coords[:-1]]
    out = []
    for g in getattr(shape, 'geoms', [shape]):
        if g.is_empty or g.geom_type != 'Polygon':
            continue
        g = g.simplify(1e-3)
        out.append((ring(g.exterior), [ring(i) for i in g.interiors]))
    return out


def pattern(windows):
    """{name: (cover piece, [(outer loop, [island loops])])} for the window polygons the build cuts."""
    top, _ = top_face(windows)
    faces = sorted(top.geoms, key=lambda g: g.centroid.x)          # L, T, R
    assert len(faces) == 3, len(faces)
    text = text_shape()
    assert faces[0].buffer(-TEXT_EDGE).contains(text), 'the name does not fit the left block'
    return {'L_name': (COVER_L, _loops(text))}


def emit(feature, sketch, windows, top_plane):
    """One sketch and one blind cut per decoration, after the silhouette window. The cut names each groove by the
    curves of its outer loop; the loops inside it are then its islands and stay (profiles 'all' would cut them too)."""
    for name, (piece, grooves) in pattern(windows).items():
        loops, outers, n = [], [], 0
        for outer, islands in grooves:           # build_seam_v5.helpers' sketch() numbers the lines l1.. in loop order
            outers.append([f'l{n + j + 1}' for j in range(len(outer))])
            for loop in [outer, *islands]:
                loops.append(loop)
                n += len(loop)
        sk = sketch(f'SK36_COVER_PATTERN_V5_{name}', top_plane, loops)
        feature('extrude', f'COVER_PATTERN_V5_{name}', sketch=sk, profiles=dict(type='curves', loops=outers),
                extent=dict(convention='total_distance', direction='negative', distance='v5_cover_pattern_depth'),
                operation='cut', targets=[piece])


def floor_areas(windows):
    """Expected engraved floor area per cover piece (groove area without its islands)."""
    from shapely.geometry import Polygon
    out = {}
    for piece, grooves in pattern(windows).values():
        out[piece] = out.get(piece, 0.0) + sum(Polygon(outer, islands).area for outer, islands in grooves)
    return out


def check_levels(levels, top_z, windows, tol=0.02):
    """Each cover's upward faces: the top at top_z and, where the piece carries a decoration, the engraved floor at
    top_z - DEPTH with the groove area (relative tol). Returns the checked floor areas."""
    floors = floor_areas(windows)
    floor_z = round(top_z - DEPTH, 4)
    out = {}
    for name, faces in levels.items():
        want = {round(top_z, 4)} | ({floor_z} if name in floors else set())
        assert set(faces) == want, (name, faces)
        if name in floors:
            assert abs(faces[floor_z] - floors[name]) <= tol * floors[name], (name, faces[floor_z], floors[name])
            out[name] = dict(floor_Z=floor_z, floor_area_mm2=faces[floor_z], expected_mm2=round(floors[name], 3))
    return out
