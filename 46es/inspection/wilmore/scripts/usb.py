import sys
import numpy as np
sys.path.insert(0, sys.argv[0].rsplit('/', 1)[0])
from loops2 import section
d = np.load(sys.argv[1]); lab = np.load(sys.argv[2])
V, N = d['V'].astype(float), d['nrm'].astype(float)
for comp in [0, 2]:
    sel = lab == comp
    for z in np.arange(2.6, 21.2, 0.5):
        S = section(V[sel], N[sel], z)
        for yv in ([98.0, 101.0, 103.5] if comp == 0 else [98.2]):
            a, b = S[:, 0], S[:, 1]
            mm = (a[:, 1] - yv) * (b[:, 1] - yv) < 0
            f = (yv - a[mm, 1]) / (b[mm, 1] - a[mm, 1]); xs = np.sort(a[mm, 0] + f * (b[mm, 0] - a[mm, 0]))
            xs = xs[(xs > 300) & (xs < 360)]
            if len(xs): print(f'comp{comp} z={z:.1f} y={yv}: x={np.round(xs, 3)}')
