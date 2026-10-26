"""Publish battery selection as an overlay on the historic V7 procurement list."""
from pathlib import Path
import json, hashlib

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
REL=str(HERE.relative_to(ROOT))

def load(path):return json.loads((ROOT/path).read_text())
def write(path,data):
    p=ROOT/path;p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
def backup(path):
    source=ROOT/path;target=HERE/'before'/path
    if not target.exists():target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(source.read_bytes())

paths=['design-selection.json','hardware-selection/power-selection-2s.json',
       'design-coordination/interface-proposal.json','README.md',
       'hardware-selection/power-selection-2s.md','pcb-design/native-rev-b/装配与上电核对.md',
       'mechanical-design/structure-a3/README.md']
for p in paths:backup(p)

battery=dict(quantity=1,selection_type='stock_hobby_pack_with_separate_protection',
    model='格氏ACE GS8002S45',supplier='格氏电池全国总代',
    url='https://item.taobao.com/item.htm?id=663039669190&skuId=4779123056788',
    item_id='663039669190',sku_id='4779123056788',sku='T型插头；800mAh-45C-7.4V-2S1P',
    nominal_voltage_v=7.4,full_charge_voltage_v=8.4,configuration='2S1P_standard_4.2V_LiPo',
    capacity_mah=800,nominal_energy_wh=5.92,body_dimensions_seller_mm=[60,32,16],
    body_dimensions_measured_mm=None,weight_seller_g=[55,60],
    weight_source_discrepancy='SKU image:55g ±15g; detail table:60g',
    discharge_c_seller=45,whole_power_path_tested=False,internal_protection_verified=False,
    main_lead_awg=16,main_lead_length_mm=80,balance_lead_awg=22,balance_lead_length_mm=45,
    connector='T plug; use matching machine-side connector; retain live battery plug',
    observed_price_cny=39.6,observed_stock='有货',purchase_confirmed=False)
bms=dict(quantity=1,model='HX-2S-JH20',supplier='深圳市优信电子科技有限公司',
    url='https://item.taobao.com/item.htm?id=574046367042',observed_price_cny=9.02,
    observed_stock='有货',dimensions_seller_mm=[46.7,23,3.15],
    working_current_upper_seller_a=10,instantaneous_current_upper_seller_a=20,
    overcharge_per_cell_v=4.25,overcharge_tolerance_v=.05,
    overdischarge_per_cell_v=2.9,overdischarge_tolerance_v=.05,
    balancing=True,common_charge_discharge_port=True,charger=False,
    internal_resistance_upper_seller_ohm=.3,
    source=REL+'/evidence/YourCee-67325-2S-protection.pdf',
    connections={'B+':'raw pack main positive','B-':'raw pack main negative',
                 'BM/MB':'cell midpoint only','P+':'fuse then charge/load junction',
                 'P-':'all machine and charger returns; never bridge to raw B-'},
    purchase_confirmed=False,thermal_load_tested=False)
selection=dict(date='2026-09-09',status='selected_for_prototype_not_purchased',
    authority='user requested off-the-shelf sourcing and adapting the design',
    battery=battery,protection_module=bms,observed_subtotal_cny=48.62,
    subtotal_excludes=['machine-side T mating pigtail','balance mating pigtail','insulation/fixing materials'],
    mechanical_record='mechanical-design/battery-ace800-a3/README.md',
    pcb_revision='RevB',pcb_copper_change_required=False,
    charging=dict(target_v=8.4,target_cc_a=.4,current_module='TELESKY MK021163',
        current_setting_verified=False,ready_to_connect_to_battery=False,
        action='measure/configure CC/CV before connecting battery; external configurable 2S charger if incompatible'),
    firmware=dict(bringup_changed=False,battery_adc_or_low_voltage_stop_implemented=False,
        future_warning_v=7.2,future_motion_stop_v=7.0,thresholds_validated=False))
write(REL+'/selection.json',selection)

readback=load(REL+'/evidence/eda-schematic-readback.json')['result']
src=readback['source']
checks={name:token in src for name,token in {'lcd_3v3':'LCD_3V3','battery_switched':'VBAT_SW',
    'divider_100k':'100k 1%','divider_33k':'33k 1%','j8':'"value":"J8"',
    'j9':'"value":"J9"'}.items()}
assert all(checks.values()),checks
review=dict(date='2026-09-09',active_document=readback['document'],live_source_checks=checks,
    source_sha256=hashlib.sha256(src.encode()).hexdigest(),pcb_revision='RevB',
    carrier_changes_required=False,live_project_mutated=False,gerber_reexported=False,
    rationale='same 2S maximum 8.4V, same regulated 5V and 3.3V; charging/protection/servo current already offboard',
    full_charge_adc_v=8.4*33/(100+33),pcb_sense_ground='protected P-',
    original_fabrication_checks='pcb-design/native-rev-b/README.md',
    verification_scope='live schematic interface and archived RevB architecture; no new routing or new DRC claim',
    hardware_tested=False)
write(REL+'/electrical-review.json',review)

p=load('hardware-selection/power-selection-2s.json')
p['battery']=battery;p['external_protection']=bms;p['date']=p['updated']='2026-09-09'
p['status']='stock_2s_pack_selected_prototype_load_charge_fit_tests_pending'
p['record']=p['current_sourcing_record']=REL+'/README.md'
p['charger']['conservative_charge_current_target_a']=[.4,.4]
p['charger']['ready_to_connect_to_selected_battery']=False
p['charger']['actual_constant_charge_current_a']=None
p['integration']['power_topology']['positive']='raw T+ -> B+; raw T- -> B-; midpoint -> BM; P+ -> fuse -> junction; junction -> charger BAT+; junction -> S1A -> VBAT_SW -> two regulators and J9.1'
p['integration']['power_topology']['negative']='P- only: charger negative, both regulator returns, machine GND and J9.2; never bypass via B-'
p['integration']['power_topology']['low_voltage']='future calibrated firmware: warn 7.2V, motion stop 7.0V, user switches OFF; not implemented in bringup; 2.9V/cell BMS is backup cutoff'
p['integration']['automatic_low_voltage_load_disconnect_implemented']=False
p['screen_controls']={'status':'user_confirmed_A3','proposal':'retain original EC11/key on stock board inside removable front cap','control_relocation':False}
write('hardware-selection/power-selection-2s.json',p)

d=load('design-selection.json')
d['power_selection'].update(updated='2026-09-09',candidate_architecture='stock ACE800 2S + external HX-2S-JH20 protection/balance; existing dual 5V regulators',
    specific_battery_and_power_skus_selected=True,battery_custom_specification_selected=False,
    battery_supplier_can_make_confirmed=False,battery_custom_message=None,
    record=REL+'/README.md',battery_supplier_confirmation_source='stock SKU observed in live Taobao; no supplier message',
    battery_lead='stock 16AWG 80mm T plug; matching machine-side lead',
    battery_connector='T plug',battery_pack=battery,external_protection=bms)
d['current_bom']=REL+'/README.md';d['current_bom_data']=REL+'/bom-data.json'
d['procurement_workbooks']['battery_overlay']=REL+'/README.md'
d['procurement_workbooks']['taobao_tmall_note']='V7 is historical base; P01 and W08 replaced by battery-stock-2026-09-09; quantities/status not refreshed wholesale'
d['procurement_provisional_status'].update(date='2026-09-09',battery_shop=battery['supplier'],
    battery_supplier_response='现货SKU，助手按用户授权选定',battery_pending=['收货量尺寸','充电电流验证','台面负载与温升验证'],battery_custom_added_to_cart=False)
d['current_mechanical']['battery_addendum']={'revision':'A3-ACE800','record':'mechanical-design/battery-ace800-a3/README.md',
    'blend':'mechanical-design/battery-ace800-a3/DesktopAssistant-A3-ACE800.blend','additional_parts':['R21','R22']}
write('design-selection.json',d)

i=load('design-coordination/interface-proposal.json')
i['battery_envelope']={'target_xyz':[60,32,16],'body_center_xyz':[0,14,43.6],
    'body_bbox':[[-30,-2,35.6],[30,30,51.6]],'basis':'ACE800 seller drawing, not measured',
    'supplier_final_confirmed':False,'stock_sku_selected':True,'placement_frozen':False,
    'source':REL+'/selection.json','adapter':'mechanical-design/battery-ace800-a3/README.md'}
i['protection_module_envelope']={'model':'HX-2S-JH20','body_xyz':[46.7,3.15,23],
    'center_xyz':[0,-10.575,53.7],'orientation':'vertical in front of battery',
    'nominal_clearance_to_screen_pcb_rear_mm':7.25, 'nominal_clearance_to_screen_support_mm':1.65,'physical_fit_tested':False}
write('design-coordination/interface-proposal.json',i)

base=load('hardware-selection/bom-v7/bom-data.json')
base['schema_version']=8;base['date']='2026-09-09'
base['scope']='V7常规物料底表＋现成电池适配覆盖；未重新核对全部购物车或结算价'
base['battery_supplier_provisional']={'status':'stock battery selected not purchased','record':REL+'/selection.json'}
for row in base['bom']:
    if row['id']=='P01':row.update(status='已选现货·未购买',name='格氏ACE800 2S动力电池',spec=battery['sku'],
        installed='1包',purchase='1包',channel=battery['supplier'],url=battery['url'],cost=39.6,
        note='取代定制包；保护均衡外置；标称60×32×16mm，45C未实测')
    elif row['id']=='W08':row.update(status='机器端配套待购',name='T插机器端配对短线',
        spec='匹配电池T插，16/18AWG；保留电池原插头',installed='1条',purchase='1条',channel='现成线束',
        url='',cost=None,note='不再要求随定制附送XT30；按实物接头极性配线')
    elif row['id']=='E01':row.update(status='用户已购买',note='等待实物测量；按RevB仅3.3V供电')
    elif row['id']=='E02':row.update(status='用户已买1个·其余暂缓',purchase='首轮1个（已买）',note='整机规划仍8个，本轮先做单舵机测试')
    elif row['id']=='E03':
        if 'ESP32' in str(row):row['status']='用户已购买'
base['bom'].extend([
    dict(id='P01B',name='2S保护均衡模块',spec='HX-2S-JH20',status='已选现货·未购买',installed='1块',purchase='1块',channel=bms['supplier'],url=bms['url'],cost=9.02,note='板外共口保护均衡，非充电器'),
    dict(id='W08B',name='2S三线平衡头配对线',spec='匹配实物平衡头；BM只用于中点检测',status='待购配套',installed='1条',purchase='1条',channel='现成线束',url='',cost=None,note='两端备用线独立绝缘，主电流走T插')])
base['historical_taobao_cart_items']=base.pop('taobao_cart_items')
base['historical_procurement_totals']=base.pop('procurement_totals')
base['current_battery_known_subtotal_cny']=48.62
base['current_whole_robot_total_cny']=None
base['current_cart_reaudited']=False
base['order_placed']=False
write(REL+'/bom-data.json',base)

# Replace the active battery paragraphs; preserve original source text in before/.
readme=(ROOT/'README.md').read_text()
old=readme.splitlines()[2]
new='采购状态更新（2026-09-09）：电池改为现货格氏ACE800（2S、7.4V、800mAh、45C、T插）＋HX-2S-JH20外置保护均衡板，前两项参考¥48.62，尚未购买。详见[成品电池与设计适配]('+REL+'/README.md)。常规配件以V7为底表，旧电池定制与随包XT30行停用；当前开发先用已购买的屏幕、主控和1个MG90S。'
readme=readme.replace(old,new,1)
readme=readme.replace('## 0. 当前采购交付 V7','## 0. 常规采购底表 V7（电池由2026-09-09现成方案覆盖）')
readme=readme.replace('Type-C数据/充电线取消本次采购；PCB打样、整套3D及试样打印暂缓。电池采用2S1P、7.4V/满8.4V、1000mAh、整包持续≥10A，含逐节保护/均衡、18AWG短引线和XT30配对件。目标75×40×20mm、≤80g，真实尺寸与供货仍需商家确认。[电池定制文字](hardware-selection/bom-v7/03-电池定制-发给商家.txt)由用户自行发送。',
    'Type-C数据/充电线取消本次采购。旧定制电池规格已停用；本轮选现货ACE800＋板外保护均衡，载板保持RevB。[电池适配试装件](mechanical-design/battery-ace800-a3/README.md)新增R21/R22，原A3的30件保持原文件。新的电源接线、价格与尚未完成的实测以[现成方案]('+REL+'/README.md)为准。')
(ROOT/'README.md').write_text(readme)

notices={
 'hardware-selection/power-selection-2s.md':'2026-09-09现行方案：[ACE800成品电池＋外置保护均衡](battery-stock-2026-09-09/README.md)。下文定制1000mAh/XT30及6.4V阈值是历史记录；当前阈值与接线以新方案为准。',
 'pcb-design/native-rev-b/装配与上电核对.md':'2026-09-09电池适配补充：现货ACE800＋HX-2S-JH20外置保护均衡板；RevB铜线/接口继续兼容。整机GND、J9.2和充电负极统一接P−，不接原始B−。见[板外电源接线](../../hardware-selection/battery-stock-2026-09-09/接线与调试.md)。',
 'mechanical-design/structure-a3/README.md':'2026-09-09电池适配补充：新增[ACE800成品电池适配件](../battery-ace800-a3/README.md)，另有Blender副本及R21/R22两件STL。下文30件与75×40×20电池占位为原A3基础版本；新电池场景以适配副本为准。'}
for path,note in notices.items():
    text=(ROOT/path).read_text()
    if note not in text:
        first,rest=text.split('\n',1);(ROOT/path).write_text(first+'\n\n'+note+'\n'+rest)

print('Published selection overlay and backed up current pointers.')
