"""Write the A3 prototype handoff from verified exported geometry."""
import csv, json, hashlib
from pathlib import Path
OUT=Path(__file__).resolve().parents[1];R=OUT/'reports'
def read(name):return json.loads((R/name).read_text())
manifest=read('complete-manifest.json');stl=read('complete-stl-verification.json')
collision=read('assembly-collision-check.json');service=read('cover-service-check.json');motion=read('leg-motion-sample-check.json')
assert len(manifest)==30 and stl['mesh_check_pass'] and service['pass']
assert not collision['conflicts_over_0p05_mm3'] and motion['sampled_pose_checks_pass']
for r in stl['items']:assert hashlib.sha256((OUT/r['file']).read_bytes()).hexdigest()==r['sha256']

groups=[
 ('屏幕固定框→主壳','M2×6',4,'R04/R01，螺母在主壳内侧槽'),
 ('两块电源架→侧壁','M2×6',8,'R17/R18；外侧装螺母，模块避开螺丝头'),
 ('充电托架→后盖','M2×6',2,'R09/R03，螺母在托架内侧槽'),
 ('8个舵机安装耳','M2×8',16,'每个2颗；耳片厚度待实物复核'),
 ('8个原装双臂舵盘→连杆','M2×8',16,'每个2颗；不能替代原舵机中心螺丝'),
 ('小耳朵','M2×8',2,'R12/R13；螺母从耳朵后侧装入'),
 ('可换麦克风架','M2×8',2,'R14/R01；内侧沉孔，外侧装螺母，实物复核螺丝尖端'),
 ('主控PCB→R06','M2×8',4,'头径≤4mm、头高≤2mm；不用大垫片，保留PCB原Ø3.2孔'),
 ('喇叭压圈','M2×10',2,'R11/R03，后盖外侧装螺母'),
 ('两条充电板压条','M2×10',4,'R10/R09，托架底部装螺母'),
 ('完整屏幕原板→固定框','M3×8',4,'R04，配0.8mm垫片；旋钮与按键保持原装'),
 ('可拆后盖→主壳','M3×10',4,'R03/R01，配0.8mm垫片'),
 ('底盘→主壳','M3×10',4,'R05/R01，配0.8mm垫片；前2个固定点已转移到R01'),
 ('主控架→底盘','M3×10',4,'R06，侧装M3螺母，配0.8mm垫片'),
 ('PCA9685架→底盘','M3×10',4,'R16，侧装M3螺母，配0.8mm垫片'),
 ('四个髋座→底盘','M3×12',8,'每座2颗；底盘顶部装螺母，配0.8mm垫片'),
 ('深可拆前盖→主壳','M3×30',4,'R02/R01，必须配0.8mm垫片；无深沉孔，螺杆名义Y−47～−17')]
totals={}
for _,spec,n,_ in groups:totals[spec]=totals.get(spec,0)+n
assert totals=={'M2×6':14,'M2×8':40,'M2×10':6,'M3×8':4,'M3×10':16,'M3×12':8,'M3×30':4}
def csvwrite(name,header,rows):
 with (OUT/name).open('w',encoding='utf-8-sig',newline='') as f:
  w=csv.writer(f);w.writerow(header);w.writerows(rows)
csvwrite('紧固件安装明细.csv',['安装位置','螺丝规格','单台数量','装配备注'],groups)
hardware=[
 ('M2×6',14,'V7立创BOM列100颗','数量够；长度按实物复核'),
 ('M2×8',40,'V7未明确列此长度','建议备50颗；PCB的4颗须小头'),
 ('M2×10',6,'V7未明确列此长度','建议备10颗'),
 ('M2螺母',60,'V7淘宝列20颗','还差40颗；可加2包20颗，另备损耗'),
 ('M3×8',4,'V7立创BOM列100颗','数量够'),
 ('M3×10',16,'V7未明确列此长度','建议备20颗'),
 ('M3×12',8,'V7未明确列此长度','建议备10颗'),
 ('M3×30',4,'A3深前盖新增长度','前盖4颗；建议备6颗，配0.8mm平垫'),
 ('M3螺母',32,'V7淘宝列50颗','数量够'),
 ('M3平垫片 Ø6×0.8',32,'V7淘宝列200片','前盖按外径≤7mm预留；PCB的M2处不用此垫片'),
 ('原装双臂舵盘及中心螺丝',8,'随8个MG90S附带情况待确认','原装花键和中心螺纹，不能用普通M2代替'),
 ('Ø12×2硅胶脚垫',4,'V7淘宝列50只','每脚1只'),
 ('10×150mm电池束带',1,'V7淘宝列2条','到货后确认搭接长度'),
 ('1mm EVA薄垫',1,'V7淘宝列1卷','电池/模块边缘裁切；电源架可叠至约2mm'),
 ('2.5×100mm扎带',20,'V7淘宝列100条','走线备料，实际用量视线束确定')]
csvwrite('紧固件与辅料核对.csv',['规格','单台数量或备料数','V7记录（非到货）','当前处理'],hardware)

orientation={'Z':'沿现有底面','inverted':'倒置，支脚朝上','front_down':'正面朝下','back_down':'背面朝下','side_down':'侧面朝下'}
rows=[]
for r in sorted(manifest,key=lambda m:(not m['id'].startswith('R'),m['id'])):
 rows.append(f"| {r['id']} | {r['label_zh']} | 1 | {'×'.join(f'{v:.2f}' for v in r['dimensions_mm'])} | {orientation[r['orientation']]} |")
(OUT/'零件清单.md').write_text('''# A3 整机打印零件清单

**30个独立STL，每个打印1件。** 当前只取本目录的 `stl-complete/`。FL/FR/RL/RR为机器人自身的左前/右前/左后/右后。每个STL为单一闭合连通体，已按建议朝向旋转并在Z=0落底；导入切片器保持100%、毫米，不要放大1000倍。

| 件号 | 零件用途 | 单台数量 | 导出X×Y×Z包络 mm | 导出姿态 |
|---|---|---:|---|---|
'''+ '\n'.join(rows)+'''

相对A2，R01增加底盘前固定横梁，R02改深可拆前盖，R03取消旋钮/按键孔，R04补排针末端让位。R07、R08后置压片已取消，旋钮和按键保留在屏幕原板上。编号有空缺是有意保留历史件号。

R02集成遮光井和导声管；R05集成电池托架；R03集成喇叭套和功放固定座；L102集成上腿和膝舵机座；L104集成下腿和脚掌。无需另打印这些已集成结构。小耳内片为浅浮雕，后处理上色。

电子件、金属螺丝、原装舵盘、硅胶脚垫及画面中的屏幕内容都是装配参照，不导出为打印件。V1、A1、A2继续保留为历史，不与A3混打。
''')

table='\n'.join(f'| {s} | {n} | {old} | {note} |' for s,n,old,note in hardware)
(OUT/'装配与打印说明.md').write_text('''# A3 装配与打印说明

本版按用户确认的旧V1结构修正：**屏幕竖直正对前方，原板旋钮和按键藏在可拆前盖里面，拆盖后操作。** 前盖外表面Y−46.2，玻璃前面约Y−25.41，名义内凹20.79mm。主壳、内部模块和四腿的其余结构沿用A2；本版仍用于首轮试装。

## 打印建议

- 主壳、盖板和支架优先PETG；腿件不建议用脆性展示树脂。PLA可先试孔位。
- 初始切片参考0.4mm喷嘴、0.2mm层高；壳盖4圈壁，腿座/连杆/底盘5～6圈壁、约35%～45%填充。这些是试打起点，尚未实际切片。
- R02正面朝下，后口朝上。四根长螺丝柱、内井、导声管与前盖已连接成一个打印件；检查导声管转接处和定位唇的局部支撑。R01螺丝座、R06/R16桥架和腿座横梁也需在切片器核查支撑。
- 螺母槽不能被难以拆除的支撑堵死。清理后手推试入螺母，薄壁螺丝座轻拧。M2通孔约Ø2.4，M3多数Ø3.3～3.4，实际补偿取决于打印机和材料。
- 前盖浅线槽涂薄荷色，遮光井内壁涂哑黑；黑色和薄荷色是同一实体的表面处理。STL不带这些颜色，Blender中保留材质区域。小耳浅浮雕区可涂奶油白。

## 装配顺序

1. 预装各处螺母：R06/R16支脚从侧槽装；R01前盖与屏幕框螺母从内侧装；两路电源架和麦克风架螺母从主壳外侧装；R03喇叭螺母从后盖外侧装。
2. 先组一条腿验证MG90S耳孔、原装双臂舵盘和活动间隙。髋舵机装L101，膝舵机装L102；卸载回中后用原装舵盘和中心螺丝连接。打印连杆与舵盘各用2颗M2固定，再装其余三腿。
3. 四个L101用8颗M3×12固定到R05。电池托架先放1mm EVA与目标尺寸假体，再试合电池束带。实际电池尚未确认，不能强压软包。
4. PCB用4颗小头M2×8固定到R06，头径≤4mm，不加大垫片；PCB原Ø3.2孔不改。R06/R16各用4颗M3×10固定到底盘。PCA9685用绝缘垫和扎带固定到开放架。
5. 装小耳、R14麦克风架和R17/R18电源架。模块边缘避开螺丝头。麦克风实际拾音口对准导声管；泡棉仅封边，不能覆盖声孔。
6. **保留完整91×44mm屏幕原板、原EC11和独立按键，不拆焊控件。** 屏幕4孔固定到R04，R04再固定到R01。屏幕显示面与前盖窗口平行，正对整机−Y方向。检查排针两端的让位。
7. 底盘固定到R01主壳，前2个M3螺母座现已移到主壳。检查线束避开屏幕、旋钮和前盖长柱后，沿+Y方向合前盖，用4颗M3×30配0.8mm垫片固定。不要自行加深沉孔或换更长螺丝，避免尖端触碰内部结构。
8. 喇叭装R03套筒，用R11压住外壳边缘；不得压振膜。充电板装R09，由R10两条压住已核实无元件的边缘；MAX98357用后盖中央绑带座固定；S1A用自身安装螺母固定。后盖没有EC11/独立按键。
9. 保险和XT30线束固定在底盘后部，舵机线留活动余量。后盖线束留检修余量，检查不夹线后锁4颗M3×10。贴4只脚垫。

## 前后盖拆卸

前盖：断电后取下正面4颗M3×30及垫片，沿整机−Y水平向前抽出。内井和导声管随盖一起移出，不连接电线；屏幕、旋钮、按键和麦克风保持固定。无需拆底盘或PCB。旋钮和独立按键需拆前盖后才能接触。

后盖：断电后松4颗固定螺丝，确认线束余量或断开相关插头，再沿+Y向后移出。充电架、喇叭压圈、总开关和功放随盖移动。此版只检查了名义硬件的离散拆卸位置，未建模柔性线束。

`A3-front-open.png`中，前盖先向前退出，再放到旁边方便观看；图中的侧向摆放不是拆卸方向。Blender主装配场景保留正确装配坐标。

USB调试首轮通过拆后盖、松右侧电源架接入主控USB。后盖Type-C为独立充电口，仍按既有方案关机充电。

## 紧固件与V7清单的差额

以下记录是采购核对，不代表到货；未更改购物车或下单。A3取消两块后控件压片，用量较A2减少4颗M2×8及4个M2螺母；前盖4颗M3改为30mm长。

| 规格 | 单台数量/备料数 | V7记录 | 处理 |
|---|---:|---|---|
'''+table+'''

机牙螺丝位置共M2 60个、M3 32个，对应M2螺母60、M3螺母32及M3平垫32。具体分配见[紧固件安装明细.csv](紧固件安装明细.csv)。螺丝长度需要结合真实耳片/垫厚复核，不能顶住电路板或模块。

## 仍需实物确认

- 屏幕相对PCB的位置、真实可见区、排针高度及针序；原板安装孔标称84.5×37.5mm。屏幕原板不能裁切。
- **EC11轴长15mm不等于装板后旋钮的总高度。** A3按旧V1的旋钮包络留位，模型中旋钮最前点与盖内面约1.3mm轴向间隙；必须用所购实物核对，必要时加深前盖。
- 导声通道与真实麦克风声孔的密封和拾音效果；麦克风模块具体外形身份仍待确认。
- MG90S同批外形、耳孔、轴伸、舵盘和扭矩；电池75×40×20mm、≤80g是定制目标，不是实物结果。
- DFR0753包络为空间预留；PCA、功放、充电板元件位置、UBEC引线/磁环与线束弯曲待实测。
- 网格和名义干涉检查不代替实际切片、试装、强度、温升、连续运动、步态、RF和声学测试。
''')

params=json.loads((OUT.parent/'structure-a2/reports/assembly-parameters.json').read_text())
params.update(revision='A3',printable_files=30,fastener_counts=totals,M2_nuts=60)
params['body'].update(front_outer_y=-46.2,depth_with_covers=116.8)
params['display'].update(glass_recess_target=20.79,front_normal=[0,-1,0],pcb_center=[10.5,-20.2,68],
 original_controls_retained=True,control_relocation=False,front_window_size=[70,51],
 light_well_rear_aperture=[59.4,41.8],knob_height_basis='V1 nominal envelope; seller 15mm is shaft length only')
params['rear_controls_xz']={'S1A':[19,55],'charger':[-22,55.5],'speaker':[-35,84]}
params['original_display_controls_xz']={'EC11':[43.5,78.5],'button':[43.5,55.8]}
params['front_service']={'direction':[0,-1,0],'fasteners':'4 M3x30 + 0.8mm washers','floor_boss_owner':'R01',
 'light_well_and_acoustic_duct_integrated':True,'knob_to_front_inner_face_axial_gap_mm':service['knob_to_front_plate_inner_face_axial_gap_mm']}
params['minimum_designed_load_walls_mm'].pop('rear_control_and_speaker_nut_pocket',None)
params['minimum_designed_load_walls_mm']['rear_speaker_nut_pocket']=1.6
(R/'assembly-parameters.json').write_text(json.dumps(params,ensure_ascii=False,indent=2))

(OUT/'验证说明.md').write_text(f'''# A3 验证记录

- 30/30个STL重新读回：每个为单一连通闭合体、正体积，无边界/非流形边、重复或退化三角面；与清单尺寸一致，毫米单位，Z=0落底。
- 主装配场景30个可打印网格重开闭合。原V1/A1保留，A2作为历史参考不覆盖。
- 完整91×44mm原板与7个原位旋钮/按键对象已恢复；显示面法线为−Y。正面有效区{service['front_sightline_rays']}条抽样视线均未被前盖或遮光井挡住。
- 玻璃前面至前盖最前面名义内凹{service['glass_front_recess_mm']:.2f}mm；旋钮包络最前点至盖内面轴向间隙{service['knob_to_front_plate_inner_face_axial_gap_mm']:.2f}mm。
- 静态检查覆盖{collision['purchased_envelopes_checked']}个外购件、接插件或预留体，{collision['solid_intersection_pairs_checked']}对执行实体交集，未发现超过0.05mm³冲突。包含原位EC11、独立按键、屏幕排针与前盖M3×30螺丝包络。
- 前盖沿−Y、后盖及其附件沿+Y，各抽样16个位置：0、0.25、0.5、1、2、3、5、8、12、16、20、24、30、40、60、100mm，未报告超过0.05mm³的冲突。
- 腿部沿用A2几何；已抽样{motion['sampled_poses']}个逐腿姿态（髋−15/0/+15°，膝−20/0/+20°的非静止组合），未报告零件冲突。不是同时四腿联动验证。
- 爆炸和拆盖展示场景生成前后，主装配打印件的几何与位置指纹一致。

实体交集小于0.05mm³不列作冲突，共面安装接触允许。直视检查不保证大角度可视范围；离散拆盖位置不等于连续扫掠。旋钮总高度仍用V1假设，商品图仅确认轴长标记。以上没有验证真实模块、线束、打印公差、螺纹受力、负载、步态、温升或声学表现。

报告位于reports/：complete-stl-verification.json、complete-reopen.json、assembly-collision-check.json、cover-service-check.json、leg-motion-sample-check.json、complete-preservation.json、presentation-preservation.json、final-artifact-reopen.json。独立交付包内含相同报告。
''')

(OUT/'README.md').write_text('''# Desktop Assistant — 整机结构 A3

**当前模型：DesktopAssistant-整机结构-A3.blend；30个独立STL在stl-complete/中，每件打印1个。**

按旧V1恢复：屏幕保持竖直正对使用者，旋钮和按键留在完整原板上，藏在深可拆前盖内。玻璃名义内凹约20.8mm，拆前盖后操作控件。后盖取消旋钮/按键孔和R07/R08压片，保留充电、总开关、喇叭及功放固定。PCB电气设计保持原状。

当前四个场景：`10_A3_COMPLETE_ASSEMBLY`正确坐标总装、`11_A3_EXPLODED_ASSEMBLY`爆炸关系、`12_A3_PRINT_PARTS_OVERVIEW`打印件总览、`13_A3_FRONT_CAP_REMOVED`拆前盖展示。旧场景继续留在文件内供追溯；编辑和打印请从A3场景及清单开始。

- [设计修正说明](设计修正说明.md)
- [30件零件清单](零件清单.md)
- [装配、拆盖与打印说明](装配与打印说明.md)
- [紧固件核对](紧固件与辅料核对.csv)及[安装明细](紧固件安装明细.csv)
- [检查范围与结果](验证说明.md)
- [参数记录](reports/assembly-parameters.json)

机身含盖约124×116.8×76mm，不含腿、耳朵和外伸总开关/螺丝头。R02加深，R01接管底盘前固定点，R04增加排针末端让位，其余结构沿用A2。前盖用4颗M3×30和0.8mm垫片；拆前盖不用拆底盘或主板。

屏幕及旋钮的实物高度仍需核对：商品图的15mm是轴长，不是原板到旋钮顶端的总高。本套是**实物试装版**，尚未实际切片或完成装配、承载、线束、声学、温升与步态验证。

![正面：屏幕竖直正对使用者](renders/A3-front.png)

![斜视：显示内凹关系](renders/A3-perspective.png)

![前盖取下：完整原板、右侧旋钮及按键](renders/A3-front-open.png)

![后盖](renders/A3-rear.png)

![内部](renders/A3-internal.png)

![爆炸关系](renders/A3-exploded.png)

![30个打印件](renders/A3-parts.png)

完整项目中的scripts/可重建；依赖旧A1/R06输入、原V1及PCB参数，独立ZIP无需运行脚本即可编辑Blender和读取STL。STL不保留材质，前盖黑色内井和薄荷线槽通过打印后上色实现。
''')
print('A3_DOCUMENTATION_DONE',len(manifest),totals)
