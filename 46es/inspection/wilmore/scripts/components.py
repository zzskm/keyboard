import sys
import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
d = np.load(sys.argv[1]); V = d['V'].astype(float)
P = np.round(V.reshape(-1, 3), 4)
uv, inv = np.unique(P, axis=0, return_inverse=True); inv = inv.reshape(-1, 3)
n = len(uv)
r = np.r_[inv[:, 0], inv[:, 1]]; c = np.r_[inv[:, 1], inv[:, 2]]
g = coo_matrix((np.ones(len(r)), (r, c)), shape=(n, n))
k, lab = connected_components(g, directed=False)
tl = lab[inv[:, 0]]
# relabel by size
u, cnt = np.unique(tl, return_counts=True)
order = u[np.argsort(-cnt)]
remap = np.zeros(k, int); remap[order] = np.arange(len(order))
tl = remap[tl]
np.save(sys.argv[2], tl)
for i in range(len(order)):
    m = tl == i
    pts = V[m].reshape(-1, 3)
    print(i, m.sum(), pts.min(0).round(3), pts.max(0).round(3))
