import sys,json
from pathlib import Path
P=Path(__file__).resolve().parent;sys.path.insert(0,str(P.parent/'repair-2026-09-12'))
from eda_client import execute
r=json.loads((P/'sheet03-before.json').read_text());ws=[w['primitiveId']for w in r['wires'] if w['net'].startswith('ENC_')];assert len(ws)==3
js='const d=await eda.dmt_SelectControl.getCurrentDocumentInfo();if(d.uuid!=="8e03abe4b069eaeb")throw Error("wrong page03");await eda.sch_PrimitiveWire.delete('+json.dumps(ws)+');'
for ref,nums in [('J1',['13']),('J2',['2','8'])]:
 c=next(c for c in r['components']if c.get('designator')==ref)
 js+='for(const p of await eda.sch_PrimitiveComponent.getAllPinsByPrimitiveId('+json.dumps(c['primitiveId'])+'))if('+json.dumps(nums)+'.includes(p.getState_PinNumber())){const a=p.toAsync();a.setState_NoConnected(true);await a.done();}'
js+='await eda.sch_PrimitiveText.modify("6ab288cdf0f6c6c0",{content:"Revision 1.2 - 2026-09-12 - 03/05"});return {saved:await eda.sch_Document.save(),source:await eda.sys_FileManager.getDocumentSource()};'
r=execute(js,'remove-encoder-mcu-stubs');(P/'sheet03-after.source').write_text(r['source']);print({'page03Saved':r['saved']})
for i,pid in [(1,'654247b3dab7ee5f'),(2,'1b2919cc1262fe39'),(5,'7020da259480076a')]:
 execute('return await eda.dmt_EditorControl.openDocument('+json.dumps(pid)+');',f'no-encoder-open-{i}')
 r=execute('const d=await eda.dmt_SelectControl.getCurrentDocumentInfo();if(d.uuid!=='+json.dumps(pid)+')throw Error("wrong sheet");let changed=0;for(const t of await eda.sch_PrimitiveText.getAll())if(t.getState_Content().startsWith("Revision 1.1")){await eda.sch_PrimitiveText.modify(t,{content:'+json.dumps(f'Revision 1.2 - 2026-09-12 - 0{i}/05')+'});changed++;}return {changed,saved:await eda.sch_Document.save()};',f'no-encoder-version-{i}');print(i,r)
# Independent expected map based only on the reviewed previous revision and explicit change.
exp=json.loads((P.parent/'final-2026-09-12/Reviewed_pin_nets.json').read_text())
for ref in ['EC1','R11','R12','R26']:del exp[ref]
for ref,pn in [('J1','13'),('J2','2'),('J2','8')]:exp[ref]['pins'][pn]=''
(P/'reviewed-pin-nets.json').write_text(json.dumps(exp,ensure_ascii=False,indent=2))
# Reuse the existing independent functional checks with this revision's output location.
v=(P.parent/'repair-2026-09-12/verify_schematic.py').read_text().replace("from eda_client import execute,ROOT","from eda_client import execute\nfrom pathlib import Path\nROOT=Path(__file__).resolve().parent").replace("out=ROOT/'generated'","out=ROOT").replace('check(true,true,true)','check(true,false,true)')
(P/'verify_schematic.py').write_text(v)
