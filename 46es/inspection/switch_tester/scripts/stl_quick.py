import sys,struct,numpy as np
p=sys.argv[1]; b=open(p,'rb').read()
if b[:5]==b'solid' and b'facet' in b[:300]:
    import re
    v=np.array(re.findall(rb'vertex\s+([-\d.eE+]+)\s+([-\d.eE+]+)\s+([-\d.eE+]+)',b),dtype=float)
    tri=v.reshape(-1,3,3); kind='ascii'
else:
    n=struct.unpack('<I',b[80:84])[0]
    a=np.frombuffer(b[84:84+n*50],dtype=np.dtype([('n','<3f4'),('v','<9f4'),('a','<u2')]))
    tri=a['v'].reshape(-1,3,3).astype(float); kind='binary'
print(kind,'tris',len(tri))
v=tri.reshape(-1,3); print('bbox min',v.min(0).round(3),'max',v.max(0).round(3),'size',(v.max(0)-v.min(0)).round(3))
# z histogram of horizontal faces
nrm=np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0]); area=np.linalg.norm(nrm,axis=1)/2; nz=nrm[:,2]/np.maximum(np.linalg.norm(nrm,axis=1),1e-12)
hz=np.abs(nz)>0.999; zs=tri[hz][:,0,2]
import collections
c=collections.defaultdict(float)
for z,a,s in zip(zs.round(3),area[hz],np.sign(nz[hz])): c[(z,s)]+=a
for (z,s),a in sorted(c.items()):
    if a>5: print('horiz z=%.3f %s area=%.1f'%(z,'+' if s>0 else '-',a))
# vertical faces: planes with normal ±x or ±y, grouped by coordinate
for ax,name in ((0,'x'),(1,'y')):
    m=(np.abs(nrm[:,ax]/np.maximum(np.linalg.norm(nrm,axis=1),1e-12))>0.999)
    d=collections.defaultdict(float)
    for t,a in zip(tri[m],area[m]): d[round(t[0,ax],3)]+=a
    print('vertical',name,'planes:',' '.join('%.3f(%.0f)'%(k,v) for k,v in sorted(d.items()) if v>8))
