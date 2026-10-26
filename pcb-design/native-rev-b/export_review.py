"""Export the saved RevB documents and collect fresh native checks."""
import json
from datetime import datetime
from eda_client import ROOT, execute
from apply_local_routing import readback


def write(name, data):
    (ROOT/name).write_text(json.dumps(data, ensure_ascii=False, indent=2))


def export_binary(code, label):
    r = execute(code + 'if(!f)throw new Error("Export failed");return {name:f.name,bytes:Array.from(new Uint8Array(await f.arrayBuffer()))};', label)
    if label == 'export-revb-gerber' and not r['name'].endswith('.zip'):
        r['name'] += '.zip'
    (ROOT/r['name']).write_bytes(bytes(r['bytes']))
    print(r['name'], len(r['bytes']), flush=True)


if __name__ == '__main__':
    for name, doc, domain in [('schematic','834bc1f5a1044766','sch'), ('pcb','641e84beea5fc9c6','pcb')]:
        execute('await eda.dmt_EditorControl.openDocument('+json.dumps(doc)+');return await eda.dmt_EditorControl.zoomToAllPrimitives();', 'prepare-'+name+'-view')
        r = execute('const d=await eda.dmt_SelectControl.getCurrentDocumentInfo();if(d.uuid!=='+json.dumps(doc)+')throw new Error("Document mismatch");const ESYS_NetlistType={JLCEDA_PRO:"JLCEDA"};const f=await eda.'+domain+'_ManufactureData.getNetlistFile("DesktopAssistant_'+name+'_RevB",ESYS_NetlistType.JLCEDA_PRO);return {source:await eda.sys_FileManager.getDocumentSource(),netlist:await f.text(),passed:await eda.'+domain+'_Drc.check(true,true,false),errors:await eda.'+domain+'_Drc.check(true,true,true)};', 'final-'+name+'-source-and-check')
        (ROOT/(name+'-final.source')).write_text(r.pop('source'))
        ename = 'DesktopAssistant_Carrier_RevB.enet' if name=='schematic' else 'DesktopAssistant_PCB_RevB.enet'
        (ROOT/ename).write_text(r.pop('netlist'))
        r['checked_at'] = datetime.now().astimezone().isoformat()
        write('native-'+name+'-drc.json', r)
        assert r['passed'] and not r['errors'], r
        img = execute('const f=await eda.dmt_EditorControl.getCurrentRenderedAreaImage();if(!f)throw new Error("Render unavailable");return {bytes:Array.from(new Uint8Array(await f.arrayBuffer()))};', 'capture-'+name+'-native-view')
        (ROOT/(name+'-native.png')).write_bytes(bytes(img['bytes']))
    readback('pcb-final-readback')
    export_binary('const f=await eda.sys_FileManager.getProjectFile("DesktopAssistant_RevB_PCB_review",undefined,"epro2");','export-revb-native-project')
    export_binary('const ESYS_Unit={MILLIMETER:"mm"};const f=await eda.pcb_ManufactureData.getGerberFile("DesktopAssistant_RevB_Gerber_review",false,ESYS_Unit.MILLIMETER,undefined,{metallicDrillingInformation:true,nonMetallicDrillingInformation:true,drillTable:true,flyingProbeTestingFile:true});','export-revb-gerber')
