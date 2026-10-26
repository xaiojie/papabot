import sys,json
from pathlib import Path
P=Path(__file__).resolve().parent;sys.path.insert(0,str(P.parent/'repair-2026-09-12'));from eda_client import execute
b=json.loads((P/'pcb-before.json').read_text());refs={'EC1','R11','R12','R26'};nets={'ENC_A','ENC_B','ENC_SW_N'}
cs=[c['component']['primitiveId']for c in b['geometry']if c['component']['designator']in refs]
# Exact reference-audited branches: +3V3 fanout from J2.19 to all three pullups;
# GND loop serving EC1 only, between J1 ground and the existing ground near U7.
ps=[l for l in b['lines']if l['net']=='+3V3' and l['layer']==1 and max(-l['startY']*.0254,-l['endY']*.0254)>57]
gs=[l for l in b['lines']if l['net']=='GND' and l['layer']==1 and l['lineWidth']*.0254<.3 and max(-l['startY']*.0254,-l['endY']*.0254)>57 and max(l['startX']*.0254,l['endX']*.0254)>74]
ls=[l for l in b['lines']if l['net']in nets]+ps+gs
vs=[v for v in b['vias']if v['net']in nets]
plan={'components':cs,'references':sorted(refs),'signal_lines':len(ls)-len(ps)-len(gs),'power_branches':ps,'ground_branches':gs,'lines':[l['primitiveId']for l in ls],'vias':[v['primitiveId']for v in vs]}
assert len(cs)==4 and len(vs)==4 and len(ps)==13 and len(gs)==18,(len(ps),len(gs))
(P/'pcb-deletion-plan.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2))
guard='const d=await eda.dmt_SelectControl.getCurrentDocumentInfo();if(d.uuid!=="bc31667e02a33e5b")throw Error("wrong PCB");'
js=guard+'const deletedLines=await eda.pcb_PrimitiveLine.delete('+json.dumps(plan['lines'])+');const deletedVias=await eda.pcb_PrimitiveVia.delete('+json.dumps(plan['vias'])+');const deletedComponents=await eda.pcb_PrimitiveComponent.delete('+json.dumps(cs)+');'
for ref,nums in [('J1',['13']),('J2',['2','8'])]:
 c=next(c['component']for c in b['geometry']if c['component']['designator']==ref)
 js+='for(const p of await eda.pcb_PrimitiveComponent.getAllPinsByPrimitiveId('+json.dumps(c['primitiveId'])+'))if('+json.dumps(nums)+'.includes(p.getState_PadNumber())){const a=p.toAsync();a.setState_Net("");await a.done();}'
js+='await eda.pcb_PrimitiveString.modify("2ab80fa9d311f03c",{text:"Integrated V1.2"});return {deletedLines,deletedVias,deletedComponents,saved:await eda.pcb_Document.save()};'
print(execute(js,'remove-encoder-pcb'))
