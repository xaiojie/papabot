import json,collections,re
from eda_client import execute,ROOT
out=ROOT/'generated'
r=execute('const f=await eda.sch_ManufactureData.getNetlistFile("Integrated_verified","JLCEDA");return {netlist:await f.text(),drc:await eda.sch_Drc.check(true,true,true),pass:await eda.sch_Drc.check(true,false,false)};','full-native-verification')
(out/'native-netlist.json').write_text(r['netlist']);(out/'native-drc.json').write_text(json.dumps({'result':r['drc'],'pass':r['pass']},indent=2))
act=json.loads(r['netlist']);exp=json.load(open(out/'reviewed-pin-nets.json'));by={v['props']['Designator']:v for v in act['components'].values()};errors=[]
if len(by)!=len(act['components']):errors.append('Duplicate designators')
if set(by)!=set(exp):errors.append({'missing':sorted(set(exp)-set(by)),'extra':sorted(set(by)-set(exp))})
netpins=collections.defaultdict(list);pins=0
for ref,c in by.items():
 if ref not in exp:continue
 expected=exp[ref]['pins'];actual=c['pinInfoMap']
 if set(expected)!=set(actual):errors.append({'ref':ref,'expected_pins':list(expected),'actual_pins':list(actual)})
 for pn,p in actual.items():
  pins+=1
  want=expected.get(pn) or '';got=p['net']
  if got!=want:errors.append({'ref':ref,'pin':pn,'expected':want,'actual':got})
  if got:netpins[got].append(f'{ref}.{pn}')
 if not c['props'].get('Footprint'):errors.append({'ref':ref,'missing_footprint':True})
 if not re.fullmatch(r'C\d+',c['props'].get('Supplier Part','')):errors.append({'ref':ref,'invalid_supplier_part':c['props'].get('Supplier Part')})
# Functional invariants independent of the source layout.
def net(r,p):return by[r]['pinInfoMap'][str(p)]['net']
checks={
 'raw_negative_is_separate':net('JBAT',1)=='VBAT_RAW_N' and net('Q1',1)=='GND' and net('Q2',1)=='VBAT_RAW_N',
 'back_to_back_mos_common_drain':all(net(q,p)=='MOS_MID' for q in ['Q1','Q2'] for p in [5,6,7,8]),
 'mos_gates_not_sources':all(net(q,4)!=net(q,1) for q in ['Q1','Q2']),
 'protection_filters_connected':net('R1',2)==net('U1',5)==net('C1',1)=='PROT_VDD' and net('R2',2)==net('U1',4)==net('C2',1)=='PROT_VC',
 'balance_outputs_drive_gates':net('U2',6)==net('Q3',1)=='BAL1_GATE' and net('U3',6)==net('Q4',1)=='BAL2_GATE',
 'charger_vsys_not_vout':net('U4',19)=='CHG_VSYS' and net('U4',21)=='VBAT_FUSED',
 'charger_pack_minus_protected':net('U4',18)==net('U4',25)=='GND',
 'charger_voltage_and_cells_correct':not net('U4',3) and not net('U4',10),
 'charger_current_programmed':net('U4',11)==net('R8',1)=='CHG_ISET',
 'charge_enable_default_pulldown':net('U4',12)==net('R24',1)=='CHG_EN' and net('R24',2)=='GND',
 'regulator_outputs_separate':net('J_LOG_OUT',1)=='+5V_LOGIC' and net('J_SRV_OUT',1)=='+5V_SERVO',
 'mcu_5v_isolated':net('JP_MCU',1)=='+5V_LOGIC' and net('JP_MCU',2)==net('J1',17)=='MCU_5V',
 'lcd_source_isolated':net('JP_LCD',1)=='+3V3' and net('JP_LCD',2)==net('J3',2)==net('J3',8)=='LCD_3V3',
 'servo_headers_three_pins':all(set(by['SV'+str(i)]['pinInfoMap'])=={'1','2','3'} for i in range(1,9)),
 'servo_oe_pullup_and_clock':net('U7',23)==net('R15',2)=='PCA_OE' and net('R15',1)=='+3V3' and net('U7',25)=='GND'
}
for k,v in checks.items():
 if not v:errors.append({'functional_check_failed':k})
report={'component_count':len(by),'pin_count':pins,'net_count':len(netpins),'nc_pin_count':sum(1 for c in by.values() for p in c['pinInfoMap'].values() if not p['net']),'single_pin_nets':{k:v for k,v in netpins.items() if len(v)<2},'pin_net_errors':errors,'functional_invariants':checks,'drc':r['drc'],'drc_pass':r['pass']}
(out/'verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));print(json.dumps(report,ensure_ascii=False,indent=2))
