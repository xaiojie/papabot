import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { Workbook, SpreadsheetFile } from '@oai/artifact-tool';

const out = path.join(path.dirname(fileURLToPath(import.meta.url)), 'exports');
const headers = ['原型号', '原品牌', '原封装', '原参数', '原C编码', '单套用量', '备损量'];
const rows = [
  ['LCKFB-ESP32S3R8N8','立创开发板','开发板成品','ESP32-S3；8MB Flash+8MB PSRAM；USB-C；含排针，需自行焊接','C20626143',1,0],
  ['PCA9685 16路舵机驱动模块','','成品模块','I2C；3.3V逻辑；舵机V+独立5V；带排针与接线端子；不要裸芯片','',1,0],
  ['INMP441 I2S数字麦克风模块','','成品模块','3.3V供电；I2S数字输出；已焊器件的小板；不要裸MEMS','',1,0],
  ['MAX98357A I2S数字功放模块','','成品模块','5V供电；单声道；配4欧姆3W喇叭；不要裸芯片','',1,0],
  ['4欧姆3W扬声器','','带线成品','圆形直径约28至30mm；厚度及固定方式待最终商品确认','',1,0],
  ['2S 7.4V 1000mAh锂电池包','','带保护均衡成品包','满电8.4V；持续放电>=10A；允许充电>=1A；每节保护及均衡；XT30；75x40x20mm为目标上限非已知尺寸；禁止匹配裸电芯','',1,0],
  ['Type-C 2S 8.4V锂电池充电模块','','成品模块','5V输入；2串CC/CV；充电电流0.4至0.5A目标且需核实；接电池保护后端；关机充电；不要3串12.6V款','',1,0],
  ['DC-DC同步降压模块 5V 6A','','成品模块','输入覆盖6至8.4V；5V持续6A目标并需验证温升；舵机专用；不要仅峰值6A或裸芯片','',1,0],
  ['DC-DC降压模块 5V 2A','','成品模块','输入覆盖6至8.4V；输出5V持续2A；主控音频屏幕独立供电；不要AMS1117线性板','',1,0],
  ['直流电源开关','','面板安装成品','额定>=12VDC 10A；切断电池负载支路；开孔尺寸按最终型号；充电支路独立','',1,0],
  ['小型汽车插片保险丝座 带线','','带线成品','适配7.5A小型插片保险丝；额定>=32VDC 10A；20AWG或更粗引线','',1,0],
  ['7.5A 小型插片保险丝','','MINI插片','32VDC；与保险丝座配套；1个使用1个备用；须结合实测电流复核','',1,1],
  ['XT30 公母配对插头','','公母一套','电池与供电可拆连接；额定电流>=10A；每套含公头母头','',2,0],
  ['20AWG硅胶电子线 红色','','1米','电池及舵机电源正极配线；不能用杜邦线承担整机舵机总电流','',1,0],
  ['20AWG硅胶电子线 黑色','','1米','电池及舵机电源地线；电源各支路共地','',1,0],
  ['杜邦线 母对母 10cm 40P','','40根一排','2.54mm；仅用于信号与小电流模块；按需要拆分','',1,0],
  ['5V2A USB-A电源适配器','','成品充电头','正规认证；USB-A 5V2A；用于2S升压充电模块输入','',1,0],
  ['USB-A转Type-C数据线 0.5米','','成品线缆','支持5V2A及USB2.0数据；可用于开发板下载和充电','',1,0],
  ['1000uF 10V 低ESR铝电解电容','','直插','舵机5V母线滤波；额定105摄氏度；直径高度以最终选型为准','',2,0],
  ['470uF 10V 低ESR铝电解电容','','直插','逻辑5V支路滤波；注意极性','',1,0],
  ['双面玻纤万能板 4x6cm','','2.54mm孔距','首版信号及小电流分配载板；舵机大电流另用20AWG配线','',1,0],
  ['2.54mm 1x40P 单排排针','','直插公针','可剪断；模块及信号分配备用；主控随附排针不重复计算','',2,0],
  ['2.54mm 1x40P 单排排母','','直插母座','可分切或改选短排母组合；模块可拆安装；插接高度需计入结构','',2,0],
  ['M2x6 十字盘头螺钉','','公制机牙','模块及试装通用备料；不替代舵机随附中心螺钉；最终长度待结构确认','',20,0],
  ['M2 六角螺母','','公制','与M2机牙螺钉配套','',20,0],
  ['M3x8 内六角圆柱头螺钉','','公制机牙','外壳可拆连接备料；最终长度待模型确认','',12,0],
  ['M3 热熔铜螺母 外径4.6 长4mm','','黄铜嵌件','用于PLA外壳；嵌件底孔以实际规格和试样调整','',12,0],
  ['M3 平垫圈','','金属平垫','用于机壳螺钉连接','',12,0],
  ['防滑橡胶脚垫 直径12mm','','成品脚垫','约12mm直径、厚3至5mm；四足脚底；最终粘接面待模型确认','',4,0],
  ['魔术贴电池绑带 10x150mm','','一条','电池可拆固定；不挤压软包','',1,0],
  ['EVA闭孔泡棉 背胶 厚1mm','','100x100mm一片','电池托架缓冲及模块防振；避免覆盖热源','',1,0],
  ['绝缘热缩管套装','','多规格小套装','覆盖20AWG线与XT30焊点；含2mm、3mm、5mm等常用规格','',1,0],
];

if (rows.length !== 32 || rows.some(r => r.length !== 7 || !Number.isInteger(r[5]) || r[5] < 1)) throw new Error('BOM data validation failed');
await fs.mkdir(out, { recursive: true });
const wb = Workbook.create();
const s = wb.worksheets.add('配件待匹配_不含屏幕舵机');
s.getRange('A1:G33').values = [headers, ...rows];
s.getRange('A1:G33').format.font = { name: 'Arial', size: 11, color: '#273B32' };
s.getRange('A1:G33').format.verticalAlignment = 'center';
s.getRange('A1:G33').format.wrapText = true;
s.getRange('A2:G33').format.rowHeight = 62;
for (const [col, width] of Object.entries({ A: 36, B: 14, C: 21, D: 79, E: 16, F: 12, G: 12 })) s.getRange(`${col}1:${col}33`).format.columnWidth = width;
s.getRange('A1:G1').format = { fill: '#345C4B', font: { name: 'Arial', size: 11, bold: true, color: '#FFFFFF' }, rowHeight: 30, horizontalAlignment: 'center', verticalAlignment: 'center' };
s.getRange('F2:G33').setNumberFormat('0');
s.getRange('F2:G33').format.horizontalAlignment = 'center';
s.getRange('F2:G33').format.fill = '#FFF1CC';
for (let r = 2; r <= 33; r += 2) s.getRange(`A${r}:E${r}`).format.fill = '#F0F6F2';
s.getRange('A7:G7').format.rowHeight = 78;
s.freezePanes.freezeRows(1);
s.freezePanes.freezeColumns(1);
const output = path.join(out, '桌面助手-立创BOM导入-不含屏幕舵机.xlsx');
await (await SpreadsheetFile.exportXlsx(wb)).save(output);
const preview = await wb.render({ sheetName: s.name, range: 'A1:G9', scale: 1, format: 'png' });
await fs.writeFile(path.join(out, '立创BOM导入-预览.png'), new Uint8Array(await preview.arrayBuffer()));
await fs.writeFile(path.join(out, '立创BOM导入-核验数据.json'), JSON.stringify({ headers, rows }, null, 2));
console.log(JSON.stringify({ output, rows: rows.length, columns: headers.length, status: 'awaiting_user_matching' }));
