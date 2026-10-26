"""Render real A3 geometry; use the straight-on view to establish screen direction."""
import bpy, bmesh, json, hashlib, sys
from pathlib import Path
OUT=Path(__file__).resolve().parents[1]
FILE=OUT/'DesktopAssistant-整机结构-A3.blend'
bpy.ops.wm.open_mainfile(filepath=str(FILE))
scene=bpy.data.scenes['10_A3_COMPLETE_ASSEMBLY'];bpy.context.window.scene=scene
manifest=json.loads((OUT/'reports/complete-manifest.json').read_text())
parts=[scene.objects[r['name']] for r in manifest]
checks=[]
for o in parts:
    bm=bmesh.new();bm.from_mesh(o.data)
    checks.append({'id':o['part_id'],'nonmanifold_edges':sum(not e.is_manifold for e in bm.edges)})
    bm.free()
assert len(parts)==30 and all(c['nonmanifold_edges']==0 for c in checks)
views=['front','perspective','rear','internal','front-open','exploded','parts']
if '--' in sys.argv: views=sys.argv[sys.argv.index('--')+1:]
for view in views:
    if view in ['front','perspective','rear','internal']:
        bpy.context.window.scene=scene
        scene.camera=scene.objects['A3_COMPLETE_'+view+'_camera']
        if view=='internal':scene.camera.data.ortho_scale=.330
        scene.objects['A3_COMPLETE_studio_floor'].hide_render=(view=='front')
        for o in parts:o.hide_render=(view=='internal' and o['part_id'] in ['R01','R02'])
        active=scene
    else:
        active=bpy.data.scenes[{'front-open':'13_A3_FRONT_CAP_REMOVED','exploded':'11_A3_EXPLODED_ASSEMBLY','parts':'12_A3_PRINT_PARTS_OVERVIEW'}[view]]
        bpy.context.window.scene=active
    active.render.filepath=str(OUT/'renders'/('A3-'+view+'.png'))
    bpy.ops.render.render(write_still=True)
(OUT/'reports/final-artifact-reopen.json').write_text(json.dumps({
 'blend_sha256':hashlib.sha256(FILE.read_bytes()).hexdigest(),'scene':scene.name,
 'part_count':len(parts),'all_closed':True,'scenes_available':list(bpy.data.scenes.keys()),
 'parts':checks,'rendered_views_this_run':views,'render_only_changes_saved':False},ensure_ascii=False,indent=2))
print('A3_RENDERS_DONE',views,flush=True)
