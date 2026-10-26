"""Create editable overview scenes and render the actual A3 meshes, in background."""
import bpy, json, math, hashlib, struct, sys
from pathlib import Path
from mathutils import Matrix, Vector

OUT = Path(__file__).resolve().parents[1]
FILE = OUT / 'DesktopAssistant-整机结构-A3.blend'
M = .001
bpy.ops.wm.open_mainfile(filepath=str(FILE))
main = bpy.data.scenes['10_A3_COMPLETE_ASSEMBLY']
bpy.context.window.scene = main
bpy.context.view_layer.update()
manifest = json.loads((OUT / 'reports/complete-manifest.json').read_text())
parts = [bpy.data.objects[r['name']] for r in manifest]

def fingerprint():
    h = hashlib.sha256()
    for o in parts:
        h.update(o.name.encode())
        h.update(str(tuple(tuple(q) for q in o.matrix_world)).encode())
        for v in o.data.vertices: h.update(struct.pack('<3f', *v.co))
        for f in o.data.polygons: h.update(str(tuple(f.vertices)).encode())
    return h.hexdigest()

before = fingerprint()
def new_scene(name, width, height):
    if name in bpy.data.scenes: bpy.data.scenes.remove(bpy.data.scenes[name])
    sc = bpy.data.scenes.new(name); sc.use_fake_user = True
    sc.unit_settings.system = 'METRIC'; sc.unit_settings.length_unit = 'MILLIMETERS'
    sc.world = main.world; sc.render.engine = 'CYCLES'
    sc.cycles.samples = 24; sc.cycles.use_denoising = True
    sc.render.resolution_x = width; sc.render.resolution_y = height
    sc.render.resolution_percentage = 100; sc.render.image_settings.file_format = 'PNG'
    sc.view_settings.view_transform = 'AgX'
    sc.view_settings.exposure = -.6
    try: sc.view_settings.look = 'AgX - Medium High Contrast'
    except: pass
    return sc

def duplicate(o, sc, prefix, delta=(0,0,0)):
    cp = o.copy(); cp.name = prefix + o.name
    cp.animation_data_clear(); cp.parent = None
    cp.matrix_world = Matrix.Translation(Vector(delta) * M) @ o.matrix_world
    sc.collection.objects.link(cp)
    cp.hide_render = False; cp.hide_viewport = False
    return cp

def studio(sc, loc, target, objects, scale_lights=1):
    bpy.context.window.scene = sc
    data = bpy.data.cameras.new(sc.name + '_camera')
    cam = bpy.data.objects.new(data.name, data); sc.collection.objects.link(cam)
    cam.location = Vector(loc) * M
    cam.rotation_euler = (Vector(target) * M - cam.location).to_track_quat('-Z','Y').to_euler()
    data.type = 'ORTHO'; data.clip_start = .0001; data.clip_end = 10
    sc.camera = cam
    bpy.context.view_layer.update()
    projected = [cam.matrix_world.inverted() @ (o.matrix_world @ Vector(v))
                 for o in objects if o.type in ['MESH','FONT','CURVE'] for v in o.bound_box]
    # Fit orthographic width as well as height, including all exploded parts.
    h = max(p.y for p in projected) - min(p.y for p in projected)
    w = max(p.x for p in projected) - min(p.x for p in projected)
    aspect = sc.render.resolution_x / sc.render.resolution_y
    data.ortho_scale = max(w, h * aspect) * 1.13
    centre_x = (max(p.x for p in projected) + min(p.x for p in projected)) / 2
    centre_y = (max(p.y for p in projected) + min(p.y for p in projected)) / 2
    cam.location += cam.matrix_world.to_3x3() @ Vector((centre_x, centre_y, 0))
    for name, xyz, energy, size in [('key',(-300,-400,800),10,.65),('fill',(500,-100,550),6,.7),('rim',(100,500,600),9,.6)]:
        ld = bpy.data.lights.new(sc.name + name, 'AREA'); ld.energy = energy * scale_lights; ld.size = size
        lo = bpy.data.objects.new(ld.name, ld); sc.collection.objects.link(lo); lo.location = Vector(xyz)*M
        lo.rotation_euler = (Vector(target)*M-lo.location).to_track_quat('-Z','Y').to_euler()
    bpy.ops.mesh.primitive_plane_add(size=4, location=(0,0,-.001))
    floor = bpy.context.object; floor.name = sc.name+'_STUDIO_NOT_PRINT'
    floor.data.materials.append(bpy.data.materials['A3M studio ground'])
    return cam

explode = new_scene('11_A3_EXPLODED_ASSEMBLY', 1900, 1500)
explode['purpose'] = '装配关系示意；爆炸位移不是安装间隙或装配运动验证'
offsets = {'R01':(0,0,94),'R02':(0,-65,0),'R03':(0,60,0),
           'R04':(0,-32,0),'R05':(0,0,0),'R06':(0,0,24),
           'R09':(0,65,-10),
           'R10_1':(0,65,2),'R10_2':(0,65,2),'R11':(0,35,0),
           'R14':(-35,-20,0),'R16':(0,20,35),'R17':(30,0,20),'R18':(-30,0,20)}
def offset(o):
    ident = o.get('part_id','')
    if ident in offsets: return offsets[ident]
    if ident.startswith('R12'): return (0,0,112)
    if ident.startswith('R13'): return (0,0,101)
    if ident.startswith('L'):
        sign = -1 if ident.endswith(('FL','RL')) else 1
        amount = 24 if ident.startswith('L101') else 47 if ident.startswith('L102') else 72
        return (sign*amount,0,0)
    name = o.name
    if name.startswith('REF_SCREEN'): return (0,-32,0)
    if name.startswith('REF__FRONT_M3'): return (0,-65,0)
    if name.startswith('REF_CURRENT') and not 'BATTERY' in name: return (0,0,24)
    for leg in ['FL','FR','RL','RR']:
        if name.startswith('REF__'+leg+'_'):
            sign = -1 if leg.endswith('L') else 1
            amount = 72 if any(s in name for s in ['SILICONE','STOCK_KNEE']) else 47 if 'KNEE' in name or 'STOCK_HIP' in name else 24
            return (sign*amount,0,0)
    if any(s in name for s in ['S1A','SPEAKER','MAX98357']): return (0,60,0)
    if 'CHARGER' in name: return (0,65,-10)
    if 'PCA9685' in name: return (0,20,35)
    if 'DFR0753' in name or 'R17_M2' in name: return (30,0,20)
    if 'HOBBYWING' in name or 'R18_M2' in name: return (-30,0,20)
    if 'MIC_NARROW' in name: return (-35,-20,0)
    return (0,0,0)

exploded = []
for obj in list(main.objects):
    if obj.type in ['MESH','CURVE','FONT'] and not obj.name.startswith('A3_COMPLETE_studio'):
        exploded.append(duplicate(obj, explode, 'EXP__', offset(obj)))
studio(explode, (430,-540,420), (0,10,115), exploded)

opened = new_scene('13_A3_FRONT_CAP_REMOVED', 1900, 1250)
opened['purpose'] = '前盖先沿-Y移出，再放到左侧展示；原板和原位旋钮/按键保持整机坐标。此展示位移不是拆卸路径。'
open_objs=[]
for obj in list(main.objects):
    if obj.type not in ['MESH','CURVE','FONT'] or obj.name.startswith('A3_COMPLETE_studio'): continue
    delta=(-145,-70,-28) if obj.get('part_id')=='R02' else (0,0,0)
    if obj.name.startswith('REF__FRONT_M3'):
        # Removed screws are omitted from this explanatory view to expose all cap holes.
        continue
    open_objs.append(duplicate(obj,opened,'OPEN__',delta))
studio(opened,(85,-570,180),(-65,0,58),open_objs)

layout = new_scene('12_A3_PRINT_PARTS_OVERVIEW', 2200, 2200)
layout['purpose'] = '30个真实打印件，等比例零件总览；不是单盘切片排版'
layout_objs=[]
orientation = {'front_down': Matrix.Rotation(math.pi/2,4,'X'),
               'back_down': Matrix.Rotation(-math.pi/2,4,'X'),
               'side_down': Matrix.Rotation(math.pi/2,4,'Y'),
               'inverted': Matrix.Rotation(math.pi,4,'X'), 'Z': Matrix.Identity(4)}
records=sorted(manifest, key=lambda r:(not r['id'].startswith('R'), r['id']))
for n, r in enumerate(records):
    source = bpy.data.objects[r['name']]
    cp=duplicate(source,layout,'LAYOUT__')
    rot=orientation[r['orientation']]
    coords=[rot@(source.matrix_world@v.co) for v in source.data.vertices]
    lo=Vector([min(v[i] for v in coords) for i in range(3)])
    hi=Vector([max(v[i] for v in coords) for i in range(3)])
    centre=Vector(((lo.x+hi.x)/2,(lo.y+hi.y)/2,lo.z))
    pos=Vector(((n%6-2.5)*140,(2.5-n//6)*140,0.6))*M
    cp.matrix_world=Matrix.Translation(pos-centre)@rot@source.matrix_world
    layout_objs.append(cp)
    curve=bpy.data.curves.new('LABEL_'+r['id'],'FONT');curve.body=r['id'];curve.size=9*M;curve.align_x='CENTER'
    label=bpy.data.objects.new(curve.name,curve);layout.collection.objects.link(label)
    label.location=pos+Vector((0,-62,.3))*M;curve.materials.append(bpy.data.materials['A3M black'])
    layout_objs.append(label)
studio(layout,(0,-550,1400),(0,0,15),layout_objs,1.3)

bpy.context.window.scene=main;bpy.context.view_layer.update()
after=fingerprint();assert before==after
bpy.ops.wm.save_as_mainfile(filepath=str(FILE))
(OUT/'reports/presentation-preservation.json').write_text(json.dumps({
    'main_part_geometry_before':before,'main_part_geometry_after':after,'unchanged':before==after,
    'new_scenes':[explode.name,layout.name,opened.name],'print_part_count':len(parts)},indent=2))
for sc, filename in ([] if '--no-render' in sys.argv else [(opened,'A3-front-open.png'),(explode,'A3-exploded.png'),(layout,'A3-parts.png')]):
    bpy.context.window.scene=sc;sc.render.filepath=str(OUT/'renders'/filename)
    bpy.ops.render.render(write_still=True)
print('DELIVERY_VIEWS_DONE',flush=True)
