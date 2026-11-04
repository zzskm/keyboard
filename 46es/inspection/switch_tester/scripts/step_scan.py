import re,sys,collections
p=sys.argv[1]; t=open(p,encoding='utf-8',errors='replace').read()
ents=collections.Counter(re.findall(r'=\s*([A-Z_0-9]+)\(',t))
for k in ['MANIFOLD_SOLID_BREP','CLOSED_SHELL','ADVANCED_FACE','CYLINDRICAL_SURFACE','PLANE','NEXT_ASSEMBLY_USAGE_OCCURRENCE','PRODUCT_DEFINITION','SHAPE_REPRESENTATION','ADVANCED_BREP_SHAPE_REPRESENTATION','CARTESIAN_POINT']:
    print(k,ents.get(k,0))
pts=[tuple(map(float,m.split(','))) for m in re.findall(r"CARTESIAN_POINT\('[^']*',\(([^)]*)\)\)",t) if m.count(',')==2]
import numpy as np
a=np.array(pts); print('npts',len(a)); print('min',a.min(0).round(3)); print('max',a.max(0).round(3)); print('size',(a.max(0)-a.min(0)).round(3))
for m in re.findall(r"PRODUCT_DEFINITION\('([^']*)','([^']*)'",t): print('PD',m)
for m in re.findall(r"NEXT_ASSEMBLY_USAGE_OCCURRENCE\('([^']*)','([^']*)','([^']*)'",t): print('NAUO',m)
for m in re.findall(r"STYLED_ITEM|COLOUR_RGB\('[^']*',([^)]*)\)",t)[:10]: print('col',m)
for m in re.findall(r"CYLINDRICAL_SURFACE\('[^']*',#\d+,([0-9.]+)\)",t): pass
r=collections.Counter(re.findall(r"CYLINDRICAL_SURFACE\('[^']*',#\d+,([0-9.]+)\)",t)); print('cyl radii',r.most_common(15))
