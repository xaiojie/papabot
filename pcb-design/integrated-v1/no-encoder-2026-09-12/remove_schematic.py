import sys,json
from pathlib import Path
P=Path(__file__).resolve().parent
sys.path.insert(0,str(P.parent/'repair-2026-09-12'))
from eda_client import execute
old=json.loads((P/'sheet04-before.json').read_text())
refs={'EC1','R11','R12','R26'}
cs=[c['primitiveId'] for c in old['components'] if c.get('designator') in refs]
# Each wire in the former encoder block is a terminal stub (all endpoints audited).
ws=[w['primitiveId'] for w in old['wires'] if w['line'][0]>=970 and 285<=w['line'][1]<=545]
assert len(cs)==4 and len(ws)==13
plan={'components':cs,'wires':ws,'references':sorted(refs)}
(P/'schematic-deletion-plan.json').write_text(json.dumps(plan,indent=2))
guard='const d=await eda.dmt_SelectControl.getCurrentDocumentInfo();if(d.uuid!=="2f4bfc0bfa3d836a")throw Error("wrong page04");'
js=guard+'const removedWires=await eda.sch_PrimitiveWire.delete('+json.dumps(ws)+');const removedComponents=await eda.sch_PrimitiveComponent.delete('+json.dumps(cs)+');'
mods={'b4a88dda5011e7c0':'HS24S010B interface notes / 屏幕接口说明','ea551164942b4868':'All ESP32 and LCD signals are 3.3V. No on-board encoder or user buttons.','9d3fb7e48157aa87':'Revision 1.2 - 2026-09-12 - 04/05','45371453969dcb1e':'DesktopAssistant Integrated | Display and audio / 显示与音频'}
for k,v in mods.items():js+='await eda.sch_PrimitiveText.modify('+json.dumps(k)+','+json.dumps({'content':v})+');'
notes=[(545,'ST7789V2 - 240 x 320 - 4-wire SPI - 3.3V only'),(505,'CN1: 1 GND | 2 VCC | 3 SCL | 4 SDA | 5 RES'),(465,'CN1: 6 DC | 7 CS | 8 BLK | 9 FSO | 10 FCS'),(425,'BLK is a control input: held HIGH for backlight ON.'),(385,'FSO/FCS: optional font/flash; pins 9/10 are NC here.'),(345,'Pin table and mechanical CN1 agree; inset schematic differs.'),(305,'Check actual screen silk before wiring the XH-to-2.54mm cable.')]
for y,t in notes:js+=f'await eda.sch_PrimitiveText.create(830,{y},'+json.dumps(t)+',0,null,null,12);'
js+='return {removedWires,removedComponents,saved:await eda.sch_Document.save(),components:await eda.sch_PrimitiveComponent.getAll(),wires:await eda.sch_PrimitiveWire.getAll(),texts:await eda.sch_PrimitiveText.getAll()};'
r=execute(js,'remove-encoder-page04');(P/'sheet04-after.json').write_text(json.dumps(r,ensure_ascii=False,indent=2));print({k:r[k] for k in ['removedWires','removedComponents','saved']})
print(execute('return await eda.dmt_EditorControl.openDocument("8e03abe4b069eaeb");','no-encoder-open-page03'))
