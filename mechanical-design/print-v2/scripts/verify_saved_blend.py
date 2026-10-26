import bpy,json,hashlib,struct
from pathlib import Path
OUT=Path(__file__).resolve().parents[1]
bpy.ops.wm.open_mainfile(filepath=str(OUT/'desktop-assistant-print-v2.blend'))
source=bpy.data.scenes['01_ASSEMBLY_AND_DISASSEMBLY']
active=bpy.context.scene
bpy.context.window.scene=source
bpy.context.view_layer.update()
h=hashlib.sha256()
for o in sorted(source.objects,key=lambda a:a.name):
    h.update(o.name.encode());h.update(o.type.encode());h.update(str(tuple(tuple(row) for row in o.matrix_world)).encode())
    if o.type=='MESH':
        for v in o.data.vertices:h.update(struct.pack('<3f',*v.co))
        for f in o.data.polygons:h.update(str(tuple(f.vertices)).encode())
preservation=json.loads((OUT/'reports/source-preservation.json').read_text())
bpy.context.window.scene=active
manifest=json.loads((OUT/'reports/export-manifest.json').read_text())
source_path=OUT.parent/'assembly-v1/desktop-assistant-assembly-v1.blend'
result={'reopened':True,'active_scene':bpy.context.scene.name,'scenes':[s.name for s in bpy.data.scenes],'source_scene_object_count':len(source.objects),'source_scene_fingerprint_after_reopen':h.hexdigest(),'source_geometry_and_transforms_preserved':h.hexdigest()==preservation['source_scene_fingerprint_before'],'original_file_unchanged':hashlib.sha256(source_path.read_bytes()).hexdigest()==preservation['source_copy_sha256'],'new_part_count':len(bpy.data.collections['V2_PRINT_COUPONS__EXPORT_ONLY_THIS_COLLECTION'].objects),'expected_part_count':len(manifest),'all_objects_present':all(x['name'] in bpy.data.objects for x in manifest),'mm_display_units':bpy.context.scene.unit_settings.length_unit=='MILLIMETERS','render_exists':(OUT/'renders/fit-coupons-overview.png').exists()}
result['pass']=result['source_geometry_and_transforms_preserved'] and result['original_file_unchanged'] and result['all_objects_present'] and result['new_part_count']==len(manifest) and result['mm_display_units'] and result['render_exists']
(OUT/'reports/reopen-verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
print(json.dumps(result,ensure_ascii=False,indent=2));assert result['pass']
