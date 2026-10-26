"""Add editable trial parts without touching the saved user assembly.
Blender background runner. Mesh geometry metres; STL coordinates millimetres.
All edits and outputs remain inside print-v2. Adjust ../parameters.json and rerun.
"""
import bpy, bmesh, math, json, struct, hashlib
from pathlib import Path
from mathutils import Vector
OUT=Path(__file__).resolve().parents[1]
P=json.loads((OUT/'parameters.json').read_text())
M=.001
SOURCE=OUT/'source/desktop-assistant-user-saved-v1.blend'
bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
source_scene=bpy.context.scene

def source_fingerprint():
    h=hashlib.sha256()
    for o in sorted(source_scene.objects,key=lambda a:a.name):
        h.update(o.name.encode()); h.update(o.type.encode())
        h.update(str(tuple(tuple(row) for row in o.matrix_world)).encode())
        if o.type=='MESH':
            for v in o.data.vertices: h.update(struct.pack('<3f',*v.co))
            for f in o.data.polygons: h.update(str(tuple(f.vertices)).encode())
    return h.hexdigest()
before=source_fingerprint()

scene=bpy.data.scenes.new('02_PRINT_V2__FIT_COUPONS_ONLY')
bpy.context.window.scene=scene
scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=1;scene.unit_settings.length_unit='MILLIMETERS'
scene.render.engine='CYCLES';scene.cycles.samples=32;scene.cycles.use_denoising=True
scene.render.resolution_x=1800;scene.render.resolution_y=1300;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG'
scene.world=bpy.data.worlds.new('V2 coupon studio');scene.world.use_nodes=True
bg=next((n for n in scene.world.node_tree.nodes if n.type=='BACKGROUND'),None) or scene.world.node_tree.nodes.new('ShaderNodeBackground')
wo=next((n for n in scene.world.node_tree.nodes if n.type=='OUTPUT_WORLD'),None) or scene.world.node_tree.nodes.new('ShaderNodeOutputWorld')
scene.world.node_tree.links.new(bg.outputs[0],wo.inputs[0])
bg.inputs['Color'].default_value=(.8,.85,.82,1)
bg.inputs['Strength'].default_value=.45
scene.view_settings.view_transform='AgX'
try:scene.view_settings.look='AgX - Medium High Contrast'
except:pass

def collection(name):
    c=bpy.data.collections.new(name);scene.collection.children.link(c);return c
parts=collection('V2_PRINT_COUPONS__EXPORT_ONLY_THIS_COLLECTION')
labels=collection('V2_LABELS__NOT_PRINT')
studio=collection('V2_STUDIO__NOT_PRINT')

def mat(name,color):
    ma=bpy.data.materials.new(name);ma.diffuse_color=(*color,1);ma.use_nodes=True
    bs=next((n for n in ma.node_tree.nodes if n.type=='BSDF_PRINCIPLED'),None) or ma.node_tree.nodes.new('ShaderNodeBsdfPrincipled')
    mo=next((n for n in ma.node_tree.nodes if n.type=='OUTPUT_MATERIAL'),None) or ma.node_tree.nodes.new('ShaderNodeOutputMaterial')
    ma.node_tree.links.new(bs.outputs[0],mo.inputs[0])
    bs.inputs['Base Color'].default_value=(*color,1);bs.inputs['Roughness'].default_value=.65
    return ma
cream=mat('V2 cream trial parts',(.83,.8,.73))
mint=mat('V2 mint trial parts',(.35,.50,.41))
dark=mat('V2 dark labels',(.05,.09,.08))
floor=mat('V2 neutral background',(.72,.75,.72))

def move(o,c):
    for old in list(o.users_collection):old.objects.unlink(o)
    c.objects.link(o)
def cube(name,dimensions,location=(0,0,0),c=parts):
    bpy.ops.mesh.primitive_cube_add(size=1,location=Vector(location)*M)
    o=bpy.context.object;o.name=name;o.dimensions=Vector(dimensions)*M
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);move(o,c);return o
def cylinder(name,radius,depth,location,vertices=96):
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices,radius=radius*M,depth=depth*M,location=Vector(location)*M)
    o=bpy.context.object;o.name=name;move(o,parts);return o
def boolean(o,c):
    mod=o.modifiers.new('Cut dimensioned opening','BOOLEAN');mod.operation='DIFFERENCE';mod.solver='EXACT';mod.object=c
    bpy.context.view_layer.objects.active=o;bpy.ops.object.modifier_apply(modifier=mod.name)
    bpy.data.objects.remove(c,do_unlink=True)
def clean(o):
    bm=bmesh.new();bm.from_mesh(o.data)
    bmesh.ops.remove_doubles(bm,verts=bm.verts,dist=1e-8)
    bmesh.ops.recalc_face_normals(bm,faces=bm.faces)
    bm.to_mesh(o.data);bm.free();o.data.update()
def text_label(body,location,size=3.1):
    cu=bpy.data.curves.new('V2 label '+body,'FONT');cu.body=body;cu.size=size*M;cu.align_x='CENTER';cu.align_y='CENTER'
    o=bpy.data.objects.new('LABEL '+body,cu);labels.objects.link(o);o.location=Vector(location)*M;cu.materials.append(dark);return o
def engrave(o,body,xy,z,size=2.6):
    cu=bpy.data.curves.new('engrave '+body,'FONT');cu.body=body;cu.size=size*M;cu.align_x='CENTER';cu.align_y='CENTER';cu.extrude=.4*M
    ob=bpy.data.objects.new('CUT text',cu);parts.objects.link(ob);ob.location=Vector((xy[0],xy[1],z-.35))*M
    bpy.ops.object.select_all(action='DESELECT');ob.select_set(True);bpy.context.view_layer.objects.active=ob
    bpy.ops.object.convert(target='MESH');boolean(o,bpy.context.object)

manifest=[]
def finalize(o,id,label,material,pos,parameters):
    clean(o);o.data.materials.clear();o.data.materials.append(material)
    for face in o.data.polygons:face.material_index=0
    o['part_id']=id;o['label_zh']=label;o['manufacturing_status']='FIT_COUPON_ONLY__NOT_FINAL_ROBOT_PART'
    o['units']='mm';o['parameters_json']=json.dumps(parameters,ensure_ascii=False)
    # export before layout translation, all files lie on z=0
    mesh=o.data.copy();bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.triangulate(bm,faces=bm.faces);bm.to_mesh(mesh);bm.free()
    mesh.calc_loop_triangles();points=[o.matrix_world@v.co/M for v in mesh.vertices]
    lo=Vector(tuple(min(v[i] for v in points) for i in range(3)));hi=Vector(tuple(max(v[i] for v in points) for i in range(3)))
    shift=Vector(((lo.x+hi.x)/2,(lo.y+hi.y)/2,lo.z))
    file=OUT/'stl'/f'{id}__{o.name.split("__",1)[1]}__mm.stl'
    with file.open('wb') as f:
        f.write((f'{id} FIT COUPON ONLY | UNITS MILLIMETRES'.encode()+b' '*80)[:80]);f.write(struct.pack('<I',len(mesh.loop_triangles)))
        for tri in mesh.loop_triangles:
            vs=[points[i]-shift for i in tri.vertices];n=(vs[1]-vs[0]).cross(vs[2]-vs[0]).normalized()
            f.write(struct.pack('<12fH',*n,*vs[0],*vs[1],*vs[2],0))
    bpy.data.meshes.remove(mesh)
    manifest.append({'id':id,'name':o.name,'label_zh':label,'file':str(file.relative_to(OUT)),'quantity_trial':1,'dimensions_mm':[round(x,4) for x in hi-lo],'print_orientation':'as exported, flat bottom at Z=0; no supports intended','status':'FIT_COUPON_ONLY','parameters':parameters})
    o.location+=Vector(pos)*M

d=P['display'];o=cube('T01__display_hole_pitch_frame',d['jig_outer_mm'],(0,0,1.5))
boolean(o,cube('CUT open center',(*d['jig_inner_mm'],7),(0,0,1.5)))
for x in [-d['hole_pitch_nominal_mm'][0]/2,d['hole_pitch_nominal_mm'][0]/2]:
    for y in [-d['hole_pitch_nominal_mm'][1]/2,d['hole_pitch_nominal_mm'][1]/2]:boolean(o,cylinder('CUT screen hole',d['jig_clearance_hole_mm']/2,7,(x,y,1.5)))
engrave(o,'T01 84.5 x 37.5',(0,-20.5),3,2.4)
finalize(o,'T01','屏幕四孔孔距试配框',cream,(0,40,0),d)
text_label('T01 / DISPLAY HOLE-PITCH GAUGE',(0,72,.2),3.2)
text_label('91 x 44 PCB  |  nominal holes 84.5 x 37.5',(0,8,.2),2.7)

for i,nu in enumerate(P['nut_coupons']):
    w,h,t=nu['outer_mm'];o=cube(nu['id']+'__'+nu['thread']+'_nut_fit_coupon',(w,h,t),(0,0,t/2))
    for x,af in zip(nu['x_mm'],nu['pocket_af_mm']):
        radius=af/math.sqrt(3)
        cut=cylinder('CUT hex pocket',radius,nu['pocket_depth_mm']+1,(x,2,t-nu['pocket_depth_mm']/2+.5),vertices=6)
        boolean(o,cut);boolean(o,cylinder('CUT through screw',nu['through_hole_mm']/2,t+2,(x,2,t/2)))
        engrave(o,f'{af:.1f}',(x,-6.2),t,2.6)
    pos=(-31 if i==0 else 30,-21,0)
    finalize(o,nu['id'],nu['thread']+'六角螺母间隙样件',cream,pos,nu)
    text_label(nu['id']+' / '+nu['thread']+' NUT POCKETS',(pos[0],-39,.2),2.9)

for i,g in enumerate(P['servo_gauges']):
    w,h=g['opening_mm'];t=g['height_mm'];wall=g['wall_mm']
    o=cube(g['id']+'__MG90S_body_opening_gauge',(w+2*wall,h+2*wall,t),(0,0,t/2))
    boolean(o,cube('CUT servo body opening',(w,h,t+2),(0,0,t/2)))
    engrave(o,g['id'],(0,-h/2-wall/2),t,2.2)
    pos=((i-1)*40,-65,0)
    finalize(o,g['id'],'MG90S机壳开口试配规'+chr(65+i),mint,pos,g)
    text_label(f'{w:.1f} x {h:.1f}',(pos[0],-81,.2),2.9)
text_label('MG90S BODY FIT ONLY  /  NO MOUNTING OR SPLINE ASSUMPTION',(0,-92,.2),2.9)

# Studio is not exported. Editable preserved assembly remains in its own original scene.
cube('V2 studio ground',(700,600,2),(0,0,-1.4),studio).data.materials.append(floor)
def aim(o,pt):o.rotation_euler=(Vector(pt)*M-o.location).to_track_quat('-Z','Y').to_euler()
for name,loc,energy,size in [('V2 softbox',(-100,-80,260),.18,.22),('V2 fill',(140,70,210),.1,.17)]:
    data=bpy.data.lights.new(name,'AREA');data.energy=energy;data.shape='DISK';data.size=size
    ob=bpy.data.objects.new(name,data);studio.objects.link(ob);ob.location=Vector(loc)*M;aim(ob,(0,0,0))
data=bpy.data.cameras.new('V2 print samples camera');cam=bpy.data.objects.new('V2 print samples camera',data);studio.objects.link(cam)
cam.location=Vector((0,-165,340))*M;aim(cam,(0,-7,0));data.type='ORTHO';data.ortho_scale=.235;data.lens=50;scene.camera=cam
scene.render.filepath=str(OUT/'renders/fit-coupons-overview.png')
scene['manufacturing_status']='TEST_PARTS_ONLY__NO_FULL_ASSEMBLY_MANUFACTURING_RELEASE'
scene['readme']='See print-v2/README.md; original saved assembly is retained in scene 01. Only six named V2 coupon objects are exported.'

after=source_fingerprint()
assert before==after,'Source scene modified unexpectedly'
(OUT/'reports/export-manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2))
(OUT/'reports/source-preservation.json').write_text(json.dumps({'source_copy_sha256':hashlib.sha256(SOURCE.read_bytes()).hexdigest(),'source_scene_object_count':len(source_scene.objects),'source_scene_fingerprint_before':before,'source_scene_fingerprint_after':after,'source_scene_preserved':before==after,'new_scene':scene.name},indent=2))
# Open the new file directly to the trial-parts scene, preserving all original scene data.
bpy.ops.object.select_all(action='DESELECT')
for o in parts.objects:o.select_set(True)
bpy.context.view_layer.objects.active=next(iter(parts.objects))
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type=='VIEW_3D':area.spaces.active.region_3d.view_perspective='CAMERA'
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'desktop-assistant-print-v2.blend'))
bpy.ops.render.render(write_still=True)
print('V2_DONE',json.dumps({'parts':len(manifest),'source_preserved':before==after},ensure_ascii=False))
