import sys,json
from pathlib import Path
P=Path(__file__).resolve().parent;sys.path.insert(0,str(P.parent/'repair-2026-09-12'));from eda_client import execute
pages=['654247b3dab7ee5f','1b2919cc1262fe39','8e03abe4b069eaeb','2f4bfc0bfa3d836a','7020da259480076a']
# SCH text update methods in EDA 3.2 alter API state but do not persist the source.
# Replace only the affected text primitives; preserve coordinates and styling.
for i,pid in enumerate(pages,1):
 r=json.loads((P/f'sheet0{i}-final-texts.json').read_text())['texts']
 ts=[t for t in r if t['content'].startswith('Revision ')or t['primitiveId']in ['b4a88dda5011e7c0','ea551164942b4868','45371453969dcb1e']]
 execute('return await eda.dmt_EditorControl.openDocument('+json.dumps(pid)+');','replace-texts-open-'+str(i))
 js='const d=await eda.dmt_SelectControl.getCurrentDocumentInfo();if(d.uuid!=='+json.dumps(pid)+')throw Error("wrong sheet");const ts='+json.dumps(ts)+';const ids=[];for(const t of ts){const n=await eda.sch_PrimitiveText.create(t.x,t.y,t.content,t.rotation,t.textColor,t.fontName,t.fontSize,t.bold,t.italic,t.underLine);ids.push(n.getState_PrimitiveId());}await eda.sch_PrimitiveText.delete(ts.map(t=>t.primitiveId));return {ids,saved:await eda.sch_Document.save(),source:await eda.sys_FileManager.getDocumentSource()};'
 result=execute(js,'replace-texts-save-'+str(i));(P/f'sheet0{i}-final.source').write_text(result.pop('source'));print(i,result)
