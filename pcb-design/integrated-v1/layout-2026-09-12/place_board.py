import json,sys,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent.parent/'repair-2026-09-12'))
from eda_client import execute,ROOT
out=Path(__file__).resolve().parent
# Human drawing coordinates in mm: origin at board upper-left, Y down.
pos={
'J2':(55,27.5,270),'J1':(72.78,27.5,270),
'JBAT':(11,10,0),'JBAL':(8,21,0),'F1':(26,10,0),'J_SW':(40,6,0),
'Q2':(15,28,0),'Q1':(24,28,180),'U1':(26,20,0),
'R1':(29.5,17,0),'C1':(29.5,19.3,180),'R2':(29.5,21.8,0),'C2':(29.5,24.1,180),'R3':(22,21,0),
'U2':(7,34,0),'C3':(7,37.3,0),'R4':(7,30.6,0),'Q3':(15,35,0),'R18':(15,31.4,0),'R19':(15,38.3,0),
'U3':(23,35,0),'C4':(23,38.3,0),'R5':(23,31.6,0),'Q4':(30,35,0),'R20':(30,31.4,0),'R21':(30,38.3,0),
'J_LOG_IN':(40,20,90),'J_SRV_IN':(40,33,90),'J_LOG_OUT':(40,46,90),'C10':(43,56,0),'JP_MCU':(74,56,0),
'R10':(48,8,90),'R9':(49.5,4,90),'C14':(51.5,4,90),
'J6':(9,70,0),'U4':(22,60,0),'L1':(19,51,0),
'C8':(24,56.3,0),'R6':(28.5,52.5,90),'C5':(26,56.7,270),
'C6':(9,64,0),'C7':(17,61.5,0),'C13':(17,64,0),'C11':(17,56.5,0),'C12':(17,59,0),
'R16':(7.7,66.7,90),'R17':(11.2,66.7,90),'R8':(26.4,59.3,0),'R22':(26.4,61.7,0),'R23':(24,65,90),
'J7':(25,70,0),'JP_CHG':(32,57,90),'R24':(29.3,60,90),'R7':(17,67.2,0),'D2':(17,71,0),
'J3':(88,6,0),'JP_LCD':(77,12,0),'J10':(87,13,0),'C15':(78,9,0),'C16':(92,12,0),
'J4':(47,24,270),'J5':(79,23,270),
'U7':(89,34,90),'C17':(84,38.2,90),'C18':(84,41.5,90),'R13':(83,32,0),'R14':(83,34.4,0),'R15':(83,36.8,0),
'J_SRV_OUT':(102,62,90),'C9':(94,54,0),'C19':(97,49,0),
'EC1':(88,65,0),'R11':(77.5,65,90),'R12':(77.5,61,90),'R26':(77.5,69,90),
}
for i in range(1,9):pos['SV'+str(i)]=(104,18+(i-1)*4.4,0)
g=json.load(open(out/'geometry.json'));by={x['component']['designator']:x for x in g};assert set(pos)==set(by),(set(by)-set(pos),set(pos)-set(by))
(out/'placement.json').write_text(json.dumps(pos,indent=2))
execute('return await eda.dmt_EditorControl.openDocument("bc31667e02a33e5b");','open-layout');time.sleep(.5)
for start in range(0,len(pos),15):
 rows=[]
 for ref,(x,y,rot) in list(pos.items())[start:start+15]:rows.append({'ref':ref,'id':by[ref]['component']['primitiveId'],'x':x/.0254,'y':-y/.0254,'r':rot})
 code='if((await eda.dmt_SelectControl.getCurrentDocumentInfo()).uuid!=="bc31667e02a33e5b")throw Error("wrong PCB");const out=[];for(const p of '+json.dumps(rows)+'){const c=await eda.pcb_PrimitiveComponent.get(p.id);const a=c.toAsync();a.setState_X(p.x);a.setState_Y(p.y);a.setState_Rotation(p.r);await a.done();out.push(p.ref);}return out;'
 print(execute(code,'place-components-'+str(start)),flush=True)
print(execute('const EPCB_LayerId={BOARD_OUTLINE:11};const outline=[[0,0],[110,0],[110,-75],[0,-75],[0,0]];const ids=[];for(let i=0;i<4;i++){const p=outline[i],q=outline[i+1];const a=await eda.pcb_PrimitiveLine.create("",EPCB_LayerId.BOARD_OUTLINE,p[0]/.0254,p[1]/.0254,q[0]/.0254,q[1]/.0254,4,true);ids.push(a.getState_PrimitiveId());}return ids;','create-board-outline'),flush=True)
print(execute('const EPCB_LayerId={MULTI:12};const EPCB_PrimitivePadHoleType={ROUND:"ROUND"};const EPCB_PrimitivePadShapeType={ELLIPSE:"ELLIPSE"};const out=[];for(const p of [[4,4],[106,4],[4,71],[106,71]]){const h=await eda.pcb_PrimitivePad.create(EPCB_LayerId.MULTI,"",p[0]/.0254,-p[1]/.0254,0,[EPCB_PrimitivePadShapeType.ELLIPSE,3.2/.0254,3.2/.0254],"",[EPCB_PrimitivePadHoleType.ROUND,3.2/.0254],0,0,0,false);out.push(h);}return out;','create-mounting-holes'),flush=True)
print(execute('return {saved:await eda.pcb_Document.save(),zoom:await eda.pcb_Document.zoomToBoardOutline()};','save-first-placement'),flush=True)
