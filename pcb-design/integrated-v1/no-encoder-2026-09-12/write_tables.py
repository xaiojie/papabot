import json,csv,re,collections,zipfile
from pathlib import Path
P=Path(__file__).resolve().parent.parent/'final-no-encoder-2026-09-12'
g=json.loads((P/'PCB1_geometry.json').read_text());n=json.loads((P/'Schematic_netlist.json').read_text());old=P.parent/'final-2026-09-12'
def csvout(name,header,rows):
 with (P/name).open('w',encoding='utf-8-sig',newline='')as f:w=csv.writer(f);w.writerow(header);w.writerows(rows)
def natural(s):return [int(x)if x.isdigit()else x for x in re.split(r'(\d+)',s)]
by={c['component']['designator']:c['component']for c in g['geometry']};sn={c['props']['Designator']:c for c in n['components'].values()};assert set(by)==set(sn)and len(by)==79
with (old/'板载BOM_83器件.csv').open(encoding='utf-8-sig')as f:
 rows=list(csv.reader(f));header=rows.pop(0);bom=[r for r in rows if r[0]in by]
assert len(bom)==79 and len({r[5]for r in bom})==36
for r in bom:assert by[r[0]]['supplierId']==r[5]
csvout('板载BOM_79器件.csv',header,bom)
group=collections.defaultdict(list)
for r in bom:group[r[5]].append(r)
csvout('采购BOM_合并同料.csv',['立创编号','型号','值','封装','单板数量','位号'],[[k,v[0][2],v[0][3],v[0][4],len(v),' '.join(r[0]for r in v)]for k,v in sorted(group.items())])
pins=[];connectors=[]
for ref,c in sorted(sn.items(),key=lambda x:natural(x[0])):
 for pn,pin in sorted(c['pinInfoMap'].items(),key=lambda x:natural(x[0])):
  pins.append([ref,pn,pin.get('name',pn),pin['net'],'CONNECTED'if pin['net']else'NC'])
  if ref.startswith(('J','SV')):connectors.append([ref,pn,pin['net']or'NC','按PCB方焊盘/封装1脚标记辨认；屏幕端按CN1信号核对'])
csvout('引脚网络表_310引脚.csv',['位号','引脚号','引脚名称','网络','连接状态'],pins)
csvout('接口引脚表.csv',['接口','引脚','网络','接口朝向依据'],connectors)
assert len(pins)==310
placement={ref:{'x_mm':c['x']*.0254,'y_mm':-c['y']*.0254,'rotation':c['rotation']}for ref,c in sorted(by.items(),key=lambda x:natural(x[0]))}
(P/'Placement_final.json').write_text(json.dumps(placement,ensure_ascii=False,indent=2))
csvout('器件坐标_结构参考.csv',['位号','X_mm_板左侧为零','Y_mm_板上侧为零','EDA旋转度','层','封装'],[[ref,round(c['x']*.0254,4),round(-c['y']*.0254,4),c['rotation'],'Top',c['footprint'].get('name','')]for ref,c in sorted(by.items(),key=lambda x:natural(x[0]))])
with zipfile.ZipFile(P/'DesktopAssistant_Integrated_final.epro2')as z:
 (P/'PCB_native_preview.webp').write_bytes(z.read('IMAGE/bc31667e02a33e5b.webp'))
 (P/'project2_readback.json').write_bytes(z.read('project2.json'))
print('BOM 79 components / 36 part numbers; 310 pins; no EC1 or ENC nets')
