"""Bounded RevB change against a captured native source, with audit records."""
import copy
import json
from pathlib import Path
from eda_client import execute, ROOT


def patch_existing():
    source = (ROOT / 'before/schematic.source').read_text()
    rows = [(json.loads(h), json.loads(b.rstrip('|')))
            for h, b in (line.split('||', 1) for line in source.splitlines())]
    wire = '6e71bf2a6c212fa4'
    port = '7ae4d2064f4b8878'
    changes = []
    for h, d in rows:
        old = copy.deepcopy(d)
        if h['type'] == 'ATTR':
            parent, key = d.get('parentId'), d.get('key')
            if parent in (wire, port) and key in ('NET', 'Name') and d.get('value') == '+5V_LOGIC':
                d['value'] = 'LCD_3V3'
            if parent == '8f4268105a083fba':
                if key in ('Name', 'Value'):
                    d['value'] = 'LCD_3V3_SPI'
                if key == 'Assembly note':
                    d['value'] = '3.3V ONLY: VCC and BLK use LCD_3V3. Stock EC11 and key remain on the original module; see J7.'
            if parent == '8f4268105a083fba-e33' and key == 'NO_CONNECT':
                d['value'] = 'no'
            if parent == '9cfaa876b030a1c2':
                if key in ('Name', 'Value'):
                    d['value'] = 'LCD_STOCK_CONTROLS'
                if key == 'Assembly note':
                    d['value'] = 'A/B/PUSH/K0 from original screen PCB at 3.3V. Keep original controls; match signal labels.'
            if parent in ('b88989ce5ce819e4', 'c506a9ca445803df', 'b8020d6d5c8dbd49', '031511184ff5ae23') and key == 'Assembly note':
                d['value'] = 'DNP by default: stock module already has 10k pull-ups to LCD_3V3. Optional footprint retained.'
        if h['type'] == 'TEXT':
            text_changes = {
                '5019dd82b9b7172e': 'DESKTOP ASSISTANT | Rev B | 3.3V display carrier',
                '205abd5a5bb2007a': 'JP1 / JP2 / JP3 initially OPEN. JP3 closed: MCU 3V3; open: J10 external 3V3. Never parallel regulator outputs.',
                'a5b15eb7fdadc7db': 'LCD VCC + BLK = 3.3V. Keep stock EC11/key. R4-R7 DNP. Power MCU/LCD together; avoid signal backfeed.',
            }
            if h['id'] in text_changes:
                d['value'] = text_changes[h['id']]
        if old != d:
            changes.append(dict(type=h['type'], id=h.get('id'), before=old, after=d))
    assert len(changes) >= 13, len(changes)
    modified = '\n'.join(json.dumps(h, separators=(',', ':')) + '||' +
                         json.dumps(d, ensure_ascii=False, separators=(',', ':')) + '|'
                         for h, d in rows) + '\n'
    (ROOT / 'schematic-modification-plan.json').write_text(json.dumps(changes, ensure_ascii=False, indent=2))
    (ROOT / 'schematic-modified.source').write_text(modified)
    guard = 'const d=await eda.dmt_SelectControl.getCurrentDocumentInfo();if(d.uuid!=="834bc1f5a1044766")throw new Error("SCH mismatch");'
    assert execute(guard + 'return await eda.sys_FileManager.setDocumentSource(' + json.dumps(modified) + ');', 'apply-screen-3v3-source')
    print('Applied source changes:', len(changes), flush=True)


def add_parts():
    specs = [
        dict(ref='JP3', dev='eab4a8150b6d4918927e38d645cd50f2', name='LCD_3V3_LINK_OPEN', x=800, y=595, rot=0,
             nets={'1': '+3V3', '2': 'LCD_3V3'}, note='Normally OPEN low-profile wire link. Close only after MCU LDO current/thermal checks; external J10 must be disconnected.'),
        dict(ref='J10', dev='eab4a8150b6d4918927e38d645cd50f2', name='LCD_EXT_3V3_IN', x=1060, y=435, rot=0,
             nets={'1': 'LCD_3V3', '2': 'GND'}, note='Regulated 3.3V ONLY. JP3 must be OPEN. Power MCU/LCD together. Never connect 5V or parallel regulator outputs.'),
        dict(ref='C5', dev='477a96a6592848738afbd710f8b39fc8', name='100nF 50V P5.08', x=1060, y=285, rot=90,
             nets={'1': 'LCD_3V3', '2': 'GND'}, note='LCD rail bypass. External regulator must include its specified bulk/output capacitors; module already includes local decoupling.'),
    ]
    code = 'const d=await eda.dmt_SelectControl.getCurrentDocumentInfo();if(d.uuid!=="834bc1f5a1044766")throw new Error("SCH mismatch");'
    code += 'const existing=await eda.sch_PrimitiveComponent.getAll();const result=[];'
    code += 'for(const s of ' + json.dumps(specs) + '){'
    code += 'if(existing.some(c=>c.getState_Designator()===s.ref))throw new Error("Part already exists: "+s.ref);'
    code += 'const c=await eda.sch_PrimitiveComponent.create({libraryUuid:"0819f05c4eef4c71ace90d822a990e87",uuid:s.dev},s.x,s.y,undefined,s.rot,false,true,true);if(!c)throw new Error("Create failed");'
    code += 'await eda.sch_PrimitiveComponent.modify(c,{designator:s.ref,name:s.name,uniqueId:"revb-"+s.ref,otherProperty:{"Value":s.name,"Assembly note":s.note,"Procurement":"2.54mm low-profile connection or existing 100nF P5.08 capacitor"}});'
    code += 'for(const p of await c.getAllPins()){const n=s.nets[p.getState_PinNumber()];const x=p.getState_X(),y=p.getState_Y(),a=p.getState_Rotation()*Math.PI/180;const ex=x+25*Math.cos(a),ey=y+25*Math.sin(a);if(!await eda.sch_PrimitiveWire.create([x,y,ex,ey],n))throw new Error("Wire failed");if(!await eda.sch_PrimitiveComponent.createNetPort("BI",n,ex,ey,p.getState_Rotation()))throw new Error("Port failed");}result.push({ref:s.ref,component:c,pins:await c.getAllPins()});}'
    code += 'if(!await eda.sch_PrimitiveWire.create([780,665,755,665],"LCD_3V3"))throw new Error("BLK wire failed");if(!await eda.sch_PrimitiveComponent.createNetPort("BI","LCD_3V3",755,665,180))throw new Error("BLK port failed");if(!await eda.sch_Document.save())throw new Error("Save failed");return result;'
    result = execute(code, 'add-lcd-power-selection')
    (ROOT / 'schematic-new-parts.json').write_text(json.dumps(result, ensure_ascii=False, indent=2))
    (ROOT / 'new-part-specs.json').write_text(json.dumps(specs, ensure_ascii=False, indent=2))
    print('Added:', [r['ref'] for r in result], flush=True)


if __name__ == '__main__':
    patch_existing()
    add_parts()
