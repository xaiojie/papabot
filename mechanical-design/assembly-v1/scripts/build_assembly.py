"""Stage-1 dimensioned assembly / not a manufacturing release.
Run: Blender --background --python scripts/build_assembly.py -- --preview
All design inputs below are in millimetres; Blender geometry uses metres.
"""
import bpy, bmesh, math, json, csv, sys
from pathlib import Path
from mathutils import Vector

OUT=Path(__file__).resolve().parents[1]
M=.001
P={
 'body_width':118., 'body_height':76., 'body_center_z':68.,
 'hood_front_y':-15., 'hood_rear_y':38., 'front_cover_y':-46.2,
 'wall':2.4, 'pcb_width':91., 'pcb_height':44., 'pcb_thickness':1.6,
 'pcb_center_x':10.5, 'pcb_center_z':68., 'pcb_front_y':-21.,
 'pcb_hole_x':84.5, 'pcb_hole_z':37.5, 'pcb_hole_d':3.,
 'lcd_outer_width':59., 'lcd_outer_height':41.5,
 'lcd_glass_y':-25.4, 'active_width':48.768, 'active_height':36.576,
 'encoder_protrusion':21., 'encoder_diameter':15.5,
 'front_window_width':70., 'front_window_height':51.,
 'leg_lateral_offset':13., 'servo_case_assumed':[22.8,12.2,22.5], 'servo_overall_height_assumed':28.5,
 'exploded_frame':100, 'assembly_frame':1, 'front_open_frame':40, 'bottom_open_frame':70,
}
CATEGORIES={}
PARTS=[]

bpy.ops.wm.read_factory_settings(use_empty=True)
scene=bpy.context.scene
scene.name='01_ASSEMBLY_AND_DISASSEMBLY'
scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=1.;scene.unit_settings.length_unit='MILLIMETERS'
scene.render.engine='CYCLES';scene.cycles.samples=40;scene.cycles.use_denoising=True
scene.render.resolution_x=1800;scene.render.resolution_y=1350;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG';scene.render.film_transparent=False
scene.render.fps=24;scene.frame_start=1;scene.frame_end=100
scene.world=bpy.data.worlds.new('Studio world');scene.world.use_nodes=True
scene.world.node_tree.nodes['Background'].inputs['Color'].default_value=(.76,.81,.84,1)
scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.35
scene.view_settings.view_transform='AgX'
try:scene.view_settings.look='AgX - Medium High Contrast'
except:pass
scene.view_settings.exposure=.3
try:
 prefs=bpy.context.preferences.addons['cycles'].preferences;prefs.compute_device_type='METAL';prefs.get_devices()
 for d in prefs.devices:d.use=(d.type=='METAL')
 if any(d.type=='METAL' for d in prefs.devices):scene.cycles.device='GPU'
except Exception as e:print('GPU fallback',str(e))


def collection(name):
 c=bpy.data.collections.new(name);scene.collection.children.link(c);return c
cols={k:collection(v) for k,v in {
 'shell':'01_PRINT_CANDIDATES__HOUSING', 'legs':'02_PRINT_CANDIDATES__LEGS',
 'display':'03_SELECTED_DISPLAY_MODULE', 'electronics':'04_UNSELECTED_ELECTRONIC_ENVELOPES',
 'hardware':'05_OFF_THE_SHELF_HARDWARE', 'controls':'06_ASSEMBLY_CONTROLS',
 'envelopes':'07_CLEARANCE_GUIDES__NON_PRINT', 'studio':'90_STUDIO', 'labels':'91_LAYOUT_LABELS',
}.items()}

def move_col(obj,key):
 for c in list(obj.users_collection):c.objects.unlink(obj)
 cols[key].objects.link(obj)

def parent_keep(obj,parent):
 if parent:
  obj.parent=parent;obj.matrix_parent_inverse=parent.matrix_world.inverted()

def lin(v):return v/12.92 if v<=.04045 else ((v+.055)/1.055)**2.4

def mat(name,hexcol,rough=.55,metal=0.,micro=False):
 rgb=tuple(lin(int(hexcol[i:i+2],16)/255) for i in (1,3,5))
 m=bpy.data.materials.new(name);m.diffuse_color=(*rgb,1);m.use_nodes=True
 bs=m.node_tree.nodes.get('Principled BSDF');bs.inputs['Base Color'].default_value=(*rgb,1)
 bs.inputs['Roughness'].default_value=rough;bs.inputs['Metallic'].default_value=metal
 if micro:
  n=m.node_tree.nodes.new('ShaderNodeTexNoise');n.inputs['Scale'].default_value=950.
  n.inputs['Detail'].default_value=2.;b=m.node_tree.nodes.new('ShaderNodeBump')
  b.inputs['Strength'].default_value=.15;b.inputs['Distance'].default_value=.000035
  m.node_tree.links.new(n.outputs['Fac'],b.inputs['Height']);m.node_tree.links.new(b.outputs['Normal'],bs.inputs['Normal'])
 return m
mats={
 'cream':mat('CMF_A | cream body #EEEADF','#EEEADF',.58,micro=True),
 'face':mat('CMF_A | warm white face #F4F0E8','#F4F0E8',.55,micro=True),
 'mint':mat('CMF_A | mint #9FB9A9','#9FB9A9',.57,micro=True),
 'black':mat('Optical well | black','#10191C',.43),
 'glass':mat('LCD cover glass','#081114',.18),
 'rubber':mat('Soft foot pads | purchased/TBD','#20292B',.77),
 'blue':mat('Servo blue | assumed purchased housing','#125ABA',.29),
 'pcb':mat('Selected display PCB | blue','#20578A',.42),
 'greenpcb':mat('PCB envelopes | green','#397564',.48),
 'metal':mat('Steel fasteners','#BAC4C8',.27,.78),
 'gold':mat('Connector pins','#C6A65A',.28,.7),
 'chip':mat('Electronic envelope detail','#28353A',.48),
 'amber':mat('Unconfirmed electronic envelopes','#D49C49',.58),
 'floor':mat('Studio warm neutral','#DFE3E0',.83),
 'label':mat('Technical text','#253F45',.65),
}
em=bpy.data.materials.new('LCD cyan graphics | render only');em.use_nodes=True
bs=em.node_tree.nodes.get('Principled BSDF');bs.inputs['Base Color'].default_value=(0,.65,.85,1)
bs.inputs['Emission Color'].default_value=(0,.65,.85,1);bs.inputs['Emission Strength'].default_value=2.5;bs.inputs['Roughness'].default_value=.4
mats['cyan']=em

def finish(obj,name,material,key,parent=None,category='REFERENCE',label='',part_id=None):
 obj.name=name;move_col(obj,key)
 if material:obj.data.materials.append(mats.get(material,material))
 parent_keep(obj,parent)
 obj['category']=category;obj['label_zh']=label or name
 if category=='PRINT_CANDIDATE':
  obj['manufacturing_status']='stage_1_geometry__NOT_RELEASED_FOR_PRINT'
  obj['part_id']=part_id or name.split('__')[0];PARTS.append(obj)
 elif category=='ENVELOPE':obj['dimension_status']='assumed__replace_after_selection_or_measurement'
 return obj

def apply_mod(obj,mod):
 bpy.context.view_layer.objects.active=obj;bpy.ops.object.modifier_apply(modifier=mod.name)

def bevel(obj,amount=.5,segments=3):
 if amount<=0:return
 mod=obj.modifiers.new('Edge radius mm','BEVEL');mod.width=amount*M;mod.segments=segments
 apply_mod(obj,mod)
 for f in obj.data.polygons:f.use_smooth=True
 # Normal modifiers are added only after all geometry operations.

def cube(name,dim,loc,material,key,parent=None,bevel_mm=.4,category='REFERENCE',label='',part_id=None):
 bpy.ops.mesh.primitive_cube_add(size=1,location=Vector(loc)*M)
 o=bpy.context.object;o.dimensions=Vector(dim)*M;bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
 bevel(o,min(bevel_mm,min(dim)*.48),4)
 return finish(o,name,material,key,parent,category,label,part_id)

def cylinder(name,radius,depth,loc,material,key,parent=None,axis='Z',category='REFERENCE',label='',vertices=40):
 bpy.ops.mesh.primitive_cylinder_add(vertices=vertices,radius=radius*M,depth=depth*M,location=Vector(loc)*M)
 o=bpy.context.object
 if axis=='X':o.rotation_euler[1]=math.pi/2
 if axis=='Y':o.rotation_euler[0]=math.pi/2
 bpy.ops.object.transform_apply(location=False,rotation=True,scale=True)
 bevel(o,min(.24,depth*.15),3)
 return finish(o,name,material,key,parent,category,label)

def boolean(obj,cutter,operation='DIFFERENCE'):
 mod=obj.modifiers.new('Geometric '+operation,'BOOLEAN');mod.operation=operation;mod.solver='EXACT';mod.object=cutter
 apply_mod(obj,mod);bpy.data.objects.remove(cutter,do_unlink=True)

def rr_points(w,h,r,n=12):
 r=min(r,w/2-.01,h/2-.01);out=[]
 for cx,cz,a in [(w/2-r,h/2-r,0),(-w/2+r,h/2-r,90),(-w/2+r,-h/2+r,180),(w/2-r,-h/2+r,270)]:
  for i in range(n+1):
   ang=math.radians(a+i*90/n);out.append((cx+r*math.cos(ang),cz+r*math.sin(ang)))
 return out

def loft(name,profiles,material,key,parent=None,category='REFERENCE',label='',cap=True):
 # profiles: y, w, h, radius, x centre, z centre; consistent sampled outlines
 verts=[]
 for y,w,h,r,cx,cz in profiles:
  verts += [(M*(x+cx),M*y,M*(z+cz)) for x,z in rr_points(w,h,r)]
 n=len(verts)//len(profiles);faces=[]
 for s in range(len(profiles)-1):
  for i in range(n):j=(i+1)%n;faces.append((s*n+i,s*n+j,(s+1)*n+j,(s+1)*n+i))
 if cap:faces += [tuple(reversed(range(n))),tuple(range((len(profiles)-1)*n,len(profiles)*n))]
 mesh=bpy.data.meshes.new(name+' mesh');mesh.from_pydata(verts,[],faces);mesh.update()
 o=bpy.data.objects.new(name,mesh);cols[key].objects.link(o)
 bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.recalc_face_normals(bm,faces=bm.faces);bm.to_mesh(mesh);bm.free()
 return finish(o,name,material,key,parent,category,label)

def ring_loft(name,outer,inner,material,key,parent=None,category='REFERENCE',label=''):
 o=loft(name,outer,material,key,parent,category,label)
 c=loft('CUT ring',inner,None,'envelopes');boolean(o,c);bevel(o,min(.22,min(o.dimensions)/M*.27),3);return o

def tube(name,r,inner,depth,loc,material,key,parent=None,axis='Y',category='REFERENCE'):
 o=cylinder(name,r,depth,loc,material,key,parent,axis,category)
 c=cylinder('CUT hole',inner,depth+2,loc,None,'envelopes',axis=axis);boolean(o,c);return o

def empty(name,loc=(0,0,0),parent=None,key='controls'):
 o=bpy.data.objects.new(name,None);cols[key].objects.link(o);o.location=Vector(loc)*M;o.empty_display_size=.012
 o.empty_display_type='PLAIN_AXES';parent_keep(o,parent);return o

def rod(name,a,b,thickness,material,key,parent=None,category='REFERENCE',label=''):
 a,b=Vector(a),Vector(b);delta=b-a
 o=cube(name,(thickness[0],thickness[1],delta.length+3),(a+b)/2,material,key,None,min(thickness)*.4,category,label)
 o.rotation_euler=delta.to_track_quat('Z','Y').to_euler();parent_keep(o,parent);return o

def wire(name,points,r,material,key,parent=None):
 cr=bpy.data.curves.new(name,'CURVE');cr.dimensions='3D';cr.resolution_u=16;cr.bevel_depth=r*M;cr.bevel_resolution=3
 sp=cr.splines.new('BEZIER');sp.bezier_points.add(len(points)-1)
 for bp,pt in zip(sp.bezier_points,points):bp.co=Vector(pt)*M;bp.handle_left_type='AUTO';bp.handle_right_type='AUTO'
 o=bpy.data.objects.new(name,cr);cols[key].objects.link(o);o.data.materials.append(mats[material]);parent_keep(o,parent)
 o['category']='WIRE_ROUTING_CONCEPT';return o

def screw(name,loc,parent=None,axis='Y',r=2.4,key='hardware'):
 h=cylinder(name,r,1.4,loc,'metal',key,parent,axis=axis)
 v=Vector(loc)
 if axis=='Y':v.y-=.75;d=(r*1.1,.14,.52)
 elif axis=='X':v.x+=.75;d=(.14,r*1.1,.52)
 else:v.z+=.75;d=(r*1.1,.52,.14)
 cube(name+'_drive',d,v,'chip',key,parent,0)
 return h

root=empty('DESKTOP_ASSISTANT | A cream mint | STAGE 1')
root['readme']='Separate part assembly, not print-ready; markers 1 assembled, 40 face open, 70 bottom open, 100 exploded.'
root['design_parameters_mm']=json.dumps(P,ensure_ascii=False)
groups={n:empty('ASSEMBLY_'+n,parent=root) for n in ['HOOD','FRONT_COVER','FRONT_TRIM','SCREEN_WELL','BOTTOM','DISPLAY','DISPLAY_BRACKET','ELECTRONICS','EAR_L','EAR_R','LEG_FL','LEG_FR','LEG_RL','LEG_RR']}

# Main hood: open front and bottom. Side portals are provisional servo mounting apertures.
hood=ring_loft('P001__main_hood',
 [(-14.7,118,76,14,0,68),(31,118,76,14,0,68),(36.5,115,73,12.5,0,68),(38,110,68,10.5,0,68)],
 [(-16,113.2,71.2,11.6,0,68),(29.5,113.2,71.2,11.6,0,68),(33.5,110,68,10,0,68),(35.6,105,63,8.5,0,68)],
 'cream','shell',groups['HOOD'],'PRINT_CANDIDATE','主壳：前部和底部可拆')
boolean(hood,cube('CUT bottom opening',(106,58,15),(0,10,27),None,'envelopes',bevel_mm=2))
for s in [-1,1]:
 for y in [-18,22]:
  boolean(hood,cube('CUT servo side portal',(12,27,31),(s*57,y,56),None,'envelopes',bevel_mm=4))
# microphone aperture
boolean(hood,cylinder('CUT microphone',1.7,12,(-12,-1,106),None,'envelopes'))
# rear speaker hole pattern: actual speaker/driver model still TBD
for x,z in [(x,z) for x in range(-10,11,5) for z in range(-10,11,5) if x*x+z*z<=120]:
 boolean(hood,cylinder('CUT grille',1.1,9,(22+x,37.5,78+z),None,'envelopes',axis='Y',vertices=20))
boolean(hood,cube('CUT rear power slot',(12,12,7),(-30,37.5,47),None,'envelopes',bevel_mm=2))
# Front cap is a hollow deep cap, accommodating the intact protruding encoder.
cover=ring_loft('P002__removable_front_cover',
 [(-46.2,109,70,12,0,68),(-44.3,114,74,13,0,68),(-40,118,76,14,0,68),(-15.25,118,76,14,0,68)],
 [(-43.7,104.2,65.2,10,0,68),(-41.8,109.2,69.2,11,0,68),(-39,113.2,71.2,11.6,0,68),(-14.5,113.2,71.2,11.6,0,68)],
 'face','shell',groups['FRONT_COVER'],'PRINT_CANDIDATE','可拆前盖：保留旋钮内腔')
boolean(cover,loft('CUT display aperture',[(-49,70,51,4.2,0,68),(-40,70,51,4.2,0,68)],None,'envelopes'))
trim=ring_loft('P003__mint_front_outline',
 [(-46.55,107.5,68.5,12,0,68),(-46.15,107.5,68.5,12,0,68)],
 [(-47,104.8,65.8,10.8,0,68),(-45,104.8,65.8,10.8,0,68)],
 'mint','shell',groups['FRONT_TRIM'],'PRINT_CANDIDATE','薄荷绿细边：嵌件/着色方式待验证')
# Aperture baffle matches the real screen recess. It is NOT a second screen.
well=ring_loft('P004__screen_light_baffle',
 [(-46.3,71,52,4.5,0,68),(-25.7,60.5,43.5,2.5,0,68)],
 [(-47,68.8,49.8,3.6,0,68),(-25.0,58.2,41.2,1.6,0,68)],
 'black','shell',groups['SCREEN_WELL'],'PRINT_CANDIDATE','屏幕遮光井：正面遮住 PCB，屏幕实际后退')
# Integrated locating pins and matching receivers. 0.2 mm radial gap is a trial assumption.
for x in [-44,44]:
 for z in [35.2,100.8]:
  pin=tube('FEATURE cap locator',3.2,1.3,8,(x,-16.8,z),'face','shell',groups['FRONT_COVER'])
  boolean(cover,pin,'UNION')
  socket=cylinder('FEATURE hood receiver',4.6,4.5,(x,-12.15,z),'cream','shell',groups['HOOD'],axis='Y')
  boolean(hood,socket,'UNION')
  boolean(hood,cylinder('CUT receiver relief',3.4,6.5,(x,-12.5,z),None,'envelopes',axis='Y'))
cover['locator_fit']='trial radial gap 0.2 mm; not tolerance validated; fastening TBD'

# bottom tray: separate enclosure component, holes/rails TBD
bottom=cube('P005__removable_bottom_tray',(109,48,3),(0,11.1,31.2),'cream','shell',groups['BOTTOM'],1.3,'PRINT_CANDIDATE','底盖/维修托盘')
for x in [-40,40]:
 for y in [-5,29]:
  boolean(bottom,cylinder('CUT base screw',1.6,8,(x,y,31.2),None,'envelopes'))
  screw(f'Base_screw_{x}_{y}',(x,y,29.4),groups['BOTTOM'],axis='Z')
for x in [-28,-14,0,14,28]:
 boolean(bottom,cube('CUT base ventilation',(5,18,8),(x,14,31.2),None,'envelopes',bevel_mm=1.5))
# Shelves represent replaceable trays rather than unverified production hole patterns.
tray=cube('P006__electronics_tray',(84,37,2.6),(0,10,36.5),'mint','shell',groups['ELECTRONICS'],3,'PRINT_CANDIDATE','可更换电子托板：安装孔待主控/PCB选定')
for x in [-36,36]:
 for y in [-3,23]:
  standoff=tube('FEATURE tray standoff',2.5,1.1,2.7,(x,y,34.05),'mint','shell',groups['ELECTRONICS'],axis='Z')
  boolean(tray,standoff,'UNION')

# Selected screen module: nominal PCB and hole pattern.
pcb=cube('D001__TOUGLESY_ST7789_EC11_PCB',(91,1.6,44),(10.5,-20.2,68),'pcb','display',groups['DISPLAY'],.45,label='已选模块 PCB，商品标称 91×44 mm')
pcb['dimension_status']='supplier_nominal__measure_before_manufacture'
for x in [10.5-42.25,10.5+42.25]:
 for z in [68-18.75,68+18.75]:
  boolean(pcb,cylinder('CUT display mounting hole',1.5,6,(x,-20.2,z),None,'envelopes',axis='Y'))
  tube('Display_hole_plating',2.0,1.5,.12,(x,-21.08,z),'gold','display',groups['DISPLAY'])
  screw('Display_mount_screw',(x,-21.7,z),groups['DISPLAY'],r=2.2)
  tube('P007_display_spacer',3.0,1.65,6.4,(x,-16.2,z),'cream','shell',groups['DISPLAY_BRACKET'],category='PRINT_CANDIDATE')
frame=cube('D002__LCD_frame_assumed',(59,3.6,41.5),(0,-23,68),'metal','display',groups['DISPLAY'],.6,label='LCD 外形占位：59×41.5，待实测')
frame['dimension_status']='assumed_from_supplier_picture__not_active_area'
glass=cube('D003__LCD_glass',(58.3,.32,41.0),(0,-25.25,68),'glass','display',groups['DISPLAY'],.15)
active=cube('D004__LCD_active_area_2p4in_4to3',(48.768,.12,36.576),(0,-25.46,68),'glass','display',groups['DISPLAY'],.05)
active['dimension_status']='derived_from_nominal_2.4inch_4to3__measure_actual'
for x in [-10.5,10.5]:
 loft('LCD_eye',[(-25.59,5.0,9.5,2.45,x,72.2),(-25.64,5.0,9.5,2.45,x,72.2)],'cyan','display',groups['DISPLAY'])
wire('LCD_smile',[(-4.5,-25.65,64.8),(-2.5,-25.65,62.6),(0,-25.65,62.1),(2.5,-25.65,62.6),(4.5,-25.65,64.8)],.72,'cyan','display',groups['DISPLAY'])
font_path='/System/Library/Fonts/Supplemental/Arial Unicode.ttf'
font=bpy.data.fonts.load(font_path)
font.pack()
def text_obj(name,text,loc,size,parent=None,key='labels',material='label',align='CENTER'):
 cr=bpy.data.curves.new(name,'FONT');cr.body=text;cr.font=font;cr.size=size*M;cr.align_x=align;cr.align_y='CENTER';cr.extrude=.000005
 o=bpy.data.objects.new(name,cr);cols[key].objects.link(o);o.location=Vector(loc)*M;o.rotation_euler=(math.pi/2,0,0);o.data.materials.append(mats[material]);parent_keep(o,parent);return o
text_obj('LCD_Chinese_render_content','你好呀',(0,-25.72,55.8),5.6,groups['DISPLAY'],'display','cyan')
# encoder body and knob - height is a disclosed envelope assumption
cube('D005__EC11_metal_body',(12.5,5.4,13),(43.5,-23.7,78.5),'metal','display',groups['DISPLAY'],.7)
cylinder('D006__EC11_shaft',3.0,15,(43.5,-33.7,78.5),'metal','display',groups['DISPLAY'],axis='Y')
knob=cylinder('D007__EC11_knob_envelope',7.75,13.8,(43.5,-35.1,78.5),'black','display',groups['DISPLAY'],axis='Y')
knob['dimension_status']='protrusion_21mm_assumed__physical_measurement_required'
cylinder('D008__knob_top',7.0,.5,(43.5,-42.1,78.5),'chip','display',groups['DISPLAY'],axis='Y')
cube('D009__knob_indicator',(.55,.15,4.2),(43.5,-42.42,82.0),'face','display',groups['DISPLAY'],.04)
cube('D010__K0_button_base',(12,4,12),(43.5,-23,55.8),'black','display',groups['DISPLAY'],1.1)
cylinder('D011__K0_button',3.3,5.5,(43.5,-27,55.8),'chip','display',groups['DISPLAY'],axis='Y')
cube('D012__header_housing_assumed',(3.2,4,31),(-33,-17.6,68),'chip','display',groups['DISPLAY'],.3)
for i in range(12):cube(f'D013__pin_{i:02}',(.55,7,.55),(-33,-14,54+i*2.54),'gold','display',groups['DISPLAY'],.04)
brace=ring_loft('P007__screen_module_support',
 [(-13,91.5,44.5,3.2,10.5,68),(-10,91.5,44.5,3.2,10.5,68)],
 [(-14,80,33,2,10.5,68),(-9,80,33,2,10.5,68)],
 'cream','shell',groups['DISPLAY_BRACKET'],'PRINT_CANDIDATE','屏幕支撑框：孔位按商品标称占位')

# Local relief for the assumed rear-facing display header pins.
boolean(brace,cube('CUT header clearance',(6,8,33),(-33,-11.5,68),None,'envelopes',bevel_mm=.3))

# Internal electronic envelopes; no connector or board selection implied.
def board_envelope(name,label,size,loc):
 o=cube(name,size,loc,'greenpcb','electronics',groups['ELECTRONICS'],.5,'ENVELOPE',label)
 return o
board_envelope('E001__ESP32_S3_board_ENVELOPE','ESP32-S3 主控占位，型号/尺寸待选',(62,28,1.6),(-11,10,42))
cube('E001_shield_ENVELOPE',(18,18,3),(-29,10,44.4),'metal','electronics',groups['ELECTRONICS'],.5,'ENVELOPE')
cube('E001_module_ENVELOPE',(18,20,6),(-5,10,46),'chip','electronics',groups['ELECTRONICS'],.5,'ENVELOPE')
board_envelope('E002__servo_driver_ENVELOPE','舵机驱动占位，PCA9685 仅为候选',(62,25,1.6),(0,12,66))
for x in range(-25,30,7):cube('E002_pin_bank',(4,11,7),(x,18,70.2),'chip','electronics',groups['ELECTRONICS'],.3,'ENVELOPE')
board_envelope('E003__audio_amp_ENVELOPE','I2S 功放占位，具体板型待选',(20,18,1.6),(32,-1,42))
cube('E003_chip',(8,8,2),(32,-1,43.8),'chip','electronics',groups['ELECTRONICS'],.25,'ENVELOPE')
board_envelope('E004__power_ENVELOPE','外部供电处理区域，具体电路待定',(30,17,1.6),(-26,17,87))
cube('E004_power_inductor',(11,11,5),(-26,17,90),'chip','electronics',groups['ELECTRONICS'],.8,'ENVELOPE')
speaker=cylinder('E005__speaker_ENVELOPE',14,7,(22,29,78),'black','electronics',groups['ELECTRONICS'],axis='Y',category='ENVELOPE',label='扬声器占位 Ø28×7 mm，待选型')
cylinder('E005_magnet',8,4,(22,24.5,78),'metal','electronics',groups['ELECTRONICS'],axis='Y',category='ENVELOPE')
board_envelope('E006__microphone_ENVELOPE','I2S 麦克风占位，声孔与外壳孔对齐',(15,10,1.6),(-12,-1,100.5))
cylinder('E006_mic_port',1.7,2,(-12,-1,102),'chip','electronics',groups['ELECTRONICS'],category='ENVELOPE')
cube('E007__power_connector_ENVELOPE',(11,9,6),(-30,35,47),'metal','electronics',groups['ELECTRONICS'],1.2,'ENVELOPE','电源入口占位，连接器规格待定')
cube('E007_connector_dark',(8,.5,3.2),(-30,39.7,47),'black','electronics',groups['ELECTRONICS'],1)
wire('W01_display_SPI_route',[(-33,-10,62),(-39,-3,59),(-37,4,49),(-15,9,48)],.8,'chip','electronics',groups['ELECTRONICS'])
wire('W02_speaker_route',[(22,28,74),(28,20,59),(32,0,45)],.7,'gold','electronics',groups['ELECTRONICS'])
wire('W03_microphone_route',[(-12,-1,100),(-20,-1,91),(-17,3,75),(-8,8,50)],.7,'black','electronics',groups['ELECTRONICS'])

# Ears are independent keyed pieces with shallow cream inserts.
def rounded_triangle(name,cx,y,z,w,h,depth,material,parent,part):
 pts=[Vector((-w/2,0)),Vector((w/2,0)),Vector((0,h))];outline=[]
 for i,p in enumerate(pts):
  a=p+(pts[(i-1)%3]-p)*.18;b=p+(pts[(i+1)%3]-p)*.18
  for j in range(10):
   t=j/9;q=(1-t)**2*a+2*(1-t)*t*p+t*t*b;outline.append(q)
 verts=[((q.x+cx)*M,(y+dy)*M,(q.y+z)*M) for dy in [-depth/2,depth/2] for q in outline];n=len(outline)
 faces=[tuple(reversed(range(n))),tuple(range(n,n*2))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
 mesh=bpy.data.meshes.new(name);mesh.from_pydata(verts,[],faces);mesh.update();o=bpy.data.objects.new(name,mesh);cols['shell'].objects.link(o)
 bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.recalc_face_normals(bm,faces=bm.faces);bm.to_mesh(mesh);bm.free()
 finish(o,name,material,'shell',parent,'PRINT_CANDIDATE',part);bevel(o,min(.5,depth*.27),3);return o
for side,cx in [('L',-36),('R',36)]:
 g=groups['EAR_'+side]
 ear=rounded_triangle('P008_ear_'+side,cx,-1,106.1,20,18,6,'mint',g,'独立耳框与一体定位键')
 rounded_triangle('P009_ear_insert_'+side,cx,-4.12,108.3,12.5,11.9,.7,'face',g,'奶白耳饰内片')
 boolean(ear,cylinder('FEATURE ear key',2.5,5,(cx,-1,104),'mint','shell',g),'UNION')
 boolean(hood,cylinder('CUT ear socket',2.7,10,(cx,-1,106),None,'envelopes'))

# Four 2-joint servo limb concept assemblies. Servo cases are approximate 9g-size envelopes.
def servo(name,s,y,z,parent):
 center=(s*53,y,z)
 case=cube(name+'_case',(12.2,22.8,22.5),center,'blue','hardware',parent,1.1,'ENVELOPE','微型舵机外形占位；非已选型号')
 cube(name+'_mount_flange',(12.2,31.8,2.5),(s*53,y,z+6.5),'blue','hardware',parent,.6,'ENVELOPE')
 cylinder(name+'_output_boss',5.3,3.8,(s*61,y,z+8),'blue','hardware',parent,axis='X',category='ENVELOPE')
 cylinder(name+'_shaft',2.4,2.7,(s*63.5,y,z+8),'gold','hardware',parent,axis='X')
 return case
for side,s in [('L',-1),('R',1)]:
 for fore,y,fy in [('F',-18,-43),('R',22,46)]:
  ident=fore+side;g=groups['LEG_'+ident]
  hip=empty('J_'+ident+'_HIP__rotate_local_X',(s*64,y,64),g)
  knee=empty('J_'+ident+'_KNEE__rotate_local_X',(s*75,y,43),hip)
  hip['purpose']='pose control only; travel limits and gait not validated';knee['purpose']=hip['purpose']
  servo('S_'+ident+'_HIP',s,y,56,g)
  # Structural concept envelope only: load attachment must follow actual servo selection
  mount=cube('P010_'+ident+'_servo_mount',(5,33,29),(s*44.5,y,56),'mint','legs',g,2,'ENVELOPE','机身侧舵机连接概念：承载连接与孔位未设计完成')
  mount.hide_render=True;mount.display_type='WIRE'
  mount['unresolved']='Mount is a reserved interface envelope, not a completed bracket. Rebuild after servo selection.'
  rod('P011_'+ident+'_upper_link',(s*65.3,y,64),(s*71.5,y,42),(7,15),'mint','legs',hip,'PRINT_CANDIDATE','上连杆与第二舵机连接区')
  # knee servo housing with independently selected actual part dimensions still pending
  cube('S_'+ident+'_KNEE_case',(12.2,22.8,22.5),(s*67,y,35),'blue','hardware',hip,1.0,'ENVELOPE','膝关节舵机占位')
  cylinder('S_'+ident+'_KNEE_boss',5.3,3.8,(s*74,y,43),'blue','hardware',hip,axis='X',category='ENVELOPE')
  rod('P012_'+ident+'_lower_leg',(s*78,y,43),(s*84,fy,8),(9.8,12),'mint','legs',knee,'PRINT_CANDIDATE','下腿：舵盘连接尺寸待选型')
  cylinder('P013_'+ident+'_hip_cap',9.6,4,(s*65.2,y,64),'mint','legs',hip,axis='X',category='PRINT_CANDIDATE')
  cylinder('P014_'+ident+'_knee_cap',8.7,4,(s*78,y,43),'face','legs',knee,axis='X',category='PRINT_CANDIDATE')
  screw('H_'+ident+'_hip_screw',(s*68,y,64),hip,axis='X',r=2.5)
  screw('H_'+ident+'_knee_screw',(s*80.8,y,43),knee,axis='X',r=2.3)
  foot=cube('F_'+ident+'_rubber_pad',(14,17,7),(s*84,fy,3.5),'rubber','hardware',knee,3.2,label='独立软脚垫占位')
  wire('W_servo_'+ident,[(s*49,y,48),(s*42,y,43),(s*33,12,68)],.8,'gold','hardware',g)

# Groups define repeatable assembly / disassembly poses, separate from joint controls.
explodes={
 'HOOD':(0,40,65),'FRONT_COVER':(0,-83,0),'FRONT_TRIM':(0,-85,0),'SCREEN_WELL':(0,-48,0),
 'DISPLAY':(0,-24,0),'DISPLAY_BRACKET':(0,0,0),'BOTTOM':(0,10,-32),'ELECTRONICS':(0,36,8),
 'EAR_L':(-8,42,97),'EAR_R':(8,42,97),
 'LEG_FL':(-37,-20,0),'LEG_FR':(37,-20,0),'LEG_RL':(-37,30,0),'LEG_RR':(37,30,0),
}
for name,g in groups.items():
 for frame in [1,40,70,100]:
  offset=(0,0,0)
  if frame==40 and name in ['FRONT_COVER','FRONT_TRIM','SCREEN_WELL']:offset=(0,-85,0)
  if frame==70 and name=='BOTTOM':offset=(0,0,-29)
  if frame==100:offset=explodes[name]
  if name.startswith('LEG_'):
   lateral=-P['leg_lateral_offset'] if name.endswith('L') else P['leg_lateral_offset']
   offset=(offset[0]+lateral,offset[1],offset[2])
  g.location=Vector(offset)*M;g.keyframe_insert('location',frame=frame)
for frame,label in [(1,'01 ASSEMBLED'),(40,'02 FRONT COVER REMOVED'),(70,'03 BOTTOM REMOVED'),(100,'04 EXPLODED')]:scene.timeline_markers.new(label,frame=frame)
scene.frame_set(1)

# Hidden outline guides make assumptions visible in the viewport without pretending to be real parts.
for name,dim,loc in [('G_body_envelope',(118,84.2,76),(0,-4.1,68)),('G_main_PCB_reserved',(84,37,8),(0,10,41)),('G_encoder_clearance',(18,24,18),(43.5,-31,78.5))]:
 o=cube(name,dim,loc,None,'envelopes',bevel_mm=0,category='ENVELOPE');o.display_type='WIRE';o.hide_render=True;o.hide_set(True)
# Studio
floor=cube('Studio floor',(50000,50000,4),(0,0,-2),'floor','studio',bevel_mm=0)

def area(name,loc,energy,size,color):
 d=bpy.data.lights.new(name,'AREA');d.energy=energy;d.shape='DISK';d.size=size*M;d.color=color
 o=bpy.data.objects.new(name,d);cols['studio'].objects.link(o);o.location=Vector(loc)*M;o.rotation_euler=(Vector((0,0,65))*M-o.location).to_track_quat('-Z','Y').to_euler()
area('Key large softbox',(-240,-270,340),1.5,320,(1,.91,.80))
area('Fill cool softbox',(280,-120,190),.7,240,(.80,.92,1))
area('Rim upper rear',(-40,270,300),2.,240,(1,1,1))

def camera(name,loc,target,ortho=None,lens=58):
 d=bpy.data.cameras.new(name);o=bpy.data.objects.new(name,d);cols['studio'].objects.link(o);o.location=Vector(loc)*M
 o.rotation_euler=(Vector(target)*M-o.location).to_track_quat('-Z','Y').to_euler();d.lens=lens;d.clip_start=.001;d.clip_end=100
 if ortho:d.type='ORTHO';d.ortho_scale=ortho*M
 return o
cams={
 'hero':camera('CAM_01_HERO',(148,-455,204),(0,-1,62),lens=59),
 'front':camera('CAM_02_FRONT',(0,-5000,140),(0,-3,65),ortho=250),
 'side':camera('CAM_03_SIDE',(440,-40,121),(0,0,62),ortho=208),
 'rear':camera('CAM_04_REAR',(180,450,191),(0,3,65),lens=61),
 'front_open':camera('CAM_05_FRONT_OPEN',(-192,-395,221),(0,-40,68),ortho=282),
 'bottom_open':camera('CAM_06_BOTTOM_OPEN',(188,-300,-115),(0,-2,48),ortho=245),
 'exploded':camera('CAM_07_EXPLODED',(-270,-500,310),(0,-13,108),ortho=405),
 'layout':camera('CAM_08_LAYOUT',(-210,-380,240),(0,-2,66),ortho=278),
}
scene.camera=cams['hero']
# Documentary labels are in an explicitly separate, hidden render collection.
for t,loc in [('DISPLAY PCB 91 x 44',(-5,-7,103)),('CONTROL BOARDS: ENVELOPES',(0,35,115))]:text_obj('LABEL_'+t,t,loc,4.2,root)
cols['labels'].hide_render=True;cols['labels'].hide_viewport=True
# Ensure opening the blend shows material colours and an assembled model.
for screen in bpy.data.screens:
 for ar in screen.areas:
  if ar.type=='VIEW_3D':
   ar.spaces.active.shading.type='MATERIAL'
   ar.spaces.active.region_3d.view_perspective='CAMERA'
   ar.spaces.active.overlay.show_overlays=False
   ar.spaces.active.region_3d.view_camera_zoom=5
   ar.spaces.active.region_3d.view_distance=.30
   ar.spaces.active.region_3d.view_location=Vector((0,0,62))*M
   ar.spaces.active.clip_start=.001
for o in bpy.context.selected_objects:o.select_set(False)
hood.select_set(True);bpy.context.view_layer.objects.active=hood
scene.frame_set(1);scene.camera=cams['hero']
scene['stage']='STAGE_1_ASSEMBLY_REVIEW__NO_PRINT_RELEASE'
scene['selected_cmf']='A cream mint; see design-selection.json'
scene['assumptions']='Board 91x44 nominal; LCD offset and 21mm encoder protrusion assumed; servo/electronics not selected.'
# Apply shading normals only after all Boolean and bevel geometry operations.
for obj in bpy.data.objects:
 if obj.type=='MESH' and obj.get('category') not in ['ENVELOPE']:
  normal=obj.modifiers.new('Final weighted normals','WEIGHTED_NORMAL');normal.keep_sharp=True
# Pack the font; render graphics are native objects, no external bitmap dependencies.
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'desktop-assistant-assembly-v1.blend'))

# Measurements / topology from evaluated geometry; studio and text excluded from physical dimensions.
deps=bpy.context.evaluated_depsgraph_get()
records=[]
for obj in bpy.data.objects:
 if obj.type!='MESH' or 'category' not in obj:continue
 ev=obj.evaluated_get(deps);mesh=ev.to_mesh();bm=bmesh.new();bm.from_mesh(mesh)
 dims=[round(x/M,4) for x in obj.dimensions]
 records.append({'object':obj.name,'category':obj['category'],'label_zh':obj.get('label_zh',''),
  'part_id':obj.get('part_id',''),'dimensions_mm':dims,
  'non_manifold_edges':sum(not e.is_manifold for e in bm.edges),
  'zero_area_faces':sum(f.calc_area()<1e-14 for f in bm.faces),
  'volume_mm3':round(abs(bm.calc_volume(signed=True))/M**3,4),
  'dimension_status':obj.get('dimension_status','design_assumption')})
 bm.free();ev.to_mesh_clear()
(OUT/'reports/object-inventory.json').write_text(json.dumps(records,ensure_ascii=False,indent=2))
(OUT/'reports/design-parameters.json').write_text(json.dumps(P,ensure_ascii=False,indent=2))
with (OUT/'reports/component-list.csv').open('w',encoding='utf-8-sig',newline='') as f:
 w=csv.writer(f);w.writerow(['object','category','part_id','label_zh','x_mm','y_mm','z_mm','non_manifold_edges','dimension_status'])
 for r in records:w.writerow([r['object'],r['category'],r['part_id'],r['label_zh'],*r['dimensions_mm'],r['non_manifold_edges'],r['dimension_status']])
print('BUILD_COMPLETE',len(records),'mesh objects',sum(r['category']=='PRINT_CANDIDATE' for r in records),'print candidate objects',flush=True)
args=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
if '--preview' in args:
 scene.render.resolution_percentage=55;scene.cycles.samples=20;scene.render.filepath=str(OUT/'previews/hero-preview.png');bpy.ops.render.render(write_still=True)
if '--render' in args:
 for key,frame in [('hero',1),('front',1),('side',1),('rear',1),('front_open',40),('bottom_open',70),('exploded',100),('layout',1)]:
  scene.frame_set(frame);scene.camera=cams[key]
  floor.hide_render=key in ['bottom_open','exploded']
  cols['shell'].hide_render=(key=='layout')
  scene.render.filepath=str(OUT/'renders'/f'{key}.png');bpy.ops.render.render(write_still=True)
 scene.frame_set(1);scene.camera=cams['hero'];floor.hide_render=False;cols['shell'].hide_render=False
 bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'desktop-assistant-assembly-v1.blend'))
