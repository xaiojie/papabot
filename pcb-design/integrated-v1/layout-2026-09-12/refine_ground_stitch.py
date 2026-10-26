from board_geom import *
sys.path.insert(0,str(P.parent/'repair-2026-09-12'));from eda_client import execute
plan=json.loads((P/'ground-fill-plan.json').read_text());ids=json.loads((P/'ground-fill-ids.json').read_text());d=json.loads((P/'ground-drc.json').read_text());bad={e['objs'][0] for g in d['drc'] for sub in g['list'] for e in sub['list'] if e['obj1']['typeName']=='Fill Region'}
def ring(p):
 n=[x for x in p if isinstance(x,(int,float))];return [(n[i]*M,-n[i+1]*M) for i in range(0,len(n),2)]
cu=[]
kept=[r for i,r in enumerate(plan['regions']) if ids[i] not in bad]
for l in [1,2]:cu.append(union_all([Polygon(ring(r['paths'][0]),[ring(h) for h in r['paths'][1:]]) for r in kept if r['layer']==l]))
vs=[v for v in plan['vias'] if all(g.buffer(-.3).covers(Point(v['x'],v['y'])) for g in cu)]
js='const vs='+json.dumps(vs)+';const ids=[];for(const v of vs){const p=await eda.pcb_PrimitiveVia.create("GND",v.x/.0254,-v.y/.0254,v.drill/.0254,v.diameter/.0254,undefined,undefined,undefined,true);ids.push(p.getState_PrimitiveId());}return ids;'
(P/'ground-stitch-ids.json').write_text(json.dumps(execute(js,'stitch-verified-ground')))
plan.update(regions=kept,vias=vs,removed_unanchored_regions=len(bad));(P/'ground-fill-final.json').write_text(json.dumps(plan,indent=2))
print('Verified grounded regions',len(kept),'stitched vias',len(vs));print(execute('return {drc:await eda.pcb_Drc.check(true,false,true),pass:await eda.pcb_Drc.check(true,false,false)};','verified-ground-drc'))
