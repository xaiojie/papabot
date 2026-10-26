import json,math,hashlib
from eda_client import execute,ROOT
pages=json.load(open(ROOT/'generated/pages.json'))
expected=json.load(open(ROOT/'generated/reviewed-pin-nets.json'));layout=json.load(open(ROOT/'generated/pins-layout.json'))
def uid(k):return hashlib.sha256(('integrated-repair-v1:'+k).encode()).hexdigest()[:16]
pg='01';pid=pages[pg]
execute('return await eda.dmt_EditorControl.openDocument('+json.dumps(pid)+');','polish-open')
ops=[]
for ref in ['R4','U2','C3','R18','Q3','R19']:
 # The initial authored origins are derived from this page's deterministic source.
 src=(ROOT/'generated/01.source').read_text()
 for line in src.splitlines():
  a,b=line.split('||',1);h=json.loads(a);v=json.JSONDecoder().raw_decode(b)[0]
  if h.get('id')==expected[ref]['id']:cy=-v['y'];break
 ops.append('if(!await eda.sch_PrimitiveComponent.modify('+json.dumps(expected[ref]['id'])+',{y:'+str(cy-50)+'}))throw new Error("move component");')
 for p in layout[ref]:
  net=expected[ref]['pins'][p['pinNumber']]
  if not net:continue
  rad=math.radians(p['rotation']);points=[p['x'],p['y']-50,round(p['x']+45*math.cos(rad),6),round(p['y']-50+45*math.sin(rad),6)]
  ops.append('if(!await eda.sch_PrimitiveWire.modify('+json.dumps(uid('wire:'+ref+':'+p['pinNumber']))+',{line:'+json.dumps(points)+'}))throw new Error("move wire");')
ops.append('if(!await eda.sch_PrimitiveRectangle.modify('+json.dumps(uid('box:01:Lower cell balance / 下节电芯'))+',{topLeftY:570,height:340}))throw new Error("move box");')
ops.append('if(!await eda.sch_PrimitiveText.modify('+json.dumps(uid('text:01:65:665:Lower cell balance / 下节电芯'))+',{y:545}))throw new Error("move title");')
print(execute(''.join(ops)+'return await eda.sch_Document.save();','polish-lower-balance'))
