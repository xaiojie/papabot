import sys,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent.parent/'repair-2026-09-12'))
from eda_client import execute,ROOT
out=Path(__file__).resolve().parent
r=execute('const d=await eda.dmt_SelectControl.getCurrentDocumentInfo();if(d.uuid!=="bc31667e02a33e5b")throw Error("wrong PCB");const out=[];for(const c of await eda.pcb_PrimitiveComponent.getAll())out.push({component:c,pads:await eda.pcb_PrimitiveComponent.getAllPinsByPrimitiveId(c.getState_PrimitiveId())});return {geometry:out,source:await eda.sys_FileManager.getDocumentSource(),pads:await eda.pcb_PrimitivePad.getAll()};','snapshot-placed-board')
for k,v in r.items():(out/('placed-'+k+('.source' if k=='source' else '.json'))).write_text(v if isinstance(v,str) else json.dumps(v,ensure_ascii=False,indent=2))
print(execute('return await eda.dmt_EditorControl.zoomToAllPrimitives();','zoom-layout'))
r=execute('return await eda.pcb_Drc.check(true,false,true);','placement-drc');(out/'placement-drc.json').write_text(json.dumps(r,ensure_ascii=False,indent=2));print('DRC summary',json.dumps(r,ensure_ascii=False)[:2400])
