"""Reopen final artifact, verify nominal connector access and record mass assumptions."""
from pathlib import Path
src=Path(__file__).with_name('check_a4.py').read_text()
exec(compile(src[:src.index("if '--motion' in sys.argv:")],__file__,'exec'))
import hashlib
def gauge(name,d,loc):
 bpy.ops.mesh.primitive_cube_add(size=1,location=Vector(loc)*M);o=bpy.context.object;o.name=name;o.dimensions=Vector(d)*M
 bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);return o
body=gauge('CHECK_USB_PLUG_BODY',(15,14,8),(46,46,79.8))
metal=gauge('CHECK_USB_PLUG_METAL',(6.5,8.4,2.6),(35.25,46,79.8))
fixed=[o for o in parts+refs if o.name not in ['REF__PCB_J6']]
plug_tests=[]
for delta in [0,3,8,15]:
 body.location.x=(46+delta)*M;metal.location.x=(35.25+delta)*M;bpy.context.view_layer.update()
 bad,cnt=pairs_check(list(itertools.product([body,metal],fixed)))
 plug_tests.append({'outward_from_mated_mm':delta,'conflicts':bad,'tested_pairs':cnt})
for o in [body,metal]:bpy.data.objects.remove(o,do_unlink=True)
screen=scene.objects['REF__SCREEN_CN1_10PIN_AND_LOW_PROFILE_PLUG']
bad,cnt=pairs_check([(screen,o) for o in refs if o.name.startswith(('REF__PCB_','REF__ESP32'))])
report={'nominal_usb_pass':not any(r['conflicts'] for r in plug_tests),'usb_tests':plug_tests,'usb_body_xyz':[15,14,8],'usb_metal_xyz':[6.5,8.4,2.6],'mating_exception':'Metal tongue to REF__PCB_J6 is intended mating; exact C165948 footprint and mouth datum still require supplier/received-part check.','screen_connector_to_pcb_pass':not bad,'screen_conflicts':bad,'screen_connector_depth_mm':7.7,'screen_connector_to_board_front_gap_mm':1.1,'limits':['Connector check applies only to these explicit nominal gauges.','Screen female housing may need a low-profile or right-angle solution; common long Dupont ends are not approved by this gauge.','Real plug insertion force, cable bend radius and tolerances not measured.']}
(OUT/'reports/connector-access-check.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))

# Geometric material centroid with a solid PETG mass upper bound, not print-weight prediction.
def centroid_volume(o):
 me=o.data.copy();bm=bmesh.new();bm.from_mesh(me);bmesh.ops.triangulate(bm,faces=bm.faces);bm.to_mesh(me);bm.free();me.calc_loop_triangles()
 vtot=0;c=Vector((0,0,0))
 for tri in me.loop_triangles:
  a,b,d=[o.matrix_world@me.vertices[i].co/M for i in tri.vertices];v=a.dot(b.cross(d))/6;vtot+=v;c+=(a+b+d)/4*v
 bpy.data.meshes.remove(me);return abs(vtot),c/vtot
part_mass=[]
for o in parts:
 vol,c=centroid_volume(o);part_mass.append({'id':o['part_id'],'solid_PETG_g_at_1p27':vol*.00127,'centroid_mm':list(c)})
assumed=[('PCB incl components',55,[0,4,82]),('ESP32',10,[-10,-4.89,90]),('screen',11,[0,-61,76]),('ACE800',55,[-10,-15,46.1]),('DFR0753',20,[0,35,42.8]),('UBEC',13,[28.5,-16,41.3]),('speaker',10,[-15,58.1,55]),('switch',8,[16,48.8,65]),('amp',5,[17,53.8,90]),('wire and fasteners',35,[0,0,60])]
for leg in ['FL','FR','RL','RR']:
 for typ in ['HIP','KNEE']:
  o=scene.objects['REF__'+leg+'_'+typ+'_CASE'];lo,hi=bounds(o);assumed.append((leg+' '+typ+' MG90S',13.4,list((lo+hi)/2)))
scenarios=[]
for factor in [.55,1.0]:
 weighted=[(r['solid_PETG_g_at_1p27']*factor,Vector(r['centroid_mm'])) for r in part_mass]+[(m,Vector(c)) for _,m,c in assumed]
 total=sum(m for m,c in weighted);com=sum((m*c for m,c in weighted),Vector())/total
 scenarios.append({'print_mass_fraction_of_solid':factor,'assumed_total_mass_g':round(total,1),'estimated_com_mm':[round(x,2) for x in com],'static_projection_margin_to_foot_center_rectangle_mm':round(min(79.2-abs(com.x),67.5-abs(com.y)),2)})
(OUT/'reports/mass-and-support-estimate.json').write_text(json.dumps({'status':'ASSUMPTION_SENSITIVITY_ONLY_NOT_PHYSICAL_STABILITY_TEST','foot_centers_xy':[[-79.2,-67.5],[79.2,-67.5],[-79.2,67.5],[79.2,67.5]],'nominal_solid_material_density_g_cm3':1.27,'part_solid_masses':part_mass,'hardware_assumptions':[{'name':n,'mass_g':m,'center_mm':c} for n,m,c in assumed],'scenarios':scenarios,'limits':['Only screen 11g is read from supplied PDF; other weights are provisional engineering assumptions.','55 percent effective print mass is not a slicer result.','Static support projection does not prove adequate torque, stability while walking, traction or battery run time.']},ensure_ascii=False,indent=2))

protected=json.loads((OUT/'reports/source-and-change-scope.json').read_text())
root=OUT.parents[1]
preserved={p:hashlib.sha256((root/p).read_bytes()).hexdigest()==h for p,h in protected['protected_sha256'].items()}
reopen={'file':str(OUT/'DesktopAssistant-整机结构-A4.blend'),'sha256':hashlib.sha256((OUT/'DesktopAssistant-整机结构-A4.blend').read_bytes()).hexdigest(),'opened_with':'Blender 5.2.1 LTS --background --disable-autoexec','main_scene':scene.name,'available_scenes':list(bpy.data.scenes.keys()),'main_print_count':len(parts),'texture_packed':all(im.packed_file is not None for im in bpy.data.images if im.name=='User_latest_Gerber_Top.png'),'protected_sources_unchanged':preserved,'physical_tested':False}
(OUT/'reports/final-artifact-reopen.json').write_text(json.dumps(reopen,ensure_ascii=False,indent=2))
print('FINAL_AUDIT',report['nominal_usb_pass'],report['screen_connector_to_pcb_pass'],all(preserved.values()),flush=True)
