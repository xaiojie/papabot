import sys,json
from pathlib import Path
P=Path(__file__).resolve().parent
sys.path.insert(0,str(P.parent/'repair-2026-09-12'))
from eda_client import execute
r=execute('const d=await eda.dmt_SelectControl.getCurrentDocumentInfo();if(d.uuid!=="bc31667e02a33e5b")throw Error("wrong PCB");return await eda.sys_FileManager.getDocumentSource();','before-body-refine')
(P/'before-body-refine.source').write_text(r)
print(execute('const d=await eda.dmt_SelectControl.getCurrentDocumentInfo();if(d.uuid!=="bc31667e02a33e5b")throw Error("wrong PCB");const lines=(await eda.pcb_PrimitiveLine.getAll()).filter(l=>!l.getState_PrimitiveLock());await eda.pcb_PrimitiveLine.delete(lines.map(l=>l.getState_PrimitiveId()));const vs=(await eda.pcb_PrimitiveVia.getAll()).filter(v=>!v.getState_PrimitiveLock());await eda.pcb_PrimitiveVia.delete(vs.map(v=>v.getState_PrimitiveId()));for(const c of await eda.pcb_PrimitiveComponent.getAll()){const r=c.getState_Designator();if(r==="U1"||r==="JBAL"){const a=c.toAsync();a.setState_Y(-(r==="U1"?21:22.5)/.0254);await a.done();}}return {removedLines:lines.length,removedVias:vs.length};','refine-bodies'))
r=execute('const g=[];for(const c of await eda.pcb_PrimitiveComponent.getAll())g.push({component:c,pads:await eda.pcb_PrimitiveComponent.getAllPinsByPrimitiveId(c.getState_PrimitiveId())});const f=await eda.pcb_ManufactureData.getDsnFile("native-refined.dsn");return {geometry:g,dsn:await f.text(),drc:await eda.pcb_Drc.check(true,false,true)};','export-refined')
(P/'placed-geometry.json').write_text(json.dumps(r['geometry'],ensure_ascii=False,indent=2));(P/'native-critical.dsn').write_text(r['dsn']);(P/'body-refine-drc.json').write_text(json.dumps(r['drc'],ensure_ascii=False,indent=2));print([(d['name'],d['count']) for d in r['drc']])
p=json.loads((P/'placement.json').read_text());print(type(p))
