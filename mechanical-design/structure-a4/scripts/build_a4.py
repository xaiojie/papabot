"""A4 enclosure: true millimetre interfaces, nominal purchased envelopes, no PCB edits.
Run with Blender --background --disable-autoexec --python scripts/build_a4.py.
All model dimensions below are mm; native scene is metres, STL exports are mm.
"""
exec(compile((__import__('pathlib').Path(__file__).parent/'core.py').read_text(),str(__file__),'exec'))
SOURCE=OUT.parent/'structure-a3/DesktopAssistant-整机结构-A3.blend'
PROTECTED=[SOURCE,PROJECT/'pcb-design/integrated-v1/user-latest-review-2026-09-13/User_latest_PCB1.source',PROJECT/'hardware-selection/procurement/2026-09-12/最新BOM总表.md']
hashes={str(p.relative_to(PROJECT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in PROTECTED}
PCB_Z=76.5;PCB_DY=4.0
HOLES=[(x,y+PCB_DY) for x in [-33.5,33.5] for y in [-51,51]]
BASE_FIX=[(x,y) for x in [-42,42] for y in [-55,55]]
FRONT_FIX=[(x,z) for x in [-41.5,41.5] for z in [40,94]]
LEG_POS=[('FL',-1,-1,-26.5),('FR',1,-1,-26.5),('RL',-1,1,26.5),('RR',1,1,26.5)]

def native_box(name,d,loc,mat=cream):
 o=cube(name,d,loc,mat=mat);return o
def rc(name,w,h,r,y0,y1,x=0,z=68):return loft(name,[(y0,w,h,r,x,z),(y1,w,h,r,x,z)])
def attach_nut(o,af,depth,loc,axis='Z'):hex_hole(o,af,depth,loc,axis)
def refcyl(name,r,h,loc,axis='Z',mat=black):
 o=cyl('REF__'+name,r,h,loc,axis,c=refs);assign(o,mat);electronics.append(o);o['never_print']=True;return o
def recess_slot(o,d,loc):boolean(o,cube('CUT rectangular',d,loc))

# Lift-off upper shell. Front and back are individually removable from this shell.
hood=ring('R01__94mm_lift_off_housing',[(y,94,76,10,0,68) for y in [-63.3,63.3]],[(y,89.2,71.2,7.6,0,68) for y in [-65,65]])
recess_slot(hood,(96,140,40),(0,0,14.8))
for x,y in BASE_FIX:
 addbox(hood,(5.8,9,8),(x,y,38.9));addbox(hood,(5,9,5),(42.5*(1 if x>0 else -1),y,38))
 hole(hood,1.7,20,(x,y,38));attach_nut(hood,5.8,3,(x,y,40.5))
 recess_slot(hood,(8,5.8,3),(x-(2 if x>0 else -2),y,40.5))
for y in [-60.4,60.4]:
 for x,z in FRONT_FIX:
  addbox(hood,(7,5.8,7),(x,y,z));addbox(hood,(7,5.8,7),((1 if x>0 else -1)*42,y,z))
  hole(hood,1.65,15,(x,y,z),'Y');attach_nut(hood,5.8,2.8,(x,y+(1 if y<0 else -1)*1.5,z),'Y')
for ident,s,sy,yh in LEG_POS:
 recess_slot(hood,(25,25,52),(s*48,yh,56))
# Side access plate: long open-bottom channel permits lift-off with fixed USB PCB.
recess_slot(hood,(14,27.6,15.2),(47,46,83))
for z in [95,100]:recess_slot(hood,(12,22,2),(46,43,z))
for z in [91,97]:recess_slot(hood,(12,22,2),(-46,40,z))
for x in [-29,29]:hole(hood,2.7,12,(x,-43,105))
assign(hood,cream);register(hood,'R01','94 mm 可拆上壳','front_down',note='壁2.4；底盘4×M3；前后各4×M3；侧板先卸下再向上取壳。')

# Floor follows the curved body bottom, without scaling its load-bearing thickness.
base=rc('R05__load_floor',93.4,75.4,9.7,-63.3,63.3)
boolean(base,cube('CUT floor slab',(100,140,4.6),(0,0,32.3)),'INTERSECT')
for x,y in BASE_FIX:
 addcyl(base,4.5,4.6,(x,y,32.3));hole(base,1.7,15,(x,y,32.3))
for x,y in HOLES:hole(base,1.7,12,(x,y,32.3))
for ident,s,sy,yh in LEG_POS:
 for y in [yh-8,yh+8]:
  addbox(base,(10,9,4.6),(s*40,y,32.3));hole(base,1.7,12,(s*39,y,32))
for x,y in [(-29,-15),(9,-15),(-28,35),(28,35),(18,0),(39,0)]:hole(base,.85,12,(x,y,32))
for x,y in [(-32,6),(12,10),(-30,18),(31,14)]:
 for dx in [-3,3]:recess_slot(base,(2,6,8),(x+dx,y,32))
assign(base,mint);register(base,'R05','承力底盘与四腿固定孔','Z',note='4.6 mm 底；腿座负载传到底盘；电池和模块托盘均可拆。')

# Four-post open PCB carrier; actual hole pitch 67 x 102, PCB top support D5.4.
carrier=cube('R06__110x75_PCB_carrier',(6,102,2.4),(-33.5,4,71.2))
addbox(carrier,(6,102,2.4),(33.5,4,71.2))
for y in [-44,15]:addbox(carrier,(67,6,2.4),(0,y,71.2))
for x,y in HOLES:
 addcyl(carrier,3.5,39.3,(x,y,54.95))
 addcyl(carrier,4.5,7,(x,y,38.4))
 addcyl(carrier,2.7,3.5,(x,y,74.75))
 hole(carrier,1.7,11,(x,y,38));attach_nut(carrier,5.8,2.8,(x,y,38.5))
 recess_slot(carrier,(6,5.8,2.8),(x+(2 if x>0 else -2),y,38.5))
 hole(carrier,1.4,10,(x,y,74));attach_nut(carrier,5.2,2.3,(x,y,72.8))
 recess_slot(carrier,(5,5.2,2.3),(x+(2 if x>0 else -2),y,72.8))
assign(carrier,mint);register(carrier,'R06','四柱主板支架 67×102','inverted',note='板底Z76.5；4×M2.5×8配螺母，头径≤5.0，不用Ø6垫片；架底4×M3×10。')
pcb=reference('PCB_USER_110x75x1p6',(75,110,1.6),(0,4,77.3),green,'CURRENT_PCB_GEOMETRY_VERIFIED')
for x,y in HOLES:hole(pcb,1.6,8,(x,y,77))
pcb['coordinate_transform']='X=v-37.5; Y=59-u; Z=76.5+w'
# Actual user Gerber top image is mapped to the board, including the user's silk text.
tex=bpy.data.materials.new('A4 actual user Gerber top');tex.use_nodes=True
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

# Front carries a replaceable black bezel and screen compression cradle.
# Datasheet drawing's AA/VA differ from its table; adjustable clamps avoid false hole precision.
front=rc('R02__shallow_front_panel',94,76,10,-66,-63.6)
boolean(front,rc('CUT bezel',60.8,44.8,3.4,-69,-60,x=2.62,z=76))
boolean(front,rc('CUT bezel flange rebate',64.4,48.4,3.8,-64.4,-63.2,x=2.62,z=76))
for x,z in FRONT_FIX:hole(front,1.65,10,(x,-65,z),'Y')
for x,z in [(-34,50),(34,50),(-34,100.5),(37.5,100.5)]:
 addcyl(front,2.8,4.5,(x,-61.8,z),'Y');hole(front,.85,4.2,(x,-60.8,z),'Y')
for x in [-3,0,3]:hole(front,.7,8,(x,-65,45),'Y')
assign(front,face);register(front,'R02','浅前脸、压屏固定点和麦克风孔','front_down',note='前表面Y−66；不保留EC11或按钮；4×M3×10固定。')
bezel=ring('R07__replaceable_black_screen_bezel',[(y,60.2,44.2,3,2.62,76) for y in [-65.7,-64.1]],[(y,51,38.7,1,2.62,76) for y in [-67,-62]])
lip=ring('ADD rear flange',[(y,63.8,47.8,3.5,2.62,76) for y in [-64.3,-63.7]],[(y,51,38.7,1,2.62,76) for y in [-65,-61]])
boolean(bezel,lip,'UNION')
boolean(bezel,rc('CUT front protective lens seat',57.6,42.6,2.2,-66.2,-64.7,x=2.62,z=76))
assign(bezel,black);register(bezel,'R07','黑色可换屏幕遮边','front_down',note='外边低于前框0.3 mm；57.6×42.6的浅槽放57×42×0.8透明PC片，面低0.45 mm；后方开窗51×38.7。')
# A separately retained clear PC lens makes the outer screen window nearly flush.
clear=material('A4 clear protective PC','#F6FAF9');bs=clear.node_tree.nodes.get('Principled BSDF');bs.inputs['Transmission Weight'].default_value=1;bs.inputs['IOR'].default_value=1.49;bs.inputs['Roughness'].default_value=.08
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

def module_tray(id,label,d,center,fix):
 x,y,z=center;w,l,h=d
 o=cube(id+'__adjustable_strap_tray',(w+4,l+4,2.2),(x,y,z-h/2-2))
 for xx in [x-w/2-1.2,x+w/2+1.2]:addbox(o,(1.6,l+4,3),(xx,y,z-h/2-.3))
 for fx,fy in fix:
  addbox(o,(7,8,2.2),(fx,fy,z-h/2-2));hole(o,1.2,9,(fx,fy,z-h/2-2))
 for yy in [y-l/2+4,y+l/2-4]:
  for xx in [x-w/2+3,x+w/2-3]:recess_slot(o,(2.2,5,9),(xx,yy,z-h/2-2))
 assign(o,mint);register(o,id,label,'Z',note='2×M2自攻螺丝可拆；EVA+束带；尺寸为标称/预留，实物接线和端子另核。')
 reference(id+'_MODULE_RESERVATION',d,center,black);return o
module_tray('R17','DFR0753 开放绑带托架',(50,30,10),(0,35,42.8),[(-28,35),(28,35)])
module_tray('R18','好盈 UBEC 开放绑带托架',(17,43,7),(28.5,-16,41.3),[(18,0),(39,0)])

# Rear panel, replaceable switch insert, speaker clamp and amplifier shelf.
rear=rc('R03__rear_service_panel',94,76,10,63.6,66)
for x,z in FRONT_FIX:hole(rear,1.65,10,(x,65,z),'Y')
for dx in [-6,-3,0,3,6]:
 for dz in [-6,-3,0,3,6]:
  if dx*dx+dz*dz<60:hole(rear,.85,10,(-15+dx,65,55+dz),'Y')
for z in [82,87,92]:recess_slot(rear,(36,10,2),(0,65,z))
recess_slot(rear,(28,10,22),(16,65,65))
for x in [3,30]:
 addbox(rear,(6,3.4,7),(x,64.3,65));hole(rear,1.2,12,(x,63,65),'Y');attach_nut(rear,4.3,2.3,(x,64.5,65),'Y')
cup=cyl('ADD speaker ring',14,11.2,(-15,58.1,55),'Y');hole(cup,12.2,15,(-15,58,55),'Y');boolean(rear,cup,'UNION')
for z in [39.8,71]:
 addcyl(rear,2.7,11,(-15,58.1,z),'Y');hole(rear,.85,18,(-15,58,z),'Y')
assign(rear,face);register(rear,'R03','可拆后盖、散热及喇叭座','back_down',note='喇叭后置低位；4×M3×10；开关板独立，未定型号可只换小板。')
swplate=cube('R08__replaceable_switch_insert',(34,2,22),(16,61.3,65))
for x in [3,30]:hole(swplate,1.2,10,(x,61.3,65),'Y')
hole(swplate,6.25,8,(16,61.3,65),'Y');assign(swplate,mint);register(swplate,'R08','后开关可换接口板','back_down',note='Ø12.5为旧S1A候选；未确认采购，正式安装前重配孔或装空白板。')
reference('S1A_BODY_TERMINAL_CANDIDATE',(26,23,18),(16,48.8,65))
refcyl('S1A_BUSHING',6,6,(16,64,65),'Y',silver)
refcyl('S1A_LEVER',2,12,(16,73,65),'Y',silver)
sp=refcyl('SPEAKER_23p6x10p4',11.8,10.4,(-15,58.1,55),'Y')
ret=cyl('R11__24mm_speaker_clamp',14,2,(-15,51,55),'Y');hole(ret,8,8,(-15,51,55),'Y')
for z in [39.8,71]:addcyl(ret,2.7,2,(-15,51,z),'Y');hole(ret,1.2,10,(-15,51,z),'Y')
assign(ret,mint);register(ret,'R11','24 mm 级喇叭后压圈','front_down',note='候选23.6×10.4；2×M2×8自攻轻压壳边，不能压振膜；型号变更替换此件。')

# Small rear upper amp holder; front bottom microphone holder.
amp=cube('R19__amp_backplate',(28,2.2,23),(17,59.2,90))
for x in [4,30]:
 addbox(rear,(5,3,5),(x,62.1,90));hole(rear,.85,9,(x,62,90),'Y');hole(amp,1.2,8,(x,59.2,90),'Y')
for z in [81,97]:recess_slot(amp,(3,9,2),(17,59.2,z))
assign(amp,mint);register(amp,'R19','功放后盖绑带架','back_down',note='2×M2×6；预留端子高度，不与外部独立PCA板混淆。')
reference('MAX98357_AND_TERMINALS',(20,8,18),(17,53.8,90))
mic=cube('R14__front_mic_tray',(23,2,12),(0,-57,44))
for x in [-11,11]:
 addbox(front,(5,5.4,5),(x,-61,44));hole(front,.85,4,(x,-60.1,44),'Y');hole(mic,1.2,8,(x,-57,44),'Y')
for x in [-6,6]:recess_slot(mic,(2,8,7),(x,-58,44))
assign(mic,mint);register(mic,'R14','前部可换麦克风托架','front_down',note='可调绑带+EVA；按MSM261S4030H0实际模块调整导声垫，非承诺旧Ø14模块适配。')
reference('MIC_MODULE_RESERVE',(16,3,12),(0,-61,44))

# Side plate gives the whole USB plug overmould a path to the recessed connector.
usb=cube('R20__USB_recess_side_insert',(2.0,27,14),(46,46,83))
recess_slot(usb,(10,17,11),(46,46,79.8))
for y in [34.5,57.5]:
 addbox(hood,(4.4,10,5),(42.8,y,87));hole(hood,.85,12,(43,y,87),'X')
 hole(usb,1.2,9,(46,y,87),'X')
assign(usb,mint);register(usb,'R20','USB 插接通道可换侧板','side_down',note='17×11入口允许插头护套深入；C165948与PCB封装兼容尚无完整重合证明。2×M2×6自攻先拆侧板再提壳。')
plug=reference('USB_PLUG_INSERTION_GAUGE',(15,14,8),(46,46,79.8),amber,'GAUGE_NOT_SOLID_HARDWARE')
plug.hide_render=True;plug.hide_set(True);electronics.remove(plug);move(plug,guides)

# Reuse A3 ear silhouettes at a new position, with original size and fixing interface.
with bpy.data.libraries.load(str(SOURCE),link=False) as (src,dst):
 dst.objects=[n for n in ['R12_L__ear_with_integrated_insert','R12_R__ear_with_integrated_insert','R13_L__ear_retaining_washer','R13_R__ear_retaining_washer'] if n in src.objects]
for o in dst.objects:
 side='L' if '_L__' in o.name else 'R';s=-1 if side=='L' else 1
 structs.objects.link(o);o.location+=Vector((-s*7,-42,0))*M
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
 hc=50.5;hk=58.8;zc=63;yk=yh+sy*29;kzc=34;axisz=39.7;xf=79.2;yf=yk+sy*12
 fixed=cube('L101_'+ident+'__compact_hip_bracket',(3,22,38),(s*(hc+5.75),yh,zc))
 recess_slot(fixed,(12,13.4,24),(s*(hc+5.75),yh,zc))
 for dz in [-13.75,13.75]:slot(fixed,1.2,(s*(hc+5.75),yh,zc+dz-.7),(s*(hc+5.75),yh,zc+dz+.7),10,'X')
 addbox(fixed,(23,22,3.4),(s*46.5,yh,28.3))
 for yy in [yh-9.4,yh+9.4]:
  addbox(fixed,(3,3.2,18),(s*56.25,yy,37.5));recess_slot(fixed,(8,1.8,3),(s*56.25,yy,40))
 for yy in [yh-8,yh+8]:hole(fixed,1.7,12,(s*39,yy,29))
 assign(fixed,mint);register(fixed,'L101_'+ident,'收拢髋固定座 '+ident,'side_down',note='MG90S原尺寸；2×M3×12固定底盘；耳孔试配槽27.5±1.4。')
 hiprefs=servo(ident,'HIP',s,hc,yh,zc)
 hj=joint('JNT_'+ident+'_HIP_X',(s*(hc+17.4),yh,68.7))
 upper=cyl('L102_'+ident+'__inboard_knee_link',12,3.6,(s*69.7,yh,68.7),'X')
 beam=yz_beam('ADD upper bridge',(s*69.7,yh,68.7),(s*69.7,yk,54),8,3.6);boolean(upper,beam,'UNION')
 addbox(upper,(12,20,4),(s*65.2,yk,54))
 collar=cube('ADD knee collar',(3,22,38),(s*64.5,yk,kzc));recess_slot(collar,(12,13.4,24),(s*64.5,yk,kzc));boolean(upper,collar,'UNION')
 hole(upper,3.2,12,(s*69.7,yh,68.7),'X')
 for sg in [-1,1]:slot(upper,1.2,(s*69.7,yh+sg*6,68.7),(s*69.7,yh+sg*8.1,68.7),12,'X')
 for dz in [-13.75,13.75]:slot(upper,1.2,(s*64.5,yk,kzc+dz-.7),(s*64.5,yk,kzc+dz+.7),12,'X')
 assign(upper,mint);register(upper,'L102_'+ident,'向内错位膝座及上腿 '+ident,'side_down',note='用原装舵盘；中心Ø6.4工具孔；2×M2螺丝接舵盘。')
 knee_refs=servo(ident,'KNEE',s,hk,yk,kzc)
 kj=joint('JNT_'+ident+'_KNEE_X',(s*(hk+17.5),yk,axisz),hj)
 lower=yz_beam('L104_'+ident+'__lower_leg_and_foot',(s*xf,yk,axisz),(s*xf,yf,6),12,4.8)
 addcyl(lower,12,4.8,(s*xf,yk,axisz),'X');recess_slot(lower,(60,100,20),(s*xf,yf,-8));addcyl(lower,8.25,4,(s*xf,yf,4))
 hole(lower,3.2,12,(s*xf,yk,axisz),'X');dy=sy*12;dz=6-axisz;ll=math.hypot(dy,dz)
 for sg in [-1,1]:slot(lower,1.2,(s*xf,yk+sg*dy/ll*6,axisz+sg*dz/ll*6),(s*xf,yk+sg*dy/ll*8.1,axisz+sg*dz/ll*8.1),14,'X')
 assign(lower,mint);register(lower,'L104_'+ident,'收拢下腿及脚掌 '+ident,'side_down',note='Ø12×2脚垫；原装舵盘，非打印花键；新腿不可默认与A3混装。')
 foot=refcyl(ident+'_SILICONE_12x2',6,2,(s*xf,yf,1))
 hh=reference(ident+'_STOCK_HIP_HORN',(1.6,18,4),(s*(hc+16.6),yh,68.7),face)
 kh=yz_beam('REF__'+ident+'_STOCK_KNEE_HORN',(s*(hk+17.2),yk-dy/ll*8,axisz-dz/ll*8),(s*(hk+17.2),yk+dy/ll*8,axisz+dz/ll*8),4,1.6,face);move(kh,refs)
 for o in [upper,*knee_refs,hh]:parent_keep(o,hj)
 for o in [lower,foot,kh]:parent_keep(o,kj)
 legs.append({'id':ident,'hip_joint':hj.name,'knee_joint':kj.name,'fixed':fixed.name,'upper':upper.name,'lower':lower.name,'foot_center_mm':[s*xf,yf,1]})

# Screen expression is render-only and does not imply touch or firmware changes.
glow=material('A4 display mint','#B8FFF5');bs=glow.node_tree.nodes.get('Principled BSDF');bs.inputs['Emission Color'].default_value=(.32,1,.88,1);bs.inputs['Emission Strength'].default_value=.9
for x in [-10,10]:
 eye=rc('DISPLAY_ONLY_eye',3.2,9,1.6,-63.64,-63.60,x=x,z=79);move(eye,preview);assign(eye,glow)
for i in range(15):
 a=math.radians(210+i*120/14);o=refcyl('DISPLAY_ONLY_smile_'+str(i),.7,.05,(5*math.cos(a),-63.62,72+4*math.sin(a)),'Y',glow);move(o,preview);electronics.remove(o)

# Record sources and explicit mechanical limits; exports/render scenes handled separately.
bpy.context.view_layer.update()
for rec in parts:clean(rec['object'])
manifest=[]
for rec in parts:
 o=rec['object'];manifest.append({k:v for k,v in rec.items() if k!='object'}|{'name':o.name,'assembly_bbox_mm':mesh_bounds(o)})
(OUT/'reports/complete-manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2))
(OUT/'reports/leg-interfaces.json').write_text(json.dumps(legs,ensure_ascii=False,indent=2))
(OUT/'reports/source-and-change-scope.json').write_text(json.dumps({'protected_sha256':hashes,'preserved':all(hashlib.sha256(p.read_bytes()).hexdigest()==hashes[str(p.relative_to(PROJECT))] for p in PROTECTED),'A4_source':str(SOURCE),'reused':'A3 ear silhouettes and millimetre boolean/STL workflow; all A4 chassis and leg parts rebuilt','pcb_modified':False,'bom_modified':False},ensure_ascii=False,indent=2))
(OUT/'reports/assembly-parameters.json').write_text(json.dumps({'revision':'A4','units':'mm','body_xyz':[94,132,76],'body_z':[30,106],'wall':2.4,'floor_thickness':4.6,'pcb_xyz':[75,110,1.6],'pcb_bottom_z':PCB_Z,'pcb_center_xy':[0,4],'pcb_holes_xy':HOLES,'pcb_transform':'X=v-37.5; Y=59-u','screen_module_xyz':[72.26,3.7,43],'front_outer_y':-66,'bezel_recess':.3,'glass_recess':2.5,'outer_protective_window_recess':.45,'protective_PC_sheet':[57,42,.8],'standing_outer_foot_width':174.9,'battery_nominal':[32,60,16],'purchased_servo_case':[22.5,12.2,22.8],'physical_fit_tested':False,'important_limits':['Screen PDF table/drawing title and AA/VA disagree; adjustable clamping used.','Low profile or right-angle screen harness required; plug body reserve 7.7 mm.','C165948 USB footprint compatibility is not proven by this mechanical model.','DFR0753, microphone and switch are replaceable provisional envelopes.','Servo torque, continuous movement and thermal performance need hardware tests.']},ensure_ascii=False,indent=2))

# Studio in the same scale as A3. All images are renders of this editable geometry.
def aim(o,p):o.rotation_euler=(Vector(p)*M-o.location).to_track_quat('-Z','Y').to_euler()
def camera(name,loc,target,scale):
 d=bpy.data.cameras.new(name);o=bpy.data.objects.new(name,d);studio.objects.link(o);o.location=Vector(loc)*M;aim(o,target);d.type='ORTHO';d.ortho_scale=scale*M;d.clip_start=.0001;return o
for name,loc,target,scale in [('front',(0,-400,66),(0,0,66),218),('perspective',(220,-360,215),(0,0,62),255),('rear',(240,350,200),(0,0,62),255),('internal',(210,-290,340),(0,0,62),250),('top',(0,0,450),(0,0,62),225)]:camera('A4_'+name+'_camera',loc,target,scale)
for name,loc,en,size in [('key',(-180,-200,320),.8,.22),('fill',(170,-80,240),.35,.2),('rim',(70,200,270),.7,.2)]:
 d=bpy.data.lights.new('A4 '+name,'AREA');d.energy=en;d.size=size;o=bpy.data.objects.new(name,d);studio.objects.link(o);o.location=Vector(loc)*M;aim(o,(0,0,65))
cube('A4_studio_floor',(10000,10000,2),(0,0,-1),studio,ground)
scene.camera=bpy.data.objects['A4_perspective_camera'];scene['revision']='A4';scene['status']='CAD trial assembly; physical tests pending'
scene['manufacturing_scope']='Only registered print parts; REF and DISPLAY_ONLY collections must never be printed'
for screen in bpy.data.screens:
 for ar in screen.areas:
  if ar.type=='VIEW_3D':
   ar.spaces.active.clip_start=.0001;ar.spaces.active.clip_end=10;ar.spaces.active.shading.color_type='MATERIAL'
   ar.spaces.active.region_3d.view_location=Vector((0,0,62))*M;ar.spaces.active.region_3d.view_distance=.32;ar.spaces.active.region_3d.view_rotation=scene.camera.rotation_euler.to_quaternion()
bpy.ops.object.select_all(action='DESELECT');hood.select_set(True);bpy.context.view_layer.objects.active=hood
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'DesktopAssistant-整机结构-A4.blend'))
print('A4_BUILT',len(parts),flush=True)
