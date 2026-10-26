"""Compare proposed PCB screw heads with the current nominal header bodies."""
import bpy, bmesh, json, math
from pathlib import Path
from mathutils import Matrix, Vector

OUT = Path(__file__).resolve().parents[1]
bpy.ops.wm.open_mainfile(filepath=str(OUT / 'DesktopAssistant-整机结构-A2.blend'))
scene = bpy.data.scenes['10_A2_COMPLETE_ASSEMBLY']
bpy.context.window.scene = scene
bpy.context.view_layer.update()
headers = [o for o in scene.objects if o.name.startswith('REF_CURRENT__REF_J')]

def volume_intersection(a, b):
    copies = []
    for o in [a, b]:
        me = o.data.copy()
        me.transform(Matrix.Scale(1000, 4) @ o.matrix_world)
        for v in me.vertices:
            v.co = Vector([round(q, 5) for q in v.co])
        cp = bpy.data.objects.new('TEMP_HEAD_CHECK', me)
        scene.collection.objects.link(cp)
        copies.append(cp)
    x, y = copies
    mod = x.modifiers.new('Head interference', 'BOOLEAN')
    mod.operation = 'INTERSECT'
    mod.solver = 'EXACT'
    mod.object = y
    bpy.context.view_layer.objects.active = x
    bpy.ops.object.modifier_apply(modifier=mod.name)
    bm = bmesh.new(); bm.from_mesh(x.data)
    volume = abs(bm.calc_volume()); bm.free()
    for cp in copies:
        bpy.data.objects.remove(cp, do_unlink=True)
    return volume

results = []
for label, diameter, height in [('M3 head envelope', 6.0, 2.4), ('M2 small head envelope', 4.0, 2.0)]:
    conflicts = []
    for x, y in [(-35, 3), (35, 3), (35, 25), (-35, 25)]:
        bpy.ops.mesh.primitive_cylinder_add(vertices=96, radius=diameter / 2000,
            depth=height / 1000, location=(x / 1000, y / 1000, (67.6 + height / 2) / 1000))
        head = bpy.context.object
        bpy.context.view_layer.update()
        for body in headers:
            v = volume_intersection(head, body)
            if v > .001:
                conflicts.append({'xy_mm': [x, y], 'header': body.name, 'volume_mm3': round(v, 5)})
        bpy.data.objects.remove(head, do_unlink=True)
    results.append({'candidate': label, 'diameter_mm': diameter, 'height_mm': height,
                    'conflicts': conflicts})
report = {'source_blend': 'DesktopAssistant-整机结构-A2.blend', 'comparisons': results,
          'minimum_nominal_M2_head_to_J9_body_gap_mm': .46,
          'scope': 'PCB top screw heads versus nominal header plastic bodies; received hardware unmeasured'}
(OUT / 'reports/pcb-fastener-head-check.json').write_text(json.dumps(report, ensure_ascii=False, indent=2))
print(json.dumps(report, ensure_ascii=False), flush=True)
