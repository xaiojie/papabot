import bpy,json,sys
from pathlib import Path
OUT=Path(__file__).resolve().parents[1]
bpy.ops.wm.open_mainfile(filepath=str(OUT/'DesktopAssistant-整机结构-A4.blend'))
views=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else ['perspective','front','rear','internal','lower-deck','exploded','front-open','parts']
mapping={'internal':'21_A4_INTERNAL','lower-deck':'22_A4_LOWER_DECK','exploded':'23_A4_EXPLODED','front-open':'24_A4_FRONT_REMOVED','parts':'25_A4_PRINT_PARTS'}
for name in views:
 sc=bpy.data.scenes[mapping.get(name,'20_A4_COMPLETE_ASSEMBLY')];bpy.context.window.scene=sc
 if name not in mapping:
  sc.camera=bpy.data.objects['A4_'+name+'_camera'];sc.objects['A4_studio_floor'].hide_render=(name=='front')
 sc.render.filepath=str(OUT/'renders'/('A4-'+name+'.png'));bpy.ops.render.render(write_still=True)
 print('RENDER_DONE',name,flush=True)
