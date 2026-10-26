"""Additive ACE800 battery fit study. Keeps the source A3 file unchanged.
Blender 5.2; output STL coordinates are millimetres, at print-bed Z=0.
"""
import bpy, bmesh, json, math, struct, hashlib
from pathlib import Path
from mathutils import Vector, Matrix

OUT = Path(__file__).resolve().parents[1]
ROOT = OUT.parents[1]
SOURCE = OUT.parent / 'structure-a3/DesktopAssistant-整机结构-A3.blend'
M = .001
OUT.mkdir(exist_ok=True)
for d in ['stl', 'reports', 'renders']:
    (OUT / d).mkdir(exist_ok=True)
source_hash = hashlib.sha256(SOURCE.read_bytes()).hexdigest()
bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
original = bpy.data.scenes['10_A3_COMPLETE_ASSEMBLY']
scene = bpy.data.scenes.new('20_A3_ACE800_ASSEMBLY')
scene.world = original.world
scene.unit_settings.system = 'METRIC'
scene.unit_settings.length_unit = 'MILLIMETERS'
bpy.context.window.scene = scene
excluded = []
for o in original.objects:
    if 'BATTERY' in o.name:
        excluded.append(o.name)
    else:
        scene.collection.objects.link(o)
new_objects = []

def mat(name, rgba):
    m = bpy.data.materials.new(name)
    m.diffuse_color = rgba
    return m

mint = mat('ACE800 | printable mint', (.38,.65,.51,1))
black = mat('ACE800 | battery wrap', (.035,.045,.05,1))
foam = mat('ACE800 | insulating foam', (.24,.26,.28,1))
pcbmat = mat('ACE800 | BMS envelope', (.10,.34,.19,1))

def cube(name, dims, loc, material=None, tracked=True):
    bpy.ops.mesh.primitive_cube_add(size=1, location=Vector(loc)*M)
    o = bpy.context.object
    o.name = name
    o.dimensions = Vector(dims)*M
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if material: o.data.materials.append(material)
    if tracked: new_objects.append(o)
    return o

def mm_mesh(o):
    me = bpy.data.meshes.new_from_object(o.evaluated_get(bpy.context.evaluated_depsgraph_get()))
    me.transform(Matrix.Scale(1000,4) @ o.matrix_world)
    for v in me.vertices: v.co=Vector([round(q,5) for q in v.co])
    bm=bmesh.new();bm.from_mesh(me)
    bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.00002)
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(me);bm.free()
    return me

def boolean(a,b,op='DIFFERENCE', remove=True):
    bpy.context.view_layer.update()
    ac = bpy.data.objects.new('TEMP A', mm_mesh(a))
    bc = bpy.data.objects.new('TEMP B', mm_mesh(b))
    scene.collection.objects.link(ac); scene.collection.objects.link(bc)
    mod = ac.modifiers.new('mm exact boolean', 'BOOLEAN')
    mod.operation=op; mod.solver='MANIFOLD'; mod.object=bc
    bpy.context.view_layer.objects.active=ac
    bpy.ops.object.modifier_apply(modifier=mod.name)
    if remove:
        me=ac.data.copy(); me.transform(a.matrix_world.inverted() @ Matrix.Scale(M,4))
        a.data=me
    bm=bmesh.new(); bm.from_mesh(ac.data)
    volume=abs(bm.calc_volume(signed=True)); bm.free()
    if op=='INTERSECT' and volume>.05:
        ps=[v.co for v in ac.data.vertices]
        print('INTERSECTION',a.name,b.name,volume,
              [[round(fn(v[i] for v in ps),3) for i in range(3)] for fn in [min,max]],flush=True)
    bpy.data.objects.remove(ac,do_unlink=True); bpy.data.objects.remove(bc,do_unlink=True)
    if remove: bpy.data.objects.remove(b,do_unlink=True)
    return volume

def cut(a,dims,loc):
    boolean(a,cube('CUT',dims,loc,tracked=False))

def add(a,dims,loc):
    boolean(a,cube('ADD',dims,loc,tracked=False),'UNION')

# Slip-in ring fits A3's 79 x 44 mm tray. 2 mm side foam fits the
# 64 x 36 opening around the 60 x 32 mm soft pack without clamp pressure.
ring = cube('R21__ACE800_spacer', (78,42,5.9), (0,14,37.65), mint)
cut(ring,(64,36,10),(0,14,37.6))
cut(ring,(12,16,10),(36,14,37.6))  # Existing +X cable exit.
for y in [-7,35]:
    cut(ring,(12,10,2.2),(0,y,35.5))  # Belt passes under, not through the ring roof.
for x in [-20,20]:
    cut(ring,(4.6,2.6,2.4),(x,-5.7,39.6))

# The BMS stands in front of the battery, behind the screen. This avoids
# the R06 crossmembers at Z58.6 and never loads the soft pack.
shelf = cube('R22__HX2S_front_cradle', (52,1.6,25.3), (0,-7.7,53.35), mint)
for x in [-20,20]:
    add(shelf,(4,2,2.4),(x,-5.7,39.8))
    add(shelf,(6,3.8,1.6),(x,-6.4,41.4))
# Bottom support and two side guides, leaving the wire pads accessible.
add(shelf,(52,5.4,1.4),(0,-9.6,41.4))
for x in [-25.2,25.2]:
    add(shelf,(1.6,4.8,10),(x,-9.8,52))

pack=cube('REF_ACE800_60x32x16_DO_NOT_PRINT',(60,32,16),(0,14,43.6),black)
pad=cube('REF_EVA_60x32x1_DO_NOT_PRINT',(60,32,1),(0,14,35.1),foam)
strap=cube('REF_BATTERY_STRAP_DO_NOT_PRINT',(10,32,1),(0,14,52.1),foam)
insulator=cube('REF_BMS_INSULATION_0p5_DO_NOT_PRINT',(46.7,.5,23),(0,-8.75,53.7),foam)
bms=cube('REF_HX2S_46p7x23x3p15_DO_NOT_PRINT',(46.7,3.15,23),(0,-10.575,53.7),pcbmat)

def bounds(o):
    p=[o.matrix_world@v.co/M for v in o.data.vertices]
    return [[min(v[i] for v in p) for i in range(3)], [max(v[i] for v in p) for i in range(3)]]

def export_part(o, part):
    me=mm_mesh(o)
    bm=bmesh.new(); bm.from_mesh(me)
    bmesh.ops.recalc_face_normals(bm,faces=bm.faces)
    bad=sum(not e.is_manifold for e in bm.edges)
    visited=set(); components=0
    for v in bm.verts:
        if v in visited: continue
        components+=1; stack=[v]; visited.add(v)
        while stack:
            v=stack.pop()
            for e in v.link_edges:
                w=e.other_vert(v)
                if w not in visited: visited.add(w); stack.append(w)
    volume=abs(bm.calc_volume(signed=True))
    assert bad==0 and components==1 and volume>0, (part,bad,components,volume)
    bmesh.ops.triangulate(bm,faces=bm.faces); bm.to_mesh(me); bm.free(); me.calc_loop_triangles()
    ps=[v.co.copy() for v in me.vertices]
    lo=Vector([min(v[i] for v in ps) for i in range(3)])
    hi=Vector([max(v[i] for v in ps) for i in range(3)])
    shift=Vector(((lo.x+hi.x)/2,(lo.y+hi.y)/2,lo.z))
    path=OUT/'stl'/f'{part}__ACE800__mm.stl'
    with path.open('wb') as f:
        f.write((part+' | mm | TRIAL FIT | ONE PART').encode().ljust(80,b' '))
        f.write(struct.pack('<I',len(me.loop_triangles)))
        for t in me.loop_triangles:
            v=[ps[i]-shift for i in t.vertices]
            n=(v[1]-v[0]).cross(v[2]-v[0]).normalized()
            f.write(struct.pack('<12fH',*n,*v[0],*v[1],*v[2],0))
    bpy.data.meshes.remove(me)
    return dict(id=part,bounds_mm=bounds(o),size_mm=list(hi-lo),nonmanifold_edges=bad,
                connected_components=components,volume_mm3=volume,stl=path.name,
                sha256=hashlib.sha256(path.read_bytes()).hexdigest())

bpy.context.view_layer.update()
parts=[export_part(ring,'R21'),export_part(shelf,'R22')]
# Only incremental fit is claimed. Existing A3 entities/poses are not rebuilt.
checked=[]; conflicts=[]
old=[o for o in original.objects if o.type=='MESH' and o.name not in excluded
     and not any(s in o.name.upper() for s in ['STUDIO','GROUND','RESERVATION','ANTENNA'])]
for i,a in enumerate(new_objects):
    for b in old+new_objects[i+1:]:
        aa,bb=bounds(a),bounds(b)
        if not all(min(aa[1][k],bb[1][k])-max(aa[0][k],bb[0][k])>.001 for k in range(3)): continue
        v=boolean(a,b,'INTERSECT',False)
        checked.append(dict(a=a.name,b=b.name,intersection_mm3=v))
        if v>.05: conflicts.append(checked[-1])

report=dict(revision='A3-ACE800',source=str(SOURCE),source_sha256=source_hash,
    source_unchanged=source_hash==hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
    battery_body_mm=[60,32,16],battery_center_mm=[0,14,43.6],
    bms_mount='vertical in front of battery; cells face +Y, screen faces -Y',
    bms_to_display_support_rear_plane_clearance_mm=1.65,
    bms_to_screen_pcb_rear_plane_clearance_mm=7.25,
    cradle_backplate_to_battery_body_clearance_mm=4.9,
    clearance_excludes_wires_solder_and_manufacturing_tolerance=True,
    excluded_historical_battery_references=excluded,parts=parts,
    intersection_candidates=len(checked),intersection_results=checked,conflicts=conflicts,
    physical_fit_tested=False,thermal_and_load_tested=False,
    installation='2mm soft side pads; 1mm base pad; original 10mm battery strap; 0.5mm BMS insulation; removable RTV locks two locating feet after trial fit')
(OUT/'reports/fit-check.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
assert not conflicts, conflicts
scene.render.engine='BLENDER_WORKBENCH'
scene.display.shading.light='STUDIO';scene.display.shading.color_type='MATERIAL'
scene.display.shading.show_shadows=True;scene.display.shading.show_cavity=True
scene.display.shading.background_type='WORLD';scene.world.color=(.8,.85,.82)
scene.render.resolution_x=1440;scene.render.resolution_y=1080;scene.render.resolution_percentage=100
bpy.ops.object.camera_add(location=Vector((140,-155,145))*M)
cam=bpy.context.object;cam.name='ACE800_detail_camera';cam.data.type='ORTHO';cam.data.ortho_scale=.185
cam.rotation_euler=(Vector((0,14,48))*M-cam.location).to_track_quat('-Z','Y').to_euler();scene.camera=cam
# Detail scene shows only the floor, support, and new battery components.
detail=bpy.data.scenes.new('21_ACE800_POWER_BAY_DETAIL')
detail.world=scene.world;detail.render.engine='BLENDER_WORKBENCH'
detail.display.shading.color_type='MATERIAL';detail.display.shading.show_cavity=True
detail.render.resolution_x=1440;detail.render.resolution_y=1080;detail.render.resolution_percentage=100
detail.collection.objects.link(cam);detail.camera=cam
for o in new_objects+[bpy.data.objects['R05__reinforced_floor_and_battery_tray_A3']]:
    detail.collection.objects.link(o)
bpy.context.window.scene=detail
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'DesktopAssistant-A3-ACE800.blend'))
detail.render.filepath=str(OUT/'renders/power-bay.png');bpy.ops.render.render(write_still=True)
print(json.dumps({'parts':parts,'intersection_candidates':len(checked),'conflicts':conflicts},ensure_ascii=False))
