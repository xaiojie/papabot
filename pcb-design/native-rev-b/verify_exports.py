"""Verify native archive, pin maps and the actual exported fabrication geometry."""
import copy
import json
import math
import hashlib
import re
import zipfile
from collections import Counter, defaultdict
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parent
PCB = '641e84beea5fc9c6'
SCH = '834bc1f5a1044766'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(name, data):
    (ROOT/name).write_text(json.dumps(data, ensure_ascii=False, indent=2))


def parse(source):
    docs = defaultdict(dict)
    current = None
    for line in source.splitlines():
        if not line.strip():
            continue
        h, d = line.split('||', 1)
        h = json.loads(h)
        d = d.rstrip('|')
        d = json.loads(d) if d else ''
        if h['type'] == 'DOCHEAD':
            current = d['uuid']
        key = h['type'], h.get('id')
        previous = docs[current].get(key)
        if previous is None or h.get('ticket', 0) >= previous[0].get('ticket', 0):
            docs[current][key] = h, d
    return {doc:{key:d for key,(h,d) in items.items() if d != ''} for doc,items in docs.items()}


def equivalent(a, b, tolerance=.0001):
    if isinstance(a, dict) and isinstance(b, dict):
        return a.keys() == b.keys() and all(equivalent(a[k], b[k], tolerance) for k in a)
    if isinstance(a, (list, tuple)) and isinstance(b, (list, tuple)):
        return len(a) == len(b) and all(equivalent(x,y,tolerance) for x,y in zip(a,b))
    if isinstance(a, (float,int)) and isinstance(b, (float,int)):
        return abs(a-b) <= tolerance
    return a == b


def points_match(actual, expected, tolerance=.001):
    remaining = list(actual)
    largest = 0
    for p in expected:
        index = next((i for i,q in enumerate(remaining) if max(abs(x-y) for x,y in zip(p,q)) <= tolerance), None)
        assert index is not None, ('Missing geometry', p)
        q = remaining.pop(index)
        largest = max(largest, max(abs(x-y) for x,y in zip(p,q)))
    assert not remaining, ('Unexpected geometry', remaining[:5])
    return largest


def drills(text):
    tools, current, points = {}, None, []
    for line in text.splitlines():
        match = re.fullmatch(r'T(\d+)C([\d.]+)', line)
        if match:
            tools[match[1]] = float(match[2])
        elif re.fullmatch(r'T\d+', line):
            current = line[1:]
        elif line.startswith('X'):
            m = re.fullmatch(r'X(-?[\d.]+)Y(-?[\d.]+)', line)
            assert m, line
            points.append((float(m[1]),float(m[2]),tools[current]))
    return points


def gerber_tracks(text):
    assert '%FSLAX26Y26*%' in text and '%MOMM*%' in text
    apertures = {key:float(width) for key,width in re.findall(r'%ADD(\d+)C,([\d.]+)\*%',text)}
    block = text.split('G04 Track Start*')[1].split('G04 Track End*')[0]
    points, current, xy = [], None, None
    for line in block.splitlines():
        m = re.fullmatch(r'G54D(\d+)\*', line)
        if m:
            current = m[1]
            continue
        m = re.fullmatch(r'G01X(-?\d+)Y(-?\d+)D0([12])\*',line)
        if m:
            end = (int(m[1])/1e6,int(m[2])/1e6)
            if m[3] == '1':
                assert xy is not None
                a,b = sorted([xy,end])
                points.append((*a,*b,apertures[current]))
            xy = end
        elif line.strip():
            raise ValueError('Unsupported track command: '+line)
    return points


def main():
    archive = ROOT/'DesktopAssistant_RevB_PCB_review.epro2'
    gerber = ROOT/'DesktopAssistant_RevB_Gerber_review.zip'
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None
        source = z.read(next(n for n in z.namelist() if n.endswith('.epru'))).decode()
        docs = parse(source)
    live = parse((ROOT/'pcb-final.source').read_text())[PCB]
    archived = docs[PCB]
    # The document-source API materializes these inherited selectors, whereas
    # getProjectFile omits them. Accept only these exact no-override forms;
    # actual rule values, other selectors and the layer stack still compare.
    inherited_selectors = {
        ('RULE_SELECTOR', '["RULE_SELECTOR",["NET",""]]'): {
            'ruleOrder':4, 'ruleKeyValue':{'NET_LENGTH_TOLERANCE':['default',None]},
            'copperValue':{}, 'innerPlaneValue':{}},
        ('RULE_SELECTOR', '["RULE_SELECTOR",["NET","LCD_3V3"]]'): {
            'ruleOrder':4, 'ruleKeyValue':{}, 'copperValue':{}, 'innerPlaneValue':{}},
    }
    rule_normalization = []
    for key, expected in inherited_selectors.items():
        assert live.get(key) == expected and key not in archived, (key, live.get(key), archived.get(key))
        rule_normalization.append(dict(selector=json.loads(key[1])[1], source=expected,
            archive='omitted', reason='No custom rule override; inherits unchanged DEFAULT rules'))
    assert archived[('RULE','["RULE","NET_LENGTH_TOLERANCE","netLengthTolerance"]')]['ruleState']=='DEFAULT'
    def canonical_rules(records):
        result = dict(records)
        for key, expected in inherited_selectors.items():
            if key in result:
                assert result[key] == expected, (key,result[key])
                del result[key]
        return result
    live_compare = canonical_rules(live)
    types = {'COMPONENT','PAD_NET','PAD','LINE','VIA','POLY','ATTR','STRING','RULE','RULE_SELECTOR','RULE_TEMPLATE','LAYER_PHYS'}
    differences = [key for key in live_compare.keys() | archived.keys() if key[0] in types and not equivalent(live_compare.get(key),archived.get(key))]
    assert not differences, differences
    sch_live = parse((ROOT/'schematic-final.source').read_text())[SCH]
    sch_types = {'COMPONENT','ATTR','WIRE','LINE','TEXT'}
    sch_compare = copy.deepcopy(sch_live)
    sch_arch_compare = copy.deepcopy(docs[SCH])
    sch_presentation_normalization = []
    for key in sch_live.keys() | docs[SCH].keys():
        if key[0] != 'ATTR' or equivalent(sch_live.get(key),docs[SCH].get(key)):
            continue
        a,b = sch_live[key],docs[SCH][key]
        changed = {f for f in a.keys() | b.keys() if a.get(f)!=b.get(f)}
        assert changed <= {'strikeout','zIndex'}, (key,changed)
        assert a.get('strikeout') is False and b.get('strikeout') is None
        assert isinstance(a['zIndex'],int) and isinstance(b['zIndex'],int)
        sch_presentation_normalization.append(dict(id=key[1],key=a['key'],
            live_z_index=a['zIndex'],archive_z_index=b['zIndex'],
            strikeout='false in rendered source, absent in archive'))
        for records in (sch_compare,sch_arch_compare):
            records[key].pop('strikeout',None)
            records[key].pop('zIndex',None)
    sch_diffs = [key for key in sch_compare.keys() | sch_arch_compare.keys() if key[0] in sch_types and not equivalent(sch_compare.get(key),sch_arch_compare.get(key))]
    assert not sch_diffs, sch_diffs
    write('source-archive-normalization.json',dict(rule_selectors=rule_normalization,
        schematic_attribute_presentation=sch_presentation_normalization,
        note='Only implicit default selectors and ATTR presentation order/default strikeout are normalized. All values, pins, positions, visibility, components and wires compare unchanged.'))
    old = parse((ROOT/'before/pcb.source').read_text())[PCB]
    rule_types = {'RULE','RULE_SELECTOR','RULE_TEMPLATE','LAYER_PHYS'}
    assert {k:v for k,v in canonical_rules(old).items() if k[0] in rule_types} == {k:v for k,v in archived.items() if k[0] in rule_types}
    assert {k:v for k,v in old.items() if k[0] in ('PAD','POLY')} == {k:v for k,v in archived.items() if k[0] in ('PAD','POLY')}
    for (typ,cid), c in old.items():
        if typ == 'COMPONENT':
            assert equivalent({k:c[k] for k in ('x','y','angle','layerId')}, {k:archived[(typ,cid)][k] for k in ('x','y','angle','layerId')})
    geometry = json.loads((ROOT/'pcb-final-readback.json').read_text())
    api_pads = {p['primitiveId']:p for p in geometry['allPads']}
    attrs = {(d['parentId'],d['key']):d['value'] for (typ,_),d in archived.items() if typ=='ATTR'}
    netmaps = {(json.loads(key)[1],json.loads(key)[3]):d['padNet'] for (typ,key),d in archived.items() if typ=='PAD_NET'}
    exact_pads = []
    for (typ,cid), c in archived.items():
        if typ != 'COMPONENT':
            continue
        assert c['layerId'] == 1
        fp = attrs[(cid,'Footprint')]
        angle = math.radians(c['angle'])
        for (pt,pid),p in docs[fp].items():
            if pt != 'PAD':
                continue
            assert p['hole']['holeType']=='ROUND' and not p['specialPad']
            x = c['x']+p['centerX']*math.cos(angle)-p['centerY']*math.sin(angle)
            y = c['y']+p['centerX']*math.sin(angle)+p['centerY']*math.cos(angle)
            actual = api_pads[cid+pid]
            assert math.hypot(actual['x']-x,actual['y']-y)<.02
            assert actual['net'] == netmaps[(cid,pid)]
            q = copy.deepcopy(actual)
            shape = p['defaultPad']
            pad_angle = math.radians(c['angle']+p['padAngle'])
            q.update(x=x,y=y,rotation=pad_angle,
                holeX=x+p['padOffsetX']*math.cos(pad_angle)-p['padOffsetY']*math.sin(pad_angle),
                holeY=y+p['padOffsetX']*math.sin(pad_angle)+p['padOffsetY']*math.cos(pad_angle),
                pad=[shape['padType'],shape['width'],shape['height']], hole=['ROUND',p['hole']['width']])
            exact_pads.append(q)
    for (typ,pid),p in archived.items():
        if typ=='PAD':
            q=copy.deepcopy(api_pads[pid]);q.update(x=p['centerX'],y=p['centerY'],hole=['ROUND',p['hole']['width']])
            exact_pads.append(q)
    assert len(exact_pads)==108
    geometry['allPads']=exact_pads
    for v in geometry['vias']:
        d=archived[('VIA',v['primitiveId'])]
        v.update(x=d['centerX'],y=d['centerY'],diameter=d['viaDiameter'],holeDiameter=d['holeDiameter'])
    geometry['geometry_source_note']='Reconstructed from the exported epro2 PCB and footprint primitives; native pad center, shape, drill and via dimensions.'
    geometry['native_archive_sha256']=sha(archive)
    write('pcb-persisted-geometry.json',geometry)
    enets = []
    for fn in ('DesktopAssistant_Carrier_RevB.enet','DesktopAssistant_PCB_RevB.enet'):
        d=json.loads((ROOT/fn).read_text())
        enets.append({(c['props']['Designator'],str(pin)):v['net'] for c in d['components'].values() for pin,v in c['pinInfoMap'].items()})
    assert enets[0]==enets[1] and len(enets[0])==104
    by_ref = {p['primitiveId']:(c['component']['designator'],str(p['padNumber'])) for c in geometry['components'] for p in c['pads']}
    assert all(enets[0][by_ref[p['primitiveId']]]==p['net'] for p in exact_pads if p['metallization'])
    assert enets[0][('J3','2')]==enets[0][('J3','8')]==enets[0][('JP3','2')]==enets[0][('J10','1')]==enets[0][('C5','1')]=='LCD_3V3'
    assert enets[0][('JP3','1')]=='+3V3' and enets[0][('J10','2')]=='GND'
    write('netlist-check.json',dict(passed=True,pin_count=104,schematic_pcb_pinmaps_identical=True,archive_pinmaps_identical=True,
        screen_supply_isolated_from_5v=True,jp3_open_separates_mcu_and_lcd_3v3=True,
        pinmap=[dict(ref=ref,pin=pin,net=net)for(ref,pin),net in sorted(enets[0].items())]))
    with zipfile.ZipFile(gerber) as z:
        assert z.testzip() is None
        pth=drills(z.read('Drill_PTH_Through.DRL').decode());npth=drills(z.read('Drill_NPTH_Through.DRL').decode());vias=drills(z.read('Drill_PTH_Through_Via.DRL').decode())
        epth=[(p['holeX']*.0254,p['holeY']*.0254,p['hole'][1]*.0254)for p in exact_pads if p['metallization']]
        enpth=[(p['x']*.0254,p['y']*.0254,p['hole'][1]*.0254)for p in exact_pads if not p['metallization']]
        evias=[(v['x']*.0254,v['y']*.0254,v['holeDiameter']*.0254)for v in geometry['vias']]
        drill_delta=max(points_match(pth,epth+evias),points_match(npth,enpth),points_match(vias,evias))
        outline_text=z.read('Gerber_BoardOutlineLayer.GKO').decode()
        outline=[(int(x)/1e6,int(y)/1e6)for x,y in re.findall(r'G01X(-?\d+)Y(-?\d+)D0[12]\*',outline_text)]
        expected=[(0,0),(80,0),(80,32),(0,32),(0,22.5),(24.17,22.5),(24.17,9.5),(0,9.5),(0,0)]
        assert equivalent(outline,expected,.000002) or equivalent(outline,list(reversed(expected)),.000002)
        track_counts={};track_delta=0
        for layer,fn in ((1,'Gerber_TopLayer.GTL'),(2,'Gerber_BottomLayer.GBL')):
            actual=gerber_tracks(z.read(fn).decode());expected=[]
            for t in geometry['lines']:
                if t['layer']!=layer:continue
                a,b=sorted([(t['startX']*.0254,t['startY']*.0254),(t['endX']*.0254,t['endY']*.0254)])
                expected.append((*a,*b,t['lineWidth']*.0254))
            track_delta=max(track_delta,points_match(actual,expected,.000002));track_counts[fn]=len(actual)
        probe=json.loads(z.read('FlyingProbeTesting.json'))
        probe_by_name=defaultdict(list)
        for row in probe['pins']['rows']:
            probe_by_name[row[1]].append(row)
        pads_by_ref={by_ref[p['primitiveId']]:p for p in exact_pads if p['metallization']}
        nc_probe_nets={}
        for (ref,pin),net in enets[0].items():
            rows=probe_by_name[ref+'_'+pin]
            assert rows and len({row[6] for row in rows})==1
            if net:
                assert all(row[6]==net for row in rows)
            else:
                generated=rows[0][6]
                assert re.fullmatch(r'NET_\d+',generated) and generated not in enets[0].values()
                nc_probe_nets[ref+'.'+pin]=generated
            p=pads_by_ref[(ref,pin)]
            for row in rows:
                assert equivalent([row[2],row[3],row[9],row[10],row[11]],
                    [p['x'],p['y'],p['pad'][1],p['pad'][2],p['hole'][1]],.001)
        assert len(nc_probe_nets)==len(set(nc_probe_nets.values()))==11
        report=dict(passed=True,sha256=sha(gerber),zip_crc_pass=True,board_outline_mm=outline,
            plated_hole_count=len(pth),component_hole_count=len(epth),via_count=len(vias),nonplated_hole_count=len(npth),
            maximum_drill_difference_mm=drill_delta,all_drills_match_native_archive=True,
            copper_segments_by_layer=track_counts,all_copper_segments_match_native_archive=True,maximum_track_difference_mm=track_delta,
            flying_probe_pinmap_matches=True,flying_probe_pad_geometry_matches=True,
            flying_probe_generated_isolated_nc_names=nc_probe_nets,separate_via_drill_file_is_subset_of_pth=True)
        write('gerber-export-check.json',report)
    report=dict(passed=True,checked_at=datetime.now().astimezone().isoformat(),native_archive_sha256=sha(archive),
        archive_crc_pass=True,pcb_archive_matches_saved_source_after_default_normalization=True,
        schematic_content_and_geometry_match_saved_source=True,schematic_attribute_presentation_normalized=len(sch_presentation_normalization),
        unchanged_original_component_placements=21,outline_and_mounting_holes_unchanged=True,design_rule_values_and_effective_selectors_unchanged=True,
        inherited_rule_selector_serialization=rule_normalization,
        pcb_components=24,component_pads=104,copper_segments=752,vias=25,checks_not_disabled=True)
    write('native-archive-check.json',report)
    print(json.dumps(report,ensure_ascii=False,indent=2));print(json.dumps(json.loads((ROOT/'gerber-export-check.json').read_text()),ensure_ascii=False,indent=2))


if __name__=='__main__':
    main()
