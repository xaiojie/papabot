"""Persist text-only removals through the documented source setter.
All non-TEXT records must remain byte-identical; electrical data is unchanged.
"""
import sys,json
from pathlib import Path
P=Path(__file__).resolve().parent;sys.path.insert(0,str(P.parent/'repair-2026-09-12'));from eda_client import execute
pages=['654247b3dab7ee5f','1b2919cc1262fe39','8e03abe4b069eaeb','2f4bfc0bfa3d836a','7020da259480076a']
for i,pid in enumerate(pages,1):
 execute('return await eda.dmt_EditorControl.openDocument('+json.dumps(pid)+');','source-texts-open-'+str(i))
 guard='const d=await eda.dmt_SelectControl.getCurrentDocumentInfo();if(d.uuid!=='+json.dumps(pid)+')throw Error("wrong sheet");'
 src=execute(guard+'return await eda.sys_FileManager.getDocumentSource();','source-texts-before-'+str(i));(P/f'sheet0{i}-text-clean-before.source').write_text(src)
 kept=[];removed=[]
 for line in src.splitlines():
  if '||'in line:
   a,b=line.split('||',1);h=json.loads(a);v=json.loads(b.rstrip('|')) if b.rstrip('|')else None
   if h.get('type')=='TEXT'and v:
    text=v.get('value','')
    if text.startswith('Revision 1.1')or text in ['EC11 controls / 旋钮与按压','All ESP32 signals are 3.3V. Debounce encoder and button in firmware.','DesktopAssistant Integrated  |  Display, audio and controls / 显示音频与交互']:
     removed.append(h['id']);continue
  kept.append(line)
 clean='\n'.join(kept)+'\n'
 assert len(removed) in [0,(4 if i==4 else 1)],(i,removed)
 assert 'Revision 1.2' in clean and 'Revision 1.1' not in clean
 (P/f'sheet0{i}-text-clean.source').write_text(clean)
 r=execute(guard+'const applied=await eda.sys_FileManager.setDocumentSource('+json.dumps(clean)+');return {applied,saved:await eda.sch_Document.save()};','source-texts-apply-'+str(i));print(i,r,flush=True)
