import bpy,bmesh,json
from pathlib import Path
OUT=Path(__file__).resolve().parents[1]
bpy.ops.wm.open_mainfile(filepath=str(OUT/'DesktopAssistant-整机结构-A2.blend'))
for r in json.loads((OUT/'reports/complete-manifest.json').read_text()):
 o=bpy.data.objects[r['name']];bm=bmesh.new();bm.from_mesh(o.data)
 bad=[e for e in bm.edges if not e.is_manifold]
 if bad:print(r['id'],[(len(e.link_faces),[[round(v,4) for v in (o.matrix_world@a.co)*1000] for a in e.verts]) for e in bad][:15],flush=True)
 bm.free()
