"""Decoration on the cover top (user 2026-11-10, font and text 2026-11-11): the name engraved small on the left piece.

TEXT is set in the Xifiction font by Nowak.tv (user 2026-11-11), from dafont: https://www.dafont.com/xifiction.font
("Free for personal use" there; the file says "freeware [for non-commercial use]"). The
font file is not committed: FONT_DATA holds only the outlines of the glyphs TEXT uses, flattened to straight
segments in font units, and `python 46es/tools/cover_pattern_v5.py --font Xifiction.ttf` rewrites it from the TTF.
The glyphs sit on a 200-unit grid in a 1200 x 1600 cell with a 1399 advance: strokes 400, counters and the gap
between letters 200 (199), so at TEXT_HEIGHT (the 1600 cell) the stroke is TEXT_HEIGHT / 4 and the narrowest rib
TEXT_HEIGHT / 8. That rib is below the resin wall rule (1.0) at any size that fits the left block; the user chose
this place and a smaller size anyway (2026-11-11) and the boss tab carries the same engraving to test it.
It sits on L at the top of the left block beside the key window (place picked by the user on a screenshot),
centred on TEXT_AT.

It is cut v5_cover_pattern_depth down from the top (Z 19 -> 18), a blind pocket, nothing goes through. The loops are
fixed numbers in the sketch, regenerated from these constants and FONT_DATA (like the window outline). A groove is
(outer loop, [island loops]); the cut leaves the islands standing.
"""
import json
from pathlib import Path

from cover_v5 import COVER_L

DEPTH = 1.0            # engraving depth (parameter v5_cover_pattern_depth)
TEXT = 'kb46es/26'
TEXT_HEIGHT = 2.0      # glyph cell height (font units 0..1600): stroke 0.5, narrowest rib 0.25, 15.5 wide
TEXT_AT = (11.0, 40.5)  # centre of the text box: L left block (X -0.4..22, Y 29..45), under its rear edge
TEXT_EDGE = 1.0        # full-height wall kept from the text to the cover edge and window
FONT_DATA = Path(__file__).with_name('cover_logo_xifiction.json')
CURVE_SEGMENTS = 6     # straight segments per quadratic curve when FONT_DATA is written
# Cover outline: the case inner size minus the cover gap, corner radius TBD_cover_R (cover_v5 outline sketch).
CASE_IN, PCB0, COVER_GAP, COVER_R_CORNER = (286.381, 95.934), (0.693, 0.667), 0.3, 2.5


def font():
    return json.loads(FONT_DATA.read_text(encoding='utf-8'))


def scale():
    """mm per font unit at TEXT_HEIGHT."""
    return TEXT_HEIGHT / font()['cell_height']


def stroke():
    """Glyph stroke width in mm (400 units)."""
    return round(font()['stroke'] * scale(), 4)


def rib():
    """Narrowest rib left standing in mm: counters and the gap between letters (200 units)."""
    return round(font()['rib'] * scale(), 4)


def top_face(windows):
    """Plan polygon of the cover top face: outline minus the window cut (silhouette and split gaps)."""
    from shapely.geometry import Polygon, box
    from shapely.ops import unary_union
    x0, y0 = COVER_GAP - PCB0[0], COVER_GAP - PCB0[1]
    x1, y1 = CASE_IN[0] - PCB0[0] - COVER_GAP, CASE_IN[1] - PCB0[1] - COVER_GAP
    outline = box(x0, y0, x1, y1).buffer(-COVER_R_CORNER).buffer(COVER_R_CORNER)
    cut = unary_union([Polygon(p) for p in windows])
    return outline.difference(cut), cut


def text_shape():
    """The name as one shapely geometry: the glyph outlines of FONT_DATA scaled to TEXT_HEIGHT, centred on TEXT_AT.
    Each glyph's contours are combined even-odd (outer ring, counters as holes)."""
    from shapely.geometry import Polygon
    from shapely.ops import unary_union
    data = font()
    k = scale()
    advance = [data['glyphs'][ch]['advance'] for ch in TEXT]
    left, right = data['glyphs'][TEXT[0]]['xmin'], sum(advance[:-1]) + data['glyphs'][TEXT[-1]]['xmax']
    x0, y0 = TEXT_AT[0] - (left + right) / 2 * k, TEXT_AT[1] - TEXT_HEIGHT / 2
    out, pen = [], 0.0
    for ch, adv in zip(TEXT, advance):
        glyph = Polygon()
        for ring in data['glyphs'][ch]['contours']:
            glyph = glyph.symmetric_difference(Polygon([(x0 + (pen + u) * k, y0 + v * k) for u, v in ring]))
        out.append(glyph)
        pen += adv
    return unary_union(out)


def write_font_data(ttf):
    """FONT_DATA from the TTF: the TEXT glyphs' contours, quadratic curves split into CURVE_SEGMENTS lines."""
    from fontTools.pens.basePen import BasePen
    from fontTools.ttLib import TTFont
    from common import write_json

    class Pen(BasePen):
        def __init__(self, glyphs):
            super().__init__(glyphs)
            self.rings, self.ring = [], []

        def _moveTo(self, p):
            self.ring = [p]

        def _lineTo(self, p):
            self.ring.append(p)

        def _qCurveToOne(self, a, b):
            p0 = self.ring[-1]
            for i in range(1, CURVE_SEGMENTS + 1):
                t = i / CURVE_SEGMENTS
                self.ring.append(tuple((1 - t) ** 2 * p0[j] + 2 * (1 - t) * t * a[j] + t * t * b[j] for j in (0, 1)))

        def _curveToOne(self, a, b, c):
            raise ValueError('cubic outline: expected a TrueType font')

        def _closePath(self):
            ring = [(round(x, 2), round(y, 2)) for x, y in self.ring]
            ring = [q for i, q in enumerate(ring) if q != ring[i - 1]]
            self.rings.append([list(q) for q in ring])
            self.ring = []

    f = TTFont(ttf)
    names = {r.nameID: r.toUnicode() for r in f['name'].names if r.platformID == 3}
    glyph_set, cmap = f.getGlyphSet(), f.getBestCmap()
    glyphs = {}
    for ch in sorted(set(TEXT)):
        g = glyph_set[cmap[ord(ch)]]
        pen = Pen(glyph_set)
        g.draw(pen)
        xs = [x for r in pen.rings for x, _ in r]
        glyphs[ch] = dict(name=cmap[ord(ch)], advance=g.width, xmin=min(xs), xmax=max(xs), contours=pen.rings)
    write_json(FONT_DATA, dict(
        font=names.get(4), version=names.get(5), license=names.get(0), units_per_em=f['head'].unitsPerEm,
        source='https://www.dafont.com/xifiction.font (Nowak.tv, "Free for personal use")',
        cell_height=1600, stroke=400, rib=200,
        note='Outlines of the glyphs in cover_pattern_v5.TEXT only, curves flattened. Rewrite with '
             'python 46es/tools/cover_pattern_v5.py --font <Xifiction.ttf>',
        glyphs=glyphs))


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


if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser(description='Rewrite FONT_DATA from the font file')
    ap.add_argument('--font', required=True)
    write_font_data(ap.parse_args().font)
    print(FONT_DATA, text_shape().bounds)
