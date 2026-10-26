import json,re,math
from pathlib import Path
out=Path(__file__).resolve().parent
s=(out/'native-critical.dsn').read_text()
# EasyEDA 3.2.149 exports numeric track layers but named structure layers.
s=s.replace('(path 1 ','(path TopLayer ').replace('(path 2 ','(path BottomLayer ')
# Match the native 2 oz profile: pad spacing 6 mil; track spacing 8 mil.
s=s.replace('(clear 8.04 (type default_smd))','(clear 6.1 (type default_smd))').replace('(clear 8.04 (type smd_smd))','(clear 6.1 (type smd_smd))')
# Native export represents forbidden regions as unconnected padstacks; keep them.
# Add explicit router keepouts for the antenna and all screw-head regions as well.
keep=[]
for layer in ['TopLayer','BottomLayer']:
 x1,x2=56.5/.0254,71.3/.0254;y1,y2=(75-10)/.0254,75/.0254
 keep.append(f'(keepout RF_{layer} (rect {layer} {x1:.4f} {y1:.4f} {x2:.4f} {y2:.4f}))')
 for i,(x,y) in enumerate([(4,4),(106,4),(4,71),(106,71)]):
  keep.append(f'(keepout MH{i}_{layer} (circle {layer} {5.6/.0254:.4f} {x/.0254:.4f} {(75-y)/.0254:.4f}))')
s=s.replace('    (layer BottomLayer\n      (type signal)\n    )', '    (layer BottomLayer\n      (type signal)\n    )\n    '+'\n    '.join(keep), 1)
(out/'routing-input.dsn').write_text(s)
print('Prepared',len(s),'bytes')
