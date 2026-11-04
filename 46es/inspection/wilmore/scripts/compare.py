"""Overlay z-sections of the SolidCraft housing (model frame) and the Wilmore mesh (kb2 frame shifted to model frame).
usage: compare.py wil_kb2.npz wil_lab.npy housing.stl out_prefix"""
import sys, struct
import numpy as np
sys.path.insert(0, sys.argv[0].rsplit('/', 1)[0])
from loops2 import section
from render import write_png
OFF = np.array([305.004, 1.441, 8.730])
d = np.load(sys.argv[1]); lab = np.load(sys.argv[2])
VW = d['V'].astype(float) - OFF; NW = d['nrm'].astype(float)
keep = np.isin(lab, [0, 2, 3, 4, 5, 1])
VW, NW, LW = VW[keep], NW[keep], lab[keep]
with open(sys.argv[3], 'rb') as f:
    f.read(80); n = struct.unpack('<I', f.read(4))[0]
    dt = np.dtype([('n', '<f4', 3), ('v', '<f4', (3, 3)), ('a', '<u2')])
    H = np.fromfile(f, dtype=dt, count=n)
VH = H['v'].astype(float)
e1 = VH[:, 1] - VH[:, 0]; e2 = VH[:, 2] - VH[:, 0]; NH = np.cross(e1, e2); NH /= np.maximum(np.linalg.norm(NH, axis=1, keepdims=True), 1e-12)
print('housing tris', n, 'bbox', VH.reshape(-1, 3).min(0).round(3), VH.reshape(-1, 3).max(0).round(3))
def cross(S, axis, val):
    a, b = S[:, 0], S[:, 1]; o = 1 - axis
    m = (a[:, axis] - val) * (b[:, axis] - val) < 0
    f = (val - a[m, axis]) / (b[m, axis] - a[m, axis])
    return np.sort(a[m, o] + f * (b[m, o] - a[m, o]))
for z in [-5.5, -3.0, 0.0 - 0.3, 4.0, 10.0]:
    SH = section(VH, NH, z); SW = section(VW, NW, z)
    print(f'--- z={z}')
    for axis, vals in [(1, [10, 38.1, 47.6, 66.7]), (0, [18.7, 25.2, 128.2, 190.5, 260.05])]:
        for v in vals:
            h = cross(SH, axis, v); w = cross(SW, axis, v)
            print(f'  {"y" if axis == 1 else "x"}={v}: housing {np.round(h, 2)}  |  wilmore {np.round(w, 2)}')
    # overlay image
    s = 3.0; allp = np.concatenate([SH.reshape(-1, 2), SW.reshape(-1, 2)])
    mn = allp.min(0) - 2; mx = allp.max(0) + 2
    w_, h_ = int((mx[0] - mn[0]) * s) + 1, int((mx[1] - mn[1]) * s) + 1
    img = np.full((h_, w_, 3), 255, np.uint8)
    for col, S in [((230, 80, 40), SW), ((20, 60, 200), SH)]:
        for (a, b) in S:
            k = int(max(abs(b - a)) * s * 2) + 2; t = np.linspace(0, 1, k)[:, None]; p = a + t * (b - a)
            img[h_ - 1 - ((p[:, 1] - mn[1]) * s).astype(int), ((p[:, 0] - mn[0]) * s).astype(int)] = col
    write_png(f'{sys.argv[4]}_z{z}.png', img)
