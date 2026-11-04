"""X-section (plane x=val) of keyboard-frame mesh; list z crossings at given y per component, and y crossings at given z.
usage: vcross.py mesh.npz labels.npy xval"""
import sys
import numpy as np
d = np.load(sys.argv[1]); lab = np.load(sys.argv[2]); xv = float(sys.argv[3])
V = d['V'].astype(float)
dist = V[:, :, 0] - xv
m = (dist > 0).any(1) & (dist <= 0).any(1)
segs, L = [], []
for t, dd, l in zip(V[m], dist[m], lab[m]):
    pts = []
    for i, j in ((0, 1), (1, 2), (2, 0)):
        if (dd[i] > 0) != (dd[j] > 0):
            f = dd[i] / (dd[i] - dd[j]); pts.append(t[i, 1:] + f * (t[j, 1:] - t[i, 1:]))
    if len(pts) == 2: segs.append(pts); L.append(l)
S = np.array(segs); L = np.array(L)
def cr(axis, val, comp):
    s = S[L == comp]; a, b = s[:, 0], s[:, 1]; o = 1 - axis
    mm = (a[:, axis] - val) * (b[:, axis] - val) < 0
    f = (val - a[mm, axis]) / (b[mm, axis] - a[mm, axis])
    return np.round(np.sort(a[mm, o] + f * (b[mm, o] - a[mm, o])), 3)
for comp in sorted(set(L)):
    print('comp', comp)
    for yv in [-12, -8, -5, -1.5, 0, 2, 10, 48, 90, 96, 98, 101, 103]:
        r = cr(0, yv, comp)
        if len(r): print(f'   y={yv}: z={r}')
    for zv in [0.5, 2, 3.2, 5, 10, 15, 18, 19, 20, 20.5, 21, 21.1]:
        r = cr(1, zv, comp)
        if len(r): print(f'   z={zv}: y={r}')
np.savez(sys.argv[4], S=S, L=L) if len(sys.argv) > 4 else None
