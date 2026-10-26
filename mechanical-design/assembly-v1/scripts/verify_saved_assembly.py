"""Read/reopen verification for a STAGE 1 Blender assembly, not print certification.
Run Blender --background desktop-assistant-assembly-v1.blend --python this_script.
"""
import bpy, bmesh, json, math
from pathlib import Path
from mathutils import Vector
from bpy_extras.object_utils import world_to_camera_view

OUT=Path(__file__).resolve().parents[1]
scene=bpy.context.scene
M=.001
scene.frame_set(1)
checks=[]
def check(name,passed,details):
    checks.append(dict(name=name,passed=bool(passed),details=details))
def bounds(obj):
    pts=[obj.matrix_world@Vector(v) for v in obj.bound_box]
    return [[min(p[i] for p in pts)/M for i in range(3)],
            [max(p[i] for p in pts)/M for i in range(3)]]
def dimensions(obj):
    a,b=bounds(obj)
    return [round(b[i]-a[i],4) for i in range(3)]
def intersection_mm3(a,b):
    """Exact evaluated solid intersection for one explicitly named pair."""
    deps=bpy.context.evaluated_depsgraph_get()
    ma=bpy.data.meshes.new_from_object(a.evaluated_get(deps))
    mb=bpy.data.meshes.new_from_object(b.evaluated_get(deps))
    oa=bpy.data.objects.new('VERIFY_A',ma);ob=bpy.data.objects.new('VERIFY_B',mb)
    scene.collection.objects.link(oa);scene.collection.objects.link(ob)
    oa.matrix_world=a.matrix_world.copy();ob.matrix_world=b.matrix_world.copy()
    bpy.context.view_layer.objects.active=oa
    mod=oa.modifiers.new('Read-only intersection verification','BOOLEAN')
    mod.operation='INTERSECT';mod.solver='EXACT';mod.object=ob
    bpy.ops.object.modifier_apply(modifier=mod.name)
    bm=bmesh.new();bm.from_mesh(oa.data)
    value=abs(bm.calc_volume(signed=True))/M**3
    bm.free()
    bpy.data.objects.remove(oa,do_unlink=True);bpy.data.objects.remove(ob,do_unlink=True)
    if ma.users==0:bpy.data.meshes.remove(ma)
    if mb.users==0:bpy.data.meshes.remove(mb)
    return round(value,6)

check('saved stage flag',scene.get('stage')=='STAGE_1_ASSEMBLY_REVIEW__NO_PRINT_RELEASE',scene.get('stage'))
check('metric units',scene.unit_settings.system=='METRIC' and scene.unit_settings.length_unit=='MILLIMETERS',
      {'system':scene.unit_settings.system,'length_unit':scene.unit_settings.length_unit,'scale':scene.unit_settings.scale_length})
pcb=bpy.data.objects['D001__TOUGLESY_ST7789_EC11_PCB']
active=bpy.data.objects['D004__LCD_active_area_2p4in_4to3']
cover=bpy.data.objects['P002__removable_front_cover']
hood=bpy.data.objects['P001__main_hood']
well=bpy.data.objects['P004__screen_light_baffle']
brace=bpy.data.objects['P007__screen_module_support']
check('supplier nominal PCB envelope',all(abs(a-b)<.001 for a,b in zip(dimensions(pcb),[91,1.6,44])),dimensions(pcb))
check('display centered on body X axis',abs(active.matrix_world.translation.x)<1e-8,
      {'active_center_x_mm':active.matrix_world.translation.x/M,'body_center_x_mm':hood.matrix_world.translation.x/M})
check('body design width',abs(dimensions(cover)[0]-118)<.02,dimensions(cover))
hole_rays=[]
for x in [-31.75,52.75]:
    for z in [49.25,86.75]:
        origin=Vector((x,-28,z))*M
        hit=pcb.ray_cast(pcb.matrix_world.inverted()@origin,Vector((0,1,0)),distance=.02)[0]
        hole_rays.append({'center_mm':[x,-20.2,z],'center_ray_is_open':not hit})
check('four PCB mounting centers are open',all(r['center_ray_is_open'] for r in hole_rays),hole_rays)

mesh_rows=[]
for obj in list(bpy.data.objects):
    if obj.type!='MESH' or not obj.get('category') or any(c.name=='90_STUDIO' for c in obj.users_collection):continue
    deps=bpy.context.evaluated_depsgraph_get();ev=obj.evaluated_get(deps);mesh=ev.to_mesh()
    bm=bmesh.new();bm.from_mesh(mesh)
    bad_edges=sum(not e.is_manifold for e in bm.edges)
    zero=sum(f.calc_area()<1e-14 for f in bm.faces)
    mesh_rows.append({'object':obj.name,'category':obj['category'],'non_manifold_edges':bad_edges,'zero_area_faces':zero})
    bm.free();ev.to_mesh_clear()
check('single-mesh topology only',all(r['non_manifold_edges']==0 and r['zero_area_faces']==0 for r in mesh_rows),
      {'mesh_count':len(mesh_rows),'bad_meshes':[r for r in mesh_rows if r['non_manifold_edges'] or r['zero_area_faces']]})
pair_results=[]
for name,a,b in [('cover / main hood',cover,hood),('optical well / EC11 knob',well,bpy.data.objects['D007__EC11_knob_envelope']),
                 ('speaker / main hood',bpy.data.objects['E005__speaker_ENVELOPE'],hood),
                 ('left ear / hood',bpy.data.objects['P008_ear_L'],hood),('right ear / hood',bpy.data.objects['P008_ear_R'],hood)]:
    v=intersection_mm3(a,b);pair_results.append({'pair':name,'intersection_mm3':v})
    check(name+' sampled solids',v<.001,{'intersection_mm3':v})
servo_clearances=[]
for o in list(bpy.data.objects):
    if o.name.startswith('S_') and o.name.endswith('_HIP_case'):
        v=intersection_mm3(o,pcb)
        servo_clearances.append({'servo':o.name,'pcb_intersection_mm3':v})
check('PCB / four hip servo envelopes',all(r['pcb_intersection_mm3']<.001 for r in servo_clearances),servo_clearances)

# Discrete samples of cover removal against the selected display; cables/tools omitted.
removal_samples=[]
moving=[bpy.data.objects['ASSEMBLY_'+n] for n in ['FRONT_COVER','FRONT_TRIM','SCREEN_WELL']]
obstacles=[pcb,bpy.data.objects['D007__EC11_knob_envelope'],bpy.data.objects['D002__LCD_frame_assumed']]
for travel in [0,2,5,10,20,40,85]:
    for g in moving:g.location.y=-travel*M
    bpy.context.view_layer.update()
    values=[intersection_mm3(a,b) for a in [cover,well] for b in obstacles]
    removal_samples.append({'travel_mm':travel,'maximum_pair_intersection_mm3':max(values)})
for g in moving:g.location.y=0
scene.frame_set(1);bpy.context.view_layer.update()
check('seven sampled front removal positions',all(r['maximum_pair_intersection_mm3']<.001 for r in removal_samples),removal_samples)

pose_rows=[]
for f,group,expected in [(1,'FRONT_COVER',[0,0,0]),(40,'FRONT_COVER',[0,-85,0]),(70,'BOTTOM',[0,0,-29]),(100,'HOOD',[0,40,65])]:
    scene.frame_set(f);actual=[round(v/M,3) for v in bpy.data.objects['ASSEMBLY_'+group].location]
    pose_rows.append({'frame':f,'group':group,'offset_mm':actual,'expected_mm':expected})
check('four disassembly display states',all(r['offset_mm']==r['expected_mm'] for r in pose_rows),pose_rows)
scene.frame_set(1)
physical=[o for o in bpy.data.objects if o.type=='MESH' and o.get('category') and not o.hide_render and
          all(c.name not in ['90_STUDIO','07_CLEARANCE_GUIDES__NON_PRINT','91_LAYOUT_LABELS'] for c in o.users_collection)]
allpts=[o.matrix_world@Vector(v) for o in physical for v in o.bound_box]
envelope={'min_mm':[round(min(p[i] for p in allpts)/M,3) for i in range(3)],
          'max_mm':[round(max(p[i] for p in allpts)/M,3) for i in range(3)]}
envelope['size_mm']=[round(envelope['max_mm'][i]-envelope['min_mm'][i],3) for i in range(3)]
frame_bounds=[]
for key,f in [('HERO',1),('FRONT',1),('SIDE',1),('REAR',1),('FRONT_OPEN',40),('BOTTOM_OPEN',70),('EXPLODED',100),('LAYOUT',1)]:
    scene.frame_set(f);bpy.context.view_layer.update()
    cam=next(o for o in bpy.data.objects if o.type=='CAMERA' and o.name.endswith('_'+key))
    visible=[o for o in physical if key!='LAYOUT' or not any(c.name=='01_PRINT_CANDIDATES__HOUSING' for c in o.users_collection)]
    pts=[world_to_camera_view(scene,cam,o.matrix_world@Vector(v)) for o in visible for v in o.bound_box]
    b=[min(p.x for p in pts),min(p.y for p in pts),max(p.x for p in pts),max(p.y for p in pts)]
    row={'view':key,'projected_bounding_rect':[round(v,4) for v in b]}
    frame_bounds.append(row);check('framing '+key,min(b[:2])>0 and max(b[2:])<1,row)
fonts=[{'name':f.name,'packed':bool(f.packed_file)} for f in bpy.data.fonts if not f.name.startswith('Bfont')]
check('fonts embedded',all(f['packed'] for f in fonts) and len(fonts)>0,fonts)
check('native graphics dependency',[i.name for i in bpy.data.images if i.source=='FILE']==[],{'external_bitmap_count':len([i for i in bpy.data.images if i.source=='FILE'])})
scene.frame_set(1)
result={'scope':'stage_1_reopen_geometry_and_sampled_view_verification_only',
        'blender_version':bpy.app.version_string,'opened_file':Path(bpy.data.filepath).name,
        'check_count':len(checks),'pass_count':sum(c['passed'] for c in checks),'checks':checks,
        'assembled_visible_mesh_envelope_mm':envelope,'mesh_topology':mesh_rows,
        'not_checked':['whole-assembly collision matrix','continuous swept-volume clearance','manufacturing tolerances and min wall thickness',
                       'fastening, assembly tools and load paths','servo travel, strength, stability and gait','slicing or physical print fit',
                       'electrical, thermal, acoustic performance'],
        'print_release':False}
(OUT/'reports/reopen-verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
print('REOPEN_VERIFICATION',result['pass_count'],'/',result['check_count'],flush=True)
for c in checks:
    if not c['passed']:print('FAILED',c['name'],c['details'],flush=True)
print('ENVELOPE_MM',envelope,flush=True)
if result['pass_count']!=result['check_count']:raise RuntimeError('Review failed checks; no delivery claim allowed')
