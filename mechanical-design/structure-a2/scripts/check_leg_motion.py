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
 bpy.data.objects.remove(x,do_unlink=True);bpy.data.objects.remove(y,do_unlink=True)
 return v

def descendant(o,j):
 p=o.parent
 while p:
  if p==j:return True
  p=p.parent
 return False
results=[];total_pairs=0
all_fixed_candidates=parts+refs
for ident in ['FL','FR','RL','RR']:
 h=bpy.data.objects['JNT_'+ident+'_HIP_X'];k=bpy.data.objects['JNT_'+ident+'_KNEE_X']
 moving=[o for o in scene.objects if o.type=='MESH' and descendant(o,h) and (o in parts or any(t in o.name for t in ['KNEE_CASE','KNEE_FLANGE','KNEE_BOSS']))]
 fixed=[o for o in all_fixed_candidates if o not in moving and not descendant(o,h)]
 for ha in [-15,0,15]:
  for ka in [-20,0,20]:
   if ha==0 and ka==0:continue
   h.rotation_euler.x=math.radians(ha);k.rotation_euler.x=math.radians(ka);bpy.context.view_layer.update()
   failures=[];bboxes={o.name:bounds(o) for o in moving+fixed}
   for a,b in itertools.product(moving,fixed):
    al,ah=bboxes[a.name];bl,bh=bboxes[b.name]
    if not all(min(ah[i],bh[i])-max(al[i],bl[i])>.00005 for i in range(3)):continue
    v=volume_intersection(a,b);total_pairs+=1
    if v>.1:failures.append({'a':a.name,'b':b.name,'volume_mm3':round(v,4)})
   results.append({'leg':ident,'hip_deg':ha,'knee_deg':ka,'conflicts':failures})
   if failures:print('POSE_CONFLICT',ident,ha,ka,failures,flush=True)
 h.rotation_euler.x=0;k.rotation_euler.x=0;bpy.context.view_layer.update()
report={'sampled_poses':len(results),'exact_intersection_pairs_checked':total_pairs,'sampled_pose_checks_pass':not any(r['conflicts'] for r in results),'results':results,'limits':['Only the recorded discrete combinations of hip +/-15deg and knee +/-20deg were sampled, one leg at a time.','Unsampled intermediate or larger angles, simultaneous gait, cable bends, torque, support stability and ground penetration are not validated.','Purchased servo and horn geometry is nominal and must be checked against physical parts.']}
(OUT/'reports/leg-motion-sample-check.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
print('POSE_DONE',report['sampled_poses'],report['sampled_pose_checks_pass'],total_pairs,flush=True)
