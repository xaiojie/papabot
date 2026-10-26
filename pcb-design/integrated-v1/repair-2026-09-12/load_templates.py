import json
from eda_client import execute,ROOT
catalog={}
for filename in ['library-search.json','more-library.json','additional-library.json','final-library.json','extra-library.json']:
 for _,ls in json.load(open(ROOT/filename)).items():
  for d in ls: catalog[d['uuid']]=d
choices={'HY2120':'cae7209412d44bb6aaeeb1e50b6ac7ec','HY2213':'59efb5bbae9b49dbbedf1ac77ecf01d5','IP2326':'b7d58ec30f374c90a8082eb629f41681','XH2':'96395fd10e1147659737ad0dcda73174','XH3':'6934d76a8ee6438388dad49508dc5ccf','XT30':'b32777ef8cbb47c2aab830bd60bc67df','HDR3':'acd188b15a9c406bb9cb83c474d5327e','TERM2':'41ddecaaf01b4c1aa92ec4bfe22149b7','R255K':'3e16f8bbf31540d1863960ed64dad214','R100':'3140f4b435ed496db8557758bbe577c7','R82K':'fd0b712b8930485998a59734d41901df','R120K':'75ad0715d6df46c1aa879563ed1d5d2e','C22':'12477188fb4242298ab942da8fe1e223','R220':'b0b9aad34d05469eb60746619986555a','L2U2':'88005668dcea49f9b6524a4fcaabf85f','R050':'839f4eef35724e3a800bc4ef2fdbb750','HDR2':'eab4a8150b6d4918927e38d645cd50f2'}
path=ROOT/'templates.json'
result=json.load(open(path)) if path.exists() else {}
for key,uid in choices.items():
 if key in result:continue
 device=catalog[uid]
 js='const d=await eda.dmt_SelectControl.getCurrentDocumentInfo();if(d.uuid!=="b8d9a582c4360871")throw new Error("Wrong sheet");const c=await eda.sch_PrimitiveComponent.create('+json.dumps(device)+',2000,'+str(100+len(result)*150)+',undefined,0,false,true,true);if(!c)throw new Error("Create failed");await eda.sch_PrimitiveComponent.modify(c.getState_PrimitiveId(),{designator:'+json.dumps('TMP'+str(len(result)+1))+'});return {id:c.getState_PrimitiveId(),pins:await c.getAllPins()};'
 result[key]=execute(js,'template-'+key);result[key]['device']=device
 path.write_text(json.dumps(result,ensure_ascii=False,indent=2))
 print(key,[(p['pinNumber'],p['pinName']) for p in result[key]['pins']],flush=True)
s=execute('return await eda.sys_FileManager.getDocumentSource();','template-source')
(ROOT/'template.source').write_text(s)
