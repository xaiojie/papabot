"""Offline two-layer routing candidate. Never connects to or changes EDA."""
from pathlib import Path
import sys, json, math, heapq, hashlib, time, argparse, html
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / '_deps'))
import numpy as np
from shapely import contains_xy, union_all
from shapely.geometry import Point, LineString, Polygon, box
from shapely.affinity import rotate

MM = 1000 / 25.4
W, H = 80 * MM, 32 * MM
CUT_X, CUT_Y0, CUT_Y1 = 24.17 * MM, 9.5 * MM, 22.5 * MM
CLEAR, EDGE, HOLE_CLEAR = 8.0, 12.0, .9 * MM
VIA_DIAM, VIA_DRILL = .6 * MM, .3 * MM
EPS = .04
LAYERS = ['TOP', 'BOTTOM']
BOARD = Polygon([(0,0),(W,0),(W,H),(0,H),(0,CUT_Y1),
                 (CUT_X,CUT_Y1),(CUT_X,CUT_Y0),(0,CUT_Y0)])
HOLES = [Point(x*MM,y*MM).buffer(1.6*MM, quad_segs=64)
         for x,y in [(5,5),(75,5),(75,27),(5,27)]]
HOLE_FORBIDDEN = union_all([g.buffer(HOLE_CLEAR + EPS, quad_segs=32) for g in HOLES])
COPPER_AREA = BOARD.buffer(-EDGE-EPS).difference(HOLE_FORBIDDEN)
POWER_WIDTHS = {'GND':40, 'LCD_3V3':24, '+3V3':24, '+5V_LOGIC':40, '+5V_MCU':40, 'VBAT_SW':32}
POWER = set(POWER_WIDTHS)

def pad_geom(p):
    typ, w, h, *_ = p['pad']
    if typ == 'ELLIPSE':
        if abs(w-h)>1e-6: raise ValueError('Noncircular pad needs ellipse support')
        return Point(p['x'],p['y']).buffer(w/2, quad_segs=64)
    if typ == 'RECT':
        g=box(p['x']-w/2,p['y']-h/2,p['x']+w/2,p['y']+h/2)
        return rotate(g,p.get('rotation',0),origin=(p['x'],p['y']))
    raise ValueError('Unsupported pad shape '+typ)

def read_input():
    src=ROOT.parent/'pcb-placed-pads.json'
    data=src.read_bytes(); raw=json.loads(data); pads=[]
    for c in raw:
        ref=c['component']['designator']
        for p in c['pads']:
            if p['layer'] != 12 or not p.get('metallization'):
                raise ValueError('Input assumption changed: all pads must be plated through holes')
            q={k:p[k] for k in ['x','y','rotation','pad','net','padNumber']}
            q.update(ref=ref,id=ref+'.'+str(p['padNumber']),primitiveId=p['primitiveId'])
            q['geom']=pad_geom(q); pads.append(q)
    return src,hashlib.sha256(data).hexdigest(),raw,pads

def precise_pads(pads):
    src=ROOT.parent/'pcb-free-pads.json'
    data=src.read_bytes();native=json.loads(data)
    lookup={p['primitiveId']:p for p in native}
    result=[];maximum_shift=0
    for p in pads:
        npad=lookup[p['primitiveId']]
        if npad['net']!=p['net'] or npad['pad']!=p['pad'] or str(npad['padNumber'])!=str(p['padNumber']):raise ValueError('Precise pad identities/geometry differ from frozen placement')
        shift=math.hypot(p['x']-npad['x'],p['y']-npad['y']);maximum_shift=max(maximum_shift,shift)
        if shift>.15:raise ValueError('Precise pad position exceeds rounding-only difference')
        q=dict(p,x=npad['x'],y=npad['y'],rotation=npad['rotation'],hole=npad['hole'],holeOffsetX=npad.get('holeOffsetX',0),holeOffsetY=npad.get('holeOffsetY',0))
        q['geom']=pad_geom(q);result.append(q)
    return result,{'source':'../pcb-free-pads.json','sha256':hashlib.sha256(data).hexdigest(),'native_pad_count':len(native),'matched_copper_pads':len(result),'maximum_center_shift_mil':maximum_shift,'plated_drill_sizes_mil':sorted({p['hole'][1] for p in result})}

def trace_geom(t, extra=0):
    return LineString(t['points']).buffer(t['width']/2+extra,quad_segs=32)

class DSU:
    def __init__(self,n): self.p=list(range(n))
    def root(self,i):
        while self.p[i]!=i:
            self.p[i]=self.p[self.p[i]];i=self.p[i]
        return i
    def join(self,i,j):self.p[self.root(i)]=self.root(j)

def simplify(points):
    out=[]
    for p in points:
        p=[round(float(p[0]),4),round(float(p[1]),4)]
        if out and out[-1]==p:continue
        while len(out)>1:
            a,b=out[-2],out[-1]
            cross=(b[0]-a[0])*(p[1]-b[1])-(b[1]-a[1])*(p[0]-b[0])
            dot=(b[0]-a[0])*(p[0]-b[0])+(b[1]-a[1])*(p[1]-b[1])
            if abs(cross)<1e-7 and dot>=0:out.pop()
            else:break
        out.append(p)
    return out

class Router:
    def __init__(self,pads,step=5,order='signals-first',priority=(),preconnect=(),ground_layer=None):
        self.pads=pads;self.step=step;self.order=order;self.priority=list(priority)
        # A 70.9 mil pad on 100 mil pitch leaves a 1.1 mil centre corridor
        # for a 12 mil trace with 8 mil clearance. A plain 5 mil raster can
        # miss it entirely. Add actual pad centres and connector midlines.
        self.xs=np.array(sorted({round(float(x),4) for x in np.arange(0,W,step)} | {round(p['x']+d,4) for p in pads for d in [-50,0,50] if 0<=p['x']+d<=W}))
        self.ys=np.array(sorted({round(float(y),4) for y in np.arange(0,H,step)} | {round(p['y']+d,4) for p in pads for d in [-50,0,50] if 0<=p['y']+d<=H}))
        self.nx=len(self.xs);self.ny=len(self.ys)
        self.xx,self.yy=np.meshgrid(self.xs,self.ys)
        self.traces=[];self.vias=[];self.attempts=[]
        self.preconnect=list(preconnect);self.seed_edges=[]
        self.ground_layer=ground_layer
        self.by_net={n:[p for p in pads if p['net']==n] for n in sorted({p['net'] for p in pads if p['net']})}

    def obstacles(self,net):
        fixed=[p['geom'] for p in self.pads if p['net']!=net]
        for v in self.vias:
            if v['net']!=net:fixed.append(Point(v['x'],v['y']).buffer(v['diameter']/2,quad_segs=32))
        return [union_all(fixed+[trace_geom(t) for t in self.traces if t['net']!=net and t['layer']==l]) for l in LAYERS]

    def masks(self,net,width):
        obs=self.obstacles(net)
        allowed=[COPPER_AREA.buffer(-width/2-EPS).difference(g.buffer(CLEAR+width/2+EPS,quad_segs=32)) for g in obs]
        walk=np.stack([contains_xy(g,self.xx,self.yy) for g in allowed])
        if net=='GND' and self.ground_layer:walk[LAYERS.index('TOP' if self.ground_layer=='BOTTOM' else 'BOTTOM')]=False
        vr=max(width/2,VIA_DIAM/2)
        va=COPPER_AREA.buffer(-vr-EPS).difference(union_all(obs).buffer(CLEAR+vr+EPS,quad_segs=32))
        via=contains_xy(va,self.xx,self.yy)
        through=contains_xy(union_all([p['geom'] for p in self.by_net[net]]),self.xx,self.yy)
        return walk,via,through,obs

    def astar(self,a,b,walk,via,through,max_nodes=450000):
        nx,ny=self.nx,self.ny;s=self.step;area=nx*ny
        ax,ay=int(np.argmin(abs(self.xs-a['x']))),int(np.argmin(abs(self.ys-a['y'])))
        bx,by=int(np.argmin(abs(self.xs-b['x']))),int(np.argmin(abs(self.ys-b['y'])))
        goals=None;bounds=None
        if b.get('targets'):
            goals={(l,int(np.argmin(abs(self.xs-x))),int(np.argmin(abs(self.ys-y)))) for l,x,y in b['targets']}
            bounds=(min(self.xs[x] for l,x,y in goals),min(self.ys[y] for l,x,y in goals),max(self.xs[x] for l,x,y in goals),max(self.ys[y] for l,x,y in goals))
        def key(l,x,y):return l*area+y*nx+x
        def heuristic(x,y):
            if bounds:
                x0,y0,x1,y1=bounds
                return math.hypot(max(x0-self.xs[x],self.xs[x]-x1,0),max(y0-self.ys[y],self.ys[y]-y1,0))/s
            return math.hypot(self.xs[x]-self.xs[bx],self.ys[y]-self.ys[by])/s
        dist=np.full(2*area,np.inf);prev=np.full(2*area,-1,dtype=np.int32)
        heap=[]
        for l in range(2):
            if walk[l,ay,ax]:
                k=key(l,ax,ay);dist[k]=0;heapq.heappush(heap,(heuristic(ax,ay),0,k))
        if not heap:return None,0,'start pad inaccessible at selected width/grid'
        moves=[(1,0,1),(-1,0,1),(0,1,1),(0,-1,1),(1,1,math.sqrt(2)),(1,-1,math.sqrt(2)),(-1,1,math.sqrt(2)),(-1,-1,math.sqrt(2))]
        seen=0
        while heap:
            _,cost,k=heapq.heappop(heap)
            if cost>dist[k]+1e-8:continue
            seen+=1
            if seen>max_nodes:return None,seen,'search expansion limit'
            l,rem=divmod(k,area);y,x=divmod(rem,nx)
            if (l,x,y) in goals if goals is not None else x==bx and y==by:
                path=[]
                while k!=-1:
                    ll,rr=divmod(k,area);yy,xx=divmod(rr,nx);path.append((ll,float(self.xs[xx]),float(self.ys[yy])));k=int(prev[k])
                path.reverse();return path,seen,'found'
            for dx,dy,base in moves:
                xx,yy=x+dx,y+dy
                if xx<0 or yy<0 or xx>=nx or yy>=ny or not walk[l,yy,xx]:continue
                if dx and dy and (not walk[l,y,xx] or not walk[l,yy,x]):continue
                base=math.hypot(self.xs[xx]-self.xs[x],self.ys[yy]-self.ys[y])/s
                penalty=.04*base if (l==0 and dy and not dx) or (l==1 and dx and not dy) else 0
                kk=key(l,xx,yy);g=cost+base+penalty
                if g<dist[kk]-1e-8:
                    dist[kk]=g;prev[kk]=k;heapq.heappush(heap,(g+heuristic(xx,yy),g,kk))
            if through[y,x] or via[y,x]:
                ll=1-l
                if walk[ll,y,x]:
                    kk=key(ll,x,y);g=cost+(.1 if through[y,x] else 22)
                    if g<dist[kk]-1e-8:
                        dist[kk]=g;prev[kk]=k;heapq.heappush(heap,(g+heuristic(x,y),g,kk))
        return None,seen,'no path at required width/clearance'

    def geometry_from_path(self,net,width,a,b,path):
        traces=[];vias=[];layer=path[0][0];points=[[a['x'],a['y']],[path[0][1],path[0][2]]]
        own=[p['geom'] for p in self.by_net[net]]
        for l,x,y in path[1:]:
            if l!=layer:
                pts=simplify(points)
                if len(pts)>1:traces.append({'net':net,'layer':LAYERS[layer],'points':pts,'width':width})
                if not any(g.covers(Point(x,y)) for g in own):
                    vias.append({'net':net,'x':x,'y':y,'diameter':VIA_DIAM,'drill':VIA_DRILL})
                layer=l;points=[[x,y]]
            else:points.append([x,y])
        points.append([b['x'],b['y']]);pts=simplify(points)
        if len(pts)>1:traces.append({'net':net,'layer':LAYERS[layer],'points':pts,'width':width})
        return traces,vias

    def accept_geometry(self,traces,vias,obs):
        for l,layer in enumerate(LAYERS):
            shapes=[trace_geom(t,EPS) for t in traces if t['layer']==layer]
            shapes += [Point(v['x'],v['y']).buffer(v['diameter']/2+EPS,quad_segs=32) for v in vias]
            if not shapes:continue
            copper=union_all(shapes)
            if not COPPER_AREA.covers(copper):return False,'exact board edge / mounting hole check rejected candidate'
            if copper.distance(obs[l])<CLEAR-1e-7:return False,'exact different-net clearance check rejected candidate'
        return True,'accepted'

    def run(self):
        lookup={p['id']:p for p in self.pads}
        for first,last in self.preconnect:
            a,b=lookup[first],lookup[last]
            if a['net']!=b['net']:raise ValueError('Seed pair must share a net')
            net=a['net'];width=POWER_WIDTHS.get(net,12)
            walk,via,through,obs=self.masks(net,width)
            path,expanded,reason=self.astar(a,b,walk,via,through)
            if path:
                ts,vs=self.geometry_from_path(net,width,a,b,path)
                good,reason=self.accept_geometry(ts,vs,obs)
                if good:
                    self.traces.extend(ts);self.vias.extend(vs);self.seed_edges.append((first,last))
            print(json.dumps({'preconnect':[first,last],'result':reason}),flush=True)
        nets=list(self.by_net)
        # Short local connections first within each class. Wide nets keep their required width.
        def span(n):
            ps=self.by_net[n];return max(p['x'] for p in ps)-min(p['x'] for p in ps)+max(p['y'] for p in ps)-min(p['y'] for p in ps)
        nets.sort(key=lambda n:((n in POWER) if self.order=='signals-first' else (n not in POWER),span(n)))
        nets=[n for n in self.priority if n in nets]+[n for n in nets if n not in self.priority]
        for net in nets:
            ps=self.by_net[net];width=POWER_WIDTHS.get(net,12)
            walk,via,through,obs=self.masks(net,width);ds=DSU(len(ps));fail=0;made=0
            ids={p['id']:i for i,p in enumerate(ps)}
            for first,last in self.seed_edges:
                if first in ids:ds.join(ids[first],ids[last])
            edges=sorted((math.hypot(a['x']-b['x'],a['y']-b['y']),i,j) for i,a in enumerate(ps) for j,b in enumerate(ps) if j>i)
            for _,i,j in edges:
                if ds.root(i)==ds.root(j):continue
                started=time.monotonic();path,expanded,reason=self.astar(ps[i],ps[j],walk,via,through)
                valid=False
                if path:
                    ts,vs=self.geometry_from_path(net,width,ps[i],ps[j],path)
                    valid,reason=self.accept_geometry(ts,vs,obs)
                    if valid:
                        self.traces.extend(ts)
                        for v in vs:
                            if not any(q['net']==v['net'] and abs(q['x']-v['x'])<.01 and abs(q['y']-v['y'])<.01 for q in self.vias):self.vias.append(v)
                        ds.join(i,j);made+=1
                self.attempts.append({'net':net,'a':ps[i]['id'],'b':ps[j]['id'],'accepted':valid,'reason':reason,'expanded':expanded,'seconds':round(time.monotonic()-started,3)})
                if not valid:fail+=1
                if fail>=40:break
            groups={}
            for i,p in enumerate(ps):groups.setdefault(ds.root(i),[]).append(p['id'])
            print(json.dumps({'net':net,'width':width,'connections':made,'pad_groups':list(groups.values()),'failed_attempts':fail}),flush=True)
        return {'traces':self.traces,'vias':self.vias,'attempts':self.attempts}

def validate(pads,candidate):
    """Independent continuous copper geometry and connectivity audit, not grid assertions."""
    problems=[];traceobjs=[(t,trace_geom(t)) for t in candidate['traces']]
    viaobjs=[(v,Point(v['x'],v['y']).buffer(v['diameter']/2,quad_segs=64)) for v in candidate['vias']]
    objects=[]
    for p in pads:
        circular=p['pad'][0]=='ELLIPSE'
        objects.append({'id':p['id'],'net':p['net'] or 'NC:'+p['id'],'layers':set(LAYERS),'geom':p['geom'],'kind':'pad','core':Point(p['x'],p['y']) if circular else p['geom'],'radius':p['pad'][1]/2 if circular else 0})
    for i,(t,g) in enumerate(traceobjs):objects.append({'id':'trace'+str(i),'net':t['net'],'layers':{t['layer']},'geom':g,'kind':'trace','core':LineString(t['points']),'radius':t['width']/2})
    for i,(v,g) in enumerate(viaobjs):objects.append({'id':'via'+str(i),'net':v['net'],'layers':set(LAYERS),'geom':g,'kind':'via','core':Point(v['x'],v['y']),'radius':v['diameter']/2})
    min_clear=1e9;min_edge=1e9;min_hole=1e9
    for o in objects:
        g=o['core'];edge=g.distance(BOARD.boundary)-o['radius'] if BOARD.covers(g) else -1
        hd=min(g.distance(Point(x*MM,y*MM))-1.6*MM-o['radius'] for x,y in [(5,5),(75,5),(75,27),(5,27)])
        min_edge=min(min_edge,edge);min_hole=min(min_hole,hd)
        if edge<EDGE-1e-3:problems.append({'kind':'board-edge','id':o['id'],'gap_mil':edge})
        if hd<HOLE_CLEAR-1e-3:problems.append({'kind':'mounting-hole','id':o['id'],'gap_mil':hd})
    for i,a in enumerate(objects):
        for b in objects[i+1:]:
            if a['net']==b['net'] or not(a['layers']&b['layers']):continue
            dist=a['core'].distance(b['core'])-a['radius']-b['radius'];min_clear=min(min_clear,dist)
            if dist<CLEAR-1e-3:problems.append({'kind':'different-net-clearance','a':a['id'],'b':b['id'],'nets':[a['net'],b['net']],'gap_mil':dist})
    connectivity=[]
    for net in sorted({p['net'] for p in pads if p['net']}):
        obs=[o for o in objects if o['net']==net];ds=DSU(len(obs))
        for i,a in enumerate(obs):
            for j,b in enumerate(obs[i+1:],i+1):
                if a['layers']&b['layers'] and a['core'].distance(b['core'])-a['radius']-b['radius']<.001:ds.join(i,j)
        groups={}
        for i,o in enumerate(obs):
            if o['kind']=='pad':groups.setdefault(ds.root(i),[]).append(o['id'])
        connectivity.append({'net':net,'connected':len(groups)==1,'groups':list(groups.values())})
    widths=[t['width'] for t in candidate['traces']]
    for i,t in enumerate(candidate['traces']):
        req=POWER_WIDTHS.get(t['net'],12)
        if t['width']<req:problems.append({'kind':'trace-width','trace':i,'required':req})
    drill_check=None
    if all('hole' in p for p in pads):
        drills=[{'id':p['id'],'x':p['x']+p.get('holeOffsetX',0),'y':p['y']+p.get('holeOffsetY',0),'diameter':p['hole'][1]} for p in pads]
        drills += [{'id':'via'+str(i),'x':v['x'],'y':v['y'],'diameter':v['drill']} for i,v in enumerate(candidate['vias'])]
        drills += [{'id':'NPTH'+str(i),'x':x*MM,'y':y*MM,'diameter':3.2*MM} for i,(x,y) in enumerate([(5,5),(75,5),(75,27),(5,27)])]
        minimum=min((math.hypot(a['x']-b['x'],a['y']-b['y'])-(a['diameter']+b['diameter'])/2,a['id'],b['id']) for i,a in enumerate(drills) for b in drills[i+1:])
        drill_check={'minimum_drill_edge_gap_mil':minimum[0],'closest_drill_ids':list(minimum[1:]),'all_drills_nonoverlapping':minimum[0]>=0,'source':'Precise native pcb_PrimitivePad.getAll() hole values; 4 frozen 3.2mm NPTH holes'}
        if minimum[0]<0:problems.append({'kind':'overlapping-drills','detail':drill_check})
    return {'status':'PASS_GEOMETRY' if not problems else 'FAIL_GEOMETRY','not_native_eda_drc':True,
            'geometry_model':'Exact point/line cores plus circular radii; rotated rectangular pad polygons. Copper spacing does not rely on tessellated circle buffers.',
            'minimum_different_net_clearance_mil':min_clear,'minimum_copper_board_edge_mil':min_edge,
            'minimum_copper_mounting_hole_mil':min_hole,'violations':problems,'connectivity':connectivity,
            'connected_nets':sum(n['connected'] for n in connectivity),'total_nets':len(connectivity),
            'trace_count':len(traceobjs),'via_count':len(viaobjs),'all_nets_connected':all(n['connected'] for n in connectivity),
            'trace_widths_mil':sorted(set(widths)),
            'widths_by_net_mil':{n:sorted({t['width'] for t in candidate['traces'] if t['net']==n}) for n in sorted({p['net'] for p in pads if p['net']})},
            'required_widths_by_net_mil':{n:POWER_WIDTHS.get(n,12) for n in sorted({p['net'] for p in pads if p['net']})},
            'power_vias':[v for v in candidate['vias'] if v['net'] in POWER],
            'drill_audit':drill_check,
            'limits':['Does not replace native EDA DRC or manufacturing review','Rounded getAllPins() hole readout ignored; precise native Pad drill values used when available','No impedance, thermal, voltage drop, antenna RF, assembly or soldermask validation']}

def preview(pads,candidate,validation,name='route-preview.svg'):
    scale=.42;mx=75;my=115;fw=W*scale+mx*2;fh=H*scale+my+110
    def xy(x,y):return (mx+x*scale,my+(H-y)*scale)
    def pathpoints(ps):return ' '.join(f'{xy(x,y)[0]:.2f},{xy(x,y)[1]:.2f}' for x,y in ps)
    out=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{fw:.0f}" height="{fh:.0f}" viewBox="0 0 {fw:.0f} {fh:.0f}">',
         '<rect width="100%" height="100%" fill="#f7f9fc"/>',
         '<style>text{font-family:Arial,sans-serif;fill:#233449} .padlabel{font-size:9px} .ref{font-size:12px;font-weight:bold}</style>',
         '<text x="40" y="35" font-size="24" font-weight="bold">Desktop Assistant - Actual placement / two-layer route candidate</text>',
         f'<text x="40" y="61" font-size="15">{validation["connected_nets"]}/{validation["total_nets"]} nets connected | {len(candidate["traces"])} traces | {len(candidate["vias"])} vias | {validation["status"]}</text>',
         '<text x="40" y="84" font-size="13">TOP red / BOTTOM blue / through-hole pads gold | 12 mil signals, 40 mil 5V/GND, 24 mil 3V3, 8 mil clearance | file units: mil</text>',
         f'<polygon points="{pathpoints(BOARD.exterior.coords)}" fill="#e2eadf" stroke="#45604b" stroke-width="2"/>']
    for x,y in [(5,5),(75,5),(75,27),(5,27)]:
        xx,yy=xy(x*MM,y*MM)
        out.append(f'<circle cx="{xx}" cy="{yy}" r="{2.5*MM*scale}" fill="none" stroke="#889994" stroke-dasharray="4 3"/><circle cx="{xx}" cy="{yy}" r="{1.6*MM*scale}" fill="#f7f9fc" stroke="#526674"/>')
    for t in sorted(candidate['traces'],key=lambda t:t['layer']=='TOP'):
        color='#d84b4b' if t['layer']=='TOP' else '#426fc4'
        out.append(f'<polyline points="{pathpoints(t["points"])}" fill="none" stroke="{color}" opacity=".8" stroke-width="{t["width"]*scale}" stroke-linecap="round" stroke-linejoin="round"><title>{html.escape(t["net"])} {t["layer"]}, {t["width"]} mil</title></polyline>')
    for v in candidate['vias']:
        x,y=xy(v['x'],v['y']);out.append(f'<circle cx="{x}" cy="{y}" r="{v["diameter"]/2*scale}" fill="#4f9465" stroke="#23402e"/><circle cx="{x}" cy="{y}" r="{v["drill"]/2*scale}" fill="#f7f9fc"/>')
    for p in pads:
        out.append(f'<polygon points="{pathpoints(p["geom"].exterior.coords)}" fill="#d6b362" stroke="#795c22" stroke-width=".7"><title>{html.escape(p["id"]+" "+(p["net"] or "NC"))}</title></polygon>')
        x,y=xy(p['x'],p['y']);out.append(f'<text x="{x}" y="{y+3}" class="padlabel" text-anchor="middle">{p["padNumber"]}</text>')
    for ref in sorted({p['ref'] for p in pads}):
        ps=[p for p in pads if p['ref']==ref];x,y=xy(sum(p['x'] for p in ps)/len(ps),sum(p['y'] for p in ps)/len(ps))
        out.append(f'<text x="{x}" y="{y-22}" class="ref" text-anchor="middle">{html.escape(ref)}</text>')
    lookup={p['id']:p for p in pads}
    for n in validation['connectivity']:
        if n['connected']:continue
        a=lookup[n['groups'][0][0]]
        for group in n['groups'][1:]:
            b=lookup[group[0]];out.append(f'<polyline points="{pathpoints([(a["x"],a["y"]),(b["x"],b["y"])])}" fill="none" stroke="#ce24a8" stroke-width="1.5" stroke-dasharray="6 4"><title>UNROUTED {html.escape(n["net"])}</title></polyline>')
    out += [f'<text x="40" y="{fh-63}" font-size="13">U-notch: x 0..24.17 mm, y 9.5..22.5 mm. Holes: diameter 3.2 mm; dashed rings = 2.5 mm screw-head radius. Edge: 12 mil.</text>',
            f'<text x="40" y="{fh-39}" font-size="13">Pad geometry and positions come from pcb-placed-pads.json. Empty-net pads remain copper obstacles. Magenta dashed lines = disconnected groups.</text>',
            f'<text x="40" y="{fh-15}" font-size="13">Offline candidate only. Independent continuous geometry audit performed; native EDA DRC and fabrication checks remain required.</text>','</svg>']
    (ROOT/name).write_text('\n'.join(out))

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--step',type=float,default=5);ap.add_argument('--order',choices=['signals-first','power-first'],default='signals-first');ap.add_argument('--priority',default='');ap.add_argument('--preconnect',default='');ap.add_argument('--ground-layer',choices=LAYERS);ap.add_argument('--prefix',default='route-candidate');ap.add_argument('--validate-only',action='store_true');args=ap.parse_args()
    src,digest,raw,pads=read_input()
    if args.validate_only:
        candidate=json.loads((ROOT/(args.prefix+'.json')).read_text())
        if candidate['source_sha256']!=digest:raise RuntimeError('Placement changed since routing; regenerate before acceptance')
        if candidate.get('precise_pad_audit'):
            pads,precise_evidence=precise_pads(pads)
            if precise_evidence['sha256']!=candidate['precise_pad_audit']['sha256']:raise RuntimeError('Precise pad source changed')
    else:
        started=time.monotonic();router=Router(pads,args.step,args.order,[n for n in args.priority.split(',') if n],[x.split(':') for x in args.preconnect.split(',') if x],args.ground_layer);candidate=router.run()
        candidate.update(schema='desktop-assistant.offline-route-candidate.v1',units='mil',source='../pcb-placed-pads.json',source_sha256=digest,
                         input_components=len(raw),input_pads=len(pads),grid_mil=args.step,grid_type='base grid plus pad centres and 100mil connector midlines',route_order=args.order,priority=router.priority,preconnect=router.preconnect,ground_layer=args.ground_layer,
                         rules={'signal_width':12,'width_by_power_net':POWER_WIDTHS,'clearance':CLEAR,'board_edge_clearance':EDGE,'mounting_hole_copper_clearance':HOLE_CLEAR,'screw_head_keepout_radius_mm':2.5,'via_diameter':VIA_DIAM,'via_drill':VIA_DRILL},
                         board={'outline_mil':list(BOARD.exterior.coords),'size_mm':[80,32],'cutout_mm':[0,24.17,9.5,22.5],'holes_mm':[[5,5,3.2],[75,5,3.2],[75,27,3.2],[5,27,3.2]]},
                         elapsed_seconds=round(time.monotonic()-started,3),not_for_fabrication=True)
        if hashlib.sha256(src.read_bytes()).hexdigest()!=digest:raise RuntimeError('Placement changed during routing; no candidate published')
    check=validate(pads,candidate)
    if candidate.get('precise_pad_audit'):check['precise_pad_audit']=candidate['precise_pad_audit']
    candidate['unrouted']=[n for n in check['connectivity'] if not n['connected']]
    candidate['validation_summary']={k:check[k] for k in ['status','connected_nets','total_nets','all_nets_connected','trace_count','via_count']}
    (ROOT/(args.prefix+'.json')).write_text(json.dumps(candidate,ensure_ascii=False,indent=2)+'\n')
    (ROOT/(args.prefix+'-validation.json')).write_text(json.dumps(check,ensure_ascii=False,indent=2)+'\n')
    preview(pads,candidate,check,args.prefix+'-preview.svg')
    print(json.dumps({'FINAL':candidate['validation_summary'],'violations':check['violations'][:10],'unrouted':candidate['unrouted']},ensure_ascii=False),flush=True)

if __name__=='__main__':main()
