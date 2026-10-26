"""Call the local EDA adapter. JSON params come from a file or stdin."""
import json
from pathlib import Path
import sys
import urllib.request
import urllib.error

ROOT = Path(__file__).resolve().parent


def call(method, params=None):
    request = urllib.request.Request(
        "http://127.0.0.1:49640/rpc",
        data=json.dumps({"method": method, "params": params or {}}).encode(),
        headers={"Content-Type": "application/json", "Authorization": "Bearer " + (ROOT / ".local-key").read_text().strip()},
    )
    try:
        with urllib.request.urlopen(request, timeout=150) as response:
            result = json.load(response)
    except urllib.error.HTTPError as exc:
        raise RuntimeError(exc.read().decode()) from exc
    return result["result"]


if __name__ == "__main__":
    params = json.loads(Path(sys.argv[2]).read_text()) if len(sys.argv) > 2 else (json.load(sys.stdin) if not sys.stdin.isatty() else {})
    print(json.dumps(call(sys.argv[1], params), ensure_ascii=False, indent=2))
