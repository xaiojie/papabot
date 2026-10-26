import json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent.parent/'repair-2026-09-12'))
from eda_client import execute,ROOT
out=Path(__file__).resolve().parent
pos=json.load(open(out/'placement.json'))
changes={'Q2':[15,27,270],'Q1':[24,27,90],'C1':[32,19.3,180],'R1':[32,17,0],'C2':[32,24.1,180],'R2':[32,21.8,0],'C17':[84.5,40,0],'C18':[84.5,43.4,0],'C8':[22,56.3,180],'C5':[27,55.8,90],'J6':[13,70,0],'R16':[11.75,65.5,90],'R17':[14.75,65.5,90],'C6':[10,62,0],'D2':[35,71,0],'R7':[29,67.2,0]}
rows=[dict(ref=k,x=v[0]/.0254,y=-v[1]/.0254,r=v[2]) for k,v in changes.items()]
print(execute('const all=await eda.pcb_PrimitiveComponent.getAll();for(const p of '+json.dumps(rows)+'){const c=all.find(c=>c.getState_Designator()===p.ref);const a=c.toAsync();a.setState_X(p.x);a.setState_Y(p.y);a.setState_Rotation(p.r);await a.done();}return await eda.pcb_Document.save();','refine-component-spacing'))
pos.update(changes);(out/'placement.json').write_text(json.dumps(pos,indent=2))
# Apply the existing vendor 2 oz profile, preserving every check.
r=json.load(open(out/'rules-before.json'))['rules']['config']
for section,kind in [('Spacing','Safe Spacing'),('Physics','Track')]:
 for k,v in r[section][kind].items():v['isSetDefault']=k=='copperThickness2oz'
r['Physics']['Track']['copperThickness2oz']['form']['data']['1']['maxValue']=10
(out/'rules-2oz.json').write_text(json.dumps(r,ensure_ascii=False,indent=2))
print(execute('return await eda.pcb_Drc.overwriteCurrentRuleConfiguration('+json.dumps(r)+');','apply-2oz-rules'))
code='const EPCB_LayerId={TOP:1,BOTTOM:2};const RT={NO_COMPONENTS:2,NO_WIRES:5,NO_FILLS:6,NO_POURS:7};const out=[];for(const layer of [EPCB_LayerId.TOP,EPCB_LayerId.BOTTOM]){const p=eda.pcb_MathPolygon.createPolygon([56.5/.0254,0,"L",71.3/.0254,0,71.3/.0254,-10/.0254,56.5/.0254,-10/.0254,56.5/.0254,0]);out.push(await eda.pcb_PrimitiveRegion.create(layer,p,[RT.NO_COMPONENTS,RT.NO_WIRES,RT.NO_FILLS,RT.NO_POURS],"ESP32 antenna clearance",4,true));}return out;'
print('antenna regions',len(execute(code,'add-antenna-keepout')))
# Screw-head clearance is deliberately larger than the mechanical drill.
code='const EPCB_LayerId={TOP:1,BOTTOM:2};const RT={NO_COMPONENTS:2,NO_WIRES:5,NO_FILLS:6,NO_POURS:7};const out=[];for(const a of [[4,4],[106,4],[4,71],[106,71]])for(const layer of [EPCB_LayerId.TOP,EPCB_LayerId.BOTTOM]){const p=eda.pcb_MathPolygon.createPolygon(["CIRCLE",a[0]/.0254,-a[1]/.0254,2.8/.0254]);out.push(await eda.pcb_PrimitiveRegion.create(layer,p,[RT.NO_COMPONENTS,RT.NO_WIRES,RT.NO_FILLS,RT.NO_POURS],"M3 screw head clearance",4,true));}return out.length;'
print('screw regions',execute(code,'add-screw-keepout'))
print(execute('return await eda.pcb_Document.save();','save-clearance-refinement'))
