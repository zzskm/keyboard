"""Line crossings of a z-section. usage: crossings.py mesh.npz labels.npy comps z"""
import sys
import numpy as np
sys.path.insert(0, sys.argv[0].rsplit('/', 1)[0])
from loops2 import section, fit_circle
d = np.load(sys.argv[1]); lab = np.load(sys.argv[2])
comps = [int(c) for c in sys.argv[3].split(',')]; z = float(sys.argv[4])
sel = np.isin(lab, comps)
S = section(d['V'].astype(float)[sel], d['nrm'].astype(float)[sel], z)
def cross(axis, val):
    a, b = S[:, 0], S[:, 1]
    o = 1 - axis
    m = (a[:, axis] - val) * (b[:, axis] - val) < 0
    f = (val - a[m, axis]) / (b[m, axis] - a[m, axis])
    return np.sort(a[m, o] + f * (b[m, o] - a[m, o]))
for yv in [5, 20, 30, 48, 60, 80, 95]:
    print(f'z={z} y={yv}: x =', np.round(cross(1, yv), 3))
for xv in [310, 330, 360, 400, 450, 500, 550, 580]:
    print(f'z={z} x={xv}: y =', np.round(cross(0, xv), 3))
