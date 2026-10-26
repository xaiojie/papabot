from pathlib import Path
import json,csv,html,hashlib,math
ROOT=Path(__file__).resolve().parent
L=['GPIO1','GPIO2','GPIO3','GPIO4','GPIO5','GPIO6','GND','GPIO7','GPIO8','GPIO9','GPIO10','GPIO11','GPIO12','GPIO13','GPIO14','RESET','3V3','3V3','3V3','GND']
R=['GPIO46','GPIO45','GPIO42','GPIO41','GPIO15','GPIO16','GPIO17','GPIO18','GND','GPIO21','GPIO40','GPIO39','GPIO38','GPIO47','GPIO48','BOOT_GPIO0','5V','5V','5V','GND']
gpio=[(1,'ADC_BAT','电池电压采样','ADC1_CH0','100k/33k/100nF；从总开关后取样'),(8,'PCA_SDA','PCA I2C数据','I/O','上拉只到3.3V，核模块已有阻值'),(9,'PCA_SCL','PCA I2C时钟','OUT','初始100kHz；短线'),(10,'PCA_OE_N','舵机输出禁止','OUT','10k上拉3.3V；高电平禁止；核原模块下拉'),(11,'LCD_MOSI','屏幕SPI数据','OUT','单向SPI，不需要MISO'),(12,'LCD_SCLK','屏幕SPI时钟','OUT','初始10MHz后实测提高'),(13,'LCD_CS_N','屏幕片选','OUT','启动先置高'),(14,'LCD_DC','屏幕数据命令','OUT','3.3V逻辑'),(21,'LCD_RST_N','屏幕复位','OUT','不接主控RESET脚'),(4,'MIC_BCLK','麦克风I2S时钟','OUT','独立I2S接收时钟域'),(5,'MIC_WS','麦克风I2S帧时钟','OUT','32bit槽；采样格式按实际芯片确认'),(6,'MIC_SD','麦克风I2S数据','IN','3.3V麦克风输出'),(15,'AMP_BCLK','功放I2S时钟','OUT','与麦克风分开，避免采样率强绑定'),(16,'AMP_WS','功放I2S帧时钟','OUT','MAX98357A为I2S；B版为左对齐，核丝印'),(17,'AMP_DIN','功放I2S数据','OUT','左右槽先送相同单声道数据'),(7,'ENC_A','后置旋钮A','IN','10k上拉3.3V，机械公共端确认后接地'),(2,'ENC_B','后置旋钮B','IN','10k上拉3.3V，正反方向可固件配置'),(38,'ENC_SW_N','后置旋钮按压','IN','10k上拉3.3V，软件消抖'),(40,'KEY_N','后置独立按键','IN','10k上拉3.3V，软件消抖')]
gmap={f'GPIO{g}':n for g,n,*_ in gpio}
pins=[]
for side,labels in [('L',L),('R',R)]:
 for i,label in enumerate(labels,1):
  net=gmap.get(label, {'GND':'GND','3V3':'+3V3','5V':'+5V_MCU'}.get(label,''))
  status='供电/地' if label in ('GND','3V3','5V') else '本轮分配' if net else '保留不接'
  pins.append({'pad':side+str(i),'label':label,'net':net,'status':status,'manufacturer_pin':('J2' if side=='L' else 'J1')+'.'+str(21-i),'source':'lckfb-datasheet.pdf page 4; lckfb-schematic-core.jpg header block','orientation':'元件面朝上，天线在上，USB在下；每列由上到下1–20。这是本项目坐标，不是厂家焊盘编号。'})
pinloc={x['label']:x['pad'] for x in pins if x['label'].startswith('GPIO')}
with (ROOT/'01-controller-pinout.csv').open('w',encoding='utf-8-sig',newline='') as f:
 w=csv.writer(f);w.writerow(['本项目位置','厂家原理图针号','厂家丝印','本轮网络','状态','观察方向']);w.writerows((p['pad'],p['manufacturer_pin'],p['label'],p['net'],p['status'],p['orientation']) for p in pins)
with (ROOT/'02-gpio-plan.csv').open('w',encoding='utf-8-sig',newline='') as f:
 w=csv.writer(f);w.writerow(['GPIO','主控位置','网络','用途','方向','注意']);w.writerows((g,pinloc['GPIO'+str(g)],n,p,d,a) for g,n,p,d,a in gpio)
connectors=[
 {'ref':'J_LCD','name':'屏幕线束','pins':['GND','+5V_LOGIC','LCD_SCLK','LCD_MOSI','LCD_RST_N','LCD_DC','LCD_CS_N',None],'note':'载板自定义1×8顺序；屏幕端按实物GND/VCC/SCL/SDA/RES/DC/CS/BLK丝印换线，不能认为线序相同。厂家确认VCC为3.3–5V，Rev A接+5V_LOGIC、SPI用3.3V；第8脚与模块BLK各自留空，默认全亮。'},
 {'ref':'J_PCA','name':'PCA信号线束','pins':['GND','+3V3','PCA_SDA','PCA_SCL','PCA_OE_N'],'note':'只接模块GND/VCC/SDA/SCL/OE；模块V+不走此接口，8路舵机红线不接PCA成品板公共电源排针。'},
 {'ref':'J_MIC','name':'麦克风线束','pins':['GND','+3V3','MIC_BCLK','MIC_WS','MIC_SD','MIC_LR_GND'],'note':'模块端功能分别GND/VCC/SCK/WS/SD/LR；MIC_LR_GND与GND在载板相连，拟选左声道。成品板物理顺序和模块身份待确认。'},
 {'ref':'J_AMP','name':'功放信号线束','pins':['GND','AMP_BCLK','AMP_WS','AMP_DIN'],'note':'对应GND/BCLK/LRC/DIN；功放5V另走短粗线，不经此小信号插头。SD_MODE保留模块原配置，禁止直接接GPIO或5V上拉回灌GPIO。'},
 {'ref':'J_REAR','name':'后置控件线束','pins':['GND','ENC_A','ENC_B','GND','ENC_SW_N','GND','KEY_N'],'note':'1=编码器公共端；2=A；3=B；4=旋钮按压公共端；5=旋钮按压；6=独立键公共端；7=独立键。仅适用拆下后确认是无源干触点的元件，EC11实际脚序需通断表。屏幕原控件焊盘不自动并接。'},
 {'ref':'J_LOGIC_IN','name':'逻辑5V入口焊盘','pins':['+5V_LOGIC','GND'],'note':'好盈UBEC设5V，接已购粗线；孔径和焊盘尺寸待线材/电流核定。'},
 {'ref':'J_SENSE','name':'开关后电池采样线束','pins':['VBAT_SW','GND'],'note':'只承载分压电流，接S1A后端；禁止改接开关前节点造成关机ADC反向供电。'}]
components=[]
def comp(ref,value,pindict,where='carrier',status='review_proposal'):
 components.append({'ref':ref,'value':value,'pins':pindict,'location':where,'status':status})
comp('U1','LCKFB-ESP32S3R8N8',{p['pad']:p['net'] for p in pins if p['net']},status='manufacturer_pin_labels_verified; footprint_not_released')
for c in connectors:comp(c['ref'],c['name'],{str(i):n for i,n in enumerate(c['pins'],1)})
comp('JP_MCU','可断开的外供5V连接；默认不装',{'1':'+5V_LOGIC','2':'+5V_MCU'},status='open_for_initial_bringup; U1_USB_VBUS_to_5V_direct_connection_verified; no_simultaneous_USB_and_battery')
comp('JP_SENSE','电池采样可断开线桥；初次上电断开',{'1':'VBAT_SW','2':'VBAT_SENSE'},status='open_until_power_and_ADC_input_voltage_checked')
comp('R1','100k 1% axial 1/4W',{'1':'VBAT_SENSE','2':'ADC_BAT'})
comp('R2','33k 1% axial 1/4W',{'1':'ADC_BAT','2':'GND'})
comp('C1','100nF 50V THT P5.08',{'1':'ADC_BAT','2':'GND'})
comp('R3','10k 1% OE pullup',{'1':'+3V3','2':'PCA_OE_N'})
for i,n in enumerate(['ENC_A','ENC_B','ENC_SW_N','KEY_N'],4):comp('R'+str(i),'10k 1% control pullup',{'1':'+3V3','2':n})
comp('C2','470uF 16V, polarity checked',{'+':'+5V_LOGIC','-':'GND'},'logic regulator output / amplifier branch')
comp('C3','1000uF 10V, polarity checked',{'+':'+5V_SERVO','-':'GND'},'servo power board')
comp('C4','1000uF 10V, polarity checked',{'+':'+5V_SERVO','-':'GND'},'servo power board')
comp('BAT1','2S protected balanced 7.4V pack',{'P+':'VBAT_PROTECTED','P-':'GND'},'battery compartment','supplier_final_spec_pending')
comp('F1','029707.5WXNV in 01530008Z holder',{'1':'VBAT_PROTECTED','2':'VBAT_FUSED'},'dedicated power PCB','holder footprint/current/temperature pending')
comp('SW1','NKK S1A',{'1':'VBAT_FUSED','2':'VBAT_SW'},'rear panel')
comp('CHG1','TELESKY MK021163 Type-C 8.4V charger',{'BAT+':'VBAT_FUSED','BAT-':'GND','USB5V':'USB_CHARGE_5V'},'rear panel','pin labels/current/reverse leakage pending')
comp('REG_S','DFR0753',{'VIN+':'VBAT_SW','VIN-':'GND','VOUT+':'+5V_SERVO','VOUT-':'GND'},'power compartment','product functional ports only; physical pads pending')
comp('REG_L','Hobbywing 86010010 5V jumper',{'VIN+':'VBAT_SW','VIN-':'GND','VOUT+':'+5V_LOGIC','VOUT-':'GND'},'power compartment','factory leads polarity to verify')
comp('PCA1','HANLI PCA9685 module',{'VCC':'+3V3','GND':'GND','SDA':'PCA_SDA','SCL':'PCA_SCL','OE':'PCA_OE_N',**{f'PWM{i}':f'SERVO_PWM{i}' for i in range(8)}},'remote signal module','functional labels known; selected-board pullups/pin order pending')
comp('MIC1','purchased MSM261S4030H0 I2S module',{'VCC':'+3V3','GND':'GND','SCK':'MIC_BCLK','WS':'MIC_WS','SD':'MIC_SD','LR':'MIC_LR_GND'},'acoustic mount','exact board identity unresolved')
comp('AMP1','purchased MAX98357 soldered module',{'VIN':'+5V_LOGIC','GND':'GND','BCLK':'AMP_BCLK','LRC':'AMP_WS','DIN':'AMP_DIN','SPK+':'SPK_P','SPK-':'SPK_N'},'near speaker','actual board labels/SD_MODE/GAIN straps pending')
comp('SPK1','4ohm 3W C50387237',{'1':'SPK_P','2':'SPK_N'},'speaker pocket')
comp('LCD1','TOUGLESY ST7789 2.4inch',{'GND':'GND','VCC':'+5V_LOGIC','SCL':'LCD_SCLK','SDA':'LCD_MOSI','RES':'LCD_RST_N','DC':'LCD_DC','CS':'LCD_CS_N','BLK':None},'front cover','module_VCC_3.3_to_5V_verified; use_5V_LOGIC; BLK_NC_default_full_brightness; physical_pin_order_pending')
for i,leg in enumerate(['前左髋','前左膝','前右髋','前右膝','后左髋','后左膝','后右髋','后右膝']):
 comp('SERVO'+str(i),'MG90S '+leg,{'SIGNAL':f'SERVO_PWM{i}','RED':'+5V_SERVO','RETURN':'GND'},'legs','verify real wire colours and connector orientation')
# MIC LR tied to ground by an explicit wire link; not a second ground domain.
comp('LINK_LR','0-ohm solder bridge',{'1':'MIC_LR_GND','2':'GND'})
nets={}
native_refs={'J_LCD':'J3','J_PCA':'J4','J_MIC':'J5','J_AMP':'J6','J_REAR':'J7','J_LOGIC_IN':'J8','J_SENSE':'J9','JP_MCU':'JP1','JP_SENSE':'JP2'}
for c in connectors:c['native_ref']=native_refs[c['ref']]
for c in components:
 if c['ref'] in native_refs:c['native_ref']=native_refs[c['ref']]
 if c['ref']=='U1':c['native_interface']='C429947 x2, separate 20P sockets; row spacing 17.78mm'
 for pin,n in c['pins'].items():
  if n is not None:nets.setdefault(n,[]).append({'ref':c['ref'],'pin':pin})
netlist={'schema':'desktop-assistant.logical-review-netlist.v1','revision':'A0-electrical / A1-mechanical-candidate','date':'2026-09-08','release_status':'NOT_FOR_FABRICATION','native_eda_project':{'id':'e5e438419c1c4681946d5009bb8d6daf','name':'DesktopAssistant_RevA','writes_by_this_script':False},'module_pin_number_policy':'模块使用功能端名；只U1有原厂图可核的本项目L/R位置。J_*数字是载板设计定义，不是所购模块针号。','components':components,'nets':nets,'connectors':connectors,'conditional_unpowered_nets':[],'no_connect_points':[{'ref':'J_LCD','pin':'8','reason':'reserved connector pin, no BLK wire'},{'ref':'LCD1','pin':'BLK','reason':'supplier permits NC, default full brightness'}],'unpopulated_power_link':'JP_MCU','open_for_initial_bringup':['JP_MCU','JP_SENSE'],'native_carrier_summary':{'schematic_components':22,'pcb_components':21,'off_board_component':'C2 470uF 16V','source':'main task reported native carrier, 2026-09-08','scope':'controller sockets, signal interfaces, low-current power/sense circuitry; external servo and amplifier power by separate harness','logical_count_is_not_native_count':True},'route_constraints':['GND is electrically common; servo returns must run directly to servo regulator/power distribution, never through MCU headers','+5V_SERVO and +5V_LOGIC must never be joined','VBAT_FUSED charger branch before SW1; ADC senses VBAT_SW after SW1 through disconnectable JP2 / JP_SENSE','SPK_P and SPK_N are BTL outputs, neither is ground','Manufacturer schematic confirms U1 USB VBUS directly joined to 5V headers; first USB programming requires U1 removed from carrier; do not plug USB during assembled battery operation; JP1/JP2 are manual disconnectable links, not automatic isolation','Eight servo currents and fuse holder are outside the 80x32 signal carrier proposal'],'source_supplement':{'display':'sources/selected-display-module-evidence.json','controller_power':'sources/lckfb-schematic-core.jpg','review':'05-electrical-evidence-review.md','native_eda_not_modified':True},'not_an_erc_result':True}
(ROOT/'03-logical-netlist.json').write_text(json.dumps(netlist,ensure_ascii=False,indent=2))
(ROOT/'04-connector-map.csv').write_text('\ufeff'+''.join([]))
with (ROOT/'04-connector-map.csv').open('w',encoding='utf-8-sig',newline='') as f:
 w=csv.writer(f);w.writerow(['载板接口','原生位号','载板针号','网络','模块端对应/限制'])
 for c in connectors:
  for i,n in enumerate(c['pins'],1):w.writerow([c['ref'],c['native_ref'],i,n if n is not None else 'NC（不接线）',c['note']])
interface={'revision':'A1 candidate, not frozen','unit':'mm','carrier':{'width':80,'depth':32,'thickness':1.6,'holes':[[5,5],[75,5],[75,27],[5,27]],'hole_diameter':3.2,'world_transform':{'x':'u-40','y':'v-2','z':'w+64','w_origin':'board bottom'},'role':'controller sockets + signal connectors + low current ADC/pullups only','board_layers_proposal':2,'copper_weight_not_selected':True},'controller':{'size_nominal':[51.66,20.32],'header_pitch':2.54,'row_spacing':17.78,'positions_per_row':20,'header_span':48.26,'source':'sources/lckfb-datasheet.pdf page 2','local_board_bounds_proposal':[8,5.84,59.66,26.16],'antenna_facing':'-u / machine left','USB_facing':'+u / machine right','Z_budget_provisional':'1.6 carrier + 8.5mm socket body + male-header seated stack + controller PCB/components; reserve up to w=20 and measure. 8.5mm is not complete installed height.','antenna':'carrier copper/component keepout beneath ceramic antenna; broader no-metal/no-battery/no-cable volume to be derived from original antenna layout. Provisional review zone u8..18,v8..24 is not RF approval.'},'remote_modules':[{'name':'Hobbywing86010010','nominal_size':[43,17,7],'weight_g':11,'source':'https://www.hobbywing.com/products/ubec-3a-2-6s99','extra_envelope':'factory wires, ferrite ring, jumper and wire bend/strain relief not included'}, {'name':'DFR0753','nominal_size':None,'source':'https://www.dfrobot.com.cn/goods-2971.html','note':'HTML provides power ratings, not complete mechanical dimensions; do not substitute DFR1202 dimensions'},{'name':'MSM261S4030H0 microphone module','nominal_size':None,'note':'DFRobot SKU SEN0327 HTML diameter14mm conflicts with its linked Sipeed PDF15.24x9.14x11.2mm; same chip does not identify same board.'}], 'layout_status':'historical A1 area proposal; native 21-component PCB (22 schematic components) is drawn separately by main task; this file does not certify native placement, routing or DRC','native_carrier_components_reported':21,'power_board_required':'MINI PCB fuse holder needs its own rated PCB mounting; independent 8-servo copper distribution. Size/connector/track/ripple and thermal design remains required; 80x32 signal board does not include it.'}
(ROOT/'board-interface.json').write_text(json.dumps(interface,ensure_ascii=False,indent=2))
# SVG construction: text uses source-backed functional labels; no counterfeit EDA symbols.
FONT='Arial, PingFang SC, Microsoft YaHei, sans-serif'
def svgstart(w,h,title,subtitle):
 return [f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">',f'<rect width="{w}" height="{h}" fill="#f5f7f9"/>',f'<style>text{{font-family:{FONT};fill:#183041}} .t{{font-size:26px;font-weight:bold}} .s{{font-size:15px}} .b{{font-size:18px;font-weight:bold}} .m{{font-size:14px}} .note{{fill:#9b5f00}}</style>',f'<text x="30" y="42" class="t">{html.escape(title)}</text>',f'<text x="30" y="71" class="s">{html.escape(subtitle)}</text>']
def text(s,x,y,t,cls='m',fill=None):s.append(f'<text x="{x}" y="{y}" class="{cls}"'+(f' style="fill:{fill}"' if fill else '')+'>'+html.escape(t)+'</text>')
def box(s,x,y,w,h,title,lines,color='#dbe9e3'):
 s.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="8" fill="white" stroke="#98aeb6"/>');s.append(f'<rect x="{x}" y="{y}" width="{w}" height="32" rx="8" fill="{color}"/>');text(s,x+12,y+23,title,'b')
 for i,l in enumerate(lines):text(s,x+12,y+55+i*22,l)
def wire(s,pts,label=None,color='#398469'):
 d=' '.join(f'{x},{y}' for x,y in pts);s.append(f'<polyline points="{d}" fill="none" stroke="{color}" stroke-width="3"/>')
 if label:text(s,pts[0][0]+5,pts[0][1]-9,label,fill=color)
def save(s,name):s.append('</svg>');(ROOT/name).write_text('\n'.join(s))
s=svgstart(1440,990,'电源与关断原理草图 · Rev A','用于审阅连接关系；USB与5V排针直连已证实；模块电流/上电时序仍待实测，不可直接打样。')
box(s,30,120,205,130,'BAT1 · 2S保护电池',['7.4V / 满充8.4V','1000mAh / 整包≥10A','保护＋均衡＋XT30'])
box(s,300,120,195,130,'F1 · 7.5A保险',['MINI保险＋PCB座','靠近电池正极','需专用配电PCB'])
box(s,575,120,210,130,'SW1 · NKK S1A',['机械总开关','断开两路工作负载','充电分支在开关前'])
box(s,925,120,260,140,'REG_S · DFR0753',['6–14V输入 → 5V','标称最大8A，目标6A待测','输入/输出物理焊盘待核'])
box(s,925,335,260,140,'REG_L · 好盈UBEC',['86010010 / 3A (2–6S)','跳帽设5V，先测电压','两路5V禁止并联'])
box(s,1220,120,190,205,'舵机配电',['8×MG90S','每支路独立插座','PWM来自PCA0–7','2×1000uF/10V','地回到舵机降压','不经主控排针'])
box(s,570,335,235,140,'CHG1 · 2S充电板',['USB输入5V','BAT+接保险后/开关前','BAT−接保护后的P−','目标0.4–0.5A；实际待核'])
box(s,925,560,260,140,'逻辑5V与功放支路',['470uF/16V就近放置','功放VIN / 屏VCC接逻辑5V','主控5V经可断JP1','装机电池供电时勿插USB'])
wire(s,[(235,175),(300,175)],'P+');wire(s,[(495,175),(575,175)]);text(s,500,107,'VBAT_FUSED');wire(s,[(785,175),(860,175),(925,175)],'VBAT_SW');wire(s,[(860,175),(860,390),(925,390)]);wire(s,[(1185,175),(1220,175)]);text(s,1190,107,'+5V_SERVO');wire(s,[(535,175),(535,390),(570,390)]);wire(s,[(1055,475),(1055,560)],'+5V_LOGIC');wire(s,[(130,250),(130,290),(460,290),(460,755),(1370,755)],color='#546e7a');text(s,140,285,'P− / GND')
for x,y in [(685,475),(1080,700),(1300,325)]:wire(s,[(x,y),(x,755)],color='#546e7a')
wire(s,[(1055,260),(1205,260),(1205,755)],color='#546e7a')
wire(s,[(1110,475),(1205,475)],color='#546e7a')
box(s,30,335,400,365,'电池ADC · GPIO1 / ADC1_CH0',[])
text(s,43,393,'VBAT_SW → JP2 → VBAT_SENSE'); text(s,96,438,'R1 100k'); text(s,332,407,'GPIO1')
wire(s,[(48,415),(60,415)]);s.append('<circle cx="60" cy="415" r="3" fill="white" stroke="#398469"/><circle cx="85" cy="415" r="3" fill="white" stroke="#398469"/><path d="M60 415L82 403" stroke="#398469" stroke-width="2"/>');wire(s,[(85,415),(95,415)]);s.append('<rect x="95" y="408" width="60" height="14" fill="white" stroke="#398469" stroke-width="2"/>');wire(s,[(155,415),(355,415)])
wire(s,[(245,415),(245,440)]);s.append('<rect x="238" y="440" width="14" height="35" fill="white" stroke="#398469" stroke-width="2"/>');wire(s,[(245,475),(245,505),(310,505)],color='#546e7a');text(s,171,463,'R2 33k')
wire(s,[(310,415),(310,451)]);s.append('<path d="M299 451H321 M299 460H321" stroke="#398469" stroke-width="3"/>');wire(s,[(310,460),(310,505)],color='#546e7a');text(s,327,455,'C1');text(s,322,479,'100nF')
s.append('<circle cx="245" cy="415" r="4" fill="#398469"/><circle cx="310" cy="415" r="4" fill="#398469"/>');wire(s,[(270,505),(270,515)],color='#546e7a');s.append('<path d="M258 515H282 M262 520H278 M266 525H274" stroke="#546e7a" stroke-width="2"/>')
for i,t in enumerate(['8.4V时2.084V；1%最坏约2.116V','等效阻抗24.8kΩ；RC约2.48ms','ADC衰减、校准、断电注入仍需核验','JP2初次断开；确认ADC电压后接通']):text(s,43,555+i*27,t)

text(s,30,807,'共地并不意味着共用细回路线：舵机与功放返回各自电源支路，ADC地就近接主控安静地。','s')
text(s,30,842,'USB首次烧录：取下主控单独接USB；装机电池供电时勿插USB。JP1/JP2为可断线桥，初次均断开。','s')
text(s,30,872,'厂家图已证实USB VBUS与5V排针直连；JP1/JP2不是自动隔离，外供一颗二极管不能保护电脑。','s')
text(s,30,907,'首版关机充电。保险座、动力铜路/线径、支路插针额定、模块温升、充电电流与反向漏电都需进入后续检查。','s')
text(s,30,950,'网络数据：03-logical-netlist.json  |  这是逻辑原理草图，不是已经ERC/DRC通过的EDA原理图。','m')
save(s,'power-schematic.svg')
s=svgstart(1440,1100,'主控与信号连接草图 · Rev A','GPIO来源已核主控原厂图；J_*针号为本项目定义，模块端仍必须按丝印/实物重新排列线序。')
box(s,475,120,450,550,'U1 · LCKFB-ESP32S3R8N8',['SPI: 11 MOSI / 12 CLK / 13 CS','       14 DC / 21 LCD_RST','I2C: 8 SDA / 9 SCL / 10 OE','I2S RX: 4 BCLK / 5 WS / 6 SD','I2S TX: 15 BCLK / 16 WS / 17 DIN','REAR: 7 A / 2 B / 38 PRESS / 40 KEY','ADC: 1 (ADC1_CH0)','3V3: L17/L18/L19 → 信号外设','5V: R17/R18/R19 ← JP1线桥','GND: L7/L20/R9/R20','天线上、USB下观察，左右列编号','避用0/3/45/46启动脚、48板载LED','USB19/20、UART43/44及内存脚保留','未使用18/39/41/42/47暂不连接','每个GPIO仅分配一次'])
box(s,30,120,360,210,'J3 · LCD 1×8（载板顺序）',['1 GND / 2 +5V_LOGIC','3 CLK / 4 MOSI / 5 LCD_RST','6 DC / 7 CS / 8 NC不接线','模块3.3–5V；本版供5V','SPI用3.3V，BLK留空默认全亮','保留91×44原板，控件移至后方'])
box(s,30,420,360,230,'J7 · 后置控件1×7',['1 编码器公共端 → GND','2 A → GPIO7 / 3 B → GPIO2','4 按压公共端 → GND','5 按压 → GPIO38','6 独立键公共端 → GND','7 独立键 → GPIO40','A/B/两键各10k上拉3.3V'])
box(s,1015,120,395,190,'J4 · PCA逻辑1×5',['1 GND / 2 VCC=3.3V','3 SDA=8 / 4 SCL=9 / 5 OE=10','OE：10k上拉，默认禁用','先核模块下拉；V+不接本接口','PWM0–7只取信号，供电外部分配'])
box(s,1015,385,395,190,'J5 · MIC 1×6',['1 GND / 2 VCC=3.3V','3 SCK=4 / 4 WS=5 / 5 SD=6','6 LR→GND（左声道提案）','圆板14mm vs 矩形资料存在冲突','保留功能映射，暂不锁物理孔位'])
box(s,1015,660,395,210,'J6 · AMP 1×4信号',['1 GND / 2 BCLK=15','3 LRC=16 / 4 DIN=17','VIN从逻辑5V另接粗短线','SPK+ / SPK− → 4Ω3W喇叭','BTL两端均不得接GND','SD_MODE/GAIN原板配置待核'])
wire(s,[(390,220),(475,220)],'SPI');wire(s,[(390,520),(475,520)],'控件');wire(s,[(925,220),(1015,220)],'I2C');wire(s,[(925,445),(1015,445)],'I2S RX');wire(s,[(925,590),(960,590),(960,730),(1015,730)],'I2S TX')
box(s,30,745,895,145,'8路PWM与腿位（固件命名提案）',['0 前左髋　1 前左膝　2 前右髋　3 前右膝','4 后左髋　5 后左膝　6 后右髋　7 后右膝','50Hz为调试起点；先单舵机卸载限位标定，PWM中值不代表机构绝对安全角度','OE只禁止PWM，不能切断舵机供电；八舵机上电/重启动作仍需实测'])
text(s,30,949,'后置控件：拆下后测出A/B/C、按压两端与独立键两端，再接线束；不凭通用EC11照片定义实物脚序。','s')
text(s,30,979,'外设供电/固件启动顺序：OE保持高 → 配置I2C/PCA频率与零输出 → 自检/低电压检查 → 最后使能。','s')
text(s,30,1009,'供电：J8接逻辑5V；J9接开关后电池采样。JP1控主控5V，JP2控采样；两线桥初次上电断开。','s')
text(s,30,1039,'原理图22元件/PCB21元件，C2外置；高电流支路走外部线束。厂家USB与5V直连，装机电池供电勿插USB。','s')
text(s,30,1080,'GPIO表：02-gpio-plan.csv  |  接口逐针表：04-connector-map.csv  |  未冻结项：README.md','m')
save(s,'signal-schematic.svg')
s=svgstart(1280,750,'载板与结构接口 · A1候选','80×32×1.6mm只是空间分配草案，主控可放入，不代表连接器、走线和高度已经全部通过。')
scale=11;ox=95;oy=200
def pos(u,v):return ox+u*scale,oy+(32-v)*scale
s.append(f'<rect x="{ox}" y="{oy}" width="880" height="352" fill="#d9e8e1" stroke="#398469" stroke-width="3"/>')
for u,v in [[5,5],[75,5],[75,27],[5,27]]:
 x,y=pos(u,v);s.append(f'<circle cx="{x}" cy="{y}" r="17.6" fill="white" stroke="#567"/>');s.append(f'<circle cx="{x}" cy="{y}" r="33" fill="none" stroke="#b1c3ba" stroke-dasharray="5 4"/>')
x,y=pos(8,26.16);s.append(f'<rect x="{x}" y="{y}" width="{51.66*scale}" height="{20.32*scale}" fill="#faf8ee" stroke="#7d8a9b"/>');text(s,x+140,y+90,'U1 51.66 × 20.32mm','b');text(s,x+140,y+117,'两排20P · 列距17.78mm','m')
for v in [7.11,24.89]:
 for i in range(20):
  x,y=pos(9.70+i*2.54,v);s.append(f'<circle cx="{x}" cy="{y}" r="5" fill="#ad874c"/>')
x,y=pos(8,24);s.append(f'<rect x="{x}" y="{y}" width="110" height="176" fill="#f5d098" fill-opacity="0.6" stroke="#d08829" stroke-dasharray="6 4"/>');text(s,x+6,y+76,'天线','b');text(s,x+6,y+101,'净空待核','m')
x,y=pos(59.66,16);wire(s,[(x,y),(x+50,y)],'USB → +X','#587ba6')
text(s,ox+630,oy+80,'右侧接口候选区','m');text(s,ox+630,oy+103,'不能占USB插头空间','m');text(s,ox+240,oy+330,'前侧LCD短线　/　后侧控件短线','m')
text(s,40,605,'整机坐标：X=u−40，Y=v−2，Z=w+64；w=0是载板底面。四孔Ø3.2，中心(5,5)(75,5)(75,27)(5,27)。','s')
text(s,40,635,'高度先预留载板底到最高点20mm，包含插座/开发板/线束弯折；排母8.5mm不是完整装配高度。','s')
text(s,40,665,'外置：MINI保险配电板、舵机铜母线、两路降压、PCA、功放、麦克风；需结构继续容纳并留检修/散热。','s')
text(s,40,710,'本图保留A1空间候选；原生21元件PCB由主任务维护，实际板框/位置/DRC以原生工程为准。','m')
save(s,'board-interface.svg')
# Review checks catch mapping mistakes without pretending to be electrical/ERC validation.
assert len(gpio)==len(set(g for g,*_ in gpio))
assert not set(g for g,*_ in gpio)&{0,3,19,20,26,27,28,29,30,31,32,33,34,35,36,37,43,44,45,46,48}
assert all('GPIO'+str(g) in pinloc for g,*_ in gpio)
assert len(pins)==40 and len({p['pad'] for p in pins})==40
assert not any(c['pins'].get('VOUT+')=='+5V_SERVO' and c['ref']=='REG_L' for c in components)
assert set(components[-1]['pins'].values())=={'MIC_LR_GND','GND'}
assert {x['pin'] for x in nets['ADC_BAT'] if x['ref']=='U1'}=={'L1'}
assert all(x['ref'] not in ['R1','J_SENSE','JP_SENSE'] for x in nets['VBAT_FUSED'])
assert {x['ref'] for x in nets['VBAT_SENSE']}=={'JP_SENSE','R1'}
assert next(c for c in components if c['ref']=='LCD1')['pins']['VCC']=='+5V_LOGIC'
assert next(c for c in components if c['ref']=='LCD1')['pins']['BLK'] is None
assert None not in nets
assert all(next(c for c in components if c['ref']==e['ref'])['pins'][e['pin']]==n for n,es in nets.items() for e in es)
assert all(x['ref'] in ['AMP1','SPK1'] for n in ['SPK_P','SPK_N'] for x in nets[n])
validation={'status':'review_data_checks_passed','checks':['40 unique U1 header locations','19 unique GPIO assignments on exposed pins','reserved boot/USB/memory/LED pins not allocated','ADC uses GPIO1/L1 and switched battery node','separate servo and logic 5V net names','speaker BTL nets only join amp and speaker','module physical pin numbers not invented','screen VCC uses 5V_LOGIC and two NC points excluded from nets','JP2 separates switched battery sense input from R1','manufacturer J1/J2 number mapping included'],'not_performed':['EDA ERC','PCB placement/routing/DRC','populated CAD collision checks','real USB backfeed test','servo current/thermal/EMI validation'],'counts':{'gpio':len(gpio),'controller_pins':len(pins),'components':len(components),'nets':len(nets),'no_connect_points':len(netlist['no_connect_points']),'native_schematic_reported_by_main_task':22,'native_pcb_reported_by_main_task':21},'source_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT/'sources').iterdir() if p.suffix.lower() in ['.pdf','.jpg','.png']}}
(ROOT/'validation.json').write_text(json.dumps(validation,ensure_ascii=False,indent=2))
print(json.dumps(validation['counts']))
