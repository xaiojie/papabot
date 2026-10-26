import bpy, json, hashlib, bmesh, sys
from pathlib import Path

OUT=Path(__file__).resolve().parents[1]
file=OUT/'DesktopAssistant-整机结构-A2.blend'
bpy.ops.wm.open_mainfile(filepath=str(file))
scene=bpy.data.scenes['10_A2_COMPLETE_ASSEMBLY']
bpy.context.window.scene=scene;bpy.context.view_layer.update()
manifest=json.loads((OUT/'reports/complete-manifest.json').read_text())
assert all(r['name'] in scene.objects for r in manifest)
parts=[scene.objects[r['name']] for r in manifest]
checks=[]
for o in parts:
    bm=bmesh.new();bm.from_mesh(o.data)
    checks.append({'id':o['part_id'],'nonmanifold_edges':sum(not e.is_manifold for e in bm.edges)})
    bm.free()
assert len(parts)==32 and all(c['nonmanifold_edges']==0 for c in checks)
assert '11_A2_EXPLODED_ASSEMBLY' in bpy.data.scenes and '12_A2_PRINT_PARTS_OVERVIEW' in bpy.data.scenes
scene.objects['A2_COMPLETE_internal_camera'].data.ortho_scale=.315
bpy.ops.wm.save_as_mainfile(filepath=str(file))
views=['internal'] if '--internal-only' in sys.argv else ['front','rear','internal']
for view in views:
    scene.camera=scene.objects['A2_COMPLETE_'+view+'_camera']
    for o in parts: o.hide_render=(view=='internal' and o['part_id'] in ['R01','R02'])
    scene.render.filepath=str(OUT/'renders'/('A2-'+view+'.png'))
    bpy.ops.render.render(write_still=True)
(OUT/'reports/final-artifact-reopen.json').write_text(json.dumps({
    'blend_sha256':hashlib.sha256(file.read_bytes()).hexdigest(),
    'scene':scene.name,'part_count':len(parts),'all_closed':True,
    'scenes_available':list(bpy.data.scenes.keys()),'parts':checks,
    'rendered_views':['front','rear','internal'],'rendered_views_this_run':views,
    'saved_camera_framing_update':'internal orthographic width 315mm',
    'render_only_changes_saved':False},ensure_ascii=False,indent=2))
print('FINAL_RENDERS_DONE',flush=True)
