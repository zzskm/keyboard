"""Plan sections of a binary STL, compared with expected 2D profiles (numpy + shapely)."""
import struct

import numpy as np
from shapely.geometry import MultiLineString, Polygon
from shapely.ops import polygonize, unary_union


def read_stl(path):
    data = open(path, 'rb').read()
    n = struct.unpack_from('<I', data, 80)[0]
    if len(data) != 84 + 50 * n:
        raise ValueError(f'{path}: not a binary STL')
    rec = np.frombuffer(data, dtype=np.dtype([('n', '<f4', 3), ('v', '<f4', (3, 3)), ('a', '<u2')]), count=n, offset=84)
    return rec['v'].astype(np.float64)


def section(tris, z, snap=1e-4):
    """Material region of the mesh in the plane Z=z (even-odd nesting of the cut loops)."""
    segments = []
    for tri in tris:
        above = tri[:, 2] > z
        if above.all() or (~above).all():
            continue
        points = []
        for i in range(3):
            a, b = tri[i], tri[(i + 1) % 3]
            if (a[2] > z) != (b[2] > z):
                t = (z - a[2]) / (b[2] - a[2])
                points.append((round(a[0] + t * (b[0] - a[0]), 4), round(a[1] + t * (b[1] - a[1]), 4)))
        if len(points) == 2 and points[0] != points[1]:
            segments.append(points)
    # polygonize already assigns holes to shells; nest by shell containment so a hole face
    # (depth 1) is removed and an island inside a hole (depth 2) is kept
    faces = list(polygonize(unary_union(MultiLineString(segments))))
    shells = [Polygon(face.exterior) for face in faces]
    depth = {}
    for i, face in enumerate(faces):
        point = face.representative_point()          # inside the face's own material, never in one of its holes
        depth[i] = sum(1 for j, other in enumerate(shells) if j != i and other.contains(point))
    result = Polygon()
    for level in range(max(depth.values(), default=-1) + 1):
        layer = unary_union([shells[i] for i in depth if depth[i] == level])
        result = result.union(layer) if level % 2 == 0 else result.difference(layer)
    return result.buffer(0)


def align(tris, bounds):
    """Translate a print-oriented mesh (box moved to 0,0) back to the plan bounds of its outline."""
    shift = np.array([bounds[0] - tris[:, :, 0].min(), bounds[1] - tris[:, :, 1].min(), 0.0])
    return tris + shift


def compare(tris, expected, max_area=0.5, max_distance=0.1):
    """Per height: symmetric difference area and boundary Hausdorff distance against the expected profile."""
    report = {}
    for z, shape in expected.items():
        cut = section(tris, z)
        area = cut.symmetric_difference(shape).area
        distance = cut.boundary.hausdorff_distance(shape.boundary) if not cut.is_empty else float('inf')
        report[z] = dict(section_area=round(cut.area, 3), expected_area=round(shape.area, 3),
                         symmetric_difference_mm2=round(area, 4), boundary_deviation_mm=round(distance, 4),
                         ok=bool(area <= max_area and distance <= max_distance))
    return report
