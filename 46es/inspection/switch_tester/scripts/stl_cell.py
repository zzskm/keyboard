import sys,struct,numpy as np,collections
p=sys.argv[1]; b=open(p,'rb').read()
n=struct.unpack('<I',b[80:84])[0]
a=np.frombuffer(b[84:84+n*50],dtype=np.dtype([('n','<3f4'),('v','<9f4'),('a','<u2')]))
tri=a['v'].reshape(-1,3,3).astype(float)
def crossings(z, axis, other_val=0.0, lim=9.6):
    # intersect with plane z, keep segments, then crossings of line (other axis = other_val)
    xs=[]
    for t in tri:
        zz=t[:,2]; 
        if zz.min()>z or zz.max()<z or zz.min()==zz.max(): continue
        pts=[]
        for i in range(3):
            p0,p1=t[i],t[(i+1)%3]
            if (p0[2]-z)*(p1[2]-z)<0:
                f=(z-p0[2])/(p1[2]-p0[2]); pts.append(p0+f*(p1-p0))
        if len(pts)!=2: continue
        q0,q1=pts; o=1-axis
        if (q0[o]-other_val)*(q1[o]-other_val)<0:
            f=(other_val-q0[o])/(q1[o]-q0[o]); x=q0[axis]+f*(q1[axis]-q0[axis])
            if abs(x)<lim: xs.append(round(float(x),3))
    return sorted(set(xs))
for z in [0.6,1.3,3.0,5.0,6.5,7.0,7.5,8.0,8.5,9.0,9.5,9.9,11,13,15,16.1]:
    print('z=%5.1f  x@y0: %-40s y@x0: %s'%(z,crossings(z,0,0.0),crossings(z,1,0.0)))
print('--- off-centre line y=5 (to see relief extent) ---')
for z in [7.5,9.0]:
    print('z=%5.1f  x@y5: %-40s y@x5: %s'%(z,crossings(z,0,5.0),crossings(z,1,5.0)))
# planes within centre cell
nrm=np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0]); area=np.linalg.norm(nrm,axis=1)/2
c=tri.mean(1); inc=(np.abs(c[:,0])<9.5)&(np.abs(c[:,1])<9.5)
d=collections.defaultdict(lambda:[0,99,-99])
for t,nn,ar in zip(tri[inc],nrm[inc],area[inc]):
    u=nn/max(np.linalg.norm(nn),1e-12)
    for ax,nm in ((0,'x'),(1,'y'),(2,'z')):
        if abs(u[ax])>0.999:
            k=(nm,'+' if u[ax]>0 else '-',round(float(t[0,ax]),3)); d[k][0]+=ar; d[k][1]=min(d[k][1],t[:,2].min()); d[k][2]=max(d[k][2],t[:,2].max())
print('--- centre-cell planes: axis sign coord area zmin zmax')
for k,v in sorted(d.items()): print(k, round(v[0],1), round(v[1],2), round(v[2],2))
