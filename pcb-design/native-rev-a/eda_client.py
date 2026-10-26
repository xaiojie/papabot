"""Project-scoped client for the official easyeda-api bridge."""
import json
import time
from pathlib import Path
import urllib.request
import urllib.error

ROOT = Path(__file__).resolve().parent
PROJECT_ID = 'e5e438419c1c4681946d5009bb8d6daf'
WINDOW_ID = '0a44f0d1-b04c-42dd-92da-e9fd1a6db543'
PORT = 49620


def execute(code, label='inspect', guarded=True):
    if guarded:
        code = 'const taskProject = await eda.dmt_Project.getCurrentProjectInfo(); if (!taskProject || taskProject.uuid !== ' + json.dumps(PROJECT_ID) + ') throw new Error("DesktopAssistant project guard mismatch");\n' + code
    payload = {'code': code, 'windowId': WINDOW_ID}
    audit = ROOT / 'audit'
    audit.mkdir(exist_ok=True)
    prefix = f'{time.time_ns()}-{label}'
    (audit / f'{prefix}.js').write_text(code)
    request = urllib.request.Request(f'http://127.0.0.1:{PORT}/execute',data=json.dumps(payload).encode(),headers={'Content-Type':'application/json'})
    try:
        with urllib.request.urlopen(request,timeout=40) as r:
            result = json.load(r)
    except urllib.error.HTTPError as e:
        result = json.loads(e.read())
    (audit / f'{prefix}.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
    if not result.get('success'):
        raise RuntimeError(result)
    return result.get('result')


if __name__ == '__main__':
    import sys
    print(json.dumps(execute(Path(sys.argv[1]).read_text(),Path(sys.argv[1]).stem),ensure_ascii=False,indent=2))
