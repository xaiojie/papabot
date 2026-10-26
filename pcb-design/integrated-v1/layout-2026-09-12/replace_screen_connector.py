import json,hashlib,sys,copy,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent.parent/'repair-2026-09-12'))
from eda_client import execute,ROOT
out=Path(__file__).resolve().parent

def parse(s):
 return [(json.loads(l.split('||',1)[0]),json.JSONDecoder().raw_decode(l.split('||',1)[1])[0]) for l in s.splitlines() if '||' in l]
def uid(s):return hashlib.sha256(('layout-screen:'+s).encode()).hexdigest()[:16]
def rec(t,i,v):return ({'type':t,'id':uid(i),'ticket':10000},v)
def attr(i,k,v,**kw):return rec('ATTR',i+':'+k,dict(parentId=i,key=k,value=v,zIndex=10,valueVisible=False,keyVisible=False,**kw))
old=parse((ROOT/'generated/final-04.source').read_text())
tmp=json.load(open(out/'screen-template.json'));tid=tmp['component']['primitiveId'];cid=next(v['parentId'] for h,v in old if h['type']=='ATTR' and v.get('key')=='Designator' and v.get('value')=='J3')
wg={v['lineGroup'] for h,v in old if h['type']=='LINE' and min(v['startX'],v['endX'])>810 and min(v['startY'],v['endY'])<-650}
assert len(wg)==8
rs=[(h,v) for h,v in old if h.get('id')!=cid and not v.get('parentId','').startswith(cid) and h.get('id') not in wg and v.get('parentId') not in wg and v.get('lineGroup') not in wg]
for h,v in rs:
 if h['type']=='TEXT' and v['value']=='Pins 1-10 = primary interface; alternate pins 11-20 unused.':v['value']='J3: cable to external HS24S010B pins 1-10; pins 9/10 NC.'
 if h['type']=='TEXT' and v['value']=='SPI display / HS24S010B':v['value']='SPI display harness / 屏幕线束接口'
for h,v in parse(tmp['source']):
 if h.get('id')==tid or v.get('parentId')==tid:
  h=copy.deepcopy(h);v=copy.deepcopy(v);h['id']=cid if h['type']=='COMPONENT' else uid(h['id'])
  if h['type']=='ATTR':
   v['parentId']=cid
   if v.get('key')=='Designator':v.update(value='J3',x=1200,y=-925,fontSize=8,align='CENTER_BOTTOM',valueVisible=True)
   if v.get('key')=='Unique ID':v['value']='int-J3'
   if v.get('key')=='Name':v.update(x=1200,y=-775,fontSize=7,align='CENTER_BOTTOM',valueVisible=True)
  rs.append((h,v))
exp=json.load(open(ROOT/'generated/reviewed-pin-nets.json'));nets={k:v for k,v in exp['J3']['pins'].items() if int(k)<=10}
for p in tmp['pins']:
 pn=p['pinNumber'];n=nets[pn];x=p['x'];y=-p['y'];suffix=p['primitiveId'][len(tid):]
 if not n:rs.append(attr(cid+suffix,'NO_CONNECT','yes',x=x,y=y));continue
 w=uid('wire:'+pn);rs.append(({'type':'WIRE','id':w,'ticket':10000},{'zIndex':100}))
 rs.append(rec('LINE','line:'+pn,dict(startX=x,startY=y,endX=x-55,endY=y,lineGroup=w,strokeWidth=None,strokeColor=None,strokeStyle=None,fillColor=None,fillStyle=None)))
 a=attr(w,'NET',n,x=x-5,y=y-2,fontSize=6,rotation=0,align='RIGHT_BOTTOM');a[1]['valueVisible']=True;rs.append(a);rs.append(attr(w,'Relevance',[]))
page=execute('return await eda.dmt_Schematic.createSchematicPage("6c93ab84d69093e6");','create-final-display-sheet')
assert page
for h,v in rs:
 if h['type']=='DOCHEAD':v['uuid']=page
source='\n'.join(json.dumps(h,ensure_ascii=False)+'||'+json.dumps(v,ensure_ascii=False)+'|' for h,v in rs)+'\n'
(out/'display-with-connector.source').write_text(source)
execute('return await eda.dmt_EditorControl.openDocument('+json.dumps(page)+');','open-final-display');time.sleep(.6)
print(execute('if((await eda.dmt_SelectControl.getCurrentDocumentInfo()).uuid!=='+json.dumps(page)+')throw Error("wrong sheet");if(!await eda.sys_FileManager.setDocumentSource('+json.dumps(source)+'))throw Error("source rejected");return await eda.sch_Document.save();','write-final-display'),flush=True)
state=json.load(open(out/'screen-page.json'));state['final']=page;(out/'screen-page.json').write_text(json.dumps(state))
for p in [state['old'],state['new']]:print('remove backed up sheet',p,execute('return await eda.dmt_Schematic.deleteSchematicPage('+json.dumps(p)+');','remove-replaced-sheet'),flush=True)
execute('return await eda.dmt_Schematic.modifySchematicPageName('+json.dumps(page)+',"04_显示音频与交互");','name-display-sheet')
pp=ROOT/'generated/pages.json';pages=json.load(open(pp));pages['04']=page;pp.write_text(json.dumps(pages,indent=2))
exp['J3'].update(pins=nets,pinNames={str(i):str(i) for i in range(1,11)},template='XH10',name='XH-10A display harness')
(out/'reviewed-pin-nets-before-screen.json').write_bytes((ROOT/'generated/reviewed-pin-nets.json').read_bytes())
(ROOT/'generated/reviewed-pin-nets.json').write_text(json.dumps(exp,ensure_ascii=False,indent=2))
print('new page',page)
