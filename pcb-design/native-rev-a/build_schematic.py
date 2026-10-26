"""Historical initial schematic builder; NOT the current design source.

The live schematic was subsequently refined and C2 moved off-board.
Do not rerun this file on the current project: use the native epro2 snapshot
and the audit records for the final state.
"""
import csv
import json
import sys
from eda_client import execute, ROOT

LIB = '0819f05c4eef4c71ace90d822a990e87'
PAGE = '834bc1f5a1044766'
DEV = {
    2: 'eab4a8150b6d4918927e38d645cd50f2',
    4: 'd5e86a4f70d24c6c950b9ff10d30894b',
    5: 'e999019a30fc45b6addfb63daf8ef2f8',
    6: '8713123b624d4455bcbe38688209bdf0',
    7: '46da13cb38f04076aa100edb7adcd933',
    8: 'fd554b15b6eb4d6f90f5fd338a8ff700',
    '100k': 'e3837981a48340158888ed736539403b',
    '33k': 'b5820c5bc6c347098811112c5fd72b49',
    '10k': 'aa2dc670869d4717b8e9c7ad13737883',
    '100n': '477a96a6592848738afbd710f8b39fc8',
    '470u': 'a84729d2d31842da95d4ba6480505198',
}
parts = []
def part(ref, kind, name, x, y, nets, rot=0, note='', actual=False):
    parts.append(dict(ref=ref, device=DEV[kind], name=name,x=x,y=y,rotation=rot,
                      nets={str(i+1):n for i,n in enumerate(nets)},note=note,actual=actual))

part('J3',8,'LCD_5V_SPI',800,700,['GND','+5V_LOGIC','LCD_SCLK','LCD_MOSI','LCD_RST_N','LCD_DC','LCD_CS_N',None],note='TOUGLESY 2.4 TFT: match signal names at module. BLK left open, default full brightness.')
part('J4',5,'PCA9685_LOGIC_ONLY',800,530,['GND','+3V3','PCA_SDA','PCA_SCL','PCA_OE_N'],note='VCC 3.3V. OE high=disabled. Module V+ and servo red wires use external power distribution.')
part('J5',6,'MIC_3V3_I2S',1060,700,['GND','+3V3','MIC_BCLK','MIC_WS','MIC_SD','GND'],note='Pin 6 is microphone LR, grounded for left channel. Match module silk, not cable position.')
part('J6',4,'AMP_I2S_SIGNALS',1060,530,['GND','AMP_BCLK','AMP_WS','AMP_DIN'],note='MAX98357 power uses short external UBEC branch. SD_MODE keeps module default.')
part('J7',7,'REAR_DRY_CONTACTS',1060,320,['GND','ENC_A','ENC_B','GND','ENC_SW_N','GND','KEY_N'],note='Desolder original EC11 and key. Verify dry contacts with continuity meter before connecting.')
part('J8',2,'LOGIC_5V_IN',200,420,['+5V_LOGIC','GND'],note='UBEC 3A set to 5V. Carrier input excludes amplifier branch and all servo currents.')
part('J9',2,'SWITCHED_BAT_SENSE',200,260,['VBAT_SW','GND'],note='Sense only: connect after main switch. Never connect to unswitched battery.')
part('JP1',2,'MCU_POWER_LINK',460,420,['+5V_LOGIC','+5V_MCU'],note='Solder wire link for standalone battery operation. USB VBUS is NOT isolated. Remove MCU to USB program.')
part('JP2',2,'BAT_SENSE_LINK',420,260,['VBAT_SW','VBAT_SENSE'],note='Solder link only after battery/MCU power-up verification. Open for standalone USB operation.')
part('R1','100k','100k 1% 0.25W',600,260,['VBAT_SENSE','ADC_BAT'])
part('R2','33k','33k 1% 0.25W',700,180,['ADC_BAT','GND'],90)
part('R3','10k','10k 1% OE pull-up',620,520,['+3V3','PCA_OE_N'],90,note='Check/remove module OE pull-down if fitted; verify OE remains high at boot.')
for ref,x,net in [('R4',600,'ENC_A'),('R5',710,'ENC_B'),('R6',820,'ENC_SW_N'),('R7',930,'KEY_N')]:
    part(ref,'10k','10k 1% 0.25W',x,370,['+3V3',net],90)
part('C1','100n','100nF 50V P5.08',800,180,['ADC_BAT','GND'],90)
part('C2','470u','470uF 16V',300,350,['+5V_LOGIC','GND'],0,actual=True)
part('C3','100n','100nF 50V P5.08',460,160,['+3V3','GND'],90)
part('C4','100n','100nF 50V P5.08',1060,180,['+5V_LOGIC','GND'],90)

rows=list(csv.DictReader(open(ROOT.parent/'rev-a/01-controller-pinout.csv',encoding='utf-8-sig')))
pinmaps={ref:{r['本项目位置'][1:]:r['本轮网络'] or None for r in rows if r['本项目位置'].startswith(side)} for ref,side in [('J1','L'),('J2','R')]}
pinmaps.update({p['ref']:p['nets'] for p in parts})
(ROOT/'carrier-definition.json').write_text(json.dumps({'parts':parts,'pinmaps':pinmaps},ensure_ascii=False,indent=2))
guard=f'const doc=await eda.dmt_SelectControl.getCurrentDocumentInfo();if(doc?.uuid!=="{PAGE}")throw new Error("Wrong schematic page");'

stage=sys.argv[1]
if stage=='place':
    start=int(sys.argv[2]);end=int(sys.argv[3])
    code=guard+'const parts='+json.dumps(parts[start:end])+';const out=[];const existing=await eda.sch_PrimitiveComponent.getAll();for(const p of parts){let c=existing.find(c=>c.getState_Designator()===p.ref);if(c){out.push({ref:p.ref,skipped:true,id:c.getState_PrimitiveId()});continue;}c=await eda.sch_PrimitiveComponent.create({libraryUuid:'+json.dumps(LIB)+',uuid:p.device},p.x,p.y,undefined,p.rotation,false,true,true);if(!c)throw new Error("create "+p.ref);const props={designator:p.ref,name:p.name,otherProperty:{"Assembly note":p.note,"Procurement":"Use previously selected BOM item; library geometry is a template."}};if(!p.actual)Object.assign(props,{supplier:null,supplierId:null,manufacturer:null,manufacturerId:null});c=await eda.sch_PrimitiveComponent.modify(c,props);out.push({ref:p.ref,id:c.getState_PrimitiveId(),pins:await c.getAllPins()});}return {placed:out,saved:await eda.sch_Document.save()};'
    r=execute(code,f'place-carrier-{start}-{end}')
    (ROOT/f'placed-{start}-{end}.json').write_text(json.dumps(r,ensure_ascii=False,indent=2))
    for c in r['placed']:print(c)
elif stage=='wire':
    start=int(sys.argv[2]);end=int(sys.argv[3]);maps={p['ref']:p['nets'] for p in parts[start:end]}
    code=guard+'const maps='+json.dumps(maps)+';const out=[];for(const c of await eda.sch_PrimitiveComponent.getAll()){const ref=c.getState_Designator();if(!maps[ref])continue;for(const p of await c.getAllPins()){const net=maps[ref][p.getState_PinNumber()];if(!net){const a=p.toAsync();a.setState_NoConnected(true);await a.done();continue;}const x=p.getState_X(),y=p.getState_Y(),r=p.getState_Rotation()*Math.PI/180;const ex=x+Math.round(Math.cos(r)*25),ey=y+Math.round(Math.sin(r)*25);const w=await eda.sch_PrimitiveWire.create([x,y,ex,ey],net);if(!w)throw new Error("wire "+ref+"."+p.getState_PinNumber());const label=await eda.sch_PrimitiveComponent.createNetPort("BI",net,ex,ey,0);if(!label)throw new Error("label "+ref);out.push({ref,pin:p.getState_PinNumber(),net});}}return {wired:out,saved:await eda.sch_Document.save()};'
    r=execute(code,f'wire-carrier-{start}-{end}')
    (ROOT/f'wired-{start}-{end}.json').write_text(json.dumps(r,ensure_ascii=False,indent=2))
    print(r)
elif stage=='export':
    r=execute('const f=await eda.sch_ManufactureData.getNetlistFile("DesktopAssistant_Carrier_RevA");return f?{name:f.name,text:await f.text()}:null;','export-carrier-netlist')
    (ROOT/'carrier-netlist-export.json').write_text(json.dumps(r,ensure_ascii=False,indent=2));print({'name':r['name'],'bytes':len(r['text'])})
else:raise SystemExit('Unknown stage')
