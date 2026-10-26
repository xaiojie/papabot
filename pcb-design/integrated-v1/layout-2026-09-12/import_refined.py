import sys,json
from pathlib import Path
P=Path(__file__).resolve().parent
sys.path.insert(0,str(P.parent/'repair-2026-09-12'));from eda_client import execute
print(execute('const d=await eda.dmt_SelectControl.getCurrentDocumentInfo();if(d.uuid!=="bc31667e02a33e5b")throw Error("PCB guard");return await eda.pcb_Document.importAutoRouteSesFile(new File(['+json.dumps((P/'routed-refined.ses').read_text())+'],"routed-refined.ses"));','import-refined-routes'))
r=execute('return {drc:await eda.pcb_Drc.check(true,false,true),lines:await eda.pcb_PrimitiveLine.getAll(),vias:await eda.pcb_PrimitiveVia.getAll(),source:await eda.sys_FileManager.getDocumentSource()};','check-refined-routes');(P/'after-ses.json').write_text(json.dumps(r,ensure_ascii=False,indent=2));print([(x['name'],x['count']) for x in r['drc']]);
for group in r['drc']:
 for sub in group['list']:print(sub['name'],[(x.get('objs'),x.get('obj1'),x.get('obj2')) for x in sub['list']])
