import sys,json,math
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent.parent/'repair-2026-09-12'))
from eda_client import execute,ROOT
out=Path(__file__).resolve().parent
changes={'R6':[29,52.5,270],'R17':[14.75,64,90],'C8':[24.2,55.8,180],'C5':[29,56.5,0],'R11':[75,65,90],'L1':[22,49,270],'C11':[17,56.5,180],'C12':[17,59,180],'C7':[17,61.5,180],'C13':[18,64,180],'EC1':[86,65,0],'C9':[94,52,0],'C19':[98,46.5,0]}
print(execute('const all=await eda.pcb_PrimitiveComponent.getAll();for(const [ref,p] of Object.entries('+json.dumps(changes)+')){const a=all.find(c=>c.getState_Designator()===ref).toAsync();a.setState_X(p[0]/.0254);a.setState_Y(-p[1]/.0254);a.setState_Rotation(p[2]);await a.done();}return true;','optimize-charge-loop-placement'))
pos=json.load(open(out/'placement.json'));pos.update(changes);(out/'placement.json').write_text(json.dumps(pos,indent=2))
g=execute('const out=[];for(const c of await eda.pcb_PrimitiveComponent.getAll())out.push({component:c,pads:await eda.pcb_PrimitiveComponent.getAllPinsByPrimitiveId(c.getState_PrimitiveId())});return out;','critical-route-geometry')
(out/'placed-geometry.json').write_text(json.dumps(g,ensure_ascii=False,indent=2))
pins={}
for c in g:
 for p in c['pads']:pins[c['component']['designator']+'.'+p['padNumber']]=p
tracks=[];vias=[]
def p(s):
 a=pins[s];return [a['x']*.0254,-a['y']*.0254]
def wire(net,points,width,layer=1):
 points=[p(x) if isinstance(x,str) else x for x in points]
 for a,b in zip(points,points[1:]):
  if math.dist(a,b)<.001:continue
  tracks.append({'net':net,'layer':layer,'a':a,'b':b,'w':width})
def via(net,x,y,d=.6,h=.3):vias.append({'net':net,'x':x,'y':y,'d':d,'h':h})
# High-current pack path. Board copper does not bypass the protection FETs.
wire('VBAT_RAW_P',['JBAT.2',[18.5,7],'F1.1'],2.5)
wire('VBAT_FUSED',['F1.2',[30,6],'J_SW.1'],2.5)
wire('VBAT_SW',['J_SW.2',[44.5,8],[44.5,35.5],'J_SRV_IN.1'],2.5)
wire('VBAT_SW',[[44.5,22.5],'J_LOG_IN.1'],2)
wire('VBAT_RAW_N',['JBAT.1',[13.8,7.3],[13.8,23],[12.316,25.095]],2.2)
wire('VBAT_RAW_N',['Q2.1','Q2.3'],.8)
for pin in ['1','2','3']:wire('VBAT_RAW_N',['Q2.'+pin,[13.8,p('Q2.'+pin)[1]]],.8)
for pa,pb in [('8','5'),('7','6'),('6','7'),('5','8')]:wire('MOS_MID',['Q2.'+pa,'Q1.'+pb],1.0)
wire('MOS_MID',[[19.5,25.1],[19.5,28.9]],3.5)
for pin in ['1','2','3']:wire('GND',['Q1.'+pin,[28.3,p('Q1.'+pin)[1]]],.8)
wire('GND',[[28.3,26.365],[28.3,29]],1.8)
for x in [28.0,28.8]:
 for y in [26.6,27.5,28.4]:via('GND',x,y)
wire('GND',[[28.3,27.5],[33,30.5],'J_SRV_IN.2'],2.5,2)
wire('GND',[[33,30.5],[33,17.5],'J_LOG_IN.2'],2.5,2)
# Servo supply uses parallel copper on both sides; ground returns beside it.
for layer in [1,2]:
 wire('+5V_SERVO',[[104,18],[104,52.6]],2.5,layer)
 for i in range(1,9):wire('+5V_SERVO',['SV'+str(i)+'.2',[104,p('SV'+str(i)+'.2')[1]]],1,layer)
 wire('+5V_SERVO',['J_SRV_OUT.1',[99,64.5],[99,55.6],[104,52.6]],2.5,layer)
 wire('+5V_SERVO',['C9.1',[92.25,57],[98,57],[99,58]],1.5,layer)
 wire('GND',[[108.2,18],[108.2,59.5],'J_SRV_OUT.2'],1.8,layer)
 for i in range(1,9):wire('GND',['SV'+str(i)+'.3',[108.2,p('SV'+str(i)+'.3')[1]]],1.3,layer)
# IP2326 power and bootstrap loop; short narrow necks only at QFN leads.
for n in ['15','16','17']:wire('SW_CHG',['U4.'+n,[p('U4.'+n)[0],57.25]],.25)
wire('SW_CHG',[[21.25,57.25],[22.25,57.25]],.3)
wire('SW_CHG',[[21.5,57.25],[21.0,56.3],[21.0,54.8],'L1.2'],.7)
wire('SW_CHG',['C8.2',[23.2,54.8],'L1.2'],.5)
wire('BST_CAP',['U4.14',[22.75,57.45],[23.2,57],[25.2,57],'C8.1'],.25)
wire('CHG_VIN',['U4.13',[23.25,57.3],[25,57.3],'C5.1'],.25)
wire('CHG_VIN',['C5.1',[28,54.45],'R6.2'],.5)
wire('VBUS',['R6.1',[29,45.5],[27.5,44.05],'L1.1'],1)
wire('VBUS',['L1.1',[7.8,44.05],[7.8,59.5],[9,60.7],'C6.1'],1.2)
# Each connector VBUS pad escapes before joining the common supply.
wire('VBUS',['J6.A4B9',[10.6,66],[8.5,64],[8.5,62],'C6.1'],.5)
wire('VBUS',['J6.B4A9',[15.4,66.9],[15.9,66.4]],.4)
via('VBUS',15.9,66.4)
wire('VBUS',[[15.9,66.4],[8.5,66.4],[8.5,62]],.8,2);via('VBUS',8.5,62)
wire('GND',['U4.18',[20.75,58.8],[21.3,59.3],'U4.25'],.25)
for x in [21.4,22.6]:
 for y in [59.4,60.6]:via('GND',x,y)
wire('CHG_VSYS',['U4.19',[19.4,58.75]],.25)
wire('CHG_VSYS',['U4.20',[19.4,59.25]],.25)
wire('CHG_VSYS',[[19.4,58.75],[19.4,59.25]],.3)
wire('CHG_VSYS',[[19.4,59],'C12.1'],.65)
wire('CHG_VSYS',['C12.1',[18,57.2],'C11.1'],.7)
wire('VBAT_FUSED',['U4.21',[19.25,59.75],[19,60.2],[19,61.5],'C7.1'],.25)
wire('VBAT_FUSED',['U4.22',[19.25,60.249]],.25)
wire('VBAT_FUSED',['C7.1',[18.9,62.4],'C13.1'],.6)
# Ground stitching next to local capacitor returns.
for name in ['C5.2','C6.2','C11.2','C12.2','C7.2','C13.2']:
 x,y=p(name);dx=-1 if name in ['C11.2','C12.2','C7.2','C13.2'] else 1.1
 dy=1.4 if name=='C5.2' else 0
 if dy:dx=0
 via('GND',x+dx,y+dy);wire('GND',[name,[x+dx,y+dy]],.5)
(out/'critical-tracks.json').write_text(json.dumps(tracks,indent=2));(out/'critical-vias.json').write_text(json.dumps(vias,indent=2))
live=execute('return {lines:await eda.pcb_PrimitiveLine.getAll(),vias:await eda.pcb_PrimitiveVia.getAll(),source:await eda.sys_FileManager.getDocumentSource()};','backup-critical-routing-before-refine')
(out/'critical-before-refine.source').write_text(live['source'])
lineids=[v['primitiveId'] for v in live['lines'] if v['layer'] in [1,2]]
viaids=[v['primitiveId'] for v in live['vias']]
if lineids:execute('return await eda.pcb_PrimitiveLine.delete('+json.dumps(lineids)+');','clear-previous-generated-critical-tracks')
if viaids:execute('return await eda.pcb_PrimitiveVia.delete('+json.dumps(viaids)+');','clear-previous-generated-critical-vias')
ids=[]
for start in range(0,len(tracks),30):
 code='const EPCB_LayerId={TOP:1,BOTTOM:2};const ids=[];for(const t of '+json.dumps(tracks[start:start+30])+'){const c=await eda.pcb_PrimitiveLine.create(t.net,t.layer===1?EPCB_LayerId.TOP:EPCB_LayerId.BOTTOM,t.a[0]/.0254,-t.a[1]/.0254,t.b[0]/.0254,-t.b[1]/.0254,t.w/.0254,true);ids.push(c.getState_PrimitiveId());}return ids;'
 ids+=execute(code,'route-critical-'+str(start))
vids=execute('const ids=[];for(const v of '+json.dumps(vias)+'){const a=await eda.pcb_PrimitiveVia.create(v.net,v.x/.0254,-v.y/.0254,v.h/.0254,v.d/.0254,undefined,undefined,undefined,true);ids.push(a.getState_PrimitiveId());}return ids;','critical-thermal-vias')
(out/'critical-native-ids.json').write_text(json.dumps({'lines':ids,'vias':vids},indent=2))
print('tracks',len(ids),'vias',len(vids));print(execute('return await eda.pcb_Document.save();','save-critical-routing'))
