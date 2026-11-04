"""Fit corner radii on a z-section. usage: corners.py mesh.npz labels.npy comps z x0 x1 y0 y1 [band]
(x0,x1,y0,y1) = the straight-wall coordinates of one rectangle (inner or outer) to fit corners for."""
import sys
import numpy as np
sys.path.insert(0, sys.argv[0].rsplit('/', 1)[0])
from loops2 import section, fit_circle
d = np.load(sys.argv[1]); lab = np.load(sys.argv[2])
comps = [int(c) for c in sys.argv[3].split(',')]; z = float(sys.argv[4])
x0, x1, y0, y1 = map(float, sys.argv[5:9]); band = float(sys.argv[9]) if len(sys.argv) > 9 else 12
sel = np.isin(lab, comps)
S = section(d['V'].astype(float)[sel], d['nrm'].astype(float)[sel], z)
P = np.unique(np.round(S.reshape(-1, 2), 5), axis=0)
res = []
for name, cx, cy, sx, sy in [('FL', x0, y0, 1, 1), ('FR', x1, y0, -1, 1), ('BL', x0, y1, 1, -1), ('BR', x1, y1, -1, -1)]:
    dx = (P[:, 0] - cx) * sx; dy = (P[:, 1] - cy) * sy
    m = (dx > 0.003) & (dy > 0.003) & (dx < band) & (dy < band)
    # keep only the points closest to the corner (the corner arc), not other features
    q = P[m]
    if len(q) < 4:
        print(name, 'no arc points'); continue
    # arc points satisfy: near the boundary, i.e. min(dx,dy) small relative to band; keep points with max(dx,dy) < band and lying on a convex curve
    c, r, e = fit_circle(q)
    print(f'{name}: n={len(q)} center=({c[0]:.3f},{c[1]:.3f}) R={r:.3f} maxres={e:.3f}  tangent-check dx={abs(c[0]-cx):.3f} dy={abs(c[1]-cy):.3f}')
