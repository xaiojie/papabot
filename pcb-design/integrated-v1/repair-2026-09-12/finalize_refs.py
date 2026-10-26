import json
from eda_client import execute,ROOT
pages=json.load(open(ROOT/'generated/pages.json'));expected=json.load(open(ROOT/'generated/reviewed-pin-nets.json'))
for phase in ['temporary','final']:
 for pg,pid in sorted(pages.items()):
  execute('return await eda.dmt_EditorControl.openDocument('+json.dumps(pid)+');',f'activate-{phase}-{pg}')
  items=[dict(id=v['id'],ref=('REPAIR_'+k if phase=='temporary' else k),unique='int-'+k) for k,v in expected.items() if v['page']==pg]
  code='const d=await eda.dmt_SelectControl.getCurrentDocumentInfo();if(d.uuid!=='+json.dumps(pid)+')throw new Error("Wrong sheet");const out=[];for(const x of '+json.dumps(items)+'){const c=await eda.sch_PrimitiveComponent.modify(x.id,{designator:x.ref,uniqueId:x.unique});if(!c)throw new Error("Missing component "+x.id);out.push(c.getState_Designator());}return {refs:out,saved:await eda.sch_Document.save()};'
  print(phase,pg,execute(code,f'refs-{phase}-{pg}'),flush=True)
print(execute('const ps=(await eda.dmt_Schematic.getAllSchematicPagesInfo()).filter(p=>p.parentSchematicUuid==="6c93ab84d69093e6").sort((a,b)=>a.name.localeCompare(b.name));return await eda.dmt_Schematic.reorderSchematicPages("6c93ab84d69093e6",ps);','sort-five-pages'))
