import json,zipfile
from eda_client import execute,ROOT
with zipfile.ZipFile(ROOT/'generated/Integrated_five_sheets.epro2') as z:
 assert z.testzip() is None
 s=z.read('DesktopAssistant_Integrated.epru').decode()
 assert 'VBAT_RAW_N' in s and 'BAL1_VDD' in s
pp=ROOT/'generated/pages.json';pages=json.load(open(pp));old=pages['01']
new=execute('return await eda.dmt_Schematic.createSchematicPage("6c93ab84d69093e6");','create-fresh-battery-page')
assert new
(ROOT/'generated/replaced-page.json').write_text(json.dumps({'old':old,'new':new}))
print('fresh',new,flush=True)
print('remove cached old page',execute('return await eda.dmt_Schematic.deleteSchematicPage('+json.dumps(old)+');','remove-backed-up-stale-page'),flush=True)
pages['01']=new;pp.write_text(json.dumps(pages,indent=2))
