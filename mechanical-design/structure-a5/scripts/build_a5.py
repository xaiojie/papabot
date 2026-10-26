"""A5 enclosure: true millimetre interfaces, nominal purchased envelopes, no PCB edits.
Run with Blender --background --disable-autoexec --python scripts/build_a5.py.
All model dimensions below are mm; native scene is metres, STL exports are mm.
"""
exec(compile((__import__('pathlib').Path(__file__).parent/'core.py').read_text(),str(__file__),'exec'))
SOURCE=OUT.parent/'structure-a3/DesktopAssistant-整机结构-A3.blend'
PROTECTED=[OUT.parent/"structure-a4/DesktopAssistant-整机结构-A4.blend",SOURCE,PROJECT/'pcb-design/integrated-v1/user-latest-review-2026-09-13/User_latest_PCB1.source',PROJECT/'采购清单-20260912/最新BOM总表.md']
hashes={str(p.relative_to(PROJECT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in PROTECTED}
PCB_Z=80.5;PCB_DY=4.0
HOLES=[(x,y) for x in [-51,51] for y in [-29.5,37.5]]
CARRIER_FIX=[(-51,0),(51,0)]
BASE_FIX=[(-58.5,0),(58.5,0)]
FRONT_FIX=[(-56.5,94),(56.5,94),(-54,68),(54,68)]
LEG_POS=[('FL',-1,-1,-22),('FR',1,-1,-22),('RL',-1,1,22),('RR',1,1,22)]

def native_box(name,d,loc,mat=cream):
 o=cube(name,d,loc,mat=mat);return o
def rc(name,w,h,r,y0,y1,x=0,z=68):return loft(name,[(y0,w,h,r,x,z),(y1,w,h,r,x,z)])
def attach_nut(o,af,depth,loc,axis='Z'):hex_hole(o,af,depth,loc,axis)
def refcyl(name,r,h,loc,axis='Z',mat=black):
 o=cyl('REF__'+name,r,h,loc,axis,c=refs);assign(o,mat);electronics.append(o);o['never_print']=True;return o
def recess_slot(o,d,loc):boolean(o,cube('CUT rectangular',d,loc))


def transform_group(objects,mat):
 bpy.context.view_layer.update()
 for o in objects:o.matrix_world=mat@o.matrix_world
 bpy.context.view_layer.update()
def since(items):return [o for o in list(scene.objects) if o not in items and o.type=='MESH']
def translate_group(objects,d):transform_group(objects,Matrix.Translation(Vector(d)*M))
# A5 numerical layout is a new fit revision; purchased parts are never scaled.
# Wider, shorter lift-off shell. Hip cases sit within its side silhouette.
hood=ring('R01__124mm_lift_off_housing',[(y,124,76,10,0,68) for y in [-53.3,53.3]],[(y,119.2,71.2,7.6,0,68) for y in [-55,55]])
recess_slot(hood,(130,120,40),(0,0,14.8))
for x,y in BASE_FIX:
 addbox(hood,(5.8,9,8),(x,y,38.9));addbox(hood,(5,9,6),((1 if x>0 else -1)*59,y,38))
 hole(hood,1.4,20,(x,y,38));attach_nut(hood,5.2,2.4,(x,y,40.5))
 recess_slot(hood,(8,5.2,2.4),(x-(2 if x>0 else -2),y,40.5))
for y in [-50.4,50.4]:
 for x,z in FRONT_FIX:
  addbox(hood,(7,5.8,7),(x,y,z));addbox(hood,(7,5.8,7),((1 if x>0 else -1)*57,y,z))
  hole(hood,1.65,15,(x,y,z),'Y');attach_nut(hood,5.8,2.8,(x,y+(1 if y<0 else -1)*1.5,z),'Y')
for ident,sg,sy,yh in LEG_POS:
 recess_slot(hood,(22,15,36),(sg*62,yh,63))
 # Open-bottom lower relief clears the knee swept envelope and shell lift path.
 recess_slot(hood,(28,43,46),(sg*62,sy*31,39))
for x in [-40,40]:hole(hood,2.7,12,(x,-33,105))
for sg in [-1,1]:
 for z in [94,99]:recess_slot(hood,(10,34,2),(sg*61,12,z))
assign(hood,cream);register(hood,'R01','124 mm 宽体可拆上壳','front_down',note='124×112×76机身；壁2.4；底部2×M2.5；充电口移到可拆后盖。')
base=rc('R05__load_floor',123.4,75.4,9.7,-53.3,53.3)
boolean(base,cube('CUT floor slab',(130,120,4.6),(0,0,32.3)),'INTERSECT')
for x,y in BASE_FIX+CARRIER_FIX:hole(base,1.7,15,(x,y,32.3))
for ident,sg,sy,yh in LEG_POS:
 for yy in [sy*6,sy*14]:
  hole(base,1.7,12,(sg*37,yy,32));hole(base,3,2.1,(sg*37,yy,33.65))
  refcyl(ident+'_M3_LOW_HEAD_'+str(yy),2.75,1.8,(sg*37,yy,33.5),mat=silver)
for ident,sg,sy,yh in LEG_POS:
 recess_slot(base,(8,23,12),(sg*56.25,yh,32))
 recess_slot(base,(28.95,38,12),(sg*55.525,sy*38,32))
# Tray fasteners are placed from A5 coordinates, independent of A4 floor holes.
for x,y in [(-8,-29),(-8,9),(-25,31),(31,31),(35.5,-35),(35.5,15)]:hole(base,.85,12,(x,y,32))
assign(base,mint);register(base,'R05','宽体承力底盘','Z',note='4.6mm底；上壳、主板架、腿座及下层托盘独立固定。')
# Two elevated side rails connect four PCB holes to posts between the hip servos.
carrier=cube('R06__rotated_PCB_carrier',(4.8,67,4),(-51,4,77.5))
addbox(carrier,(4.8,67,4),(51,4,77.5));addbox(carrier,(108,7,4),(0,0,77.5))
for x,y in CARRIER_FIX:
 addcyl(carrier,3.5,41.2,(x,y,55.5));addbox(carrier,(6,18,7),(x,y,38.4))
 addbox(carrier,(8,8,4),(x-(1.5 if x>0 else -1.5),y,77.5))
 hole(carrier,1.7,11,(x,y,38));attach_nut(carrier,5.8,2.8,(x,y,38.5))
 recess_slot(carrier,(6,5.8,2.8),(x+(2 if x>0 else -2),y,38.5))
for x,y in HOLES:
 addcyl(carrier,2.7,2,(x,y,79.5));hole(carrier,1.4,10,(x,y,79))
 attach_nut(carrier,5.2,2.3,(x,y,77.3));recess_slot(carrier,(5,5.2,2.3),(x+(2 if x>0 else -2),y,77.3))
assign(carrier,mint);register(carrier,'R06','主板横置支架 102×67','inverted',note='板底Z80.5；四孔102×67；支柱移至髋舵机之间。4×M2.5固定PCB，2×M3固定底盘。')
before=set(scene.objects)
pcb=reference('PCB_USER_110x75x1p6',(75,110,1.6),(0,4,77.3),green,'CURRENT_PCB_GEOMETRY_VERIFIED')
for x,y in [(x,y+4) for x in [-33.5,33.5] for y in [-51,51]]:hole(pcb,1.6,8,(x,y,77))
pcb['coordinate_transform']='X=v-37.5; Y=59-u; Z=76.5+w'
# Actual user Gerber top image is mapped to the board, including the user's silk text.
tex=bpy.data.materials.new('A5 actual user Gerber top');tex.use_nodes=True
bs=tex.node_tree.nodes.get('Principled BSDF');im=tex.node_tree.nodes.new('ShaderNodeTexImage')
im.image=bpy.data.images.load(str(PROJECT/'pcb-design/integrated-v1/user-latest-review-2026-09-13/User_latest_Gerber_Top.png'));im.image.pack()
tex.node_tree.links.new(im.outputs['Color'],bs.inputs['Base Color']);bs.inputs['Roughness'].default_value=.5
pcb.data.materials.clear();pcb.data.materials.append(green);pcb.data.materials.append(tex);uv=pcb.data.uv_layers.new(name='ActualGerberUV');uv.active_render=True
for poly in pcb.data.polygons:
 poly.material_index=1 if poly.normal.z>.9 else 0
 for li in poly.loop_indices:
  q=pcb.matrix_world@pcb.data.vertices[pcb.data.loops[li].vertex_index].co/M
  uv.data[li].uv=((59-q.y)/110,1-(q.x+37.5)/75)

rows=list(csv.DictReader((PROJECT/'pcb-design/integrated-v1/final-no-encoder-2026-09-12/器件坐标_结构参考.csv').open(encoding='utf-8-sig')))
component_refs=[]
for row in rows:
 ref,u,v,rot,layer,fp=list(row.values());u=float(u);v=float(v);rot=float(rot);x=v-37.5;y=59-u
 # Planar location follows user PCB. Heights are mechanical reserves, explicitly nominal.
 if ref in ['C9','C10']:
  o=refcyl('PCB_'+ref,4,12,(x,y,84.1));o['height_basis']='BOM 8x12 nominal'
  component_refs.append(o);continue
 if ref=='F1':d=(8,20,18)
 elif ref=='L1':d=(10,11,12)
 elif ref in ['J1','J2']:d=(50.8,2.5,8.5)
 elif ref in ['J4','J5']:d=(15.24,2.5,8.5)
 elif ref=='J3':d=(6,28,8)
 elif ref=='J6':d=(7.35,9.0,3.4)
 elif ref=='JBAT':d=(8,10,9)
 elif ref=='JBAL':d=(6,10,8)
 elif ref in ['J7','J10']:d=(6,7.5,8)
 elif ref.startswith('J_'):d=(10,10,12)
 elif ref.startswith('SV'):d=(2.5,7.62,8.5)
 elif ref.startswith('JP'):d=(2.5,5.08,8.5)
 elif ref=='U7':d=(6.4,9.7,1.5)
 elif ref in ['Q1','Q2']:d=(6,5,1.6)
 elif ref.startswith('U'):d=(3,3,1.2)
 elif ref.startswith('Q'):d=(2,3,1.2)
 else:d=(1.3,2.1,.8)
 o=reference('PCB_'+ref,d,(x,y,78.1+d[2]/2),silver if ref=='J6' else black,'PLANAR_COORDINATE_VERIFIED_HEIGHT_NOMINAL')
 o['footprint']=fp;o['pcb_rotation_deg']=rot;component_refs.append(o)
# MCU's two long sockets lie along X at Y -13.78 and +4.
reference('ESP32_BOARD_51p9x20p5',(51.9,20.5,1.6),(-10,-4.89,88.4),green,'VENDOR_NOMINAL_STACK_NOT_MEASURED')
reference('ESP32_COMPONENT_AND_USB_HEIGHT',(48,18,5),(-10,-4.89,91.7))


transform_group(since(before),Matrix.Translation(Vector((4,4,4))*M)@Matrix.Rotation(math.pi/2,4,'Z'))
pcb['coordinate_transform']='X=u-55; Y=v-33.5; Z=80.5+w'
before=set(scene.objects)
# Front carries a replaceable black bezel and screen compression cradle.
# Datasheet drawing's AA/VA differ from its table; adjustable clamps avoid false hole precision.
front=rc('R02__shallow_front_panel',124,76,10,-66,-63.6)
boolean(front,rc('CUT bezel',60.8,44.8,3.4,-69,-60,x=2.62,z=76))
boolean(front,rc('CUT bezel flange rebate',64.4,48.4,3.8,-64.4,-63.2,x=2.62,z=76))
for x,z in FRONT_FIX:hole(front,1.65,10,(x,-65,z),'Y')
for x,z in [(-34,50),(34,50),(-34,100.5),(37.5,100.5)]:
 addcyl(front,2.8,4.5,(x,-61.8,z),'Y');hole(front,.85,4.2,(x,-60.8,z),'Y')
for x in [-3,0,3]:hole(front,.7,8,(x,-65,45),'Y')
assign(front,face);register(front,'R02','浅前脸、压屏固定点和麦克风孔','front_down',note='前表面Y−56；不保留EC11或按钮；4×M3×10固定。')
bezel=ring('R07__replaceable_black_screen_bezel',[(y,60.2,44.2,3,2.62,76) for y in [-65.7,-64.1]],[(y,51,38.7,1,2.62,76) for y in [-67,-62]])
lip=ring('ADD rear flange',[(y,63.8,47.8,3.5,2.62,76) for y in [-64.3,-63.7]],[(y,51,38.7,1,2.62,76) for y in [-65,-61]])
boolean(bezel,lip,'UNION')
boolean(bezel,rc('CUT front protective lens seat',57.6,42.6,2.2,-66.2,-64.7,x=2.62,z=76))
assign(bezel,black);register(bezel,'R07','黑色可换屏幕遮边','front_down',note='外边低于前框0.3 mm；57.6×42.6的浅槽放57×42×0.8透明PC片，面低0.45 mm；后方开窗51×38.7。')
# A separately retained clear PC lens makes the outer screen window nearly flush.
clear=material('A5 clear protective PC','#F6FAF9');bs=clear.node_tree.nodes.get('Principled BSDF');bs.inputs['Transmission Weight'].default_value=1;bs.inputs['IOR'].default_value=1.49;bs.inputs['Roughness'].default_value=.08
lens=rc('REF__HS24_PROTECTIVE_PC_SHEET',57,42,2,-65.55,-64.75,x=2.62,z=76);move(lens,refs);assign(lens,clear);electronics.append(lens);lens['never_print']=True;lens['status']='NEW_CUT_PC_SHEET_57x42x0p8_NOT_PURCHASED'
# Optical centre is shifted +2.62 mm relative to centred module, following PDF drawing.
screenpcb=reference('HS24S010B_BACKPLATE_72p26x43',(72.26,1.2,43),(0,-60.4,76),green,'SUPPLIED_PDF_DRAWING_NOMINAL_CONFLICTING_TITLE')
glass=reference('HS24S010B_LCD_60p39',(60.39,2.5,42),(-.065,-62.25,76),black,'SUPPLIED_PDF_DRAWING_NOMINAL')
screenface=reference('HS24S010B_VISIBLE_AREA',(49.96,.10,37.72),(2.62,-63.56,76),black,'DISPLAY_ONLY_NOT_PRINT')
# Right side single-row CN1 and removable female connection reserved to Y -52.
header=reference('SCREEN_CN1_10PIN_AND_LOW_PROFILE_PLUG',(4.6,7.7,25.4),(34.13,-55.95,76),black,'LOW_PROFILE_CONNECTOR_REQUIRED_FIT_PENDING')
cradle=ring('R04__screen_back_clamping_cradle',[(y,75.5,52,3,0,76) for y in [-59.3,-57.1]],[(y,65,40.5,1,0,76) for y in [-61,-55]])
# Keep both candidate header edges open. Screen supported at short corner ledges, EVA contact.
for xx in [-34.13,34.13]:recess_slot(cradle,(7,10,30),(xx,-58,76))
for x,z in [(-34,50),(34,50),(-34,100.5),(37.5,100.5)]:
 addcyl(cradle,2.8,2.2,(x,-58.2,z),'Y');hole(cradle,1.2,12,(x,-58,z),'Y')
assign(cradle,mint);register(cradle,'R04','HS24S010B 可换背压框','back_down',note='72.26×43标称背板；四角0.5mm EVA，禁止压玻璃/焊点；4×M2×6自攻。CN1插头深度须≤7.7mm或改弯脚线束。')


translate_group(since(before),(0,10,0))
before=set(scene.objects)
# Battery: independent soft-lined tray. Low centre of mass, no external protector rack.
bt=cube('R21__ACE800_replaceable_battery_tray',(36.8,65,2.4),(-10,-15,36.1))
for x in [-27.4,7.4]:addbox(bt,(2,65,5),(x,-15,39.3))
for y in [-46.5,16.5]:addbox(bt,(36.8,2,5),(-10,y,39.3))
recess_slot(bt,(20,8,8),(-10,17,40))
for x in [-29,9]:
 addbox(bt,(6,10,2.4),(x,-15,36.1));hole(bt,1.2,8,(x,-15,36))
for y in [-32,2]:
 for x in [-24,4]:recess_slot(bt,(2.5,6,7),(x,y,36))
assign(bt,mint);register(bt,'R21','ACE800 可换电池托盘','Z',note='内净32.8×61；按标称60×32×16包络，各侧需试配后微调；0.8mm EVA；两条束带，不能压电池引线。')
reference('BATTERY_ACE800_60x32x16',(32,60,16),(-10,-15,46.1),amber,'PROVISIONAL_ACE800_NOT_PURCHASE_CONFIRMATION')
reference('BATTERY_EVA',(32,60,.8),(-10,-15,37.7),black)


transform_group(since(before),Matrix.Translation(Vector((-23,0,0))*M)@Matrix.Rotation(math.pi/2,4,'Z'))
def module_tray(id,label,d,center,fix):
 x,y,z=center;w,l,h=d
 o=cube(id+'__adjustable_strap_tray',(w+4,l+4,2.2),(x,y,z-h/2-2))
 for xx in [x-w/2-1.2,x+w/2+1.2]:addbox(o,(1.6,l+4,3),(xx,y,z-h/2-.3))
 for fx,fy in fix:
  addbox(o,(7,8,2.2),(fx,fy,z-h/2-2));addcyl(o,2.8,z-h/2-1-34.9,(fx,fy,(z-h/2-1+34.9)/2));hole(o,1.2,12,(fx,fy,z-h/2-2))
 for yy in [y-l/2+4,y+l/2-4]:
  for xx in [x-w/2+3,x+w/2-3]:recess_slot(o,(2.2,5,9),(xx,yy,z-h/2-2))
 assign(o,mint);register(o,id,label,'Z',note='2×M2自攻螺丝可拆；EVA+束带；尺寸为标称/预留，实物接线和端子另核。')
 reference(id+'_MODULE_RESERVATION',d,center,black);return o
module_tray('R17','DFR0753 开放绑带托架',(50,30,10),(3,31,45.8),[(-25,31),(31,31)])
module_tray('R18','好盈 UBEC 开放绑带托架',(17,43,7),(35.5,-10,41.3),[(35.5,-35),(35.5,15)])

before=set(scene.objects)
recess_slot(next(r['object'] for r in parts if r['id']=='R18'),(12,14,14),(47,-31.5,39))

# Rear panel, replaceable switch insert, speaker clamp and amplifier shelf.
rear=rc('R03__rear_service_panel',124,76,10,63.6,66)
for x,z in FRONT_FIX:hole(rear,1.65,10,(x,65,z),'Y')
for dx in [-6,-3,0,3,6]:
 for dz in [-6,-3,0,3,6]:
  if dx*dx+dz*dz<60:hole(rear,.85,10,(-35+dx,65,60+dz),'Y')
for z in [82,87,92]:recess_slot(rear,(36,10,2),(0,65,z))
cup=cyl('ADD speaker ring',14,11.2,(-35,58.1,60),'Y');hole(cup,12.2,15,(-35,58,60),'Y');boolean(rear,cup,'UNION')
for z in [44.8,76]:
 addcyl(rear,2.7,11,(-35,58.1,z),'Y');hole(rear,.85,18,(-35,58,z),'Y')
assign(rear,face);register(rear,'R03','可拆后盖、散热及喇叭座','back_down',note='喇叭后置，避开膝关节；4×M3×10；开关板独立，未定型号可只换小板。')
sp=refcyl('SPEAKER_23p6x10p4',11.8,10.4,(-35,58.1,60),'Y')
ret=cyl('R11__24mm_speaker_clamp',14,2,(-35,51,60),'Y');hole(ret,8,8,(-35,51,60),'Y')
for z in [44.8,76]:addcyl(ret,2.7,2,(-35,51,z),'Y');hole(ret,1.2,10,(-35,51,z),'Y')
assign(ret,mint);register(ret,'R11','24 mm 级喇叭后压圈','front_down',note='候选23.6×10.4；2×M2×8自攻轻压壳边，不能压振膜；型号变更替换此件。')

# Small rear upper amp holder; front bottom microphone holder.
amp=cube('R19__amp_backplate',(28,2.2,23),(17,59.2,90))
for x in [4,30]:
 addbox(rear,(5,3,5),(x,62.1,90));hole(rear,.85,9,(x,62,90),'Y');hole(amp,1.2,8,(x,59.2,90),'Y')
for z in [81,97]:recess_slot(amp,(3,9,2),(17,59.2,z))
assign(amp,mint);register(amp,'R19','功放后盖绑带架','back_down',note='2×M2×6；预留端子高度，不与外部独立PCA板混淆。')
reference('MAX98357_AND_TERMINALS',(20,8,14),(17,53.8,94))

translate_group(since(before),(0,-10,0))
before=set(scene.objects)
mic=cube('R14__front_mic_tray',(23,2,12),(0,-57,44))
for x in [-11,11]:
 addbox(front,(5,5.4,5),(x,-51,44));hole(front,.85,4,(x,-50.1,44),'Y');hole(mic,1.2,8,(x,-57,44),'Y')
for x in [-6,6]:recess_slot(mic,(2,8,7),(x,-58,44))
assign(mic,mint);register(mic,'R14','前部可换麦克风托架','front_down',note='可调绑带+EVA；按MSM261S4030H0实际模块调整导声垫，非承诺旧Ø14模块适配。')
reference('MIC_MODULE_RESERVE',(16,3,12),(0,-61,44))


translate_group(since(before),(0,10,0))
# Recessed existing S1A candidate: lever remains inside the rear silhouette.
# Electrical function is retained on J_SW; no unverified miniature power switch substituted.
recess_slot(rear,(34.6,10,26.6),(0,55,64.5))
recess_slot(rear,(40.6,3,32.6),(0,55.5,64.5))
for x in [-19,19]:
 addbox(rear,(4,5.3,7),(x,50.95,64.5));hole(rear,.85,12,(x,53,64.5),'Y')
swplate=rc('R08__recessed_power_switch_bay',40,32,3,54,55.7,x=0,z=64.5)
boolean(swplate,rc('CUT switch access',30,22,2,50,59,x=0,z=64.5))
wall=ring('ADD recess walls',[(y,34,26,3,0,64.5) for y in [39,54.5]],[(y,30,22,2,0,64.5) for y in [38,56]])
boolean(swplate,wall,'UNION');addbox(swplate,(34,2,26),(0,38.3,64.5))
hole(swplate,6.25,8,(0,38.3,64.5),'Y')
for x in [-19,19]:hole(swplate,1.2,8,(x,55,64.5),'Y')
assign(swplate,mint);register(swplate,'R08','内凹总电源开关仓','back_down',note='保留J_SW总开关功能；沿用S1A候选包络，拨杆不超出后盖；实际型号仍需核对。')
reference('S1A_BODY_TERMINAL_CANDIDATE',(26,23,18),(0,25.8,64.5))
refcyl('S1A_BUSHING',6,6,(0,41,64.5),'Y',silver)
refcyl('S1A_LEVER',2,12,(0,50,64.5),'Y',silver)
# J6 moves to rear-left after PCB rotation; insertion axis is +Y, away from rear legs.
recess_slot(rear,(27.6,10,16.6),(-42,55,85.3))
usb=cube('R20__USB_C_rear_insert',(27,2,16),(-42,55,85.3))
recess_slot(usb,(17,12,11),(-42,55,83.8))
for x in [-50,-34]:
 addbox(rear,(4,5,4),(x,51.5,92));hole(rear,.85,10,(x,53,92),'Y');hole(usb,1.2,10,(x,55,92),'Y')
assign(usb,mint);register(usb,'R20','J6充电USB-C可换后盖孔板','back_down',note='17×11插头入口；口中心X−42/Z83.8；插拔沿Y；2×M2×6固定。5V充电，不是主控下载口。')
plug=reference('USB_PLUG_INSERTION_GAUGE',(14,15,8),(-42,50,83.8),amber,'GAUGE_NOT_SOLID_HARDWARE')
plug.hide_render=True;plug.hide_set(True);electronics.remove(plug);move(plug,guides)
# Reuse A3 ear silhouettes at a new position, with original size and fixing interface.
with bpy.data.libraries.load(str(SOURCE),link=False) as (src,dst):
 dst.objects=[n for n in ['R12_L__ear_with_integrated_insert','R12_R__ear_with_integrated_insert','R13_L__ear_retaining_washer','R13_R__ear_retaining_washer'] if n in src.objects]
for o in dst.objects:
 side='L' if '_L__' in o.name else 'R';s=-1 if side=='L' else 1
 structs.objects.link(o);o.location+=Vector((s*4,-32,0))*M
 assign(o,mint if o.name.startswith('R12') else cream)
 register(o,'R12_'+side if o.name.startswith('R12') else 'R13_'+side,'原型小耳朵 '+side if o.name.startswith('R12') else '耳朵压垫 '+side,'front_down' if o.name.startswith('R12') else 'Z')

# Compact legs: original purchased servo dimensions, repositioned cases, new bridges.
def parent_keep(o,p):
 bpy.context.view_layer.update();mw=o.matrix_world.copy();o.parent=p;o.matrix_world=mw
def joint(name,loc,parent=None):
 o=bpy.data.objects.new(name,None);refs.objects.link(o);o.location=Vector(loc)*M;o.empty_display_type='ARROWS';o.empty_display_size=.007
 if parent:parent_keep(o,parent)
 joints.append(o);return o
def yz_beam(name,p,q,width,thickness,mat=mint):
 mid=(Vector(p)+Vector(q))/2;length=(Vector(q)-Vector(p)).length
 o=cube(name,(thickness,width,length),mid);o.rotation_euler.x=-math.atan2(q[1]-p[1],q[2]-p[2])
 bpy.context.view_layer.objects.active=o;bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
 for point in [p,q]:addcyl(o,width/2,thickness,point,'X')
 assign(o,mat);return o
legs=[]
def servo(ident,typ,s,c,y,z):
 case=reference(ident+'_'+typ+'_CASE',(22.5,12.2,22.8),(s*c,y,z))
 flange=reference(ident+'_'+typ+'_FLANGE',(2,12.2,32.4),(s*(c+8.25),y,z))
 for dz in [-13.75,13.75]:hole(flange,1.2,8,(s*(c+8.25),y,z+dz),'X')
 boss=refcyl(ident+'_'+typ+'_BOSS',5.3,3.8,(s*(c+13.15),y,z+5.7),'X')
 shaft=refcyl(ident+'_'+typ+'_SHAFT',2.4,1.45,(s*(c+15.775),y,z+5.7),'X',silver)
 return [case,flange,boss,shaft]
for ident,s,sy,yh in LEG_POS:
 hc=50.5;hk=52.8;zc=63;yk=yh+sy*18;kzc=28;axisz=33.7;xf=73.2;yf=yk+sy*10
 fixed=cube('L101_'+ident+'__compact_hip_bracket',(3,22,38),(s*(hc+4.75),yh,zc))
 recess_slot(fixed,(12,13.4,24),(s*(hc+4.75),yh,zc))
 for dz in [-13.75,13.75]:slot(fixed,1.2,(s*(hc+4.75),yh,zc+dz-.7),(s*(hc+4.75),yh,zc+dz+.7),10,'X')
 for dz in [-13.75,13.75]:
  addcyl(fixed,2.2,1.3,(s*57.1,yh,zc+dz),'X');hole(fixed,1.2,10,(s*57.1,yh,zc+dz),'X')
 addbox(fixed,(24,18,3.4),(s*44,sy*10,28.3))
 for yy in [yh-sy*9.4,yh-sy*6.2]:
  addbox(fixed,(3,3.2,18),(s*55.25,yy,37.5));recess_slot(fixed,(8,1.8,3),(s*55.25,yy,40))
 for yy in [sy*6,sy*14]:
  hole(fixed,1.7,12,(s*37,yy,29));attach_nut(fixed,5.8,2.2,(s*37,yy,27.65))
 recess_slot(fixed,(3,25,5),(s*54, yh,80.5))
 assign(fixed,mint);register(fixed,'L101_'+ident,'收拢髋固定座 '+ident,'side_down',note='MG90S原尺寸；2×M3×12固定底盘，底盘内沉头槽配D≤5.5/H≤1.8低头螺丝；底面M3螺母槽；耳孔27.5±1.4。')
 hiprefs=servo(ident,'HIP',s,hc,yh,zc)
 hj=joint('JNT_'+ident+'_HIP_X',(s*(hc+17.4),yh,68.7))
 upper=cyl('L102_'+ident+'__inboard_knee_link',12,3.6,(s*69.7,yh,68.7),'X')
 beam=yz_beam('ADD upper bridge',(s*69.7,yh,68.7),(s*69.7,yk,50.5),8,3.6);boolean(upper,beam,'UNION')
 addbox(upper,(13,20,3),(s*63.7,yk,46.2))
 collar=cube('ADD knee collar',(3,22,38),(s*58.5,yk,kzc));recess_slot(collar,(12,13.4,24),(s*58.5,yk,kzc));boolean(upper,collar,'UNION')
 hole(upper,3.2,12,(s*69.7,yh,68.7),'X')
 for sg in [-1,1]:slot(upper,1.2,(s*69.7,yh+sg*6,68.7),(s*69.7,yh+sg*8.1,68.7),12,'X')
 for dz in [-13.75,13.75]:slot(upper,1.2,(s*58.5,yk,kzc+dz-.7),(s*58.5,yk,kzc+dz+.7),12,'X')
 assign(upper,mint);register(upper,'L102_'+ident,'向内错位膝座及上腿 '+ident,'side_down',note='用原装舵盘；中心Ø6.4工具孔；2×M2螺丝接舵盘。')
 knee_refs=servo(ident,'KNEE',s,hk,yk,kzc)
 kj=joint('JNT_'+ident+'_KNEE_X',(s*(hk+17.5),yk,axisz),hj)
 lower=yz_beam('L104_'+ident+'__lower_leg_and_foot',(s*xf,yk,axisz),(s*xf,yf,6),12,4.8)
 addcyl(lower,12,4.8,(s*xf,yk,axisz),'X');recess_slot(lower,(60,100,20),(s*xf,yf,-8));addcyl(lower,8.25,4,(s*xf,yf,4))
 hole(lower,3.2,12,(s*xf,yk,axisz),'X');dy=sy*10;dz=6-axisz;ll=math.hypot(dy,dz)
 for sg in [-1,1]:slot(lower,1.2,(s*xf,yk+sg*dy/ll*6,axisz+sg*dz/ll*6),(s*xf,yk+sg*dy/ll*8.1,axisz+sg*dz/ll*8.1),14,'X')
 assign(lower,mint);register(lower,'L104_'+ident,'收拢下腿及脚掌 '+ident,'side_down',note='Ø12×2脚垫；原装舵盘，非打印花键；新腿不可默认与A3混装。')
 foot=refcyl(ident+'_SILICONE_12x2',6,2,(s*xf,yf,1))
 hh=reference(ident+'_STOCK_HIP_HORN',(1.6,18,4),(s*(hc+16.6),yh,68.7),face)
 kh=yz_beam('REF__'+ident+'_STOCK_KNEE_HORN',(s*(hk+17.2),yk-dy/ll*8,axisz-dz/ll*8),(s*(hk+17.2),yk+dy/ll*8,axisz+dz/ll*8),4,1.6,face);move(kh,refs)
 for o in [upper,*knee_refs,hh]:parent_keep(o,hj)
 for o in [lower,foot,kh]:parent_keep(o,kj)
 legs.append({'id':ident,'hip_joint':hj.name,'knee_joint':kj.name,'fixed':fixed.name,'upper':upper.name,'lower':lower.name,'foot_center_mm':[s*xf,yf,1]})

before=set(scene.objects)
# Screen expression is render-only and does not imply touch or firmware changes.
glow=material('A5 display mint','#B8FFF5');bs=glow.node_tree.nodes.get('Principled BSDF');bs.inputs['Emission Color'].default_value=(.32,1,.88,1);bs.inputs['Emission Strength'].default_value=.9
for x in [-10,10]:
 eye=rc('DISPLAY_ONLY_eye',3.2,9,1.6,-63.64,-63.60,x=x,z=79);move(eye,preview);assign(eye,glow)
for i in range(15):
 a=math.radians(210+i*120/14);o=refcyl('DISPLAY_ONLY_smile_'+str(i),.7,.05,(5*math.cos(a),-63.62,72+4*math.sin(a)),'Y',glow);move(o,preview);electronics.remove(o)


translate_group(since(before),(0,10,0))
# Local lower corner relief for the articulated knee sweep; front optical geometry is unchanged.
for panel in [front,rear]:
 for sg in [-1,1]:
  recess_slot(panel,(30,150,20),(sg*55,0,35))
  recess_slot(panel,(10,150,30),(sg*60,0,44))
for sg in [-1,1]:recess_slot(hood,(28,114,29),(sg*62,0,47))

# Blend the front knee relief into a quarter-ellipse instead of a stepped notch.
for sg in [-1,1]:
 arc=[(sg*(55-15*math.cos(math.pi/2*i/24)),45+14*math.sin(math.pi/2*i/24)) for i in range(25)]
 outline=[(sg*40,25),(sg*70,25),(sg*70,59)]+list(reversed(arc))
 vs=[(x*M,y*M,z*M) for y in [-57,-53.55] for x,z in outline];n=len(outline)
 fs=[tuple(reversed(range(n))),tuple(range(n,2*n))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
 me=bpy.data.meshes.new('CUT rounded knee relief');me.from_pydata(vs,[],fs);me.update()
 tool=bpy.data.objects.new(me.name,me);structs.objects.link(tool);clean(tool);boolean(front,tool)

# Record sources and explicit mechanical limits; exports/render scenes handled separately.
bpy.context.view_layer.update()
for rec in parts:clean(rec['object'])
manifest=[]
for rec in parts:
 o=rec['object'];manifest.append({k:v for k,v in rec.items() if k!='object'}|{'name':o.name,'assembly_bbox_mm':mesh_bounds(o)})
(OUT/'reports/complete-manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2))
(OUT/'reports/leg-interfaces.json').write_text(json.dumps(legs,ensure_ascii=False,indent=2))
(OUT/'reports/source-and-change-scope.json').write_text(json.dumps({'protected_sha256':hashes,'preserved':all(hashlib.sha256(p.read_bytes()).hexdigest()==hashes[str(p.relative_to(PROJECT))] for p in PROTECTED),'A5_source':str(SOURCE),'reused':'A3 ear silhouettes and millimetre boolean/STL workflow; all A5 chassis and leg parts rebuilt','pcb_modified':False,'bom_modified':False},ensure_ascii=False,indent=2))
(OUT/'reports/assembly-parameters.json').write_text(json.dumps({'revision':'A5','units':'mm','body_xyz':[124,112,76],'body_z':[30,106],'wall':2.4,'floor_thickness':4.6,'pcb_xyz':[110,75,1.6],'pcb_bottom_z':PCB_Z,'pcb_center_xy':[0,4],'pcb_holes_xy':HOLES,'pcb_transform':'X=u-55; Y=v-33.5','screen_module_xyz':[72.26,3.7,43],'front_outer_y':-56,'bezel_recess':.3,'glass_recess':2.5,'outer_protective_window_recess':.45,'protective_PC_sheet':[57,42,.8],'standing_outer_foot_width':162.9,'battery_nominal':[32,60,16],'purchased_servo_case':[22.5,12.2,22.8],'physical_fit_tested':False,'important_limits':['Screen PDF table/drawing title and AA/VA disagree; adjustable clamping used.','Low profile or right-angle screen harness required; plug body reserve 7.7 mm.','C165948 USB footprint compatibility is not proven by this mechanical model.','DFR0753, microphone and switch are replaceable provisional envelopes.','Servo torque, continuous movement and thermal performance need hardware tests.']},ensure_ascii=False,indent=2))

# Studio in the same scale as A3. All images are renders of this editable geometry.
def aim(o,p):o.rotation_euler=(Vector(p)*M-o.location).to_track_quat('-Z','Y').to_euler()
def camera(name,loc,target,scale):
 d=bpy.data.cameras.new(name);o=bpy.data.objects.new(name,d);studio.objects.link(o);o.location=Vector(loc)*M;aim(o,target);d.type='ORTHO';d.ortho_scale=scale*M;d.clip_start=.0001;return o
for name,loc,target,scale in [('front',(0,-400,66),(0,0,66),218),('perspective',(220,-360,215),(0,0,62),255),('rear',(240,350,200),(0,0,62),255),('internal',(210,-290,340),(0,0,62),250),('top',(0,0,450),(0,0,62),225)]:camera('A5_'+name+'_camera',loc,target,scale)
for name,loc,en,size in [('key',(-180,-200,320),.8,.22),('fill',(170,-80,240),.35,.2),('rim',(70,200,270),.7,.2)]:
 d=bpy.data.lights.new('A5 '+name,'AREA');d.energy=en;d.size=size;o=bpy.data.objects.new(name,d);studio.objects.link(o);o.location=Vector(loc)*M;aim(o,(0,0,65))
cube('A5_studio_floor',(10000,10000,2),(0,0,-1),studio,ground)
scene.camera=bpy.data.objects['A5_perspective_camera'];scene['revision']='A5';scene['status']='CAD trial assembly; physical tests pending'
scene['manufacturing_scope']='Only registered print parts; REF and DISPLAY_ONLY collections must never be printed'
for screen in bpy.data.screens:
 for ar in screen.areas:
  if ar.type=='VIEW_3D':
   ar.spaces.active.overlay.show_extras=False;ar.spaces.active.overlay.show_relationship_lines=False;ar.spaces.active.overlay.show_floor=False;ar.spaces.active.overlay.show_axis_x=False;ar.spaces.active.overlay.show_axis_y=False;ar.spaces.active.clip_start=.0001;ar.spaces.active.clip_end=10;ar.spaces.active.shading.color_type='MATERIAL'
   ar.spaces.active.region_3d.view_location=Vector((0,0,62))*M;ar.spaces.active.region_3d.view_distance=.32;ar.spaces.active.region_3d.view_rotation=scene.camera.rotation_euler.to_quaternion()
for o in studio.objects:o.hide_set(True)
bpy.ops.object.select_all(action='DESELECT');hood.select_set(True);bpy.context.view_layer.objects.active=hood
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'DesktopAssistant-整机结构-A5.blend'))
print('A5_BUILT',len(parts),flush=True)
