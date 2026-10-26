from board_geom import *
attrs=json.loads((P/'attributes-before.json').read_text())
co={c['component']['primitiveId']:c for c in components}
body={}
for c in components:
 ref=c['component']['designator'];pg=[p['geom'] for p in pads if p['ref']==ref];bg=[b['geom'] for b in bodies if b['ref']==ref]
 body[ref]=union_all(pg+bg).envelope.buffer(.12)
# New cable connector body is not in the earlier archive's footprint library snapshot.
body['J3']=box(75,2.5,101,9.6)
occupied=union_all(list(body.values())+[keep,box(56.7,10,71.2,53)])
usable=box(.8,.8,109.2,74.2)
labels=[]
def try_label(text,x,y,size,ref=None,rotation=0,force=False):
 global occupied
 w=size*.77*len(text)+.3;h=size+.3
 if rotation==90:w,h=h,w
 bb=box(x-w/2,y-h/2,x+w/2,y+h/2)
 if not force and (not usable.covers(bb) or bb.intersects(occupied)):return False
 labels.append(dict(text=text,x=x,y=y,size=size,rotation=rotation,ref=ref,bounds=list(bb.bounds)))
 occupied=union_all([occupied,bb.buffer(.12)])
 return True
for text,x,y,size in [('DesktopAssistant',52,62,1.35),('Integrated V1.0',52,65,1.15),('2S / 2oz / 1.6mm',52,67.3,.95),('Jay',48,70,1.5),('S',101.46,14.8,1),('+',104,14.8,1),('-',106.54,14.8,1),('B-',11.5,2.2,.9),('B+',16.5,2.2,.9),('B-  BM  B+',8,26.3,.8),('LCD SPI 3V3',88,1.15,.9),('USB 5V CHARGE',13,65.6,.8),('100k NTC',25,74,.8),('OPEN',32,60.4,.8),('OPEN',77,14.5,.8),('OPEN',74,58.8,.8)]:
 if not try_label(text,x,y,size):print('Legend needs reposition',text)
for a in sorted([a for a in attrs if a['key']=='Designator'],key=lambda a:(-len(a['value']),a['value'])):
 c=co[a['parentPrimitiveId']];ref=c['component']['designator'];x0,y0,x1,y1=body[ref].bounds;cx=(x0+x1)/2;cy=(y0+y1)/2
 found=False
 for sz in [.85,.75]:
  w=sz*.77*len(ref)+.3;h=sz+.3
  for gap in [.3,.65,1,1.6,2.3,3.0,4.0]:
   candidates=[(cx,y0-h/2-gap),(cx,y1+h/2+gap),(x0-w/2-gap,cy),(x1+w/2+gap,cy)]
   candidates += [(cx+dx,y0-h/2-gap) for dx in [-2,2,-4,4]]
   candidates += [(cx+dx,y1+h/2+gap) for dx in [-2,2,-4,4]]
   for x,y in candidates:
    if try_label(ref,x,y,sz,ref=ref):found=True;break
   if found:break
  if found:break
 if not found:print('No label position',ref)
byref={a['value']:a for a in attrs if a['key']=='Designator'}
mods=[]
for l in labels:
 if l['ref']:
  a=byref[l['ref']];mods.append(dict(id=a['primitiveId'],prop=dict(x=l['x']/M,y=-l['y']/M,rotation=0,fontSize=l['size']/M,lineWidth=.15/M,alignMode=5,keyVisible=False,valueVisible=True)))
for a in attrs:
 if a['key']!='Designator' and (a['keyVisible'] or a['valueVisible']):mods.append(dict(id=a['primitiveId'],prop=dict(keyVisible=False,valueVisible=False)))
plan=dict(labels=labels,attributes=mods,legends=[l for l in labels if not l['ref']])
(P/'silkscreen-plan.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2));print('Labels',len(labels),'designators',sum(bool(l['ref']) for l in labels),'legends',len(plan['legends']))
