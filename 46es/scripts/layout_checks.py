"""Read-only r2 layout checks; CAD booleans remain in SolidCraft MCP."""
import json, math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = json.loads((ROOT/'inspection/source_features_by_panel.json').read_text(encoding='utf-8-sig'))

def rect(cx, cy, w, h, deg=0):
    c,s=math.cos(math.radians(deg)),math.sin(math.radians(deg))
    return [(cx+x*c-y*s,cy+x*s+y*c) for x,y in [(-w/2,-h/2),(w/2,-h/2),(w/2,h/2),(-w/2,h/2)]]

KEYS=[dict(x=q['rx']-.693,y=q['ry']-.667,rot=q['rot']) for q in DATA['P3_astel2T']['squares']]

def cross(a,b,c): return (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])
def clip(poly, window):
    for a,b in zip(window,window[1:]+window[:1]):
        out=[]
        for p,q in zip(poly,poly[1:]+poly[:1]):
            cp,cq=cross(a,b,p),cross(a,b,q)
            if cp>=-1e-9: out.append(p)
            if (cp>0)!=(cq>0):
                t=cp/(cp-cq)
                out.append((p[0]+t*(q[0]-p[0]),p[1]+t*(q[1]-p[1])))
        poly=out
        if not poly: break
    return poly

def area(p): return abs(sum(a[0]*b[1]-a[1]*b[0] for a,b in zip(p,p[1:]+p[:1])))/2
def pseg(p,a,b):
    dx,dy=b[0]-a[0],b[1]-a[1]
    t=max(0,min(1,((p[0]-a[0])*dx+(p[1]-a[1])*dy)/(dx*dx+dy*dy)))
    return math.hypot(p[0]-a[0]-t*dx,p[1]-a[1]-t*dy)
def distance(p,q):
    if area(clip(p,q))>1e-8:return 0
    return min([pseg(v,a,b) for v in p for a,b in zip(q,q[1:]+q[:1])]+[pseg(v,a,b) for v in q for a,b in zip(p,p[1:]+p[:1])])

def nearest(poly,side=16.5):
    return sorted([dict(index=i,**k,distance=distance(poly,rect(k['x'],k['y'],side,side,k['rot'])),overlap=area(clip(poly,rect(k['x'],k['y'],side,side,k['rot'])))) for i,k in enumerate(KEYS)],key=lambda q:q['distance'])[:6]

if __name__=='__main__':
    targets={'spine_front':rect(130.881,42,18,8),'spine_rear':rect(130.881,83,30,8),'bracket_roof':rect(130.881,22.064485,21,21.6)}
    for name,p in targets.items(): print(name,json.dumps(nearest(p,18.5)))
    for x,y in [(125,17),(125,25),(126.381,42),(135.381,42),(121.881,83),(142.881,83)]:
        print('bolt',x,y,json.dumps(nearest(rect(x,y,4.4,4.4))[:2]))
