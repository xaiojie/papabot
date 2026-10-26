import bpy,json,sys
from pathlib import Path
OUT=Path(__file__).resolve().parents[1]
bpy.ops.wm.open_mainfile(filepath=str(OUT/'DesktopAssistant-整机结构-A5.blend'))
views=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else ['perspective','front','rear','internal','lower-deck','exploded','front-open','parts']
mapping={'internal':'21_A5_INTERNAL','lower-deck':'22_A5_LOWER_DECK','exploded':'23_A5_EXPLODED','front-open':'24_A5_FRONT_REMOVED','parts':'25_A5_PRINT_PARTS'}
for name in views:
 sc=bpy.data.scenes[mapping.get(name,'20_A5_COMPLETE_ASSEMBLY')];bpy.context.window.scene=sc
 if name not in mapping:
  sc.camera=bpy.data.objects['A5_'+name+'_camera'];sc.objects['A5_studio_floor'].hide_render=(name=='front')
 sc.render.filepath=str(OUT/'renders'/('A5-'+name+'.png'));bpy.ops.render.render(write_still=True)
 print('RENDER_DONE',name,flush=True)
