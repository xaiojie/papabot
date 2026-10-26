"""Import the approved offline candidate through the official gateway.

Only adds missing candidate copper; never removes existing PCB work.
Exact geometry keys and a pad-placement guard make interrupted runs reviewable.
"""
import argparse
import hashlib
import json
from pathlib import Path

from eda_client import ROOT, execute

PCB_UUID = '641e84beea5fc9c6'
GUARD = ('const taskDoc = await eda.dmt_SelectControl.getCurrentDocumentInfo(); '
         f'if (taskDoc?.uuid !== {json.dumps(PCB_UUID)}) throw new Error("PCB1 guard mismatch"); ')
ENUMS = 'const EPCB_LayerId = {TOP:1,BOTTOM:2}; '


def dump(name, data):
    (ROOT / name).write_text(json.dumps(data, ensure_ascii=False, indent=2))


def line_key(p):
    ends = sorted([(round(p['startX'], 4), round(p['startY'], 4)),
                   (round(p['endX'], 4), round(p['endY'], 4))])
    return p['net'], p['layer'], round(p['lineWidth'], 4), tuple(ends)


def via_key(p):
    return (p['net'], round(p['x'], 4), round(p['y'], 4),
            round(p['diameter'], 4), round(p['holeDiameter'], 4))


def pad_signature(items):
    return sorted((c['component']['designator'], str(p['padNumber']), p['net'],
                   round(p['x'], 3), round(p['y'], 3), p['layer'],
                   tuple(p['pad']), p.get('rotation', 0))
                  for c in items for p in c['pads'])


def readback(label):
    data = execute(GUARD + 'const components=[]; '
                   'for (const c of await eda.pcb_PrimitiveComponent.getAll()) '
                   'components.push({component:c,pads:await c.getAllPins()}); '
                   'return {components,lines:await eda.pcb_PrimitiveLine.getAll(),'
                   'vias:await eda.pcb_PrimitiveVia.getAll(),'
                   'allPads:await eda.pcb_PrimitivePad.getAll()};', label)
    dump(label + '.json', data)
    return data


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('candidate', type=Path)
    args = parser.parse_args()
    candidate_bytes = args.candidate.read_bytes()
    candidate = json.loads(candidate_bytes)
    source_bytes = (ROOT / 'pcb-placed-pads.json').read_bytes()
    assert candidate['units'] == 'mil'
    assert candidate['source_sha256'] == hashlib.sha256(source_bytes).hexdigest()
    assert candidate['validation_summary']['all_nets_connected']
    assert candidate['validation_summary']['status'] == 'PASS_GEOMETRY'
    assert not candidate['unrouted']
    native = readback('routing-before')
    assert pad_signature(native['components']) == pad_signature(json.loads(source_bytes)), 'Pad placement changed'
    lines = []
    for t in candidate['traces']:
        assert t['layer'] in ('TOP', 'BOTTOM')
        for a, b in zip(t['points'], t['points'][1:]):
            if a != b:
                lines.append(dict(net=t['net'], layer={'TOP': 1, 'BOTTOM': 2}[t['layer']],
                                  startX=a[0], startY=a[1], endX=b[0], endY=b[1], lineWidth=t['width']))
    # Coincident segments within the same net are electrically redundant.
    lines = list({line_key(p): p for p in lines}.values())
    vias = [dict(net=v['net'], x=v['x'], y=v['y'], diameter=v['diameter'],
                 holeDiameter=v['drill']) for v in candidate['vias']]
    vias = list({via_key(p): p for p in vias}.values())
    existing_lines = {line_key(p) for p in native['lines'] if p['layer'] in (1, 2)}
    expected_lines = {line_key(p) for p in lines}
    assert not existing_lines - expected_lines, 'Unexpected pre-existing copper; inspect before proceeding'
    existing_vias = {via_key(p) for p in native['vias']}
    expected_vias = {via_key(p) for p in vias}
    assert not existing_vias - expected_vias, 'Unexpected pre-existing vias'
    pending_lines = [p for p in lines if line_key(p) not in existing_lines]
    pending_vias = [p for p in vias if via_key(p) not in existing_vias]
    dump('routing-import-plan.json', dict(candidate=str(args.candidate),
         candidate_sha256=hashlib.sha256(candidate_bytes).hexdigest(),
         line_count=len(lines), via_count=len(vias), lines=lines, vias=vias))
    print(f'Import plan: {len(pending_lines)} missing segments, {len(pending_vias)} missing vias', flush=True)
    for start in range(0, len(pending_lines), 40):
        chunk = pending_lines[start:start + 40]
        code = GUARD + ENUMS + 'const result=[]; for (const p of ' + json.dumps(chunk) + ') {'
        code += ('const line=await eda.pcb_PrimitiveLine.create(p.net,'
                 'p.layer===EPCB_LayerId.TOP?EPCB_LayerId.TOP:EPCB_LayerId.BOTTOM,'
                 'p.startX,p.startY,p.endX,p.endY,p.lineWidth,false); '
                 'if(!line) throw new Error("Line creation returned no primitive"); result.push(line); } return result;')
        result = execute(code, f'import-copper-{start:04d}')
        assert len(result) == len(chunk)
        print(f'Imported segments {start + len(chunk)}/{len(pending_lines)}', flush=True)
    for start in range(0, len(pending_vias), 20):
        chunk = pending_vias[start:start + 20]
        code = GUARD + 'const result=[]; for (const p of ' + json.dumps(chunk) + ') {'
        code += ('const via=await eda.pcb_PrimitiveVia.create(p.net,p.x,p.y,p.holeDiameter,p.diameter); '
                 'if(!via) throw new Error("Via creation returned no primitive"); result.push(via); } return result;')
        result = execute(code, f'import-vias-{start:04d}')
        assert len(result) == len(chunk)
    assert execute(GUARD + 'return await eda.pcb_Document.save();', 'save-routed-pcb')
    actual = readback('pcb-routed-readback')
    actual_lines = {line_key(p) for p in actual['lines'] if p['layer'] in (1, 2)}
    actual_vias = {via_key(p) for p in actual['vias']}
    report = dict(candidate_sha256=hashlib.sha256(candidate_bytes).hexdigest(),
                  expected_segments=len(lines), actual_segments=sum(p['layer'] in (1, 2) for p in actual['lines']),
                  expected_vias=len(vias), actual_vias=len(actual['vias']),
                  exact_lines_match=actual_lines == expected_lines,
                  exact_vias_match=actual_vias == expected_vias,
                  pads_unchanged=pad_signature(actual['components']) == pad_signature(native['components']))
    dump('routing-import-check.json', report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    assert report['exact_lines_match'] and report['exact_vias_match'] and report['pads_unchanged']


if __name__ == '__main__':
    main()
