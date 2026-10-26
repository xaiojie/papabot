"""Produce a traceable A2 part list, assembly guide and hardware reconciliation."""
import csv, json, hashlib
from pathlib import Path

OUT=Path(__file__).resolve().parents[1]
PROJECT=OUT.parents[1]
R=OUT/'reports'
manifest=json.loads((R/'complete-manifest.json').read_text())
stl=json.loads((R/'complete-stl-verification.json').read_text())
collision=json.loads((R/'assembly-collision-check.json').read_text())
assert len(manifest)==32 and stl['mesh_check_pass']
assert not collision['conflicts_over_0p05_mm3'], 'Finish collision review before documentation release'
for item in stl['items']:
    assert hashlib.sha256((OUT/item['file']).read_bytes()).hexdigest()==item['sha256']

groups=[
 ('屏幕固定框→主壳','M2×6',4,'R04/R01，螺母在主壳内侧槽'),
 ('两块电源架→侧壁','M2×6',8,'R17/R18；螺母从主壳外侧装入，模块边缘避开螺丝头'),
 ('充电托架→后面板','M2×6',2,'R09/R03，螺母在托架内侧槽'),
 ('8个舵机安装耳','M2×8',16,'每个2颗；实物舵机耳片厚度需复核'),
 ('8个原装双臂舵盘→打印连杆','M2×8',16,'每个2颗；不替代舵机中心螺丝'),
 ('独立按键后置压片','M2×8',2,'R08/R03，螺母从后面板外侧装入'),
 ('EC11后置压片','M2×8',2,'R07/R03，螺母从后面板外侧装入'),
 ('小耳朵','M2×8',2,'R12/R13；螺母从耳朵后侧装入'),
 ('可换麦克风架','M2×8',2,'R14/R01；内侧沉孔，螺母从外侧装入，试配后修短外露尖端'),
 ('主控PCB→R06','M2×8',4,'头径≤4.0mm、头高≤2mm；不用大垫片，沿用PCB原Ø3.2孔'),
 ('喇叭后压圈','M2×10',2,'R11/R03，螺母从后面板外侧装入'),
 ('两条充电板压条','M2×10',4,'R10/R09，螺母从托架底部装入'),
 ('屏幕原板→固定框','M3×8',4,'R04，配0.8mm平垫片；螺母从框背面装入'),
 ('前盖、后盖→主壳','M3×10',8,'各4颗；配0.8mm平垫片'),
 ('底盘→前盖/主壳','M3×10',4,'R05；配0.8mm平垫片，前2个螺母在前盖背部'),
 ('主控架→底盘','M3×10',4,'R06；M3螺母从支脚侧面装入，配0.8mm平垫片'),
 ('PCA9685架→底盘','M3×10',4,'R16；M3螺母从支脚侧面装入，配0.8mm平垫片'),
 ('四个髋座→底盘','M3×12',8,'每座2颗；螺母从底盘顶部装入，配0.8mm平垫片'),
]
totals={}
for _,spec,n,_ in groups: totals[spec]=totals.get(spec,0)+n
assert totals=={'M2×6':14,'M2×8':44,'M2×10':6,'M3×8':4,'M3×10':20,'M3×12':8}
with (OUT/'紧固件安装明细.csv').open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.writer(f);w.writerow(['安装位置','螺丝规格','单台数量','装配备注']);w.writerows(groups)
hardware=[
 ('M2×6',14,'100颗已列立创BOM','数量够，长度与实物复核'),
 ('M2×8',44,'V7未明确列此长度','新增，建议备50颗；PCB用4颗必须小头'),
 ('M2×10',6,'V7未明确列此长度','新增，建议备10颗'),
 ('M2螺母',64,'淘宝已选20颗','还差44颗；原20颗装可再备3包，总计80颗'),
 ('M3×8',4,'100颗已列立创BOM','数量够'),
 ('M3×10',20,'V7未明确列此长度','新增，建议备30颗'),
 ('M3×12',8,'V7未明确列此长度','新增，建议备10颗'),
 ('M3螺母',32,'淘宝已选50颗','数量够'),
 ('M3平垫片（Ø6×0.8）',32,'淘宝已选200片','数量够；PCB的M2处不用此垫片'),
 ('原装舵盘与中心螺丝',8,'随8个MG90S附带情况待实物确认','原装花键和中心螺纹，不能用普通M2代替'),
 ('Ø12×2硅胶脚垫',4,'淘宝已选50只','每脚1只'),
 ('10×150mm电池束带',1,'淘宝已选2条','电池实物到货后确认搭接长度'),
 ('1mm EVA薄垫',1,'淘宝已选1卷','按电池、模块、控件边缘裁切；电源模块可叠到约2mm'),
 ('2.5×100mm扎带',20,'淘宝已选100条','建议预留20根，按走线裁定；不勒压电芯'),
]
with (OUT/'紧固件与辅料核对.csv').open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.writer(f);w.writerow(['规格','单台数量或备料数','V7清单记录（非到货）','当前处理']);w.writerows(hardware)

orientation={'Z':'沿现有底面','inverted':'倒置，支脚朝上','front_down':'正面朝下','back_down':'背面朝下','side_down':'侧面朝下'}
rows=[]
for m in sorted(manifest,key=lambda x:(not x['id'].startswith('R'),x['id'])):
    rows.append(f"| {m['id']} | {m['label_zh']} | 1 | {'×'.join(f'{v:.2f}' for v in m['dimensions_mm'])} | {orientation[m['orientation']]} |")
parts_doc='''# A2 整机打印零件清单

当前共 **32 个独立 STL，每个打印 1 件**。FL/FR/RL/RR 分别是左前/右前/左后/右后，以机器人自己的朝向判断。左右及前后孔位不同，请按件号取件。

尺寸来自已导出的 STL，顺序为导出文件的 X×Y×Z（mm），已经按建议打印方向旋转。导入切片器保持 **100% / 毫米**，不要再放大1000倍。STL统一在Z=0落底。

| 件号 | 零件用途 | 每台数量 | STL包络 mm | 导出姿态 |
|---|---|---:|---|---|
'''+ '\n'.join(rows)+'''

R05集成电池托架，R03集成喇叭套筒及功放支撑，L102集成上腿和膝舵机座，L104集成下腿和脚掌。耳朵内片已合并为浅浮雕，后处理上色即可。因此没有另缺一份独立电池盒、功放座、膝座、脚掌或耳朵内片。

电子模块、电池、金属螺丝、原装舵盘和硅胶脚垫在Blender里用于装配参照，不属于打印件。编号不连续是保留历史件号，不能据此判定缺件。

旧 `print-v2` 里的6个结构草稿和6个试配片仅保留历史；`structure-a2/stl` 里的单件R06是支架检查副本。整机统一使用本目录 **stl-complete/** 的32个文件。
'''
(OUT/'零件清单.md').write_text(parts_doc)

table='\n'.join(f'| {spec} | {n} | {old} | {note} |' for spec,n,old,note in hardware)
assembly='''# A2 装配、打印与紧固件说明

这是一套可编辑、可单件切片的整机试装模型。主体/腿/模块固定结构已建出；舵机、屏幕、电池和部分模块尚无同批实物尺寸，首轮用途是试装验证。

## 打印建议

- 主壳、盖板、支架建议PETG；承载腿件不建议用脆性普通展示树脂。PLA可先试孔位，但不能据此认定温升和长期受力合格。
- 初始切片参考：0.4mm喷嘴、0.2mm层高，主壳/盖板4圈壁；腿座、连杆、底盘5～6圈壁，约35%～45%填充。以上是起始建议，未实际切片或试打。
- STL已有建议朝向。R01内侧悬空螺丝座、R06/R16桥架、腿座横梁以及局部压条需要检查支撑；优先可移除的局部支撑，不能让封闭螺母槽被支撑堵死。
- 清理支撑和毛边后先手推试入螺母，再装零件。M2通孔设计Ø2.4，M3多数Ø3.4；槽公差受材料和机器影响。薄壁螺丝座轻拧，不用电动起子强攻。
- R12耳朵整体薄荷色打印，浅浮雕区可涂奶油白；壳体不加字样和Logo。

## 建议装配顺序

1. **先预装螺母。** R06/R16底部M3螺母从支脚侧槽装入；R06上部M2螺母从底侧装入。R01侧壁电源架/麦克风螺母从外侧装入。R03控件和喇叭螺母从外侧装入。孔槽配合松时可少量可移除胶固定螺母外缘，别堵螺纹。
2. **组单腿。** 每条腿由L101、L102、L104组成。先装髋舵机到L101、膝舵机到L102；在断载条件下通电回中，再用原装舵盘和原中心螺丝连接。打印连杆与双臂舵盘各用2颗M2固定。先把一条腿的耳孔、舵盘孔和活动间隙试通，再复制到其余三腿。
3. **组底盘。** 4个L101用8颗M3×12从底面固定到R05，顶部螺母槽先放螺母。电池托架内垫1mm EVA，穿10mm束带；先按目标假体试装，再放已确认尺寸的电池，束带不勒压软包。
4. **组主控与后舱。** 将PCB装到R06的4个绝缘台面上，用小头M2×8（头径≤4mm），不加大垫片；PCB本体的Ø3.2孔和电气文件不变。R06、R16各用4颗M3×10固定到底盘。PCA9685放在R16上用绝缘垫和扎带固定，连接器避开夹持边。
5. **组主壳附件。** 趁前后开口未封，装R12/R13耳朵、R14麦克风托架、R17/R18电源架。模块与架间留约2mm绝缘/缓冲空间并避开螺丝头。麦克风拾音口对准前盖声孔，泡棉只封边，不盖住拾音口。
6. **组前屏。** 保留91×44mm屏幕PCB完整，拆焊后置的EC11和独立按键另接线。屏幕4孔固定到R04，R04再固定到R01，最后装R02。屏幕有效区/排针高度及玻璃约0.8mm内缩均要用实物复核。
7. **组后面板。** 将喇叭、EC11、按键分别用R11/R07/R08压住外壳边缘，不能压振膜或裸焊点；充电板放R09，用R10两条压住已确认无元件的边缘。MAX98357装在R03中央绑带座。S1A用自身安装螺母固定。
8. **布线后合盖。** 保险及XT30线束固定在底盘后部扎带孔附近，舵机线留关节活动余量。模块之间按既有电气方案连线，舵机大电流使用独立配电线。先合主壳/底盘与前盖，再检查后盖线束不夹线，最后锁后盖。脚底贴4只硅胶垫。

USB调试首轮通过打开后盖、松开右侧电源架接入右向的主控USB；此版没有保证任意USB插头能直接穿过封闭壳体。充电使用独立的后面板Type-C口，仍按关机充电方案。

## 紧固件与V7采购清单的差额

原采购表是结构设计前的估数。下表按A2安装点更新，**不代表已经买到，也未修改购物车或下单**。普通M2不替代舵机中心螺丝。螺丝长度按无额外垫厚的模型核算，实装不得顶到电路板或模块；有外露尖端时选短一档或修短。

| 规格 | 单台数量/备料数 | V7已有记录 | A2处理 |
|---|---:|---|---|
'''+table+'''

每个机牙螺丝位置对应1个螺母：M2共64、M3共32。M3共32个位置使用Ø6×0.8mm平垫片。各安装位置的分配见[紧固件安装明细.csv](紧固件安装明细.csv)。

## 实物仍需确认的配合

- MG90S同批外形、耳孔距、轴伸、双臂舵盘厚度和孔距；模型用了可调耳槽及原装舵盘接口，没有打印花键。当前腿结构需要负载、扭矩和步态验证。
- 屏幕开窗和厚度、拆焊后残余高度、插头针序及线束弯曲；完整屏幕板不能裁切。
- 电池75×40×20mm是给商家的目标，并非已收到的成品尺寸；保护板、包膜、出线及≤80g重量仍以最终实物为准。
- DFR0753预留空间、麦克风模块外形身份、PCA9685及功放接插件、充电板元件位置、UBEC线头和磁环需复测。开放架和可换小支架用于后续调整。
- 静态干涉检查和32个腿部抽样姿态不等于连续运动扫掠、线束活动、强度、温升、RF或整机行走试验。
'''
(OUT/'装配与打印说明.md').write_text(assembly)

params={
 'revision':'A2','units':'mm','status':'complete_prototype_geometry__physical_fit_pending',
 'coordinate_system':'X左右；Y前后（前为负）；Z向上',
 'body':{'width':124,'height':76,'centre_z':68,'front_outer_y':-26.2,'rear_shell_y':68,'rear_panel_outer_y':70.6,'depth_with_covers':96.8,'wall_nominal':2.4},
 'floor':{'z_range':[30,34.6],'nominal_thickness':4.6,'base_mount_xy':[[-33,-16],[33,-16],[-50,8],[50,8]]},
 'front_fastener_xz':[[-48,41.7],[48,41.7],[-48,96],[48,96]],
 'display_tab_fastener_xz':[[-43,44],[46,44],[-43,94],[46,94]],
 'display':{'nominal_uncut_pcb_xyz':[91,1.6,44],'nominal_hole_pitch':[84.5,37.5],'glass_recess_target':.8,'measured':False},
 'pcb':{'native_definition':'pcb-design/native-rev-a/carrier-definition.json','world_transform':'X=u-40;Y=v-2;Z=w+66','board_bottom_z':66,'board_top_z':67.6,'physical_mount_hole_diameter':3.2,'mount_holes_uv':[[5,5],[75,5],[75,27],[5,27]],'screws':'4 M2x8, head D<=4mm; PCB unchanged'},
 'controller':{'socket_plastic_height_known':8.5,'male_spacer_nominal':2.5,'pcb_bottom_z':78.6,'pcb_top_z':80.2,'component_reserve_top_z':86.2,'stack_physically_measured':False},
 'battery':{'target_xyz':[75,40,20],'body_bbox':[[-37.5,-6,35.6],[37.5,34,55.6]],'max_mass_target_g':80,'supplier_final_confirmed':False},
 'rear_controls_xz':{'EC11':[28,90],'button':[28,73],'S1A':[19,55],'charger':[-22,55.5],'speaker':[-35,84]},
 'module_bays':{'DFR0753':{'size_xyz':[10,50,30],'centre':[48,30,83],'basis':'reservation only, not a measured product dimension'},'UBEC':{'size_xyz':[7,17,43],'centre':[-49.7,45,77.5],'basis':'vendor nominal body, excludes leads/magnetic ring'},'mic':{'size_xyz':[14,11.2,22],'centre':[-50,-11.1,76.8],'basis':'adjustable provisional bay; exact module identity unresolved'}},
 'fastener_counts':totals,'M2_nuts':64,'M3_nuts':32,
 'minimum_designed_load_walls_mm':{'R06_R16_floor_nut_pocket':1.6,'rear_control_and_speaker_nut_pocket':1.6,'power_mount_nut_pocket':1.4,'mic_nut_pocket':1.0},
 'printable_files':32,'electronic_envelopes_exported':False,'physical_fit_tested':False}
(R/'assembly-parameters.json').write_text(json.dumps(params,ensure_ascii=False,indent=2))

limits='''检查采用模型名义尺寸，尚未实际切片、试装或承载测试。小于0.05mm³的交叠不作为本检查冲突，接触安装面允许共面。抽样姿态逐腿独立检查，没有证明整个连续活动范围、同时四腿联动、线束或地面支撑安全。
'''
motion=json.loads((R/'leg-motion-sample-check.json').read_text())
report=f'''# A2 交付验证

- 32/32个STL重新读回通过：单一连通闭合体、正体积；无边界边、非流形边、重复/退化三角面；尺寸与清单相符，导出单位mm且Z=0落底。
- 主装配场景内32个可打印网格闭合；原V1和A1源文件保留，完整性记录见complete-preservation.json。
- 静态检查覆盖{collision['purchased_envelopes_checked']}个外购件/接插件/引脚预留体；{collision['solid_intersection_pairs_checked']}对执行实体交集，超过0.05mm³的冲突为0。
- 4条腿共32个离散抽样姿态未报告零件碰撞。采样：髋−15/0/+15°、膝−20/0/+20°，每腿8个非静止组合。抽样中的移动件与固定件包围盒已分离，不需进一步实体交集。
- PCB紧固件专项：Ø6mm的M3螺丝头与J9名义排针壳体相交；采用Ø≤4mm的M2螺丝头后，名义最小边缘间隙约0.46mm。PCB没有修改。
- 螺母受力路径已按建模尺寸复核：R06/R16脚底侧装槽留1.6mm下承压壁；后控件/喇叭固定座留1.6mm前承压壁。模型检查不证明打印后的材料强度。

{limits}

证据文件：complete-stl-verification.json、complete-reopen.json、assembly-collision-check.json、leg-motion-sample-check.json、pcb-fastener-head-check.json、complete-preservation.json、presentation-preservation.json。它们位于本目录或交付包的reports/中。
'''
(OUT/'验证说明.md').write_text(report)

readme='''# Desktop Assistant — 整机结构 A2

**当前入口：DesktopAssistant-整机结构-A2.blend。32个独立STL在stl-complete/中，每个打印1件。**

本轮已完成主壳、前后盖、加强底盘、主控/屏幕支架、四条两关节腿、后控件和电源音频固定结构。电子件采用已选型号的资料尺寸或明确标记的预留包络，仍需拿实物试装。

Blender中保留三个当前视图：`10_A2_COMPLETE_ASSEMBLY`整机装配、`11_A2_EXPLODED_ASSEMBLY`爆炸关系、`12_A2_PRINT_PARTS_OVERVIEW`零件总览。旧用户场景也保留；当前打印只取stl-complete/。

- [零件清单](零件清单.md)：全部32件与导出尺寸。
- [装配与打印说明](装配与打印说明.md)：打印建议、装配顺序、采购差额及待测尺寸。
- [紧固件核对CSV](紧固件与辅料核对.csv)与[安装明细CSV](紧固件安装明细.csv)。
- [验证说明](验证说明.md)：网格、静态干涉、腿部抽样的实际检查范围。
- [参数记录](reports/assembly-parameters.json)：尺寸和坐标基准。

机身含前后盖约124×96.8×76mm（不含腿、耳朵、外伸旋钮）。屏幕91×44mm原板保留完整，EC11和独立按键后置；电池仍按75×40×20mm目标。主控PCB按原80×32mm板框和4孔安装，板底Z66。四处PCB固定改用小头M2，底盘固定仍为M3。

新增结构明确了紧固件数量：需核对M2×8、M2×10、M3×10、M3×12和增加的M2螺母；原V7采购表里的数量为设计前估数，未自动变更购物车。

![整机](renders/A2-front.png)

![后部](renders/A2-rear.png)

![内部](renders/A2-internal.png)

![爆炸关系](renders/A2-exploded.png)

![32个打印件](renders/A2-parts.png)

重建脚本位于完整项目的structure-a2/scripts/，依赖原项目中的A1及原生PCB资料。独立交付ZIP不包含重建输入，但无需运行脚本即可编辑Blender和读取STL。几何和拓扑检查已完成；实际切片、实物适配、线束、承载、步态、温升与RF测试尚未完成。
'''
(OUT/'README.md').write_text(readme)
print('DOCUMENTATION_DONE',len(manifest),totals)
