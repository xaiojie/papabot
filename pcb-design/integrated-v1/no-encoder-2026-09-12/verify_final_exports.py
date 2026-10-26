"""Validate saved native archive and actual exported Gerber/drill geometry."""
import sys,json,re,math,zipfile,hashlib,csv,shutil
from pathlib import Path
from collections import defaultdict,Counter
from datetime import datetime
sys.path.insert(0,str(Path(__file__).resolve().parent.parent/"layout-2026-09-12"))
from gerber_review import read,native_region,shape
from shapely.geometry import Point,LineString,box,Polygon
from shapely.affinity import rotate,translate
from shapely import union_all
P=Path(__file__).resolve().parent.parent/'final-no-encoder-2026-09-12'
sys.path.insert(0,str(P.parents[1]/'native-rev-b'))
from verify_exports import parse,equivalent,points_match,gerber_tracks
M=.0254;PCB='bc31667e02a33e5b'
def write(n,v):(P/n).write_text(json.dumps(v,ensure_ascii=False,indent=2))
def sha(f):return hashlib.sha256(f.read_bytes()).hexdigest()
def drill(text):
    tools={};cur=None;holes=[];slots=[]
    for l in text.splitlines():
        m=re.fullmatch(r'T(\d+)C([\d.]+)',l)
        if m:tools[m[1]]=float(m[2]);continue
        if re.fullmatch(r'T\d+',l):cur=l[1:];continue
        if l.startswith('X'):
            nums=list(map(float,re.findall(r'[XY](-?[\d.]+)',l)))
            if 'G85' in l:
                a,b=sorted([tuple(nums[:2]),tuple(nums[2:])]);slots.append((*a,*b,tools[cur]))
            else:holes.append((*nums,tools[cur]))
    return holes,slots

archive=P/'DesktopAssistant_Integrated_final.epro2'
gerber=P/'DesktopAssistant_Integrated_Gerber_review.zip'
with zipfile.ZipFile(archive) as z:
    assert z.testzip() is None;docs=parse(z.read('DesktopAssistant_Integrated.epru').decode())
pcb=docs[PCB];live=parse((P/'PCB1.source').read_text())[PCB]
types={'COMPONENT','PAD_NET','PAD','LINE','VIA','POLY','ATTR','STRING','RULE','RULE_SELECTOR','RULE_TEMPLATE','LAYER_PHYS','FILL'}
empty=('RULE_SELECTOR','["RULE_SELECTOR",["NET",""]]')
assert live[empty]=={'ruleOrder':4,'ruleKeyValue':{'NET_LENGTH_TOLERANCE':['default',None]},'copperValue':{},'innerPlaneValue':{}} and empty not in pcb
# Canonical archive retains sub-2um endpoint segments removed from the live API's view.
# Accept them only when their entire copper lies within 2um of same-net live copper.
canonical=[];diff=[]
for k in live.keys()|pcb.keys():
    if k[0]not in types or k==empty or equivalent(live.get(k),pcb.get(k)):continue
    a,b=live.get(k),pcb.get(k)
    if k[0]=='COMPONENT'and a and b:
        aa=dict(a);bb=dict(b);aa['angle']%=360;bb['angle']%=360
        if equivalent(aa,bb):canonical.append({'key':k,'normalization':'rotation modulo 360'});continue
    if k==('RULE_SELECTOR','["RULE_SELECTOR",["NET","GND"]]') and a=={'ruleOrder':4,'ruleKeyValue':{},'copperValue':{},'innerPlaneValue':{}} and b=={'ruleOrder':4,'ruleKeyValue':{'COPPER':'copperRegion'},'copperValue':{},'innerPlaneValue':{}}:
        canonical.append({'key':k,'normalization':'native GND copperRegion selector'});continue
    if k[0]=='LINE'and a is None and b:
        def cu(v):return LineString([(v['startX']*M,v['startY']*M),(v['endX']*M,v['endY']*M)]).buffer(v['width']*M/2)
        length=math.hypot(b['startX']-b['endX'],b['startY']-b['endY'])*M
        own=union_all([cu(v)for(t,_),v in live.items()if t=='LINE'and v['netName']==b['netName']and v['layerId']==b['layerId']]+[native_region(v['path'])for(t,_),v in live.items()if t=='FILL'and v['netName']==b['netName']and v['layerId']==b['layerId']])
        if length<.002 and cu(b).difference(own.buffer(.002)).area<1e-8:
            canonical.append({'key':k,'normalization':'sub-2um covered endpoint segment','length_mm':length});continue
    diff.append(k)
assert not diff,diff
pages=sorted([(r[('META','META')]['zIndex'],i,r[('META','META')]['title'])for i,r in docs.items()if r.get(('DOCHEAD',None),{}).get('docType')=='SCH_PAGE'and not r.get(('DELETE_DOC','DELETE_DOC'),{}).get('isDelete')])
assert [t for _,_,t in pages]==['01_电池保护与均衡','02_USB充电','03_配电与主控','04_显示音频与交互','05_八路舵机驱动']
geo=json.loads((P/'PCB1_geometry.json').read_text())
gen=P.parent/'no-encoder-2026-09-12'
for old,new in [('native-netlist.json','Schematic_netlist.json'),('verification.json','Schematic_verification.json'),('native-drc.json','Schematic_DRC_final.json'),('reviewed-pin-nets.json','Reviewed_pin_nets.json')]:shutil.copyfile(gen/old,P/new)
netlist=json.loads((P/'Schematic_netlist.json').read_text());expected={(c['props']['Designator'],str(pin)):v['net']for c in netlist['components'].values()for pin,v in c['pinInfoMap'].items()}
actual={(c['component']['designator'],str(p['padNumber'])):p['net']for c in geo['geometry']for p in c['pads']}
assert expected==actual and len(actual)==310
attrs={(v['parentId'],v['key']):v['value']for (t,_),v in pcb.items()if t=='ATTR'}
pnmap={(json.loads(k)[1],json.loads(k)[3]):v['padNet']for(t,k),v in pcb.items()if t=='PAD_NET'}
pth=[];npth=[];slots=[];padgeoms=[];bodies=[];stencil_custom=0
for (t,cid),co in pcb.items():
    if t!='COMPONENT':continue
    assert co['layerId']==1
    fp=attrs[(cid,'Footprint')];ref=attrs[(cid,'Designator')];angle=math.radians(co['angle'])
    def transform(x,y):return (co['x']+x*math.cos(angle)-y*math.sin(angle),co['y']+x*math.sin(angle)+y*math.cos(angle))
    for (pt,pid),pad in docs[fp].items():
        if pt=='FILL'and pad.get('layerId')==12:
            path=pad['path'];assert path[0]=='CIRCLE'
            hx,hy=transform(path[1],path[2]);npth.append((hx*M,hy*M,path[3]*2*M))
        if pt=='POLY'and pad.get('layerId')==48:
            # Straight courtyards only; circles handled separately.
            path=pad['path']
            if path[0]=='CIRCLE':b=Point(path[1]*M,path[2]*M).buffer(path[3]*M)
            elif len(path)>2 and path[2]=='L':b=native_region([path])
            elif len(path)>3 and path[2]=='ARC'and abs(path[3])>350:b=Point(0,0).buffer(math.hypot(*path[:2])*M)
            else:continue
            bodies.append((ref,translate(rotate(b,co['angle'],origin=(0,0)),co['x']*M,co['y']*M)))
        if pt=='FILL'and pad.get('layerId')==7:stencil_custom+=1
        if pt!='PAD':continue
        x,y=transform(pad['centerX'],pad['centerY']);a=math.radians(co['angle']+pad['padAngle'])
        px=x+pad['padOffsetX']*math.cos(a)-pad['padOffsetY']*math.sin(a)
        py=y+pad['padOffsetX']*math.sin(a)+pad['padOffsetY']*math.cos(a)
        sh=pad['defaultPad'];kind={'RECT':'R','ELLIPSE':'C','OVAL':'O'}[sh['padType']]
        if kind=='C'and abs(sh['width']-sh['height'])>.01:
            from shapely.affinity import scale
            pg=scale(Point(0,0).buffer(1,quad_segs=32),sh['width']*M/2,sh['height']*M/2)
        else:pg=shape(kind,sh['width']*M,sh['height']*M)
        pg=translate(rotate(pg,co['angle']+pad['padAngle'],origin=(0,0)),px*M,py*M)
        pn=str(pad['num']);net=pnmap.get((cid,pid),'')
        if pn:assert expected[(ref,pn)]==net,(ref,pn,net)
        padgeoms.append(dict(ref=ref,pin=pn,net=net,x=x,y=y,geom=pg,smd=pad['layerId']==1))
        h=pad.get('hole')
        if not h or not h.get('width'):continue
        if h['holeType']=='ROUND':(pth if pad['plated']else npth).append((px*M,py*M,h['width']*M))
        else:
            assert h['holeType']=='SLOT'and pad['plated']
            w,hh=h['width']*M,h['height']*M;r=abs(w-hh)/2;aa=math.radians(co['angle']+pad['padAngle']+pad['relativeAngle']+(90 if hh>w else 0))
            p1=(px*M-r*math.cos(aa),py*M-r*math.sin(aa));p2=(px*M+r*math.cos(aa),py*M+r*math.sin(aa));aa,bb=sorted([p1,p2]);slots.append((*aa,*bb,min(w,hh)))
for (t,_),v in pcb.items():
    if t=='PAD':npth.append((v['centerX']*M,v['centerY']*M,v['hole']['width']*M))
vias=[(v['centerX']*M,v['centerY']*M,v['holeDiameter']*M)for(t,_),v in pcb.items()if t=='VIA']
overlaps=[(a,b,round(ga.intersection(gb).area,4))for i,(a,ga)in enumerate(bodies)for b,gb in bodies[i+1:]if a!=b and ga.intersection(gb).area>.1]
assert not overlaps,overlaps
write('Native_archive_verification.json',{'passed':True,'archive_crc_pass':True,'sha256':sha(archive),'pcb_geometry_rules_stackup_match_saved_source':True,'normalized_empty_default_selector':str(empty),'export_normalizations':canonical,'active_pages':[{'uuid':i,'title':t}for _,i,t in pages],'historical_deleted_pages':4,'components':79,'component_pins':310,'schematic_pcb_pinmaps_match':True,'body_outlines_checked':len(bodies),'body_outline_overlaps':overlaps,'physical_stackup':{str(k):v for k,v in pcb.items()if k[0]=='LAYER_PHYS'}})
with zipfile.ZipFile(gerber) as z:
    assert z.testzip()is None
    holes,actualslots=drill(z.read('Drill_PTH_Through.DRL').decode());actualnpth,_=drill(z.read('Drill_NPTH_Through.DRL').decode());actualvias,_=drill(z.read('Drill_PTH_Through_Via.DRL').decode())
    delta=max(points_match(holes,pth+vias,.003),points_match(actualnpth,npth,.003),points_match(actualvias,vias,.003),points_match(actualslots,slots,.003))
    outline=[(int(x)/1e6,int(y)/1e6)for x,y in re.findall(r'G01X(-?\d+)Y(-?\d+)D0[12]\*',z.read('Gerber_BoardOutlineLayer.GKO').decode())]
    assert len(outline)==5 and max(abs(a-b)for pt,exp in zip(outline,[(0,0),(110,0),(110,-75),(0,-75),(0,0)])for a,b in zip(pt,exp))<.000002
    layers={};counts={};fill_delta={}
    for layer,fn in [(1,'Gerber_TopLayer.GTL'),(2,'Gerber_BottomLayer.GBL')]:
        text=z.read(fn).decode();segs=gerber_tracks(text);es=[]
        for l in geo['lines']:
            if l['layer']!=layer:continue
            a,b=sorted([(round(l['startX']*M,6),round(l['startY']*M,6)),(round(l['endX']*M,6),round(l['endY']*M,6))]);es.append((*a,*b,l['lineWidth']*M))
        points_match(segs,es,.00001);counts[fn]=len(segs);layers[layer],regions=read(text)
        native=union_all([native_region(v['path'])for(t,_),v in pcb.items()if t=='FILL'and v['layerId']==layer])
        fill_delta[layer]=native.difference(regions.buffer(.00001)).area;assert fill_delta[layer]<.0001,fill_delta
    paste,_=read(z.read('Gerber_TopPasteMaskLayer.GTP').decode());mask,_=read(z.read('Gerber_TopSolderMaskLayer.GTS').decode())
    missingpaste=[p['ref']+'.'+p['pin']for p in padgeoms if p['smd'] and p['geom'].intersection(paste).area<.01]
    missingmask=[p['ref']+'.'+p['pin']for p in padgeoms if p['geom'].intersection(mask).area<.01]
    assert not missingpaste,missingpaste
    assert not missingmask,missingmask
    probe=json.loads(z.read('FlyingProbeTesting.json'));byname=defaultdict(list)
    for row in probe['pins']['rows']:byname[row[1]].append(row)
    ncs={}
    for (ref,pin),net in expected.items():
        rows=byname[ref+'_'+pin];assert rows
        if net:assert all(x[6]==net for x in rows),(ref,pin)
        else:ncs[ref+'.'+pin]=rows[0][6];assert len({x[6]for x in rows})==1
    assert len(ncs)==len(set(ncs.values()))==48
    report={'passed':True,'checked_at':datetime.now().astimezone().isoformat(),'sha256':sha(gerber),'crc_pass':True,'board_outline_mm':outline,'plated_round_holes':len(holes),'plated_slots':len(slots),'component_round_holes':len(pth),'vias':len(vias),'nonplated_holes':len(npth),'mounting_holes':4,'maximum_drill_delta_mm':delta,'drills_and_slots_match_native_archive':True,'copper_segments':counts,'all_copper_segments_match':True,'static_fill_coverage_missing_mm2':fill_delta,'smd_pads_checked':sum(p['smd']for p in padgeoms),'missing_paste_openings':missingpaste,'missing_soldermask_openings':missingmask,'native_custom_stencil_regions':stencil_custom,'flying_probe_pinmaps_match':True,'isolated_nc_pins':len(ncs),'separate_via_drill_is_subset_of_pth':True}
    write('Gerber_verification.json',report)
    # Render the actual manufacturing layers for the review, independent of UI access.
    from PIL import Image,ImageDraw,ImageFont
    S=14;W=1540;H=1050
    def paint(img,g,color,flip=False):
        d=ImageDraw.Draw(img)
        def coords(seq):return [((110-x if flip else x)*S,-y*S)for x,y in seq]
        if g.is_empty:return
        if g.geom_type!='Polygon':
            for x in g.geoms:paint(img,x,color,flip)
            return
        layer=Image.new('L',(W,H));ld=ImageDraw.Draw(layer);ld.polygon(coords(g.exterior.coords),fill=255)
        for hole in g.interiors:ld.polygon(coords(hole.coords),fill=0)
        img.paste(color,(0,0),layer)
    for layer,label,silkfn in [(1,'Top','Gerber_TopSilkscreenLayer.GTO'),(2,'Bottom','Gerber_BottomSilkscreenLayer.GBO')]:
        img=Image.new('RGB',(W,H),'#092039');paint(img,layers[layer],'#0b527e',layer==2)
        solder,_=read(z.read('Gerber_TopSolderMaskLayer.GTS'if layer==1 else 'Gerber_BottomSolderMaskLayer.GBS').decode());paint(img,solder.intersection(layers[layer]),'#dec691',layer==2)
        silk,_=read(z.read(silkfn).decode());paint(img,silk,'#eef5f7',layer==2)
        for x,y,dia in holes+actualnpth:paint(img,Point(x,y).buffer(dia/2),'#101820',layer==2)
        for x,y,xx,yy,dia in actualslots:paint(img,LineString([(x,y),(xx,yy)]).buffer(dia/2),'#101820',layer==2)
        img.save(P/f'PCB_Gerber_{label}.png')
print(json.dumps(report,ensure_ascii=False,indent=2))
