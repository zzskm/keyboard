"""Read-only SolidCraft SCBREP04 cache inspection; no export or CAD mutation."""
import json, struct, zipfile, math
from pathlib import Path

class Reader:
    def __init__(self, data): self.data, self.i = data, 8
    def take(self, n):
        b=self.data[self.i:self.i+n]; self.i+=n; return b
    def num(self, f): return struct.unpack('<'+f,self.take(struct.calcsize(f)))[0]
    def string(self): return self.take(self.num('I')).decode('utf8')
    def value(self):
        tag=self.num('B')
        if tag==0: return None
        if tag==1: return True
        if tag==2: return False
        if tag==3: return self.num('q')
        if tag==4: return self.num('Q')
        if tag==5: return self.num('d')
        if tag==6: return self.string()
        if tag==7: return [self.value() for _ in range(self.num('I'))]
        if tag==8: return {self.string():self.value() for _ in range(self.num('I'))}
        raise ValueError((tag,self.i))

def read(path):
    with zipfile.ZipFile(path) as z:
        cache=json.loads(z.read('cache/model.json'))
        data=z.read('cache/bodies.bin')
    def body(i):
        start,length=cache['slices'][i]
        raw=data[start:start+length]
        assert raw[:8]==b'SCBREP04'
        r=Reader(raw); v=r.value(); assert r.i==len(raw),(r.i,len(raw))
        return v
    return cache,body

def curve_points(curve, samples=1024):
    if curve['kind']=='line': return [curve['start'],curve['end']]
    if curve['kind']=='rational_spline':
        pts=curve['homogeneous']; knots=curve['knots']; degree=len(knots)-len(pts)-1
        out=[]
        for j in range(samples+1):
            t=knots[degree]+(knots[len(pts)]-knots[degree])*j/samples
            k=next((i for i in range(degree,len(pts)) if knots[i]<=t<knots[i+1]),len(pts)-1)
            d=[list(pts[i]) for i in range(k-degree,k+1)]
            for r in range(1,degree+1):
                for i in range(degree,r-1,-1):
                    a=(t-knots[k-degree+i])/(knots[k+1+i-r]-knots[k-degree+i])
                    d[i]=[(1-a)*x+a*y for x,y in zip(d[i-1],d[i])]
            out.append([x/d[degree][3] for x in d[degree][:3]])
        return out
    raise ValueError(curve['kind'])

def shell_summary(shell):
    """Vertical prismatic shells: integrate z*n_z dA on horizontal faces.
    Rational edges are sampled; convergence and SolidCraft totals are checked.
    """
    volume=0
    for face in shell['faces']:
        sf=face['surface']
        if sf['kind']!='plane_through': continue
        a,u,v=[sf[k] for k in ['origin','u_point','v_point']]
        if abs(u[2]-a[2])+abs(v[2]-a[2])>1e-7: continue
        # loops are already oriented in the shell's boundary orientation
        area=0
        for loop in face['loops']:
            for edge in loop:
                pts=curve_points(shell['edges'][edge['edge']]['curve'])
                if not edge['forward']: pts.reverse()
                area+=sum(p[0]*q[1]-q[0]*p[1] for p,q in zip(pts,pts[1:]))/2
        volume+=a[2]*area
    return dict(signed_volume_mm3=volume,volume_mm3=abs(volume),
        bbox=dict(min=[min(p[j] for p in shell['vertices']) for j in range(3)],
                  max=[max(p[j] for p in shell['vertices']) for j in range(3)]),
        faces=len(shell['faces']),vertices=len(shell['vertices']))

if __name__=='__main__':
    import sys
    cache,body=read(sys.argv[1])
    print('names',str(cache['model']['names'])[:500])
    print('model_bodies sample',str(cache['model']['model_bodies'])[:1800])
    b=body(int(sys.argv[2]) if len(sys.argv)>2 else 0)
    print('root', {k:type(v).__name__ for k,v in b.items()})
    print('summary',str(b)[:3000])
