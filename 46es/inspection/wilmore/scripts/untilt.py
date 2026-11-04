import sys
import numpy as np
d = np.load(sys.argv[1]); lab = np.load(sys.argv[2])
V, N, A = d['V'].astype(float), d['nrm'].astype(float), d['area'].astype(float)
m = (lab == 1) & (N[:, 2] > 0.9)
n = (N[m] * A[m, None]).sum(0); n /= np.linalg.norm(n)
th = np.arctan2(-n[1], n[2])
print('mean up normal comp1', n, 'tilt deg', np.degrees(th))
for c in [0, 2]:
    mm = (lab == c) & (N[:, 2] > 0.99) & (np.abs(np.degrees(np.arctan2(-N[:, 1], N[:, 2])) - np.degrees(th)) < 0.1)
    nn = (N[mm] * A[mm, None]).sum(0); nn /= np.linalg.norm(nn)
    print('comp', c, 'tilt', np.degrees(np.arctan2(-nn[1], nn[2])))
c, s = np.cos(th), np.sin(th)
R = np.array([[1, 0, 0], [0, c, s], [0, -s, c]])
V2 = V @ R.T; N2 = N @ R.T
print('check normal', (n @ R.T).round(6))
P = V2.reshape(-1, 3)
print('rotated bbox', P.min(0).round(3), P.max(0).round(3))
for k in range(7):
    q = V2[lab == k].reshape(-1, 3)
    print(k, q.min(0).round(3), q.max(0).round(3))
np.savez_compressed(sys.argv[3], V=V2.astype(np.float32), nrm=N2.astype(np.float32), area=A.astype(np.float32), R=R, th=th)
