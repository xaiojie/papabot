import sys,json
from pathlib import Path
P=Path(__file__).resolve().parent
sys.path.insert(0,str(P.parent/'repair-2026-09-12'));from eda_client import execute
r=json.loads((P/'silkscreen-plan.json').read_text())
for k in range(0,len(r['attributes']),25):
 chunk=r['attributes'][k:k+25]
 print(execute('const d=await eda.dmt_SelectControl.getCurrentDocumentInfo();if(d.uuid!=="bc31667e02a33e5b")throw Error("PCB guard");for(const m of '+json.dumps(chunk)+'){if(!await eda.pcb_PrimitiveAttribute.modify(m.id,m.prop))throw Error(m.id)}return '+str(len(chunk))+';','align-silkscreen-'+str(k)))
js='const EPCB_LayerId={TOP_SILKSCREEN:3};const EPCB_PrimitiveStringAlignMode={CENTER:5};const ids=[];for(const p of '+json.dumps(r['legends'])+'){const s=await eda.pcb_PrimitiveString.create(EPCB_LayerId.TOP_SILKSCREEN,p.x/.0254,-p.y/.0254,p.text,"default",p.size/.0254,.15/.0254,EPCB_PrimitiveStringAlignMode.CENTER,p.rotation,false,0,false,true);ids.push(s.getState_PrimitiveId());}return ids;'
(P/'silkscreen-legend-ids.json').write_text(json.dumps(execute(js,'add-functional-silkscreen')))
print(execute('return {saved:await eda.pcb_Document.save(),drc:await eda.pcb_Drc.check(true,false,true),zoom:await eda.dmt_EditorControl.zoomToAllPrimitives()};','save-silkscreen-pcb'))
