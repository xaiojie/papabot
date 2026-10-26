// 爬爬桌面助手 · WebSocket 中转服务
// 2026-09-11
//
// 职责：
//   1. ESP32 主动连进来（设备密钥认证）—— 设备不需要公网 IP
//   2. 浏览器连进来（账号密码换 token）
//   3. 在两者之间转发消息
//
// 端口：8790（只监听 127.0.0.1，由 nginx 反代）
//
// 消息协议：
//   文本帧 = JSON  { "type": "...", ... }
//   二进制帧 = 直接透传（画面数据，不解码）

import { createServer } from 'node:http';
import { createHmac, timingSafeEqual, randomUUID } from 'node:crypto';
import { WebSocketServer } from 'ws';

// ---------------------------------------------------------------- 配置
const PORT = Number(process.env.PAPA_PORT || 8790);
const USER = process.env.PAPA_USER || 'papa';
const PASS = process.env.PAPA_PASS || '';
const DEVICE_KEY = process.env.PAPA_DEVICE_KEY || '';
const TOKEN_SECRET = process.env.PAPA_TOKEN_SECRET || randomUUID();
const TOKEN_TTL_MS = Number(process.env.PAPA_TOKEN_TTL_H || 168) * 3600_000; // 默认 7 天
const DEVICE_TIMEOUT_MS = Number(process.env.PAPA_DEVICE_TIMEOUT_S || 30) * 1000;
// ⚠️ 容器里必须绑 0.0.0.0 —— docker-proxy 是从桥接网段转发进来的，
//    绑 127.0.0.1 的话它到不了容器 loopback（表现为宿主 curl 返回 000 / nginx 502）。
//    安全性由两层保证：docker 端口发布只绑宿主 127.0.0.1 + nginx 反代。
//    裸机部署时请设 PAPA_BIND=127.0.0.1。
const BIND = process.env.PAPA_BIND || '0.0.0.0';

if (!PASS || !DEVICE_KEY) {
  console.error('[fatal] 必须设置 PAPA_PASS 和 PAPA_DEVICE_KEY');
  process.exit(1);
}

// ---------------------------------------------------------------- Token（HMAC 无状态）
const b64u = (buf) => Buffer.from(buf).toString('base64url');

function signToken(username) {
  const payload = b64u(JSON.stringify({ u: username, exp: Date.now() + TOKEN_TTL_MS }));
  const sig = createHmac('sha256', TOKEN_SECRET).update(payload).digest('base64url');
  return `${payload}.${sig}`;
}

function verifyToken(token) {
  if (typeof token !== 'string') return null;
  const i = token.lastIndexOf('.');
  if (i < 1) return null;
  const payload = token.slice(0, i);
  const sig = token.slice(i + 1);
  const want = createHmac('sha256', TOKEN_SECRET).update(payload).digest('base64url');
  const a = Buffer.from(sig);
  const b = Buffer.from(want);
  if (a.length !== b.length || !timingSafeEqual(a, b)) return null;
  try {
    const obj = JSON.parse(Buffer.from(payload, 'base64url').toString());
    if (!obj || obj.exp < Date.now()) return null;
    return obj;
  } catch {
    return null;
  }
}

function safeEqual(a, b) {
  const x = Buffer.from(String(a));
  const y = Buffer.from(String(b));
  return x.length === y.length && timingSafeEqual(x, y);
}

// ---------------------------------------------------------------- 连接状态
let device = null;              // { ws, since, info }
const clients = new Set();      // Set<ws>
const startedAt = Date.now();

function deviceOnline() {
  return !!(device && device.ws.readyState === device.ws.OPEN);
}

function broadcast(obj, except) {
  const s = JSON.stringify(obj);
  for (const c of clients) {
    if (c !== except && c.readyState === c.OPEN) {
      try { c.send(s); } catch { /* 忽略单个连接错误 */ }
    }
  }
}

function statusPayload() {
  return {
    type: 'status',
    deviceOnline: deviceOnline(),
    deviceSince: device?.since ?? null,
    clients: clients.size,
    uptimeSec: Math.floor((Date.now() - startedAt) / 1000),
  };
}

function pushStatus() {
  broadcast(statusPayload());
  notifyDeviceClients();
}

// 告诉设备「现在有几个浏览器在看」——
// 设备据此自动开关画面推流：没人看就不推，省带宽和 CPU。
// 不这样做的话，设备重启或浏览器重连后，推流就一直是关的，
// 网页上会卡在最后一帧不动。
function notifyDeviceClients() {
  if (!deviceOnline()) return;
  try {
    device.ws.send(JSON.stringify({ type: 'clients', count: clients.size }));
  } catch { /* 单个连接出错不影响别人 */ }
}

// ---------------------------------------------------------------- HTTP
function json(res, code, body) {
  const s = JSON.stringify(body);
  res.writeHead(code, {
    'content-type': 'application/json; charset=utf-8',
    'content-length': Buffer.byteLength(s),
    'cache-control': 'no-store',
  });
  res.end(s);
}

async function readBody(req, limit = 64 * 1024) {
  const chunks = [];
  let n = 0;
  for await (const c of req) {
    n += c.length;
    if (n > limit) throw new Error('body too large');
    chunks.push(c);
  }
  return Buffer.concat(chunks).toString('utf8');
}

const server = createServer(async (req, res) => {
  const url = new URL(req.url, 'http://localhost');

  // 健康检查（不需要认证，给 uptime-kuma 用）
  if (url.pathname === '/api/health') {
    return json(res, 200, {
      ok: true,
      service: 'papa-relay',
      deviceOnline: deviceOnline(),
      clients: clients.size,
      uptimeSec: Math.floor((Date.now() - startedAt) / 1000),
    });
  }

  // 登录
  if (url.pathname === '/api/login' && req.method === 'POST') {
    let body;
    try { body = JSON.parse(await readBody(req)); } catch { return json(res, 400, { error: 'bad json' }); }
    const okUser = safeEqual(body.username ?? '', USER);
    const okPass = safeEqual(body.password ?? '', PASS);
    if (!okUser || !okPass) {
      console.warn(`[login] 失败 from ${req.socket.remoteAddress}`);
      return json(res, 401, { error: '账号或密码不对' });
    }
    console.log(`[login] 成功 ${body.username} from ${req.socket.remoteAddress}`);
    return json(res, 200, { token: signToken(USER), expiresInSec: Math.floor(TOKEN_TTL_MS / 1000) });
  }

  // 需要 token 的接口
  if (url.pathname === '/api/status') {
    const t = verifyToken(url.searchParams.get('token') || req.headers['x-papa-token']);
    if (!t) return json(res, 401, { error: 'token 无效或已过期' });
    return json(res, 200, statusPayload());
  }

  // 设备上报在线状态（HTTP 方式，给不带 WS 的场景留后路）
  if (url.pathname === '/api/device/ping' && req.method === 'POST') {
    const key = url.searchParams.get('key') || '';
    if (!safeEqual(key, DEVICE_KEY)) return json(res, 401, { error: 'device key 无效' });
    return json(res, 200, { ok: true, deviceOnline: deviceOnline() });
  }

  json(res, 404, { error: 'not found' });
});

// ---------------------------------------------------------------- WebSocket
const wss = new WebSocketServer({ noServer: true });

server.on('upgrade', (req, socket, head) => {
  const url = new URL(req.url, 'http://localhost');

  // ---- 设备接入 ----
  if (url.pathname === '/ws/device') {
    const key = url.searchParams.get('key') || '';
    if (!safeEqual(key, DEVICE_KEY)) {
      console.warn(`[device] 密钥不对，拒绝 ${req.socket.remoteAddress}`);
      socket.write('HTTP/1.1 401 Unauthorized\r\n\r\n');
      socket.destroy();
      return;
    }
    wss.handleUpgrade(req, socket, head, (ws) => {
      if (device && device.ws.readyState === device.ws.OPEN) {
        console.log('[device] 新设备接入，踢掉旧连接');
        try { device.ws.close(4000, 'replaced by new connection'); } catch {}
      }
      device = { ws, since: Date.now(), info: { ip: req.socket.remoteAddress } };
      console.log(`[device] 上线 from ${req.socket.remoteAddress}`);

      ws.on('message', (data, isBinary) => {
        // 二进制 = 画面帧，原样转发给所有浏览器
        if (isBinary) {
          for (const c of clients) {
            if (c.readyState === c.OPEN) { try { c.send(data, { binary: true }); } catch {} }
          }
          return;
        }
        // 文本 = JSON，转发 + 本地处理
        let msg = null;
        try { msg = JSON.parse(data.toString()); } catch {}
        if (msg?.type === 'hello') {
          device.info = { ...device.info, ...(msg.info || {}) };
          console.log('[device] hello:', JSON.stringify(msg.info || {}));
          pushStatus();
          return;
        }
        if (msg?.type === 'status' || msg?.type === 'pong') {
          broadcast(msg);
          return;
        }
        broadcast(msg);
      });

      ws.on('close', () => {
        if (device?.ws === ws) { device = null; console.log('[device] 离线'); pushStatus(); }
      });
      ws.on('error', (e) => console.warn('[device] 错误:', e.message));

      pushStatus();
      ws.send(JSON.stringify({ type: 'welcome', server: 'papa-relay', ts: Date.now() }));
    });
    return;
  }

  // ---- 浏览器接入 ----
  if (url.pathname === '/ws/client') {
    const t = verifyToken(url.searchParams.get('token'));
    if (!t) {
      socket.write('HTTP/1.1 401 Unauthorized\r\n\r\n');
      socket.destroy();
      return;
    }
    wss.handleUpgrade(req, socket, head, (ws) => {
      clients.add(ws);
      console.log(`[client] 上线，当前 ${clients.size} 个`);

      ws.send(JSON.stringify({ type: 'welcome', server: 'papa-relay', ts: Date.now() }));
      ws.send(JSON.stringify(statusPayload()));
      notifyDeviceClients();          // 有浏览器来了，通知设备可以开始推流

      ws.on('message', (data, isBinary) => {
        if (isBinary) return;                       // 浏览器不发二进制
        const txt = data.toString();
        // 只接受 JSON，且必须是 cmd 类型 —— 不透传任意内容
        let msg = null;
        try { msg = JSON.parse(txt); } catch { return; }
        if (!msg || msg.type !== 'cmd') return;
        if (!deviceOnline()) {
          ws.send(JSON.stringify({ type: 'error', error: '设备不在线', ref: msg.id ?? null }));
          return;
        }
        try { device.ws.send(txt); } catch (e) {
          ws.send(JSON.stringify({ type: 'error', error: '转发失败: ' + e.message, ref: msg.id ?? null }));
        }
      });

      ws.on('close', () => {
        clients.delete(ws);
        console.log(`[client] 下线，剩余 ${clients.size} 个`);
        notifyDeviceClients();        // 没人看了，通知设备可以停推流
      });
      ws.on('error', () => clients.delete(ws));
    });
    return;
  }

  socket.write('HTTP/1.1 404 Not Found\r\n\r\n');
  socket.destroy();
});

// ---------------------------------------------------------------- 心跳 + 设备超时
setInterval(() => {
  for (const c of clients) {
    if (c.readyState === c.OPEN) { try { c.ping(); } catch {} }
  }
  if (deviceOnline()) { try { device.ws.ping(); } catch {} }
}, 30_000);

setInterval(() => {
  if (device && Date.now() - device.since > 0 && !deviceOnline()) { device = null; pushStatus(); }
}, 5_000);

// ---------------------------------------------------------------- 启动
server.listen(PORT, BIND, () => {
  console.log(`[papa-relay] 监听 ${BIND}:${PORT}`);
  console.log(`[papa-relay] 设备端点  /ws/device?key=<DEVICE_KEY>`);
  console.log(`[papa-relay] 浏览器端点 /ws/client?token=<TOKEN>`);
});

for (const sig of ['SIGTERM', 'SIGINT']) {
  process.on(sig, () => {
    console.log(`[papa-relay] 收到 ${sig}，退出`);
    server.close(() => process.exit(0));
    setTimeout(() => process.exit(0), 3000);
  });
}
