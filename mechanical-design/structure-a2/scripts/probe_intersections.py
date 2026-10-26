import bpy,bmesh,json,math,hashlib,struct,itertools,sys
from pathlib import Path
from mathutils import Vector,Matrix
OUT=Path(__file__).resolve().parents[1];M=.001
bpy.ops.wm.open_mainfile(filepath=str(OUT/'DesktopAssistant-整机结构-A2.blend'))
scene=bpy.data.scenes['10_A2_COMPLETE_ASSEMBLY'];bpy.context.window.scene=scene;bpy.context.view_layer.update()
manifest=json.loads((OUT/'reports/complete-manifest.json').read_text())
parts=[bpy.data.objects[r['name']] for r in manifest]
refs=[o for o in scene.objects if o.type=='MESH' and (o.name.startswith('REF__') or o.name.startswith(('REF_SCREEN__D001','REF_SCREEN__D002','REF_CURRENT__REF_PCB','REF_CURRENT__REF_LCKFB','REF_CURRENT__REF_MCU','REF_CURRENT__REF_BATTERY'))) and not any(t in o.name for t in ['PAD','STOCK','SHAFT'])]
# Axis-aligned broad phase only; every reported conflict then uses a solid boolean volume.
def bounds(o):
 ps=[o.matrix_world@Vector(c) for c in o.bound_box]
 return Vector([min(v[i] for v in ps) for i in range(3)]),Vector([max(v[i] for v in ps) for i in range(3)])
def volume_intersection(a,b):
 def copy_mm(o):
  me=bpy.data.meshes.new_from_object(o.evaluated_get(bpy.context.evaluated_depsgraph_get()))
  me.transform(Matrix.Scale(1/M,4)@o.matrix_world)
  for v in me.vertices:v.co=Vector([round(q,5) for q in v.co])
  obj=bpy.data.objects.new('CHECK_TMP',me);scene.collection.objects.link(obj);return obj
 x,y=copy_mm(a),copy_mm(b)
 mod=x.modifiers.new('Solid intersection','BOOLEAN');mod.solver='EXACT';mod.operation='INTERSECT';mod.object=y
 bpy.context.view_layer.objects.active=x;bpy.ops.object.modifier_apply(modifier=mod.name)
 bm=bmesh.new();bm.from_mesh(x.data);v=abs(bm.calc_volume());bm.free()
 bounds_result=bounds(x)
 bpy.data.objects.remove(x,do_unlink=True);bpy.data.objects.remove(y,do_unlink=True)
 return {'volume_mm3':v, 'bbox_mm':[list(vv) for vv in bounds_result]}

for target in ['R04__display_support_A2','R05__reinforced_floor_and_battery_tray_A2','R09__charger_tray','R14__microphone_replaceable_tray','REF__S1A_BODY_AND_TERMINAL_RESERVATION']:
 print(target,volume_intersection(bpy.data.objects['R01__main_housing_A2'],bpy.data.objects[target]),flush=True)
