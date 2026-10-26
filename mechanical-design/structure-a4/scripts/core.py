import bpy,bmesh,math,json,struct,hashlib,sys,csv,itertools
from pathlib import Path
from mathutils import Vector,Matrix
OUT=Path(__file__).resolve().parents[1];M=.001
PROJECT=OUT.parents[1]
for sub in ['reports','renders','stl-complete','coupons']:(OUT/sub).mkdir(exist_ok=True,parents=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
scene=bpy.context.scene;scene.name='20_A4_COMPLETE_ASSEMBLY'
scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=1;scene.unit_settings.length_unit='MILLIMETERS'
scene.render.engine='CYCLES';scene.cycles.samples=32;scene.cycles.use_denoising=True
scene.render.resolution_x=1500;scene.render.resolution_y=1200;scene.render.resolution_percentage=100;scene.render.image_settings.file_format='PNG'
scene.world=bpy.data.worlds.new('A4 studio');scene.world.use_nodes=True
bg=scene.world.node_tree.nodes.get('Background');bg.inputs['Color'].default_value=(.78,.84,.8,1);bg.inputs['Strength'].default_value=.45
scene.view_settings.view_transform='AgX';scene.view_settings.exposure=.3
def col(name):
 c=bpy.data.collections.new(name);scene.collection.children.link(c);return c
structs=col('A4_COMPLETE_PRINT_PARTS');refs=col('A4_PURCHASED_AND_LEGACY_REFERENCE__NEVER_PRINT');preview=col('A4_UNMEASURED_CONTROL_PREVIEW__NEVER_PRINT');guides=col('A4_VOLUME_RESERVATIONS__NEVER_PRINT');studio=col('A4_STUDIO');labels=col('A4_LABELS__NOT_PRINT')
def lin(x):return x/12.92 if x<=.04045 else ((x+.055)/1.055)**2.4
def material(name,hexcol):
 m=bpy.data.materials.new(name);rgb=tuple(lin(int(hexcol[i:i+2],16)/255) for i in (1,3,5));m.diffuse_color=(*rgb,1);m.use_nodes=True
 bs=next((n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED'),None) or m.node_tree.nodes.new('ShaderNodeBsdfPrincipled')
 mo=next((n for n in m.node_tree.nodes if n.type=='OUTPUT_MATERIAL'),None) or m.node_tree.nodes.new('ShaderNodeOutputMaterial')
 m.node_tree.links.new(bs.outputs[0],mo.inputs[0]);bs.inputs['Base Color'].default_value=(*rgb,1);bs.inputs['Roughness'].default_value=.59;return m
cream=material('A4 cream #EEEADF','#EEEADF');face=material('A4 face #F4F0E8','#F4F0E8');mint=material('A4 mint #9FB9A9','#9FB9A9');black=material('A4 black','#182326');green=material('A4 carrier PCB','#34735E');amber=material('A4 unverified bay','#BC9048');silver=material('A4 hardware','#AAB5B8');ground=material('A4 studio ground','#D4DCD7')
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



parts=[];electronics=[];joints=[]
def addbox(a,d,loc):boolean(a,cube('UNION solid',d,loc),'UNION')
def addcyl(a,r,h,loc,axis='Z'):boolean(a,cyl('UNION cylinder',r,h,loc,axis),'UNION')
def hole(a,r,h,loc,axis='Z'):boolean(a,cyl('CUT round',r,h,loc,axis))
def slot(a,r,p,q,h,axis='Z'):
 hole(a,r,h,p,axis);hole(a,r,h,q,axis)
 dims=[abs(q[i]-p[i])+2*r for i in range(3)];dims['XYZ'.index(axis)]=h
 boolean(a,cube('CUT slot bridge',dims,[(p[i]+q[i])/2 for i in range(3)]))
def register(o,id,label,orientation='Z',qty=1,note=''):
 o.name=id+'__'+o.name.split('__')[-1];clean(o);o['part_id']=id;o['label_zh']=label;o['quantity']=qty
 o['revision']='A4';o['status']='CAD_FOR_PROTOTYPE_FIT_TEST';o['fit_note']=note
 parts.append({'object':o,'id':id,'label_zh':label,'quantity':qty,'orientation':orientation,'note':note});return o

def reference(name,d,loc,mat=black,status='PROVISIONAL_ENVELOPE_NOT_MEASURED'):
 o=cube('REF__'+name,d,loc,refs,mat);o['status']=status;o['never_print']=True;electronics.append(o);return o

def shift_geometry(o,delta):
 o.data.transform(Matrix.Translation(Vector(delta)*M));clean(o)

