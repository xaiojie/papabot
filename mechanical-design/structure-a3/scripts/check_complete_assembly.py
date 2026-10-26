import bpy,bmesh,json,math,hashlib,struct,itertools,sys
from pathlib import Path
from mathutils import Vector,Matrix
OUT=Path(__file__).resolve().parents[1];M=.001
bpy.ops.wm.open_mainfile(filepath=str(OUT/'DesktopAssistant-整机结构-A3.blend'))
scene=bpy.data.scenes['10_A3_COMPLETE_ASSEMBLY'];bpy.context.window.scene=scene;bpy.context.view_layer.update()
manifest=json.loads((OUT/'reports/complete-manifest.json').read_text())
parts=[bpy.data.objects[r['name']] for r in manifest]
refs=[o for o in scene.objects if o.type=='MESH' and o.name.startswith(('REF__','REF_SCREEN__D','REF_CURRENT__')) and not any(t in o.name for t in ['REF_PAD','STOCK','ANTENNA'])]
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
 bpy.data.objects.remove(x,do_unlink=True);bpy.data.objects.remove(y,do_unlink=True)
 return v
bb={o.name:bounds(o) for o in parts+refs}
conflicts=[];checked=0
for a,b in list(itertools.combinations(parts,2))+list(itertools.product(parts,refs)):
 al,ah=bb[a.name];bl,bh=bb[b.name]
 if not all(min(ah[i],bh[i])-max(al[i],bl[i])>.000025 for i in range(3)):continue
 v=volume_intersection(a,b);checked+=1
 if v>.05:
  rec={'a':a.name,'b':b.name,'volume_mm3':round(v,4)};conflicts.append(rec);print('CONFLICT',json.dumps(rec),flush=True)
report={'checked_scene':scene.name,'print_part_count':len(parts),'purchased_envelopes_checked':len(refs),'solid_intersection_pairs_checked':checked,'conflicts_over_0p05_mm3':conflicts,'physical_fit_tested':False,'limits':['Nominal purchased dimensions and reserved connector volumes are not received-part measurements.','Contact at shared mounting planes is allowed; report threshold 0.05mm3.','This static rest-pose pass does not validate strength or full range of motion.']}
(OUT/'reports/assembly-collision-check.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
print('COLLISION_DONE',checked,len(conflicts),flush=True)
# Read-back validation of editable meshes and source preservation.
reopen=[]
for o in parts:
 bm=bmesh.new();bm.from_mesh(o.data);reopen.append({'name':o.name,'nonmanifold_edges':sum(not e.is_manifold for e in bm.edges),'volume_mm3':bm.calc_volume()/(M**3)});bm.free()
(OUT/'reports/complete-reopen.json').write_text(json.dumps({'scene':scene.name,'parts':reopen,'part_count':len(parts),'all_closed':all(r['nonmanifold_edges']==0 for r in reopen)},indent=2))
if '--render' in sys.argv:
 scene.camera=bpy.data.objects['A3_COMPLETE_front_camera'];scene.render.filepath=str(OUT/'renders/A3-front.png');bpy.ops.render.render(write_still=True)
 scene.camera=bpy.data.objects['A3_COMPLETE_rear_camera'];scene.render.filepath=str(OUT/'renders/A3-rear.png');bpy.ops.render.render(write_still=True)
 for o in parts:
  if o['part_id'] in ['R01','R02']:o.hide_render=True
 scene.camera=bpy.data.objects['A3_COMPLETE_internal_camera'];scene.render.filepath=str(OUT/'renders/A3-internal.png');bpy.ops.render.render(write_still=True)
