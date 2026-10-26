"""Package only current checked deliverables, with hashes and matching render timestamps."""
import json,csv,hashlib,zipfile
from pathlib import Path
OUT=Path(__file__).resolve().parents[1]
def read(n):return json.loads((OUT/'reports'/n).read_text())
checks={
 '静态装配':read('assembly-check.json')['collision_pass'],
 '原生零件闭合连通':read('assembly-check.json')['topology_pass'],
 '31个毫米STL':read('stl-verification.json')['mesh_check_pass'],
 '5个试配件':read('coupon-verification.json')['mesh_check_pass'],
 '36组腿部离散姿态':read('leg-motion-sample-check.json')['pass'],
 '23个拆装位置':read('cover-service-check.json')['pass'],
 'USB插拔量规':read('connector-access-check.json')['nominal_usb_pass'],
 '屏幕接头对主板':read('connector-access-check.json')['screen_connector_to_pcb_pass'],
 '原文件保护':all(read('final-artifact-reopen.json')['protected_sources_unchanged'].values()),
}
assert all(checks.values()),checks
blend=OUT/'DesktopAssistant-整机结构-A4.blend';digest=hashlib.sha256(blend.read_bytes()).hexdigest()
assert digest==read('final-artifact-reopen.json')['sha256']
views=['perspective','front','rear','internal','lower-deck','exploded','front-open','parts']
for view in views:
 p=OUT/'renders'/('A4-'+view+'.png');assert p.exists() and p.stat().st_mtime>=blend.stat().st_mtime,view
manifest=read('complete-manifest.json')
with (OUT/'零件清单.csv').open('w',encoding='utf-8-sig',newline='') as f:
 w=csv.writer(f);w.writerow(['编号','名称','装机数量','STL文件','打印外包尺寸mm','建议方向','说明'])
 for r in manifest:w.writerow([r['id'],r['label_zh'],1,r['file'],' × '.join(str(round(x,2)) for x in r['dimensions_mm']),r['orientation'],r['note']])
for name in ['stl-verification.json','coupon-verification.json']:
 for r in read(name)['items']:assert hashlib.sha256((OUT/r['file']).read_bytes()).hexdigest()==r['sha256']
summary='# A4 CAD 试装版本验收摘要\n\n日期：2026-09-14。原生文件重新打开、几何检查和导出验证完成；未进行实物打印或负载测试。\n\n'
summary+='| 检查 | 本次结果 |\n|---|---|\n'+''.join('| '+k+' | 通过 |\n' for k in checks)
summary+='| 最终图像 | 8张，与最终原生文件对应 |\n\n'
summary+='静态交集阈值0.05 mm³；腿部离散检查阈值0.1 mm³。腿部每条检查髋−15/0/+15°和膝−20/0/+20°的9种组合，共36组；不表示整个连续行程、同时步态或地面接触已验证。拆装需按README的断线、拆盖、拆主板顺序。\n\n'
summary+='USB检查仅适用于15×14×8 mm护套及6.5×8.4×2.6 mm金属端量规，检查装入及向外3/8/15 mm位置。J6金属端的正常插接重合排除，采购连接器与PCB焊盘兼容仍待核实。屏幕接头使用7.7 mm深包络，与主板前边相隔1.1 mm，不能直接换成长母头。\n\n'
summary+='原生文件：`DesktopAssistant-整机结构-A4.blend`\n\nSHA-256：`'+digest+'`\n\n'
summary+='原A3、用户最新版PCB source、最新BOM总表的哈希前后相同。主板纹理已打包到Blender文件。\n\n'
summary+='质量和重心仅为明示假设下的估算，详见`reports/mass-and-support-estimate.json`；未据此批准舵机扭矩或整机承重。屏幕、舵机、开关、降压、电池等实际配合以试配结果为准。\n'
(OUT/'验收摘要.md').write_text(summary)
render_index={'blend_sha256':digest,'views':[],'visual_review':'See visual-review.json for manual image inspection.'}
for v in views:
 p=OUT/'renders'/('A4-'+v+'.png');render_index['views'].append({'view':v,'file':str(p.relative_to(OUT)),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
(OUT/'reports/render-artifacts.json').write_text(json.dumps(render_index,ensure_ascii=False,indent=2))
files=[blend]+sorted(OUT.glob('*.md'))+sorted(OUT.glob('*.csv'))+sorted((OUT/'scripts').glob('*.py'))+sorted((OUT/'stl-complete').glob('*.stl'))+sorted((OUT/'coupons').glob('*.stl'))+sorted((OUT/'reports').glob('*.json'))+[OUT/'renders'/('A4-'+v+'.png') for v in views]
hashlist={str(p.relative_to(OUT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
(OUT/'SHA256.json').write_text(json.dumps(hashlist,ensure_ascii=False,indent=2));files.append(OUT/'SHA256.json')
package=OUT/'DesktopAssistant-A4-试装模型包.zip'
with zipfile.ZipFile(package,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
 for p in files:z.write(p,Path('DesktopAssistant-A4')/p.relative_to(OUT))
with zipfile.ZipFile(package) as z:
 assert z.testzip() is None
 for rel,h in hashlist.items():assert hashlib.sha256(z.read('DesktopAssistant-A4/'+rel)).hexdigest()==h
print('PACKAGED',package,len(files),'files',round(package.stat().st_size/1024/1024,2),'MB')
