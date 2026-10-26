import sys,json
from pathlib import Path
P=Path(__file__).resolve().parent;sys.path.insert(0,str(P.parent/'repair-2026-09-12'));from eda_client import execute
plan=json.loads((P/'ground-heal-plan.json').read_text());old=json.loads((P.parent/'final-no-encoder-2026-09-12/PCB1_geometry.json').read_text())['fills']
guard='const d=await eda.dmt_SelectControl.getCurrentDocumentInfo();if(d.uuid!=="bc31667e02a33e5b")throw Error("wrong PCB");'
ids=[]
# Add all replacement regions first; only then delete superseded fill primitives.
for i,r in enumerate(plan['regions']):
 js=guard+'const EPCB_LayerId={TOP:1,BOTTOM:2};const EPCB_PrimitiveFillMode={SOLID:0};const r='+json.dumps(r)+';const p=eda.pcb_MathPolygon.createComplexPolygon(r.paths);const f=await eda.pcb_PrimitiveFill.create(r.layer===1?EPCB_LayerId.TOP:EPCB_LayerId.BOTTOM,p,"GND",EPCB_PrimitiveFillMode.SOLID,0,true);return f.getState_PrimitiveId();'
 ids.append(execute(js,'encoder-ground-heal-'+str(i)))
 (P/'ground-heal-new-ids.json').write_text(json.dumps(ids))
print(execute(guard+'return {deletedOld:await eda.pcb_PrimitiveFill.delete('+json.dumps([f['primitiveId']for f in old])+'),saved:await eda.pcb_Document.save()};','encoder-ground-heal-replace'))
