"""Check actual EDA readback geometry, including accurate native pad coordinates.

This is an independent connectivity/clearance check, not the native EDA DRC.
"""
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'router' / '_deps'))
from shapely.geometry import Point, LineString, box
from shapely.affinity import rotate, scale
from shapely.ops import polygonize, unary_union

MIL_MM = .0254
CLEARANCE = 8.0
EDGE = 12.0
TOL = .001


def main():
    source = sys.argv[1] if len(sys.argv) > 1 else 'pcb-routed-readback.json'
    data = json.loads((ROOT / source).read_text())
    outlines = [LineString([(p['startX'], p['startY']), (p['endX'], p['endY'])])
                for p in data['lines'] if p['layer'] == 11]
    for p in data.get('polylines', []):
        if p['layer'] != 11:
            continue
        source_points = p['polygon']['polygon']
        assert source_points[2] == 'L' and all(isinstance(v, (int, float)) for v in source_points[3:])
        coords = source_points[:2] + source_points[3:]
        points = list(zip(coords[::2], coords[1::2]))
        assert points[0] == points[-1], 'Native outline polyline must be closed'
        outlines.append(LineString(points))
    polys = list(polygonize(unary_union(outlines)))
    assert len(polys) == 1, 'Board outline must form exactly one closed polygon'
    board = polys[0]
    ref_by_id = {p['primitiveId']: c['component']['designator'] + '.' + str(p['padNumber'])
                 for c in data['components'] for p in c['pads']}
    objects, holes, violations = [], [], []
    for p in data['allPads']:
        if not p['metallization']:
            assert p['hole'][0] == 'ROUND'
            holes.append(dict(id=p['padNumber'], x=p['x'], y=p['y'], diameter=p['hole'][1]))
            continue
        shape, w, h, *_ = p['pad']
        if shape == 'ELLIPSE':
            geom = scale(Point(p['x'], p['y']).buffer(1, quad_segs=96), w/2, h/2)
        elif shape == 'RECT':
            geom = box(p['x'] - w/2, p['y'] - h/2, p['x'] + w/2, p['y'] + h/2)
        else:
            raise ValueError('Unsupported native pad shape: ' + shape)
        # getAll() reports radians; all noncircular pads in this design are unrotated.
        geom = rotate(geom, p.get('rotation', 0), origin=(p['x'], p['y']), use_radians=True)
        objects.append(dict(id=ref_by_id[p['primitiveId']], net=p['net'],
                            layers={1, 2} if p['layer'] == 12 else {p['layer']}, geom=geom, kind='pad'))
    widths = defaultdict(set)
    for p in data['lines']:
        if p['layer'] not in (1, 2):
            continue
        assert p['net'], 'Unassigned copper trace'
        geom = LineString([(p['startX'], p['startY']), (p['endX'], p['endY'])]).buffer(p['lineWidth']/2, quad_segs=64)
        objects.append(dict(id=p['primitiveId'], net=p['net'], layers={p['layer']}, geom=geom, kind='trace'))
        widths[p['net']].add(p['lineWidth'])
        required = 40 if p['net'] in ('GND', '+5V_LOGIC', '+5V_MCU') else 24 if p['net'] == '+3V3' else 12
        if p['lineWidth'] < required - TOL:
            violations.append(dict(kind='line-width', id=p['primitiveId'], net=p['net'], actual=p['lineWidth'], required=required))
    for p in data['vias']:
        assert p['net'], 'Unassigned via'
        geom = Point(p['x'], p['y']).buffer(p['diameter']/2, quad_segs=96)
        objects.append(dict(id=p['primitiveId'], net=p['net'], layers={1, 2}, geom=geom, kind='via'))
        if p['holeDiameter'] < .3 / MIL_MM - TOL or p['diameter'] < .6 / MIL_MM - TOL:
            violations.append(dict(kind='via-size', id=p['primitiveId']))
    assert len(holes) == 4
    edge_min = float('inf')
    screw_min = float('inf')
    clearance_min = float('inf')
    parent = list(range(len(objects)))
    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i
    for i, a in enumerate(objects):
        edge_distance = a['geom'].distance(board.boundary) if board.covers(a['geom']) else -1
        edge_min = min(edge_min, edge_distance)
        if edge_distance < EDGE - TOL:
            violations.append(dict(kind='copper-board-edge', id=a['id'], gap_mil=edge_distance))
        for hole in holes:
            gap = a['geom'].distance(Point(hole['x'], hole['y'])) - 2.5 / MIL_MM
            screw_min = min(screw_min, gap)
            if gap < -TOL:
                violations.append(dict(kind='screw-head-keepout', id=a['id'], hole=hole['id'], gap_mil=gap))
        for j in range(i):
            b = objects[j]
            if not (a['layers'] & b['layers']):
                continue
            gap = a['geom'].distance(b['geom'])
            if a['net'] and a['net'] == b['net']:
                if gap <= TOL:
                    parent[find(i)] = find(j)
            else:
                clearance_min = min(clearance_min, gap)
                if gap < CLEARANCE - TOL:
                    violations.append(dict(kind='different-net-clearance', a=a['id'], b=b['id'],
                                           net_a=a['net'], net_b=b['net'], gap_mil=gap))
    groups = defaultdict(lambda: defaultdict(list))
    for i, a in enumerate(objects):
        if a['kind'] == 'pad' and a['net']:
            groups[a['net']][find(i)].append(a['id'])
    connectivity = [dict(net=n, connected=len(g) == 1, groups=[sorted(v) for v in g.values()])
                    for n, g in sorted(groups.items())]
    pad_roots = {find(i) for i, a in enumerate(objects) if a['kind'] == 'pad' and a['net']}
    orphan_copper = [dict(id=a['id'], net=a['net'], kind=a['kind'])
                     for i, a in enumerate(objects)
                     if a['kind'] in ('trace', 'via') and find(i) not in pad_roots]
    for orphan in orphan_copper:
        violations.append(dict(kind='orphan-copper', object=orphan))
    report = dict(source=source, source_coordinates=data.get('geometry_source_note', 'pcb_PrimitivePad.getAll (unrounded)'),
                  not_native_eda_drc=True, components=len(data['components']),
                  pads=len(ref_by_id), connected_pad_count=sum(a['kind'] == 'pad' and bool(a['net']) for a in objects),
                  nc_pads=[a['id'] for a in objects if a['kind'] == 'pad' and not a['net']],
                  board_size_mm=[(board.bounds[2] - board.bounds[0]) * MIL_MM, (board.bounds[3] - board.bounds[1]) * MIL_MM],
                  board_area_mm2=board.area * MIL_MM**2, mounting_holes=holes,
                  minimum_different_net_clearance_mil=clearance_min,
                  minimum_copper_board_edge_mil=edge_min,
                  minimum_screw_head_clearance_mil=screw_min,
                  trace_widths_mil={k: sorted(v) for k, v in sorted(widths.items())},
                  connectivity=connectivity, connected_nets=sum(c['connected'] for c in connectivity),
                  total_nets=len(connectivity), all_nets_connected=all(c['connected'] for c in connectivity),
                  orphan_copper=orphan_copper, all_copper_connected_to_pads=not orphan_copper,
                  violations=violations, geometry_pass=not violations)
    (ROOT / 'native-routing-validation.json').write_text(json.dumps(report, ensure_ascii=False, indent=2))
    print(json.dumps({k: v for k, v in report.items() if k not in ('connectivity', 'mounting_holes', 'trace_widths_mil')}, ensure_ascii=False, indent=2))
    assert report['geometry_pass'] and report['all_nets_connected']


if __name__ == '__main__':
    main()
