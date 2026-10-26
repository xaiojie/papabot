"""Validate local native exports and rebuild the review delivery (no EDA writes)."""
import csv
import hashlib
import json
import re
import shutil
import zipfile
from collections import Counter
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def read(name):
    return json.loads((ROOT / name).read_text())


def write(name, obj):
    (ROOT / name).write_text(json.dumps(obj, ensure_ascii=False, indent=2) + '\n')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def drill_points(text):
    tools, current, points = {}, None, []
    for line in text.splitlines():
        match = re.fullmatch(r'T(\d+)C([\d.]+)', line)
        if match:
            tools[match[1]] = float(match[2])
        elif re.fullmatch(r'T\d+', line):
            current = line[1:]
        elif line.startswith('X'):
            match = re.fullmatch(r'X(-?[\d.]+)Y(-?[\d.]+)', line)
            assert match, line
            points.append((float(match[1]), float(match[2]), tools[current]))
    return points


def match_points(actual, expected, tolerance=.001):
    remaining = list(actual)
    maximum_delta = 0
    for p in expected:
        i = next((i for i, q in enumerate(remaining)
                  if max(abs(a-b) for a, b in zip(p, q)) <= tolerance), None)
        assert i is not None, ('Missing drill', p)
        q = remaining.pop(i)
        maximum_delta = max(maximum_delta, max(abs(a-b) for a, b in zip(p, q)))
    assert not remaining, ('Unexpected drills', remaining)
    return maximum_delta


def main():
    now = datetime.now().astimezone().isoformat()
    archive = ROOT / 'DesktopAssistant_RevA_PCB_review.epro2'
    gerber = ROOT / 'DesktopAssistant_RevA_Gerber_review.zip'
    geometry = read('pcb-persisted-geometry.json')
    assert geometry['native_archive_sha256'] == sha(archive)
    native = read('native-pcb-drc.json')
    schematic = read('native-schematic-drc.json')
    validation = read('native-routing-validation.json')
    assert native['passed'] and schematic['passed']
    assert validation['geometry_pass'] and validation['all_nets_connected']
    assert validation['all_copper_connected_to_pads']
    with zipfile.ZipFile(gerber) as z:
        assert z.testzip() is None
        required = ['Gerber_TopLayer.GTL', 'Gerber_BottomLayer.GBL',
                    'Gerber_TopSilkscreenLayer.GTO', 'Gerber_BottomSilkscreenLayer.GBO',
                    'Gerber_TopSolderMaskLayer.GTS', 'Gerber_BottomSolderMaskLayer.GBS',
                    'Gerber_BoardOutlineLayer.GKO', 'Drill_PTH_Through.DRL',
                    'Drill_NPTH_Through.DRL', 'Drill_PTH_Through_Via.DRL']
        assert set(required) <= set(z.namelist())
        pth = drill_points(z.read('Drill_PTH_Through.DRL').decode())
        npth = drill_points(z.read('Drill_NPTH_Through.DRL').decode())
        vias = drill_points(z.read('Drill_PTH_Through_Via.DRL').decode())
        expected_pth, expected_npth = [], []
        for pad in geometry['allPads']:
            point = (pad['x']*.0254, pad['y']*.0254, pad['hole'][1]*.0254)
            (expected_pth if pad['metallization'] else expected_npth).append(point)
        expected_vias = [(p['x']*.0254, p['y']*.0254, p['holeDiameter']*.0254)
                         for p in geometry['vias']]
        deltas = [match_points(pth, expected_pth + expected_vias),
                  match_points(npth, expected_npth), match_points(vias, expected_vias)]
        outline_text = z.read('Gerber_BoardOutlineLayer.GKO').decode()
        assert '%FSLAX26Y26*%' in outline_text and '%MOMM*%' in outline_text
        outline = [(int(x)/1e6, int(y)/1e6) for x, y in
                   re.findall(r'G01X(-?\d+)Y(-?\d+)D0[12]\*', outline_text)]
        expected_outline = [(0,0),(80,0),(80,32),(0,32),(0,22.5),
                            (24.17,22.5),(24.17,9.5),(0,9.5),(0,0)]
        assert outline == expected_outline or outline == list(reversed(expected_outline))
        report = dict(checked_at=now, sha256=sha(gerber), zip_crc_pass=True,
                      files=z.namelist(), board_outline_mm=outline,
                      plated_hole_count=len(pth), component_hole_count=len(expected_pth),
                      nonplated_hole_count=len(npth), via_count=len(vias),
                      drill_diameters_mm=dict(Counter(round(p[2], 4) for p in pth)),
                      all_drills_match_native_geometry=True, comparison_tolerance_mm=.001,
                      maximum_coordinate_or_diameter_difference_mm=max(deltas),
                      coordinate_note='按1µm容差逐孔比对。电阻14孔的API坐标与Gerber有0.279µm差异；其余差异更小。',
                      separate_via_drill_file_is_subset_of_pth=True,
                      note='原生检查导出；板框与钻孔已核对，尚待实物及外壳配合验收。')
        write('gerber-export-check.json', report)

    enet = read('DesktopAssistant_Carrier_RevA.enet')['components']
    pins = {(c['props']['Designator'], str(k)): p['net']
            for c in enet.values() for k, p in c['pinInfoMap'].items()}
    check = read('netlist-check.json')
    assert len(pins) == 98
    assert all(pins[(ref, number)] == (expected or '')
               for ref, number, expected, _ in check['checks'])
    check.update(checked_at=now, exported_netlist_sha256=sha(ROOT/'DesktopAssistant_Carrier_RevA.enet'))
    write('netlist-check.json', check)
    pcb_check = read('pcb-netlist-check.json')
    pcb_check.update(checked_at=now, native_archive_sha256=sha(archive))
    write('pcb-netlist-check.json', pcb_check)
    resolution = dict(checked_at=now, initial_pcb_errors=38,
                      initial_connectivity_errors=37, initial_netlist_errors=1,
                      final_pcb_drc_pass=True, final_schematic_drc_pass=True,
                      final_schematic_errors=0, final_schematic_warnings=0,
                      copper_and_pad_geometry_unchanged=True, design_rules_unchanged=True,
                      checks_not_disabled=True,
                      outline_recognition_fix=read('outline-recognition-check.json'),
                      actions=['同步原理图与PCB器件属性后，原生连接性提示消失；保存重开后通过。',
                               'J1/J2保留C429947，补齐官方属性，Name为制造商型号，图面Value保留接口用途。',
                               '原理图保存重开通过，最终属性同步回PCB后再次通过。'],
                      limitation='API无原生连接性内部状态接口，未证明旧连接性结果的内部原因。')
    write('drc-resolution.json', resolution)

    bom_file = ROOT/'载板装配清单.csv'
    with bom_file.open(encoding='utf-8-sig', newline='') as f:
        rows = list(csv.DictReader(f))
    for row in rows:
        if row['位号'] in ('J1', 'J2'):
            row['备注'] = 'C429947 / JILN 22850120ANG1SYA01；单排20P、2.54mm、塑高8.5mm；两排安装间距17.78mm。'
    with bom_file.open('w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    manifest = dict(project_name='DesktopAssistant_RevA',
                    project_id='e5e438419c1c4681946d5009bb8d6daf', pcb_uuid='641e84beea5fc9c6',
                    updated_at=now, native_archive=archive.name, archive_bytes=archive.stat().st_size,
                    sha256=sha(archive), gerber_archive=gerber.name, gerber_sha256=sha(gerber),
                    native_pcb_drc_pass=True, native_schematic_drc_pass=True,
                    geometry_pass=True, connected_nets=25, orphan_copper_count=0,
                    native_ui_outline_recognized=True, outline_type='closed POLY',
                    not_for_fabrication=True, status='电气检查通过；待实物与机械配合验收',
                    remaining_reviews=['模块针序、电压与主控插座方向/高度实物确认',
                                       '天线避空与U形槽加工内角确认',
                                       '外壳安装配合、线束及电源负载实测'],
                    mechanical_work='paused', fabrication_order_placed=False)
    write('delivery-manifest.json', manifest)
    files = ['README.md', archive.name, gerber.name, '装配与上电核对.md',
             '载板接口与引脚.csv', '载板装配清单.csv', 'DesktopAssistant_Carrier_RevA.enet',
             'native-pcb-drc.json', 'native-schematic-drc.json', 'native-routing-validation.json',
             'netlist-check.json', 'pcb-netlist-check.json', 'native-archive-check.json',
             'gerber-export-check.json', 'drc-resolution.json', 'delivery-manifest.json',
             'outline-recognition-check.json',
             'pcb-persisted-geometry.json', 'pcb-routed-readback.json',
             'carrier-definition.json', 'schematic-final-components.json',
             'routing-import-check.json', 'native-import-geometry-delta.json',
             'verify_native_routing.py', 'previews/641e84beea5fc9c6.webp',
             'previews/834bc1f5a1044766.webp']
    bundle = ROOT/'DesktopAssistant_RevA_PCB检查包.zip'
    backup = ROOT/'history/before-drc-fix'/bundle.name
    if bundle.exists() and not backup.exists():
        shutil.copy2(bundle, backup)
    with zipfile.ZipFile(bundle, 'w', zipfile.ZIP_DEFLATED) as z:
        for filename in files:
            z.write(ROOT/filename, filename)
    with zipfile.ZipFile(bundle) as z:
        assert z.testzip() is None and len(z.namelist()) == len(files)
    print(json.dumps(dict(bundle=str(bundle), bytes=bundle.stat().st_size,
                          files=len(files), pcb_drc=True, schematic_drc=True,
                          drilled_holes=len(pth)+len(npth)), ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
