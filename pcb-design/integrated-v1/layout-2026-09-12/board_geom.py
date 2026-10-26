from pathlib import Path
import sys,json,math,heapq
P=Path(__file__).resolve().parent
sys.path.insert(0,str(P.parents[1]/'native-rev-a/router/_deps'))
import numpy as np
from shapely import union_all,contains_xy
from shapely.geometry import Point,LineString,Polygon,box
from shapely.affinity import rotate,translate,scale
M=.0254
raw=json.loads((P/'after-ses.json').read_text())
components=json.loads((P/'placed-geometry.json').read_text())
lib=json.loads((P/'library-docs.json').read_text())
def pad_shape(p):
 t,w,h,*_=p['pad'];w*=M;h*=M;x=p['x']*M;y=-p['y']*M
 if t=='RECT': g=box(-w/2,-h/2,w/2,h/2)
 elif t=='ELLIPSE':g=scale(Point(0,0).buffer(1,quad_segs=32),w/2,h/2)
 elif t=='OVAL':
  if w>=h:g=LineString([(-w/2+h/2,0),(w/2-h/2,0)]).buffer(h/2)
  else:g=LineString([(0,-h/2+w/2),(0,h/2-w/2)]).buffer(w/2)
 else:raise ValueError(t)
 return translate(rotate(g,-p['rotation'],origin=(0,0)),x,y)
def line_shape(l):return LineString([(l['startX']*M,-l['startY']*M),(l['endX']*M,-l['endY']*M)]).buffer(l['lineWidth']*M/2,quad_segs=24)
def path_shape(path):
 if isinstance(path[0],list):return union_all([path_shape(p) for p in path])
 if path[0]=='CIRCLE':return Point(path[1]*M,-path[2]*M).buffer(path[3]*M,quad_segs=48)
 if len(path)>2 and path[2]=='L':
  nums=[n for n in path if isinstance(n,(int,float))];return Polygon([(nums[i]*M,-nums[i+1]*M) for i in range(0,len(nums),2)])
 
 if len(path)>2 and path[2]=='ARC' and abs(path[3])>350:
  return Point(0,0).buffer(math.hypot(path[0],path[1])*M,quad_segs=64)
 raise ValueError(path)
pads=[];slots=[];bodies=[]
for c in components:
 ref=c['component']['designator'];co=c['component']
 for p in c['pads']:pads.append(dict(p,ref=ref,geom=pad_shape(p)))
 for h,v in lib.get(co['footprint']['uuid'],{}).get('records',[]):
  if (h['type']=='FILL' and v['layerId']==12) or (h['type']=='POLY' and v['layerId']==48):
   g=path_shape(v['path']);g=translate(rotate(g,-co['rotation'],origin=(0,0)),co['x']*M,-co['y']*M)
   (slots if v['layerId']==12 else bodies).append(dict(ref=ref,id=co['primitiveId']+h['id'],geom=g))
keep=union_all([Point(x,y).buffer(2.8) for x,y in [(4,4),(106,4),(4,71),(106,71)]]+[box(56.5,0,71.3,10)])

def copper(net,layer,lines=None):
 ls=raw['lines'] if lines is None else lines
 return union_all([line_shape(l) for l in ls if l['net']==net and l['layer']==layer])
def draw(bounds,name,highlight=()):
 from PIL import Image,ImageDraw,ImageFont
 x0,y0,x1,y1=bounds;sc=min(90,1400/(x1-x0));W=int((x1-x0)*sc);H=int((y1-y0)*sc)
 im=Image.new('RGB',(2*W,H+30),'#151920');d=ImageDraw.Draw(im);font=ImageFont.truetype('/System/Library/Fonts/Monaco.ttf',11)
 def poly(g,fill,ofs):
  if g.is_empty:return
  if g.geom_type!='Polygon':
   for t in g.geoms:poly(t,fill,ofs)
   return
  pts=[((x-x0)*sc+ofs,(y-y0)*sc+30) for x,y in g.exterior.coords];d.polygon(pts,fill=fill)
 for li,layer in enumerate([1,2]):
  ofs=li*W;d.text((ofs+5,3),'TOP' if li==0 else 'BOTTOM',font=font,fill='white')
  for l in raw['lines']:
   if l['layer']==layer:poly(line_shape(l),'#d77952' if l['net'] in highlight else ('#722c36' if li==0 else '#324481'),ofs)
  for v in raw['vias']:poly(Point(v['x']*M,-v['y']*M).buffer(v['diameter']*M/2),'#db8748',ofs)
  for p in pads:
   if p['layer'] not in [layer,12]:continue
   poly(p['geom'],'#fff264' if p['net'] in highlight else '#959583',ofs)
   x,y=p['x']*M,-p['y']*M
   if x0<=x<=x1 and y0<=y<=y1:d.text(((x-x0)*sc+ofs,(y-y0)*sc+30),p['ref']+'.'+p['padNumber'],font=font,fill='#8fffee')
  for g in slots:poly(g['geom'],'#dddddd',ofs)
 im.save(P/name)
if __name__=='__main__':
 before=json.loads((P/'before-ses.json').read_text())
 lost=[]
 for key in {(l['net'],l['layer']) for l in before['lines']}:
  old=copper(*key,lines=before['lines']);new=copper(*key)
  delta=old.difference(new.buffer(.003))
  if delta.area>.001:lost.append((key,delta.area))
 print('Critical copper area lost mm2',lost)
 draw((10,26,30,39),'bm-routing.png',['BM'])
 draw((18,54,32,65),'chg-routing.png',['CHG_EN'])
 print('slots',[(s['ref'],s['id'],s['geom'].bounds) for s in slots])
 print('body overlaps',[(a['ref'],b['ref'],round(a['geom'].intersection(b['geom']).area,3)) for i,a in enumerate(bodies) for b in bodies[i+1:] if a['ref']!=b['ref'] and a['geom'].intersection(b['geom']).area>.1])
