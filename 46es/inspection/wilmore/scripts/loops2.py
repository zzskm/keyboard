"""Directed Z-section loops (keyboard frame). usage: loops2.py mesh.npz labels.npy comps z [png scale] [loops_out.npz]"""
import sys
import numpy as np
sys.path.insert(0, sys.argv[0].rsplit('/', 1)[0])
from render import write_png

def section(V, N, z):
    dz = V[:, :, 2] - z
    pos = dz > 0
    m = pos.any(1) & (~pos).any(1)
    T, D, NN = V[m], dz[m], N[m]
    segs = []
    for t, dd, n in zip(T, D, NN):
        pts = []
        for i, j in ((0, 1), (1, 2), (2, 0)):
            if (dd[i] > 0) != (dd[j] > 0):
                f = dd[i] / (dd[i] - dd[j]); pts.append(t[i, :2] + f * (t[j, :2] - t[i, :2]))
        if len(pts) != 2: continue
        a, b = pts
        dirn = np.array([-n[1], n[0]])  # ez x n
        if np.dot(b - a, dirn) < 0: a, b = b, a
        segs.append((a, b))
    return np.array(segs)

def chain(S, tol=1e-3):
    from scipy.spatial import cKDTree
    starts = S[:, 0]; tree = cKDTree(starts)
    used = np.zeros(len(S), bool); loops = []
    for s0 in range(len(S)):
        if used[s0]: continue
        used[s0] = True; pts = [S[s0][0]]; cur = S[s0][1]
        while True:
            cand = tree.query_ball_point(cur, tol)
            cand = [c for c in cand if not used[c]]
            if not cand: break
            c = min(cand, key=lambda k: np.linalg.norm(starts[k] - cur))
            used[c] = True; pts.append(S[c][0]); cur = S[c][1]
        pts.append(cur)
        loops.append(np.array(pts))
    return loops

def area(L):
    x, y = L[:, 0], L[:, 1]
    return 0.5 * np.sum(x * np.roll(y, -1) - np.roll(x, -1) * y)

def fit_circle(P):
    A = np.c_[2 * P[:, 0], 2 * P[:, 1], np.ones(len(P))]
    b = (P ** 2).sum(1)
    c, *_ = np.linalg.lstsq(A, b, rcond=None)
    r = np.sqrt(c[2] + c[0] ** 2 + c[1] ** 2)
    return c[:2], r, np.abs(np.sqrt(((P - c[:2]) ** 2).sum(1)) - r).max()

if __name__ == '__main__':
    d = np.load(sys.argv[1]); lab = np.load(sys.argv[2])
    comps = [int(c) for c in sys.argv[3].split(',')]
    z = float(sys.argv[4])
    sel = np.isin(lab, comps)
    V = d['V'].astype(float)[sel]; N = d['nrm'].astype(float)[sel]
    S = section(V, N, z)
    loops = chain(S)
    out = []
    for L in loops:
        a = area(L)
        if abs(a) < 0.05: continue
        closed = np.linalg.norm(L[0] - L[-1]) < 1e-2
        out.append((abs(a), a, L.min(0), L.max(0), L, closed))
    out.sort(key=lambda t: -t[0])
    print(f'z={z} comps={comps} loops={len(out)} segs={len(S)}')
    for absa, a, mn, mx, L, closed in out:
        sz = mx - mn
        line = f'  {"outer" if a > 0 else "HOLE "} area {a:10.2f} bbox [{mn[0]:.3f},{mn[1]:.3f}]-[{mx[0]:.3f},{mx[1]:.3f}] size {sz[0]:.3f} x {sz[1]:.3f} n={len(L)}{"" if closed else " OPEN"}'
        if sz.max() < 15:
            c, r, e = fit_circle(L)
            line += f'  circ c=({c[0]:.3f},{c[1]:.3f}) r={r:.3f} res={e:.3f}'
        print(line)
    if len(sys.argv) > 6 and sys.argv[5] != '-':
        s = float(sys.argv[6]); allp = np.concatenate([o[4] for o in out])
        mn = allp.min(0) - 2; mx = allp.max(0) + 2
        w, h = int((mx[0] - mn[0]) * s) + 1, int((mx[1] - mn[1]) * s) + 1
        img = np.full((h, w, 3), 255, np.uint8)
        for g in np.arange(np.ceil(mn[0] / 10) * 10, mx[0], 10): img[:, int((g - mn[0]) * s)] = (225, 225, 225)
        for g in np.arange(np.ceil(mn[1] / 10) * 10, mx[1], 10): img[h - 1 - int((g - mn[1]) * s)] = (225, 225, 225)
        for (a, b) in S:
            n = int(max(abs(b - a)) * s * 2) + 2; t = np.linspace(0, 1, n)[:, None]; p = a + t * (b - a)
            img[h - 1 - ((p[:, 1] - mn[1]) * s).astype(int), ((p[:, 0] - mn[0]) * s).astype(int)] = (20, 20, 20)
        write_png(sys.argv[5], img)
    if len(sys.argv) > 7:
        np.savez(sys.argv[7], *[o[4] for o in out])
