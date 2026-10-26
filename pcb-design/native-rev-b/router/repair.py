"""Join disconnected copper trees using actual same-net traces as route targets."""
import argparse,json
import route as r

def groups(pads,candidate,net):
    objects=[]
    for p in pads:
        if p['net']==net:objects.append({'kind':'pad','pad':p,'geom':p['geom'],'layers':{0,1}})
    for t in candidate['traces']:
        if t['net']==net:objects.append({'kind':'trace','trace':t,'geom':r.trace_geom(t),'layers':{r.LAYERS.index(t['layer'])}})
    for v in candidate['vias']:
        if v['net']==net:objects.append({'kind':'via','via':v,'geom':r.Point(v['x'],v['y']).buffer(v['diameter']/2,quad_segs=64),'layers':{0,1}})
    ds=r.DSU(len(objects))
    for i,a in enumerate(objects):
        for j,b in enumerate(objects[i+1:],i+1):
            if a['layers']&b['layers'] and a['geom'].distance(b['geom'])<.01:ds.join(i,j)
    result={}
    for i,o in enumerate(objects):result.setdefault(ds.root(i),[]).append(o)
    return sorted([g for g in result.values() if any(o['kind']=='pad' for o in g)],key=lambda g:-sum(o['kind']=='pad' for o in g))

def main():
    ap=argparse.ArgumentParser();ap.add_argument('prefix');ap.add_argument('--output',default='route-repaired');args=ap.parse_args()
    src,digest,raw,pads=r.read_input()
    candidate=json.loads((r.ROOT/(args.prefix+'.json')).read_text())
    if digest!=candidate['source_sha256']:raise ValueError('Input changed')
    router=r.Router(pads);router.traces=candidate['traces'];router.vias=candidate['vias']
    attempts=[]
    for net in sorted(router.by_net):
        while True:
            gs=groups(pads,candidate,net)
            if len(gs)<2:break
            targets=[]
            for o in gs[0]:
                if o['kind']=='pad':targets += [(l,o['pad']['x'],o['pad']['y']) for l in o['layers']]
                if o['kind']=='trace':targets += [(l,x,y) for l in o['layers'] for x,y in o['trace']['points']]
                if o['kind']=='via':targets += [(l,o['via']['x'],o['via']['y']) for l in o['layers']]
            b={'x':targets[0][1],'y':targets[0][2],'targets':targets}
            width=r.POWER_WIDTHS.get(net,12);walk,via,through,obs=router.masks(net,width);made=False
            for g in gs[1:]:
                for o in g:
                    if o['kind']!='pad':continue
                    a=o['pad'];path,expanded,reason=router.astar(a,b,walk,via,through)
                    if path:
                        endpoint={'x':path[-1][1],'y':path[-1][2]}
                        ts,vs=router.geometry_from_path(net,width,a,endpoint,path)
                        good,reason=router.accept_geometry(ts,vs,obs)
                        if good:router.traces.extend(ts);router.vias.extend(vs);made=True
                    attempts.append({'net':net,'source':a['id'],'expanded':expanded,'result':reason})
                    if made:break
                if made:break
            print(json.dumps({'net':net,'groups_before':len(gs),'connected_to_tree':made,'attempt':attempts[-1]}),flush=True)
            if not made:break
    check=r.validate(pads,candidate);candidate['tree_repair_attempts']=attempts
    candidate['unrouted']=[n for n in check['connectivity'] if not n['connected']]
    candidate['validation_summary']={k:check[k] for k in ['status','connected_nets','total_nets','all_nets_connected','trace_count','via_count']}
    (r.ROOT/(args.output+'.json')).write_text(json.dumps(candidate,ensure_ascii=False,indent=2)+'\n')
    (r.ROOT/(args.output+'-validation.json')).write_text(json.dumps(check,ensure_ascii=False,indent=2)+'\n')
    r.preview(pads,candidate,check,args.output+'-preview.svg')
    print(json.dumps(candidate['validation_summary']))

if __name__=='__main__':main()
