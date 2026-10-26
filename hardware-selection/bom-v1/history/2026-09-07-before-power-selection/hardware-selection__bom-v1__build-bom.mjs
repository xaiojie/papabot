import fs from 'node:fs/promises';
import path from 'node:path';
import crypto from 'node:crypto';
import { Workbook, SpreadsheetFile } from '@oai/artifact-tool';

const root = '/Users/jay/work/自研桌面助手/ESP32-desktop-assistant-handoff';
const here = path.join(root, 'hardware-selection/bom-v1');
const output = path.join(root, 'outputs/01a07a09-ef1b-7760-a41d-14c5a4d8f9ec');
await fs.mkdir(output, { recursive: true });
const refs = {
  mg: 'https://towerpro.com.tw/product/mg90s-3/',
  sg: 'https://towerpro.com.tw/product/sg90-analog/',
  esp: 'https://www.waveshare.net/shop/ESP32-S3-DEV-KIT-N16R8.htm',
  pwm: 'https://www.nxp.com/docs/en/data-sheet/PCA9685.pdf',
  amp: 'https://www.analog.com/en/products/max98357a.html',
};
// Unit budgets are planning inputs. Only E01 and E02 have supplier screenshot prices.
// Columns: ID, item, qty, unit, low, base, high, status, mechanical dependency, price evidence, source/search.
const bom = [
  ['E01','途格斯 2.4寸 ST7789 TFT＋EC11',1,'块',32.4,32.4,32.4,'已选，待实测','开窗、支架、前盖深度','用户此前选中 SKU 截图 ¥32.4；非实时价','hardware-selection/reference/screen-2p4-ec11-price-32p40.png'],
  ['E02','MG90S 全金属齿轮 180度，带舵盘螺丝',8,'个',10,10,10,'本轮选定，待实测','安装耳、输出轴、舵盘、腿部承载','用户图二选中 SKU 截图 ¥10；非实时价',refs.mg],
  ['E03','ESP32-S3 N16R8 已焊排针开发板',1,'块',38,45,55,'推荐型号，板型待定','USB孔、托板、排母高度与天线空间','预算预留；官网有型号，未读到人民币价',refs.esp+'（参考 N16R8-M）'],
  ['E04','PCA9685 16路 PWM 成品模块',1,'块',8,12,15,'推荐模块，待选商品','托板、排针与舵机插头空间','预算预留，未询价',refs.pwm],
  ['E05','I²S 数字麦克风模块，INMP441 类',1,'块',6,8,12,'推荐接口，待选商品','声孔方向、密封导音、安装卡座','预算预留，未询价','检索：INMP441 I2S 麦克风模块 已焊排针 尺寸图'],
  ['E06','MAX98357A I²S 单声道功放模块',1,'块',4,6,10,'推荐模块，待选商品','托板、接线端子空间','预算预留，未询价',refs.amp],
  ['E07','4Ω 3W 小喇叭，优先约28～30mm外形',1,'个',4,6,10,'规格方向，外形待选','声孔、支架、背腔与磁体高度','预算预留，未询价','检索：4欧 3W 28mm 30mm 喇叭 带线 尺寸'],
  ['P01','成品2S 7.4V锂电池包，含匹配保护',1,'包',40,55,70,'电池必需；具体电池待选','电池仓、压条、线缆和重心','预算预留，未询价；不另计包内保护板','候选：1000～1500mAh；核实放电能力、尺寸、质量、保护及均衡'],
  ['P02','与电池包配套的8.4V锂电充电器',1,'个',15,20,30,'依电池匹配，待选商品','决定机身充电接口形式','预算预留，未询价；外置配件','要求与2S标准锂电匹配，确认充电电流、极性与均衡方案'],
  ['P03','舵机路降压模块，约5V大电流输出',1,'块',18,28,40,'电源路线候选，待选商品','板体、散热、接线与固定空间','预算预留，未询价','候选目标：5V连续6A级；按8舵机实测峰值和温升选定'],
  ['P04','逻辑/音频路降压模块，5V约2A级',1,'块',8,12,18,'电源路线候选，待选商品','托板、散热与接线空间','预算预留，未询价','2S输入；与舵机分支供电并共地，实际余量待验证'],
  ['P05','带线面板充电插座',1,'个',3,5,8,'依充电器选定','开孔、面板厚度、螺母与插头空间','预算预留，未询价','优先与充电器成套匹配；不把USB调试口当充电口'],
  ['P06','电源控制开关',1,'个',3,5,8,'开关外形待选','开孔、拨杆行程与内侧固定','预算预留，未询价','优先控制负载开关；若直接切电源须满足实际直流电流'],
  ['P07','负载开关/保险、采样与滤波元件',1,'套',10,15,20,'原理图阶段定值','高件高度、发热、维修空间','预算预留，未询价；非器件级PCB BOM','包括必要MOSFET、保险、分压、电容等；具体料号待原理图'],
  ['P08','电源/信号线、排母及配套连接器',1,'套',12,18,25,'接口方向待定','插拔、弯曲、走线和扎线位置','预算预留，未询价','主电流接头按电流选；舵机标准3线接口；大电流不走开发板'],
  ['P09','定制载板/配电PCB首次打样',1,'批',20,30,50,'待设计','板框、孔位、接口边和最高元件','预算预留，非板厂报价；按一次小批订单','单机用1块；以5片小批作为询价口径，计整批现金，不计SMT'],
  ['M01','壳体与支架螺钉、螺母、垫柱',1,'套',10,15,20,'规格与数量待结构设计','通孔、螺母槽、柱体与工具空间','预算预留；舵机随包中心螺丝不重复计价','建议主体以M2螺钉/捕获螺母起步；舵机中心螺丝用随包件'],
  ['M02','软脚垫4只',1,'套',5,8,10,'外形待定','脚底嵌槽与支撑高度','预算预留，未询价','硅胶/橡胶脚垫或TPU件，采购与打印二选一计价'],
  ['M03','电池束带、缓冲/导音泡棉和扎带',1,'套',3,5,8,'依结构裁切','电池固定、导音与线束整理','预算预留，未询价','不可挤压软包电池；尺寸按所选电池和固定方式确定'],
  ['M04','整套壳体、腿及安装小件打印',1,'套',60,90,140,'分件计划，未出生产文件','全部外壳、关节、耳饰及安装件','预算预留，非商家报价；不按广告每克价折算','原色FDM及基础处理口径；奶油白/薄荷绿，精细喷漆另询价'],
  ['M05','屏幕样框、单腿与配合试样打印',1,'轮',10,20,30,'需尺寸后建模','校准间隙、紧固及单腿装配','预算预留；为额外试样，不与整套打印重复','优先小件试配，失败改图后再打印整套'],
  ['L01','多个供应商合计运费',1,'项',15,25,35,'待结算','无模型影响','预算预留；已包邮部分应扣除','与各件单价分开'],
  ['L02','补件与试制返工预留',1,'项',20,40,60,'预留','无固定模型尺寸','预算预留，不是已发生支出','不含购买打印机/焊接工具和长期语音服务费用'],
];
const dims = [
  ['D01','显示屏＋EC11整板','商品91×44；孔距84.5×37.5，孔Ø3','板厚、玻璃/发光区尺寸及偏置；旋钮/按键/排针总高','前盖、居中开窗、支架、机身深度','商品图；V1测量表','未提供','型号已选，详细尺寸缺失'],
  ['D02','屏幕平齐安装方式','V1玻璃后退约20.8；旋钮完整藏盖内','选择移置控件、换纯屏，或允许局部凸罩；核对高度链','决定前盖截面，不能靠移动假屏面解决','V1参数和用户平齐需求','未决定','需要先决定结构方式'],
  ['D03','8个MG90S本体','已选全金属齿轮180度；V1为占位','含安装耳尺寸、孔距孔径、轴中心/高度、线缆出口、质量','四腿安装座、关节位置与摆动范围','所选商家尺寸图/实物；官方仅作型号参考','未提供','商品已选，安装尺寸缺失'],
  ['D04','配套舵盘＋中心螺丝','主图有塑料舵盘和螺丝','舵盘厚度、孔位、花键配合、中心螺丝规格与工具空间','上/下腿连接，不能按通用圆盘硬画','所选MG90S配套实物','未提供','必须先有尺寸'],
  ['D05','内置电池包','用户确认首版带电池；建议研究2S成品包','含保护板/包膜外形、质量、线缆和插头、放电/充电参数','电池仓、机身内腔、底盖和整机重心','待选商品及尺寸图','未提供','必须先选具体电池'],
  ['D06','充电插座＋电源开关','充电器/插座需成套匹配；开关待选','开孔、面板夹持厚度、内侧尺寸、端子朝向和操作行程','后部可更换接口板和固定结构','待选商品图','未提供','开孔前必须确定'],
  ['D07','ESP32-S3主控板','N16R8方向；可参考微雪加焊排针款','具体板型长宽高、排针/排母、USB位置、插头空间、天线边界','可换托板与USB开孔','微雪官方页面及所选实物','未提供','托板孔位前确定'],
  ['D08','喇叭','4Ω3W方向；V1的Ø28×7仅占位','外框、厚度、磁体、孔位/压边、出线位置与所需背腔','声孔、支架、壳内背腔','待选商品图','未提供','声孔和固定座前确定'],
  ['D09','麦克风','I²S模块方向；具体板型未选','顶/底拾音孔方向、板体和声孔坐标、接线高度','收音孔、导音泡棉与麦克风座','待选商品图','未提供','收音孔前确定'],
  ['D10','PCA9685/功放/两路降压模块','芯片/接口方向已给，成品板未选','外形、孔位、高件、端子、散热和线束插拔','可更换托板、内腔和通风','待选成品板图；不要把芯片尺寸当板尺寸','未提供','可先预留，固定孔后定'],
  ['D11','自定义PCB','原理图和布线未开始','先共定板框、固定孔、接口方向、元件高度与禁布区','托板、机身内腔和外部接口','我们设计的机械约束','未设计','板框孔位需先定，布线可并行'],
  ['D12','紧固件＋软脚垫','紧固建议M2为起点；脚垫4只','螺钉头/长度、螺母外形、柱高、脚垫外形','可拆壳体、舵盘连接和脚底','供货尺寸与结构设计','未提供','加工孔之前定'],
  ['D13','腿长、关节轴向和承载','当前两关节仅姿态占位，含腿宽208','运动范围、有效力臂、整机质量/重心、舵机持续工作能力','腿、支架、避让、站姿','我们设计并由单腿/整机测试验证','未设计','不能照抄V1当运动机构'],
  ['D14','打印材料与公差','配色磨砂已定；V1壁厚2.4、间隙为试验值','材料、工艺、供应商公差；薄件厚度和孔配合试样','所有最终打印件，尤其关节和螺母槽','商家能力与试样','未确定','整套发布前确定'],
];
const parts = [
  ['S01','主壳',1,'奶油白，低光泽','前/底盖接口、舵机载荷路径','V1有外形，结构待细化'],
  ['S02','可拆前盖',1,'奶油白','有效开窗、屏幕平齐方式','需要重做前端高度关系'],
  ['S03','底盖/维修盖',1,'奶油白','电池取出、紧固和工具通路','V1有外形，锁止待设计'],
  ['S04','前脸薄荷装饰圈',1,'薄荷绿','可独立嵌件或着色，避免过薄','V1仅0.4mm深，需按工艺调整'],
  ['S05','屏幕固定支架',1,'内部色不限','91×44板与真实孔位，需排针避让','V1占位支架，待实测'],
  ['S06','短遮光圈/玻璃保护边',1,'深色或奶白内部','与平齐方案联动，不沿用20mm深井','重新设计'],
  ['S07','屏幕隔离垫柱',4,'内部色不限','真实板厚和安装高度，可并入支架','按实物定高，数量可合并'],
  ['S08','可更换电子托板',1,'内部色不限','主控、驱动和PCB板框孔位','V1有占位，孔位待定'],
  ['S09','耳框',2,'薄荷绿','底座可拆，避开声孔','V1有形状，紧固待细化'],
  ['S10','耳内片',2,'奶油白','可嵌入，按工艺确定厚度','V1厚0.7mm，待工艺调整'],
  ['S11','机身侧舵机安装座',4,'薄荷绿/内部结构色','MG90S安装耳、轴线、承载连接','V1仅占位，需新建'],
  ['S12','上腿/第二舵机承载件',4,'薄荷绿；结构材料待定','输出舵盘与第二舵机本体固定','需按MG90S与舵盘重画'],
  ['S13','下腿',4,'薄荷绿；结构材料待定','舵盘连接、限位、脚垫','需按舵盘与步态重画'],
  ['S14','关节装饰盖',8,'奶白/薄荷绿','旋转避让与中心螺丝可达','V1有外观，需调整'],
  ['S15','电池托架',1,'内部色不限','按成品电池外形、质量与出线设计','新增，等待电池型号'],
  ['S16','电池压条/束带座',1,'内部色不限','固定牢靠且不压迫电池','新增，随托架设计'],
  ['S17','喇叭支架/背腔件',1,'内部色不限','喇叭外框、磁体与声学空间','新增/与壳体整合待定'],
  ['S18','麦克风固定座',1,'内部色不限','拾音孔与泡棉导音对齐','新增，待麦克风板型'],
  ['S19','后部可更换接口板',1,'奶油白','充电、USB、开关的具体开孔','新增，等待连接器'],
  ['S20','线束固定夹',2,'内部色不限','弯曲/插拔空间、避免进入关节','建议起始数量，布局后调整'],
  ['S21','舵机局部装饰罩（可选）',8,'薄荷绿/奶油白','只遮外露侧面，留散热和摆动空间','可选外观件，运动校核后决定'],
];

const sum = index => Math.round(bom.reduce((v,r)=>v+r[2]*r[index],0)*100)/100;
const totals = { low_cny:sum(4), reference_cny:sum(5), high_cny:sum(6), screenshot_subtotal_cny:bom[0][2]*bom[0][5]+bom[1][2]*bom[1][5] };
const wb = Workbook.create();
const s = wb.worksheets.add('采购BOM');
const d = wb.worksheets.add('开孔前的尺寸');
const p = wb.worksheets.add('分件计划');
const ink='#25372F', mint='#DDE9DF', yellow='#FFF0CE';
function base(sheet,title,lastRow,lastCol,widths){
  sheet.showGridLines=false;
  sheet.getRange(`A1:${lastCol}${lastRow}`).format.font={name:'Arial',size:11,color:'#28312B'};
  sheet.getRange(`A1:${lastCol}${lastRow}`).format.verticalAlignment='center';
  sheet.getRange(`A1:${lastCol}${lastRow}`).format.rowHeight=24;
  sheet.getRange('A1:A100').format.columnWidth=3;
  for(const [col,width] of Object.entries(widths))sheet.getRange(`${col}1:${col}${lastRow}`).format.columnWidth=width;
  sheet.getRange('B2').values=[[title]];
  sheet.getRange('B2').format.font={name:'Arial',size:16,bold:true,color:ink};
  sheet.getRange(`B3:${lastCol}3`).format.borders={bottom:{style:'thin',color:'#9FB9A9'}};
  sheet.tabColor=ink;
}
function header(sheet,address){
  sheet.getRange(address).format={fill:ink,font:{name:'Arial',size:11,bold:true,color:'#FFFFFF'},rowHeight:30,horizontalAlignment:'center',verticalAlignment:'center',wrapText:true};
}
base(s,'奶油薄荷桌面助手 · 内置电池版 BOM',39,'L',{B:9,C:44,D:8,E:8,F:14,G:14,H:24,I:32,J:3,K:52,L:72});
s.getRange('B4').values=[['首轮现金预留（元）']];
s.getRange('D4').formulas=[['=G35']];
s.getRange('B5').values=[['屏幕＋舵机截图小计（元）']];
s.getRange('D5').formulas=[['=G11+G12']];
s.getRange('D4:D5').setNumberFormat('0.00');
s.getRange('B6').values=[['已确认首版内置电池。其余预算未询价，不能视作成交金额或预算已获批准。']];
s.getRange('B7').values=[['黄色 D/F 列可修改；F 列为参考预算单价。币种：人民币。']];
s.getRange('B8').values=[['包括一次 PCB 小批打样、整套打印和一轮试样；不含工具、精细喷漆及后续语音服务。']];
s.getRange('B10:I10').values=[['编号','器件 / 规格方向','数量','单位','参考单价','预算小计','当前选型状态','影响哪些模型']];
s.getRange('K10:L10').values=[['价格依据','资料 / 搜索方向']];
header(s,'B10:I10'); header(s,'K10:L10');
s.getRange('B11:I33').values=bom.map(r=>[r[0],r[1],r[2],r[3],r[5],null,r[7],r[8]]);
s.getRange('K11:L33').values=bom.map(r=>[r[9],r[10]]);
s.getRange('G11:G33').formulas=bom.map((r,i)=>{const n=i+11;return [`=IF(OR(D${n}="",F${n}=""),"待填写",D${n}*F${n})`];});
s.getRange('F35').values=[['现金预留合计']];
s.getRange('G35').formulas=[['=IF(COUNT(G11:G33)=ROWS(G11:G33),SUM(G11:G33),"待填写")']];
s.getRange('F35:I35').format.fill=mint;
s.getRange('F35:G35').format.font={name:'Arial',size:11,bold:true};
s.getRange('F11:G35').setNumberFormat('0.00');
s.getRange('D11:D33').setNumberFormat('0');
s.getRange('D11:D33').format.fill=yellow;
s.getRange('F11:F33').format.fill=yellow;
s.getRange('B11:I33').format.wrapText=true;
s.getRange('B11:I33').format.rowHeight=53;
s.getRange('K11:L33').format.wrapText=false;
s.dataValidations.add({range:'D11:D33',rule:{type:'whole',operator:'between',formula1:0,formula2:1000}});
s.getRange('G11:G33').conditionalFormats.add('containsText',{text:'待填写',format:{fill:'#FCE4DE',font:{color:'#A93226'}}});
s.freezePanes.freezeRows(10);
s.freezePanes.freezeColumns(3);

base(d,'开孔之前，需要哪些准确尺寸',22,'I',{B:8,C:26,D:44,E:58,F:38,G:48,H:32,I:28});
d.getRange('B4').values=[['型号、商品尺寸图和装配方式足够明确时可以开始细化；关键配合仍应通过小件试样确认。']];
d.getRange('B5').values=[['H 列留给实测值或收到的尺寸图。主控小板用可更换托板；外壳接口可用可更换接口板。']];
d.getRange('B7:I7').values=[['编号','器件 / 决定','已有依据（mm）','必须补齐的尺寸或决定','对应结构','依据','实测值 / 文件','当前状态']];
header(d,'B7:I7');
d.getRange('B8:I21').values=dims;
d.getRange('B8:I21').format.wrapText=true;
d.getRange('B8:I21').format.rowHeight=74;
d.getRange('H8:H21').format.fill=yellow;
d.freezePanes.freezeRows(7);

base(p,'外壳与安装配件分件计划',29,'G',{B:9,C:34,D:10,E:34,F:64,G:44});
p.getRange('B4').values=[['预计分件清单，不是已发布的 STL 数量；允许将垫柱/夹子等并入相邻零件。']];
p.getRange('B5').values=[['电池托架、实际舵机承载座和后接口板需新增；外购舵机、舵盘和螺丝不在打印件中。']];
p.getRange('B7:G7').values=[['编号','部件','预计数量','颜色 / 材料方向','定尺寸和连接的依据','目前状态']];
header(p,'B7:G7');
p.getRange('B8:G28').values=parts;
p.getRange('B8:G28').format.wrapText=true;
p.getRange('B8:G28').format.rowHeight=53;
p.getRange('D8:D28').setNumberFormat('0');
p.freezePanes.freezeRows(7);

wb.recalculate();
function assertTotal(expected){const n=s.getRange('G35').values[0][0];if(typeof n!=='number'||Math.abs(n-expected)>0.001)throw new Error(`BOM total mismatch ${n} vs ${expected}`);}
assertTotal(totals.reference_cny);
s.getRange('F12').values=[[11]]; wb.recalculate(); assertTotal(totals.reference_cny+8);
s.getRange('F12').values=[[10]];
s.getRange('F13').values=[[null]]; wb.recalculate();
if(s.getRange('G35').values[0][0]!=='待填写')throw new Error('Missing unit price was incorrectly treated as zero');
s.getRange('F13').values=[[45]]; wb.recalculate(); assertTotal(totals.reference_cny);
const errors=await wb.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A|#NUM!|#NULL!|#SPILL!|#CALC!',options:{useRegex:true,maxResults:30},summary:'BOM formula errors'});
await fs.writeFile(path.join(here,'formula-scan.ndjson'),errors.ndjson);
console.log((await wb.inspect({kind:'table',range:'采购BOM!F33:I35',include:'values,formulas',tableMaxRows:3,tableMaxCols:4,maxChars:1200})).ndjson);
for(const [sheetName,range,name] of [['采购BOM','B2:I17','bom-preview'],['开孔前的尺寸','B2:I14','dimensions-preview'],['分件计划','B2:G17','parts-preview']]){
  const rendered=await wb.render({sheetName,range,scale:1.3,format:'png'});
  await fs.writeFile(path.join(here,name+'.png'),new Uint8Array(await rendered.arrayBuffer()));
}
const bookFile=path.join(output,'桌面助手-BOM与建模尺寸.xlsx');
await (await SpreadsheetFile.exportXlsx(wb)).save(bookFile);

const manifest=JSON.parse(await fs.readFile(path.join(root,'mechanical-design/assembly-v1/manifest-sha256.json'),'utf8'));
const mismatches=[];
for(const [file,hash] of Object.entries(manifest)){
  const current=crypto.createHash('sha256').update(await fs.readFile(path.join(root,'mechanical-design/assembly-v1',file))).digest('hex');
  if(current!==hash)mismatches.push(file);
}
const audit={date:'2026-09-07',checked_manifest_entries:Object.keys(manifest).length,mismatches,verification:'file integrity against existing manifest; no new Blender geometry or motion validation',blend_sha256:manifest['desktop-assistant-assembly-v1.blend'],render_count:8,print_release:false};
await fs.writeFile(path.join(here,'assembly-v1-inspection.json'),JSON.stringify(audit,null,2)+'\n');
const data={date:'2026-09-07',scope:'first prototype with internal battery, PCB small batch and print trials',currency:'CNY',price_status:'only display and servos have user screenshot prices; all other unit budgets are planning allowances',power:{internal_battery:'user_confirmed',candidate:'2S 7.4V protected standard lithium pack, matching 8.4V charger, separate regulated logic and servo branches',specific_skus_selected:false},totals,columns:['id','item','quantity','unit','low_unit_budget','reference_unit_budget','high_unit_budget','selection_status','mechanical_dependency','price_evidence','source_or_search'],bom,dimensions:dims,planned_print_parts:parts,workbook:path.relative(root,bookFile)};
await fs.writeFile(path.join(here,'bom-data.json'),JSON.stringify(data,null,2)+'\n');
const rows=bom.map(r=>`| ${r[0]} | ${r[1]} | ${r[2]} ${r[3]} | ${r[5].toFixed(2)} | ${(r[2]*r[5]).toFixed(2)} | ${r[7]} |`).join('\n');
const dimRows=dims.map(r=>`| ${r[1]} | ${r[3]} | ${r[4]} |`).join('\n');
const partRows=parts.map(r=>`| ${r[0]} | ${r[1]} | ${r[2]} | ${r[5]} |`).join('\n');
const note=`# 内置电池版：整机 BOM 与建模准备\n\n日期：2026-09-07。用户已确认第一版内置电池并预留充电接口。本次给出采购与结构设计用的模块级整机 BOM；定制 PCB 的芯片、阻容、连接器逐项料号仍需在原理图阶段建立。\n\n[可编辑 Excel](../../${path.relative(root,bookFile)}) 包含采购 BOM、开孔尺寸待办及分件计划。\n\n## 已恢复的交付状态\n\n读取了根 README、assembly-v1 的说明、参数、组件和测量表，对照查看 V1 实际渲染与已选概念图。现有 manifest 的 **${audit.checked_manifest_entries} 个文件全部哈希一致**，八张渲染仍在；没有覆盖旧 Blender 文件。旧报告记载的 25 项限定检查属于上次交付，本次没有重新声称完成新的运动或制造验证。聊天记录缺失原因不能由这些文件确定。\n\nV1 主体约118×84.6×76 mm，含腿耳的静态范围约208×106×122.5 mm；显示玻璃后退约20.8 mm。主控等是占位，P010 舵机连接区未完成；31个打印候选对象不等于31个可直接交商家的制造件。新增电池后须重新布置并评估重量与重心。\n\n## 舵机决定\n\n选 **MG90S舵机（全金属齿轮）180度，8个，每腿2个**。用户此前图二该SKU截图10元/个，合计80元；最新综合商品图只显示5.8元起，不能将起价当MG90S价格。\n\n对照SG90塑齿轮款，MG90S的金属齿轮方向更符合承载关节的试制用途。这个推荐不是整机承载已经验证；两者原厂资料均列4.8V下约1.8kgf·cm堵转扭矩，不能仅看MG型号便认定力矩更大，也不能把堵转值当持续能力。所选商家未证实与原厂同版，孔位、质量和电气参数须看该店尺寸图和实物。[MG90S官方资料](${refs.mg})、[SG90官方资料](${refs.sg})。\n\n蓝色只是SG90外壳/旧占位模型的外观，不作为承载选型条件。保持奶油白＋薄荷绿，通过局部装饰罩或支架遮挡黑色外露面；装饰件避开输出轴、螺丝、线缆和散热。舵机购买成品，腿与支架由我们设计；优先用所附舵盘适配轴，不凭照片直接打印花键。\n\n## 采购 BOM 与金额口径\n\n**参考现金预留 ${totals.reference_cny.toFixed(2)} 元**；按各项低/高预算输入组合，敏感范围为 ${totals.low_cny.toFixed(2)}～${totals.high_cny.toFixed(2)} 元。这个范围是规划假设，不是已核实市场报价、承诺价格或新的获批预算。\n\n已有截图价格的屏幕和舵机小计为 **${totals.screenshot_subtotal_cny.toFixed(2)} 元**。其余均为明确标注的预算预留，尤其电池电源、PCB打样和打印必须询价。将商家广告的每克单价直接当整套打印费用会漏掉最低起做价、支撑、后处理和运费。本轮不执行采购。\n\n| 编号 | 部件 / 规格方向 | 数量 | 参考单价（元） | 小计（元） | 状态 |\n|---|---|---:|---:|---:|---|\n${rows}\n| | **现金预留合计** | | | **${totals.reference_cny.toFixed(2)}** | |\n\n- PCB行计首次小批打样整单现金，不把5片中使用1片简单按五分之一计费用；元件和连接器已在模块/辅料行中，避免重复。没有计SMT代贴。\n- 电池行含成品包内保护，不再次计同一块保护板；是否包含均衡及与充电器配套的方式要核实。保护板不等于充电器。\n- 打印整套与第一轮小试样分别计价；精细喷漆、工具、更多返工和持续语音服务不在此口径。\n- 2个舵机的单腿先行试样是8个总数量中的一部分，不应再增加到10个。\n\n## 电池与接口布局方向\n\n本轮按成品2S标准7.4V锂电池包＋匹配8.4V充电器＋降压供电研究，容量1000～1500mAh只作为首批检索方向。容量不能代替放电能力，续航、重量和最终体积均未验证。电池包、充电器、保护/均衡方式和接头须作为一套确认。具体商品未选定，不冻结电池仓尺寸。\n\n两路降压分别服务舵机和主控/音频并共地；2S电池不得直接接到这些低压模块。舵机支路先以约5V、连续6A级作为选型目标，逻辑/音频约5V2A级；两项不是已测足够的结论，电池包和保护电路也要匹配实测峰值。配电载板承担连接和保护，PCA9685只提供PWM信号，不能将其芯片输出当作电机电源。[PCA9685资料](${refs.pwm})。\n\n首轮布局按关机充电考虑，不默认支持边充边运动。可用配套充电插座；若要Type-C充电，必须另选支持该2S电池的完整充电电路及输入方案后再定孔，主控USB调试口不会自动变成电池充电口。\n\n主控可优先选有完整资料的ESP32-S3 N16R8已焊排针板；微雪有N16R8-M款和单Type-C接口，板型仍需实际选择，官网本轮未读到人民币数值。[微雪型号页面](${refs.esp})。语音方向为I²S数字麦克风＋MAX98357A＋4Ω3W小喇叭；MAX98357A使用I²S且不需MCLK，具体商品模块外形、GPIO分配、供电和并发功能仍需验证。[MAX98357A资料](${refs.amp})。\n\n## 开孔前必须确定的配件\n\n不是必须先把所有东西买齐，但至少要有可靠的具体商品尺寸图、接头状态和装配方式。最优先是屏幕/控件、舵机与舵盘、电池、穿壳接口、喇叭和麦克风。\n\n| 器件 / 决定 | 要补齐什么 | 决定哪些结构 |\n|---|---|---|\n${dimRows}\n\n主控、PWM、功放和降压小板放在可更换托板上，可以先研究包络与安装方向；最终固定孔仍应等待具体板型。后部充电/USB/开关做可更换接口板可以减少后续换件改主壳。PCB不必先布完线：先共定板框、安装孔、连接器位置、高度和禁布区，再让电路与结构并行。\n\n## 平齐屏幕必须先解决的结构决定\n\n当前完整EC11突出于LCD玻璃之前，所以“保持完整控件在同一平板前盖后面”与“LCD玻璃和整个前盖齐平”不能直接同时满足。只摘旋钮帽未必足够，轴和按键仍可能顶住前盖。\n\n若坚持完全平的前脸，研究将EC11及独立按键移到顶/后部，或采用不带旋钮的同尺寸屏模块；前者要确认该商品焊接和移置条件，后者会改变屏幕采购项及尺寸。若保留完整模块不改焊，则可评估局部凸罩，但前脸不会处处同一平面。这三个选择尚未获用户定稿，本轮没有拆改硬件或更换已选屏幕。\n\n因此，前盖可以继续研究形状和分件，但现在不能将70×51开口、59×42.5商品标注或约20.8mm深井当作最终制造尺寸。商品59×42.5与2.4英寸的口径不一致，真实发光区、玻璃边框与相对PCB的坐标要分开测量。\n\n## 全部外壳与安装件的计划\n\n下表为下一版分件计划，数量可以在结构合并时修订。外购舵机/舵盘不打印；电池托架、真实承载座、接口板等需要新增。\n\n| 编号 | 部件 | 预计数量 | 当前状态 |\n|---|---|---:|---|\n${partRows}\n\n今天的工作顺序：先补齐上述关键硬件资料和屏幕前端决定，建立真实元件尺寸与安装基准；接着排布电池与板卡、确定重心和关节轴向，细化分件和孔位；先输出屏幕样框、单腿、接口板配合试样，再完成全套装配和打印检查。工艺公差与实物承载尚未确认时，交付应标成试配版，不能只凭渲染宣称兼容。\n`;
await fs.writeFile(path.join(here,'README.md'),note+'\n价格截图已保存在项目中：[屏幕选中价32.40元](../reference/screen-2p4-ec11-price-32p40.png)、[MG90S选中价10元](../reference/servo-option-2-mg90s-180-selected.png)、[本轮综合商品页5.8元起](../reference/servo-combined-listing-start-price.png)。\n');
console.log(JSON.stringify({workbook:bookFile,totals,manifest:audit,checks:['formulas recalculated','8-servo price change propagated','blank price blocked total','all 3 sheets rendered']},null,2));
