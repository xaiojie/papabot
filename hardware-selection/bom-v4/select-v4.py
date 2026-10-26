"""Build the dated V4 sourcing data from the preserved V3 snapshot."""
from pathlib import Path
import copy
import json
import shutil

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
history = HERE / 'history/before-current-pointers'
history.mkdir(parents=True, exist_ok=True)
for name in ['README.md', 'START-HERE.txt', 'design-selection.json',
             'hardware-selection/power-selection-2s.json',
             'hardware-selection/power-selection-2s.md', 'hardware-selection/bom-v3/README.md']:
    target = history / name.replace('/', '__')
    if not target.exists():
        shutil.copy2(ROOT / name, target)

data = copy.deepcopy(json.loads((ROOT / 'hardware-selection/bom-v3/bom-data.json').read_text()))
data['bom'] = [r for r in data['bom'] if r['id'] != 'F05']
by = {r['id']: r for r in data['bom']}
chosen = ['E04', 'P03', 'P04', 'P06', 'W02', 'W03']
for key in chosen:
    by[key].update(selection_status='已定为样机采购型号；未实测',
                   selection_authority='用户授权助手完成本轮选型', selected_for_prototype=True,
                   hardware_tested=False, purchase_confirmed=False,
                   exact_purchase_sku_available=True)

by['E04']['notes'] = 'HANLI/汉丽电子科技，16路PWM/IIC成品板；1块8.90元，页面有货。VCC接3.3V，I²C上拉到3.3V，共地；仅从板上取PWM信号，八舵机正电源由外部配电通路分配，不经过本板V+总线。OE上电默认禁用方案计入F07，按到货板确认焊盘/跳线。快递5元归L01统一预留。'
by['P03'].update(observed_moq=1,
    selection_status='保留1块DFR0753作舵机路；6A目标待实测',
    notes='6–14V输入，5V±1%输出，厂家最大8A；本机5V/6A目标尚未验证。仅采购1块。与好盈UBEC输入并接开关后的2S母线、共地，两路5V输出不并联。低于6V超出输入规格。')
by['P04'].update(model='UBEC 3A (2-6S) / 86010010', original_model='86010010',
    original_brand='HOBBYWING(好盈)', item='逻辑/音频路5V降压模块',
    unit_price_or_allowance_cny=35, price_basis='本轮网页价', channel='淘宝 · 顶峰模型',
    url='https://item.taobao.com/item.htm?id=820639316179', observed_moq=1,
    observed_stock='所选3A(2-6S)有货', price_observation_date='2026-09-08',
    notes='购买颜色分类3A(2-6S)，已点选核价35元（非起价）；快递6元归L01统一预留。厂家编号86010010，输入5.5–26V，5V/3A或6V/3A跳帽切换；必须断电置5V档并空载测压后接ESP32/屏幕/功放，6V档不可用。保留厂家输入输出引线，核对极性后焊接/转接；不通过FIT0030杜邦线承载整条5V/2A逻辑路。纹波<50mVpp仅对应厂家12V输入、2A条件，未在本机2S实测。',
    mechanical_constraints='厂家标称43×17×7mm，11g；留引线、磁环、跳帽和散热空间，安装在绝缘托架，远离I²S麦克风与天线。')
by['P06'].update(item='电池工作负载总开关，SPST保持型', model='S1A', original_model='S1A',
    original_brand='NKK Switches', original_package='插件', lcsc_code='C5366606',
    core_import_eligible=True, unit_price_or_allowance_cny=29.42, price_basis='本轮网页价',
    channel='立创商城', url='https://item.szlcsc.com/6201668.html', observed_moq=1,
    observed_stock='现货16个', price_observation_date='2026-09-08',
    notes='单刀单掷ON-OFF保持型、非发光、焊片。NKK官网规格表列15A(AC/DC)、30VDC；本方案按该较保守直流额定选用，分销商另列20A/DC不用于提高本机额定。电池保护输出P+经保险后分出充电支路，再经本开关供两路降压；P−共地。可直接机械断开工作负载，因此移除原F05控制开关/MOSFET重复预算。关机充电；手动开关不提供自动低压切断。',
    mechanical_constraints='NKK官网面板安装孔Ø12.5mm；后部可拆面板安装并留拨杆操作、焊片绝缘及引线弯曲空间。螺纹有效长度/面板厚度和内腔包络须按图纸/实物再定，不沿用小滑动开关孔。')
by['W02'].update(selection_status='已定小包装信号线：3包共30根',
    notes='FIT0030：20cm母对母，10根/包，买3包共30根。官网允许电流<1000mA；仅信号和小电流支路，不作电池、舵机或逻辑/功放总电源线。线长整理和模块端排针装配在后续线束表落实。')
by['W03'].update(selection_status='已定小包装电源线：1套红黑各1m',
    notes='FIT0585：红1m＋黑1m，18AWG/0.75mm²多股镀锡铜硅胶线；自裁并焊接电池、总开关、降压和配电板短线。含裸线而非预压接整机线束；8舵机各自原装线复用，XT30配对件由电池包定制要求包含，不再单买。线长/压降/成束温升待布局验证，不把网页22A标称视为本机额定。')
by['F06']['notes'] = '满电8.4V也须低于ADC输入范围；电压采样点取总开关后，避免关机反向供电。建议负载下约6.4V停止动作并提示关机，阈值/回差/压降待验证；动作停止不等于切断舵机电源。包内每节保护仍必须具备，本版不提供额外电子自动断电。'

for row in data['dimensions']:
    if row[0] == 'D06':
        row[1] = 'Type-C充电板＋NKK S1A总开关'
        row[2] = 'MK021163名义28×17mm；S1A面板开孔Ø12.5mm'
        row[3] = '充电板厚度/孔位/端口；S1A螺纹长度、开关体和焊片包络、引线弯曲空间'
        row[-1] = '采购款式已定；CAD开孔及内部适配未完成'
    if row[0] == 'D10':
        row[1] = 'HANLI PCA9685 / DFR0954 / DFR0753 / 好盈UBEC 3A'
        row[2] = 'PWM与两路降压已定采购；UBEC标称43×17×7mm、11g'
        row[3] = 'PCA/功放/DFR0753板框孔位和高件；UBEC引线磁环跳帽、散热及接口'
        row[-1] = '商品选型完成不代表CAD及负载验证完成'

data.update(schema_version=4, previous_bom='hardware-selection/bom-v3/README.md',
    workbook='hardware-selection/bom-v4/桌面助手-全量BOM导入V4.xlsx',
    core_import_workbook='hardware-selection/bom-v4/立创BOM导入-全部已知C编号V4.xlsx',
    user_correction='历史更正：已确认的是舵机，不是舵机电源。本轮用户授权完成四类配件选型；舵机路保留1块DFR0753，逻辑路改好盈86010010。',
    export_status='four_requested_categories_selected_for_prototype__other_design_dependencies_remain',
    core_import_limit='10项已知C编号含总开关；其他条件候选和MRO适配限制仍保留，未上传验证。')
data['row_replacements']['F05'] = 'removed__P06_S1A_direct_mechanical_load_switch_no_extra_MOSFET_control'
data['selection_closeout'] = dict(date='2026-09-08',
    requested_categories=['PCA9685成品现货','更便宜的逻辑降压','总开关','小包装线材/线束'],
    status='all_four_selected_for_prototype', row_ids=chosen, remaining_dfr0753_quantity=1,
    logic_saving_vs_second_dfr0753_cny=20, hardware_validation_completed=False,
    assembly_harness_completed=False, online_bom_import_owner='user',
    online_bom_changed=False, order_placed=False)
data['power_topology'] = {
    'positive': 'protected pack P+ -> fuse F01/F02 -> junction; junction -> charger BAT+; junction -> S1A P06 -> DFR0753 P03 and UBEC P04 inputs',
    'negative': 'protected pack P- is common return for charger, regulators, controller and servo signal reference',
    'operation': 'first version power switch OFF while charging; external USB/debug feed disconnected when assessing all-off state',
    'outputs': 'P03 servo 5V and P04 logic 5V never parallel; PCA9685 VCC=3.3V, PWM only; servo distribution external',
    'low_voltage': '6.4V under-load motion-stop starting point requires calibration/hysteresis; user then switches OFF; cell-level BMS required; no separate automatic high-side disconnect in this version'}
data['new_research'] += [
    dict(id='P04', date='2026-09-08', model='86010010', seller='顶峰模型', url=by['P04']['url'],
         selected_variant='3A(2-6S)', price_cny=35, price_scope='已点选具体规格，起价字样消失',
         stock_label='有货', shipping_observed_cny=6,
         official_url='https://www.hobbywing.com/products/ubec-3a-2-6s99',
         manual_url='https://oss.hobbywing.com/pdf/pdfcn/UBEC3A2-6S.pdf',
         official_observed='编号86010010；5.5–26V；5V@3A或6V@3A跳帽切换；43×17×7mm；11g；纹波<50mVpp仅12V输入/2A。',
         lcsc_search='UBEC搜索未找到对应稳压成品，返回无关管盖；不等于全站永远无货。'),
    dict(id='P06', date='2026-09-08', model='S1A', brand='NKK Switches', lcsc_code='C5366606',
         url=by['P06']['url'], price_cny=29.42, moq=1, observed_stock=16,
         official_url='https://www.nkkswitches.eu/products/Toggles/Toggles%20S/S1A/',
         official_observed='SPST、On-Off、15A(AC/DC)、30V DC、non-illuminated、panel hole 12.5Dia、solder lug。',
         rating_note='部分分销商列20A/DC；按官网较低15A/DC记入选型，不混用AC额定。')]
data['documentation'] += [
    dict(name='好盈UBEC 3A厂家规格', url='https://www.hobbywing.com/products/ubec-3a-2-6s99', scope='已阅读规格，5V跳帽档用于逻辑路。'),
    dict(name='好盈UBEC 3A说明书', url='https://oss.hobbywing.com/pdf/pdfcn/UBEC3A2-6S.pdf', scope='官网说明书链接；本轮参数来自官网HTML规格。'),
    dict(name='NKK S1A厂家规格', url='https://www.nkkswitches.eu/products/Toggles/Toggles%20S/S1A/', scope='已阅读规格表，15A AC/DC、30V DC、SPST、Ø12.5面板孔与焊片。')]
data['rejected_candidates'] += [
    dict(model='TDSEMIC-183 / C48953880', url='https://item.szlcsc.com/51278806.html', reason='MP1584模块标题/描述写成升压、1A，与降压芯片性质冲突，不选为逻辑电源。'),
    dict(model='MP1584固定5V通用模块', url='https://item.taobao.com/item.htm?id=725939875506', reason='3元起价非具体5V首档报价；改选有明确厂家输入/输出规格的好盈86010010。'),
    dict(model='KCD1通用12V20A联系SKU', url='https://www.taobao.com/list/item/dEQrS3EwMzl0bk1RWkhicjdZdGFUZz09.htm', reason='可见规格为不要拍/联系客服，不作为可直接采购的已选项；改立创S1A。')]
(HERE / 'bom-data.json').write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')
print('V4 sourcing data created:', len(data['bom']), 'rows')
