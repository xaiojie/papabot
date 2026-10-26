import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import crypto from 'node:crypto';
import { Workbook, SpreadsheetFile } from '@oai/artifact-tool';

const here = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(here, '../..');
const output = path.join(here, 'exports');
await fs.mkdir(output, { recursive: true });
const refs = {
  mg: 'https://towerpro.com.tw/product/mg90s-3/',
  sg: 'https://towerpro.com.tw/product/sg90-analog/',
  esp: 'https://www.waveshare.net/shop/ESP32-S3-DEV-KIT-N16R8.htm',
  pwm: 'https://www.nxp.com/docs/en/data-sheet/PCA9685.pdf',
  amp: 'https://www.analog.com/en/products/max98357a.html',
};
// Unit budgets are planning inputs. E01, E02 and P02 have supplier screenshot prices.
// Columns: ID, item, qty, unit, low, base, high, status, mechanical dependency, price evidence, source/search.
const bom = [
  ['E01','途格斯 2.4寸 ST7789 TFT＋EC11',1,'块',32.4,32.4,32.4,'已选，待实测','开窗、支架、前盖深度','用户此前选中 SKU 截图 ¥32.4；非实时价','hardware-selection/reference/screen-2p4-ec11-price-32p40.png'],
  ['E02','MG90S 全金属齿轮 180度，带舵盘螺丝',8,'个',10,10,10,'本轮选定，待实测','安装耳、输出轴、舵盘、腿部承载','用户图二选中 SKU 截图 ¥10；非实时价',refs.mg],
  ['E03','ESP32-S3 N16R8 已焊排针开发板',1,'块',38,45,55,'推荐型号，板型待定','USB孔、托板、排母高度与天线空间','预算预留；官网有型号，未读到人民币价',refs.esp+'（参考 N16R8-M）'],
  ['E04','PCA9685 16路 PWM 成品模块',1,'块',8,12,15,'推荐模块，待选商品','托板、排针与舵机插头空间','预算预留，未询价',refs.pwm],
  ['E05','I²S 数字麦克风模块，INMP441 类',1,'块',6,8,12,'推荐接口，待选商品','声孔方向、密封导音、安装卡座','预算预留，未询价','检索：INMP441 I2S 麦克风模块 已焊排针 尺寸图'],
  ['E06','MAX98357A I²S 单声道功放模块',1,'块',4,6,10,'推荐模块，待选商品','托板、接线端子空间','预算预留，未询价',refs.amp],
  ['E07','4Ω 3W 小喇叭，优先约28～30mm外形',1,'个',4,6,10,'规格方向，外形待选','声孔、支架、背腔与磁体高度','预算预留，未询价','检索：4欧 3W 28mm 30mm 喇叭 带线 尺寸'],
  ['P01','定制2S 7.4V 1000mAh电池包＋保护均衡',1,'包',60,80,120,'规格选定；待商家确认可做','电池仓、压条、插头和重心','80元为定制预算，未报价；含保护均衡及已焊线接头','定制询价入口：https://item.taobao.com/item.htm?id=966262592635；持续10A、允许充电至少1A、XT30；75×40×20仅包络目标'],
  ['P02','TELESKY 2S 8.4V Type-C充电板 MK021163',1,'块',14.13,14.13,14.13,'选TYPE-C款；充电电流待核','后接口板、28×17板体与插拔空间','用户图五TYPE-C款14.13元；非结算价，不含改电流服务','https://detail.tmall.com/item.htm?id=709098048793&skuId=5148568746386；目标0.4～0.5A，实际限流须与电池允许值匹配'],
  ['P03','舵机路降压模块，约5V大电流输出',1,'块',18,28,40,'电源路线候选，待选商品','板体、散热、接线与固定空间','预算预留，未询价','候选目标：5V连续6A级；按8舵机实测峰值和温升选定'],
  ['P04','逻辑/音频路降压模块，5V约2A级',1,'块',8,12,18,'电源路线候选，待选商品','托板、散热与接线空间','预算预留，未询价','2S输入；与舵机分支供电并共地，实际余量待验证'],
  ['P05','USB-A转Type-C充电线，支持5V2A',1,'条',3,5,8,'选接口方向；线材待购','外部插头避让；充电座已在P02上','预算预留；替代原面板充电插座，避免重复计价','与P10及P02配套；现有合适线材可将数量改0'],
  ['P06','电源控制开关',1,'个',3,5,8,'开关外形待选','开孔、拨杆行程与内侧固定','预算预留，未询价','优先控制负载开关；若直接切电源须满足实际直流电流'],
  ['P07','负载开关/保险、采样与滤波元件',1,'套',10,15,20,'原理图阶段定值','高件高度、发热、维修空间','预算预留，未询价；非器件级PCB BOM','包括必要MOSFET、保险、分压、电容等；具体料号待原理图'],
  ['P08','电源/信号线、排母及配套连接器',1,'套',12,18,25,'接口方向待定','插拔、弯曲、走线和扎线位置','预算预留，未询价','主电流接头按电流选；舵机标准3线接口；大电流不走开发板'],
  ['P09','定制载板/配电PCB首次打样',1,'批',20,30,50,'待设计','板框、孔位、接口边和最高元件','预算预留，非板厂报价；按一次小批订单','单机用1块；以5片小批作为询价口径，计整批现金，不计SMT'],
  ['P10','5V 2A USB-A成品电源适配器',1,'个',15,20,30,'输入规格选定；商品待购','外置，无机身开孔','预算预留；已有合适5V电源可将数量改0','用于Type-C充电板输入；不当作八舵机工作电源'],
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
  ['D02','屏幕平齐安装方式','上轮建议EC11/按键移到后部可拆面板','核实拆焊焊点、屏与PCB高度；玻璃内缩0.5～1仅设计目标','前盖、显示支架、后控件板；原PCB不裁切','用户平齐需求；移位方案尚待硬件核实','建议记录：power-selection-2s.md','建议方案，未改硬件或CAD'],
  ['D03','8个MG90S本体','已选全金属齿轮180度；收到黑色商品图','含安装耳尺寸、孔距孔径、轴中心/高度、线缆出口、质量','四腿安装座、关节位置与摆动范围','商家无尺寸图；官方仅作可调整占位参考','servo-mg90s-product-photo.png','外观图已有；安装尺寸待实测'],
  ['D04','配套舵盘＋中心螺丝','照片有单臂、双臂和十字塑料舵盘','舵盘厚度、孔位、花键配合、中心螺丝规格与工具空间','上/下腿连接；复用随包舵盘，不打印花键','所选MG90S配套实物；照片不提供精确尺寸','servo-mg90s-product-photo.png','外观可建；配合尺寸待实测'],
  ['D05','内置电池包','定制2S1000mAh，持续10A，包内保护均衡','商家确认可做、真实长宽厚/质量、插头位置与极性、充电上限','电池仓、底盖、重心；75×40×20只是询价目标','图二定制入口；未获得该规格供货承诺','定制要求：power-selection-2s.md','规格已写；供货和尺寸未冻结'],
  ['D06','Type-C充电板＋电源开关','TELESKY TYPE-C款；图示板体28×17','板厚/最高件、孔径孔距、USB口坐标、允许面板厚度；开关外形','后部可更换接口板；USB插头和线束避让','图五MK021163；人工尺寸误差0.5～1','charger-telesky-2s-typec.png','板型已选；精确开孔待实测'],
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
  ['S15','电池托架',1,'内部色不限','定制2S1000mAh；按含保护板包膜的成品尺寸','规格已写，实物尺寸与布局待定'],
  ['S16','电池压条/束带座',1,'内部色不限','固定牢靠且不压迫电池','新增，随托架设计'],
  ['S17','喇叭支架/背腔件',1,'内部色不限','喇叭外框、磁体与声学空间','新增/与壳体整合待定'],
  ['S18','麦克风固定座',1,'内部色不限','拾音孔与泡棉导音对齐','新增，待麦克风板型'],
  ['S19','后部可更换接口与控件板',1,'奶油白','P02充电口、调试USB/开关；预研EC11与按键移位','充电板型已选；孔位和控件移位待核'],
  ['S20','线束固定夹',2,'内部色不限','弯曲/插拔空间、避免进入关节','建议起始数量，布局后调整'],
  ['S21','舵机局部装饰罩（可选）',8,'薄荷绿/奶油白','只遮外露侧面，留散热和摆动空间','可选外观件，运动校核后决定'],
];

const sum = index => Math.round(bom.reduce((v,r)=>v+r[2]*r[index],0)*100)/100;
const totals = { low_cny:sum(4), reference_cny:sum(5), high_cny:sum(6), screenshot_subtotal_cny:Math.round(bom.filter(r=>['E01','E02','P02'].includes(r[0])).reduce((v,r)=>v+r[2]*r[5],0)*100)/100 };
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
s.getRange('D4').formulas=[['=G36']];
s.getRange('B5').values=[['已有截图价小计（元）']];
s.getRange('D5').formulas=[['=G11+G12+G19']];
s.getRange('D4:D5').setNumberFormat('0.00');
s.getRange('B6').values=[['定制2S电池规格及Type-C板型已选。电池未报价，充电电流待核；金额为现金预留。']];
s.getRange('B7').values=[['黄色 D/F 列可修改；F 列为参考预算单价。币种：人民币。']];
s.getRange('B8').values=[['包括一次 PCB 小批打样、整套打印和一轮试样；不含工具、精细喷漆及后续语音服务。']];
s.getRange('B10:I10').values=[['编号','器件 / 规格方向','数量','单位','参考单价','预算小计','当前选型状态','影响哪些模型']];
s.getRange('K10:L10').values=[['价格依据','资料 / 搜索方向']];
header(s,'B10:I10'); header(s,'K10:L10');
s.getRange('B11:I34').values=bom.map(r=>[r[0],r[1],r[2],r[3],r[5],null,r[7],r[8]]);
s.getRange('K11:L34').values=bom.map(r=>[r[9],r[10]]);
s.getRange('G11:G34').formulas=bom.map((r,i)=>{const n=i+11;return [`=IF(AND(ISNUMBER(D${n}),ISNUMBER(F${n})),D${n}*F${n},"待填写")`];});
s.getRange('F36').values=[['现金预留合计']];
s.getRange('G36').formulas=[['=IF(COUNT(G11:G34)=ROWS(G11:G34),SUM(G11:G34),"待填写")']];
s.getRange('F36:I36').format.fill=mint;
s.getRange('F36:G36').format.font={name:'Arial',size:11,bold:true};
s.getRange('F11:G36').setNumberFormat('0.00');
s.getRange('D11:D34').setNumberFormat('0');
s.getRange('D11:D34').format.fill=yellow;
s.getRange('F11:F34').format.fill=yellow;
s.getRange('B11:I34').format.wrapText=true;
s.getRange('B11:I34').format.rowHeight=53;
s.getRange('K11:L34').format.wrapText=false;
s.getRange('K18:L19').format.wrapText=true;
s.getRange('K18:L19').format.font.size=11;
s.getRange('B18:L19').format.rowHeight=80;
s.dataValidations.add({range:'D11:D34',rule:{type:'whole',operator:'between',formula1:0,formula2:1000}});
s.getRange('G11:G34').conditionalFormats.add('containsText',{text:'待填写',format:{fill:'#FCE4DE',font:{color:'#A93226'}}});
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
function assertTotal(expected){const n=s.getRange('G36').values[0][0];if(typeof n!=='number'||Math.abs(n-expected)>0.001)throw new Error(`BOM total mismatch ${n} vs ${expected}`);}
assertTotal(totals.reference_cny);
s.getRange('F12').values=[[11]]; wb.recalculate(); assertTotal(totals.reference_cny+8);
s.getRange('F12').values=[[10]];
s.getRange('F13').values=[[null]]; wb.recalculate();
if(s.getRange('G36').values[0][0]!=='待填写')throw new Error('Missing unit price was incorrectly treated as zero');
s.getRange('F13').values=[[45]]; wb.recalculate(); assertTotal(totals.reference_cny);
s.getRange('F18').values=[[null]]; wb.recalculate();
if(s.getRange('G36').values[0][0]!=='待填写')throw new Error('Missing battery price was hidden');
s.getRange('F18').values=[[80]];
s.getRange('D27').values=[[0]]; wb.recalculate(); assertTotal(totals.reference_cny-20);
s.getRange('D27').values=[[1]]; wb.recalculate(); assertTotal(totals.reference_cny);
if(Math.abs(s.getRange('D5').values[0][0]-totals.screenshot_subtotal_cny)>0.001)throw new Error('Screenshot subtotal mismatch');
const errors=await wb.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A|#NUM!|#NULL!|#SPILL!|#CALC!',options:{useRegex:true,maxResults:30},summary:'BOM formula errors'});
await fs.writeFile(path.join(here,'formula-scan.ndjson'),errors.ndjson);
console.log((await wb.inspect({kind:'table',range:'采购BOM!F34:I36',include:'values,formulas',tableMaxRows:3,tableMaxCols:4,maxChars:1200})).ndjson);
for(const [sheetName,range,name] of [['采购BOM','B2:I19','bom-preview'],['采购BOM','B18:I27','power-preview'],['开孔前的尺寸','B8:I14','dimensions-preview'],['分件计划','B21:G28','parts-preview']]){
  const rendered=await wb.render({sheetName,range,scale:1.3,format:'png'});
  await fs.writeFile(path.join(here,name+'.png'),new Uint8Array(await rendered.arrayBuffer()));
}
const bookFile=path.join(output,'桌面助手-BOM与建模尺寸.xlsx');
await (await SpreadsheetFile.exportXlsx(wb)).save(bookFile);

const manifest=JSON.parse(await fs.readFile(path.join(root,'mechanical-design/assembly-v1/manifest-sha256.json'),'utf8'));
const mismatches=[];
const observedHashes={};
for(const [file,hash] of Object.entries(manifest)){
  const current=crypto.createHash('sha256').update(await fs.readFile(path.join(root,'mechanical-design/assembly-v1',file))).digest('hex');
  observedHashes[file]=current;
  if(current!==hash)mismatches.push(file);
}
const audit={date:'2026-09-07',checked_manifest_entries:Object.keys(manifest).length,matched_entries:Object.keys(manifest).length-mismatches.length,mismatches,verification:'file integrity against existing manifest; no new Blender geometry or motion validation',blend_sha256:observedHashes['desktop-assistant-assembly-v1.blend'],expected_blend_sha256:manifest['desktop-assistant-assembly-v1.blend'],render_count:8,print_release:false};
await fs.writeFile(path.join(here,'assembly-v1-inspection.json'),JSON.stringify(audit,null,2)+'\n');
const powerSelection=JSON.parse(await fs.readFile(path.join(root,'hardware-selection/power-selection-2s.json'),'utf8'));
const data={date:'2026-09-07',scope:'first prototype with internal battery, PCB small batch and print trials',currency:'CNY',price_status:'E01 E02 P02 have user screenshot prices; custom battery has no quote; other prices are planning allowances',power:{internal_battery:'user_confirmed',candidate:'custom protected balanced 2S 7.4V 1000mAh pack with TELESKY MK021163 TYPE-C 8.4V charger and separate regulated power branches',battery_custom_specification_selected:true,charger_sku_selected:true,specific_skus_selected:false,supplier_can_make_confirmed:false,charge_current_verified:false,record:powerSelection.record},totals,columns:['id','item','quantity','unit','low_unit_budget','reference_unit_budget','high_unit_budget','selection_status','mechanical_dependency','price_evidence','source_or_search'],bom,dimensions:dims,planned_print_parts:parts,workbook:path.relative(root,bookFile)};
await fs.writeFile(path.join(here,'bom-data.json'),JSON.stringify(data,null,2)+'\n');
const rows=bom.map(r=>'| '+[r[0],r[1],r[2]+' '+r[3],r[5].toFixed(2),(r[2]*r[5]).toFixed(2),r[7]].join(' | ')+' |').join('\n');
const dimRows=dims.map(r=>'| '+[r[1],r[3],r[4]].join(' | ')+' |').join('\n');
const partRows=parts.map(r=>'| '+[r[0],r[1],r[2],r[5]].join(' | ')+' |').join('\n');
const note=[
'# 内置电池版：整机 BOM 与建模准备',
'日期：2026-09-07。本轮更新电池定制要求、Type-C充电板、输入配件及舵机商品图。保留此前屏幕和奶油薄荷配色。尚未制作PCB、固件或正式打印文件。',
'[可编辑 Excel](../../'+path.relative(root,bookFile)+') 包含采购BOM、开孔尺寸待办及分件计划。[电池与充电选型、给商家的定制文字](../power-selection-2s.md)。',
'## 当前选择和数量',
'- 舵机：MG90S 全金属齿轮180度，**8个**，每腿2个。随包舵盘、中心螺丝一起采购；单腿试样取其中2个，不额外增加到10个。',
'- 电池：**定制成品2S 7.4V 1000mAh，1包**。要求持续10A、允许充电至少1A、包内每节保护和被动均衡、共口P+/P-及XT30配对接头。定制需求已写，但商家可做性、交期、价格、真实尺寸与重量还没有确认。',
'- 充电板：**TELESKY MK021163，TYPE-C接口，2S8.4V，1块**。用户图五价14.13元、标注板体28×17mm。默认恒流电流和厚度、孔位仍未核实；先以0.4～0.5A充电作为设计目标，实际值必须匹配电池厂家允许范围。',
'- 输入配件：5V2A USB-A充电头1个、A转Type-C线1条。原面板充电插座预算改为线材，充电座已在P02板上；不再同时计旧8.4V外置充电器。已有合适配件可把数量改0。',
'## 金额口径',
'**参考现金预留 '+totals.reference_cny.toFixed(2)+' 元**；各行低/高预留组合为 '+totals.low_cny.toFixed(2)+'～'+totals.high_cny.toFixed(2)+' 元，均不是商家总报价或获批新预算。',
'屏幕32.40元＋8个舵机80元＋充电板14.13元，已有用户截图价小计 **'+totals.screenshot_subtotal_cny.toFixed(2)+'元**。这些价格未验证结算价。定制电池80元只是预算，不使用普通对讲机电池14.70元或单节裸电芯11.80元作为定制包价格。',
'相较上一版580.40元，定制电池预留由55改80（+25），外置充电器20元改为板14.13元（-5.87），补5V输入适配器20元，总增39.13元。线材替代旧插座仍为5元。充电板改电流服务若收费需按报价更新。',
'| 编号 | 部件 / 规格 | 数量 | 参考单价（元） | 小计（元） | 当前状态 |\n|---|---|---:|---:|---:|---|\n'+rows+'\n| | **现金预留合计** | | | **'+totals.reference_cny.toFixed(2)+'** | |',
'PCB行计首次小批打样整单现金，以5片小批询价但单机只用1片。不计SMT，不把整批现金按五分之一摊去。模块、辅料与包内保护均衡不重复计价。整套打印及第一轮样片分别计；精细喷漆、购买工具、更多返工和持续语音服务未包含。',
'## 电源匹配与接口',
'电池连续10A、舵机降压5V6A级、逻辑降压5V2A级均为选型目标，尚未通过实物峰值和温升验证。容量与C数不能取代整包电芯、保护、接头和线材的电流核实。',
'首版关机充电。Type-C板给电池保护后充电口供电，电池经负载开关和两路降压给整机供电并共地。2S电压不直接送MG90S或ESP。充电板不承担八个舵机工作电源；PCA9685只提供PWM信号。',
'充电、每节电芯保护、均衡、负载降压分别核对。商品写“5V2A”是输入参数，不代表8.4V2A充电。图五没有给出默认恒流数值，本轮没有把它编成已知参数。电池定制单要求包内每节保护及均衡；商家未确认前不宣称组合已验证。',
'充电板可用28×17mm商品标注做初步包络；高度、USB口坐标、孔径孔距未给出。电池75×40×20mm、80g是询价目标，不是已知尺寸或已冻结仓体。电池和热源分开，插拔力由接口板支架承担。',
'## V1交付与屏幕前端',
'现有manifest **'+audit.matched_entries+'/'+audit.checked_manifest_entries+'项哈希一致**。不一致文件：'+(audit.mismatches.join('、')||'无')+'。保留当前Blender文件与八张历史渲染，未恢复旧模型。本轮只更新采购和尺寸资料；原25项限定检查属于上次交付，没有新的运动或制造通过结论。',
'V1主体约118×84.6×76mm，含腿耳约208×106×122.5mm，显示玻璃后退约20.8mm。旧八个蓝色舵机为占位，P010连接区未完成，31个打印候选对象不等于31个可交商家生产件。',
'屏幕按上轮建议继续研究：保留91×44mm原PCB，EC11和独立按键移至后部可拆面板，前方只露居中屏幕，玻璃内缩0.5～1mm作为目标。拆焊和实际高度链未核实，尚未动硬件或CAD；仅摘旋钮帽未必能消除突出。商品59×42.5标注、V1的70×51开窗均不能直接当有效发光区和最终加工尺寸。',
'## 无舵机尺寸图时的工作方式',
'已收到MG90S黑色机身与塑料舵盘商品照片，可开始外观重建和可调整占位。商家没有工程图，因此安装耳孔、轴中心、舵盘厚度和螺钉配合必须在收货后实测；不从透视商品照反推精确孔距，也不按照片打印花键。先做可替换舵机托架，再用2个舵机验证单腿承载与运动。',
'## 开孔尺寸待办',
'| 器件 / 决定 | 要补齐什么 | 决定哪些结构 |\n|---|---|---|\n'+dimRows,
'主控、功放、PCA9685和降压小板使用可更换托板，后部使用可更换接口板。先共定自制PCB板框、孔位、接口边和高度，再推进原理图与布线；外壳开孔仍以选定成品板与连接器的实际尺寸为准。',
'## 分件计划',
'下表是计划，允许将夹子/垫柱并入相邻部件；不等于已生成STL数量。外购舵机、配套舵盘和螺丝不打印。',
'| 编号 | 部件 | 预计数量 | 当前状态 |\n|---|---|---:|---|\n'+partRows,
'## 资料来源',
'[屏幕截图](../reference/screen-2p4-ec11-price-32p40.png)、[MG90S选中价](../reference/servo-option-2-mg90s-180-selected.png)、[本轮舵机商品图](../reference/servo-mg90s-product-photo.png)、[充电板图五](../reference/charger-telesky-2s-typec.png)、[定制入口图二](../reference/battery-custom-inquiry-7p4.png)。其他候选截图及详细比较见电源选型记录。',
'原厂型号参考：[MG90S]('+refs.mg+')、[ESP32-S3 N16R8]('+refs.esp+')、[PCA9685]('+refs.pwm+')、[MAX98357A]('+refs.amp+')。厂商芯片/型号资料不等于当前淘宝模块已经电气或机械验证。',
'本轮商品页读取被Computer Use自动访问审查拒绝，未绕过限制；价格来自用户截图，没有声称读到最新SKU详情。'
].join('\n\n');
await fs.writeFile(path.join(here,'README.md'),note+'\n');
console.log(JSON.stringify({workbook:bookFile,totals,manifest:audit,checks:['formula recalculation','8-servo price change propagated','blank component and battery prices blocked total','existing adapter quantity zero deducted 20','screenshot subtotal matches 126.53','changed views rendered']},null,2));
