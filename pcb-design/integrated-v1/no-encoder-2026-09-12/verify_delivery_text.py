"""Read-only validation of normalized EDA and PDF deliverables."""
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
import copy
import hashlib
import json
import zipfile
from pypdf import PdfReader
from pypdf.generic import ContentStream, NameObject

WORK = Path(__file__).resolve().parent
FINAL = WORK.parent / 'final-no-encoder-2026-09-12'
report = json.loads((FINAL / 'Export_text_normalization.json').read_text())

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

archive = FINAL / 'DesktopAssistant_Integrated_final.epro2'
before_archive = WORK / 'Native_export_before_text_normalization.epro2'
assert sha(archive) == report['native_archive_after_sha256']
assert sha(before_archive) == report['native_archive_before_sha256']
removed_keys = {(r['doc'], r['id']): r['text'] for r in report['removed_native_text_records']}
removed_count = 0
with zipfile.ZipFile(before_archive) as before, zipfile.ZipFile(archive) as after:
    assert before.testzip() is None and after.testzip() is None
    assert before.namelist() == after.namelist()
    for name in before.namelist():
        original, revised = before.read(name), after.read(name)
        if name != 'DesktopAssistant_Integrated.epru':
            assert original == revised, name
            continue
        kept = []
        doc = None
        for line in original.decode().splitlines():
            if '||' in line:
                header, payload = line.split('||', 1)
                header = json.loads(header)
                value = json.loads(payload.rstrip('|')) if payload.rstrip('|') else ''
                if header['type'] == 'DOCHEAD':
                    doc = value.get('uuid')
                key = (doc, header.get('id'))
                if header['type'] == 'TEXT' and key in removed_keys:
                    assert value['value'] == removed_keys[key]
                    removed_count += 1
                    continue
            kept.append(line)
        assert ('\n'.join(kept) + '\n').encode() == revised
assert removed_count == 8

pdf = FINAL / 'Integrated_schematic_final.pdf'
before_pdf = WORK / 'Native_PDF_before_text_normalization.pdf'
assert sha(pdf) == report['pdf_after_sha256']
assert sha(before_pdf) == report['pdf_before_sha256']
old, new = PdfReader(before_pdf), PdfReader(pdf)
assert len(old.pages) == len(new.pages) == 5
removed_pdf = []
expected = {(r['page'], r['text']) for r in report['removed_pdf_text_objects']}
for index, (opage, npage) in enumerate(zip(old.pages, new.pages), 1):
    ops = ContentStream(opage.get_contents(), old).operations
    kept, i = [], 0
    while i < len(ops):
        if ops[i][1] != b'BT':
            kept.append(ops[i])
            i += 1
            continue
        j = i + 1
        while ops[j][1] != b'ET':
            j += 1
        block = ops[i:j+1]
        stream = ContentStream(None, old)
        stream.operations = block
        probe = copy.copy(opage)
        probe[NameObject('/Contents')] = stream
        text = probe.extract_text()
        if (index, text) in expected:
            removed_pdf.append((index, text))
        else:
            kept.extend(block)
        i = j + 1
    # Compare the exact serialized stream used by the export correction. Parsing
    # pypdf's 8-decimal FloatObject serialization can change Python float equality.
    expected_stream = ContentStream(None, old)
    expected_stream.operations = kept
    assert expected_stream.get_data() == npage.get_contents().get_data(), index
    text = npage.extract_text()
    assert text.count('Revision 1.2') == 1
    assert 'Revision 1.1' not in text and 'EC11 controls' not in text
assert len(removed_pdf) == 8 and set(removed_pdf) == expected

result = {
    'passed': True,
    'checked_at': datetime.now(ZoneInfo('Asia/Shanghai')).isoformat(),
    'archive_sha256': sha(archive),
    'pdf_sha256': sha(pdf),
    'native_records_removed': removed_count,
    'native_changes_are_exactly_the_eight_documented_TEXT_removals': True,
    'all_electrical_and_PCB_records_byte_identical_to_pre_normalized_export': True,
    'all_other_archive_payloads_byte_identical': True,
    'pdf_pages': 5,
    'pdf_text_objects_removed': len(removed_pdf),
    'pdf_content_streams_match_exact_serialization_after_eight_text_removals': True,
    'each_page_has_one_revision_1_2_label_and_no_obsolete_revision': True,
}
(FINAL / 'Delivery_text_verification.json').write_text(json.dumps(result, ensure_ascii=False, indent=2))
print(json.dumps(result, ensure_ascii=False, indent=2))
