"""Compare the user's exported manufacturing package with the checked V1.2 baseline.

The GUI uses 4.5 coordinates, while the API used 2.6. Normalize coordinate
encoding in memory only; never modify either source archive.
"""
from pathlib import Path
from datetime import datetime
import sys, re, json, zipfile, hashlib, shutil, math
from collections import defaultdict

ROOT = Path(__file__).resolve().parent
BASE = ROOT.parent / 'final-no-encoder-2026-09-12'
NEW = Path('/Users/jay/Downloads/Gerber_PCB1_2026-09-13.zip')
sys.path.insert(0, str(ROOT.parent / 'layout-2026-09-12'))
from gerber_review import read
from shapely.geometry import Point, LineString
from shapely import union_all
sys.path.insert(0, str(ROOT.parents[1] / 'native-rev-b'))
from verify_exports import points_match, gerber_tracks
from PIL import Image, ImageDraw

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def package(p):
    with zipfile.ZipFile(p) as z:
        assert z.testzip() is None
        return {Path(n).name: z.read(n) for n in z.namelist() if not n.endswith('/')}

def normalized(data):
    text = data.decode()
    if '%FSLAX26Y26*%' in text:
        return text
    assert '%FSLAX45Y45*%' in text
    lines = []
    for line in text.splitlines():
        if re.match(r'G0[123]X', line):
            line = re.sub(r'([XYIJ])(-?\d+)', lambda m: m[1] + str(int(m[2])*10), line)
        lines.append(line.replace('%FSLAX45Y45*%', '%FSLAX26Y26*%'))
    return '\n'.join(lines)

def drill(data):
    tools, cur, holes, slots = {}, None, [], []
    text = data.decode()
    assert 'METRIC' in text
    for line in text.splitlines():
        m = re.fullmatch(r'T(\d+)C([\d.]+)', line)
        if m:
            tools[m[1]] = float(m[2]); continue
        if re.fullmatch(r'T\d+', line):
            cur = line[1:]; continue
        if line.startswith('X'):
            vals = list(map(float, re.findall(r'[XY](-?[\d.]+)', line)))
            if 'G85' in line:
                a, b = sorted([tuple(vals[:2]), tuple(vals[2:])])
                slots.append((*a, *b, tools[cur]))
            else:
                holes.append((*vals, tools[cur]))
    return holes, slots

old = package(BASE / 'DesktopAssistant_Integrated_Gerber_review.zip')
new = package(NEW)
report = {
    'checked_at': datetime.now().astimezone().isoformat(),
    'user_archive': str(NEW), 'user_sha256': sha(NEW),
    'baseline_sha256': sha(BASE / 'DesktopAssistant_Integrated_Gerber_review.zip'),
    'crc_pass': True, 'coordinate_formats': {'baseline': '2.6 mm', 'user': '4.5 mm'},
    'geometric_tolerance_mm': 0.00003,
    'additional_output_files': sorted(new.keys() - old.keys()),
    'layers': {}, 'drills': {},
}
for name in ['Drill_PTH_Through.DRL', 'Drill_NPTH_Through.DRL', 'Drill_PTH_Through_Via.DRL']:
    oh, os = drill(old[name]); nh, ns = drill(new[name])
    remaining = list(nh)
    local_differences = []
    d = 0
    special_positions = [(72.78116,-33.85058),(55.00116,-5.91058),(55.00116,-21.15058)]
    for hole in oh:
        tolerance = .003 if any(max(abs(hole[i]-xy[i]) for i in (0,1)) < .00001 for xy in special_positions) else .00003
        index = next((i for i,q in enumerate(remaining) if max(abs(hole[j]-q[j]) for j in (0,1)) <= tolerance and abs(hole[2]-q[2])<=.00003),None)
        assert index is not None, ('Unexpected drill difference',name,hole)
        current = remaining.pop(index)
        delta = max(abs(x-y) for x,y in zip(hole,current))
        d = max(d,delta)
        if delta>.00003:
            local_differences.append({'baseline':hole,'user':current,'diameter_unchanged':hole[2]==current[2]})
    assert not remaining
    d = max(d,points_match(ns,os,.00003))
    report['drills'][name] = {'round_holes':len(nh), 'slots':len(ns), 'max_delta_mm':d, 'matches':True,
        'three_NC_pad_export_position_differences':local_differences,
        'position_note':'Only the three previously corrected NC connector pads may differ by at most 0.003 mm in position; all diameters checked separately within 0.00003 mm.'}

graphs = {}
for name in ['Gerber_BoardOutlineLayer.GKO', 'Gerber_TopLayer.GTL', 'Gerber_BottomLayer.GBL',
             'Gerber_TopSolderMaskLayer.GTS', 'Gerber_BottomSolderMaskLayer.GBS',
             'Gerber_TopPasteMaskLayer.GTP', 'Gerber_BottomSilkscreenLayer.GBO',
             'Gerber_TopSilkscreenLayer.GTO']:
    a, ar = read(normalized(old[name])); b, br = read(normalized(new[name]))
    delta = {'old_area_mm2':a.area, 'new_area_mm2':b.area,
             'removed_beyond_rounding_mm2':a.difference(b.buffer(.00003)).area,
             'added_beyond_rounding_mm2':b.difference(a.buffer(.00003)).area,
             'raw_symmetric_difference_mm2':a.symmetric_difference(b).area}
    delta['matches_within_rounding'] = max(delta['removed_beyond_rounding_mm2'],delta['added_beyond_rounding_mm2']) < 0.000001
    if name in ['Gerber_TopLayer.GTL','Gerber_BottomLayer.GBL','Gerber_TopSolderMaskLayer.GTS','Gerber_BottomSolderMaskLayer.GBS']:
        # The API export kept small numeric overrides for the same three NC pads;
        # the GUI uses their nominal geometry. Limit this allowance to these pads.
        zone = union_all([Point(x,y).buffer(1.02) for x,y in [(72.78,-33.85),(55,-5.91),(55,-21.15)]])
        removed = a.difference(b.buffer(.00003))
        added = b.difference(a.buffer(.00003))
        delta['differences_outside_three_NC_pads_mm2'] = removed.difference(zone).area + added.difference(zone).area
        delta['three_NC_pad_boundary_difference_exceeding_0_003mm_mm2'] = a.intersection(zone).difference(b.buffer(.003)).area + b.intersection(zone).difference(a.buffer(.003)).area
        delta['matches_with_documented_export_numeric_differences'] = max(delta['differences_outside_three_NC_pads_mm2'],delta['three_NC_pad_boundary_difference_exceeding_0_003mm_mm2']) < .000001
    else:
        delta['matches_with_documented_export_numeric_differences'] = delta['matches_within_rounding']
    if name in ['Gerber_TopLayer.GTL','Gerber_BottomLayer.GBL']:
        aa, bb = gerber_tracks(normalized(old[name])), gerber_tracks(normalized(new[name]))
        delta['old_segments'] = len(aa); delta['new_segments'] = len(bb)
        delta['track_max_delta_mm'] = points_match(bb, aa, .00003)
        delta['fill_removed_beyond_rounding_mm2'] = ar.difference(br.buffer(.00003)).area
        delta['fill_added_beyond_rounding_mm2'] = br.difference(ar.buffer(.00003)).area
    report['layers'][name] = delta
    graphs[name] = b
    print(name, delta['matches_within_rounding'], flush=True)

probe0 = json.loads(old['FlyingProbeTesting.json'])
probe1 = json.loads(new['FlyingProbeTesting.json'])
netlist = json.loads((BASE/'Schematic_netlist.json').read_text())
expected = {c['props']['Designator']+'_'+str(pn):v['net'] for c in netlist['components'].values() for pn,v in c['pinInfoMap'].items()}
by = defaultdict(list)
for row in probe1['pins']['rows']:
    by[row[1]].append(row)
assert set(expected).issubset(by)
assert set(by) == {r[1] for r in probe0['pins']['rows']}
nc = []
for name, net in expected.items():
    rows = by[name]
    if net:
        assert all(r[6] == net for r in rows), (name,net)
    else:
        nets = {r[6] for r in rows}; assert len(nets)==1
        nc.append(next(iter(nets)))
assert len(nc) == len(set(nc)) == 48
assert not set(nc).intersection(n for n in expected.values() if n)
positions0 = sorted((r[1], *r[2:4], *r[8:]) for r in probe0['pins']['rows'])
positions1 = sorted((r[1], *r[2:4], *r[8:]) for r in probe1['pins']['rows'])
assert len(positions0)==len(positions1)
max_pin_delta = 0
for a,b in zip(positions0,positions1):
    assert len(a)==len(b)
    for x,y in zip(a,b):
        if isinstance(x,(int,float)) and isinstance(y,(int,float)):
            max_pin_delta = max(max_pin_delta,abs(x-y)*.0254)
            tolerance = .003 if a[0] in ['J1_13','J2_2','J2_8'] else .00003
            assert abs(x-y)*.0254 < tolerance,(a[0],x,y)
        else:
            assert x==y,(a,b)
report['pinmap'] = {'components':len(netlist['components']), 'pins':len(expected), 'nets':len(set(expected.values())-{''}), 'nc':len(nc), 'matches':True, 'pad_geometry_matches':True, 'max_pad_delta_mm':max_pin_delta}
report['extra_synthetic_probe_points'] = len(set(by)-set(expected))
report['only_top_silkscreen_differs_after_documented_numeric_normalization'] = all(v['matches_with_documented_export_numeric_differences'] for k,v in report['layers'].items() if k!='Gerber_TopSilkscreenLayer.GTO') and not report['layers']['Gerber_TopSilkscreenLayer.GTO']['matches_within_rounding']

W,H,S = 1540,1050,14
def paint(img,g,color):
    if g.is_empty: return
    if g.geom_type != 'Polygon':
        for child in g.geoms: paint(img,child,color)
        return
    mask = Image.new('L',(W,H)); d=ImageDraw.Draw(mask)
    coords=lambda seq:[(x*S,-y*S) for x,y in seq]
    d.polygon(coords(g.exterior.coords),fill=255)
    for hole in g.interiors: d.polygon(coords(hole.coords),fill=0)
    img.paste(color,(0,0),mask)
img=Image.new('RGB',(W,H),'#092039')
copper=graphs['Gerber_TopLayer.GTL']
paint(img,copper,'#0b527e')
paint(img,graphs['Gerber_TopSolderMaskLayer.GTS'].intersection(copper),'#dec691')
paint(img,graphs['Gerber_TopSilkscreenLayer.GTO'],'#eef5f7')
holes,slots=drill(new['Drill_PTH_Through.DRL'])
npth,_=drill(new['Drill_NPTH_Through.DRL'])
for x,y,d in holes+npth: paint(img,Point(x,y).buffer(d/2),'#101820')
for x,y,xx,yy,d in slots: paint(img,LineString([(x,y),(xx,yy)]).buffer(d/2),'#101820')
img.save(ROOT/'User_latest_Gerber_Top.png')
shutil.copy2(NEW, ROOT/NEW.name)
(ROOT/'Manufacturing_comparison.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
print(json.dumps(report,ensure_ascii=False,indent=2))
