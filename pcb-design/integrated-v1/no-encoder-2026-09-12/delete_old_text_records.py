import sys,json
from pathlib import Path
P=Path(__file__).resolve().parent;sys.path.insert(0,str(P.parent/'repair-2026-09-12'));from eda_client import execute
pages=['654247b3dab7ee5f','1b2919cc1262fe39','8e03abe4b069eaeb','2f4bfc0bfa3d836a','7020da259480076a']
for i,pid in enumerate(pages,1):
 ts=json.loads((P/f'sheet0{i}-final-texts.json').read_text())['texts'];ids=[t['primitiveId']for t in ts if t['content'].startswith('Revision ')or t['primitiveId']in ['b4a88dda5011e7c0','ea551164942b4868','45371453969dcb1e']]
 execute('return await eda.dmt_EditorControl.openDocument('+json.dumps(pid)+');','tombstone-open-'+str(i))
 guard='const d=await eda.dmt_SelectControl.getCurrentDocumentInfo();if(d.uuid!=='+json.dumps(pid)+')throw Error("wrong sheet");'
 src=execute(guard+'return await eda.sys_FileManager.getDocumentSource();','tombstone-before-'+str(i));ticket=max(json.loads(l.split('||')[0]).get('ticket',0)for l in src.splitlines()if '||'in l)
 # Explicit deletion records from the official Storage 3.0 format, no electrical changes.
 patch=src+'\n'+'\n'.join(json.dumps({'type':'TEXT','id':pid,'ticket':ticket+j+1})+'||""'for j,pid in enumerate(ids))+'\n'
 (P/f'sheet0{i}-with-text-tombstones.source').write_text(patch)
 print(i,execute(guard+'return await eda.sys_FileManager.setDocumentSource('+json.dumps(patch)+');','tombstone-apply-'+str(i)),flush=True)
 print(execute(guard+'return await eda.sch_Document.save();','tombstone-save-'+str(i)),flush=True)
