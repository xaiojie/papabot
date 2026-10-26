"""Heal only the vacated encoder area, with live geometry and retained-plane anchors."""
import sys,json
from pathlib import Path
P=Path(__file__).resolve().parent;F=P.parent/'final-no-encoder-2026-09-12'
sys.path.insert(0,str(P.parent/'layout-2026-09-12'));from board_geom import pad_shape,line_shape,M
from gerber_review import native_region
from shapely import union_all
from shapely.geometry import Point,box
from shapely.affinity import scale
from shapely.geometry.polygon import orient
sys.path.insert(0,str(P.parents[1]/'native-rev-b'));from verify_exports import parse
geo=json.loads((F/'PCB1_geometry.json').read_text());src=parse((F/'PCB1.source').read_text())['bc31667e02a33e5b']
pads=[dict(p,ref=c['component']['designator'])for c in geo['geometry']for p in c['pads']]
old={layer:union_all([native_region(v['path'])for(t,_),v in src.items()if t=='FILL'and v['layerId']==layer])for layer in [1,2]}
regions=[];report=[]
# Retain all existing copper; additions are restricted to the former EC11/pullup region.
domain=box(73,-74.35,98,-55.5)
def arr(coords):
 a=[[round(x/M,4),round(y/M,4)]for x,y in coords];return a[0]+['L']+[v for p in a[1:]for v in p]
for layer in [1,2]:
 obs=union_all([scale(pad_shape(p),xfact=1,yfact=-1,origin=(0,0))for p in pads if p['layer']in[layer,12]and p['net']!='GND']+[scale(line_shape(l),xfact=1,yfact=-1,origin=(0,0))for l in geo['lines']if l['layer']==layer and l['net']!='GND']+[Point(v['x']*M,v['y']*M).buffer(v['diameter']*M/2)for v in geo['vias']if v['net']!='GND'])
 allowed=domain.difference(obs.buffer(.34,quad_segs=24))
 # No remaining GND component pad should receive altered thermal relief in this area.
 assert not any(domain.intersects(scale(pad_shape(p),xfact=1,yfact=-1,origin=(0,0)))for p in pads if p['net']=='GND')
 patch=allowed.buffer(-.18,quad_segs=16).buffer(.18,quad_segs=16).intersection(allowed)
 polys=list(patch.geoms)if patch.geom_type=='MultiPolygon'else[patch]
 patch=union_all([p for p in polys if p.intersection(old[layer]).area>.05])
 final=old[layer].union(patch)
 assert final.difference(old[layer]).intersection(obs.buffer(.335)).area<1e-6
 for poly in (list(final.geoms)if final.geom_type=='MultiPolygon'else[final]):
  q=orient(poly.simplify(.0005,preserve_topology=True),sign=1)
  regions.append({'layer':layer,'paths':[arr(q.exterior.coords)]+[arr(h.coords)for h in q.interiors]})
 report.append({'layer':layer,'added_copper_mm2':final.difference(old[layer]).area,'removed_copper_mm2':old[layer].difference(final).area,'clearance_mm':.34,'domain_mm':[73,-74.35,98,-55.5]})
(P/'ground-heal-plan.json').write_text(json.dumps({'regions':regions,'report':report},indent=2));print(report,'regions',len(regions))
