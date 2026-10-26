from board_geom import *
from shapely.geometry.polygon import orient
clear=.32
base=box(.65,.65,109.35,74.35).difference(keep.buffer(.15)).difference(union_all([s['geom'].buffer(.5) for s in slots]))
obs=[];own=[]
for layer in [1,2]:
 obs.append(union_all([p['geom'] for p in pads if p['layer'] in [layer,12] and p['net']!='GND']+[line_shape(l) for l in raw['lines'] if l['net']!='GND' and l['layer']==layer]+[Point(v['x']*M,-v['y']*M).buffer(v['diameter']*M/2) for v in raw['vias'] if v['net']!='GND']).buffer(clear,quad_segs=16))
 own.append(union_all([p['geom'] for p in pads if p['layer'] in [layer,12] and p['net']=='GND']+[line_shape(l) for l in raw['lines'] if l['net']=='GND' and l['layer']==layer]+[Point(v['x']*M,-v['y']*M).buffer(v['diameter']*M/2) for v in raw['vias'] if v['net']=='GND']))
# Stitch only where both layers admit a through via, clear of every existing drill/pad.
viazone=base.buffer(-.35).difference(union_all(obs).buffer(.35))
vias=[];padzone=union_all([p['geom'] for p in pads]).buffer(.7)
for x in np.arange(8,106,8):
 for y in np.arange(7,74,8):
  pt=Point(x,y)
  if not viazone.covers(pt) or padzone.covers(pt):continue
  if min([pt.distance(Point(v['x']*M,-v['y']*M)) for v in raw['vias']]+[100])<2.5:continue
  vias.append(dict(net='GND',x=float(x),y=float(y),diameter=.7,drill=.35))
regions=[]
def polyarray(coords):
 a=[[round(x/M,4),round(-y/M,4)] for x,y in coords];return a[0]+['L']+[v for p in a[1:] for v in p]
for idx,layer in enumerate([1,2]):
 allowed=base.difference(obs[idx]);thermal=[];spokes=[]
 for p in pads:
  if p['net']!='GND' or p['layer'] not in [layer,12] or p['ref'] in ['U4','Q1']:continue
  g=p['geom'];thermal.append(g.buffer(.35,quad_segs=16));x=p['x']*M;y=-p['y']*M;b=g.bounds;r=max(b[2]-b[0],b[3]-b[1])/2+.7
  spokes.extend([box(x-r,y-.225,x+r,y+.225),box(x-.225,y-r,x+.225,y+r)])
 fill=allowed.difference(union_all(thermal)).union(union_all(spokes).intersection(allowed).intersection(union_all(thermal)))
 fill=fill.buffer(-.16,quad_segs=12).buffer(.16,quad_segs=12).intersection(allowed)
 polys=list(fill.geoms) if fill.geom_type=='MultiPolygon' else [fill]
 # Retain only regions electrically anchored by existing GND copper or an anchored opposite-layer via.
 seed=own[idx].buffer(.01)
 otherSeed=own[1-idx]
 kept=[]
 for poly in polys:
  if poly.area<1.0:continue
  if poly.intersects(seed):kept.append(poly)
 # Additional portions must connect through stitching to the other side's main anchored plane.
 otherAllowed=base.difference(obs[1-idx]);otherPolys=list(otherAllowed.geoms) if otherAllowed.geom_type=='MultiPolygon' else [otherAllowed]
 otherAnchored=union_all([q for q in otherPolys if q.intersects(otherSeed)])
 for poly in polys:
  if poly.area<1.0 or poly in kept:continue
  if any(poly.covers(Point(v['x'],v['y'])) and otherAnchored.covers(Point(v['x'],v['y'])) for v in vias):kept.append(poly)
 for poly in kept:
  q=orient(poly.simplify(.002,preserve_topology=True),sign=1.0)
  regions.append(dict(layer=layer,net='GND',area_mm2=q.area,paths=[polyarray(q.exterior.coords)]+[polyarray(h.coords) for h in q.interiors]))
# Only place stitching vias that actually land on retained fills on both sides.
from shapely.geometry import shape
# paths encoded in native units; reconstruct for coverage.
def reconstruct(r):
 def ring(p):
  ns=[n for n in p if isinstance(n,(float,int))];return [(ns[i]*M,-ns[i+1]*M) for i in range(0,len(ns),2)]
 return Polygon(ring(r['paths'][0]),[ring(h) for h in r['paths'][1:]])
cu=[union_all([reconstruct(r) for r in regions if r['layer']==l]) for l in [1,2]]
vias=[v for v in vias if all(g.buffer(-.25).covers(Point(v['x'],v['y'])) for g in cu)]
res=dict(method='Static editable GND fill polygons with explicit clearance and thermal relief; rebuild this script after any routing change',regions=regions,vias=vias)
(P/'ground-fill-plan.json').write_text(json.dumps(res,indent=2))
print('Ground regions',len(regions),'areas',[round(g.area,1) for g in cu],'stitch vias',len(vias),'vertices',sum(sum(len(p) for p in r['paths']) for r in regions))
