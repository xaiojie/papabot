"""Independent geometry reader for this EasyEDA RS-274X export (millimeters, 2.6)."""
import sys,re,math
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'native-rev-a/router/_deps'))
from shapely.geometry import Point,Polygon,LineString,box
from shapely import union_all
from shapely.affinity import scale

def shape(kind,w,h=None):
    h=w if h is None else h
    if kind=='R':return box(-w/2,-h/2,w/2,h/2)
    if kind=='C':return Point(0,0).buffer(w/2,quad_segs=32)
    if kind=='O':
        if abs(w-h)<1e-8:return shape('C',w)
        return (LineString([(-w/2+h/2,0),(w/2-h/2,0)]).buffer(h/2,quad_segs=32) if w>h
                else LineString([(0,-h/2+w/2),(0,h/2-w/2)]).buffer(w/2,quad_segs=32))
    raise ValueError(kind)

def read(text):
    from shapely.affinity import translate
    assert '%FSLAX26Y26*%' in text and '%MOMM*%' in text
    apertures={};macros={};geoms=[];regions=[];inregion=False;contours=[];points=[];xy=None;current=None
    for s in text.splitlines():
        s=s.strip()
        if s.startswith('%AMRoundRect*'):continue
        m=re.fullmatch(r'%ADD(\d+)RoundRect,([^*]+)\*%',s)
        if m:
            dia,x1,y1,x2,y2=map(float,m[2].split('X'));macros[m[1]]=Polygon([(x1,y1),(x2,y2),(-x1,-y1),(-x2,-y2)]).buffer(dia/2,quad_segs=32);continue
        m=re.fullmatch(r'%ADD(\d+)([CRO]),([\d.]+)(?:X([\d.]+))?\*%',s)
        if m:apertures[m[1]]=(m[2],float(m[3]),float(m[4]) if m[4] else None);continue
        m=re.fullmatch(r'G54D(\d+)\*',s)
        if m:current=m[1];continue
        if s=='G36*':inregion=True;contours=[];points=[];continue
        if s=='G37*':
            if points:contours.append(points)
            region=Polygon()
            for loop in contours:
                if len(loop)>=3:region=region.symmetric_difference(Polygon(loop).buffer(0))
            regions.append(region);geoms.append(region);inregion=False;continue
        m=re.fullmatch(r'G0([123])X(-?\d+)Y(-?\d+)(?:I(-?\d+)J(-?\d+))?D0([123])\*',s)
        if m:
            end=(int(m[2])/1e6,int(m[3])/1e6);op=m[6]
            if op=='2':
                if inregion:
                    if points:contours.append(points)
                    points=[end]
                xy=end;continue
            if op=='3':
                flash=macros[current] if current in macros else shape(*apertures[current])
                geoms.append(translate(flash,*end));xy=end;continue
            assert xy is not None
            route=[xy,end]
            if m[1] in ['2','3']:
                cx=xy[0]+int(m[4])/1e6;cy=xy[1]+int(m[5])/1e6;r=math.hypot(xy[0]-cx,xy[1]-cy)
                a=math.atan2(xy[1]-cy,xy[0]-cx);b=math.atan2(end[1]-cy,end[0]-cx)
                sweep=(b-a)%(2*math.pi) if m[1]=='3' else -((a-b)%(2*math.pi))
                if abs(sweep)<1e-9:sweep=(1 if m[1]=='3' else -1)*2*math.pi
                n=max(4,math.ceil(abs(sweep)*r/.015));route=[(cx+r*math.cos(a+sweep*i/n),cy+r*math.sin(a+sweep*i/n))for i in range(n+1)]
            if inregion:points.extend(route[1:])
            else:
                kind,w,h=apertures[current];assert kind=='C';geoms.append(LineString(route).buffer(w/2,quad_segs=24))
            xy=end;continue
        if not s or s.startswith(('G04','%FSL','%MO','G75','M02')):continue
        raise ValueError('Unsupported Gerber statement '+s)
    return union_all(geoms),union_all(regions)

def native_region(paths,m=.0254):
    out=Polygon()
    for path in paths:
        assert path[2]=='L' and all(isinstance(v,(int,float))for v in path[3:])
        nums=path[:2]+path[3:]
        out=out.symmetric_difference(Polygon([(nums[i]*m,nums[i+1]*m)for i in range(0,len(nums),2)]).buffer(0))
    return out
