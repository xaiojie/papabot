"""Apply only the reviewed RevB route delta and retain unrelated primitives."""
import json
from eda_client import ROOT, execute

GUARD = 'const d=await eda.dmt_SelectControl.getCurrentDocumentInfo();if(d.uuid!=="641e84beea5fc9c6")throw new Error("PCB mismatch");'


def readback(label):
    d = execute(GUARD + 'const components=[];for(const c of await eda.pcb_PrimitiveComponent.getAll())components.push({component:c,pads:await c.getAllPins()});return {components,lines:await eda.pcb_PrimitiveLine.getAll(),vias:await eda.pcb_PrimitiveVia.getAll(),allPads:await eda.pcb_PrimitivePad.getAll(),polylines:await eda.pcb_PrimitivePolyline.getAll(),source:await eda.sys_FileManager.getDocumentSource()};', label)
    (ROOT / (label + '.source')).write_text(d.pop('source'))
    (ROOT / (label + '.json')).write_text(json.dumps(d, ensure_ascii=False, indent=2))
    return d


def key(t):
    ends = sorted([(round(t['startX'], 4), round(t['startY'], 4)), (round(t['endX'], 4), round(t['endY'], 4))])
    return t['net'], t['layer'], round(t['lineWidth'], 4), tuple(ends)


if __name__ == '__main__':
    candidate = json.loads((ROOT / 'router/route-candidate.json').read_text())
    assert candidate['validation_summary']['all_nets_connected'] and candidate['validation_summary']['status'] == 'PASS_GEOMETRY'
    native = readback('before-route-apply')
    before = json.loads((ROOT / 'pcb-placed-readback.json').read_text())
    assert native['allPads'] == before['allPads'], 'Placement changed since validation'
    expected_preserved = {t['native_id'] for t in candidate['traces'] if 'native_id' in t}
    remove_ids = [t['primitiveId'] for t in before['lines'] if t['net'] in candidate['removed_original_nets']]
    actual_ids = {t['primitiveId'] for t in native['lines']}
    assert expected_preserved <= actual_ids
    assert actual_ids <= expected_preserved | set(remove_ids), 'Unexpected user copper; review required'
    pending = []
    for t in candidate['traces']:
        if 'native_id' in t:
            continue
        for a, b in zip(t['points'], t['points'][1:]):
            if a != b:
                pending.append(dict(net=t['net'], layer={'TOP':1,'BOTTOM':2}[t['layer']],
                    startX=a[0], startY=a[1], endX=b[0], endY=b[1], lineWidth=t['width']))
    pending = list({key(t):t for t in pending}.values())
    new_vias = [v for v in candidate['vias'] if 'native_id' not in v]
    plan = dict(remove_line_ids=remove_ids, preserved_lines=len(expected_preserved), add_lines=pending, add_vias=new_vias)
    (ROOT / 'routing-change-plan.json').write_text(json.dumps(plan, indent=2))
    print('Delta:', len(remove_ids), 'removed;', len(expected_preserved), 'preserved;', len(pending), 'new segments;', len(new_vias), 'new vias', flush=True)
    assert execute(GUARD + 'return await eda.pcb_PrimitiveLine.delete(' + json.dumps(remove_ids) + ');', 'remove-old-lcd-5v-route')
    for i in range(0, len(pending), 30):
        chunk = pending[i:i+30]
        code = GUARD + 'const EPCB_LayerId={TOP:1,BOTTOM:2};const ids=[];for(const t of ' + json.dumps(chunk) + '){'
        code += 'const v=await eda.pcb_PrimitiveLine.create(t.net,t.layer===EPCB_LayerId.TOP?EPCB_LayerId.TOP:EPCB_LayerId.BOTTOM,t.startX,t.startY,t.endX,t.endY,t.lineWidth,false);if(!v)throw new Error("Route creation failed");ids.push(v.getState_PrimitiveId());}return ids;'
        result = execute(code, f'add-revb-copper-{i:03d}')
        assert len(result) == len(chunk)
        print('Added segments', i + len(chunk), '/', len(pending), flush=True)
    for v in new_vias:
        assert execute(GUARD + 'return await eda.pcb_PrimitiveVia.create(' + ','.join(json.dumps(v[k]) for k in ('net','x','y','drill','diameter')) + ');', 'add-revb-via')
    assert execute(GUARD + 'return await eda.pcb_Document.save();', 'save-revb-routing')
    readback('pcb-routed-readback')
