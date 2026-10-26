"""Compress an offline route and add checked parallel power vias where space permits."""
import argparse, json, math, hashlib
from copy import deepcopy
import route as r

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('input_prefix')
    ap.add_argument('--output',default='route-candidate')
    args=ap.parse_args()
    src,digest,raw,pads=r.read_input()
    candidate=json.loads((r.ROOT/(args.input_prefix+'.json')).read_text())
    if digest!=candidate['source_sha256']:raise RuntimeError('Frozen source changed')
    pads,precise_evidence=r.precise_pads(pads)
    candidate['precise_pad_audit']=precise_evidence
    router=r.Router(pads)
    router.traces=candidate['traces'];router.vias=candidate['vias']
    before=sum(len(t['points'])-1 for t in router.traces)
    for index,t in enumerate(list(router.traces)):
        obs=router.obstacles(t['net'])
        for tol in [20,10,5,2,1,.5,.2,.1,.02,.005]:
            points=[list(p) for p in r.LineString(t['points']).simplify(tol).coords]
            if len(points)>=len(t['points']):continue
            trial=dict(t,points=points)
            good,_=router.accept_geometry([trial],[],obs)
            if good:
                router.traces[index]=trial
                break
    after=sum(len(t['points'])-1 for t in router.traces)
    groups=[]
    for vi,v in list(enumerate(router.vias)):
        if v['net'] not in r.POWER:continue
        obs=router.obstacles(v['net']);made=False
        group={'net':v['net'],'original_index':vi,'original_xy_mil':[v['x'],v['y']]}
        for mm in [.8,1.0,1.2,1.5]:
            for deg in range(0,360,30):
                theta=math.radians(deg)
                nv=dict(v,x=round(v['x']+mm*r.MM*math.cos(theta),4),y=round(v['y']+mm*r.MM*math.sin(theta),4))
                point=r.Point(nv['x'],nv['y'])
                # Keep the new drill well clear of every existing pad and via.
                if any(point.distance(p['geom'])<nv['diameter']/2+r.CLEAR+r.EPS for p in pads):continue
                if any(point.distance(r.Point(q['x'],q['y']))<.6*r.MM for q in router.vias):continue
                ts=[{'net':v['net'],'layer':layer,'points':[[v['x'],v['y']],[nv['x'],nv['y']]],'width':r.POWER_WIDTHS[v['net']]} for layer in r.LAYERS]
                good,_=router.accept_geometry(ts,[nv],obs)
                if good:
                    router.traces.extend(ts);router.vias.append(nv)
                    group.update(parallel_index=len(router.vias)-1,parallel_xy_mil=[nv['x'],nv['y']],paired=True)
                    made=True;break
            if made:break
        if not made:group.update(paired=False,reason='No checked position available for parallel via and full-width two-layer connection')
        groups.append(group)
    candidate['finalization']={'input_prefix':args.input_prefix,'segments_before_compression':before,'segments_after_compression':after,'power_via_pairs':groups,'power_via_current_capacity_validated':False}
    check=r.validate(pads,candidate)
    check['precise_pad_audit']=precise_evidence
    candidate['unrouted']=[n for n in check['connectivity'] if not n['connected']]
    candidate['validation_summary']={k:check[k] for k in ['status','connected_nets','total_nets','all_nets_connected','trace_count','via_count']}
    if hashlib.sha256(src.read_bytes()).hexdigest()!=digest:raise RuntimeError('Frozen source changed during finalization')
    (r.ROOT/(args.output+'.json')).write_text(json.dumps(candidate,ensure_ascii=False,indent=2)+'\n')
    (r.ROOT/(args.output+'-validation.json')).write_text(json.dumps(check,ensure_ascii=False,indent=2)+'\n')
    r.preview(pads,candidate,check,args.output+'-preview.svg')
    print(json.dumps({'summary':candidate['validation_summary'],'segments_before':before,'segments_after':after,'power_original_vias':len(groups),'power_vias_paired':sum(g['paired'] for g in groups),'unrouted':candidate['unrouted'],'violations':check['violations']},ensure_ascii=False))

if __name__=='__main__':main()
