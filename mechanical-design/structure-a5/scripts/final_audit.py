"""Reopen A5 and verify charging port against the rotated PCB, plus saved view state."""
from pathlib import Path
src=Path(__file__).with_name('check_a5.py').read_text()
exec(compile(src[:src.index("if '--motion' in sys.argv:")],__file__,'exec'))
import hashlib

def gauge(name,d,loc):
 bpy.ops.mesh.primitive_cube_add(size=1,location=Vector(loc)*M);o=bpy.context.object;o.name=name;o.dimensions=Vector(d)*M
 bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);return o
body=gauge('CHECK_USB_PLUG_BODY',(14,15,8),(-42,50,83.8))
metal=gauge('CHECK_USB_PLUG_METAL',(8.4,6.5,2.6),(-42,39.25,83.8))
fixed=[o for o in parts+refs if o.name!='REF__PCB_J6']
tests=[]
for delta in [0,3,8,15]:
 body.location.y=(50+delta)*M;metal.location.y=(39.25+delta)*M;bpy.context.view_layer.update()
 bad,cnt=pairs_check(list(itertools.product([body,metal],fixed)))
 tests.append({'outward_from_mated_mm':delta,'conflicts':bad,'tested_pairs':cnt})
for o in [body,metal]:bpy.data.objects.remove(o,do_unlink=True)
screen=scene.objects['REF__SCREEN_CN1_10PIN_AND_LOW_PROFILE_PLUG']
bad,cnt=pairs_check([(screen,o) for o in refs if o.name.startswith(('REF__PCB_','REF__ESP32'))])
report={'nominal_usb_pass':not any(t['conflicts'] for t in tests),'usb_tests':tests,'usb_body_xyz':[14,15,8],'usb_metal_xyz':[8.4,6.5,2.6],'port_center_xz_mm':[-42,83.8],'rear_panel_y_mm':56,'insertion_axis':'Y','opening_xz_mm':[17,11],'clearance_per_side_mm':[1.5,1.5],'connector':'J6 charging 5V VBUS, not ESP32 programming USB','mating_exception':'Metal tongue mating with J6 excluded. C165948 exact footprint/mouth datum still requires received-part verification.','screen_connector_to_pcb_pass':not bad,'screen_conflicts':bad,'screen_connector_depth_mm':7.7,'screen_connector_to_board_front_gap_mm':8.6,'limits':['Nominal insertion gauges, no physical cable or plug force test.','HS24 low profile/right angle header remains required.','USB-C footprint compatibility is not proven by enclosure clearance.']}
(OUT/'reports/connector-access-check.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
visible=[o for o in scene.objects if o.type=='MESH' and not o.hide_render and o.name!='A5_studio_floor']
points=[o.matrix_world@v.co/M for o in visible for v in o.data.vertices]
lo=Vector([min(p[i] for p in points) for i in range(3)]);hi=Vector([max(p[i] for p in points) for i in range(3)])
meas={'body_xyz_mm':[124,112,76],'standing_xyz_mm':[round(v,3) for v in hi-lo],'min_xyz_mm':list(lo),'max_xyz_mm':list(hi),'pose':'saved neutral standing pose; includes pads and ears, excludes external cable','pcb_transform':'X=u-55; Y=v-33.5; Z=80.5+w','pcb_mm':[110,75,1.6],'pcb_bottom_z_mm':80.5,'pcb_hole_pitch_xy_mm':[102,67],'a4_body_xyz_mm':[94,132,76],'a4_standing_xyz_mm':[174.9,154.75,122.46]}
(OUT/'reports/dimensions.json').write_text(json.dumps(meas,ensure_ascii=False,indent=2))
protected=json.loads((OUT/'reports/source-and-change-scope.json').read_text());root=OUT.parents[1]
preserved={p:hashlib.sha256((root/p).read_bytes()).hexdigest()==h for p,h in protected['protected_sha256'].items()}
view=[]
for scr in bpy.data.screens:
 for ar in scr.areas:
  if ar.type=='VIEW_3D':view.append({'screen':scr.name,'extras':ar.spaces.active.overlay.show_extras,'relationship_lines':ar.spaces.active.overlay.show_relationship_lines})
reopen={'file':str(OUT/'DesktopAssistant-整机结构-A5.blend'),'sha256':hashlib.sha256((OUT/'DesktopAssistant-整机结构-A5.blend').read_bytes()).hexdigest(),'opened_with':'Blender 5.2.1 LTS --background --disable-autoexec','main_scene':scene.name,'available_scenes':list(bpy.data.scenes.keys()),'main_print_count':len(parts),'texture_packed':all(im.packed_file is not None for im in bpy.data.images if im.name=='User_latest_Gerber_Top.png'),'protected_sources_unchanged':preserved,'saved_viewport':view,'physical_tested':False}
(OUT/'reports/final-artifact-reopen.json').write_text(json.dumps(reopen,ensure_ascii=False,indent=2))
print('FINAL_AUDIT',report['nominal_usb_pass'],report['screen_connector_to_pcb_pass'],all(preserved.values()),flush=True)
print(json.dumps(meas,ensure_ascii=False),flush=True)
