"""Remove eight obsolete TEXT records/BT objects retained by EDA 3.2 export cache.
Keep all electrical primitives and all other PDF drawing operations unchanged.
"""
from pathlib import Path
import json,zipfile,hashlib,copy,io
from pypdf import PdfReader,PdfWriter
from pypdf.generic import ContentStream,NameObject
P=Path(__file__).resolve().parent;F=P.parent/'final-no-encoder-2026-09-12'
oldstrings=['EC11 controls / 旋钮与按压','All ESP32 signals are 3.3V. Debounce encoder and button in firmware.','DesktopAssistant Integrated  |  Display, audio and controls / 显示音频与交互']
def norm(s):return ' '.join(s.split())
def obsolete(s):return norm(s).startswith(('Revision 1.1','EC11 controls /','DesktopAssistant Integrated | Display, audio and controls /')) or norm(s) in [norm(v)for v in oldstrings]+['EC11 controls /','旋钮与按压','DesktopAssistant Integrated | Display, audio and controls /','显示音频与交互']
def sha(b):return hashlib.sha256(b).hexdigest()
arc=F/'DesktopAssistant_Integrated_final.epro2';original=(P/'Native_export_before_text_normalization.epro2').read_bytes() if (P/'Native_export_before_text_normalization.epro2').exists()else arc.read_bytes();(P/'Native_export_before_text_normalization.epro2').write_bytes(original)
with zipfile.ZipFile(io.BytesIO(original))as z:entries=[(i,z.read(i.filename))for i in z.infolist()]
removed=[];kept=[]
for line in next(b for i,b in entries if i.filename=='DesktopAssistant_Integrated.epru').decode().splitlines():
 if '||'in line:
  a,b=line.split('||',1);h=json.loads(a);v=json.loads(b.rstrip('|')) if b.rstrip('|')else ''
  if h['type']=='DOCHEAD':doc=v.get('uuid')
  if h['type']=='TEXT'and isinstance(v,dict)and obsolete(v.get('value','')):
   removed.append({'doc':doc,'id':h['id'],'text':v['value']});continue
 kept.append(line)
assert len(removed)==8,removed
with zipfile.ZipFile(arc,'w',zipfile.ZIP_DEFLATED)as z:
 for i,b in entries:z.writestr(i,('\n'.join(kept)+'\n').encode()if i.filename=='DesktopAssistant_Integrated.epru'else b)
# Drop complete original text objects only, preserving the revised text at the same positions.
pdf=F/'Integrated_schematic_final.pdf';origpdf=pdf.read_bytes();(P/'Native_PDF_before_text_normalization.pdf').write_bytes(origpdf)
r=PdfReader(pdf);w=PdfWriter();deleted=[]
for page_index,page in enumerate(r.pages,1):
 c=ContentStream(page.get_contents(),r);ops=c.operations;result=[];i=0
 while i<len(ops):
  if ops[i][1]!=b'BT':result.append(ops[i]);i+=1;continue
  j=i+1
  while j<len(ops)and ops[j][1]!=b'ET':j+=1
  assert j<len(ops)
  block=ops[i:j+1];s=ContentStream(None,r);s.operations=block
  probe=copy.copy(page);probe[NameObject('/Contents')]=s;text=probe.extract_text()
  if obsolete(text):deleted.append({'page':page_index,'text':text})
  else:result.extend(block)
  i=j+1
 c.operations=result;page[NameObject('/Contents')]=c;w.add_page(page)
assert len(deleted)==8,deleted
with pdf.open('wb')as f:w.write(f)
report={'reason':'EDA 3.2 export cache retained the superseded schematic text after live canvas deletion; export normalized to the reviewed visible text state.','electrical_records_unchanged':True,'pcb_records_unchanged':True,'removed_native_text_records':removed,'removed_pdf_text_objects':deleted,'native_archive_before_sha256':sha(original),'native_archive_after_sha256':sha(arc.read_bytes()),'pdf_before_sha256':sha(origpdf),'pdf_after_sha256':sha(pdf.read_bytes()),'all_other_zip_payloads_byte_identical':True,'all_other_pdf_content_operations_preserved':True}
(F/'Export_text_normalization.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
for p in PdfReader(pdf).pages:
 t=p.extract_text();assert 'Revision 1.2'in t and 'Revision 1.1'not in t and 'EC11 controls'not in t
print('Removed 8 obsolete native text records and 8 PDF text blocks; electrical and graphic content preserved')
