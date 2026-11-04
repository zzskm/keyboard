"""Apply small Z-rotation so case inner walls align with axes; report fitted angle."""
import sys
import numpy as np
sys.path.insert(0, sys.argv[0].rsplit('/', 1)[0])
from loops2 import section
d = np.load(sys.argv[1]); lab = np.load(sys.argv[2])
V, N = d['V'].astype(float), d['nrm'].astype(float)
sel = lab == 0
S = section(V[sel], N[sel], 12.0)
P = S.reshape(-1, 2)
angs = []
# left inner wall: x near 301.3, right inner 593.7 ; front inner y near -2.25, back inner 99.7
for name, cond, ax in [('L', np.abs(P[:, 0] - 301.33) < 0.2, 0), ('R', np.abs(P[:, 0] - 593.70) < 0.2, 0), ('Lo', np.abs(P[:, 0] - 291.06) < 0.2, 0), ('Ro', np.abs(P[:, 0] - 603.97) < 0.2, 0)]:
    q = P[cond & (P[:, 1] > 5) & (P[:, 1] < 90)]
    k = np.polyfit(q[:, 1], q[:, 0], 1)[0]; angs.append(np.degrees(np.arctan(k)))
    print(name, 'dx/dy', k, 'deg', angs[-1], len(q))
for name, cond in [('F', np.abs(P[:, 1] + 2.25) < 0.2), ('B', np.abs(P[:, 1] - 99.68) < 0.2), ('Fo', np.abs(P[:, 1] + 13.99) < 0.2), ('Bo', np.abs(P[:, 1] - 103.72) < 0.2)]:
    q = P[cond & (P[:, 0] > 320) & (P[:, 0] < 570)]
    k = np.polyfit(q[:, 0], q[:, 1], 1)[0]; angs.append(-np.degrees(np.arctan(k)))
    print(name, 'dy/dx', k, 'deg', angs[-1], len(q))
angs = [a for a in angs if abs(a) < 1]; psi = np.radians(np.median(angs))
print('mean skew deg', np.degrees(psi))
# rotate by +psi about Z: x' = x cos - y sin ... we want walls with dx/dy=k -> 0 : rotate by +atan(k)
c, s = np.cos(psi), np.sin(psi)
Rz = np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])
V2 = V @ Rz.T; N2 = N @ Rz.T
np.savez_compressed(sys.argv[3], V=V2.astype(np.float32), nrm=N2.astype(np.float32), area=d['area'], R=Rz @ d['R'], th=d['th'], psi=psi)
