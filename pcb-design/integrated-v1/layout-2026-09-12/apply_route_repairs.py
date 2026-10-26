import sys,json
from pathlib import Path
P=Path(__file__).resolve().parent
sys.path.insert(0,str(P.parent/'repair-2026-09-12'));from eda_client import execute
r=json.loads((P/'routing-repairs.json').read_text())
code='const d=await eda.dmt_SelectControl.getCurrentDocumentInfo();if(d.uuid!=="bc31667e02a33e5b")throw Error("PCB guard");const EPCB_LayerId={TOP:1,BOTTOM:2};const r='+json.dumps(r)+';await eda.pcb_PrimitiveLine.delete(r.delete);const ids=[];for(const t of r.traces){for(let i=1;i<t.points.length;i++){const a=t.points[i-1],b=t.points[i];const l=await eda.pcb_PrimitiveLine.create(t.net,t.layer===1?EPCB_LayerId.TOP:EPCB_LayerId.BOTTOM,a[0]/.0254,-a[1]/.0254,b[0]/.0254,-b[1]/.0254,t.width/.0254,false);ids.push(l.getState_PrimitiveId());}}return ids;'
print(execute(code,'repair-slot-clearances'))
r=execute('return {drc:await eda.pcb_Drc.check(true,false,true),lines:await eda.pcb_PrimitiveLine.getAll(),vias:await eda.pcb_PrimitiveVia.getAll(),source:await eda.sys_FileManager.getDocumentSource()};','check-repaired-routing');(P/'after-ses.json').write_text(json.dumps(r,ensure_ascii=False,indent=2));print(json.dumps(r['drc'],ensure_ascii=False))
