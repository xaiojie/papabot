import sys,json
from pathlib import Path
P=Path(__file__).resolve().parent;F=P.parent/'final-no-encoder-2026-09-12';sys.path.insert(0,str(P.parent/'repair-2026-09-12'));from eda_client import execute
print(execute('return await eda.dmt_EditorControl.openDocument("2f4bfc0bfa3d836a");','no-encoder-pdf-open'))
r=execute('const d=await eda.dmt_SelectControl.getCurrentDocumentInfo();if(d.uuid!=="2f4bfc0bfa3d836a")throw Error("wrong sheet");const f=await eda.sch_ManufactureData.getExportDocumentFile("Integrated_schematic_final","PDF",undefined,"Current Schematic",{outputMethod:"Merged sheet"});return {name:f.name,bytes:Array.from(new Uint8Array(await f.arrayBuffer()))};','no-encoder-pdf-export');(F/'Integrated_schematic_final.pdf').write_bytes(bytes(r['bytes']));print(r['name'],len(r['bytes']))
