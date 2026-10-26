"""Embed font/image dependencies, save and reopen the distributable Blender file."""
import bpy, json, hashlib, bmesh
from pathlib import Path
OUT=Path(__file__).resolve().parents[1]
FILE=OUT/'DesktopAssistant-整机结构-A2.blend'
bpy.ops.wm.open_mainfile(filepath=str(FILE))
bpy.context.window.scene=bpy.data.scenes['10_A2_COMPLETE_ASSEMBLY']
bpy.ops.file.pack_all()
bpy.ops.wm.save_as_mainfile(filepath=str(FILE))
bpy.ops.wm.open_mainfile(filepath=str(FILE))
scene=bpy.data.scenes['10_A2_COMPLETE_ASSEMBLY'];bpy.context.window.scene=scene
manifest=json.loads((OUT/'reports/complete-manifest.json').read_text())
closed=[]
for r in manifest:
    o=scene.objects[r['name']];bm=bmesh.new();bm.from_mesh(o.data)
    closed.append(all(e.is_manifold for e in bm.edges));bm.free()
fonts=[{'name':f.name,'packed':bool(f.packed_file)} for f in bpy.data.fonts if f.filepath!='<builtin>']
images=[{'name':i.name,'packed':bool(i.packed_file)} for i in bpy.data.images if i.source=='FILE' and i.filepath]
assert all(closed) and len(closed)==32
assert all(f['packed'] for f in fonts) and all(i['packed'] for i in images)
report_path=OUT/'reports/final-artifact-reopen.json'
report=json.loads(report_path.read_text())
report.update(blend_sha256=hashlib.sha256(FILE.read_bytes()).hexdigest(),
              packed_file_reopened=True,all_closed=all(closed),fonts=fonts,images=images)
report_path.write_text(json.dumps(report,ensure_ascii=False,indent=2))
print('PACK_AND_REOPEN_DONE',len(closed),fonts,images,flush=True)
