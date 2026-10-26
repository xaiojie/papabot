"""Check the V1 display datum, front sightlines and discrete axial cover removal."""
import bpy, bmesh, json, math
from pathlib import Path
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree

OUT=Path(__file__).resolve().parents[1]; M=.001
bpy.ops.wm.open_mainfile(filepath=str(OUT/'DesktopAssistant-整机结构-A3.blend'))
scene=bpy.data.scenes['10_A3_COMPLETE_ASSEMBLY']; bpy.context.window.scene=scene
bpy.context.view_layer.update()
manifest=json.loads((OUT/'reports/complete-manifest.json').read_text())
parts=[scene.objects[r['name']] for r in manifest]
refs=[o for o in scene.objects if o.type=='MESH' and o.name.startswith(('REF__','REF_SCREEN__D','REF_CURRENT__'))]

def bounds(o):
    ps=[o.matrix_world@Vector(v)/M for v in o.bound_box]
    return [min(p[i] for p in ps) for i in range(3)], [max(p[i] for p in ps) for i in range(3)]

def volume(a,b):
    tmp=[]
    for o in [a,b]:
        mesh=bpy.data.meshes.new_from_object(o.evaluated_get(bpy.context.evaluated_depsgraph_get()))
        mesh.transform(Matrix.Scale(1/M,4)@o.matrix_world)
        for v in mesh.vertices: v.co=Vector([round(q,5) for q in v.co])
        obj=bpy.data.objects.new('TEMP_SERVICE_INTERSECTION',mesh);scene.collection.objects.link(obj);tmp.append(obj)
    mod=tmp[0].modifiers.new('Overlap','BOOLEAN');mod.operation='INTERSECT';mod.solver='EXACT';mod.object=tmp[1]
    bpy.context.view_layer.objects.active=tmp[0];bpy.ops.object.modifier_apply(modifier=mod.name)
    bm=bmesh.new();bm.from_mesh(tmp[0].data);v=abs(bm.calc_volume());bm.free()
    for obj in tmp:
        me=obj.data;bpy.data.objects.remove(obj,do_unlink=True);bpy.data.meshes.remove(me)
    return v

front=next(o for o in parts if o['part_id']=='R02')
screen=next(o for o in refs if o.name.startswith('REF_SCREEN__D004'))
glass=next(o for o in refs if o.name.startswith('REF_SCREEN__D003'))
module=next(o for o in refs if o.name.startswith('REF_SCREEN__D001'))
knobs=[o for o in refs if o.name.startswith(tuple('REF_SCREEN__D%03d'%i for i in range(5,12)))]
sl,sh=bounds(screen); gl,gh=bounds(glass); fl,fh=bounds(front); ml,mh=bounds(module)
assert len(knobs)==7
assert max(abs(v-t) for v,t in zip([mh[i]-ml[i] for i in range(3)],[91,1.6,44]))<.01
assert abs((ml[1]+mh[1])/2+20.2)<.01
assert abs(sh[1]-sl[1]-.12)<.01 and abs(sh[0]-sl[0]-48.768)<.01 and abs(sh[2]-sl[2]-36.576)<.01
verts=[front.matrix_world@v.co/M for v in front.data.vertices]
bvh=BVHTree.FromPolygons(verts,[list(p.vertices) for p in front.data.polygons])
occluded=[]; rays=0
for ix in range(13):
    for iz in range(11):
        x=sl[0]+(sh[0]-sl[0])*ix/12; z=sl[2]+(sh[2]-sl[2])*iz/10
        pos,normal,index,distance=bvh.ray_cast(Vector((x,-80,z)),Vector((0,1,0)),sl[1]+80-.02)
        rays+=1
        if index is not None: occluded.append([x,z,distance])
normal=screen.matrix_world.to_3x3()@Vector((0,-1,0));normal.normalize()
assert normal.dot(Vector((0,-1,0)))>.999999
report={'screen_normal':list(normal),'screen_vertical_front_facing':True,'active_area_bbox_mm':[sl,sh],
 'full_stock_module_bbox_mm':[ml,mh],'stock_encoder_and_key_objects':[o.name for o in knobs],
 'glass_front_recess_mm':gl[1]-fl[1],
 'knob_to_front_plate_inner_face_axial_gap_mm':min(bounds(o)[0][1] for o in knobs)-(-43.8),
 'front_sightline_rays':rays,'occluded_front_sightlines':occluded,
 'front_fastener':'4 M3x30, 0.8mm washer; nominal shank Y -47..-17',
 'front_floor_bosses_attached_to':'R01 main housing, not R02 removable cap'}

results=[]
for side,sign,ids in [('front',-1,{'R02'}),('rear',1,{'R03','R09','R10_1','R10_2','R11'})]:
    moving=[o for o in parts if o['part_id'] in ids]
    if side=='rear':
        moving += [o for o in refs if o.name.startswith(('REF__S1A','REF__SPEAKER','REF__MAX98357','REF__CHARGER'))]
    # Fasteners must be withdrawn before removing either cover.
    stationary=[o for o in parts+refs if o not in moving and not o.name.startswith('REF__FRONT_M3')]
    transforms={o.name:o.matrix_world.copy() for o in moving}
    fixed_bounds={o.name:bounds(o) for o in stationary}
    for distance in [0,.25,.5,1,2,3,5,8,12,16,20,24,30,40,60,100]:
        for obj in moving: obj.matrix_world=Matrix.Translation(Vector((0,sign*distance*M,0)))@transforms[obj.name]
        bpy.context.view_layer.update();conflicts=[];pairs=0
        for a in moving:
            al,ah=bounds(a)
            for b in stationary:
                bl,bh=fixed_bounds[b.name]
                if not all(min(ah[i],bh[i])-max(al[i],bl[i])>.025 for i in range(3)): continue
                v=volume(a,b);pairs+=1
                if v>.05: conflicts.append({'moving':a.name,'fixed':b.name,'volume_mm3':round(v,5)})
        results.append({'cover':side,'distance_mm':distance,'solid_pairs_checked':pairs,'conflicts':conflicts})
        print('SERVICE_SAMPLE',side,distance,pairs,len(conflicts),flush=True)
    for obj in moving: obj.matrix_world=transforms[obj.name]
    bpy.context.view_layer.update()
report['removal_samples']=results
report['pass']=not occluded and not any(r['conflicts'] for r in results)
report['limits']=['Geometry is based on nominal V1 encoder dimensions; 15mm in the seller image is shaft length, not total mounted height.',
 'Sightline rays check the nominal active display area straight from the front, not all viewing angles.',
 'Removal is checked at 16 discrete translations per cover, not a continuous solid sweep.',
 'Rear cables must be given slack or disconnected before removal; cable flexibility and acoustic response are untested.']
(OUT/'reports/cover-service-check.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
print('COVER_SERVICE_DONE',report['pass'],flush=True)
assert report['pass'],'Cover service or sightline check failed'
