"""Deterministic, project-local schematic repair from live native templates.
Coordinates are schematic units (10 mil), with Y increasing toward page top.
Electrical connections are explicit in REVIEWED; native export is verified separately.
"""
import json, copy, math, hashlib
from pathlib import Path
from eda_client import ROOT

def read_source(path):
 out=[]
 for l in Path(path).read_text().splitlines():
  if '||' in l:
   h,v=l.split('||',1);out.append((json.loads(h),json.JSONDecoder().raw_decode(v)[0]))
 return out
ALL=read_source(ROOT/'template.source')
COMPS={h['id']:(h,v) for h,v in ALL if h['type']=='COMPONENT'}
ATTRS={}
for h,v in ALL:
 if h['type']=='ATTR':ATTRS.setdefault(v['parentId'],[]).append((h,v))
OLDS={v['value']:v['parentId'] for h,v in ALL if h['type']=='ATTR' and v.get('key')=='Designator'}
PINS={i['id']:i['pins'] for i in json.load(open(ROOT/'all-pins.json'))}
TEMPLATES=json.load(open(ROOT/'templates.json'))
for x in TEMPLATES.values():PINS[x['id']]=x['pins']
LIBS=json.load(open(ROOT/'before/library_docs.json'))
REVIEWED={};LAYOUT={};PAGES={};counter=0

def uid(k):return hashlib.sha256(('integrated-repair-v1:'+k).encode()).hexdigest()[:16]
def attrs(cid):return {v['key']:v.get('value') for h,v in ATTRS.get(cid,[])}
def record(t,k,v):
 global counter
 counter+=1
 return ({'type':t,'id':uid(k),'ticket':10000+counter},v)
def attribute(cid,key,value,**kw):
 return record('ATTR',cid+':'+key,dict(parentId=cid,key=key,value=value,zIndex=10,keyVisible=False,valueVisible=False,**kw))
def text(page,value,x,y,size=10,color='#26364A',bold=False):
 PAGES[page].append(record('TEXT',f'text:{page}:{x}:{y}:{value}',{'x':x,'y':-y,'rotation':0,'color':color,'fontFamily':None,'fontSize':size,'fontWeight':bold,'italic':False,'underline':False,'align':'LEFT_BOTTOM','value':value,'fillColor':color,'zIndex':3000}))
def box(page,title,x1,y1,x2,y2):
 PAGES[page].append(record('RECT',f'box:{page}:{title}',{'radiusX':0,'radiusY':0,'dotX1':x1,'dotX2':x2,'dotY1':-y1,'dotY2':-y2,'strokeColor':'#BAC9D9','strokeStyle':None,'fillColor':None,'strokeWidth':1,'fillStyle':None,'rotation':0,'zIndex':1,'locked':False}))
 text(page,title,x1+15,y1-25,12,'#214F78',True)
def wire(page,key,points,net,show=True):
 wid=uid('wire:'+key)
 PAGES[page].append(({'type':'WIRE','id':wid,'ticket':10000},{'zIndex':100}))
 for i,(p,q) in enumerate(zip(points,points[1:])):
  PAGES[page].append(record('LINE',f'{key}:{i}',{'fillColor':None,'fillStyle':None,'strokeColor':None,'strokeStyle':None,'strokeWidth':None,'startX':p[0],'startY':-p[1],'endX':q[0],'endY':-q[1],'lineGroup':wid}))
 p,q=points[0],points[1]
 a=attribute(wid,'NET',net);a[1].update(valueVisible=show,fontSize=6,rotation=0,fontFamily=None,color=None,fillColor=None,align='LEFT_BOTTOM')
 if q[0]<p[0]:a[1].update(x=p[0]-5,y=-p[1]-2,align='RIGHT_BOTTOM')
 elif q[0]>p[0]:a[1].update(x=p[0]+5,y=-p[1]-2)
 else:a[1].update(x=p[0]-2,y=-p[1]-(5 if q[1]>p[1] else -5),rotation=90,align='LEFT_BOTTOM' if q[1]>p[1] else 'RIGHT_BOTTOM')
 PAGES[page].append(a)
 PAGES[page].append(attribute(wid,'Relevance',[]))

def part(page,ref,template,x,y,nets,name=None,rotation=None,bom=True,pcb=True):
 oldid=TEMPLATES[template]['id'] if template in TEMPLATES else OLDS[template]
 h,c=copy.deepcopy(COMPS[oldid]);oa=attrs(oldid)
 # Existing component identities are preserved when retaining the same device/ref.
 cid=oldid if ref==template else uid('component:'+ref)
 dx=x-c['x'];dy=-y-c['y'];oldrot=c['rotation'];rot=oldrot if rotation is None else rotation
 angle=math.radians(rot-oldrot)
 c.update(x=x,y=-y,rotation=rot,zIndex=200);h.update(id=cid,ticket=10000)
 PAGES[page].append((h,c))
 data=dict(oa)
 devdoc=LIBS.get(oa.get('Device'),[])
 for hh,vv in devdoc:
  if hh['type']=='META':
   for k,val in vv.get('attributes',{}).items():
    if k in ['Supplier Part','Manufacturer Part','Manufacturer','Supplier','Value','Datasheet','Description','Tolerance','Power(Watts)']:data[k]=val
 if template in TEMPLATES:
  d=TEMPLATES[template]['device']
  data.update({k:v for k,v in d['otherProperty'].items() if k not in ['Symbol','Footprint','Designator','Name']})
 data.update({'Designator':ref,'Name':name or oa.get('Name') or ref,'Unique ID':'int-'+ref,'Add into BOM':'yes' if bom else 'no','Convert to PCB':'yes' if pcb else 'no'})
 actualpins=[]
 for p0 in PINS[oldid]:
  p=copy.deepcopy(p0);px=p['x']-COMPS[oldid][1]['x'];py=p['y']+COMPS[oldid][1]['y']
  p['x']=round(x+px*math.cos(angle)-py*math.sin(angle),6);p['y']=round(y+px*math.sin(angle)+py*math.cos(angle),6);p['rotation']=(p['rotation']+rot-oldrot)%360
  suffix=p['primitiveId'][len(oldid):];p['primitiveId']=cid+suffix;actualpins.append(p)
 if set(nets)!={p['pinNumber'] for p in actualpins}:raise ValueError((ref,set(nets),[p['pinNumber'] for p in actualpins]))
 top=max([y]+[p['y'] for p in actualpins]);bottom=min([y]+[p['y'] for p in actualpins]);hasup=any(p['rotation']==90 and nets[p['pinNumber']] for p in actualpins);hasdown=any(p['rotation']==270 and nets[p['pinNumber']] for p in actualpins)
 for key,val in data.items():
  a=attribute(cid,key,val)
  if key in ['Designator','Name']:
   a[1].update(valueVisible=True,x=x,y=-(top+50 if hasup else top+20) if key=='Designator' else -(bottom-55 if hasdown else bottom-28),rotation=0,align='CENTER_BOTTOM',fontSize=8 if key=='Designator' else 7,fontFamily=None)
  PAGES[page].append(a)
 for p in actualpins:
  n=nets[p['pinNumber']]
  if n is None:
   PAGES[page].append(attribute(p['primitiveId'],'NO_CONNECT','yes',x=p['x'],y=-p['y']))
  else:
   a=math.radians(p['rotation']);end=(round(p['x']+45*math.cos(a),6),round(p['y']+45*math.sin(a),6))
   wire(page,ref+':'+p['pinNumber'],[(p['x'],p['y']),end],n)
 REVIEWED[ref]={'page':page,'template':template,'id':cid,'name':data['Name'],'pins':nets,'pinNames':{p['pinNumber']:p['pinName'] for p in actualpins},'pcb':pcb,'bom':bom}
 LAYOUT[ref]=actualpins

def two(page,ref,template,x,y,a,b,name=None,rotation=None):part(page,ref,template,x,y,{'1':a,'2':b},name,rotation)
def orig(page,ref,x,y,change=None,name=None):
 c=next(c for c in json.load(open(ROOT/'before/netlist.json'))['components'].values() if c['props']['Designator']==ref)
 ns={k:v['net'] or None for k,v in c['pinInfoMap'].items()};ns.update(change or {});part(page,ref,ref,x,y,ns,name)

page_defs=[('01','Battery protection and balance / 电池保护与均衡'),('02','USB-C charger / 2S 锂电充电'),('03','Power and MCU / 配电与主控'),('04','Display, audio and controls / 显示音频与交互'),('05','PWM and servos / 舵机控制与配电')]
frame='2a4da8965798a747'
for pg,title in page_defs:
 PAGES[pg]=[copy.deepcopy(r) for r in ALL if r[0]['type'] in ['DOCHEAD','CANVAS']]
 # Preserve the official A3 title block and editable sheet metadata.
 fh,fc=copy.deepcopy(COMPS[frame]);fid=uid('frame:'+pg);fh['id']=fid
 PAGES[pg].append((fh,fc))
 for ah,av in copy.deepcopy(ATTRS[frame]):
  ah['id']=uid(pg+ah['id']);av['parentId']=fid
  if av.get('key')=='Title Block':av['value']='0'
  if av.get('key')=='Version':av['value']='1.1'
  PAGES[pg].append((ah,av))
 text(pg,'DesktopAssistant Integrated  |  '+title,60,1115,18,'#183F62',True)
 text(pg,'Revision 1.1  •  2026-09-12  •  '+pg+' / 05',60,1085,9,'#576A7D')

p='01';box(p,'2S battery input / 原始电芯端',50,1050,490,780);box(p,'HY2120-CB protection / 过充过放与短路保护',520,1050,1600,600)
part(p,'JBAT','XT30',270,915,{'1':'VBAT_RAW_N','2':'VBAT_RAW_P','3':None,'4':None},'XT30 battery input')
part(p,'JBAL','XH3',270,815,{'1':'VBAT_RAW_N','2':'BM','3':'VBAT_RAW_P'},'2S balance harness')
text(p,'JBAL: 1=B−, 2=BM, 3=B+; verify cable polarity.',70,760,9)
part(p,'U1','HY2120',1080,900,{'1':'DOUT_GATE','2':'COUT_GATE','3':'VM_SENSE','4':'PROT_VC','5':'PROT_VDD','6':'VBAT_RAW_N'},'HY2120-CB')
two(p,'R1','R1',700,970,'VBAT_RAW_P','PROT_VDD','330R')
two(p,'R2','R2',700,855,'BM','PROT_VC','330R')
two(p,'C1','C1',1410,970,'PROT_VDD','VBAT_RAW_N','100nF / 50V')
two(p,'C2','C2',1410,855,'PROT_VC','VBAT_RAW_N','100nF / 50V')
two(p,'R3','R3',1410,735,'VM_SENSE','GND','1K (datasheet min)')
for ref,x,src,gate in [('Q2',730,'VBAT_RAW_N','DOUT_GATE'),('Q1',1070,'GND','COUT_GATE')]:part(p,ref,ref,x,700,{str(k):src if k<4 else gate if k==4 else 'MOS_MID' for k in range(1,9)},'AO4406 / '+('discharge' if ref=='Q2' else 'charge'))
text(p,'B− → Q2(S-D) → MOS_MID → Q1(D-S) → protected GND',550,620,10)
box(p,'Lower cell balance / 下节电芯',50,570,780,230);box(p,'Upper cell balance / 上节电芯',820,570,1600,230)
for u,q,rf,rb,rg,cap,high,low,left,cy in [('U2','Q3','R4','R18','R19','C3','BM','VBAT_RAW_N',50,430),('U3','Q4','R5','R20','R21','C4','VBAT_RAW_P','BM',820,430)]:
 idx='1' if u=='U2' else '2';vdd='BAL'+idx+'_VDD';gate='BAL'+idx+'_GATE';bleed='BAL'+idx+'_BLEED'
 two(p,rf,'R100',left+165,cy+80,high,vdd,'100R')
 part(p,u,'HY2213',left+175,cy-20,{'1':None,'2':vdd,'3':low,'4':None,'5':None,'6':gate},'HY2213-BB3A')
 two(p,cap,'C1',left+175,cy-160,vdd,low,'100nF / 50V')
 two(p,rb,'R220',left+520,cy+80,high,bleed,'220R / 1206 / 0.25W')
 part(p,q,q,left+520,cy-45,{'1':gate,'2':low,'3':bleed},'AO3400A')
 two(p,rg,'R10',left+520,cy-155,gate,low,'100K gate pull-down',0)
text(p,'Balance current ≈ 19mA at 4.2V; each bleed resistor ≈ 0.08W.',60,185,10)
text(p,'GND is protected pack negative. Do not short GND to VBAT_RAW_N.',60,155,10,'#A02C2C',True)
text(p,'Protection and balance thresholds require bench validation before battery use.',60,125,9)

p='02';box(p,'5V USB-C input / 专用 5V 适配器',50,1050,520,610);box(p,'IP2326 synchronous boost charger',550,1050,1600,610)
ns={k:None for k in next(c for c in json.load(open(ROOT/'before/netlist.json'))['components'].values() if c['props']['Designator']=='J6')['pinInfoMap']};ns.update({'1':'GND','2':'GND','3':'GND','4':'GND','B5':'CC2','A5':'CC1','B1A12':'GND','B4A9':'VBUS','A4B9':'VBUS','A1B12':'GND'})
part(p,'J6','J6',300,870,ns,'USB-C / charge only')
two(p,'R16','R16',185,680,'CC1','GND','5.1K Rd',0);two(p,'R17','R17',400,680,'CC2','GND','5.1K Rd',0)
part(p,'U4','IP2326',1080,820,{'1':None,'2':None,'3':None,'4':'NTC','5':None,'6':'CHG_LED','7':'CHG_TIME','8':None,'9':None,'10':None,'11':'CHG_ISET','12':'CHG_EN','13':'CHG_VIN','14':'BST_CAP','15':'SW_CHG','16':'SW_CHG','17':'SW_CHG','18':'GND','19':'CHG_VSYS','20':'CHG_VSYS','21':'VBAT_FUSED','22':'VBAT_FUSED','23':None,'24':None,'25':'GND'},'IP2326 / QFN24+EP')
two(p,'L1','L2U2',770,960,'VBUS','SW_CHG','2.2uH / 10A')
two(p,'R6','R050',770,820,'VBUS','CHG_VIN','0.5R / VIN filter')
two(p,'C8','C8',1400,960,'BST_CAP','SW_CHG','100nF / bootstrap')
two(p,'C11','C22',1400,820,'CHG_VSYS','GND','22uF / 25V')
two(p,'C12','C22',1400,695,'CHG_VSYS','GND','22uF / 25V')
box(p,'Input / output decoupling',50,580,800,350)
for ref,tmp,x,y,a,name in [('C6','C6',220,480,'VBUS','10uF / 50V'),('C5','C6',570,480,'CHG_VIN','10uF / 50V'),('C7','C7',220,395,'VBAT_FUSED','10uF / 50V'),('C13','C7',570,395,'VBAT_FUSED','10uF / 50V')]:two(p,ref,tmp,x,y,a,'GND',name)
box(p,'Charge settings / 电流、超时和电池温度',850,580,1600,260)
two(p,'R8','R255K',1050,490,'CHG_ISET','GND','255K / 1% → 0.353A')
two(p,'R22','R120K',1400,490,'CHG_TIME','GND','120K → 12h timeout')
two(p,'R23','R82K',1050,355,'NTC','GND','82K / NTC parallel')
two(p,'J7','XH2',1400,355,'NTC','GND','100K NTC / B4100 probe')
box(p,'Charge enable and status / 默认禁止充电',50,320,800,100)
two(p,'JP_CHG','HDR2',220,235,'CHG_VIN','CHG_EN','Fit shunt to enable')
two(p,'R24','R10',580,235,'CHG_EN','GND','100K EN pull-down',0)
two(p,'R7','R100',220,140,'CHG_LED','LED_A','100R LED series')
part(p,'D2','D2',580,140,{'1':'GND','2':'LED_A'},'Red / charging',0)
text(p,'2S: CON_SEL NC; 8.4V: VSET NC; VIN UV/OV: NC defaults.',850,220,9)
text(p,'External HY2213 balance: IP2326 pins 23/24 left NC.',850,195,9)
text(p,'Use regulated 5V ≥ 2A adapter. D+/D− unused; no QC request.',850,170,9)
text(p,'JP_CHG defaults OPEN. NTC must touch battery; charge with main switch OFF.',850,145,9,'#A02C2C')
text(p,'0.353A is calculated; validate charge current/termination before battery use.',850,120,9)

p='03';box(p,'Protected pack → fuse → switch → regulators',50,1050,1600,760)
two(p,'F1','F2',260,930,'VBAT_RAW_P','VBAT_FUSED','01530008Z fuse holder')
text(p,'Fit 029707.5WXNV 7.5A fuse into F1.',75,855,9)
two(p,'J_SW','TERM2',640,930,'VBAT_FUSED','VBAT_SW','External DC power switch')
text(p,'1=fused input; 2=switched output.',495,855,9)
two(p,'J_LOG_IN','TERM2',1060,955,'VBAT_SW','GND','MP1584 module VIN ±')
two(p,'J_LOG_OUT','TERM2',1430,955,'+5V_LOGIC','GND','MP1584 module VOUT ±')
two(p,'J_SRV_IN','TERM2',1060,825,'VBAT_SW','GND','DFR0753 module VIN ±')
two(p,'J_SRV_OUT','TERM2',1430,825,'+5V_SERVO','GND','DFR0753 module VOUT ±')
text(p,'Two external regulator modules; outputs are separate. Set both to 5.0V before connection.',65,730,10,'#A02C2C')
box(p,'ESP32-S3 carrier sockets / 保留已核对的开发板针序',50,690,850,200)
orig(p,'J1',310,440,{**{str(k):'MCU_5V' for k in [17,18,19]}},'ESP32 right row R1-R20')
orig(p,'J2',685,440,{'11':'PCA_OE'},'ESP32 left row L1-L20')
text(p,'MCU 5V isolated by JP_MCU; OPEN during USB debugging.',70,225,9,'#A02C2C')
box(p,'Logic supply / USB isolation',900,690,1600,465)
two(p,'JP_MCU','HDR2',1100,570,'+5V_LOGIC','MCU_5V','MCU supply shunt / OPEN')
two(p,'C10','C10',1440,570,'+5V_LOGIC','GND','470uF / 16V')
box(p,'Battery ADC / switched measurement',900,430,1600,215)
two(p,'R10','R10',1090,340,'VBAT_SW','ADC_BAT','100K / 1%',0)
two(p,'R9','R9',1420,340,'ADC_BAT','GND','33K / 1%',0)
two(p,'C14','C1',1090,250,'ADC_BAT','GND','100nF low-pass')
text(p,'ADC_BAT ≈ 2.08V at pack 8.4V.',1280,250,9)
text(p,'Each module connector: pin 1 positive, pin 2 GND. Modules are external, not on-board footprints.',60,160,10)
text(p,'J_SW is a cable interface, not a diode. Use a DC-rated switch appropriate for servo startup current.',60,130,9)

p='04';box(p,'3.3V LCD supply / 独立隔离的屏幕支路',50,1050,770,660);box(p,'SPI display / HS24S010B',810,1050,1600,660)
two(p,'JP_LCD','HDR2',260,935,'+3V3','LCD_3V3','MCU 3V3 → LCD / OPEN')
two(p,'J10','XH2',580,935,'LCD_3V3','GND','External regulated 3.3V')
two(p,'C15','C1',260,770,'LCD_3V3','GND','100nF')
two(p,'C16','C6',580,770,'LCD_3V3','GND','10uF / 50V')
orig(p,'J3',1200,865,{'2':'LCD_3V3','8':'LCD_3V3'},'HS24S010B / 3.3V')
text(p,'Select ONE LCD source. Keep JP_LCD open when J10 is used.',70,690,9,'#A02C2C')
text(p,'Pins 1-10 = primary interface; alternate pins 11-20 unused.',830,690,9)
box(p,'I2S module harnesses / 音频线束接口',50,630,770,220)
orig(p,'J4',290,500,name='MIC harness / SEN0327')
orig(p,'J5',625,500,name='AMP harness / MAX98357A')
text(p,'J4: 1=BCLK, 2=WS, 3=SD, 4=3V3, 5=GND, 6=L/R GND.',70,365,9)
text(p,'J5: 1=BCLK, 2=WS, 3=DIN, 4=5V, 5=GND, 6=GND aux.',70,335,9)
text(p,'These are wire-harness pinouts; follow signal names on the modules.',70,300,9)
text(p,'Speaker connects to amplifier OUT+/OUT−, not motherboard GND.',70,270,9)
box(p,'EC11 controls / 旋钮与按压',810,630,1600,220)
orig(p,'EC1',1050,450,name='EC1106S encoder')
two(p,'R11','R11',1400,545,'+3V3','ENC_A','10K',0)
two(p,'R12','R12',1400,415,'+3V3','ENC_B','10K',0)
two(p,'R26','R11',1400,285,'+3V3','ENC_SW_N','10K button pull-up',0)
text(p,'All ESP32 signals are 3.3V. Debounce encoder and button in firmware.',60,170,10)
text(p,'LCD source follows RevB isolation strategy. This page does not connect the two regulator outputs.',60,140,9)

p='05';box(p,'PCA9685  •  I2C 0x40  •  OE high = outputs disabled',50,1050,780,590)
orig(p,'U7',400,820,{'23':'PCA_OE','25':'GND'},'PCA9685PW / 3.3V logic')
two(p,'C17','C1',250,650,'+3V3','GND','100nF near VDD')
two(p,'C18','C6',600,650,'+3V3','GND','10uF local bypass')
box(p,'I2C pull-ups and safe startup',820,1050,1600,710)
two(p,'R13','R13',1040,925,'+3V3','PCA_SDA','10K SDA',0)
two(p,'R14','R14',1400,925,'+3V3','PCA_SCL','10K SCL',0)
two(p,'R15','R15',1040,790,'+3V3','PCA_OE','10K OE pull-up',0)
text(p,'OE defaults HIGH. Firmware must initialize PWM before enabling.',845,730,9)
box(p,'Eight 3-pin servo headers / 1=PWM, 2=+5V_SERVO, 3=GND',50,550,1600,230)
for i in range(8):part(p,'SV'+str(i+1),'HDR3',250+(i%4)*370,440-(i//4)*135,{'1':'PWM'+str(i),'2':'+5V_SERVO','3':'GND'},'Servo '+str(i))
two(p,'C9','C9',1040,630,'+5V_SERVO','GND','1000uF / 10V bulk')
two(p,'C19','C1',1400,630,'+5V_SERVO','GND','100nF ceramic')
text(p,'Servo power has its own 5V converter; route high-current return directly to protected power ground.',60,180,10)
text(p,'LED8-LED15 unused. EXTCLK tied to GND for internal oscillator. All address pins are GND.',60,150,9)
text(p,'No servo motion until supply, polarity, current limit and firmware fail-safe behavior have been tested.',60,120,9)

out=ROOT/'generated';out.mkdir(exist_ok=True)
for pg,rs in PAGES.items():
 (out/f'{pg}.source').write_text('\n'.join(json.dumps(h,ensure_ascii=False,separators=(',',':'))+'||'+json.dumps(v,ensure_ascii=False,separators=(',',':'))+'|' for h,v in rs)+'\n')
(out/'reviewed-pin-nets.json').write_text(json.dumps(REVIEWED,ensure_ascii=False,indent=2))
(out/'pins-layout.json').write_text(json.dumps(LAYOUT,ensure_ascii=False,indent=2))
print({p:sum(1 for x in REVIEWED.values() if x['page']==p) for p in PAGES})
print('Total components:',len(REVIEWED),'pins:',sum(len(x['pins']) for x in REVIEWED.values()))
