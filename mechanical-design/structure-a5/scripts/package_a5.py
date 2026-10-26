"""Package A5 current geometry, independent STL verification and actual final renders."""
import json,csv,hashlib,zipfile
from pathlib import Path
OUT=Path(__file__).resolve().parents[1]
def read(n):return json.loads((OUT/'reports'/n).read_text())
checks={'静态装配':read('assembly-check.json')['collision_pass'],'原生31零件闭合连通':read('assembly-check.json')['topology_pass'],'31个毫米STL复读':read('stl-verification.json')['mesh_check_pass'],'5个试配件复读':read('coupon-verification.json')['mesh_check_pass'],'36组腿部离散姿态':read('leg-motion-sample-check.json')['pass'],'24个拆装检查位置':read('cover-service-check.json')['pass'],'J6充电USB-C插拔量规':read('connector-access-check.json')['nominal_usb_pass'],'屏幕接头对主板':read('connector-access-check.json')['screen_connector_to_pcb_pass'],'原文件保护':all(read('final-artifact-reopen.json')['protected_sources_unchanged'].values())}
assert all(checks.values()),checks
blend=OUT/'DesktopAssistant-整机结构-A5.blend';digest=hashlib.sha256(blend.read_bytes()).hexdigest()
assert digest==read('final-artifact-reopen.json')['sha256']
views=['perspective','front','rear','top','internal','lower-deck','exploded','front-open','parts']
for v in views:
 p=OUT/'renders'/('A5-'+v+'.png');assert p.exists() and p.stat().st_mtime>=blend.stat().st_mtime,v
manifest=read('complete-manifest.json')
with (OUT/'零件清单.csv').open('w',encoding='utf-8-sig',newline='') as f:
 w=csv.writer(f);w.writerow(['编号','名称','装机数量','STL文件','打印外包尺寸mm','建议方向','说明'])
 for r in manifest:w.writerow([r['id'],r['label_zh'],1,r['file'],' × '.join(str(round(x,2)) for x in r['dimensions_mm']),r['orientation'],r['note']])
for name in ['stl-verification.json','coupon-verification.json']:
 for r in read(name)['items']:assert hashlib.sha256((OUT/r['file']).read_bytes()).hexdigest()==r['sha256']
summary='# A5 CAD 试装验收摘要\n\n2026-09-14。实际模型、独立STL和最终图像已核对；尚无实物打印或负载测试。\n\n'
summary+='| 检查 | 结果 |\n|---|---|\n'+''.join('| '+k+' | 通过 |\n' for k in checks)
summary+='\n静态体积交集阈值0.05 mm³，腿部检查阈值0.1 mm³。每腿髋−15/0/+15°、膝−20/0/+20°；不代表连续行程、地面接触或四腿联动已验证。\n\n'
summary+='J6量规为14×15×8护套、8.4×6.5×2.6金属端；完全插入以及向外3/8/15 mm位置均无非配合碰撞。后盖17×11入口按护套留余量。实际连接器焊盘兼容及插口基准仍须实板验证。\n\n'
summary+='整机当前站姿宽×深×高：'+ ' × '.join(str(v) for v in read('dimensions.json')['standing_xyz_mm']) +' mm；机身124×112×76 mm。未计入外接线缆。\n\n'
summary+='托盘拆卸检查包含移除R18/UBEC后向右平移2 mm再上提的路径。主板、壳体拆卸和实际线束仍需按README操作。\n\n'
summary+='9张图均由最终Blender模型渲染。默认视口关闭相机/灯光辅助物和关系线。原A4、A3、PCB source和BOM未由本次脚本修改。\n\n'
summary+='Blender SHA-256：`'+digest+'`\n'
(OUT/'验收摘要.md').write_text(summary)
render_index={'blend_sha256':digest,'views':[{'view':v,'file':'renders/A5-'+v+'.png','sha256':hashlib.sha256((OUT/'renders'/('A5-'+v+'.png')).read_bytes()).hexdigest()} for v in views]}
(OUT/'reports/render-artifacts.json').write_text(json.dumps(render_index,ensure_ascii=False,indent=2))
files=[blend]+sorted(OUT.glob('*.md'))+sorted(OUT.glob('*.csv'))+sorted((OUT/'scripts').glob('*.py'))+sorted((OUT/'stl-complete').glob('*.stl'))+sorted((OUT/'coupons').glob('*.stl'))+sorted((OUT/'reports').glob('*.json'))+[OUT/'renders'/('A5-'+v+'.png') for v in views]
hashes={str(p.relative_to(OUT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
(OUT/'SHA256.json').write_text(json.dumps(hashes,ensure_ascii=False,indent=2));files.append(OUT/'SHA256.json')
package=OUT/'DesktopAssistant-A5-试装模型包.zip'
with zipfile.ZipFile(package,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
 for p in files:z.write(p,Path('DesktopAssistant-A5')/p.relative_to(OUT))
with zipfile.ZipFile(package) as z:
 assert z.testzip() is None
 for rel,h in hashes.items():assert hashlib.sha256(z.read('DesktopAssistant-A5/'+rel)).hexdigest()==h
print('PACKAGED',len(files),'files',round(package.stat().st_size/1024/1024,2),'MB')
