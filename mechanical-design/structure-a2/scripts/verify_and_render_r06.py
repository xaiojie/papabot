import bpy,bmesh,json,hashlib,struct
from pathlib import Path
from mathutils import Vector
OUT=Path(__file__).resolve().parents[1];M=.001
file=OUT/'R06-PCB支撑架-A2.blend'
bpy.ops.wm.open_mainfile(filepath=str(file))
part=bpy.data.objects['R06__PCB_support_bridge_A2']
part_scene=bpy.data.scenes['01_R06_PART__PRINT_THIS_MESH'];fit=bpy.data.scenes['02_R06_FIT__PCB_BATTERY_FLOOR']
# Use separate stage planes so neither view hides the bottom of its model.
floor=bpy.data.objects['STUDIO floor']
for c in list(floor.users_collection):c.objects.unlink(floor)
c=bpy.data.collections.new('R06_PART_STAGE');part_scene.collection.children.link(c);c.objects.link(floor)
floor.location.z=33.6*M
fitfloor=floor.copy();fitfloor.data=floor.data.copy();fitfloor.name='STUDIO fit floor';fitfloor.location.z=30.8*M
c=bpy.data.collections.new('R06_FIT_STAGE');fit.collection.children.link(c);c.objects.link(fitfloor)
for s in [part_scene,fit]:
 bpy.context.window.scene=s
 for o in s.objects:
  if o.type in ['CAMERA','LIGHT'] or o.name.startswith('STUDIO'):o.hide_set(True)
 bpy.ops.object.select_all(action='DESELECT');part.select_set(True);bpy.context.view_layer.objects.active=part
# Saved original scene mesh/transform fingerprint rechecked after reopening.
source=bpy.data.scenes['01_ASSEMBLY_AND_DISASSEMBLY'];bpy.context.window.scene=source;bpy.context.view_layer.update()
h=hashlib.sha256()
for o in sorted(source.objects,key=lambda o:o.name):
 h.update(o.name.encode());h.update(o.type.encode());h.update(str(tuple(tuple(r) for r in o.matrix_world)).encode())
 if o.type=='MESH':
  for v in o.data.vertices:h.update(struct.pack('<3f',*v.co))
  for f in o.data.polygons:h.update(str(tuple(f.vertices)).encode())
p=json.loads((OUT/'reports/R06-preservation.json').read_text())
bm=bmesh.new();bm.from_mesh(part.data);nonmanifold=sum(not e.is_manifold for e in bm.edges);volume=bm.calc_volume();bm.free()
checks={'saved_file_reopened':True,'part_mesh_nonmanifold_edges':nonmanifold,'part_volume_mm3':volume/(M**3),
 'original_user_scene_preserved_after_reopen':h.hexdigest()==p['source_scene_before'],
 'input_a1_file_unchanged':hashlib.sha256((OUT.parent/'print-v2/desktop-assistant-structure-a1.blend').read_bytes()).hexdigest()==p['input_a1_sha256'],
 'original_v1_file_unchanged':hashlib.sha256((OUT.parent/'assembly-v1/desktop-assistant-assembly-v1.blend').read_bytes()).hexdigest()==p['original_v1_sha256'],
 'review_scenes':[part_scene.name,fit.name,'03_A2_ROBOT_CONTEXT__OTHER_PARTS_A1']}
checks['pass']=nonmanifold==0 and volume>0 and checks['original_user_scene_preserved_after_reopen'] and checks['input_a1_file_unchanged'] and checks['original_v1_file_unchanged']
(OUT/'reports/R06-reopen-verification.json').write_text(json.dumps(checks,ensure_ascii=False,indent=2));assert checks['pass'],checks
bpy.context.window.scene=part_scene
bpy.ops.wm.save_as_mainfile(filepath=str(file))
part_scene.camera=bpy.data.objects['R06 Part camera'];part_scene.render.filepath=str(OUT/'renders/R06-part.png');bpy.ops.render.render(write_still=True)
part_scene.camera=bpy.data.objects['R06 Underside camera'];floor.hide_render=True
part_scene.render.filepath=str(OUT/'renders/R06-underside.png');bpy.ops.render.render(write_still=True)
floor.hide_render=False;part_scene.camera=bpy.data.objects['R06 Part camera']
bpy.context.window.scene=fit;fit.render.filepath=str(OUT/'renders/R06-pcb-and-battery.png');bpy.ops.render.render(write_still=True)
print('REOPEN_CHECK',json.dumps(checks,ensure_ascii=False),flush=True)
