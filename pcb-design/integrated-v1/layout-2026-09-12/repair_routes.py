from board_geom import *
import time
changes={'delete':[],'traces':[],'vias':[]}

def route(net,start,end,layers=(1,1),width=.254,margin=6):
 x0=max(.6,min(start[0],end[0])-margin);x1=min(109.4,max(start[0],end[0])+margin)
 y0=max(.6,min(start[1],end[1])-margin);y1=min(74.4,max(start[1],end[1])+margin)
 step=.05
 xs=np.array(sorted(set(round(float(x),5) for x in np.arange(x0,x1,step))|{start[0],end[0]}));ys=np.array(sorted(set(round(float(y),5) for y in np.arange(y0,y1,step))|{start[1],end[1]}));xx,yy=np.meshgrid(xs,ys);nx=len(xs);ny=len(ys);area=nx*ny
 base=box(.5,.5,109.5,74.5).difference(keep.buffer(.03))
 slot=union_all([s['geom'] for s in slots])
 obs=[];vobs=[]
 for layer in [1,2]:
  ps=union_all([p['geom'] for p in pads if p['net']!=net and p['layer'] in [layer,12]])
  ts=union_all([line_shape(l) for l in raw['lines'] if l['primitiveId'] not in changes['delete'] and l['net']!=net and l['layer']==layer])
  vs=union_all([Point(v['x']*M,-v['y']*M).buffer(v['diameter']*M/2) for v in raw['vias'] if v['net']!=net])
  obs.append(union_all([ps.buffer(.16+width/2+.004),ts.buffer(.205+width/2+.004),vs.buffer(.205+width/2+.004),slot.buffer(.305+width/2+.004)]))
  vobs.append(union_all([ps.buffer(.21+.3),ts.buffer(.21+.3),vs.buffer(.21+.3),slot.buffer(.31+.3)]))
 allowed=[base.buffer(-width/2).difference(o) for o in obs];walk=np.stack([contains_xy(g,xx,yy) for g in allowed]);vallowed=base.buffer(-.3).difference(union_all(vobs));via=contains_xy(vallowed,xx,yy)
 sx,sy=int(np.argmin(abs(xs-start[0]))),int(np.argmin(abs(ys-start[1])));ex,ey=int(np.argmin(abs(xs-end[0]))),int(np.argmin(abs(ys-end[1])))
 def key(l,x,y):return l*area+y*nx+x
 def heur(x,y):return math.hypot(xs[x]-xs[ex],ys[y]-ys[ey])
 dist={};prev={};heap=[]
 for l in range(2):
  if (layers[0]==12 or l==layers[0]-1) and walk[l,sy,sx]:k=key(l,sx,sy);dist[k]=0;heapq.heappush(heap,(heur(sx,sy),0,k))
 if not heap:raise ValueError(('start blocked',net,start))
 ct=0
 while heap:
  _,cost,k=heapq.heappop(heap)
  if cost>dist[k]+1e-8:continue
  ct+=1
  l,rem=divmod(k,area);y,x=divmod(rem,nx)
  if x==ex and y==ey and (layers[1]==12 or l==layers[1]-1):break
  for dx,dy in [(1,0),(-1,0),(0,1),(0,-1),(1,1),(1,-1),(-1,1),(-1,-1)]:
   X=x+dx;Y=y+dy
   if not(0<=X<nx and 0<=Y<ny) or not walk[l,Y,X]:continue
   if dx and dy and (not walk[l,y,X] or not walk[l,Y,x]):continue
   kk=key(l,X,Y);g=cost+math.hypot(xs[X]-xs[x],ys[Y]-ys[y])
   if g<dist.get(kk,1e20):dist[kk]=g;prev[kk]=k;heapq.heappush(heap,(g+heur(X,Y),g,kk))
  if via[y,x] and walk[1-l,y,x]:
   kk=key(1-l,x,y);g=cost+4
   if g<dist.get(kk,1e20):dist[kk]=g;prev[kk]=k;heapq.heappush(heap,(g+heur(x,y),g,kk))
 else:raise ValueError(('no path',net,ct))
 path=[]
 while True:
  l,rem=divmod(k,area);y,x=divmod(rem,nx);path.append((l,float(xs[x]),float(ys[y])))
  if k not in prev:break
  k=prev[k]
 path.reverse();tr=[];vi=[];i=0
 while i<len(path):
  l=path[i][0];j=i
  while j+1<len(path) and path[j+1][0]==l:j+=1
  pts=[path[t][1:] for t in range(i,j+1)]
  # Simplify with exact centreline containment, favor orthogonal or 45-degree runs.
  result=[pts[0]];z=0
  while z<len(pts)-1:
   best=z+1
   for t in range(z+2,len(pts)):
    a=pts[z];b=pts[t];dx=abs(b[0]-a[0]);dy=abs(b[1]-a[1])
    if min(dx,dy)>.001 and abs(dx-dy)>.003:continue
    if allowed[l].covers(LineString([a,b])):best=t
   result.append(pts[best]);z=best
  if len(result)>1:tr.append(dict(net=net,layer=l+1,width=width,points=result))
  if j+1<len(path):vi.append(dict(net=net,x=path[j][1],y=path[j][2],diameter=.6,drill=.3))
  i=j+1
 changes['traces']+=tr;changes['vias']+=vi
 print('Route',net,'nodes',ct,'segments',sum(len(t['points'])-1 for t in tr),'vias',len(vi),flush=True)
 return tr,vi

def pad(ref,num):return next(p for p in pads if p['ref']==ref and p['padNumber']==str(num))
def pxy(p):return p['x']*M,-p['y']*M

if __name__=='__main__':
 errors=[e for g in raw['drc'] if g['name']=='Clearance Error' for sub in g['list'] for e in sub['list']]
 for err in errors:
  id=err['objs'][0];l=next(l for l in raw['lines'] if l['primitiveId']==id);changes['delete'].append(id)
  route(l['net'],(l['startX']*M,-l['startY']*M),(l['endX']*M,-l['endY']*M),(l['layer'],l['layer']),l['lineWidth']*M,3)
 (P/'routing-repairs.json').write_text(json.dumps(changes,indent=2))
 print('Saved routing-repairs.json')
