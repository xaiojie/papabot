"""New assembled structure study; keeps V1 user scene and six trial coupons.
Every generated geometry is a design draft, not a production release.
Only named structural drafts are exported, in mm, separately from electronics.
"""
import bpy,bmesh,math,json,struct,hashlib,sys
from pathlib import Path
from mathutils import Vector,Matrix
OUT=Path(__file__).resolve().parents[1];M=.001
P=json.loads((OUT.parent/'print-v2/structure-a1-parameters.json').read_text())
bpy.ops.wm.open_mainfile(filepath=str(OUT/'R06-PCB支撑架-A2.blend'))
source=bpy.data.scenes['01_ASSEMBLY_AND_DISASSEMBLY'];bpy.context.window.scene=source;bpy.context.view_layer.update()
def fingerprint(scene):
 h=hashlib.sha256()
 for o in sorted(scene.objects,key=lambda o:o.name):
  h.update(o.name.encode());h.update(o.type.encode());h.update(str(tuple(tuple(r) for r in o.matrix_world)).encode())
  if o.type=='MESH':
   for v in o.data.vertices:h.update(struct.pack('<3f',*v.co))
   for f in o.data.polygons:h.update(str(tuple(f.vertices)).encode())
 return h.hexdigest()
before=fingerprint(source)
scene=bpy.data.scenes.new('10_A2_COMPLETE_ASSEMBLY');bpy.context.window.scene=scene
scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=1;scene.unit_settings.length_unit='MILLIMETERS'
scene.render.engine='CYCLES';scene.cycles.samples=20;scene.cycles.use_denoising=True
scene.render.resolution_x=1600;scene.render.resolution_y=1300;scene.render.resolution_percentage=100;scene.render.image_settings.file_format='PNG'
scene.world=bpy.data.worlds.new('A2M studio');scene.world.use_nodes=True
bg=next((n for n in scene.world.node_tree.nodes if n.type=='BACKGROUND'),None) or scene.world.node_tree.nodes.new('ShaderNodeBackground')
wo=next((n for n in scene.world.node_tree.nodes if n.type=='OUTPUT_WORLD'),None) or scene.world.node_tree.nodes.new('ShaderNodeOutputWorld')
scene.world.node_tree.links.new(bg.outputs[0],wo.inputs[0]);bg.inputs['Color'].default_value=(.78,.84,.8,1);bg.inputs['Strength'].default_value=.4
scene.view_settings.view_transform='AgX'
try:scene.view_settings.look='AgX - Medium High Contrast'
except:pass
def col(name):
 c=bpy.data.collections.new(name);scene.collection.children.link(c);return c
structs=col('A2M_COMPLETE_PRINT_PARTS');refs=col('A2M_PURCHASED_AND_LEGACY_REFERENCE__NEVER_PRINT');preview=col('A2M_UNMEASURED_CONTROL_PREVIEW__NEVER_PRINT');guides=col('A2M_VOLUME_RESERVATIONS__NEVER_PRINT');studio=col('A2M_STUDIO');labels=col('A2M_LABELS__NOT_PRINT')
def lin(x):return x/12.92 if x<=.04045 else ((x+.055)/1.055)**2.4
def material(name,hexcol):
 m=bpy.data.materials.new(name);rgb=tuple(lin(int(hexcol[i:i+2],16)/255) for i in (1,3,5));m.diffuse_color=(*rgb,1);m.use_nodes=True
 bs=next((n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED'),None) or m.node_tree.nodes.new('ShaderNodeBsdfPrincipled')
 mo=next((n for n in m.node_tree.nodes if n.type=='OUTPUT_MATERIAL'),None) or m.node_tree.nodes.new('ShaderNodeOutputMaterial')
 m.node_tree.links.new(bs.outputs[0],mo.inputs[0]);bs.inputs['Base Color'].default_value=(*rgb,1);bs.inputs['Roughness'].default_value=.59;return m
cream=material('A2M cream #EEEADF','#EEEADF');face=material('A2M face #F4F0E8','#F4F0E8');mint=material('A2M mint #9FB9A9','#9FB9A9');black=material('A2M black','#182326');green=material('A2M carrier PCB','#34735E');amber=material('A2M unverified bay','#BC9048');silver=material('A2M hardware','#AAB5B8');ground=material('A2M studio ground','#D4DCD7')
def move(o,c):
 for old in list(o.users_collection):old.objects.unlink(o)
 c.objects.link(o)
def assign(o,m):
 o.data.materials.clear();o.data.materials.append(m)
 if o.type=='MESH':
  for f in o.data.polygons:f.material_index=0
def cube(name,dim,loc,c=structs,mat=None):
 bpy.ops.mesh.primitive_cube_add(size=1,location=Vector(loc)*M);o=bpy.context.object;o.name=name;o.dimensions=Vector(dim)*M
 bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);move(o,c)
 if mat:assign(o,mat)
 return o
def cyl(name,r,depth,loc,axis='Z',n=72,c=structs):
 bpy.ops.mesh.primitive_cylinder_add(vertices=n,radius=r*M,depth=depth*M,location=Vector(loc)*M);o=bpy.context.object;o.name=name;move(o,c)
 if axis=='Y':o.rotation_euler.x=math.pi/2
 elif axis=='X':o.rotation_euler.y=math.pi/2
 bpy.ops.object.transform_apply(location=False,rotation=True,scale=True);return o
def boolean(o,c,op='DIFFERENCE'):
 # Carry out booleans in mm at world origin, with coordinate quantization far below
 # printer resolution. This avoids metre-scale near-coplanar cracks in Blender.
 bpy.context.view_layer.update()
 def mm_copy(src,name):
  dg=bpy.context.evaluated_depsgraph_get()
  me=bpy.data.meshes.new_from_object(src.evaluated_get(dg))
  me.transform(Matrix.Scale(1/M,4)@src.matrix_world)
  for v in me.vertices:v.co=Vector([round(q,5) for q in v.co])
  bm=bmesh.new();bm.from_mesh(me);bmesh.ops.remove_doubles(bm,verts=bm.verts,dist=0.00002)
  bmesh.ops.dissolve_degenerate(bm,edges=list(bm.edges),dist=0.00001)
  bmesh.ops.recalc_face_normals(bm,faces=bm.faces);bm.to_mesh(me);bm.free()
  cp=bpy.data.objects.new(name,me);scene.collection.objects.link(cp);return cp
 a=mm_copy(o,'TEMP boolean base');b=mm_copy(c,'TEMP boolean tool')
 mod=a.modifiers.new('Millimetre boolean','BOOLEAN');mod.solver='MANIFOLD';mod.operation=op;mod.object=b
 bpy.context.view_layer.objects.active=a;bpy.ops.object.modifier_apply(modifier=mod.name)
 me=a.data.copy();me.transform(o.matrix_world.inverted()@Matrix.Scale(M,4))
 o.modifiers.clear();o.data=me
 bpy.data.objects.remove(a,do_unlink=True);bpy.data.objects.remove(b,do_unlink=True);bpy.data.objects.remove(c,do_unlink=True)
def rr(w,h,r,n=12):
 pts=[]
 for cx,cz,a in [(w/2-r,h/2-r,0),(-w/2+r,h/2-r,90),(-w/2+r,-h/2+r,180),(w/2-r,-h/2+r,270)]:
  for i in range(n+1):
   q=math.radians(a+i*90/n);pts.append((cx+r*math.cos(q),cz+r*math.sin(q)))
 return pts
def loft(name,profiles,c=structs):
 # tuples: y,width,height,radius,centre x,centre z
 verts=[]
 for y,w,h,r,x,z in profiles:verts += [((a+x)*M,y*M,(b+z)*M) for a,b in rr(w,h,r)]
 n=len(verts)//len(profiles);faces=[]
 for s in range(len(profiles)-1):
  for i in range(n):j=(i+1)%n;faces.append((s*n+i,s*n+j,(s+1)*n+j,(s+1)*n+i))
 faces += [tuple(reversed(range(n))),tuple(range((len(profiles)-1)*n,len(profiles)*n))]
 me=bpy.data.meshes.new(name);me.from_pydata(verts,[],faces);me.update();o=bpy.data.objects.new(name,me);c.objects.link(o);clean(o);return o
def clean(o):
 bm=bmesh.new();bm.from_mesh(o.data);bmesh.ops.remove_doubles(bm,verts=bm.verts,dist=1e-8);bmesh.ops.dissolve_degenerate(bm,edges=list(bm.edges),dist=2e-8);bmesh.ops.recalc_face_normals(bm,faces=bm.faces);bm.to_mesh(o.data);bm.free();o.data.update()
def ring(name,outer,inner,c=structs):
 o=loft(name,outer,c);boolean(o,loft('CUT hollow',inner));return o
def hex_hole(o,af,depth,loc,axis='Y'):boolean(o,cyl('CUT nut access',af/math.sqrt(3),depth,loc,axis,n=6))
def dup_mesh(o,name,c):
 cp=o.copy();cp.data=o.data.copy();cp.name=name;cp.animation_data_clear();cp.parent=None;cp.matrix_world=o.matrix_world.copy();c.objects.link(cp);return cp
def mesh_bounds(o):
 vs=[o.matrix_world@v.co/M for v in o.data.vertices];return [min(v[i] for v in vs) for i in range(3)],[max(v[i] for v in vs) for i in range(3)]


# Complete prototype mechanical assembly. Nominal purchased envelopes are explicitly
# marked; only objects registered by register() are exported as printable parts.
import csv
PROJECT=OUT.parents[1]
PCB=json.loads((PROJECT/'pcb-design/native-rev-a/carrier-definition.json').read_text())['board']
parts=[];electronics=[];joints=[]
REAR=68.0
BASE_FIX=[[-33,-16],[33,-16],[-50,8],[50,8]]
P['front_fastener_xz']=[[-48,41.7],[48,41.7],[-48,96],[48,96]]
P['display_tab_fastener_xz']=[[-43,44],[46,44],[-43,94],[46,94]]
LEG_POS=[('FL',-1,-1,-12.5),('FR',1,-1,-12.5),('RL',-1,1,25),('RR',1,1,25)]

def addbox(a,d,loc):boolean(a,cube('UNION solid',d,loc),'UNION')
def addcyl(a,r,h,loc,axis='Z'):boolean(a,cyl('UNION cylinder',r,h,loc,axis),'UNION')
def hole(a,r,h,loc,axis='Z'):boolean(a,cyl('CUT round',r,h,loc,axis))
def slot(a,r,p,q,h,axis='Z'):
 hole(a,r,h,p,axis);hole(a,r,h,q,axis)
 dims=[abs(q[i]-p[i])+2*r for i in range(3)];dims['XYZ'.index(axis)]=h
 boolean(a,cube('CUT slot bridge',dims,[(p[i]+q[i])/2 for i in range(3)]))
def register(o,id,label,orientation='Z',qty=1,note=''):
 o.name=id+'__'+o.name.split('__')[-1];clean(o);o['part_id']=id;o['label_zh']=label;o['quantity']=qty
 o['revision']='A2';o['status']='CAD_FOR_PROTOTYPE_FIT_TEST';o['fit_note']=note
 parts.append({'object':o,'id':id,'label_zh':label,'quantity':qty,'orientation':orientation,'note':note});return o

def reference(name,d,loc,mat=black,status='PROVISIONAL_ENVELOPE_NOT_MEASURED'):
 o=cube('REF__'+name,d,loc,refs,mat);o['status']=status;o['never_print']=True;electronics.append(o);return o

def shift_geometry(o,delta):
 o.data.transform(Matrix.Translation(Vector(delta)*M));clean(o)

# Existing shallow display assembly remains at the established front datum.
front=loft('R02__shallow_front_cover_A2',[(-26.2,124,76,14,0,68),(-23.8,124,76,14,0,68)])
boolean(front,loft('CUT glass frame clearance',[(-28,60,43,1.4,0,68),(-20,60,43,1.4,0,68)]))
lip=ring('ADD front location lip',[(-23.9,118.7,70.7,11.35,0,68),(-21.8,118.7,70.7,11.35,0,68)],[(-24.2,115.5,67.5,9.75,0,68),(-21.5,115.5,67.5,9.75,0,68)])
for x,z in P['front_fastener_xz']:boolean(lip,cube('CUT boss lip relief',(18,5,13),(x,-22,z)))
boolean(front,lip,'UNION')
for x,z in P['front_fastener_xz']:hole(front,1.65,10,(x,-24,z),'Y')
# Front microphone grille, left of the complete display board.
for z in [-3,0,3]:
 for x in [-2.5,0,2.5]:hole(front,.7,8,(-50+x,-25,76.8+z),'Y')
for sx in [-1,1]:
 for zz in [41.7,96]:boolean(front,cube('CUT front lip screw-arm relief',(12,3,13),(sx*60,-22.29,zz)))
for x in [-33,33]:
 addbox(front,(8,10.6,7),(x,-18.8,38.1));hole(front,1.7,14,(x,-16,38),'Z');hex_hole(front,5.8,5.5,(x,-16,38.85),'Z')
assign(front,face);register(front,'R02','浅前盖与麦克风声孔','front_down',note='60×43屏幕框开窗沿用名义几何；玻璃内缩约0.8mm需实测。')
display=ring('R04__display_support_A2',[(-17.8,99,50,3,8.5,68),(-13.8,99,50,3,8.5,68)],[(-20,77,28,1,10.5,68),(-12,77,28,1,10.5,68)])
boolean(display,cube('CUT display header',(7,10,34),(-33,-15,68)))
for x,z in P['screen_hole_xz']:
 addcyl(display,4.1,1.9,(x,-18.45,z),'Y');hole(display,1.6,12,(x,-17,z),'Y');hex_hole(display,5.7,3.1,(x,-14.85,z),'Y')
for x,z in P['display_tab_fastener_xz']:
 addbox(display,(11,2.2,8),(x,-14.9,z));hole(display,1.2,10,(x,-15.8,z),'Y')
for xx in [-55,55]:
 for zz,hh in [(41.7,8.6),(96,10)]:boolean(display,cube('CUT front shell screw-arm clearance',(28,.9,hh),(xx,-17.65,zz)))
assign(display,cream);register(display,'R04','完整屏幕板固定框','back_down',note='上下固定耳改为Z44和94，避开底盘腿座螺母；91×44板体及背面元件待实物试配。')
carrier=dup_mesh(bpy.data.objects['R06__PCB_support_bridge_A2'],'R06__PCB_support_bridge_A2_complete',structs)
register(carrier,'R06','主控PCB支撑架','inverted',note='PCB板底Z66；板上用4颗M2×8，头径≤4mm，不加大垫片；底部仍用M3×10。保留PCB原Ø3.2孔。')

# Body: the rear equipment compartment is deeper; front and screen coordinates stay fixed.
outer=[(-23.5,124,76,14,0,68),(61,124,76,14,0,68),(68,116,70,11,0,68)]
hood=ring('R01__main_housing_A2',outer,[(-25,119.2,71.2,11.6,0,68),(60,119.2,71.2,11.6,0,68),(65.6,111.2,65.2,8.6,0,68)])
boolean(hood,cube('CUT floor service',(115,88,22),(0,21.5,23.6)))
boolean(hood,loft('CUT rear access',[(63,94.6,56.6,4.7,0,74),(73,94.6,56.6,4.7,0,74)]))
for x,z in P['front_fastener_xz']:
 # Lower bosses fit between the leg nuts (top37.4) and display PCB (bottom46).
 addcyl(hood,4.0 if z<60 else 4.5,6,(x,-20.5,z),'Y');addbox(hood,(14,6,7.4 if z<60 else 8),((1 if x>0 else -1)*55,-20.5,z))
for x,z in P['display_tab_fastener_xz']:
 addcyl(hood,4,4,(x,-11.5,z),'Y');addbox(hood,(22,4,8),((1 if x>0 else -1)*53,-11.5,z))
for x,z in P['rear_fastener_xz']:
 addcyl(hood,4.5,8,(x,64,z),'Y');addbox(hood,(12,4,8),((1 if x>0 else -1)*50,66,z))
for x,y in [p for p in BASE_FIX if p[1]>=0]:
 addcyl(hood,4.5,7,(x,y,38.1),'Z')
 if y<0:addbox(hood,(28,8,5),((1 if x>0 else -1)*46,y,38.1))
 else:addbox(hood,(13,8,5),((1 if x>0 else -1)*55,y,38.1))
# Side equipment-rack fixing bosses, below the top corner curvature.
for s in [-1,1]:
 for y,z in [(5,69),(49,69),(5,96),(49,96)]:
  addcyl(hood,3.0,2.6,(s*58.7,y,z),'X')
# Mic tray ears attach to these small side-wall bosses.
for z in [62.0,91.6]:addcyl(hood,3,1.8,(-59.1,-5,z),'X')
boolean(hood,loft('CUT exterior limit',outer),'INTERSECT')
boolean(hood,cube('CUT floor final',(115,88,22),(0,21.5,23.6)))
for x,z in P['front_fastener_xz']:
 hole(hood,1.65,16,(x,-20,z),'Y');hex_hole(hood,5.7,6.1,(x,-18.05,z))
# Recess only the rear edge of a screw arm where a display mounting spacer passes.
# This preserves the full front load wall and provides 0.3mm radial clearance.
for x,z in P['screen_hole_xz']:hole(hood,4.4,2.7,(x,-18.35,z),'Y')
for x,z in P['display_tab_fastener_xz']:
 hole(hood,1.2,10,(x,-11.5,z),'Y');hex_hole(hood,4.2,4.5,(x,-10.25,z))
for x,z in P['rear_fastener_xz']:
 hole(hood,1.65,16,(x,65,z),'Y');hex_hole(hood,5.7,8.6,(x,61.3,z))
for x,y in BASE_FIX:
 hole(hood,1.7,14,(x,y,38),'Z');hex_hole(hood,5.8,5.5,(x,y,38.85),'Z')
for s in [-1,1]:
 for y,z in [(5,69),(49,69),(5,96),(49,96)]:
  hole(hood,1.2,8,(s*57.5,y,z),'X')
  hex_hole(hood,4.3,4.2,(s*60.9,y,z),'X')
for z in [62.0,91.6]:
 hole(hood,1.2,9,(-57,-5,z),'X');hex_hole(hood,4.3,3.8,(-61.1,-5,z),'X')
for x in [-36,36]:hole(hood,2.7,12,(x,-1,105),'Z')
# Actual nominal servo bodies pass through these two side openings per side.
for ident,s,sy,yh in LEG_POS:
 boolean(hood,cube('CUT hip body and cable',(18,15.4,27.0),(s*62,yh,63)))
# Rear speaker ring and one retention boss reach through the enlarged service opening.
hole(hood,14.9,12,(-35,66,84),'Y')
hole(hood,3.7,12,(-52,66,84),'Y')
# Vent slots on both sides of the rear compartment.
for s in [-1,1]:
 for z in [76,82,88,91.5]:boolean(hood,cube('CUT side vent',(18,14,2),(s*61,52,z)))
for sx in [-1,1]:
 for yy in [-17,37]:hole(hood,5.0,4.0,(sx*51,yy,35.6),'Z')
assign(hood,cream);register(hood,'R01','主外壳：加深后舱、舵机孔和模块座','front_down',note='前脸不移动，后壁Y68。供电模块壳内温升和通风需实测。')

# Load-bearing floor: four hip brackets attach directly to this plate; battery remains low.
base=cube('R05__reinforced_floor_and_battery_tray_A2',(110,85.7,4.6),(0,21.35,32.3))
rim=cube('ADD battery rim',(83.8,48.8,4.2),(0,14,36.5));boolean(rim,cube('CUT battery',(79,44,6),(0,14,37)))
boolean(rim,cube('CUT battery lead exit',(8,16,6),(41,14,37)));boolean(base,rim,'UNION')
for x,y in BASE_FIX+P['carrier_foot_xy']:hole(base,1.7,12,(x,y,33),'Z')
for y in [-7,35]:boolean(base,cube('CUT battery belt',(11,2.2,12),(0,y,33)))
# Eight M3x12 hip bracket bolts; nuts sit in top-loaded pockets, outside battery envelope.
for ident,s,sy,yh in LEG_POS:
 by=-17 if sy<0 else 37
 for x in [s*43,s*51]:
  addcyl(base,4.4,3,(x,by,35.9),'Z');hole(base,1.7,16,(x,by,33),'Z')
  hex_hole(base,5.8,3.0,(x,by,36.1),'Z')
# Rear electronics rack floor fixing, outside the battery bay.
for x in [-4,48]:
 for y in [47,57]:hole(base,1.7,12,(x,y,33),'Z')
# Fuse and harness tie-down slots in the rear floor. No bare high-current PCB bus is implied.
for x in [-10,10]:
 for y in [44,57]:boolean(base,cube('CUT power harness tie',(3.2,2.2,10),(x,y,33)))
assign(base,cream);register(base,'R05','加强底盘与电池托架','Z',note='4.6mm底板。腿座M3×12；底盖及主控架建议M3×10。电池仍按75×40×20目标。')

# All four legs use stock servo horns. Printed spline teeth are deliberately absent.
# Both joints pitch about X in a fore/aft leg plane; rest leg centres are defined below.
leg_objects=[]
def cyl_x(name,r,depth,loc,mat=mint):
 o=cyl(name,r,depth,loc,'X');assign(o,mat);return o

def parent_keep(o,parent):
 world=o.matrix_world.copy();o.parent=parent;o.matrix_world=world

def make_joint(name,loc,parent=None):
 o=bpy.data.objects.new(name,None);refs.objects.link(o);o.location=Vector(loc)*M;o.empty_display_type='ARROWS';o.empty_display_size=.006
 if parent:parent_keep(o,parent)
 o['status']='Pose control only; actual travel and torque untested';joints.append(o);return o

def yz_beam(name,p,q,width,thickness,mat=mint):
 # Rectangular beam with rounded endpoints in its Y/Z plane, extruded along X.
 mid=(Vector(p)+Vector(q))/2;length=(Vector(q)-Vector(p)).length
 o=cube(name,(thickness,width,length),mid)
 o.rotation_euler.x=-math.atan2(q[1]-p[1],q[2]-p[2]);bpy.context.view_layer.objects.active=o;bpy.ops.object.transform_apply(location=False,rotation=True,scale=True)
 for point in [p,q]:addcyl(o,width/2,thickness,point,'X')
 assign(o,mat);return o

for ident,s,sy,yh in LEG_POS:
 # Nominal MG90S: case depth is along the output axis, flange long direction is Z.
 hip=cube('L101_'+ident+'__hip_fixed_bracket',(3,22,38),(s*76.75,yh,63))
 boolean(hip,cube('CUT servo case',(12,13.4,24.0),(s*76.75,yh,63)))
 # Two slotted ear fixings allow modest case/ear-pitch variation.
 for dz in [-13.75,13.75]:slot(hip,1.2,(s*76.75,yh,63+dz-.7),(s*76.75,yh,63+dz+.7),9,'X')
 by=-17 if sy<0 else 37;miny=min(yh-12,by-5);maxy=max(yh+12,by+5)
 addbox(hip,(40,maxy-miny,3.4),(s*59.0,(miny+maxy)/2,28.3))
 for yy in [yh-9.4,yh+9.4]:addbox(hip,(3,3.2,18),(s*76.75,yy,37.5))
 for x in [s*43,s*51]:hole(hip,1.7,10,(x,by,28.7),'Z')
 # Cable ties close to the fixed case; no clamping against the case wire exit.
 for yy in [yh-9.4,yh+9.4]:boolean(hip,cube('CUT fixed cable tie',(9,1.8,3),(s*76.75,yy,40)))
 boolean(hip,cube('CUT front cover foot clearance',(125.2,20,10),(0,-31.4,28)))
 assign(hip,mint);register(hip,'L101_'+ident,'髋舵机固定座 '+ident,'side_down',note='名义壳体22.8×12.2，轴向22.5；耳孔距27.5±1.4为试配槽，非该批舵机实测。')
 case=reference(ident+'_HIP_CASE',(22.5,12.2,22.8),(s*71,yh,63))
 flange=reference(ident+'_HIP_FLANGE',(2,12.2,32.4),(s*79.25,yh,63))
 # Remove ear holes from the purchased reference flange for mating checks.
 for dz in [-13.75,13.75]:hole(flange,1.2,6,(s*79.25,yh,63+dz),'X')
 boss=cyl('REF__'+ident+'_HIP_BOSS',5.3,3.8,(s*84.15,yh,68.7),'X',c=refs);assign(boss,black);electronics.append(boss)
 shaft=cyl('REF__'+ident+'_HIP_SHAFT',2.4,1.45,(s*86.775,yh,68.7),'X',c=refs);assign(shaft,silver)
 hj=make_joint('JNT_'+ident+'_HIP_X',(s*88.4,yh,68.7))
 yk=yh+sy*8;zk=43.7
 upper=cyl_x('L102_'+ident+'__upper_link_and_knee_mount',12,3.6,(s*90.2,yh,68.7))
 # Bridge stays above the knee case; collar touches only the mounting ears.
 addbox(upper,(13.3,22,11),(s*95.05,yh+sy*4,60.5))
 knee_collar=cube('ADD knee collar',(3,22,38),(s*100.25,yk,38.0))
 boolean(knee_collar,cube('CUT knee case',(12,13.4,24),(s*100.25,yk,38)))
 boolean(upper,knee_collar,'UNION')
 hole(upper,3.2,14,(s*90.2,yh,68.7),'X')
 # Two M2 slots on opposite arms of the supplied double horn.
 for sign in [-1,1]:slot(upper,1.2,(s*90.2,yh+sign*6,68.7),(s*90.2,yh+sign*8.1,68.7),18,'X')
 for dz in [-13.75,13.75]:slot(upper,1.2,(s*100.25,yk,38+dz-.7),(s*100.25,yk,38+dz+.7),12,'X')
 register(upper,'L102_'+ident,'上腿连杆与膝舵机座一体 '+ident,'side_down',note='使用随舵机附带的双臂舵盘；中心Ø6.4通孔供原中心螺丝检修；M2槽须与舵盘试配。')
 kcase=reference(ident+'_KNEE_CASE',(22.5,12.2,22.8),(s*94.5,yk,38))
 kflange=reference(ident+'_KNEE_FLANGE',(2,12.2,32.4),(s*102.75,yk,38))
 for dz in [-13.75,13.75]:hole(kflange,1.2,6,(s*102.75,yk,38+dz),'X')
 kboss=cyl('REF__'+ident+'_KNEE_BOSS',5.3,3.8,(s*107.65,yk,zk),'X',c=refs);assign(kboss,black);electronics.append(kboss)
 kshaft=cyl('REF__'+ident+'_KNEE_SHAFT',2.4,1.45,(s*110.275,yk,zk),'X',c=refs);assign(kshaft,silver)
 kj=make_joint('JNT_'+ident+'_KNEE_X',(s*112.5,yk,zk),hj)
 yf=yk+sy*18
 lower=yz_beam('L104_'+ident+'__lower_leg_and_foot',(s*114.9,yk,zk),(s*114.9,yf,6),12,4.8)
 addcyl(lower,12,4.8,(s*114.9,yk,zk),'X')
 boolean(lower,cube('CUT sole plane',(60,100,20),(s*114.9,yf,-8)))
 addcyl(lower,9,4,(s*114.9,yf,4),'Z')
 hole(lower,3.2,12,(s*114.9,yk,zk),'X')
 dy,dz=sy*18,-37.7;l=math.hypot(dy,dz)
 for sg in [-1,1]:slot(lower,1.2,(s*114.9,yk+sg*dy/l*6,zk+sg*dz/l*6),(s*114.9,yk+sg*dy/l*8.1,zk+sg*dz/l*8.1),12,'X')
 register(lower,'L104_'+ident,'下腿与脚掌一体 '+ident,'side_down',note='脚底平面粘Ø12×2硅胶脚垫；舵盘槽及负载、行程待单腿验证。')
 foot=cyl('REF__'+ident+'_12x2_SILICONE_PAD',6,2,(s*114.9,yf,1),'Z',c=refs);assign(foot,black);electronics.append(foot)
 # Stock horn envelopes visualize the mechanical interface; no printed spline is exported.
 hh=reference(ident+'_STOCK_HIP_HORN_NOMINAL',(1.6,18,4),(s*87.6,yh,68.7),face)
 kh=yz_beam('REF__'+ident+'_STOCK_KNEE_HORN_NOMINAL',(s*111.7,yk-dy/l*8,zk-dz/l*8),(s*111.7,yk+dy/l*8,zk+dz/l*8),4,1.6,face);move(kh,refs)
 for o in [upper,kcase,kflange,kboss,kshaft,hh]:parent_keep(o,hj)
 for o in [lower,foot,kh]:parent_keep(o,kj)
 leg_objects.append({'id':ident,'fixed':hip.name,'hip_joint':hj.name,'knee_joint':kj.name,'upper':upper.name,'lower':lower.name,'nominal_servo_case':[22.5,12.2,22.8]})

# Rear panel: replaceable holders support de-soldered controls rather than assuming threaded EC11.
rear=loft('R03__rear_control_panel_A2',[(68.2,98,58,8,0,74),(70.6,98,58,8,0,74)])
for x,z in P['rear_fastener_xz']:hole(rear,1.65,9,(x,69,z),'Y')
hole(rear,3.3,12,(28,69,90),'Y');hole(rear,3.6,12,(28,69,73),'Y')
hole(rear,6.25,12,(19,69,55),'Y')
boolean(rear,cube('CUT charging plug',(13,12,8),(-22,69,55.5)))
for x in [-6,-3,0,3,6]:
 for z in [-6,-3,0,3,6]:
  if x*x+z*z<60:hole(rear,.85,10,(-35+x,69,84+z),'Y')
for x in [18,38]:
 addcyl(rear,3.1,7.3,(x,64.65,90),'Y');hole(rear,1.2,18,(x,64,90),'Y');hex_hole(rear,4.3,8.9,(x,67.05,90),'Y')
for x in [19,37]:
 addcyl(rear,3,4.2,(x,66.3,73),'Y');hole(rear,1.2,14,(x,66,73),'Y');hex_hole(rear,4.3,5.7,(x,68.65,73),'Y')
# Speaker sleeve built into the rear cover, plus a separate retaining ring.
cup=cyl('ADD speaker sleeve',14.5,11,( -35,62.7,84),'Y');hole(cup,12.2,15,(-35,62.2,84),'Y');boolean(rear,cup,'UNION')
for x in [-52,-18]:
 addcyl(rear,3.3,11.3,(x,62.85,84),'Y');hole(rear,1.2,20,(x,63,84),'Y');hex_hole(rear,4.3,12.7,(x,65.15,84),'Y')
for x in [-33.5,-10.5]:hole(rear,1.2,12,(x,69,51.2),'Y')
# Amplifier seat and two tie slots, between the speaker and controls.
for x in [-15,11]:addbox(rear,(3,3.0,22),(x,66.8,85))
for z in [78,92]:
 addbox(rear,(23,2.4,3),(-2,66.9,z));boolean(rear,cube('CUT amp tie',(3.2,8,1.8),(-2,67,z)))
assign(rear,face);register(rear,'R03','后面板：旋钮、按键、开关、充电、喇叭与功放座','back_down',note='S1A孔Ø12.5为资料值；其余控件外形/针脚、开口和压片需要实物试配。')
for id,z,xx,y0 in [('R07',90,[18,38],59.0),('R08',73,[19,37],62.2)]:
 clamp=loft(id+'__control_retainer',[(y0,26,19 if id=='R07' else 16,3,28,z),(y0+2,26,19 if id=='R07' else 16,3,28,z)])
 boolean(clamp,cube('CUT solder contact relief',(8,6,8),(28,y0+1,z)))
 for x in xx:hole(clamp,1.2,8,(x,y0+1,z),'Y')
 if id=='R07':hole(clamp,4.9,8,(42,60,99),'Y')
 assign(clamp,mint);register(clamp,id,'EC11后置压片' if id=='R07' else '独立按键后置压片','front_down',note='金属/塑料外壳边缘支撑，中央为焊脚避空；配EVA薄垫，实测后调整压紧量。')
reference('EC11_METAL_BODY_NOMINAL',(12.5,5.4,13),(28,63.7,90),silver)
reference('KEY_BODY_NOMINAL',(12,4,12),(28,66.2,73),black)
knob=cyl('REF__EC11_KNOB',7.75,13.8,(28,78,90),'Y',c=refs);assign(knob,black)
key=cyl('REF__KEY_BUTTON',3.3,5.5,(28,70,73),'Y',c=refs);assign(key,black)
reference('S1A_BODY_AND_TERMINAL_RESERVATION',(28,25,18),(19,55.7,55),black)
sw=cyl('REF__S1A_BUSHING',6,6,(19,71.2,55),'Y',c=refs);assign(sw,silver)
lever=cyl('REF__S1A_LEVER',2.5,14,(19,80,55),'Y',c=refs);assign(lever,silver)
speaker=cyl('REF__SPEAKER_23p6x10p4',11.8,10.4,(-35,62.6,84),'Y',c=refs);assign(speaker,black);electronics.append(speaker)
reference('MAX98357_RESERVATION',(22,8,20),(-2,61.2,85))
ringpart=cyl('R11__speaker_retaining_ring',14.5,2,(-35,56.2,84),'Y');hole(ringpart,8.0,6,(-35,56.2,84),'Y')
for x in [-52,-18]:addcyl(ringpart,3.3,2,(x,56.2,84),'Y');hole(ringpart,1.2,8,(x,56.2,84),'Y')
assign(ringpart,mint);register(ringpart,'R11','喇叭后压圈','front_down',note='Ø23.6×10.4为商品标称；软垫接触外壳边缘，不能压振膜。')

# Charger tray is replaceable independently of the rear panel.
charger=cube('R09__charger_tray',(23.2,32,2),(-22,52.2,52.8))
for x in [-33.0,-11.0]:addbox(charger,(2.2,32,4),(x,52.2,54.8))
addbox(charger,(34,2.2,8),(-22,67.1,52.8));boolean(charger,cube('CUT USB path',(18.4,10,9),(-22,68,55.5)))
for x in [-33.5,-10.5]:hole(charger,1.2,8,(x,67.1,51.2),'Y');hex_hole(charger,4.3,2.2,(x,65.9,51.2),'Y')
for y in [42.5,61.5]:
 for x in [-33.5,-10.5]:addcyl(charger,2.8,4,(x,y,55.0),'Z');hole(charger,1.2,10,(x,y,55),'Z');hex_hole(charger,4.3,3.4,(x,y,53.5),'Z')
hole(charger,4.9,10,(-42,67,49),'Y')
assign(charger,mint);register(charger,'R09','Type-C充电板托架','Z',note='板体28×17为商品标称；USB口伸出量、背面焊点和压条垫厚待实测。')
for i,y in enumerate([42.5,61.5]):
 clamp=cube('R10_'+str(i+1)+'__charger_edge_clamp',(29,3.4,1.8),(-22,y,60.9))
 for x in [-33.5,-10.5]:
  addbox(clamp,(6,3.4,4.8),(x,y,59.4));hole(clamp,1.2,14,(x,y,58.5),'Z')
 assign(clamp,mint);register(clamp,'R10_'+str(i+1),'充电板边缘压条 '+str(i+1),'Z',note='需要实测元件位置后选夹持边；压条与板间用EVA隔离。')
reference('CHARGER_BOARD_28x17',(17,28,1.6),(-22,53.6,54.6),green,'VENDOR_NOMINAL_28x17; thickness assumed')
reference('CHARGER_COMPONENTS_RESERVATION',(13,22,3),(-22,52.5,56.9))
reference('CHARGER_USB_ENVELOPE',(9,5,3.2),(-22,68.0,55.5),silver)

# PCA9685 rear rack: open frame, four feet and tie retention rather than fictitious module holes.
rack=cube('R16__PCA9685_rear_rack',(70,30,2.4),(9,45.5,65.8))
boolean(rack,cube('CUT rack ventilation',(57,18,8),(9,45.5,65.8)))
for x in [-4,48]:
 for y in [47,57]:
  if x>0:addbox(rack,(14,8,2.4),(45,y,65.8))
  elif y==47:addbox(rack,(8,18,2.4),(x,42.5,65.8))
  else:addbox(rack,(8,8,2.4),(x,y,65.8))
  addcyl(rack,3.5,32.4,(x,y,50.8),'Z')
  addcyl(rack,4.5,5.4,(x,y,37.3),'Z')
  hole(rack,1.7,40,(x,y,51),'Z');hex_hole(rack,5.8,2.7,(x,y,37.55),'Z')
  boolean(rack,cube('CUT side loading M3 nut',(7,5.8,2.7),(x+(3 if x>0 else -3),y,37.55)))
for x in [-17,35]:
 for y in [33.5,57.5]:boolean(rack,cube('CUT PCA cable tie',(3.2,2.2,8),(x,y,65.8)))
assign(rack,mint);register(rack,'R16','PCA9685后舱安装架','inverted',note='62×25板体为通用名义占位；开放绑带座，接插件需实物试配。')
reference('PCA9685_BOARD_NOMINAL',(62,25,1.6),(9,44,68.8),green)
reference('PCA9685_HEADER_AND_PLUG_BAY',(58,12,19),(9,47.5,79.1))
# Power module holders are open strap trays with slots, not closed encapsulations.
for id,s,label,d,z0,y0 in [('R17',1,'DFR0753舵机降压固定架',(10,50,30),83,30),('R18',-1,'好盈UBEC逻辑降压固定架',(7,17,43),77.5,45)]:
 panel=cube(id+'__power_module_strap_mount',(2.4,54,32),(s*56.2,27,82.5))
 boolean(panel,cube('CUT module ventilation',(7,42,20),(s*56.2,27,82.5)))
 for y,z in [(5,69),(49,69),(5,96),(49,96)]:
  addcyl(panel,3,2.4,(s*56.2,y,z),'X');hole(panel,1.2,8,(s*56.2,y,z),'X')
  head=cyl('REF__'+id+'_M2_PAN_HEAD',2,1.6,(s*54.2,y,z),'X',c=refs);assign(head,silver)
 # Vertical UBEC sits on a strap shelf at the rear of the shared hole grid.
 if s<0:
  addbox(panel,(2.4,19,47),(s*56.2,45,77.5))
  boolean(panel,cube('CUT UBEC open centre',(7,11,34),(s*56.2,45,77.5)))
 for y,z in ([(7,76),(51,76),(7,90),(51,90)] if s>0 else [(37,62),(53,62),(37,93),(53,93)]):
  boolean(panel,cube('CUT module strap slot',(9,2.2,3.2),(s*56.2,y,z)))
 boolean(panel,loft('CUT interior rack envelope',[(-25,118.6,70.6,11.3,0,68),(59.8,118.6,70.6,11.3,0,68),(65.3,110.6,64.6,8.3,0,68)]),'INTERSECT')
 assign(panel,mint);register(panel,id,label,'side_down',note='开式绑带固定、EVA绝缘垫。DFR0753包络是预留空间；UBEC43×17×7为标称本体，不含线和磁环。')
 reference('DFR0753_RESERVED_BAY' if s>0 else 'HOBBYWING_43x17x7_NOMINAL',d,(s*(48.0 if s>0 else 49.7),y0,z0),black)

# Universal microphone tray, sized to rotate narrow rectangular modules or a small circular board.
mic=cube('R14__microphone_replaceable_tray',(18,2.2,25.8),(-50,-3.9,76.8))
for x in [-58.4,-41.6]:addbox(mic,(1.2,12,25.8),(x,-11,76.8))
for z in [64.6,89.0]:addbox(mic,(18,12,1.4),(-50,-11,z))
for z in [62.0,91.6]:
 addbox(mic,(4.4,8,5),(-56,-5,z));hole(mic,1.2,10,(-56,-5,z),'X');hole(mic,2.2,1.2,(-54.2,-5,z),'X')
for z in [66.5,87]:boolean(mic,cube('CUT mic tie slots',(3.2,9,2.2),(-50,-4,z)))
for zz in [62,91.6]:hole(mic,3.4,1.6,(-59,-5,zz),'X')
assign(mic,mint);register(mic,'R14','可换麦克风托架','front_down',note='内腔约15.6×23.0，麦克风本体身份待核；可转向放置，EVA隔振，扎带避开声孔。')
reference('MIC_NARROW_MODULE_BAY',(14,11.2,22),(-50,-11.1,76.8))

# Retain user ear silhouettes, join the raised colour insert, and add a short locating peg.
for side,x in [('L',-36),('R',36)]:
 ear=dup_mesh(bpy.data.objects['P008_ear_'+side],'R12_'+side+'__ear_with_integrated_insert',structs)
 insert=dup_mesh(bpy.data.objects['P009_ear_insert_'+side],'TEMP ear insert',structs)
 boolean(ear,insert,'UNION');boolean(ear,cube('CUT shortened locating peg',(24,16,15),(x,-1,96.3)))
 hole(ear,1.2,12,(x,-1,107),'Z');hex_hole(ear,4.3,2.2,(x,-1,108.1),'Z')
 boolean(ear,cube('CUT rear nut loading',(4.4,4.0,2.2),(x,1,108.1)))
 assign(ear,mint);register(ear,'R12_'+side,'一体小耳朵 '+side,'front_down',note='保留原小耳轮廓，内片合并为浅浮雕供奶白上色；后侧装M2螺母，底部螺丝固定。')
 washer=cyl('R13_'+side+'__ear_retaining_washer',5,1.2,(x,-1,103),'Z');hole(washer,1.2,6,(x,-1,103),'Z')
 assign(washer,cream);register(washer,'R13_'+side,'小耳朵内侧压垫 '+side,'Z')
# Known display surface and PCB remain user-based references, without original front controls.
for o in source.objects:
 if o.type in ['MESH','CURVE','FONT'] and o.name.startswith(('D001','D002','D003','D004','D012','D013','LCD_','Display_')):
  cp=dup_mesh(o,'REF_SCREEN__'+o.name,refs);cp['never_print']=True
# Use the current R06 PCB, headers and lead geometry as hardware references.
bpy.context.window.scene=bpy.data.scenes['02_R06_FIT__PCB_BATTERY_FLOOR'];bpy.context.view_layer.update()
for o in bpy.data.collections['R06_FIT_REFERENCES__DO_NOT_PRINT'].objects:
 if o.name.startswith(('REF_PCB','REF_J','REF_LCKFB','REF_USB','REF_MCU','REF_ANTENNA','REF_PAD','REF_LEAD','REF_BATTERY','REF_FASTENER')):
  cp=dup_mesh(o,'REF_CURRENT__'+o.name,refs);cp['never_print']=True
bpy.context.window.scene=scene;bpy.context.view_layer.update()
# Purchased foam and tie routes are references; they are not exported as print geometry.
reference('BATTERY_EVA_BASE',(75,40,1),(0,14,35.1),amber)

# Standalone STL files have units mm, a flat Z=0 origin and only the one registered part.
manifest=[]
bpy.context.view_layer.update()
for rec in parts:
 o=rec['object'];clean(o);me=o.data.copy();bm=bmesh.new();bm.from_mesh(me);bmesh.ops.triangulate(bm,faces=bm.faces);bm.to_mesh(me);bm.free();me.calc_loop_triangles()
 ori=rec['orientation'];rot=Matrix.Identity(4)
 if ori=='front_down':rot=Matrix.Rotation(math.pi/2,4,'X')
 elif ori=='back_down':rot=Matrix.Rotation(-math.pi/2,4,'X')
 elif ori=='side_down':rot=Matrix.Rotation(math.pi/2,4,'Y')
 elif ori=='inverted':rot=Matrix.Rotation(math.pi,4,'X')
 ps=[rot@(o.matrix_world@v.co)/M for v in me.vertices];lo=Vector([min(v[i] for v in ps) for i in range(3)]);hi=Vector([max(v[i] for v in ps) for i in range(3)]);shift=Vector(((lo.x+hi.x)/2,(lo.y+hi.y)/2,lo.z))
 path=OUT/'stl-complete'/f'{rec["id"]}__A2__mm.stl';path.parent.mkdir(exist_ok=True)
 with path.open('wb') as f:
  f.write((rec['id']+' | A2 PROTOTYPE | MM | SINGLE PRINT PART').encode().ljust(80,b' '));f.write(struct.pack('<I',len(me.loop_triangles)))
  for tri in me.loop_triangles:
   v=[ps[i]-shift for i in tri.vertices];n=(v[1]-v[0]).cross(v[2]-v[0]).normalized();f.write(struct.pack('<12fH',*n,*v[0],*v[1],*v[2],0))
 bpy.data.meshes.remove(me)
 manifest.append({k:v for k,v in rec.items() if k!='object'}|{'name':o.name,'file':str(path.relative_to(OUT)),'dimensions_mm':[round(x,5) for x in hi-lo],'assembly_bbox_mm':mesh_bounds(o)})
(OUT/'reports/complete-manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2))
(OUT/'reports/leg-interfaces.json').write_text(json.dumps(leg_objects,ensure_ascii=False,indent=2))

# Neutral studio and true mesh renders, with no generated imagery.
def aim(o,p):o.rotation_euler=(Vector(p)*M-o.location).to_track_quat('-Z','Y').to_euler()
def camera(name,loc,target,scale):
 d=bpy.data.cameras.new(name);o=bpy.data.objects.new(name,d);studio.objects.link(o);o.location=Vector(loc)*M;aim(o,target);d.type='ORTHO';d.ortho_scale=scale*M;d.clip_start=.0001;return o
hero=camera('A2_COMPLETE_front_camera',(230,-290,185),(0,17,61),285)
backcam=camera('A2_COMPLETE_rear_camera',(-240,340,185),(0,20,64),295)
internalcam=camera('A2_COMPLETE_internal_camera',(230,-270,260),(0,22,66),285)
for name,loc,en,size in [('key',(-180,-200,320),.66,.22),('fill',(170,-80,240),.28,.2),('rim',(70,200,270),.52,.2)]:
 d=bpy.data.lights.new('A2 COMPLETE '+name,'AREA');d.energy=en;d.size=size;o=bpy.data.objects.new(name,d);studio.objects.link(o);o.location=Vector(loc)*M;aim(o,(0,15,65))
floor=cube('A2_COMPLETE_studio_floor',(1000,1000,2),(0,0,-1),studio,ground)
scene.camera=hero;scene['revision']='A2';scene['part_count']=len(parts)
scene['manufacturing_status']='Complete CAD prototype set; physical fit, strength and module final dimensions unverified'
scene['joint_description']='Each leg: hip X rotation plus knee X rotation; maintain at least three feet down during first bench gait tests'
scene['source_user_scene_preserved']=True
for saved_scene in bpy.data.scenes:saved_scene.use_fake_user=True
bpy.context.window.scene=source;bpy.context.view_layer.update();after=fingerprint(source);assert after==before
(OUT/'reports/complete-preservation.json').write_text(json.dumps({'source_before':before,'source_after':after,'preserved':before==after,'input_a1_sha256':hashlib.sha256((OUT.parent/'print-v2/desktop-assistant-structure-a1.blend').read_bytes()).hexdigest(),'v1_sha256':hashlib.sha256((OUT.parent/'assembly-v1/desktop-assistant-assembly-v1.blend').read_bytes()).hexdigest()},indent=2))
bpy.context.window.scene=scene
for screen in bpy.data.screens:
 for ar in screen.areas:
  if ar.type=='VIEW_3D':
   ar.spaces.active.clip_start=.0001;ar.spaces.active.clip_end=10
   ar.spaces.active.shading.type='SOLID';ar.spaces.active.shading.color_type='MATERIAL'
   ar.spaces.active.region_3d.view_location=Vector((0,15,62))*M;ar.spaces.active.region_3d.view_distance=.36;ar.spaces.active.region_3d.view_rotation=hero.rotation_euler.to_quaternion()
bpy.ops.object.select_all(action='DESELECT');hood.select_set(True);bpy.context.view_layer.objects.active=hood
file=OUT/'DesktopAssistant-整机结构-A2.blend';bpy.ops.wm.save_as_mainfile(filepath=str(file))
print('COMPLETE_A2_SAVED',len(parts),flush=True)
if '--no-render' not in sys.argv:
 scene.render.filepath=str(OUT/'renders/A2-front.png');bpy.ops.render.render(write_still=True)
 scene.camera=backcam;scene.render.filepath=str(OUT/'renders/A2-rear.png');bpy.ops.render.render(write_still=True)
 hood.hide_render=True;front.hide_render=True;scene.camera=internalcam;scene.render.filepath=str(OUT/'renders/A2-internal.png');bpy.ops.render.render(write_still=True)
print('COMPLETE_A2_DONE',flush=True)
