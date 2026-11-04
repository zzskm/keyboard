import numpy as np, sys
from collections import defaultdict
d = np.load(sys.argv[1]); S, L = d['S'], d['L']
S0 = S[L == int(sys.argv[2])]
key = lambda p: (round(p[0]*1000), round(p[1]*1000))
adj = defaultdict(list)
for i,(a,b) in enumerate(S0): adj[key(a)].append((i,0)); adj[key(b)].append((i,1))
used = np.zeros(len(S0), bool); loops=[]
for s0 in range(len(S0)):
    if used[s0]: continue
    used[s0]=True; pts=[S0[s0][0], S0[s0][1]]; cur=S0[s0][1]
    while True:
        nx=[(i,e) for (i,e) in adj[key(cur)] if not used[i]]
        if not nx: break
        i,e=nx[0]; used[i]=True; cur=S0[i][1-e]; pts.append(cur)
    loops.append(np.array(pts))
def cross2(a, b): return a[..., 0]*b[..., 1] - a[..., 1]*b[..., 0]
def rdp(P, eps):
    if len(P) < 3: return P
    a, b = P[0], P[-1]; ab = b - a; n = np.linalg.norm(ab)
    dd = np.abs(cross2(ab, P - a)) / n if n > 0 else np.linalg.norm(P - a, axis=1)
    i = int(np.argmax(dd))
    if dd[i] > eps: return np.vstack([rdp(P[:i+1], eps)[:-1], rdp(P[i:], eps)])
    return np.array([a, b])
oy, oz = float(sys.argv[3]), float(sys.argv[4])
for Lp in loops:
    x, y = Lp[:,0], Lp[:,1]; ar = 0.5*np.sum(x*np.roll(y,-1)-np.roll(x,-1)*y)
    print('loop n', len(Lp), 'area', round(ar,2), 'closed', np.linalg.norm(Lp[0]-Lp[-1]) < 1e-3)
    for p in rdp(Lp, float(sys.argv[5])): print('   u=%.3f v=%.3f  | model %.3f %.3f' % (p[0], p[1], p[0]-oy, p[1]-oz))
