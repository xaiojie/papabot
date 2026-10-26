import bpy,bmesh,json,math,itertools,sys
from pathlib import Path
from mathutils import Vector,Matrix
OUT=Path(__file__).resolve().parents[1];M=.001
bpy.ops.wm.open_mainfile(filepath=str(OUT/'DesktopAssistant-整机结构-A4.blend'))
scene=bpy.data.scenes['20_A4_COMPLETE_ASSEMBLY'];bpy.context.window.scene=scene;bpy.context.view_layer.update()
manifest=json.loads((OUT/'reports/complete-manifest.json').read_text());parts=[scene.objects[r['name']] for r in manifest]
refs=[o for o in scene.objects if o.type=='MESH' and o.name.startswith('REF__') and not any(s in o.name for s in ['DISPLAY_ONLY','STOCK_','INSERTION_GAUGE'])]
def bounds(o):
 ps=[o.matrix_world@Vector(c)/M for c in o.bound_box]
 return Vector([min(v[i] for v in ps) for i in range(3)]),Vector([max(v[i] for v in ps) for i in range(3)])
def intersection(a,b):
 def copy(o):
  me=bpy.data.meshes.new_from_object(o.evaluated_get(bpy.context.evaluated_depsgraph_get()));me.transform(Matrix.Scale(1/M,4)@o.matrix_world)
  for v in me.vertices:v.co=Vector([round(q,5) for q in v.co])
  cp=bpy.data.objects.new('CHECK_TEMP',me);scene.collection.objects.link(cp);return cp
 x,y=copy(a),copy(b);mod=x.modifiers.new('Intersection','BOOLEAN');mod.solver='MANIFOLD';mod.operation='INTERSECT';mod.object=y
 bpy.context.view_layer.objects.active=x;bpy.ops.object.modifier_apply(modifier=mod.name)
 bm=bmesh.new();bm.from_mesh(x.data);v=abs(bm.calc_volume());bm.free()
 if x.data.vertices:intersection.last_bbox=[[round(f(v.co[i] for v in x.data.vertices),3) for i in range(3)] for f in [min,max]]
 else:intersection.last_bbox=[]
 for o in [x,y]:
  me=o.data;bpy.data.objects.remove(o,do_unlink=True);bpy.data.meshes.remove(me)
 return v
def pairs_check(pairs,tol=.05):
 bb={o.name:bounds(o) for pair in pairs for o in pair};bad=[];cnt=0
 for a,b in pairs:
  al,ah=bb[a.name];bl,bh=bb[b.name]
  if not all(min(ah[i],bh[i])-max(al[i],bl[i])>.025 for i in range(3)):continue
  v=intersection(a,b);cnt+=1
  if v>tol:
   rec={'a':a.name,'b':b.name,'volume_mm3':round(v,4),'intersection_bbox_mm':intersection.last_bbox};bad.append(rec)
 return bad,cnt
def descendant(o,j):
 p=o.parent
 while p:
  if p==j:return True
  p=p.parent
 return False
if '--motion' in sys.argv:
 results=[]
 for leg in json.loads((OUT/'reports/leg-interfaces.json').read_text()):
  h=scene.objects[leg['hip_joint']];k=scene.objects[leg['knee_joint']]
  moving=[o for o in parts+refs if descendant(o,h)];fixed=[o for o in parts+refs if not descendant(o,h)]
  upper=[o for o in moving if not descendant(o,k)];lower=[o for o in moving if descendant(o,k)]
  for ha in [-15,0,15]:
   for ka in [-20,0,20]:
    h.rotation_euler.x=math.radians(ha);k.rotation_euler.x=math.radians(ka);bpy.context.view_layer.update()
    bad,cnt=pairs_check(list(itertools.product(moving,fixed))+list(itertools.product(upper,lower)),.1)
    results.append({'leg':leg['id'],'hip_deg':ha,'knee_deg':ka,'conflicts':bad,'tested_pairs':cnt})
  h.rotation_euler.x=0;k.rotation_euler.x=0;bpy.context.view_layer.update()
 rep={'pass':not any(r['conflicts'] for r in results),'pose_count':len(results),'results':results,'threshold_mm3':.1,'limits':['Discrete poses only, no continuous sweep, torque, cable strain, gait or ground/support validation.','Both leg-to-fixed and upper-to-lower groups tested; purchased geometry nominal.']}
 (OUT/'reports/leg-motion-sample-check.json').write_text(json.dumps(rep,ensure_ascii=False,indent=2));print('MOTION',rep['pass'],flush=True)
elif '--service' in sys.argv:
 groups={
 'upper_shell':([o for o in parts if o['part_id'] in ['R01','R12_L','R12_R','R13_L','R13_R']],(0,0,1),[0,5,15,35,80]),
 'front_assembly':([o for o in parts if o['part_id'] in ['R02','R04','R07','R14']]+[o for o in refs if any(s in o.name for s in ['HS24','SCREEN_CN1','MIC_MODULE'])],(0,-1,0),[0,3,10,25]),
 'rear_assembly':([o for o in parts if o['part_id'] in ['R03','R08','R11','R19']]+[o for o in refs if any(s in o.name for s in ['SPEAKER_','S1A_','MAX98357'])],(0,1,0),[0,3,10,25]),
 'pcb_lift':([o for o in refs if o.name.startswith(('REF__PCB_','REF__ESP32'))],(0,0,1),[0,5,15,35,75]),
 'battery_tray':([o for o in parts if o['part_id']=='R21']+[o for o in refs if 'BATTERY_' in o.name],(0,0,1),[0,5,15,35,75])}
 results=[]
 for name,(moving,axis,steps) in groups.items():
  omit={'R20'}
  if name=='upper_shell':omit|={'R02','R04','R07','R14','R03','R08','R11','R19'}
  if name in ['pcb_lift','battery_tray']:omit|={'R01','R02','R04','R07','R14','R03','R08','R11','R19','R12_L','R12_R','R13_L','R13_R'}
  if name=='battery_tray':omit|={'R06'}
  fixed=[o for o in parts+refs if o not in moving and (o not in parts or o['part_id'] not in omit)]
  if name in ['upper_shell','pcb_lift','battery_tray']:fixed=[o for o in fixed if not any(s in o.name for s in ['HS24','SCREEN_CN1','MIC_MODULE','SPEAKER_','S1A_','MAX98357'])]
  if name=='battery_tray':fixed=[o for o in fixed if not o.name.startswith(('REF__PCB_','REF__ESP32'))]
  orig={o.name:o.matrix_world.copy() for o in moving}
  for step in steps:
   for o in moving:o.matrix_world=Matrix.Translation(Vector(axis)*step*M)@orig[o.name]
   bpy.context.view_layer.update();bad,cnt=pairs_check(list(itertools.product(moving,fixed)))
   results.append({'assembly':name,'distance_mm':step,'direction':axis,'conflicts':bad,'tested_pairs':cnt})
  for o in moving:o.matrix_world=orig[o.name]
  bpy.context.view_layer.update()
 rep={'pass':not any(r['conflicts'] for r in results),'results':results,'required_sequence':['Power off; disconnect battery, then detach front/rear harnesses.','Remove USB side insert R20, front assembly and rear assembly before upper shell.','Remove PCB screws and unplug all harnesses before PCB lift.','Remove PCB and R06 carrier before battery tray; R21 independently replaceable but not hot-swap.'],'limits':['Sampled straight extraction only; cables, user fingers and tools not fully modeled.']}
 (OUT/'reports/cover-service-check.json').write_text(json.dumps(rep,ensure_ascii=False,indent=2));print('SERVICE',rep['pass'],flush=True)
else:
 topo=[]
 for o in parts:
  bm=bmesh.new();bm.from_mesh(o.data);todo=set(bm.verts);n=0
  while todo:
   n+=1;stack=[todo.pop()]
   while stack:
    v=stack.pop()
    for e in v.link_edges:
     q=e.other_vert(v)
     if q in todo:todo.remove(q);stack.append(q)
  topo.append({'id':o['part_id'],'nonmanifold_edges':sum(not e.is_manifold for e in bm.edges),'connected_bodies':n,'volume_mm3':round(abs(bm.calc_volume())/M**3,3)});bm.free()
 pairs=list(itertools.combinations(parts,2))+list(itertools.product(parts,refs))
 # Large module envelopes vs each other and all main-board components.
 major=[o for o in refs if not o.name.startswith('REF__PCB_') and not any(s in o.name for s in ['HS24','SCREEN_CN1','ESP32','_BOSS','_SHAFT','_FLANGE','S1A_BUSH','S1A_LEVER'])]
 electrical=[o for o in refs if o.name.startswith('REF__PCB_') or o.name.startswith('REF__ESP32')]
 pairs+=list(itertools.product(major,electrical))
 pairs+=list(itertools.combinations(major,2))
 bad,cnt=pairs_check(pairs)
 rep={'part_count':len(parts),'reference_count':len(refs),'topology_pass':all(r['nonmanifold_edges']==0 and r['connected_bodies']==1 for r in topo),'topology':topo,'collision_pass':not bad,'exact_pairs':cnt,'conflicts':bad,'threshold_mm3':.05,'limits':['Nominal component solids are reserves, not supplier 3D models.','On-board component-to-component overlap is not a PCB DRC check.','STL and physical fit checked separately.']}
 (OUT/'reports/assembly-check.json').write_text(json.dumps(rep,ensure_ascii=False,indent=2));print(json.dumps(rep,ensure_ascii=False,indent=2),flush=True)
