import json
from eda_client import execute,ROOT
from build_schematic import ALL,ATTRS,OLDS,LIBS,TEMPLATES,attrs
pages=json.load(open(ROOT/'generated/pages.json'));expected=json.load(open(ROOT/'generated/reviewed-pin-nets.json'))
for pg,pid in sorted(pages.items()):
 items=[]
 for ref,v in expected.items():
  if v['page']!=pg:continue
  tmp=v['template']
  if tmp in TEMPLATES:props=TEMPLATES[tmp]['device']['otherProperty']
  else:
   dev=attrs(OLDS[tmp])['Device'];props=next(a['attributes'] for h,a in LIBS[dev] if h['type']=='META')
  meta={k:x for k,x in props.items() if k not in ['Symbol','Device','Footprint','3D Model','3D Model Transform','3D Model Title','Designator','Name','Add into BOM','Convert to PCB'] and isinstance(x,(str,int,float,bool))}
  items.append({'id':v['id'],'prop':{'name':props.get('Manufacturer Part') if tmp in ['HDR2','HDR3'] else props.get('Name') or props.get('Manufacturer Part'),'manufacturer':props.get('Manufacturer'),'manufacturerId':props.get('Manufacturer Part'),'supplier':props.get('Supplier'),'supplierId':props.get('Supplier Part'),'otherProperty':meta}})
 execute('return await eda.dmt_EditorControl.openDocument('+json.dumps(pid)+');','metadata-open-'+pg)
 print(pg,execute('const out=[];for(const x of '+json.dumps(items)+'){const c=await eda.sch_PrimitiveComponent.modify(x.id,x.prop);if(!c)throw new Error(x.id);out.push(c.getState_Designator());}return {count:out.length,saved:await eda.sch_Document.save()};','correct-metadata-'+pg),flush=True)
