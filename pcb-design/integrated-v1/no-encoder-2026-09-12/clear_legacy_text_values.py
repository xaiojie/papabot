import sys,json,zipfile
from pathlib import Path
P=Path(__file__).resolve().parent;sys.path.insert(0,str(P.parent/'repair-2026-09-12'));from eda_client import execute
sys.path.insert(0,str(P.parents[1]/'native-rev-b'));from verify_exports import parse
with zipfile.ZipFile(P/'NoEncoder_before_cache_refresh.epro2')as z:docs=parse(z.read('DesktopAssistant_Integrated.epru').decode())
for i,pid in enumerate(['654247b3dab7ee5f','1b2919cc1262fe39','8e03abe4b069eaeb','2f4bfc0bfa3d836a','7020da259480076a'],1):
 old=[(k,v)for k,v in docs[pid].items()if k[0]=='TEXT'and (v.get('value','').startswith('Revision 1.1')or k[1]in ['b4a88dda5011e7c0','ea551164942b4868','45371453969dcb1e'])]
 execute('return await eda.dmt_EditorControl.openDocument('+json.dumps(pid)+');','blank-legacy-open-'+str(i))
 guard='const d=await eda.dmt_SelectControl.getCurrentDocumentInfo();if(d.uuid!=='+json.dumps(pid)+')throw Error("wrong sheet");'
 src=execute(guard+'return await eda.sys_FileManager.getDocumentSource();','blank-legacy-before-'+str(i));ticket=max(json.loads(l.split('||')[0]).get('ticket',0)for l in src.splitlines()if '||'in l)
 patch=src+'\n'
 for j,((t,ident),v)in enumerate(old):
  v=dict(v);v['value']=' ';patch+=json.dumps({'type':'TEXT','id':ident,'ticket':ticket+j+1})+'||'+json.dumps(v,ensure_ascii=False)+'|\n'
 print(i,execute(guard+'return await eda.sys_FileManager.setDocumentSource('+json.dumps(patch)+');','blank-legacy-apply-'+str(i)),flush=True)
 print(execute(guard+'return await eda.sch_Document.save();','blank-legacy-save-'+str(i)),flush=True)
