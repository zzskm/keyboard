"""Put a binary STL into print orientation: optional 180 deg turn about X, then move its box to start at 0,0,0.

python -I orient_print_stl.py IN.stl OUT.stl [--flip]

--flip turns the part over (x, y, z) -> (x, -y, -z), so a face that was on top ends on the bed.
A rotation keeps the facet winding valid, so no facet is reordered.
"""
import struct, sys


def orient(src, dst, flip):
    data = open(src, 'rb').read()
    n = struct.unpack_from('<I', data, 80)[0]
    if len(data) != 84 + 50 * n:
        raise ValueError(f'{src}: not a binary STL')
    tris = []
    for i in range(n):
        v = struct.unpack_from('<12fH', data, 84 + 50 * i)
        pts = [list(v[j:j + 3]) for j in (0, 3, 6, 9)]  # normal, a, b, c
        if flip:
            for p in pts:
                p[1], p[2] = -p[1], -p[2]
        tris.append((pts, v[12]))
    lo = [min(p[k] for pts, _ in tris for p in pts[1:]) for k in range(3)]
    out = bytearray(b'46es v4 print orientation'.ljust(80, b' '))
    out += struct.pack('<I', n)
    for pts, attr in tris:
        nrm = pts[0]
        verts = [[p[k] - lo[k] for k in range(3)] for p in pts[1:]]
        out += struct.pack('<12fH', *nrm, *verts[0], *verts[1], *verts[2], attr)
    open(dst, 'wb').write(out)
    return lo


if __name__ == '__main__':
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    if len(args) != 2:
        sys.exit(__doc__)
    print(orient(args[0], args[1], '--flip' in sys.argv))
