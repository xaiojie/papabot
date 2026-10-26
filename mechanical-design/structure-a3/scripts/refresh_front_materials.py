"""Presentation-only fix: classify whole polygons, leaving verified print geometry intact."""
import bpy, json, hashlib, struct
from pathlib import Path
OUT=Path(__file__).resolve().parents[1];FILE=OUT/'DesktopAssistant-整机结构-A3.blend';M=.001
bpy.ops.wm.open_mainfile(filepath=str(FILE))
scene=bpy.data.scenes['10_A3_COMPLETE_ASSEMBLY'];bpy.context.window.scene=scene;bpy.context.view_layer.update()
parts=[scene.objects[r['name']] for r in json.loads((OUT/'reports/complete-manifest.json').read_text())]
def fingerprint():
 h=hashlib.sha256()
 for o in parts:
  h.update(o.name.encode());h.update(str(tuple(tuple(q) for q in o.matrix_world)).encode())
  for v in o.data.vertices:h.update(struct.pack('<3f',*v.co))
  for f in o.data.polygons:h.update(str(tuple(f.vertices)).encode())
 return h.hexdigest()
before=fingerprint();front=next(o for o in parts if o['part_id']=='R02')
counts={0:0,1:0,2:0}
for poly in front.data.polygons:
 coords=[front.matrix_world@front.data.vertices[i].co/M for i in poly.vertices]
 poly.material_index=0
 if all(abs(c.x)<37.1 and abs(c.z-68)<27.5 and -46.21<c.y<-25.8 for c in coords):poly.material_index=1
 if all(-46.19<c.y<-45.85 for c in coords):poly.material_index=2
 counts[poly.material_index]+=1
scene.view_settings.exposure=.2
floor=scene.objects['A3_COMPLETE_studio_floor'];floor.dimensions.x=10;floor.dimensions.y=10
after=fingerprint();assert after==before
bpy.ops.wm.save_as_mainfile(filepath=str(FILE))
(OUT/'reports/material-refresh-preservation.json').write_text(json.dumps({'before':before,'after':after,'print_geometry_unchanged':True,'front_material_face_counts':counts},indent=2))
print('MATERIAL_REFRESH_DONE',counts,flush=True)
