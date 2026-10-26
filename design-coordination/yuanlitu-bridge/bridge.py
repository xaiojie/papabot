"""Local macOS bridge for Yuanlitu extension v0.1.1's documented-in-code RPC.

This is an independent adapter, not the vendor's Windows executable.
"""
import asyncio
import hmac
import json
import os
from pathlib import Path
import secrets
import time
import uuid

from aiohttp import web

ROOT = Path(__file__).resolve().parent
PROJECT = "e5e438419c1c4681946d5009bb8d6daf"
METHODS = {"system.health", "schematic.listPages", "schematic.inspectPage",
           "library.searchComponents", "operations.validate", "operations.apply",
           "schematic.runDrc"}
# Public fixed extension handshake constant, not a user's credential.
EXTENSION_TOKEN = "8a0d39d86c764be59260eafb7aa45ff7baf23088c03744dd84cdb186d0411324"
KEY_FILE = ROOT / ".local-key"
if not KEY_FILE.exists():
    fd = os.open(KEY_FILE, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w") as f:
        f.write(secrets.token_hex(32))
KEY = KEY_FILE.read_text().strip()


class Bridge:
    def __init__(self):
        self.ws = None
        self.window = None
        self.pending = {}
        self.lock = asyncio.Lock()

    async def socket(self, request):
        if request.remote not in {"127.0.0.1", "::1"}:
            raise web.HTTPForbidden()
        ws = web.WebSocketResponse(max_msg_size=8 * 1024 * 1024)
        await ws.prepare(request)
        await ws.send_json({"type": "handshake", "service": "yuanlitu-mcp", "protocolVersion": 1})
        registered = False
        try:
            async for msg in ws:
                if msg.type != web.WSMsgType.TEXT:
                    continue
                data = json.loads(msg.data)
                kind = data.get("type")
                if kind == "register":
                    if data.get("token") != EXTENSION_TOKEN or data.get("protocolVersion") != 1:
                        await ws.close(code=1008, message=b"Invalid extension registration")
                        break
                    if self.ws is not None and self.ws is not ws and not self.ws.closed:
                        await ws.close(code=1008, message=b"One EDA window at a time")
                        break
                    self.ws, self.window, registered = ws, data.get("windowId"), True
                    await ws.send_json({"type": "registered", "windowId": self.window, "timestamp": int(time.time()*1000)})
                    print("EDA extension connected", flush=True)
                elif registered and kind == "ping":
                    await ws.send_json({"type": "pong", "id": data.get("id"), "timestamp": int(time.time()*1000)})
                elif registered and kind in {"result", "error"}:
                    future = self.pending.get(data.get("id"))
                    if future and not future.done():
                        if kind == "error":
                            future.set_exception(RuntimeError(data.get("error", "EDA error")))
                        else:
                            future.set_result(data.get("result"))
        finally:
            if self.ws is ws:
                self.ws = self.window = None
                for future in self.pending.values():
                    if not future.done():
                        future.set_exception(ConnectionError("EDA disconnected; inspect before retrying a write"))
        return ws

    async def call(self, method, params):
        if self.ws is None or self.ws.closed:
            raise ConnectionError("EDA extension is not connected")
        call_id = str(uuid.uuid4())
        future = asyncio.get_running_loop().create_future()
        self.pending[call_id] = future
        try:
            await self.ws.send_json({"type": "rpc", "id": call_id, "method": method, "params": params})
            return await asyncio.wait_for(future, 120)
        finally:
            self.pending.pop(call_id, None)

    async def rpc(self, request):
        if request.headers.get("Origin"):
            raise web.HTTPForbidden(text="Browser-origin RPC is disabled")
        supplied = request.headers.get("Authorization", "")
        if not hmac.compare_digest(supplied, "Bearer " + KEY):
            raise web.HTTPUnauthorized()
        data = await request.json()
        method, params = data.get("method"), data.get("params", {})
        if method not in METHODS or not isinstance(params, dict):
            raise web.HTTPBadRequest(text="RPC method/parameters invalid")
        async with self.lock:
            try:
                health = await self.call("system.health", {})
                if (health.get("project") or {}).get("uuid") != PROJECT:
                    raise RuntimeError(f"Project guard: expected {PROJECT}; observed {health.get('project')}")
                if method == "system.health":
                    return web.json_response({"result": health})
                if method == "operations.apply":
                    params = dict(params)
                    if params.get("skipBackup"):
                        raise RuntimeError("Session schematic backup is required")
                    params["skipBackup"] = False
                    pages = await self.call("schematic.listPages", {})
                    page_ids = {p["uuid"] for p in pages["pages"]}
                    for op in params.get("operations", []):
                        if op.get("pageUuid") and op["pageUuid"] not in page_ids:
                            raise RuntimeError("Operation page is not in the current project")
                    stamp = time.time_ns()
                    (ROOT / "audit").mkdir(exist_ok=True)
                    (ROOT / "audit" / f"{stamp}-request.json").write_text(json.dumps(params, ensure_ascii=False, indent=2))
                result = await self.call(method, params)
                if method == "operations.apply":
                    (ROOT / "audit" / f"{stamp}-result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2))
                return web.json_response({"result": result})
            except Exception as exc:
                return web.json_response({"error": str(exc)}, status=409)


if __name__ == "__main__":
    bridge = Bridge()
    app = web.Application(client_max_size=8 * 1024 * 1024)
    app.router.add_get("/yuanlitu-mcp", bridge.socket)
    app.router.add_post("/rpc", bridge.rpc)
    web.run_app(app, host="127.0.0.1", port=49640, access_log=None)
