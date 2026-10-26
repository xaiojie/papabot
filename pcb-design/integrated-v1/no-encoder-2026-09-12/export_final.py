"""Read current native PCB and export review artifacts without changing routing."""
import sys, json, hashlib, zipfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent/'repair-2026-09-12'))
from eda_client import execute
OUT=Path(__file__).resolve().parent.parent/'final-no-encoder-2026-09-12'
OUT.mkdir(exist_ok=True)
GUARD='const d=await eda.dmt_SelectControl.getCurrentDocumentInfo();if(d.uuid!=="bc31667e02a33e5b")throw Error("wrong PCB");'
def jsonfile(name, obj):
    (OUT/name).write_text(json.dumps(obj,ensure_ascii=False,indent=2))

if __name__=='__main__':
    mode=sys.argv[1] if len(sys.argv)>1 else 'snapshot'
    if mode=='snapshot':
        r=execute(GUARD+'const geometry=[];for(const c of await eda.pcb_PrimitiveComponent.getAll())geometry.push({component:c,pads:await eda.pcb_PrimitiveComponent.getAllPinsByPrimitiveId(c.getState_PrimitiveId())});return {geometry,source:await eda.sys_FileManager.getDocumentSource(),lines:await eda.pcb_PrimitiveLine.getAll(),vias:await eda.pcb_PrimitiveVia.getAll(),fills:await eda.pcb_PrimitiveFill.getAll(),pours:await eda.pcb_PrimitivePour.getAll(),attributes:await eda.pcb_PrimitiveAttribute.getAll(),strings:await eda.pcb_PrimitiveString.getAll()};','final-pcb-snapshot')
        (OUT/'PCB1.source').write_text(r.pop('source'))
        jsonfile('PCB1_geometry.json',r)
        print({k:len(v) for k,v in r.items()})
    elif mode=='drc':
        r=execute(GUARD+'return {drc:await eda.pcb_Drc.check(true,false,true),strict_pass:await eda.pcb_Drc.check(true,false,false),saved:await eda.pcb_Document.save()};','final-pcb-drc')
        jsonfile('PCB_DRC_final.json',r); print(r)
    elif mode in ['project','gerber']:
        api='eda.sys_FileManager.getProjectFile("DesktopAssistant_Integrated_final",undefined,"epro2")' if mode=='project' else 'eda.pcb_ManufactureData.getGerberFile("DesktopAssistant_Integrated_review")'
        r=execute(GUARD+'const f=await '+api+';return f?{name:f.name,bytes:Array.from(new Uint8Array(await f.arrayBuffer()))}:null;','final-export-'+mode)
        if not r:raise RuntimeError('Native export returned no file')
        file=OUT/('DesktopAssistant_Integrated_Gerber_review.zip' if mode=='gerber' else r['name']);file.write_bytes(bytes(r['bytes']))
        with zipfile.ZipFile(file) as z:
            assert z.testzip() is None
            listing=z.namelist()
        print({'path':str(file),'bytes':file.stat().st_size,'sha256':hashlib.sha256(file.read_bytes()).hexdigest(),'members':listing})
