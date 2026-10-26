import json,sys
from eda_client import execute,ROOT
SCHEMATIC='6c93ab84d69093e6'
page_names={'01':'01_电池保护与均衡','02':'02_USB充电','03':'03_配电与主控','04':'04_显示音频与交互','05':'05_舵机控制'}
pp=ROOT/'generated/pages.json'
pages=json.load(open(pp)) if pp.exists() else {'01':'b8d9a582c4360871'}
for key in sys.argv[1:] or ['01','02','03','04','05']:
 if key not in pages:
  pages[key]=execute('return await eda.dmt_Schematic.createSchematicPage('+json.dumps(SCHEMATIC)+');','create-page-'+key)
  if not pages[key]:raise RuntimeError('Page creation failed')
  pp.write_text(json.dumps(pages,indent=2))
 pid=pages[key]
 execute('await eda.dmt_EditorControl.openDocument('+json.dumps(pid)+');return await eda.dmt_Schematic.modifySchematicPageName('+json.dumps(pid)+','+json.dumps(page_names[key])+');','open-page-'+key)
 source=(ROOT/'generated'/f'{key}.source').read_text();ls=source.splitlines();h,v=ls[0].split('||',1);v=json.loads(v[:-1]);v['uuid']=pid
 ls[0]=h+'||'+json.dumps(v)+'|';source='\n'.join(ls)+'\n'
 code='const d=await eda.dmt_SelectControl.getCurrentDocumentInfo();if(d.uuid!=='+json.dumps(pid)+')throw new Error("Wrong sheet");const ok=await eda.sys_FileManager.setDocumentSource('+json.dumps(source)+');if(!ok)throw new Error("Source rejected");return {ok,saved:await eda.sch_Document.save()};'
 print(key,execute(code,'apply-page-'+key),flush=True)
 pp.write_text(json.dumps(pages,indent=2))
