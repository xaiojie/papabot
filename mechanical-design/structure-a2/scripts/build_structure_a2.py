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
scene=bpy.data.scenes.new('04_STRUCTURE_A2__ASSEMBLY_AND_PRINT_PARTS');bpy.context.window.scene=scene
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
structs=col('A2_STRUCTURAL_DRAFTS__EXPORT_WHITELIST');refs=col('A2_PURCHASED_AND_LEGACY_REFERENCE__NEVER_PRINT');preview=col('A2_UNMEASURED_CONTROL_PREVIEW__NEVER_PRINT');guides=col('A2_VOLUME_RESERVATIONS__NEVER_PRINT');studio=col('A2_STUDIO');labels=col('A2_LABELS__NOT_PRINT')
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
