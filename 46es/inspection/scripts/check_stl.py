"""Check exported binary STL components, watertight edges, volume and bounds."""
import struct, json, sys
from collections import defaultdict

def check(path):
    data=open(path,'rb').read()
    n=struct.unpack_from('<I',data,80)[0]
    if len(data)!=84+50*n: raise ValueError('Expected binary STL')
    parent=list(range(n)); points={}; edge_uses=defaultdict(list); tris=[]
    def root(i):
        while parent[i]!=i:
            parent[i]=parent[parent[i]];i=parent[i]
        return i
    def join(a,b):
        a,b=root(a),root(b)
        if a!=b:parent[b]=a
    for i in range(n):
        v=struct.unpack_from('<12fH',data,84+50*i)
        ps=[tuple(v[j:j+3]) for j in (3,6,9)];tris.append(ps)
        ids=[]
        for p in ps:
            k=tuple(round(c,4) for c in p)
            if k not in points:points[k]=len(points)
            ids.append(points[k])
        for a,b in zip(ids,ids[1:]+ids[:1]):edge_uses[tuple(sorted((a,b)))].append(i)
    for uses in edge_uses.values():
        for b in uses[1:]:join(uses[0],b)
    groups=defaultdict(list)
    for i in range(n):groups[root(i)].append(i)
    out=[]
    for ids in groups.values():
        vs=[p for i in ids for p in tris[i]]
        vol=0
        for i in ids:
            a,b,c=tris[i]
            vol+=sum(a[j]*(b[(j+1)%3]*c[(j+2)%3]-b[(j+2)%3]*c[(j+1)%3]) for j in range(3))/6
        out.append(dict(triangles=len(ids),signed_volume=vol,bbox=dict(min=[min(p[j] for p in vs) for j in range(3)],max=[max(p[j] for p in vs) for j in range(3)])))
    out.sort(key=lambda x:abs(x['signed_volume']),reverse=True)
    return dict(path=path,triangles=n,components=out,bad_edge_count=sum(len(uses)!=2 for uses in edge_uses.values()))

if __name__=='__main__':print(json.dumps([check(p) for p in sys.argv[1:]],indent=2))
