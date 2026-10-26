import bpy, json, hashlib
from pathlib import Path
from mathutils import Vector
OUT=Path(__file__).resolve().parents[1]
SRC=OUT.parents[0]/'assembly-v1/desktop-assistant-assembly-v1.blend'
src_hash=hashlib.sha256(SRC.read_bytes()).hexdigest()
copy=OUT/'source/desktop-assistant-user-saved-v1.blend'
if not copy.exists(): copy.write_bytes(SRC.read_bytes())
bpy.ops.wm.open_mainfile(filepath=str(copy))
scene=bpy.context.scene
result={'source':str(SRC),'source_sha256':src_hash,'copy_sha256':hashlib.sha256(copy.read_bytes()).hexdigest(),'blender':bpy.app.version_string,'scene':scene.name,'saved_frame':scene.frame_current,'unit_scale':scene.unit_settings.scale_length,'objects':[]}
for o in scene.objects:
    box=[o.matrix_world@Vector(v) for v in o.bound_box] if o.type=='MESH' else []
    result['objects'].append({'name':o.name,'type':o.type,'category':o.get('category'),'hidden_render':o.hide_render,'location_mm':[round(v*1000,5) for v in o.matrix_world.translation], 'dimensions_mm':[round(v*1000,5) for v in o.dimensions], 'bbox_min_mm':[round(min(v[i] for v in box)*1000,5) for i in range(3)] if box else None, 'bbox_max_mm':[round(max(v[i] for v in box)*1000,5) for i in range(3)] if box else None,'vertices':len(o.data.vertices) if o.type=='MESH' else None,'properties':{k:str(o[k]) for k in o.keys()}})
(OUT/'reports/source-inventory.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
print(json.dumps({k:v for k,v in result.items() if k!='objects'},ensure_ascii=False))
for x in result['objects']:
    if x['type']=='MESH' and (x['name'].startswith(('P001','P005','P006','P007','E00','D001','D002','S_'))): print(json.dumps(x,ensure_ascii=False))
