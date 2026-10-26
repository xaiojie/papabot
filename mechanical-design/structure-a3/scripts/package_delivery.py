"""Package only the current print set; verify each archive member after writing."""
import json, hashlib, zipfile, re
from pathlib import Path

OUT=Path(__file__).resolve().parents[1]
def read(name): return json.loads((OUT/'reports'/name).read_text())
stl=read('complete-stl-verification.json')
reopen=read('final-artifact-reopen.json')
assert stl['mesh_check_pass'] and len(stl['items'])==30
assert reopen['packed_file_reopened'] and reopen['all_closed']
assert not read('assembly-collision-check.json')['conflicts_over_0p05_mm3']
assert read('leg-motion-sample-check.json')['sampled_pose_checks_pass']
assert read('cover-service-check.json')['pass']
assert read('material-refresh-preservation.json')['print_geometry_unchanged']
assert read('presentation-preservation.json')['unchanged']
assert hashlib.sha256((OUT/'DesktopAssistant-整机结构-A3.blend').read_bytes()).hexdigest()==reopen['blend_sha256']
for part in stl['items']:
    assert hashlib.sha256((OUT/part['file']).read_bytes()).hexdigest()==part['sha256']
pres=read('complete-preservation.json')
assert pres['preserved']
assert hashlib.sha256((OUT.parent/'assembly-v1/desktop-assistant-assembly-v1.blend').read_bytes()).hexdigest()==pres['v1_sha256']
assert hashlib.sha256((OUT.parent/'print-v2/desktop-assistant-structure-a1.blend').read_bytes()).hexdigest()==pres['input_a1_sha256']

filenames=['DesktopAssistant-整机结构-A3.blend','README.md','零件清单.md','装配与打印说明.md','验证说明.md','设计修正说明.md',
           '紧固件安装明细.csv','紧固件与辅料核对.csv']
filenames += [p['file'] for p in stl['items']]
filenames += ['renders/A3-'+v+'.png' for v in ['front','perspective','front-open','rear','internal','exploded','parts']]
filenames += ['reports/'+v for v in ['complete-manifest.json','assembly-parameters.json',
    'complete-stl-verification.json','complete-reopen.json','assembly-collision-check.json',
    'leg-interfaces.json','leg-motion-sample-check.json','cover-service-check.json',
    'complete-preservation.json','presentation-preservation.json','material-refresh-preservation.json',
    'source-and-change-scope.json','final-artifact-reopen.json']]
assert len(filenames)==len(set(filenames))
for name in filenames: assert (OUT/name).is_file(),name
for name in filenames:
    if name.endswith('.md'):
        for target in re.findall(r'\]\(([^)]+)\)',(OUT/name).read_text()):
            if not target.startswith(('http:','https:','#')):
                assert (OUT/name).parent.joinpath(target).exists(),(name,target)
checks=[{'file':name,'bytes':(OUT/name).stat().st_size,'sha256':hashlib.sha256((OUT/name).read_bytes()).hexdigest()} for name in filenames]
delivery=OUT/'delivery';delivery.mkdir(exist_ok=True)
archive=delivery/'DesktopAssistant-A3-整机结构试装包.zip'
with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
    for name in filenames: z.write(OUT/name,'DesktopAssistant-A3/'+name)
    z.writestr('DesktopAssistant-A3/文件校验.json',json.dumps(checks,ensure_ascii=False,indent=2))
with zipfile.ZipFile(archive) as z:
    assert z.testzip() is None
    assert len([n for n in z.namelist() if n.endswith('.stl')])==30
    for r in checks:
        assert hashlib.sha256(z.read('DesktopAssistant-A3/'+r['file'])).hexdigest()==r['sha256']
result={'zip':str(archive.relative_to(OUT)),'bytes':archive.stat().st_size,
        'sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),'stl_count':30,
        'file_count':len(filenames)+1,'archive_crc_and_member_sha256_verified':True,
        'original_v1_a1_files_unchanged':True,'parts':[p['id'] for p in stl['items']],
        'physical_fit_tested':False}
(OUT/'reports/delivery-check.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
print(json.dumps(result,ensure_ascii=False,indent=2))
