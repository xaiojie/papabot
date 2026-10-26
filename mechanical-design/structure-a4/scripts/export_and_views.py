"""Export A4 registered parts only, in mm. Build editable presentation scenes."""
import bpy,bmesh,math,json,struct,sys
from pathlib import Path
from mathutils import Vector,Matrix
OUT=Path(__file__).resolve().parents[1];M=.001
FILE=OUT/'DesktopAssistant-整机结构-A4.blend'
bpy.ops.wm.open_mainfile(filepath=str(FILE));main=bpy.data.scenes['20_A4_COMPLETE_ASSEMBLY'];bpy.context.window.scene=main
# Boolean cutters can leave an empty material slot; restore an explicit top/edge mapping.
board=main.objects['REF__PCB_USER_110x75x1p6'];board.data.materials.clear()
board.data.materials.append(bpy.data.materials['A4 carrier PCB']);board.data.materials.append(bpy.data.materials['A4 actual user Gerber top'])
for poly in board.data.polygons:poly.material_index=1 if poly.normal.z>.9 else 0
tex=board.data.materials[1];node=tex.node_tree.nodes.get('Actual Gerber UV') or tex.node_tree.nodes.new('ShaderNodeUVMap');node.name='Actual Gerber UV';node.uv_map='ActualGerberUV';tex.node_tree.links.new(node.outputs['UV'],next(n for n in tex.node_tree.nodes if n.type=='TEX_IMAGE').inputs['Vector'])
manifest=json.loads((OUT/'reports/complete-manifest.json').read_text())
parts=[main.objects[r['name']] for r in manifest]
def export(o,rec,sub='stl-complete'):
 me=o.data.copy();bm=bmesh.new();bm.from_mesh(me);bmesh.ops.triangulate(bm,faces=bm.faces);bm.to_mesh(me);bm.free();me.calc_loop_triangles()
 ori=rec.get('orientation','Z');rot=Matrix.Identity(4)
 if ori=='front_down':rot=Matrix.Rotation(math.pi/2,4,'X')
 elif ori=='back_down':rot=Matrix.Rotation(-math.pi/2,4,'X')
 elif ori=='side_down':rot=Matrix.Rotation(math.pi/2,4,'Y')
 elif ori=='inverted':rot=Matrix.Rotation(math.pi,4,'X')
 ps=[rot@(o.matrix_world@v.co)/M for v in me.vertices];lo=Vector([min(v[i] for v in ps) for i in range(3)]);hi=Vector([max(v[i] for v in ps) for i in range(3)])
 shift=Vector(((lo.x+hi.x)/2,(lo.y+hi.y)/2,lo.z));path=OUT/sub/(rec['id']+'__A4__mm.stl')
 with path.open('wb') as f:
  f.write((rec['id']+' A4 | MILLIMETRES | SINGLE PRINT PART | TRIAL FIT').encode().ljust(80,b' '));f.write(struct.pack('<I',len(me.loop_triangles)))
  for tri in me.loop_triangles:
   v=[ps[i]-shift for i in tri.vertices];n=(v[1]-v[0]).cross(v[2]-v[0]).normalized();f.write(struct.pack('<12fH',*n,*v[0],*v[1],*v[2],0))
 bpy.data.meshes.remove(me)
 return rec|{'file':str(path.relative_to(OUT)),'dimensions_mm':[round(x,5) for x in hi-lo],'print_rotation_matrix':[list(r) for r in rot],'print_translation_mm':list(-shift)}
manifest=[export(main.objects[r['name']],r) for r in manifest]
(OUT/'reports/complete-manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2))

# Useful coupons are exact revisions of the mating part, never a fake miniature.
coupons=[]
for ident,source,label in [('T01','R04','屏幕背压框整件试配'),('T02','R07','前窗黑色遮边整件试配'),('T03','R20','USB侧板整件试配'),('T04','L101_FR','MG90S髋座整件试配')]:
 rec=next(r for r in manifest if r['id']==source)
 coupons.append(export(main.objects[rec['name']],rec|{'id':ident,'source_part':source,'label_zh':label},'coupons'))
# R06 top section retains the real 67 x 102 mm four-hole gauge as one connected frame.
o=main.objects[next(r['name'] for r in manifest if r['id']=='R06')].copy();o.data=o.data.copy();main.collection.objects.link(o);o.parent=None
o.data.transform(Matrix.Scale(1000,4)@o.matrix_world);o.matrix_world=Matrix.Identity(4)
bpy.ops.mesh.primitive_cube_add(size=1,location=(0,4,73.5));cut=bpy.context.object;cut.dimensions=(90,120,7);bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
mod=o.modifiers.new('Gauge section','BOOLEAN');mod.solver='MANIFOLD';mod.operation='INTERSECT';mod.object=cut;bpy.context.view_layer.objects.active=o;bpy.ops.object.modifier_apply(modifier=mod.name)
bm=bmesh.new();bm.from_mesh(o.data);bmesh.ops.remove_doubles(bm,verts=bm.verts,dist=.00002);bmesh.ops.dissolve_degenerate(bm,edges=list(bm.edges),dist=.00002);bmesh.ops.recalc_face_normals(bm,faces=bm.faces);bm.to_mesh(o.data);bm.free();o.data.transform(Matrix.Scale(M,4))
coupons.append(export(o,{'id':'T05','source_part':'R06','label_zh':'主板67×102孔位上框试配','orientation':'Z'},'coupons'))
bpy.data.objects.remove(o,do_unlink=True);bpy.data.objects.remove(cut,do_unlink=True)
(OUT/'reports/coupon-manifest.json').write_text(json.dumps(coupons,ensure_ascii=False,indent=2))

def copy_scene(name):
 sc=bpy.data.scenes.new(name);sc.unit_settings.system='METRIC';sc.unit_settings.scale_length=1;sc.unit_settings.length_unit='MILLIMETERS'
 sc.world=main.world;sc.render.engine='CYCLES';sc.cycles.samples=28;sc.cycles.use_denoising=True
 sc.render.resolution_x=1700;sc.render.resolution_y=1350;sc.render.resolution_percentage=100;sc.render.image_settings.file_format='PNG'
 sc.view_settings.view_transform='AgX';sc.view_settings.exposure=.3
 return sc
def duplicate(o,sc,prefix,delta=(0,0,0)):
 cp=o.copy()
 if o.data:cp.data=o.data.copy()
 cp.name=prefix+o.name;cp.animation_data_clear();cp.parent=None;cp.matrix_world=Matrix.Translation(Vector(delta)*M)@o.matrix_world
 sc.collection.objects.link(cp);cp.hide_render=False;return cp
def studio(sc,scale,target=(0,0,75),loc=(300,-430,330)):
 for o in main.objects:
  if o.type=='LIGHT' or o.name=='A4_studio_floor':duplicate(o,sc,'STUDIO_')
 d=bpy.data.cameras.new(sc.name+'_camera');o=bpy.data.objects.new(d.name,d);sc.collection.objects.link(o);o.location=Vector(loc)*M
 o.rotation_euler=(Vector(target)*M-o.location).to_track_quat('-Z','Y').to_euler();d.type='ORTHO';d.ortho_scale=scale*M;d.clip_start=.0001;sc.camera=o
 return sc
for old in ['21_A4_INTERNAL','22_A4_LOWER_DECK','23_A4_EXPLODED','24_A4_FRONT_REMOVED','25_A4_PRINT_PARTS']:
 if old in bpy.data.scenes:bpy.data.scenes.remove(bpy.data.scenes[old])
for name,excluded in [('21_A4_INTERNAL',{'R01','R12_L','R12_R','R13_L','R13_R','R02','R04','R07','R14'}),('22_A4_LOWER_DECK',{'R01','R12_L','R12_R','R13_L','R13_R','R02','R04','R07','R14','R06'})]:
 sc=copy_scene(name)
 for o in main.objects:
  if o.type!='MESH' or o.hide_render or o.name=='A4_studio_floor':continue
  if o.get('part_id') in excluded:continue
  if o.name.startswith('DISPLAY_ONLY') or 'DISPLAY_ONLY' in o.name or o.name.startswith(('REF__HS24','REF__SCREEN_CN1','REF__MIC_MODULE')):continue
  if name=='22_A4_LOWER_DECK' and o.name.startswith(('REF__PCB_','REF__ESP32')):continue
  duplicate(o,sc,'IN_')
 studio(sc,255,(0,0,62),(160,-260,360))
ex=copy_scene('23_A4_EXPLODED')
for o in main.objects:
 if o.type!='MESH' or o.hide_render or o.name=='A4_studio_floor':continue
 pid=o.get('part_id','');delta=(0,0,0)
 if pid in ['R01','R12_L','R12_R','R13_L','R13_R']:delta=(0,0,105)
 elif pid in ['R02','R04','R07','R14'] or any(s in o.name for s in ['HS24','SCREEN_CN1','MIC_MODULE','DISPLAY_ONLY']):delta=(0,-60,0)
 elif pid in ['R03','R08','R11','R19'] or any(s in o.name for s in ['SPEAKER_','S1A_','MAX98357']):delta=(0,65,0)
 elif o.name.startswith(('REF__PCB_','REF__ESP32')):delta=(0,0,65)
 elif pid=='R06':delta=(0,0,32)
 elif pid=='R20':delta=(40,0,0)
 duplicate(o,ex,'EXP_',delta)
studio(ex,395,(0,0,103),(320,-460,310))
op=copy_scene('24_A4_FRONT_REMOVED')
for o in main.objects:
 if o.type!='MESH' or o.hide_render or o.name=='A4_studio_floor':continue
 moved=o.get('part_id') in ['R02','R04','R07','R14'] or any(s in o.name for s in ['HS24','SCREEN_CN1','MIC_MODULE','DISPLAY_ONLY'])
 duplicate(o,op,'OPEN_',(0,-45,0) if moved else (0,0,0))
studio(op,300,(0,-10,65),(220,-360,245))
layout=copy_scene('25_A4_PRINT_PARTS');layout.render.resolution_x=1900;layout.render.resolution_y=2200
for i,rec in enumerate(manifest):
 o=main.objects[rec['name']];cp=duplicate(o,layout,'PRINT_');cp.matrix_world=Matrix.Identity(4)
 rot=Matrix(rec['print_rotation_matrix']);shift=Vector(rec['print_translation_mm'])*M
 cp.data.transform(Matrix.Translation(shift)@rot@o.matrix_world)
 x=(i%5-2)*160;y=(3-i//5)*160;cp.location=Vector((x,y,0))*M
 d=bpy.data.curves.new(rec['id']+'_label','FONT');d.body=rec['id'];d.size=.011;d.align_x='CENTER';t=bpy.data.objects.new(rec['id']+'_label',d);layout.collection.objects.link(t);t.location=Vector((x,y-69,.1))*M
 d.materials.append(bpy.data.materials.get('A4 face #F4F0E8'))
studio(layout,1170,(0,0,0),(0,-10,1200))
for o in layout.objects:
 if o.type=='LIGHT':o.data.energy*=12;o.data.size*=4;o.location.z+=.8
floor=next(o for o in layout.objects if 'studio_floor' in o.name)
mat=main.objects['A4_studio_floor'].data.materials[0].copy();mat.name='A4 parts slate background';bs=mat.node_tree.nodes.get('Principled BSDF');bs.inputs['Base Color'].default_value=(.105,.145,.125,1);floor.data.materials.clear();floor.data.materials.append(mat)
for sc in bpy.data.scenes:sc.use_fake_user=True
bpy.context.window.scene=main
main.cycles.samples=28;main.render.resolution_x=1700;main.render.resolution_y=1350
bpy.ops.wm.save_as_mainfile(filepath=str(FILE))
print('EXPORTED',len(manifest),'PARTS',len(coupons),'COUPONS',flush=True)
