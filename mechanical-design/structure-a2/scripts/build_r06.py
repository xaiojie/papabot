"""New assembled structure study; keeps V1 user scene and six trial coupons.
Every generated geometry is a design draft, not a production release.
Only named structural drafts are exported, in mm, separately from electronics.
"""
import bpy,bmesh,math,json,struct,hashlib,sys
from pathlib import Path
from mathutils import Vector,Matrix
OUT=Path(__file__).resolve().parents[1];M=.001
P=json.loads((OUT.parent/'print-v2/structure-a1-parameters.json').read_text())
bpy.ops.wm.open_mainfile(filepath=str(OUT.parent/'print-v2/desktop-assistant-structure-a1.blend'))
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
scene=bpy.data.scenes.new('01_R06_PART__PRINT_THIS_MESH');bpy.context.window.scene=scene
scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=1;scene.unit_settings.length_unit='MILLIMETERS'
scene.render.engine='CYCLES';scene.cycles.samples=24;scene.cycles.use_denoising=True
scene.render.resolution_x=1500;scene.render.resolution_y=1250;scene.render.resolution_percentage=100;scene.render.image_settings.file_format='PNG'
scene.world=bpy.data.worlds.new('A2 studio');scene.world.use_nodes=True
bg=next((n for n in scene.world.node_tree.nodes if n.type=='BACKGROUND'),None) or scene.world.node_tree.nodes.new('ShaderNodeBackground')
wo=next((n for n in scene.world.node_tree.nodes if n.type=='OUTPUT_WORLD'),None) or scene.world.node_tree.nodes.new('ShaderNodeOutputWorld')
scene.world.node_tree.links.new(bg.outputs[0],wo.inputs[0]);bg.inputs['Color'].default_value=(.78,.84,.8,1);bg.inputs['Strength'].default_value=.4
scene.view_settings.view_transform='AgX'
try:scene.view_settings.look='AgX - Medium High Contrast'
except:pass
def col(name):
 c=bpy.data.collections.new(name);scene.collection.children.link(c);return c
structs=col('A2_R06_PRINT_PART');refs=col('A2_PURCHASED_AND_LEGACY_REFERENCE__NEVER_PRINT');preview=col('A2_UNMEASURED_CONTROL_PREVIEW__NEVER_PRINT');guides=col('A2_VOLUME_RESERVATIONS__NEVER_PRINT');studio=col('A2_STUDIO');labels=col('A2_LABELS__NOT_PRINT')
def lin(x):return x/12.92 if x<=.04045 else ((x+.055)/1.055)**2.4
def material(name,hexcol):
 m=bpy.data.materials.new(name);rgb=tuple(lin(int(hexcol[i:i+2],16)/255) for i in (1,3,5));m.diffuse_color=(*rgb,1);m.use_nodes=True
 bs=next((n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED'),None) or m.node_tree.nodes.new('ShaderNodeBsdfPrincipled')
 mo=next((n for n in m.node_tree.nodes if n.type=='OUTPUT_MATERIAL'),None) or m.node_tree.nodes.new('ShaderNodeOutputMaterial')
 m.node_tree.links.new(bs.outputs[0],mo.inputs[0]);bs.inputs['Base Color'].default_value=(*rgb,1);bs.inputs['Roughness'].default_value=.59;return m
cream=material('A2 cream #EEEADF','#EEEADF');face=material('A2 face #F4F0E8','#F4F0E8');mint=material('A2 mint #9FB9A9','#9FB9A9');black=material('A2 black','#182326');green=material('A2 carrier PCB','#34735E');amber=material('A2 unverified bay','#BC9048');silver=material('A2 hardware','#AAB5B8');ground=material('A2 studio ground','#D4DCD7')
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

# Revision A2, part 1. All dimensions below are millimetres in the existing body datum.
# Exact PCB outline and holes are read from the saved carrier definition. Electronics
# heights not stated in supplier data remain tagged nominal or reserved.
import csv
PROJECT=OUT.parents[1]
PCB_DIR=PROJECT/'pcb-design/native-rev-a'
B=json.loads((PCB_DIR/'carrier-definition.json').read_text())['board']
PAD_ROWS=list(csv.DictReader((PCB_DIR/'载板接口与引脚.csv').open(encoding='utf-8-sig')))
A1=bpy.data.scenes['03_STRUCTURE_A1__DRAFT_NOT_PRINT_RELEASE']
params={
 'revision':'A2-R06','part_id':'R06','label_zh':'主控PCB支撑架','quantity':1,
 'units':'mm','frame_bottom_z':58.6,'frame_top_z':61.0,'pcb_bottom_z':66.0,
 'pcb_thickness':B['thickness_target_mm'],'pcb_transform':'X=u-40; Y=v-2; Z=w+66',
 'pcb_mount_holes_uv':B['mount_holes_mm'],'pcb_outline_uv':B['outline_mm'],
 'feet_xy':P['carrier_foot_xy'],'feet_bottom_z':34.6,
 'frame_outline_xy':[88,40],'frame_opening_xy':[66,22],
 'floor_screw_clearance':3.4,'pcb_screw_clearance':2.4,'bottom_nut_AF':5.8,'pcb_nut_AF':4.3,
 'floor_nut_side_loading_z_range':[36.2,38.9],'floor_nut_load_wall_mm':1.6,
 'pcb_fastener':'4 M2x8, head diameter <=4.0mm, no oversized washers',
 'foot_diameter':8.8,'pcb_seat_diameter':5.6,'pcb_nut_boss_diameter':9.0,
 'pcb_seat_top_z':66.0,'pcb_nut_tunnel_top_z':63.2,
 'socket_plastic_height_verified':8.5,'male_header_spacer_nominal':2.5,
 'controller_bottom_nominal_z':78.6,'controller_size_nominal':[51.66,20.32,1.6],
 'controller_top_component_reserve_z':86.2,
 'battery_target_bbox':[[-37.5,-6,35.6],[37.5,34,55.6]],
 'display_connector_reserve_bbox':[[-38,-20,50],[-28,-3,90]],
 'not_measured':['battery final size','male header spacer and insertion height','received M2 head and nut dimensions','solder tails after trimming','display connector plug and cable bend']}
(OUT/'reports/R06-parameters.json').write_text(json.dumps(params,ensure_ascii=False,indent=2))

def soft(o,width=.6,segments=3):
 mod=o.modifiers.new('Edge radius mm','BEVEL');mod.width=width*M;mod.segments=segments
 bpy.context.view_layer.objects.active=o;bpy.ops.object.modifier_apply(modifier=mod.name);clean(o)
 return o

def joined_box(name,dims,loc,rad=.6):return cube(name,dims,loc)

# A connected three-sided bridge, with a left-side antenna opening and a front
# display cable relief. Four original floor fixing centres remain unchanged.
part=joined_box('R06__PCB_support_bridge_A2',(88,40,2.4),(0,14,59.8),.5)
boolean(part,joined_box('CUT centre',(66,22,12),(0,14,60),1.2))
# Floor nuts slide into side pockets above a 1.6mm load-bearing lower wall.
for x,y in params['feet_xy']:
 boolean(part,joined_box('ADD foot rail',(18,9,2.4),((1 if x>0 else -1)*43,y,59.8),.5),'UNION')
 boolean(part,cyl('ADD floor leg',4.4,25.2,(x,y,47.2),'Z'),'UNION')
 # Corner web connects the tall leg to its top pad without occupying battery width.
 boolean(part,joined_box('ADD web',(5,8,6),(x,y,57.2),.45),'UNION')
 boolean(part,cyl('CUT floor screw',1.7,34,(x,y,48),'Z'))
 hex_hole(part,5.8,2.7,(x,y,37.55),'Z')
 boolean(part,cube('CUT side loading M3 nut',(7,5.8,2.7),(x+(3 if x>0 else -3),y,37.55)))
# Each board fixing point gets a stepped insulating seat. Larger nut bodies are
# below the board; only the Ø5.6 top seat contacts the board underside.
for u,v,diam in B['mount_holes_mm']:
 x,y=u-40,v-2
 boolean(part,cyl('ADD PCB nut boss',4.5,4.0,(x,y,62.0),'Z'),'UNION')
 boolean(part,cyl('ADD PCB contact seat',2.8,2.4,(x,y,64.8),'Z'),'UNION')
 boolean(part,cyl('CUT PCB M2',1.2,13,(x,y,62),'Z'))
 hex_hole(part,4.3,5.0,(x,y,60.7),'Z')
# Apply these after all unions so later pads cannot accidentally fill the cutouts.
boolean(part,cube('CUT antenna no-bridge zone',(55,13,15),(-43.33,14,64)))
boolean(part,cube('CUT display cable corridor',(10,30,50),(-33,-18,70)))
# Tie slots on the right, clear of the RF zone and battery pouch.
for y in [9,19]:boolean(part,cube('CUT wire tie slot',(3.2,2.2,9),(40.0,y,59.8)))
# Two nearby supply/sense pad tails need local clearances in the lower nut bosses.
for row in PAD_ROWS:
 if (row['PCB位号'],row['针号']) in [('J8','2'),('J9','1')]:
  x,y=float(row['焊盘X_mm'])-40,float(row['焊盘Y_mm'])-2
  boolean(part,cyl('CUT nearby solder tail clearance',1.0,6,(x,y,64),'Z'))
clean(part);assign(part,mint)
part['part_id']='R06';part['label_zh']='主控 PCB 支撑架';part['revision']='A2';part['quantity_per_robot']=1
part['status']='CAD_PART_FOR_FIT_TEST__NOT_PHYSICALLY_VALIDATED'
part['mounting']='4 M3x10 floor screws through A2 4.6mm floor; load M3 nuts from outer side pockets. 4 small-head M2x8 PCB screws, head diameter <=4mm without oversized washers; load M2 nuts from underside'
part['material_suggestion']='PETG; supports required below bridge; four perimeters and 0.2mm layers; final fit depends on print process'
part['datum']='Units mm; Z34.6 floor contact, Z66 PCB underside'

# Export a single, independently connected printable mesh in mm. Board side is
# down to keep long legs vertical; support is needed under the shallow bridge.
mesh=part.data.copy();bm=bmesh.new();bm.from_mesh(mesh)
bmesh.ops.triangulate(bm,faces=bm.faces);bm.to_mesh(mesh);bm.free();mesh.calc_loop_triangles()
rot=Matrix.Rotation(math.pi,4,'X')
points=[rot@(part.matrix_world@v.co)/M for v in mesh.vertices]
low=Vector([min(v[i] for v in points) for i in range(3)]);high=Vector([max(v[i] for v in points) for i in range(3)])
shift=Vector(((low.x+high.x)/2,(low.y+high.y)/2,low.z))
stl=OUT/'stl/R06__PCB_support_bridge_A2__mm.stl'
with stl.open('wb') as f:
 f.write(b'R06 PCB SUPPORT A2 | MM | ONE PRINT PART | FIT TEST REQUIRED'.ljust(80,b' '));f.write(struct.pack('<I',len(mesh.loop_triangles)))
 for t in mesh.loop_triangles:
  vs=[points[i]-shift for i in t.vertices];n=(vs[1]-vs[0]).cross(vs[2]-vs[0]).normalized()
  f.write(struct.pack('<12fH',*n,*vs[0],*vs[1],*vs[2],0))
bpy.data.meshes.remove(mesh)
manifest=[{'id':'R06','name':part.name,'label_zh':'主控PCB支撑架','file':str(stl.relative_to(OUT)),
 'quantity':1,'dimensions_mm':[round(x,5) for x in high-low],
 'print_orientation':'PCB contact seats down; support bridge underside, avoid filling hex tunnels',
 'assembly_bbox_mm':mesh_bounds(part),'status':'CAD_PART_FOR_FIT_TEST'}]
(OUT/'reports/export-manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2))

# Dedicated close-up scene and additional, separately selectable fit/assembly views.
def aim(o,p):o.rotation_euler=(Vector(p)*M-o.location).to_track_quat('-Z','Y').to_euler()
def camera(name,loc,target,scale):
 d=bpy.data.cameras.new(name);o=bpy.data.objects.new(name,d);studio.objects.link(o)
 o.location=Vector(loc)*M;aim(o,target);d.type='ORTHO';d.ortho_scale=scale*M;d.clip_start=.0001;d.clip_end=10;return o
hero=camera('R06 Part camera',(140,-170,152),(0,13,50),147)
underside=camera('R06 Underside camera',(-130,-150,-45),(0,13,51),146)
for name,loc,en,size in [('R06 key',(-120,-130,230),.42,.17),('R06 fill',(140,-50,180),.23,.14),('R06 rim',(60,160,190),.42,.15)]:
 d=bpy.data.lights.new(name,'AREA');d.energy=en;d.size=size;o=bpy.data.objects.new(name,d);studio.objects.link(o);o.location=Vector(loc)*M;aim(o,(0,12,50))
scene.camera=hero
floor=cube('STUDIO floor',(650,650,2),(0,0,32.4),studio,ground)
# Three scenes share this exact part datablock. No electronics are in the STL.
fit=scene.copy();fit.name='02_R06_FIT__PCB_BATTERY_FLOOR'
fitrefs=bpy.data.collections.new('R06_FIT_REFERENCES__DO_NOT_PRINT');fit.collection.children.link(fitrefs)
bpy.context.window.scene=fit

def prism_xy(name,poly,z0,z1,c=fitrefs,mat=green):
 xy=poly[:-1] if poly[0]==poly[-1] else poly
 n=len(xy);verts=[((u-40)*M,(v-2)*M,z*M) for z in [z0,z1] for u,v in xy]
 fs=[tuple(reversed(range(n))),tuple(range(n,2*n))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
 me=bpy.data.meshes.new(name);me.from_pydata(verts,[],fs);me.update();o=bpy.data.objects.new(name,me);c.objects.link(o);clean(o);assign(o,mat);return o
pcb=prism_xy('REF_PCB_80x32__EXACT_NATIVE_OUTLINE',B['outline_mm'],66,67.6)
for u,v,d in B['mount_holes_mm']:boolean(pcb,cyl('CUT PCB fixing',d/2,5,(u-40,v-2,66.8)))
for u,v,d in B['mount_holes_mm']:
 head=cyl('REF_FASTENER_M2_HEAD_MAX_D4',2.0,2.0,(u-40,v-2,68.6),'Z',c=fitrefs)
 assign(head,silver);head['status']='Selected maximum head envelope; purchase and measure M2x8 head diameter <=4.0mm'
pcb['basis']='pcb-design/native-rev-a/carrier-definition.json: board.outline_mm and mount_holes_mm'
pcb['never_print']=True
pads_by_ref={}
for row in PAD_ROWS:pads_by_ref.setdefault(row['PCB位号'],[]).append(row)
for ref,rows in pads_by_ref.items():
 xy=[(float(r['焊盘X_mm'])-40,float(r['焊盘Y_mm'])-2) for r in rows]
 if ref in ['J1','J2']:
  o=cube('REF_'+ref+'_C429947_socket_H8p5',(50.8,2.54,8.5),(0,xy[0][1],71.85),fitrefs,black)
  o['height_source']='C429947 / JILN 22850120ANG1SYA01, plastic H8.5'
  spacer=cube('REF_'+ref+'_male_header_spacer_NOMINAL',(50.8,2.54,2.5),(0,xy[0][1],77.35),fitrefs,black)
  spacer['dimension_status']='Nominal 2.5mm spacer plus fully seated pins; measure physical stack'
 elif ref.startswith('J') and len(rows)>=2:
  cx=(min(x for x,y in xy)+max(x for x,y in xy))/2;cy=(min(y for x,y in xy)+max(y for x,y in xy))/2
  size=(max(x for x,y in xy)-min(x for x,y in xy)+2.54,max(y for x,y in xy)-min(y for x,y in xy)+2.54,2.5)
  cube('REF_'+ref+'_pin_header_body_NOMINAL',size,(cx,cy,68.85),fitrefs,black)
 for (x,y),row in zip(xy,rows):
  pad=cyl('REF_PAD_'+ref+'_'+row['针号'],.8,.15,(x,y,67.68),c=fitrefs,n=24);assign(pad,silver)
  # Model the maximum allowed trimmed tails below the PCB for clearance checks.
  lead=cyl('REF_LEAD_'+ref+'_'+row['针号'],.4,3.0,(x,y,64.5),c=fitrefs,n=12);assign(lead,silver)
  lead['status']='Solder tail length target 3.0 max; trim and verify actual solder fillet'
mcu=cube('REF_LCKFB_51p66x20p32__PCB_NOMINAL',(51.66,20.32,1.6),(0,14,79.4),fitrefs,green)
usb=cube('REF_USB_CONNECTOR__RIGHT',(7.5,9,3.4),(23.5,14,81.9),fitrefs,silver)
chip=cube('REF_MCU_COMPONENTS__HEIGHT_RESERVATION',(25,17,6),(4,14,83.2),fitrefs,black)
chip['status']='Conservative component envelope, not exact individual component geometry'
antenna=cube('REF_ANTENNA_REGION_NOMINAL',(9.0,17,.12),(-20.5,14,80.26),fitrefs,black)
# Existing lower cover retained as a reference to prove mounting alignment.
base=dup_mesh(bpy.data.objects['R05__bottom_cover_integrated_battery_tray'],'REF_R05_EXISTING_BOTTOM_AND_BATTERY_TRAY',fitrefs)
assign(base,cream);base['status']='Existing A1 part, unchanged'
battery=cube('REF_BATTERY_75x40x20__SUPPLIER_TARGET',(75,40,20),(0,14,45.6),fitrefs,black)
battery['status']='Target envelope only; supplier final dimensions pending'
# Belt model only follows known target perimeter, with a conservative top thickness.
belt=cube('REF_BATTERY_STRAP_TOP_1mm',(10,40,1),(0,14,56.1),fitrefs,amber)
belt['status']='1mm thickness reservation, not measured'
fitcam=camera('R06 Assembly camera',(140,-155,145),(0,12,60),160);fit.camera=fitcam
# Also preserve a full-body context scene, with new R06 replacing only old R06.
assembly=A1.copy();assembly.name='03_A2_ROBOT_CONTEXT__OTHER_PARTS_A1'
# copy() shares child collections, so unlink old structural collection only in new scene
# and replace with a dedicated collection containing the existing objects except R06.
for c in list(assembly.collection.children):
 if c.name.startswith('A1_STRUCTURAL'):
  replacement=bpy.data.collections.new('A2_CONTEXT_EXISTING_A1_PARTS');assembly.collection.children.link(replacement)
  for o in c.objects:
   if not o.name.startswith('R06__'):replacement.objects.link(o)
  assembly.collection.children.unlink(c)
assembly.collection.children.link(structs)
assembly['status']='R06 updated; all other components A1 references awaiting individual redesign'
# Hide legacy carrier/MCU envelopes per scene by using replacement collection.
for c in list(assembly.collection.children):
 if c.name.startswith('A1_PURCHASED'):
  cc=bpy.data.collections.new('A2_CONTEXT_LEGACY_REF');assembly.collection.children.link(cc)
  for o in c.objects:
   if not o.name.startswith(('ENV_A1__carrier_PCB','ENV_A1__2x20','ENV_A1__LCKFB')):cc.objects.link(o)
  assembly.collection.children.unlink(c)
cc=bpy.data.collections.new('A2_CONTEXT_CURRENT_PCB_REF');assembly.collection.children.link(cc)
for o in fitrefs.objects:
 if o.name.startswith(('REF_PCB','REF_J','REF_LCKFB','REF_USB','REF_MCU','REF_ANTENNA','REF_PAD','REF_LEAD')):cc.objects.link(o)

# Explicit engineering checks, separate from the print mesh topology validator.
def intersection_volume(a,b):
 cp=dup_mesh(a,'CHECK_TMP',fitrefs)
 mod=cp.modifiers.new('CHECK intersection','BOOLEAN');mod.operation='INTERSECT';mod.solver='EXACT';mod.object=b
 bpy.context.view_layer.objects.active=cp;bpy.ops.object.modifier_apply(modifier=mod.name)
 bm=bmesh.new();bm.from_mesh(cp.data);bm.transform(cp.matrix_world);v=abs(bm.calc_volume(signed=True))/(M**3);bm.free();bpy.data.objects.remove(cp,do_unlink=True)
 return v
bpy.context.window.scene=fit;bpy.context.view_layer.update()
collisions=[]
for o in [pcb,base,battery,belt,mcu]+[o for o in fitrefs.objects if o.name.startswith('REF_LEAD')]:
 vol=intersection_volume(part,o)
 if vol>.001:collisions.append({'reference':o.name,'intersection_volume_mm3':round(vol,6)})
checks={
 'pcb_outline_source':str(PCB_DIR/'carrier-definition.json'),
 'pcb_mount_centres_match_native':len(B['mount_holes_mm'])==4 and [q[:2] for q in B['mount_holes_mm']]==P['pcb_holes_uv'],
 'base_mount_centres_unchanged':params['feet_xy']==P['carrier_foot_xy'],
 'frame_to_battery_top_gap_mm':3.0,'frame_to_strap_top_gap_mm':2.0,
 'frame_to_3mm_solder_tail_gap_mm':2.0,
 'pcb_support_contact_diameter_mm':5.6,
 'checked_solder_tails':sum(o.name.startswith('REF_LEAD') for o in fitrefs.objects),
 'solid_intersections_above_0p001_mm3':collisions,
 'physical_fit_tested':False,'slicer_tested':False,
 'limits':['Battery envelope is the supplier target, not a received pack.','No RF/thermal/load test.','Female header plastic height known; male spacer/stack insertion not measured.','Current R01 shell USB opening is an old left-side proposal and must be revised to match the right-side controller USB.']}
checks['cad_checks_pass']=checks['pcb_mount_centres_match_native'] and checks['base_mount_centres_unchanged'] and not collisions
(OUT/'reports/R06-clearance-checks.json').write_text(json.dumps(checks,ensure_ascii=False,indent=2))
print('R06_CLEARANCE',json.dumps(checks,ensure_ascii=False),flush=True)

# Record actual geometry, original-file preservation, and all editable scene names.
bpy.context.window.scene=source;bpy.context.view_layer.update();after=fingerprint(source);assert after==before
bpy.context.window.scene=scene
preservation={'source_scene_before':before,'source_scene_after':after,'source_preserved':before==after,
 'original_v1_sha256':hashlib.sha256((OUT.parent/'assembly-v1/desktop-assistant-assembly-v1.blend').read_bytes()).hexdigest(),
 'input_a1_sha256':hashlib.sha256((OUT.parent/'print-v2/desktop-assistant-structure-a1.blend').read_bytes()).hexdigest()}
(OUT/'reports/R06-preservation.json').write_text(json.dumps(preservation,indent=2))
# Focus viewport on printable part with references available in scene selector.
for screen in bpy.data.screens:
 for ar in screen.areas:
  if ar.type=='VIEW_3D':
   sp=ar.spaces.active;sp.clip_start=.0001;sp.clip_end=100;sp.shading.type='SOLID';sp.shading.color_type='MATERIAL';sp.shading.light='STUDIO';sp.overlay.show_floor=False
   sp.region_3d.view_perspective='PERSP';sp.region_3d.view_location=Vector((0,14,50))*M
   sp.region_3d.view_distance=.19;sp.region_3d.view_rotation=hero.rotation_euler.to_quaternion()
bpy.ops.object.select_all(action='DESELECT');part.select_set(True);bpy.context.view_layer.objects.active=part
scene['part_review']='R06 only. Scene 02 shows actual PCB, target battery and existing floor; scene 03 full-body context.'
for preserved_scene in bpy.data.scenes: preserved_scene.use_fake_user=True
filepath=OUT/'R06-PCB支撑架-A2.blend'
bpy.ops.wm.save_as_mainfile(filepath=str(filepath))
if '--no-render' not in sys.argv:
 scene.render.filepath=str(OUT/'renders/R06-part.png');bpy.ops.render.render(write_still=True)
 # Underside view hides studio floor temporarily, and is not saved over default view.
 scene.camera=underside;floor.hide_render=True;scene.render.filepath=str(OUT/'renders/R06-underside.png');bpy.ops.render.render(write_still=True)
 floor.hide_render=False;scene.camera=hero
 bpy.context.window.scene=fit;fit.render.filepath=str(OUT/'renders/R06-pcb-and-battery.png');bpy.ops.render.render(write_still=True)
 bpy.context.window.scene=scene
print('R06_DONE',filepath,flush=True)
