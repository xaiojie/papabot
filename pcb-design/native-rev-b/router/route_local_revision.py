"""Route the new display rail while retaining unrelated RevA copper."""
import json
import time
import route as r
from repair import groups

src, digest, raw, pads = r.read_input()
pads, precise = r.precise_pads(pads)
data = json.loads((r.ROOT.parent / 'pcb-placed-readback.json').read_text())
native_vias = {}
for line in (r.ROOT.parent / 'pcb-placed.source').read_text().splitlines():
    h, d = line.split('||', 1)
    h, d = json.loads(h), json.loads(d.rstrip('|'))
    if h['type'] == 'VIA':
        native_vias[h['id']] = d

removed_nets = {'+5V_LOGIC'}
candidate = dict(traces=[], vias=[])
for t in data['lines']:
    if t['layer'] not in (1, 2) or t['net'] in removed_nets:
        continue
    candidate['traces'].append(dict(net=t['net'], layer=r.LAYERS[t['layer'] - 1],
        points=[[t['startX'], t['startY']], [t['endX'], t['endY']]], width=t['lineWidth'], native_id=t['primitiveId']))
for v in data['vias']:
    if v['net'] in removed_nets:
        continue
    n = native_vias[v['primitiveId']]
    candidate['vias'].append(dict(net=v['net'], x=n['centerX'], y=n['centerY'],
        diameter=n['viaDiameter'], drill=n['holeDiameter'], native_id=v['primitiveId']))
check = r.validate(pads, candidate)
print('Seed:', check['status'], check['connected_nets'], '/', check['total_nets'], check['violations'][:12], flush=True)
if check['violations']:
    (r.ROOT / 'seed-violations.json').write_text(json.dumps(check, indent=2))
    raise RuntimeError('New part position conflicts with preserved copper; adjust placement first')
router = r.Router(pads)
router.traces, router.vias = candidate['traces'], candidate['vias']
attempts = []
started = time.monotonic()
for net in ('LCD_3V3', '+5V_LOGIC', '+3V3', 'GND'):
    while True:
        gs = groups(pads, candidate, net)
        if len(gs) < 2:
            break
        targets = []
        for o in gs[0]:
            if o['kind'] == 'pad':
                targets += [(l, o['pad']['x'], o['pad']['y']) for l in o['layers']]
            if o['kind'] == 'trace':
                targets += [(l, x, y) for l in o['layers'] for x, y in o['trace']['points']]
            if o['kind'] == 'via':
                targets += [(l, o['via']['x'], o['via']['y']) for l in o['layers']]
        b = {'x': targets[0][1], 'y': targets[0][2], 'targets': targets}
        width = r.POWER_WIDTHS.get(net, 12)
        walk, via, through, obs = router.masks(net, width)
        sources = [o['pad'] for g in gs[1:] for o in g if o['kind'] == 'pad']
        sources.sort(key=lambda a: min((a['x']-x)**2+(a['y']-y)**2 for _,x,y in targets))
        made = False
        for a in sources:
            path, expanded, reason = router.astar(a, b, walk, via, through)
            if path:
                endpoint = {'x': path[-1][1], 'y': path[-1][2]}
                ts, vs = router.geometry_from_path(net, width, a, endpoint, path)
                good, reason = router.accept_geometry(ts, vs, obs)
                if good:
                    for t in ts:
                        for tolerance in (20, 10, 5, 2, 1, .5, .1):
                            trial = dict(t, points=[list(p) for p in r.LineString(t['points']).simplify(tolerance).coords])
                            if router.accept_geometry([trial], [], obs)[0]:
                                t['points'] = trial['points']
                                break
                    router.traces.extend(ts)
                    router.vias.extend(vs)
                    made = True
            attempts.append(dict(net=net, source=a['id'], expanded=expanded, result=reason, accepted=made))
            print(attempts[-1], flush=True)
            if made:
                break
        if not made:
            break
check = r.validate(pads, candidate)
candidate.update(schema='desktop-assistant.offline-route-candidate.v1', units='mil',
    source='../pcb-placed-pads.json', source_sha256=digest, precise_pad_audit=precise,
    input_components=len(raw), input_pads=len(pads), tree_repair_attempts=attempts,
    removed_original_nets=sorted(removed_nets), elapsed_seconds=time.monotonic()-started,
    unrouted=[n for n in check['connectivity'] if not n['connected']],
    validation_summary={k:check[k] for k in ('status','connected_nets','total_nets','all_nets_connected','trace_count','via_count')})
(r.ROOT / 'route-candidate.json').write_text(json.dumps(candidate, ensure_ascii=False, indent=2))
(r.ROOT / 'route-candidate-validation.json').write_text(json.dumps(check, ensure_ascii=False, indent=2))
r.preview(pads, candidate, check)
print('FINAL', candidate['validation_summary'], 'unrouted', candidate['unrouted'], 'violations', check['violations'][:10], flush=True)
