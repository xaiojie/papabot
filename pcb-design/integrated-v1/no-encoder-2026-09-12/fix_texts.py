import sys,json
from pathlib import Path
P=Path(__file__).resolve().parent;sys.path.insert(0,str(P.parent/'repair-2026-09-12'));from eda_client import execute
pages=['654247b3dab7ee5f','1b2919cc1262fe39','8e03abe4b069eaeb','2f4bfc0bfa3d836a','7020da259480076a']
mods={'b4a88dda5011e7c0':'HS24S010B interface notes / 屏幕接口说明','ea551164942b4868':'All ESP32 and LCD signals are 3.3V. No on-board encoder or user buttons.','45371453969dcb1e':'DesktopAssistant Integrated | Display and audio / 显示与音频'}
for i,pid in enumerate(pages,1):
 execute('return await eda.dmt_EditorControl.openDocument('+json.dumps(pid)+');','no-encoder-texts-open-'+str(i))
 js='const d=await eda.dmt_SelectControl.getCurrentDocumentInfo();if(d.uuid!=='+json.dumps(pid)+')throw Error("wrong sheet");const mods='+json.dumps(mods)+';for(const t of await eda.sch_PrimitiveText.getAll()){let value=mods[t.getState_PrimitiveId()];if(t.getState_Content().startsWith("Revision "))value='+json.dumps(f'Revision 1.2 - 2026-09-12 - 0{i}/05')+';if(value){const a=t.toAsync();a.setState_Content(value);await a.done();}}return {saved:await eda.sch_Document.save(),texts:await eda.sch_PrimitiveText.getAll()};'
 r=execute(js,'no-encoder-texts-apply-'+str(i));(P/f'sheet0{i}-final-texts.json').write_text(json.dumps(r,ensure_ascii=False,indent=2));print(i,[t['content']for t in r['texts']if t['content'].startswith('Revision')])
execute('return await eda.dmt_EditorControl.openDocument("bc31667e02a33e5b");','no-encoder-texts-open-pcb')
r=execute('const d=await eda.dmt_SelectControl.getCurrentDocumentInfo();if(d.uuid!=="bc31667e02a33e5b")throw Error("wrong PCB");const t=await eda.pcb_PrimitiveString.get("2ab80fa9d311f03c");const a=t.toAsync();a.setState_Text("Integrated V1.2");await a.done();return {saved:await eda.pcb_Document.save(),text:(await eda.pcb_PrimitiveString.get("2ab80fa9d311f03c")).getState_Text()};','no-encoder-pcb-version');print(r)
