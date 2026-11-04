"""Plane y=val section of one comp; prints z-crossings at x list and x-crossings at z list; fits arcs. usage: ysec.py mesh labels comp yval"""
import sys
import numpy as np
d = np.load(sys.argv[1]); lab = np.load(sys.argv[2]); comp = int(sys.argv[3]); yv = float(sys.argv[4])
V = d['V'].astype(float)[lab == comp]
dist = V[:, :, 1] - yv
m = (dist > 0).any(1) & (dist <= 0).any(1)
segs = []
for t, dd in zip(V[m], dist[m]):
    pts = []
    for i, j in ((0, 1), (1, 2), (2, 0)):
        if (dd[i] > 0) != (dd[j] > 0):
            f = dd[i] / (dd[i] - dd[j]); pts.append(t[i, [0, 2]] + f * (t[j, [0, 2]] - t[i, [0, 2]]))
    if len(pts) == 2: segs.append(pts)
S = np.array(segs)
def cr(axis, val):
    a, b = S[:, 0], S[:, 1]; o = 1 - axis
    mm = (a[:, axis] - val) * (b[:, axis] - val) < 0
    f = (val - a[mm, axis]) / (b[mm, axis] - a[mm, axis])
    return np.round(np.sort(a[mm, o] + f * (b[mm, o] - a[mm, o])), 3)
xs = [float(v) for v in sys.argv[5].split(',')]; zs = [float(v) for v in sys.argv[6].split(',')]
for x in xs: print(f'y={yv} x={x}: z={cr(0, x)}')
for z in zs:
    r = cr(1, z); print(f'y={yv} z={z}: x={r[(r > float(sys.argv[7])) & (r < float(sys.argv[8]))] if len(sys.argv) > 8 else r}')
