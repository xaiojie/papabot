"""Check the silkscreen-only delta in the saved native archive and actual Gerbers."""
import collections
import dataclasses
import hashlib
import json
import sys
import zipfile
from datetime import datetime
from pathlib import Path
from gerbonara import GerberFile
from gerbonara.utils import MM
from shapely.geometry import box, Polygon
from shapely.ops import unary_union

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent / 'native-rev-b'))
from verify_exports import parse, equivalent, drills

PCB = '641e84beea5fc9c6'
def archive(path):
    with zipfile.ZipFile(path) as z:
        assert z.testzip() is None
        return parse(z.read(next(n for n in z.namelist() if n.endswith('.epru'))).decode())
def normalize(v):
    if isinstance(v, float): return round(v, 5)
    if isinstance(v, dict): return {k: normalize(x) for k, x in v.items()}
    if isinstance(v, (tuple, list)): return [normalize(x) for x in v]
    return v
def primitives(z, name):
    f = GerberFile.from_string(z.read(name).decode())
    return [q for ob in f.objects for q in ob.to_primitives(unit=MM)]
def key(q):
    return json.dumps([type(q).__name__, normalize(dataclasses.asdict(q))], sort_keys=True)

before = archive(ROOT / 'before/DesktopAssistant_before_Jay_PaPa.epro2')
after = archive(ROOT / 'DesktopAssistant_RevB_Jay_PaPa.epro2')
for doc, records in before.items():
    for k, value in records.items():
        if k[0] != 'DOCHEAD':
            assert equivalent(value, after[doc].get(k)), (doc, k)
added = {k:v for k,v in after[PCB].items() if k not in before[PCB]}
assert collections.Counter(k[0] for k in added) == {'STRING': 1, 'FILL': 6}
assert all(v['layerId'] == 3 for v in added.values())
assert next(v for k,v in added.items() if k[0]=='STRING')['text'] == 'Jay'
live = parse((ROOT/'pcb-final.source').read_text())[PCB]
assert all(equivalent(v, live[k]) for k,v in added.items())
assert json.loads((ROOT/'native-pcb-drc.json').read_text())['errors'] == []

old = zipfile.ZipFile(ROOT.parent/'native-rev-b/DesktopAssistant_RevB_Gerber_review.zip')
new = zipfile.ZipFile(ROOT/'DesktopAssistant_RevB_Jay_PaPa_Gerber.zip')
assert new.testzip() is None
layer_checks = {}
for name in new.namelist():
    if name.endswith(('.GTL','.GBL','.GTS','.GBS','.GKO','.GBO')):
        a,b = primitives(old,name), primitives(new,name)
        assert collections.Counter(map(key,a)) == collections.Counter(map(key,b)), name
        layer_checks[name] = {'unchanged':True, 'primitive_count':len(b)}
    elif name.endswith('.DRL'):
        a,b = drills(old.read(name).decode()), drills(new.read(name).decode())
        assert sorted(a)==sorted(b), name
        layer_checks[name] = {'unchanged':True, 'hole_count':len(b)}

counts=collections.Counter(map(key, primitives(old,'Gerber_TopSilkscreenLayer.GTO')))
new_silk=[]
for q in primitives(new,'Gerber_TopSilkscreenLayer.GTO'):
    k=key(q)
    if counts[k]: counts[k]-=1
    else: new_silk.append(q)
assert sum(counts.values())==0, 'Existing silk changed'
assert collections.Counter(type(q).__name__ for q in new_silk)=={'Line':29,'ArcPoly':6}
bounds=[]
for q in new_silk:
    (a,b),(c,d)=q.bounding_box()
    assert a>=8 and c<=22.3 and b>=27.5 and d<=31.2
    bounds.append(box(a,b,c,d))
label_boxes=unary_union(bounds)
mask_boxes=unary_union([box(*q.bounding_box()[0],*q.bounding_box()[1])
    for q in primitives(new,'Gerber_TopSolderMaskLayer.GTS')])
clearance=label_boxes.distance(mask_boxes)
assert clearance>0.5
chinese=unary_union([Polygon(q.outline) for q in new_silk if type(q).__name__=='ArcPoly'])
outline=json.loads((ROOT/'chinese-outline.json').read_text())
assert abs(chinese.area-outline['area_mm2'])<0.0001
result={
    'checked_at':datetime.now().astimezone().isoformat(), 'passed':True,
    'native_project_existing_records_unchanged':True, 'new_top_silkscreen_objects':7,
    'native_pcb_drc_errors':0, 'gerber_geometry_rounding_mm':0.00001,
    'gerber_unchanged_layers':layer_checks, 'existing_top_silk_unchanged':True,
    'new_top_silk_primitive_types':dict(collections.Counter(type(q).__name__ for q in new_silk)),
    'lettering_bbox_mm':list(label_boxes.bounds),
    'conservative_soldermask_opening_clearance_mm':clearance,
    'chinese_gerber_area_mm2':chinese.area, 'chinese_outline_area_matches':True,
    'lettering_only_no_circuit_or_mechanical_change':True,
    'fabrication_order_placed':False,
    'files':{n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in [
        'DesktopAssistant_RevB_Jay_PaPa.epro2','DesktopAssistant_RevB_Jay_PaPa_Gerber.zip']}
}
(ROOT/'verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
print(json.dumps(result,ensure_ascii=False,indent=2))
