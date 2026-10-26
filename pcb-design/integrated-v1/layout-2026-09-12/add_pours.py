import sys,json
from pathlib import Path
P=Path(__file__).resolve().parent
sys.path.insert(0,str(P.parent/'repair-2026-09-12'));from eda_client import execute
r=execute('const d=await eda.dmt_SelectControl.getCurrentDocumentInfo();if(d.uuid!=="bc31667e02a33e5b")throw Error("PCB guard");const EPCB_LayerId={TOP:1,BOTTOM:2};const EPCB_PrimitivePourFillMethod={SOLID:"solid"};const prev=await eda.pcb_PrimitivePour.getAll();if(prev.length)throw Error("pours already exist");const out=[];for(const layer of [EPCB_LayerId.BOTTOM,EPCB_LayerId.TOP]){const p=eda.pcb_MathPolygon.createPolygon([.5/.0254,-.5/.0254,"L",109.5/.0254,-.5/.0254,109.5/.0254,-74.5/.0254,.5/.0254,-74.5/.0254,.5/.0254,-.5/.0254]);const pour=await eda.pcb_PrimitivePour.create("GND",layer,p,EPCB_PrimitivePourFillMethod.SOLID,false,"GND_"+layer,5,10,true);if(!pour)throw Error("pour creation failed");let rebuild;try{rebuild=await pour.rebuildCopperRegion()}catch(e){rebuild={error:e.message}}out.push({pour,rebuild});}return out;','add-ground-pours')
(P/'pours-created.json').write_text(json.dumps(r,ensure_ascii=False,indent=2));print(json.dumps(r,ensure_ascii=False)[:1800])
