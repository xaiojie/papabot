#!/usr/bin/env python3
"""静态文档服务器 + 和风天气本机代理。

为什么需要代理：浏览器直接请求和风 API 会被 CORS 拦下——和风的响应里没有
Access-Control-Allow-Origin，所以从 127.0.0.1 页面发起的 fetch 一定失败。
这里由本机转发一次，顺带解决两件事：
  * 页面只请求 /api/qweather/...，不需要知道 API Host
  * API Host 与 Key 从环境变量读，**不落进任何文件**

用法：
  QW_HOST=xxxxxxxx.re.qweatherapi.com QW_KEY=你的key \
      python3 scripts/docs_server.py 8770

只绑 127.0.0.1，不对外网暴露。
"""
import gzip
import http.server
import json
import os
import socketserver
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]     # bringup/，与旧地址的 /docs/... 保持一致
QW_HOST = os.environ.get("QW_HOST", "").strip()
QW_KEY = os.environ.get("QW_KEY", "").strip()
PROXY_PREFIX = "/api/qweather"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/124.0 Safari/537.36"



# ------------------------------------------------------------------ 设备实时取景
# 没有屏幕时，"看到真实画面"的唯一办法：让 ESP32 把 PSRAM 帧缓冲从串口吐出来，
# 这里重建为 PNG。串口是独占资源，所以整个模块加一把锁，并且只开一次。
import glob
import io
import select
import termios
import threading
import time
import tty

_serial_lock = threading.Lock()
_serial_fd = None
_last_screen = None
# 六个固定屏 + 数字序号（动画屏用 6,7,... #）；不再用白名单挡，
# 白名单曾经让 screen=6 静默失效 —— 抓到的其实是上一屏。
SCREENS = ["face", "clock", "analog", "weather", "chatgpt", "sys"]


def _find_port():
    for pat in ("/dev/cu.usbmodem*", "/dev/cu.wchusbserial*", "/dev/cu.usbserial*"):
        hits = sorted(glob.glob(pat))
        if hits:
            return hits[0]
    return None


def _open_serial():
    global _serial_fd
    if _serial_fd is not None:
        return _serial_fd
    port = _find_port()
    if not port:
        return None
    fd = os.open(port, os.O_RDWR | os.O_NONBLOCK)
    tty.setraw(fd)
    a = termios.tcgetattr(fd)
    a[4] = a[5] = termios.B115200
    termios.tcsetattr(fd, termios.TCSANOW, a)
    _serial_fd = fd
    return fd


def _drop_serial():
    global _serial_fd
    if _serial_fd is not None:
        try:
            os.close(_serial_fd)
        except OSError:
            pass
    _serial_fd = None


def _drain(fd, seconds):
    buf = b""
    end = time.time() + seconds
    while time.time() < end:
        r, _, _ = select.select([fd], [], [], 0.2)
        if r:
            try:
                buf += os.read(fd, 65536)
            except OSError:
                break
    return buf


def _wait_for(fd, marker, timeout=3.0):
    """读到 marker 就返回，不再死等固定时长 —— 之前那一堆 drain(2.5) 让每帧白等 4 秒。"""
    buf = b""
    end = time.time() + timeout
    while time.time() < end:
        r, _, _ = select.select([fd], [], [], 0.02)
        if r:
            try:
                buf += os.read(fd, 65536)
            except OSError:
                break
        if marker in buf:
            break
    return buf


def _read_until_idle(fd, idle=0.7, timeout=30.0):
    """读到"安静下来"为止。固定等待会漏掉慢命令的输出 ——
    比如 quota 要跑 3.8 秒 TLS，等 3 秒就永远看不到结果。"""
    buf = b""
    end = time.time() + timeout
    last = time.time()
    while time.time() < end:
        r, _, _ = select.select([fd], [], [], 0.05)
        if r:
            try:
                chunk = os.read(fd, 65536)
            except OSError:
                break
            if chunk:
                buf += chunk
                last = time.time()
        if buf and (time.time() - last) > idle:
            break
        # 兜底：一个字都没吐出来的命令，别让 HTTP 请求干等到 30 秒
        if not buf and (time.time() - last) > max(idle, 3.0):
            break
    return buf


def _send(fd, text, wait=1.5):
    os.write(fd, (text + "\r\n").encode())
    time.sleep(0.35)
    return _drain(fd, wait)


def _send_fast(fd, text, marker, timeout=3.0):
    os.write(fd, (text + "\r\n").encode())
    return _wait_for(fd, marker, timeout)


def _parse_rle(text):
    """解 DUMPR 行程编码。这些界面大部分是纯黑，RLE 通常压掉 90%+，
    一帧从 0.9 秒降到 0.02-0.04 秒，才可能接近实时。"""
    W = H = 0
    started = False
    parts = []
    for line in text.splitlines():
        if line.startswith("DUMPR "):
            _, w, h = line.split()
            W, H = int(w), int(h)
            started = True
            continue
        if line.strip() == "ENDRLE":
            break
        if started and len(line) >= 9 and all(c in "0123456789abcdef" for c in line):
            parts.append(line)
    if W == 0:
        return None
    blob = "".join(parts)
    total = W * H
    out = bytearray()
    for i in range(0, len(blob) - 8, 9):
        run = blob[i:i + 9]
        cnt = int(run[:5], 16)
        if cnt <= 0:
            continue
        if len(out) // 3 + cnt > total:          # 截断保护
            cnt = total - len(out) // 3
            if cnt <= 0:
                break
        col = int(run[5:9], 16)
        out += bytes((((col >> 11) & 0x1F) * 255 // 31,
                      ((col >> 5) & 0x3F) * 255 // 63,
                      (col & 0x1F) * 255 // 31)) * cnt
    if len(out) < total * 3:
        return None
    from PIL import Image
    img = Image.frombytes("RGB", (W, H), bytes(out[:total * 3]))
    buf = io.BytesIO()
    img.save(buf, format="PNG", compress_level=1)   # 原尺寸返回，浏览器端放大
    return buf.getvalue()


def _parse_dump(text):
    W = H = 0
    started = False
    chunks = []
    for line in text.splitlines():
        if line.startswith("DUMP "):
            _, w, h = line.split()
            W, H = int(w), int(h)
            started = True
            continue
        if line.strip() == "ENDDUMP":
            break
        if started and len(line) >= 4 and all(c in "0123456789abcdef" for c in line):
            chunks.append(line)
    blob = "".join(chunks)
    if W == 0 or len(blob) // 4 < W * H:
        return None
    from PIL import Image
    img = Image.new("RGB", (W, H))
    px = img.load()
    for i in range(W * H):
        v = int(blob[i * 4:i * 4 + 4], 16)
        px[i % W, i // W] = (((v >> 11) & 0x1F) * 255 // 31,
                             ((v >> 5) & 0x3F) * 255 // 63,
                             (v & 0x1F) * 255 // 31)
    buf = io.BytesIO()
    img.resize((W * 2, H * 2), Image.NEAREST).save(buf, format="PNG")
    return buf.getvalue()


def capture(screen=None, timeout=60, force=False):
    """切到指定屏（可选）并抓一帧，返回 PNG 字节。

    force=False 且目标屏和上次相同就跳过 screen 命令 —— 那条命令会触发一次
    320x240 全屏重绘（133 ms），实时连拍时它是最大的一块开销。
    """
    global _last_screen
    with _serial_lock:
        for attempt in (1, 2):
            fd = _open_serial()
            if fd is None:
                raise RuntimeError("找不到串口，板子插了吗？")
            try:
                _send_fast(fd, "stats off", b"stats", 1.0)
                # 只有显式 force=1 才切设备。
                # 之前是「目标屏 != 上次记录就切」，结果服务器一重启 _last_screen 就空了，
                # 页面随便一次轮询都会把设备抢走 —— 看板把设备劫持了，不是固件的毛病。
                if screen and force:
                    # "screen ->" 是 flush 之后才打印的，看到它说明画面已经画好
                    _send_fast(fd, "screen " + screen, b"screen ->", 3.0)
                    time.sleep(0.05)
                    _last_screen = screen
                # 优先用 RLE：0.02-0.04 秒一帧，hex 要 0.9 秒
                os.write(fd, b"dumpr\r\n")
                buf = b""
                buf = _wait_for(fd, b"ENDRLE", timeout)
                png = _parse_rle(buf.decode("utf-8", "replace"))
                if png is None:
                    raise RuntimeError("RLE dump 不完整")
                return png
            except OSError:
                _drop_serial()      # 端口掉了（重新烧录/重插），下一次重开
                _last_screen = None
                if attempt == 2:
                    raise RuntimeError("串口断开")
    raise RuntimeError("unreachable")


def device_command(text, timeout=30.0, idle=1.0):
    with _serial_lock:
        fd = _open_serial()
        if fd is None:
            raise RuntimeError("找不到串口")
        os.write(fd, (text + "\r\n").encode())
        out = _read_until_idle(fd, idle=idle, timeout=timeout)
        return out.decode("utf-8", "replace")


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def log_message(self, fmt, *args):  # 少刷屏
        if "/api/qweather" in (self.path or ""):
            sys.stderr.write("  [proxy] %s\n" % (fmt % args))

    def _send(self, code, body: bytes, ctype="application/json; charset=utf-8"):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")   # 本机页面同源，只是保险
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path.startswith(PROXY_PREFIX):
            return self._proxy()
        if self.path.startswith("/api/device/frame"):
            return self._device_frame()
        if self.path.startswith("/api/device/cmd"):
            return self._device_cmd()
        return super().do_GET()

    def _device_frame(self):
        q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        screen = (q.get("screen") or [None])[0]
        force = (q.get("force") or ["0"])[0] == "1"
        try:
            png = capture(screen, force=force)
        except Exception as e:                                  # noqa: BLE001
            return self._send(503, json.dumps({"error": str(e)}, ensure_ascii=False).encode())
        self.send_response(200)
        self.send_header("Content-Type", "image/png")
        self.send_header("Content-Length", str(len(png)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(png)

    def _device_cmd(self):
        q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        cmd = (q.get("c") or [""])[0]
        if not cmd:
            return self._send(400, b'{"error":"missing c"}')
        idle = float((q.get("idle") or ["1"])[0])
        try:
            out = device_command(cmd, timeout=30.0, idle=idle)
        except Exception as e:                                  # noqa: BLE001
            return self._send(503, json.dumps({"error": str(e)}, ensure_ascii=False).encode())
        return self._send(200, json.dumps({"cmd": cmd, "output": out}, ensure_ascii=False).encode())

    def _proxy(self):
        if not QW_HOST or not QW_KEY:
            return self._send(503, json.dumps({
                "error": "proxy not configured",
                "hint": "启动时给 QW_HOST 和 QW_KEY 环境变量",
            }, ensure_ascii=False).encode())

        rest = self.path[len(PROXY_PREFIX):]           # 例如 /v7/weather/now?location=101250109
        if not rest.startswith("/"):
            return self._send(400, b'{"error":"bad path"}')
        sep = "&" if "?" in rest else "?"
        url = "https://%s%s%skey=%s" % (QW_HOST, rest, sep, urllib.parse.quote(QW_KEY))

        req = urllib.request.Request(url, headers={
            "User-Agent": UA,
            "Accept": "application/json",
            # 和风的 CDN 无条件 gzip，所以显式声明并自己解压
            "Accept-Encoding": "gzip",
        })
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                body = resp.read()
                code = resp.status
                if resp.headers.get("Content-Encoding", "").lower() == "gzip":
                    body = gzip.decompress(body)
        except urllib.error.HTTPError as e:
            body = e.read()
            code = e.code
            if e.headers.get("Content-Encoding", "").lower() == "gzip":
                try:
                    body = gzip.decompress(body)
                except Exception:      # noqa: BLE001
                    pass
        except Exception as e:                          # noqa: BLE001
            return self._send(502, json.dumps({"error": str(e)}, ensure_ascii=False).encode())
        self._send(code, body)


def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8770
    if not QW_HOST or not QW_KEY:
        print("⚠️  未设置 QW_HOST / QW_KEY —— /api/qweather 会返回 503，页面上的天气仍是示例数据")
    else:
        print("天气代理已就绪：%s（Key 不落盘）" % QW_HOST)
    print("根目录：%s" % ROOT)
    try:
        import PIL  # noqa: F401
        print("PIL 已就绪：/api/device/frame 可用")
    except ImportError:
        print("⚠️  没有 PIL —— /api/device/frame 会返回 503。")
        print("   用带 Pillow 的解释器启动，例如：")
        print("   ../../.tools/pcb-lettering-venv/bin/python scripts/docs_server.py %d" % port)
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.ThreadingTCPServer(("127.0.0.1", port), Handler) as httpd:
        print("服务中： http://127.0.0.1:%d/docs/device-live.html" % port)
        httpd.serve_forever()


if __name__ == "__main__":
    main()
