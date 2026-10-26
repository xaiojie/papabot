import sys,json
from pathlib import Path
P=Path(__file__).resolve().parent
sys.path.insert(0,str(P.parent/'repair-2026-09-12'));from eda_client import execute
r=json.loads((P/'ground-fill-plan.json').read_text())
print(execute('const d=await eda.dmt_SelectControl.getCurrentDocumentInfo();if(d.uuid!=="bc31667e02a33e5b")throw Error("PCB guard");eda.sys_LoadingAndProgressBar.destroyLoading();eda.sys_LoadingAndProgressBar.destroyProgressBar();const p=await eda.pcb_PrimitivePour.getAll();return await eda.pcb_PrimitivePour.delete(p.map(x=>x.getState_PrimitiveId()));','replace-unbuilt-pours'))
ids=[]
for i,region in enumerate(r['regions']):
 s='const EPCB_LayerId={TOP:1,BOTTOM:2};const EPCB_PrimitiveFillMode={SOLID:0};const r='+json.dumps(region)+';const p=eda.pcb_MathPolygon.createComplexPolygon(r.paths);const f=await eda.pcb_PrimitiveFill.create(r.layer===1?EPCB_LayerId.TOP:EPCB_LayerId.BOTTOM,p,"GND",EPCB_PrimitiveFillMode.SOLID,0,true);return f.getState_PrimitiveId();'
 ids.append(execute(s,'ground-fill-'+str(i)))
 print('Created fill',i,flush=True)
(P/'ground-fill-ids.json').write_text(json.dumps(ids))
s='const data='+json.dumps(r['vias'])+';const ids=[];for(const v of data){const p=await eda.pcb_PrimitiveVia.create("GND",v.x/.0254,-v.y/.0254,v.drill/.0254,v.diameter/.0254,undefined,undefined,undefined,true);ids.push(p.getState_PrimitiveId());}return ids;'
(P/'ground-stitch-ids.json').write_text(json.dumps(execute(s,'ground-stitch-vias')))
d=execute('return {drc:await eda.pcb_Drc.check(true,false,true),pass:await eda.pcb_Drc.check(true,false,false),source:await eda.sys_FileManager.getDocumentSource()};','ground-fill-drc');(P/'ground-drc.json').write_text(json.dumps(d,ensure_ascii=False,indent=2));print('DRC',[(x['name'],x['count']) for x in d['drc']],d['pass'])
