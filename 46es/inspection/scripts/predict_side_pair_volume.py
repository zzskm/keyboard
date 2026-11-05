"""Read-only bottom-face clipping predicts v3 link union volume from saved v2.

Connector starts beyond the original pockets, so overlap is full-height 3mm.
Curved edges are sampled; final native CAD and mesh validation is separate.
"""
import json, math
from pathlib import Path
from read_sc_cache import read, curve_points

ROOT=Path(__file__).resolve().parents[2]
LINKS=[dict(side='L',a=[3.70934,38.0988],b=[25.1993,66.6992],names=['MOUNT_H05_SO1_MIN_V2','MOUNT_H01_SO2_MIN_V2']),
       dict(side='R',a=[281.29076,38.0988],b=[260.0499,66.6992],names=['MOUNT_H06_SO5_MIN_V2','MOUNT_H04_SO4_MIN_V2'])]

def area(poly):return sum(p[0]*q[1]-p[1]*q[0] for p,q in zip(poly,poly[1:]+poly[:1]))/2 if len(poly)>2 else 0
def clip(poly,window):
    if area(window)<0:window=window[::-1]
    def cross(a,b,c):return (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])
    for a,b in zip(window,window[1:]+window[:1]):
        out=[]
        for p,q in zip(poly,poly[1:]+poly[:1]):
            cp,cq=cross(a,b,p),cross(a,b,q)
            if cp>=-1e-10:out.append(p)
            if (cp>0)!=(cq>0):
                t=cp/(cp-cq);out.append([p[0]+t*(q[0]-p[0]),p[1]+t*(q[1]-p[1])])
        poly=out
        if not poly:break
    return poly

def ordered_loop(shell,loop):
    # Serialized edge lists need not be in traversal order. Reconstruct by
    # endpoint matching; curve direction also need not match edge.forward.
    pieces=[[[p[0],p[1]] for p in curve_points(shell['edges'][e['edge']]['curve'],4096)] for e in loop]
    poly=pieces.pop(0)
    while pieces:
        dist,i,reverse=min((math.dist(poly[-1],p[-1] if reverse else p[0]),i,reverse) for i,p in enumerate(pieces) for reverse in [False,True])
        assert dist<1e-4,('unconnected wire',dist)
        pts=pieces.pop(i)
        if reverse:pts.reverse()
        poly.extend(pts[1:])
    assert math.dist(poly[0],poly[-1])<1e-4,'open loop'
    return poly[:-1]

def main():
    cache,read_body=read(ROOT/'model/46es_mount_minimal_v2.sc');records=cache['model']['model_bodies']
    live={records[i]['name']:records[i] for start,count in cache['model']['states'][-1]['bodies'] for i in range(start,start+count)}
    old={b['name']:b['volume_mm3'] for b in json.loads((ROOT/'inspection/data/minimal-v2-mounts.json').read_text())['bodies']}
    out=[]
    for link in LINKS:
        a,b=link['a'],link['b'];length=math.dist(a,b);u=[(b[j]-a[j])/length for j in range(2)];n=[-u[1],u[0]]
        start=[a[j]+u[j]*3.7 for j in range(2)];end=[b[j]-u[j]*3.7 for j in range(2)]
        rect=[[p[j]+sign*n[j]*4 for j in range(2)] for p,sign in [(start,1),(end,1),(end,-1),(start,-1)]]
        overlaps=[]
        for name in link['names']:
            total=0
            for idx in cache['bodies'][live[name]['body']]:
                for shell in read_body(idx)['solid']['shells']:
                    for face in shell['faces']:
                        sf=face['surface']
                        if sf['kind']!='plane_through' or max(abs(sf[k][2]) for k in ['origin','u_point','v_point'])>1e-7:continue
                        loops=[]
                        for loop in face['loops']:
                            poly=ordered_loop(shell,loop)
                            loops.append((abs(area(poly)),abs(area(clip(poly,rect)))))
                        loops.sort(reverse=True)
                        total+=loops[0][1]-sum(x[1] for x in loops[1:])
            overlaps.append(dict(body=name,area_mm2=total,volume_mm3=total*3))
        prism=(length-7.4)*8*3
        out.append(dict(**link,length_mm=length,connector_polygon=rect,connector_volume_mm3=prism,overlaps=overlaps,
            before_volume_mm3=sum(old[n] for n in link['names']),expected_volume_mm3=sum(old[n] for n in link['names'])+prism-sum(x['volume_mm3'] for x in overlaps)))
    print(json.dumps(out,indent=2))

if __name__=='__main__':main()
