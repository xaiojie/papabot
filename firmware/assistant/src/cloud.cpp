#include "cloud.h"

#include <Arduino.h>
#include <ArduinoJson.h>
#include <Preferences.h>
#include <WebSocketsClient.h>
#include <WiFi.h>
#include <WiFiClientSecure.h>

#include "net.h"
#include "qweather_ca.h"

namespace cloud {
namespace {

// ---------------- 配置 ----------------
constexpr const char *kDefaultHost = "papa.papaclaoud.top";
constexpr uint16_t kDefaultPort = 443;
constexpr const char *kDefaultPath = "/ws/device";
constexpr uint32_t kStatusIntervalMs = 5000;   // 周期性上报
constexpr uint32_t kReconnectMinMs = 3000;

Preferences s_prefs;
char s_host[64] = "";
uint16_t s_port = kDefaultPort;
char s_path[96] = "";
char s_key[80] = "";

// ---------------- 运行状态 ----------------
WebSocketsClient s_ws;
State s_state = State::Disabled;
uint32_t s_connectedSince = 0;
uint32_t s_nextStatusAt = 0;
uint32_t s_cmdCount = 0;
uint32_t s_reconnects = 0;
char s_lastError[96] = "";
bool s_started = false;

CommandHandler s_handler = nullptr;

// ---------------- 推流状态 ----------------
bool s_streaming = false;
uint8_t s_streamFps = 5;
uint32_t s_lastFrameAt = 0;
uint32_t s_framesSent = 0;
int s_clientCount = 0;          // 中转服务告知的浏览器数量
// RLE 输出缓冲：放 PSRAM，省内部堆。全帧最坏情况是每个像素一个 run，
// 320*240*4 = 307KB，那不可能真发生（界面大片纯色），16KB 足够并留了余量。
// 64 KB：全分辨率下 UI 屏只要几百字节，但降采样后的照片类动画会用到几十 KB。
// 放 PSRAM，不占内部堆。
constexpr size_t kFrameBufBytes = 64 * 1024;
// 最多降采样到 1/4 边长（面积 1/16）。再糊就看不出画面内容了。
constexpr uint8_t kMaxFrameScale = 4;
uint8_t *s_frameBuf = nullptr;

// ---------------- 内部工具 ----------------
void setError(const char *fmt, ...) {
  va_list ap;
  va_start(ap, fmt);
  vsnprintf(s_lastError, sizeof s_lastError, fmt, ap);
  va_end(ap);
}

void loadPrefs() {
  s_prefs.begin("assistant", true);   // 只读
  String h = s_prefs.getString("cloudhost", kDefaultHost);
  String p = s_prefs.getString("cloudpath", kDefaultPath);
  String k = s_prefs.getString("cloudkey", "");
  s_port = static_cast<uint16_t>(s_prefs.getUShort("cloudport", kDefaultPort));
  s_prefs.end();
  snprintf(s_host, sizeof s_host, "%s", h.c_str());
  snprintf(s_path, sizeof s_path, "%s", p.c_str());
  snprintf(s_key, sizeof s_key, "%s", k.c_str());
}

void openSocket() {
  if (!*s_key) { s_state = State::Disabled; return; }
  if (!netlink::wifiConnected()) { s_state = State::Offline; return; }

  // 把设备密钥放进查询串
  char url[160];
  snprintf(url, sizeof url, "%s?key=%s", s_path, s_key);

  Serial.printf("[cloud] 连接 wss://%s:%u%s\n", s_host, static_cast<unsigned>(s_port), s_path);
  s_state = State::Connecting;
  // ISRG Root X1（Let's Encrypt）—— 和中转服务的证书链同根
  s_ws.beginSslWithCA(s_host, s_port, url, netlink::kQWeatherRootCa);
  s_ws.setReconnectInterval(kReconnectMinMs);
  s_ws.enableHeartbeat(15000, 3000, 2);
}

// 收到一行命令
void handleCmdLine(const char *line) {
  if (!line || !*line) return;
  ++s_cmdCount;
  Serial.printf("[cloud] ← cmd: %s\n", line);
  if (s_handler) {
    s_handler(line);
  } else {
    Serial.println("[cloud] ⚠️ 没有注册命令处理器，忽略");
  }
}

void onEvent(WStype_t type, uint8_t *payload, size_t length) {
  switch (type) {
    case WStype_CONNECTED: {
      s_state = State::Online;
      s_connectedSince = millis();
      s_nextStatusAt = 0;              // 立刻发一次状态
      Serial.println("[cloud] ✅ 已连上中转服务");
      // 握手：把设备信息报上去
      char hello[192];
      snprintf(hello, sizeof hello,
               "{\"type\":\"hello\",\"info\":{\"fw\":\"assistant\",\"chip\":\"esp32s3\","
               "\"ip\":\"%s\",\"rssi\":%d}}",
               netlink::ipString(), netlink::rssiDbm());
      s_ws.sendTXT(hello);
      break;
    }

    case WStype_DISCONNECTED:
      if (s_state == State::Online) ++s_reconnects;
      s_state = State::Offline;
      s_connectedSince = 0;
      Serial.println("[cloud] ⚠️ 与中转服务断开");
      break;

    case WStype_TEXT: {
      // 只处理 JSON；解析失败就当普通文本忽略
      JsonDocument doc;
      const DeserializationError err = deserializeJson(doc, payload, length);
      if (err) {
        Serial.printf("[cloud] 收到非 JSON 文本，忽略（%u 字节）\n",
                      static_cast<unsigned>(length));
        break;
      }
      const char *t = doc["type"] | "";
      if (!strcmp(t, "cmd")) {
        const char *cmd = doc["cmd"] | "";
        handleCmdLine(cmd);
      } else if (!strcmp(t, "welcome")) {
        Serial.printf("[cloud] 服务端: %s\n", doc["server"] | "?");
      } else if (!strcmp(t, "clients")) {
        // 中转服务告诉我们有几个浏览器在看 —— 据此自动开关画面推流。
        // 没有这个机制的话，设备重启后推流一直是关的，
        // 网页上会卡在最后一帧不动（实测踩过）。
        const int n = doc["count"] | 0;
        s_clientCount = n;
        Serial.printf("[cloud] 浏览器 %d 个\n", n);
        if (n > 0 && !s_streaming) {
          setStreaming(true, s_streamFps);
        } else if (n == 0 && s_streaming) {
          setStreaming(false);
        }
      } else if (!strcmp(t, "error")) {
        setError("%s", doc["error"] | "unknown");
        Serial.printf("[cloud] 服务端报错: %s\n", s_lastError);
      }
      break;
    }

    case WStype_BIN:
      // 下行二进制：目前没有用途，先记长度
      Serial.printf("[cloud] 收到二进制 %u 字节（未处理）\n", static_cast<unsigned>(length));
      break;

    case WStype_ERROR:
      setError("socket error");
      Serial.println("[cloud] socket 错误");
      break;

    default:
      break;
  }
}

}  // namespace

// ---------------------------------------------------------------- 对外接口
void setCommandHandler(CommandHandler h) { s_handler = h; }

void begin() {
  loadPrefs();
  printConfig();
  if (!*s_key) {
    s_state = State::Disabled;
    Serial.println("[cloud] 未配置设备密钥，跳过（用 `cloud key <密钥>` 配置）");
    return;
  }
  s_ws.onEvent(onEvent);
  s_started = true;
  openSocket();
}

void loop(uint32_t now) {
  if (!s_started) return;

  // Wi-Fi 掉线时不要空转重连（socket 库自己会试，但没网白费）
  if (!netlink::wifiConnected()) {
    if (s_state == State::Online) {
      s_state = State::Offline;
      s_connectedSince = 0;
    }
    return;
  }

  // Wi-Fi 刚回来但 socket 还没建 —— 重建
  if (s_state == State::Offline && *s_key) {
    static uint32_t nextTry = 0;
    if (now >= nextTry) {
      nextTry = now + 10000;
      openSocket();
    }
  }

  s_ws.loop();

  // 周期性上报状态
  if (s_state == State::Online && now >= s_nextStatusAt) {
    s_nextStatusAt = now + kStatusIntervalMs;
    pushStatus();
  }
}

State state() { return s_state; }

const char *stateName() {
  switch (s_state) {
    case State::Disabled:   return "disabled";
    case State::Connecting: return "connecting";
    case State::Online:     return "online";
    case State::Offline:    return "offline";
  }
  return "?";
}

bool connected() { return s_state == State::Online; }
uint32_t connectedSince() { return s_connectedSince; }
uint32_t cmdCount() { return s_cmdCount; }
uint32_t reconnectCount() { return s_reconnects; }
const char *lastError() { return s_lastError; }

bool sendText(const char *json) {
  if (s_state != State::Online) return false;
  return s_ws.sendTXT(json);
}

bool sendBinary(const uint8_t *data, size_t len) {
  if (s_state != State::Online || !data || !len) return false;
  return s_ws.sendBIN(data, len);
}

// ---------------------------------------------------------------- 画面推流

// 把当前帧按 scale 倍降采样 + RLE 编码进缓冲。
// 返回写好的字节数，0 表示缓冲装不下。
static size_t encodeFrameScaled(const uint16_t *fb, uint16_t w, uint16_t h, uint8_t scale) {
  const uint16_t dw = w / scale, dh = h / scale;
  const size_t dtotal = static_cast<size_t>(dw) * dh;

  size_t o = 8;                          // 前 8 字节是头，最后回填
  uint32_t runs = 0;
  // 降采样：每 scale×scale 的块取左上角像素（最省事，画面略有锯齿但足够辨认）
  for (size_t p = 0; p < dtotal; ++p) {
    if (o + 4 > kFrameBufBytes - 1) return 0;
    const size_t sy = p / dw, sx = p % dw;
    const uint16_t col = fb[(sy * scale) * w + (sx * scale)];
    // 后续块只要颜色相同就并进同一个 run
    size_t q = p + 1;
    while (q < dtotal) {
      const size_t qy = q / dw, qx = q % dw;
      if (fb[(qy * scale) * w + (qx * scale)] != col) break;
      if ((q - p) >= 0xFFFFu) break;
      ++q;
    }
    const uint16_t n = static_cast<uint16_t>(q - p);
    s_frameBuf[o++] = static_cast<uint8_t>(n & 0xFF);
    s_frameBuf[o++] = static_cast<uint8_t>(n >> 8);
    s_frameBuf[o++] = static_cast<uint8_t>(col & 0xFF);
    s_frameBuf[o++] = static_cast<uint8_t>(col >> 8);
    ++runs;
    p = q - 1;
  }

  s_frameBuf[0] = 1;                     // 帧类型：RLE 全帧
  s_frameBuf[1] = scale;
  s_frameBuf[2] = static_cast<uint8_t>(dw & 0xFF);
  s_frameBuf[3] = static_cast<uint8_t>(dw >> 8);
  s_frameBuf[4] = static_cast<uint8_t>(dh & 0xFF);
  s_frameBuf[5] = static_cast<uint8_t>(dh >> 8);
  s_frameBuf[6] = static_cast<uint8_t>(runs & 0xFF);
  s_frameBuf[7] = static_cast<uint8_t>((runs >> 8) & 0xFF);
  return o;
}

bool sendFrameRLE(const uint16_t *fb, uint16_t w, uint16_t h) {
  if (!s_streaming) return false;
  if (s_state != State::Online) return false;
  if (!fb || !w || !h) return false;

  if (!s_frameBuf) {
    s_frameBuf = static_cast<uint8_t *>(ps_malloc(kFrameBufBytes));
    if (!s_frameBuf) { setError("frame buf alloc failed"); return false; }
  }

  // 全分辨率装不下就逐级降采样重试。
  // UI 屏 scale=1 一次就成；照片类动画会一路退到 3 或 4。
  size_t o = 0;
  uint8_t usedScale = 1;
  for (uint8_t sc = 1; sc <= kMaxFrameScale; ++sc) {
    if (w % sc || h % sc) continue;      // 必须整除，省掉边界处理
    o = encodeFrameScaled(fb, w, h, sc);
    if (o) { usedScale = sc; break; }
  }
  if (!o) {
    static uint32_t dropped = 0;
    if (++dropped % 30 == 1)
      Serial.printf("[cloud] ⚠️ 降到 1/%u 仍装不下（缓冲 %u B），丢弃该帧\n",
                    kMaxFrameScale, static_cast<unsigned>(kFrameBufBytes));
    return false;
  }

  if (!s_ws.sendBIN(s_frameBuf, o)) { setError("sendBIN failed"); return false; }
  ++s_framesSent;
  static uint32_t lastLog = 0;
  if (usedScale > 1 && millis() - lastLog > 5000) {
    lastLog = millis();
    Serial.printf("[cloud] 画面帧降采样 1/%u（%u B）\n", usedScale, static_cast<unsigned>(o));
  }
  return true;
}

void setStreaming(bool on, uint8_t fps) {
  if (fps < 1) fps = 1;
  if (fps > 20) fps = 20;
  s_streamFps = fps;
  s_streaming = on;
  if (on) {
    s_lastFrameAt = 0;                  // 立刻推第一帧
    Serial.printf("[cloud] 画面推流: 开（上限 %u fps）\n", static_cast<unsigned>(fps));
  } else {
    Serial.println("[cloud] 画面推流: 关");
  }
}

bool streaming() { return s_streaming; }
uint8_t streamFps() { return s_streamFps; }
uint32_t framesSent() { return s_framesSent; }

bool streamDue(uint32_t now) {
  if (!s_streaming || s_state != State::Online) return false;
  const uint32_t gap = 1000u / s_streamFps;
  return (now - s_lastFrameAt) >= gap;
}

void markFrameSent(uint32_t now) { s_lastFrameAt = now; }

void sendStatus(const char *json) {
  if (!json || !*json) return;
  sendText(json);
}

// 组装并发送一条状态。extraJson 里可以塞额外的键（形如 ",\"screen\":\"clock\""）。
void pushStatus(const char *extraJson) {
  if (s_state != State::Online) return;
  char buf[320];
  snprintf(buf, sizeof buf,
           "{\"type\":\"status\",\"uptimeSec\":%lu,\"heapKB\":%lu,\"psramKB\":%lu,"
           "\"rssi\":%d,\"ip\":\"%s\",\"cmds\":%lu%s%s}",
           static_cast<unsigned long>(millis() / 1000u),
           static_cast<unsigned long>(ESP.getFreeHeap() / 1024u),
           static_cast<unsigned long>(ESP.getFreePsram() / 1024u),
           netlink::rssiDbm(), netlink::ipString(),
           static_cast<unsigned long>(s_cmdCount),
           extraJson ? "," : "", extraJson ? extraJson : "");
  s_ws.sendTXT(buf);
}

// ---------------------------------------------------------------- 配置
bool configured() { return *s_key != '\0'; }

void setConfig(const char *host, uint16_t port, const char *path, const char *key) {
  s_prefs.begin("assistant", false);
  if (host && *host) { snprintf(s_host, sizeof s_host, "%s", host); s_prefs.putString("cloudhost", s_host); }
  if (port) { s_port = port; s_prefs.putUShort("cloudport", port); }
  if (path && *path) { snprintf(s_path, sizeof s_path, "%s", path); s_prefs.putString("cloudpath", s_path); }
  if (key && *key)  { snprintf(s_key, sizeof s_key, "%s", key);  s_prefs.putString("cloudkey", s_key); }
  s_prefs.end();
  Serial.println("[cloud] 配置已保存");
}

void clearConfig() {
  s_prefs.begin("assistant", false);
  s_prefs.remove("cloudkey");
  s_prefs.end();
  *s_key = 0;
  s_state = State::Disabled;
  Serial.println("[cloud] 已清除设备密钥");
}

void printConfig() {
  Serial.printf("[cloud] host=%s port=%u path=%s key=%s\n",
                *s_host ? s_host : "(unset)", static_cast<unsigned>(s_port),
                *s_path ? s_path : "(unset)", *s_key ? "(set)" : "(unset)");
}

}  // namespace cloud
