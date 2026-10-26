"""Build RevB review documents from the verified saved sources (no EDA writes)."""
import csv
import hashlib
import json
import re
import shutil
import zipfile
from datetime import datetime
from pathlib import Path
from verify_exports import parse, PCB, SCH

ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parent.parent


def load(name):
    return json.loads((ROOT/name).read_text())


def write(name, data):
    (ROOT/name).write_text(json.dumps(data, ensure_ascii=False, indent=2)+'\n')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def order(ref):
    m = re.fullmatch(r'([A-Z]+)(\d+)', ref)
    return m[1], int(m[2])


def csv_write(name, columns, rows):
    with (ROOT/name).open('w', encoding='utf-8-sig', newline='') as f:
        w=csv.writer(f); w.writerow(columns); w.writerows(rows)


def main():
    native, gerber, routing, nets = [load(n) for n in (
        'native-archive-check.json','gerber-export-check.json','native-routing-validation.json','netlist-check.json')]
    assert native['passed'] and gerber['passed'] and nets['passed']
    assert routing['geometry_pass'] and routing['all_nets_connected'] and routing['total_nets']==26
    for name in ('native-pcb-drc.json','native-schematic-drc.json'):
        assert load(name)['passed'] and not load(name)['errors']
    assert digest(ROOT/'DesktopAssistant_RevB_PCB_review.epro2')==native['native_archive_sha256']
    assert digest(ROOT/'DesktopAssistant_RevB_Gerber_review.zip')==gerber['sha256']

    geometry = load('pcb-persisted-geometry.json')
    sch = parse((ROOT/'schematic-final.source').read_text())[SCH]
    attrs = {(v['parentId'],v['key']):v['value']for(t,_),v in sch.items()if t=='ATTR'}
    enet = load('DesktopAssistant_Carrier_RevB.enet')
    by_ref = {v['props']['Designator']:v for v in enet['components'].values()}
    pcb_components = {c['component']['designator']:c['component'] for c in geometry['components']}
    old = load('before/carrier-definition.json')
    old_parts = {p['ref']:p for p in old['parts']}
    pinmaps = {ref:{str(k):v['net'] or None for k,v in c['pinInfoMap'].items()} for ref,c in by_ref.items()}
    pinmaps['C2'] = old['pinmaps']['C2']
    parts = []
    for (typ,cid),c in sch.items():
        ref = attrs.get((cid,'Designator'))
        if typ!='COMPONENT' or ref not in pinmaps:
            continue
        p = dict(old_parts.get(ref,{}))
        p.update(ref=ref,device=attrs.get((cid,'Device')),name=attrs.get((cid,'Value')) or attrs[(cid,'Name')],
            x=c['x'],y=-c['y'],rotation=c['rotation'],nets=pinmaps[ref],
            note=attrs.get((cid,'Assembly note'),'') or '',native_primitive_id=cid,
            on_pcb=ref in pcb_components,default_population='DNP' if ref in ('R4','R5','R6','R7') else
            'OPEN' if ref.startswith('JP') else 'OPTIONAL_EXTERNAL_INPUT' if ref=='J10' else 'FIT')
        if ref in pcb_components:
            pc=pcb_components[ref]
            p.update(pcb_primitive_id=pc['primitiveId'],pcb_center_mm=[round(pc['x']*.0254,6),round(pc['y']*.0254,6)],
                pcb_rotation_degrees=pc['rotation'],footprint=pc['footprint']['name'])
        parts.append(p)
    assert len(parts)==25 and sum(p['on_pcb'] for p in parts)==24
    parts.sort(key=lambda p:order(p['ref']))
    supply = dict(net='LCD_3V3',voltage_v=3.3,default_jp3='OPEN',
        mcu_mode='Close JP3 only after MCU 3.3V current/thermal margin is verified; disconnect J10.',
        external_mode='JP3 open; J10.1 regulated 3.3V, J10.2 GND; MCU and LCD powered together.',
        external_regulator_selected=False,maximum_display_current_verified=False,
        regulators_must_not_be_paralleled=True)
    definition=dict(revision='RevB',updated_at=datetime.now().astimezone().isoformat(),parts=parts,pinmaps=pinmaps,
        board=old['board'],display_power=supply,
        source_note='Derived from saved RevB schematic, PCB netlists and archived geometry. x/y are schematic API coordinates (0.01 inch), y is inverted from serialized source; pcb_center_mm is separate. Historical initial-build scripts must not be rerun.',
        stock_controls_retained=True,mechanical_revision='A3',physical_fit_verified=False)
    write('carrier-definition.json',definition)

    notes = {
        'J1':'C429947 / 22850120ANG1SYA01；单排20P、2.54mm、塑高8.5mm；两排间距17.78mm，两排1脚朝天线。',
        'J2':'C429947 / 22850120ANG1SYA01；单排20P、2.54mm、塑高8.5mm；两排间距17.78mm，两排1脚朝天线。',
        'J3':'屏幕VCC和BLK均为LCD_3V3，仅3.3V；8针载板接口拆分接到12针模块，按同名信号逐根接。',
        'J4':'PCA9685逻辑VCC=3.3V，OE高时禁用；舵机电源走板外粗线，V+不经过此口。',
        'J5':'麦克风3.3V；第6脚为接地的LR，选择左声道；按所购模块丝印接线。',
        'J6':'仅音频信号；功放电源由5V逻辑UBEC另分支供给。',
        'J7':'原屏幕板控件保留；A/B/PUSH/K0分别接2/3/5/7脚；1/4/6脚为GND备用。',
        'J8':'只接已调到5V的逻辑UBEC输出；不接电池原电压或舵机功率支路。',
        'J9':'只接总开关后的电池正极作电压采样，不是供电输入。',
        'J10':'可选外部稳压3.3V输入，1脚3.3V、2脚GND；使用时JP3必须断开。采用短软线或实测可容纳的低矮连接器。',
        'JP1':'默认开路；上电检查后用低矮短导线连接逻辑5V与主控5V；USB无自动防倒灌。',
        'JP2':'默认开路；检查后连接开关后电池电压与采样分压入口。',
        'JP3':'默认开路；仅确认主控3.3V电流及温升余量后跨接，且J10不得接外部电源；优先贴板短导线。',
        'R1':'100kΩ/1%/0.25W，电池采样分压上臂。',
        'R2':'33kΩ/1%/0.25W，电池采样分压下臂。',
        'R3':'10kΩ OE上拉；若PCA模块自带OE下拉，核对并去掉该下拉后再测试上电禁用。',
        'C1':'100nF，电池ADC滤波。',
        'C2':'板外470µF/16V，放UBEC/功放电源支路；注意极性并绝缘固定，不占PCB位置。',
        'C3':'100nF，主控3.3V旁路。',
        'C4':'100nF，逻辑5V旁路。',
        'C5':'新增100nF/50V/P5.08屏幕旁路电容；外部稳压器仍须配齐其规定的输入/输出电容。',
    }
    for ref in ('R4','R5','R6','R7'):
        notes[ref]='DNP，默认不焊；原屏幕板已有10kΩ上拉到LCD_3V3。保留可选焊位，不能未经评估连接两个稳压输出。'
    pin_refs={p['primitiveId']:(c['component']['designator'],str(p['padNumber']))for c in geometry['components']for p in c['pads']}
    pin_rows=[]
    for p in geometry['allPads']:
        if not p['metallization']:continue
        ref,pin=pin_refs[p['primitiveId']]
        pin_rows.append([ref,pin,p['net'] or 'NC',round(p['x']*.0254,6),round(p['y']*.0254,6),notes[ref]])
    pin_rows.sort(key=lambda r:(order(r[0]),int(r[1])))
    assert len(pin_rows)==104
    csv_write('载板接口与引脚.csv',['PCB位号','针号','信号网络','焊盘X_mm','焊盘Y_mm','说明'],pin_rows)
    bom=[]
    for p in parts:
        ref=p['ref']; optional=ref in ('R4','R5','R6','R7','JP1','JP2','JP3','J10')
        state='不焊/DNP' if ref.startswith('R') and optional else '保持断开' if ref.startswith('JP') else '预留输入' if ref=='J10' else '安装'
        bom.append([ref,p['name'],1,0 if optional else 1,state,'PCB' if p['on_pcb'] else '板外UBEC/功放分支',p.get('footprint','不占PCB位置'),notes[ref]])
    csv_write('载板装配清单.csv',['位号','名称或规格','设计数量','初装数量','默认状态','安装位置','封装模板','备注'],bom)

    screen=[
        [1,'GND','J3.1','GND','共地'],[2,'VCC','J3.2','LCD_3V3','仅3.3V'],
        [3,'SCL','J3.3','GPIO12','SPI时钟'],[4,'SDA','J3.4','GPIO11','SPI MOSI，不是I2C数据'],
        [5,'RES','J3.5','GPIO21','复位'],[6,'DC','J3.6','GPIO14','数据/命令'],
        [7,'CS','J3.7','GPIO13','片选'],[8,'BLK','J3.8','LCD_3V3','3.3V固定高电平，全亮，无软件调光'],
        [9,'A','J7.2','GPIO7','旋钮A相'],[10,'B','J7.3','GPIO2','旋钮B相'],
        [11,'PUSH','J7.5','GPIO38','旋钮按压，按下为低'],[12,'K0 / KEY0','J7.7','GPIO40','独立按键，按下为低']]
    csv_write('屏幕12针接线表.csv',['模块针号','模块丝印','载板针脚','电源或MCU引脚','说明'],screen)
    write('screen-interface.json',dict(module='TOUGLESY ST7789 2.4-inch TFT + EC11, stock 91x44mm PCB',
        supply=supply,pins=[dict(zip(['module_pin','module_signal','carrier_pin','mcu_or_power','note'],r))for r in screen],
        unused_j7_ground_pins=['J7.1','J7.4','J7.6'],board_orientation_must_be_confirmed_on_hardware=True))
    table='| 模块针号 | 模块丝印 | 载板针脚 | MCU或供电 | 说明 |\n|---|---|---|---|---|\n'+'\n'.join('| '+' | '.join(map(str,r))+' |'for r in screen)
    (ROOT/'装配与上电核对.md').write_text('''# RevB 载板装配与上电核对

2026-09-09。屏幕的 VCC 和 BLK 已改接独立 LCD_3V3 网络。**JP1、JP2、JP3 初装均保持断开，R4–R7 默认不焊。** 本板没有新增板载稳压芯片，J10 是外部稳压 3.3V 的接入口。

这块板只连接主控及模块的逻辑信号和电源。8 个舵机及功放功率支路仍走板外配线。本说明对应 RevB，旧 RevA 的屏幕 5V 接法已停用。

## 屏幕12针接线

旋钮与独立按键保留在完整原板上，藏在可拆前盖内。屏幕竖直朝前。先按模块丝印确认插接方向，再逐根接线；本载板的 J3+J7 拆分接口不能直接套用一根同序12针排线。

'''+table+'''

J7.1/.4/.6 都是 GND 备用位，不接到模块的其他信号。模块的 GND 经 J3.1 与主控、稳压器共地。引脚说明中 B 相文字重复写成 A，按 B 标签及整板电路识别。模块自身已有四路10kΩ上拉，R4–R7 保留焊位但初装数量为0；原生库/BOM中的“加入BOM”不表示这些可选电阻需要焊接，装配以本版CSV的“初装数量/默认状态”为准。

## 屏幕3.3V的两种供电方式

| 方式 | JP3状态 | J10 | 条件 |
|---|---|---|---|
| 初始检查 | 断开 | 不接电源 | 屏幕无供电属于预期，先核对极性与短路 |
| 共用主控3.3V | 检查通过后跨接 | 不接外部电源 | 确认屏幕全亮最大电流，以及主控、麦克风、PCA等总负载的余量与温升 |
| 外部稳压3.3V | 保持断开 | 1脚3.3V，2脚GND | 外部稳压器先空载/带载确认输出和能力，MCU与LCD协调上电/掉电 |

**J10只能接稳压后的3.3V，不能接5V或电池。外接3.3V时禁止短接JP3，不能把两个稳压输出并在一起。** JP3本身是普通导线连接位，不提供限流或防倒灌。

屏幕全亮最大电流尚未取得；主控ME6217标称800mA是稳压器能力参数，并非800mA都留给外设。没有据此直接接通JP3。若采用独立稳压支路，还需确定实物模块、额定负载、输入/输出电容与安装位置；C5=100nF仅作旁路，不能替代稳压器要求的电容。

两种模式都要避免一侧未供电时经SPI或控件线给另一侧反向供电。初测可先用GPIO高阻、共同供电时序验证；如果实际上下电无法满足要求，需要带掉电保护的隔离/电平缓冲方案，不能只靠软件启动后的状态。先断电再插拔线束。

## 其余接口

元件面观察，连接器方形焊盘为1脚；详细坐标见[载板接口与引脚.csv](载板接口与引脚.csv)。

| 接口 | 从1脚起的针序或用途 |
|---|---|
| J1/J2 | 主控左/右排各20P；两排1脚均朝天线，2.54mm针距、17.78mm排距 |
| J4 | GND、3.3V、PCA_SDA、PCA_SCL、PCA_OE_N；只接PCA9685逻辑 |
| J5 | GND、3.3V、MIC_BCLK、MIC_WS、MIC_SD、GND；末脚接麦克风LR选左声道 |
| J6 | GND、AMP_BCLK、AMP_WS、AMP_DIN；MAX98357功率另接5V支路 |
| J8 | +5V_LOGIC、GND；只接已设为5V的逻辑UBEC |
| J9 | VBAT_SW、GND；只采样总开关后的电池电压 |
| JP1 | +5V_LOGIC、+5V_MCU；主控供电跨线，初始断开 |
| JP2 | VBAT_SW、VBAT_SENSE；采样跨线，初始断开 |
| JP3 | +3V3、LCD_3V3；屏幕电源选择跨线，初始断开 |
| J10 | LCD_3V3、GND；可选外部3.3V输入 |

J1/J2的左右按厂家主控元件面、天线在上的方向定义；本载板将主控横放，天线朝板左侧。不要把厂家原理图的连接器编号套成本载板编号。

## 元件与空间

- 板上24个设计焊位；初装R4–R7不焊，JP1–JP3不跨接，J10可预留。原理图另有板外C2，共25个实体元件。
- R1=100kΩ、R2=33kΩ、R3=10kΩ；C1/C3/C4/C5=100nF。C2=470µF/16V放在板外UBEC/功放支路，注意极性并绝缘固定。
- J10、JP3、C5中心分别为PCB坐标(74,11)、(74,16)、(74,21)mm。JP3优先贴板短导线，J10用短软线或实测可容纳的低矮连接器。库中的通用高排针模型不是已验证的装配选型。
- 主控插座J1/J2为C429947 / 22850120ANG1SYA01，塑高8.5mm。A3尚未实物试装，需核对插座、主控板底、线束、壳体与新增连接位的空间。
- 采购差额：100nF电容比RevA多1只，可先核现有电容包数量；JP3可用已有短导线。J10/外部3.3V稳压器是预留方案，尚未选购。没有改变购物车。

## 电源与首次上电

受保护2S电池经既定保险丝和总开关后分成两路5V稳压：DFR0753供舵机，好盈3A UBEC设5V后分别供J8与功放。两路共地，5V正极不能相并。8路舵机总电流走外部粗线，不经过载板或PCA模块的细铜箔。充电接总开关前的受保护分支，首版关机充电。

1. 不插主控和任何模块，JP1/JP2/JP3断开、R4–R7不焊。断电检查J8、J10极性，各电源与GND无短路，并确认LCD_3V3与5V网络、主控3.3V网络隔离。
2. 单独检查稳压器输出。逻辑UBEC为5V，外部屏幕支路如使用则为3.3V。未确认电流规格时使用可调限流电源逐步测试并记录，不能将空载电压正常当成满载通过。
3. 首次烧录先从插座拔出主控，单独接电脑USB。USB VBUS与主控5V排针直连，本载板没有自动电源切换。电池工作时不接电脑USB。
4. 拔掉USB、断电后插回主控，确认接法后接通JP1。先检查主控3.3V，再断电接通JP2并核对ADC_BAT；满电8.4V经100kΩ/33kΩ分压约2.084V，固件需设ADC量程并校准。
5. 按上面的供电模式准备屏幕，断电完成全部12针接线。上电后先测VCC/BLK为3.3V，检查控件高电平与主控3.3V兼容，再测试全亮、刷新、旋钮及按键。测量压降、电流和温升，含Wi-Fi、音频并发负载。
6. 再依次接麦克风、功放、PCA9685。PCA的OE高时禁用，若模块带OE下拉须核对并去除冲突。先单舵机小角度测试，再逐步增加数量和负载。

PCB文件复核已通过；实物针序、旋钮帽总高度、打印配合、天线/温升、供电时序与整机负载仍需样机验证。15mm是EC11柄长，不是PCB到旋钮帽顶端的总高。本轮未修改Blender或STL。
''')

    (ROOT/'README.md').write_text('''# DesktopAssistant RevB — 屏幕3.3V供电修订复核包

2026-09-09：已在用户现有嘉立创EDA专业版工程中完成原理图及PCB修改，并保存、重开、运行严格DRC及导出复核。当前有效PCB版本为**RevB**，旧RevA的屏幕5V文件已停用。

在线项目仍叫 `DesktopAssistant_RevA`（保留用户工程名称），其中 **Board1 / Schematic1 / P1** 和 **Board1 / PCB1** 已是RevB。板上丝印、图面标题和本目录文件名标识RevB。`Schematic1_1`是保留的历史副本，不是当前设计入口。

[打开在线工程](https://pro.lceda.cn/editor?cll=warn#id=e5e438419c1c4681946d5009bb8d6daf)

## 修改结果

| 部位 | RevB接法 |
|---|---|
| J3.2 屏幕VCC | 从5V移至独立LCD_3V3网络 |
| J3.8 BLK | 从空脚改为LCD_3V3，固定全亮 |
| JP3 新增 | 主控3.3V到LCD_3V3的可选短导线连接；默认断开 |
| J10 新增 | 外部稳压3.3V输入，1脚正、2脚地；使用时JP3断开 |
| C5 新增 | 100nF屏幕供电旁路电容 |
| J7 / R4–R7 | 改为原屏幕板控件接口说明；原板已有上拉，R4–R7默认不焊 |

板框仍为80×32mm、双层、目标1.6mm/1oz；保留天线U形开口和4个Ø3.2mm安装孔。21个原有元件的PCB位置不变，新增3个元件位。A3前盖方案保持：完整屏幕板、原位旋钮/按键、内凹屏幕；本轮没有修改Blender/STL。

**这版没有新增板载稳压器。** 屏幕最大电流尚未确认，所以JP3默认断开；确认主控稳压余量后可以共用其3.3V，否则经J10接独立稳压3.3V。两个稳压输出不能并联。完整接线、初装数量和上电步骤见[装配与上电核对](装配与上电核对.md)。

## 复核结果

- 原理图及PCB原生严格DRC均通过，错误列表为空；保存、关闭、重开后已复核。
- 104个元件焊盘的原理图、PCB网表和归档网络逐一一致；26/26条网络连通，11个NC按设计隔离，无孤立铜。
- 用原生归档封装精确尺寸检查：最小异网铜间距8.0001mil，铜到板/槽边最小13.0157mil；未放宽8mil间距及12mil板边规则。尺寸结果不包含制造公差。
- Gerber内752条铜线、104个元件孔、25个过孔、4个NPTH安装孔与工程逐一匹配；GKO为闭合80×32mm带U形开口的板框。
- 原生工程与Gerber的ZIP校验通过。独立过孔钻孔文件是129个PTH孔文件中的25孔子集，勿重复加工。
- 导出省略两个无自定义值的默认网络规则记录；原理图属性的绘制顺序和默认删除线字段也有序列化差异。已记录并核对，所有规则数值、引脚、元件、文字值、坐标和导线一致。

这些结果确认设计文件及本次电气修订通过检查。实物插座/线束/壳体配合、全亮屏幕电流、稳压温升、实际上下电时序及整机负载仍未完成；尚未代下单，也未确认首次硬件必然成功。

## 文件入口

- [原生工程 .epro2](DesktopAssistant_RevB_PCB_review.epro2)：用于嘉立创EDA专业版打开/导入。
- [Gerber及钻孔 .zip](DesktopAssistant_RevB_Gerber_review.zip)：本次复核后的制造输出；下单选择双层、1.6mm、1oz，并检查预览尺寸和孔槽加工。
- [装配与上电核对](装配与上电核对.md)：供电模式、接口与初装顺序。
- [屏幕12针接线表](屏幕12针接线表.csv)、[全部104针及坐标](载板接口与引脚.csv)、[载板装配清单](载板装配清单.csv)。
- [修改与复核报告](修改与复核报告.md)：检查范围和未完成事项。
- `carrier-definition.json`、`screen-interface.json`：可供后续设计/固件使用的本版定义。
- `native-pcb-drc.json`、`native-schematic-drc.json`、`native-routing-validation.json`、`netlist-check.json`、`native-archive-check.json`、`gerber-export-check.json`：原始检查结果。
- `delivery-manifest.json`：本次交付状态与文件校验值。

![RevB PCB原生预览](pcb-native.png)

![RevB原理图原生预览](schematic-native.png)

工作目录的 `before/` 保存修改前备份；`audit/` 记录本次API操作。`revise_schematic.py` / `apply_local_routing.py` 是仅适用于修改前状态的一次性脚本，不能在当前工程上重跑。交付ZIP不含历史工程或执行审计大文件。
''')
    (ROOT/'修改与复核报告.md').write_text(f'''# RevB 修改与复核报告

日期：2026-09-09。状态：本次屏幕供电修订和设计文件复核完成；实物试装及上电验证待完成。未下单。

## 修改依据与边界

用户提供的整板原理图显示，VCC直接供液晶并连接A/B/PUSH/K0上拉，没有画出5V稳压/电平转换；引脚说明指定3.3V。采用3.3V供电同时匹配屏幕逻辑及ESP32-S3 GPIO。BLK按说明固定接3.3V。市场图/部分示例注释的5V说法未用作本版接线依据。

原生载板新增独立LCD_3V3网络、JP3选择连接位、J10外部3.3V输入和C5旁路。屏幕5V供电铜线已移除，J3.2与J3.8均在LCD_3V3。J7沿用原脚位，说明修订为保留原板控件；R4–R7默认不焊。没有改动主控GPIO分配或机械几何。

保留21个原有PCB元件位置、原板框及安装孔。移除49段旧5V铜线，保留689段原有铜线，新增63段及1个过孔；最终752段、25个过孔、24个板上元件、104个元件焊盘。原理图另含板外C2。

## 检查证据

| 检查 | 结果 | 证据文件 |
|---|---|---|
| 原生PCB严格DRC | 通过；空错误列表 | native-pcb-drc.json |
| 原生原理图严格DRC | 通过；空错误列表 | native-schematic-drc.json |
| 原理图/PCB/归档网表 | 104/104引脚匹配；5V与LCD隔离 | netlist-check.json |
| 独立连续几何 | 26/26网络连通，无孤立铜，无间距/板边/螺钉头避让违规 | native-routing-validation.json |
| 保存工程对照 | 21个原元件位置、板框与孔不变；规则实际数值不变 | native-archive-check.json |
| Gerber输出 | 752铜线、129PTH、4NPTH逐一匹配；闭合板框 | gerber-export-check.json |

精确归档焊盘尺寸下，最小异网间距为{routing['minimum_different_net_clearance_mil']:.4f}mil（约{routing['minimum_different_net_clearance_mil']*.0254:.6f}mm），最小铜到板/槽边为{routing['minimum_copper_board_edge_mil']:.4f}mil；相对半径2.5mm螺钉头避让圆的最小额外余量为{routing['minimum_screw_head_clearance_mil']:.4f}mil。8mil间距接近规则下限，工艺选用1oz并由板厂按该能力处理，不能直接换成未经复核的厚铜工艺。

原生封装电阻孔带±0.011mil小偏移，验证分别处理焊盘中心与钻孔中心；API的孔径/尺寸取整不用于最终孔径判断。Gerber与归档最大钻孔、线段差均不超过1µm。129个PTH包含104元件孔及25过孔；via-only钻孔文件不可再次叠加加工。

归档省略LCD_3V3空规则选择器及空网络的默认等长选择器，所有实际规则与模板/层叠仍逐项比较。196项原理图属性仅在绘制顺序和默认删除线字段上不同；内容、位置、可见性、元件及连接均一致。飞针文件为11个NC脚各生成唯一NET_n名称，已确认互相独立、未与26条有效网络混同。详情见source-archive-normalization.json及gerber-export-check.json。

## 交付后仍需的实物验证

1. 屏幕3.3V/背光全亮最大电流未给出；共用主控电源的电流/温升余量尚未确认。JP3保持断开；可经J10采用独立合格3.3V支路。外部稳压器还未定型、采购或做安装验证。
2. 实物主控针序、插座高度、板底元件、J10/JP3连接方式、线束弯曲和A3壳体配合尚未验收。PCB外形不变不代表新增插头高度自动合适。
3. 上下电时序、信号倒灌、显示/语音/Wi-Fi并发、舵机负载、温升/RF和步态需要样机测试。供电检查与低速SPI调试完成后再提高刷新率。
4. U形槽内角按板厂铣刀处理，孔槽尺寸和双层1.6mm/1oz选项须在下单预览核对。用户自行决定打样，本次未执行下单。

旧RevA保留为历史备份，不能混用其5V屏幕接线或Gerber。在线项目保留旧名称DesktopAssistant_RevA，实际Board1/P1/PCB1已为RevB。
''')

    supplied=ROOT/'supplier-evidence';supplied.mkdir(exist_ok=True)
    supplier=ROOT.parent/'native-rev-a/supplier-review-2026-09-09'
    for src,dst in [('sources/原理图/原理图.png','屏幕整板原理图.png'),('sources/引脚说明.docx','引脚说明.docx'),('pin-description-extracted.json','pin-description-extracted.json')]:
        shutil.copy2(supplier/src,supplied/dst)
    write('supplier-evidence/source-manifest.json',dict(source_directory='/Users/jay/Downloads/2.4寸TFT彩屏+EC11旋转编码器模块',
        files=[dict(file=p.name,sha256=digest(p))for p in sorted(supplied.iterdir())if p.name!='source-manifest.json']))

    filenames=['README.md','修改与复核报告.md','装配与上电核对.md','载板接口与引脚.csv','载板装配清单.csv','屏幕12针接线表.csv',
        'carrier-definition.json','screen-interface.json','DesktopAssistant_RevB_PCB_review.epro2','DesktopAssistant_RevB_Gerber_review.zip',
        'DesktopAssistant_Carrier_RevB.enet','DesktopAssistant_PCB_RevB.enet','pcb-native.png','schematic-native.png',
        'pcb-final.source','schematic-final.source','pcb-persisted-geometry.json',
        'native-pcb-drc.json','native-schematic-drc.json','native-routing-validation.json','netlist-check.json',
        'native-archive-check.json','gerber-export-check.json','source-archive-normalization.json']
    filenames += [str(p.relative_to(ROOT))for p in sorted(supplied.iterdir())if p.is_file()]
    manifest=dict(revision='RevB',project_name='DesktopAssistant_RevA',project_id='e5e438419c1c4681946d5009bb8d6daf',
        pcb_uuid=PCB,schematic_page_uuid=SCH,updated_at=datetime.now().astimezone().isoformat(),
        status='SCREEN_SUPPLY_REVISION_AND_DESIGN_FILE_REVIEW_COMPLETE__PHYSICAL_AND_POWER_VALIDATION_PENDING',
        native_pcb_drc_pass=True,native_schematic_drc_pass=True,geometry_pass=True,gerber_geometry_matches=True,
        connected_nets=26,component_pads=104,orphan_copper_count=0,screen_supply_v=3.3,default_jp3='OPEN',
        default_dnp=['R4','R5','R6','R7'],external_regulator_selected=False,
        fabrication_order_placed=False,physical_fit_verified=False,full_brightness_current_verified=False,
        mechanical_files_modified=False,mechanical_revision='A3',
        before_native_archive_sha256=digest(ROOT/'before/DesktopAssistant_before_RevB.epro2'),
        current_native_archive='DesktopAssistant_RevB_PCB_review.epro2',current_gerber_archive='DesktopAssistant_RevB_Gerber_review.zip',
        files=[dict(path=n,bytes=(ROOT/n).stat().st_size,sha256=digest(ROOT/n))for n in filenames])
    write('delivery-manifest.json',manifest)
    with zipfile.ZipFile(ROOT/'DesktopAssistant-RevB-PCB复核包.zip','w',compression=zipfile.ZIP_DEFLATED,compresslevel=9)as z:
        for n in filenames+['delivery-manifest.json']:
            z.write(ROOT/n,'DesktopAssistant-RevB/'+n)
    verify_delivery()


def verify_delivery():
    manifest=load('delivery-manifest.json')
    assert len(list(csv.DictReader((ROOT/'载板接口与引脚.csv').open(encoding='utf-8-sig'))))==104
    assert len(list(csv.DictReader((ROOT/'屏幕12针接线表.csv').open(encoding='utf-8-sig'))))==12
    assert len(list(csv.DictReader((ROOT/'载板装配清单.csv').open(encoding='utf-8-sig'))))==25
    package=ROOT/'DesktopAssistant-RevB-PCB复核包.zip'
    with zipfile.ZipFile(package)as z:
        assert z.testzip() is None
        assert len(z.namelist())==len(manifest['files'])+1
        for entry in manifest['files']:
            assert digest(ROOT/entry['path'])==entry['sha256']
            assert hashlib.sha256(z.read('DesktopAssistant-RevB/'+entry['path'])).hexdigest()==entry['sha256']
    report=dict(passed=True,package=package.name,bytes=package.stat().st_size,sha256=digest(package),zip_crc_pass=True,
        manifest_files_checked=len(manifest['files']),pin_csv_rows=104,bom_csv_rows=25,screen_csv_rows=12)
    write('delivery-check.json',report)
    print(json.dumps(report,ensure_ascii=False,indent=2))


if __name__=='__main__':
    main()
