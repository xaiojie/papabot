"""New assembled structure study; keeps V1 user scene and six trial coupons.
Every generated geometry is a design draft, not a production release.
Only named structural drafts are exported, in mm, separately from electronics.
"""
import bpy,bmesh,math,json,struct,hashlib,sys
from pathlib import Path
from mathutils import Vector,Matrix
OUT=Path(__file__).resolve().parents[1];M=.001
P=json.loads((OUT/'structure-a1-parameters.json').read_text())
bpy.ops.wm.open_mainfile(filepath=str(OUT/'desktop-assistant-print-v2.blend'))
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
scene=bpy.data.scenes.new('03_STRUCTURE_A1__DRAFT_NOT_PRINT_RELEASE');bpy.context.window.scene=scene
scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=1;scene.unit_settings.length_unit='MILLIMETERS'
scene.render.engine='CYCLES';scene.cycles.samples=36;scene.cycles.use_denoising=True
scene.render.resolution_x=1600;scene.render.resolution_y=1400;scene.render.resolution_percentage=100;scene.render.image_settings.file_format='PNG'
scene.world=bpy.data.worlds.new('A1 studio');scene.world.use_nodes=True
bg=next((n for n in scene.world.node_tree.nodes if n.type=='BACKGROUND'),None) or scene.world.node_tree.nodes.new('ShaderNodeBackground')
wo=next((n for n in scene.world.node_tree.nodes if n.type=='OUTPUT_WORLD'),None) or scene.world.node_tree.nodes.new('ShaderNodeOutputWorld')
scene.world.node_tree.links.new(bg.outputs[0],wo.inputs[0]);bg.inputs['Color'].default_value=(.78,.84,.8,1);bg.inputs['Strength'].default_value=.4
scene.view_settings.view_transform='AgX'
try:scene.view_settings.look='AgX - Medium High Contrast'
except:pass
def col(name):
 c=bpy.data.collections.new(name);scene.collection.children.link(c);return c
structs=col('A1_STRUCTURAL_DRAFTS__EXPORT_WHITELIST');refs=col('A1_PURCHASED_AND_LEGACY_REFERENCE__NEVER_PRINT');preview=col('A1_UNMEASURED_CONTROL_PREVIEW__NEVER_PRINT');guides=col('A1_VOLUME_RESERVATIONS__NEVER_PRINT');studio=col('A1_STUDIO');labels=col('A1_LABELS__NOT_PRINT')
def lin(x):return x/12.92 if x<=.04045 else ((x+.055)/1.055)**2.4
def material(name,hexcol):
 m=bpy.data.materials.new(name);rgb=tuple(lin(int(hexcol[i:i+2],16)/255) for i in (1,3,5));m.diffuse_color=(*rgb,1);m.use_nodes=True
 bs=next((n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED'),None) or m.node_tree.nodes.new('ShaderNodeBsdfPrincipled')
 mo=next((n for n in m.node_tree.nodes if n.type=='OUTPUT_MATERIAL'),None) or m.node_tree.nodes.new('ShaderNodeOutputMaterial')
 m.node_tree.links.new(bs.outputs[0],mo.inputs[0]);bs.inputs['Base Color'].default_value=(*rgb,1);bs.inputs['Roughness'].default_value=.59;return m
cream=material('A1 cream #EEEADF','#EEEADF');face=material('A1 face #F4F0E8','#F4F0E8');mint=material('A1 mint #9FB9A9','#9FB9A9');black=material('A1 black','#182326');green=material('A1 carrier PCB','#34735E');amber=material('A1 unverified bay','#BC9048');silver=material('A1 hardware','#AAB5B8');ground=material('A1 studio ground','#D4DCD7')
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
 mod=o.modifiers.new('Dimensioned '+op,'BOOLEAN');mod.solver='EXACT';mod.operation=op;mod.object=c
 bpy.context.view_layer.objects.active=o;bpy.ops.object.modifier_apply(modifier=mod.name);bpy.data.objects.remove(c,do_unlink=True)
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
 bm=bmesh.new();bm.from_mesh(o.data);bmesh.ops.remove_doubles(bm,verts=bm.verts,dist=1e-8);bmesh.ops.recalc_face_normals(bm,faces=bm.faces);bm.to_mesh(o.data);bm.free();o.data.update()
def ring(name,outer,inner,c=structs):
 o=loft(name,outer,c);boolean(o,loft('CUT hollow',inner));return o
def hex_hole(o,af,depth,loc,axis='Y'):boolean(o,cyl('CUT nut access',af/math.sqrt(3),depth,loc,axis,n=6))
def dup_mesh(o,name,c):
 cp=o.copy();cp.data=o.data.copy();cp.name=name;cp.animation_data_clear();cp.parent=None;cp.matrix_world=o.matrix_world.copy();c.objects.link(cp);return cp
def mesh_bounds(o):
 vs=[o.matrix_world@v.co/M for v in o.data.vertices];return [min(v[i] for v in vs) for i in range(3)],[max(v[i] for v in vs) for i in range(3)]
manifest=[]
def export(o,id,description,print_axis,limitations,default=True):
 clean(o);o['part_id']=id;o['status']='STRUCTURAL_DRAFT__NOT_FROZEN';o['label_zh']=description;o['limitations']=limitations
 outdir=OUT/'stl-structure-a1-DRAFT';outdir.mkdir(exist_ok=True)
 me=o.data.copy();bm=bmesh.new();bm.from_mesh(me);bmesh.ops.triangulate(bm,faces=bm.faces);bm.to_mesh(me);bm.free();me.calc_loop_triangles()
 # Rotation from world assembly axes into a simple flat-on-bed trial orientation.
 rot=Matrix.Rotation(math.pi/2,4,'X') if print_axis=='front_down' else (Matrix.Rotation(-math.pi/2,4,'X') if print_axis=='back_down' else Matrix.Identity(4))
 ps=[rot@(o.matrix_world@v.co)/M for v in me.vertices];lo=Vector([min(v[i] for v in ps) for i in range(3)]);hi=Vector([max(v[i] for v in ps) for i in range(3)]);shift=Vector(((lo.x+hi.x)/2,(lo.y+hi.y)/2,lo.z))
 fn=outdir/f'{id}__{o.name.split("__",1)[1]}__DRAFT_mm.stl'
 with fn.open('wb') as f:
  f.write((f'{id} DESIGN DRAFT NOT FROZEN | UNITS MM'.encode()+b' '*80)[:80]);f.write(struct.pack('<I',len(me.loop_triangles)))
  for tr in me.loop_triangles:
   v=[ps[i]-shift for i in tr.vertices];no=(v[1]-v[0]).cross(v[2]-v[0]).normalized();f.write(struct.pack('<12fH',*no,*v[0],*v[1],*v[2],0))
 bpy.data.meshes.remove(me)
 alo,ahi=mesh_bounds(o)
 manifest.append({'id':id,'name':o.name,'label_zh':description,'file':str(fn.relative_to(OUT)),'quantity_trial':1,'dimensions_mm':[round(t,5) for t in hi-lo],'assembly_bbox_min_mm':alo,'assembly_bbox_max_mm':ahi,'print_orientation':print_axis,'status':'STRUCTURAL_DRAFT_NOT_FROZEN','default_variant':default,'limitations':limitations})

# Closed shell geometry; front, bottom and rear maintenance opening are designed cuts.
outer=[(-23.5,124,76,14,0,68),(38,124,76,14,0,68),(45,116,70,11,0,68)]
hood=ring('R01__main_housing',outer,[(-25,119.2,71.2,11.6,0,68),(37,119.2,71.2,11.6,0,68),(42.6,111.2,65.2,8.6,0,68)])
boolean(hood,cube('CUT bottom service',(115,66,22),(0,9.5,23.6)))
boolean(hood,loft('CUT rear panel opening',[(40,82,42,5,0,74),(49,82,42,5,0,74)]))
for x,z in P['front_fastener_xz']:
 boolean(hood,cyl('ADD front boss',4.5,6,(x,-20.5,z),'Y'),'UNION')
 boolean(hood,cube('ADD front boss arm',(14,6,8),((1 if x>0 else -1)*55,-20.5,z)),'UNION')
for x,z in P['rear_fastener_xz']:boolean(hood,cyl('ADD rear boss',4.5,8,(x,41,z),'Y'),'UNION')
for x,z in P['display_tab_fastener_xz']:
 boolean(hood,cyl('ADD display-tab M2 boss',4,4,(x,-11.5,z),'Y'),'UNION')
 boolean(hood,cube('ADD display-tab boss arm',(22,4,8),((1 if x>0 else -1)*53,-11.5,z)),'UNION')
for x,y in P['base_fastener_xy']:
 boolean(hood,cube('ADD base boss',(12,10,7),(x,y,38.1)),'UNION')
 boolean(hood,cube('ADD base arm',(12,10,5),((1 if x>0 else -1)*55,y,38.1)),'UNION')
# Clip the added pads to the parent exterior; no tabs protrude through the rounded surface.
boolean(hood,loft('CUT exterior envelope',outer),'INTERSECT')
boolean(hood,cube('CUT final bottom service',(115,66,22),(0,9.5,23.6)))
for x,z in P['front_fastener_xz']:
 boolean(hood,cyl('CUT front screw',1.65,16,(x,-20,z),'Y'));hex_hole(hood,5.7,6.1,(x,-18.05,z))
for x,z in P['rear_fastener_xz']:
 boolean(hood,cyl('CUT rear screw',1.65,16,(x,42,z),'Y'));hex_hole(hood,5.7,8.6,(x,38.3,z))
for x,z in P['display_tab_fastener_xz']:
 boolean(hood,cyl('CUT display-tab M2 screw',1.2,10,(x,-11.5,z),'Y'));hex_hole(hood,4.2,4.5,(x,-10.25,z))
for x,y in P['base_fastener_xy']:
 boolean(hood,cyl('CUT base screw',1.65,16,(x,y,37),'Z'));hex_hole(hood,5.7,7,(x,y,40.7),'Z')
# Ears retain old user geometry. Side windows are service/route proposals, not MG90S mount holes.
for x in [-36,36]:boolean(hood,cyl('CUT retained ear key',2.7,12,(x,-1,105),'Z'))
boolean(hood,cube('CUT side USB service window',(12,30,18),(-61,14,79)))
for sign in [-1,1]:
 for y in [-18,22]:boolean(hood,cube('CUT servo cable pass',(12,8,5),(sign*61,y,47)))
assign(hood,cream)

front=loft('R02__shallow_front_cover',[(-26.2,124,76,14,0,68),(-23.8,124,76,14,0,68)])
boolean(front,loft('CUT glass frame clearance',[(-28,60,43,1.4,0,68),(-20,60,43,1.4,0,68)]))
lip=ring('ADD front location lip',[(-23.9,118.7,70.7,11.35,0,68),(-21.8,118.7,70.7,11.35,0,68)],[(-24.2,115.5,67.5,9.75,0,68),(-21.5,115.5,67.5,9.75,0,68)])
for x,z in P['front_fastener_xz']:boolean(lip,cube('CUT boss lip relief',(18,5,13),(x,-22,z)))
boolean(front,lip,'UNION')
for x,z in P['front_fastener_xz']:boolean(front,cyl('CUT face screw',1.65,10,(x,-24,z),'Y'))
assign(front,face)

# Full PCB retained. The frame only touches mounting corners; back-side clearances are provisional.
display=ring('R04__display_support_frame',[(-17.8,99,50,3,8.5,68),(-13.8,99,50,3,8.5,68)],[(-20,77,28,1,10.5,68),(-12,77,28,1,10.5,68)])
boolean(display,cube('CUT header relief',(7,10,34),(-33,-15,68)))
for x,z in P['screen_hole_xz']:
 boolean(display,cyl('ADD display mounting spacer',4.1,1.9,(x,-18.45,z),'Y'),'UNION')
 boolean(display,cyl('CUT display screw',1.6,12,(x,-17,z),'Y'));hex_hole(display,5.7,3.1,(x,-14.85,z))
# Tabs reach front-hood fastener regions but use distinct small M2 attachments.
for x,z in P['display_tab_fastener_xz']:
 boolean(display,cube('ADD display tab',(11,2.2,10),(x,-14.9,z)),'UNION')
 boolean(display,cyl('CUT display tab M2',1.2,10,(x,-15.8,z),'Y'))
assign(display,cream)

rear=loft('R03__rear_controls_panel_BLANK',[ (45.2,98,58,8,0,74),(47.6,98,58,8,0,74)])
for x,z in P['rear_fastener_xz']:boolean(rear,cyl('CUT rear panel screw',1.65,8,(x,46,z),'Y'))
for x in [-8,-4,0,4,8]:
 for z in [-8,-4,0,4,8]:
  if x*x+z*z<=81:boolean(rear,cyl('CUT speaker grille',.9,8,(-25+x,46,81+z),'Y',n=32))
assign(rear,face)
rear_view=dup_mesh(rear,'VIEW_ONLY__rear_panel_UNMEASURED_control_holes',preview)
boolean(rear_view,cyl('CUT EC11 preview hole',3.6,8,(28,46,86),'Y'))
boolean(rear_view,cyl('CUT button preview hole',3.5,8,(28,46,62),'Y'))
rear_view['status']='VIEW_ONLY_UNMEASURED_HOLES__NOT_EXPORTED';rear.hide_render=True;rear.hide_set(True)

# Low battery position; bottom plate is also the battery tray, avoiding an extra fastener stack.
base=cube('R05__bottom_cover_integrated_battery_tray',(110,62.7,2.8),(0,9.85,33.2))
rim=cube('ADD battery low rim',(83.8,48.8,4.2),(0,14,36.5))
boolean(rim,cube('CUT battery target clearance',(79,44,6),(0,14,37)))
boolean(rim,cube('CUT right lead relief',(8,16,6),(41,14,37)))
boolean(base,rim,'UNION')
for x,y in P['base_fastener_xy']+P['carrier_foot_xy']:boolean(base,cyl('CUT bottom mounting',1.65,9,(x,y,33),'Z'))
for x,y in P['battery_strap_slot_centers_xy']:boolean(base,cube('CUT strap opening',(11,2.2,9),(x,y,33)))
assign(base,cream)

carrier=cube('R06__controller_carrier_bridge',(88,40,2.4),(0,14,60.8))
boolean(carrier,cube('CUT carrier centre',(66,20,8),(0,14,61)))
for x,y in P['carrier_foot_xy']:
 boolean(carrier,cube('ADD bridge leg top',(14,10,2.6),(x,y,60.8)),'UNION')
 boolean(carrier,cyl('ADD leg',4,27.4,(x,y,48.3)),'UNION')
 boolean(carrier,cyl('CUT leg screw channel',1.65,34,(x,y,49),'Z'));hex_hole(carrier,5.7,2.7,(x,y,35.85),'Z')
for u,v in P['pcb_holes_uv']:
 x,y=u-40,v-2
 boolean(carrier,cyl('ADD board contact post',4.1,2.2,(x,y,62.9),'Z'),'UNION')
 boolean(carrier,cyl('CUT board screw',1.65,12,(x,y,62),'Z'));hex_hole(carrier,5.7,3.3,(x,y,60.65),'Z')
assign(carrier,mint)
trim=ring('COSMETIC_ONLY__mint_painted_front_band',[(-26.25,122,74,13,0,68),(-26.15,122,74,13,0,68)],[(-26.4,119.6,71.6,11.8,0,68),(-26.0,119.6,71.6,11.8,0,68)],refs)
assign(trim,mint);trim['status']='PAINT_MASK_REFERENCE__NOT_SEPARATE_PRINT_PART'

# Preserve old display and external appearance objects as explicit non-print reference.
for o in source.objects:
 copy_it=(o.name.startswith(('D001','D002','D003','D004','D012','D013','LCD_','Display_','P008','P009','P011','P012','P013','P014','S_','H_','F_')))
 if not copy_it or o.type not in ['MESH','CURVE','FONT']:continue
 cp=dup_mesh(o,'REF_A1__'+o.name,refs);cp['status']='REFERENCE_ONLY__NOT_EXPORTED'
 if o.name.startswith(('P011','P012','P013','P014','S_','H_','F_')):
  cp.location.x += (1 if cp.matrix_world.translation.x>0 else -1)*5*M
  cp['dimension_status']='legacy_servo_leg_envelope__not_actual_mount_geometry'

# Rear controls use original envelope dimensions, relocated only for layout visualization.
def relocate_control(prefixes,old_anchor,new_anchor):
 R=Matrix.Rotation(math.pi,4,'Z');A=Matrix.Translation(Vector(new_anchor)*M)@R@Matrix.Translation(-Vector(old_anchor)*M)
 for o in source.objects:
  if o.name.startswith(prefixes):
   cp=dup_mesh(o,'UNMEASURED_REAR__'+o.name,preview);cp.matrix_world=A@o.matrix_world;cp['status']='RELOCATED_ENVELOPE_ONLY__DESOLDERING_NOT_DONE'
relocate_control(('D005','D006','D007','D008','D009'),(43.5,-21,78.5),(28,39,86))
relocate_control(('D010','D011'),(43.5,-21,55.8),(28,40,62))

battery=cube('ENV_A1__battery_TARGET_75x40x20',(75,40,20),(0,14,45.6),refs,black);battery['dimension_status']='custom supplier target only, not confirmed'
pcb=cube('ENV_A1__carrier_PCB_PROPOSAL',(80,32,1.6),(0,14,64.8),refs,green)
for u,v in P['pcb_holes_uv']:boolean(pcb,cyl('CUT PCB hole',1.6,5,(u-40,v-2,64.8),'Z'))
for y in [14-8.89,14+8.89]:cube('ENV_A1__2x20_socket_8p5_ASSUMED',(50.5,2.54,8.5),(0,y,69.85),refs,black)
mcu=cube('ENV_A1__LCKFB_board_NOMINAL',(51.66,20.32,1.6),(0,14,74.9),refs,green)
cube('ENV_A1__MCU_components_KEEPOUT',(48,18,6),(0,14,78.7),guides,amber)
cube('ENV_A1__USB_service_KEEPOUT',(39,28,16),(-43,14,78),guides,amber)
cube('ENV_A1__DFR0753_ADJUSTABLE_BAY_NOT_DIMENSION',(50,30,15),(-27,18,92.5),guides,amber)
cube('ENV_A1__Hobbywing_OFFICIAL_BODY_43x17x7',(43,17,7),(26,21,90),guides,amber)
cube('ENV_A1__PCA9685_UNMEASURED_VERTICAL_BAY',(62,10,25),(0,-5,89.5),guides,amber)
cube('ENV_A1__microphone_UNMEASURED_GENERIC_BAY',(22,18,12),(47,0,89),guides,amber)
cube('ENV_A1__audio_amp_UNMEASURED_BAY',(22,20,10),(47,18,76),guides,amber)
cube('ENV_A1__charger_UNMEASURED_BAY',(28,10,25),(5,37.5,69),guides,amber)
cube('ENV_A1__XT30_wire_service_BAY',(18,28,18),(48,14,45),guides,amber)
for o in guides.objects:o.display_type='WIRE';o.hide_render=True;o['status']='RESERVATION_ONLY__NOT_VALIDATED_PRODUCT_DIMENSIONS'

for x,z in P['front_fastener_xz']:
 screw=cyl('REF_A1__front_M3_head',2.8,1.6,(x,-27,z),'Y',c=refs);assign(screw,silver)
for x,z in P['rear_fastener_xz']:
 screw=cyl('REF_A1__rear_M3_head',2.8,1.6,(x,48.4,z),'Y',c=refs);assign(screw,silver)

# Export only structural parts. The rear panel is the blank-control variant.
export(hood,'R01','主壳草稿：开放前/底维修口','front_down','Rear control/module positions, servo attachment loads and print supports unverified. Service windows are adjustable, not dimensioned connector seats.')
export(front,'R02','浅前盖试配草稿','front_down','Glass clearance opening 60x43 is a provisional envelope, not measured active area; 0.79mm recess follows old modeled glass.')
export(rear,'R03','可拆后面板：控件区域留白','front_down','EC11/K0/charging/master-switch holes intentionally not exported; speaker grille only. Hole locations must follow physical parts.')
export(display,'R04','整块显示板支架试配草稿','back_down','Board hole pitch nominal only; 1.6mm corner separation and header slot need measurement. Four M2 tabs are design interfaces, not measured hardware holes.')
export(base,'R05','底盖与电池限位框一体草稿','Z','75x40x20 battery target unconfirmed; 1mm EVA and belt route under base proposed. No battery compression fit.')
export(carrier,'R06','主控载板桥架草稿','Z','80x32 PCB and Z64 underside not frozen. Legs/nut pockets and supports need slicer/fit checks; upper electronics not fully allocated.')

def aim(o,p):o.rotation_euler=(Vector(p)*M-o.location).to_track_quat('-Z','Y').to_euler()
floor=cube('A1 studio ground',(900,900,2),(0,0,-1),studio,ground)
for name,loc,en,size in [('A1 key',(-160,-180,300),.55,.2),('A1 fill',(150,-80,220),.22,.18),('A1 rim',(80,170,270),.45,.17)]:
 d=bpy.data.lights.new(name,'AREA');d.energy=en;d.size=size;o=bpy.data.objects.new(name,d);studio.objects.link(o);o.location=Vector(loc)*M;aim(o,(0,5,65))
def camera(name,loc,target,scale):
 d=bpy.data.cameras.new(name);o=bpy.data.objects.new(name,d);studio.objects.link(o);o.location=Vector(loc)*M;aim(o,target);d.type='ORTHO';d.ortho_scale=scale*M;return o
hero=camera('A1 camera hero',(220,-290,180),(0,5,61),260)
backcam=camera('A1 camera rear',(-220,310,180),(0,10,62),260)
explcam=camera('A1 camera exploded',(250,-320,230),(0,2,73),360)
scene.camera=hero;scene['status']='STRUCTURAL_DRAFT_NOT_FROZEN__NO_FULL_MANUFACTURING_RELEASE';scene['source_original_preserved']=True
for screen in bpy.data.screens:
 for ar in screen.areas:
  if ar.type=='VIEW_3D':ar.spaces.active.region_3d.view_perspective='CAMERA'
bpy.ops.object.select_all(action='DESELECT');hood.select_set(True);bpy.context.view_layer.objects.active=hood
(OUT/'reports/structure-a1-manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2))
bpy.context.window.scene=source;bpy.context.view_layer.update();after=fingerprint(source);assert after==before
bpy.context.window.scene=scene
(OUT/'reports/structure-a1-preservation.json').write_text(json.dumps({'source_before':before,'source_after':after,'original_scene_preserved':before==after,'original_file_sha256':hashlib.sha256((OUT.parent/'assembly-v1/desktop-assistant-assembly-v1.blend').read_bytes()).hexdigest()},indent=2))
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'desktop-assistant-structure-a1.blend'))
if '--no-render' in sys.argv:
 print('STRUCTURE_A1_SAVED_NO_RENDER',len(manifest));sys.exit(0)
scene.render.filepath=str(OUT/'renders/structure-a1-front.png');bpy.ops.render.render(write_still=True)
scene.camera=backcam;scene.render.filepath=str(OUT/'renders/structure-a1-rear.png');bpy.ops.render.render(write_still=True)
# Exploded state rendered separately; final saved scene stays assembled.
hood.hide_render=True;front.location.y-=48*M;display.location.y-=18*M;rear_view.location.y+=38*M;base.location.z-=15*M;carrier.location.z+=35*M
for o in preview.objects:
 if o!=rear_view:o.location.y+=38*M
for o in refs.objects:
 if 'front_M3' in o.name:o.location.y-=48*M
 if 'rear_M3' in o.name:o.location.y+=38*M
 if o.name.startswith(('ENV_A1__carrier_PCB','ENV_A1__2x20','ENV_A1__LCKFB')):o.location.z+=35*M
scene.camera=explcam;scene.render.filepath=str(OUT/'renders/structure-a1-internal-study.png');bpy.ops.render.render(write_still=True)
print('STRUCTURE_A1_DONE',len(manifest))
