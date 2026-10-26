// 云端连接：把设备接到 papa.papaclaoud.top 的 WebSocket 中转服务。
//
// 数据流：
//   设备 ──WSS /ws/device?key=<设备密钥>──→ 中转服务 ←──WSS /ws/client── 浏览器
//
// 设备是【主动出站】连接 —— 不需要公网 IP、不需要端口映射。
//
// 协议（与 firmware/web-console/server/server.js 对齐）：
//   文本帧 JSON：
//     上行  {"type":"hello","info":{...}}
//           {"type":"status", ...}
//     下行  {"type":"welcome","server":"papa-relay"}
//           {"type":"cmd","id":"c1","cmd":"next"}
//           {"type":"error","error":"..."}
//   二进制帧：画面数据，服务器原样透传（暂未启用）
#pragma once
#include <cstddef>
#include <cstdint>

namespace cloud {

// 收到下行命令时的回调。main.cpp 注册，把命令喂给现有的串口命令分发器。
using CommandHandler = void (*)(const char *line);
void setCommandHandler(CommandHandler h);

// ---------------- 生命周期 ----------------
// 读 NVS 里的配置；有配置就（异步）开始连接。在 setup() 末尾调用。
void begin();
// 在 loop() 里调用：处理重连、心跳、收消息。
void loop(uint32_t now);

// ---------------- 状态 ----------------
enum class State : uint8_t { Disabled, Connecting, Online, Offline };
State state();
const char *stateName();
bool connected();
uint32_t connectedSince();      // millis()；未连接返回 0
uint32_t cmdCount();            // 收到并执行过的命令数
uint32_t reconnectCount();
const char *lastError();

// ---------------- 上行 ----------------
// 发一段文本（应当是自己拼好的 JSON）。返回是否真的发出去了。
bool sendText(const char *json);
// 发二进制帧（画面数据用）
bool sendBinary(const uint8_t *data, size_t len);
// 上报一条状态（由 main.cpp 调用，内容自定）
void sendStatus(const char *json);

// ---------------- 画面推流 ----------------
// 把帧缓冲编码成二进制 RLE 帧发给浏览器。
//
// 帧格式（小端，v2 加了 scale 字段）：
//   byte 0      : 0x01  （帧类型 = RLE 全帧）
//   byte 1      : scale （1/2/3/4，像素块边长；浏览器把画布放大 scale 倍显示）
//   byte 2..3   : width  uint16（降采样后的宽 = 原宽 / scale）
//   byte 4..5   : height uint16
//   byte 6..7   : runCount uint16
//   之后 runCount 组，每组 4 字节：
//     byte 0..1 : count uint16（同一颜色的连续像素数，行优先线性扫描）
//     byte 2..3 : RGB565 uint16
//
// 相比串口那套文本格式（每个 run 9 个 ASCII 字符），二进制每 run 只要 4 字节，
// 而且两端都不用做字符串解析。
//
// ⚠️ 为什么要 scale：UI 屏大片纯色，320×240 全分辨率只要几百个 run；
// 但 GIF 动画是照片类画面，实测 3–4 万个 run（180 KB），
// 任何合理大小的缓冲都装不下。降采样成 1/4 边长后 run 数降到 1/10 左右，
// 还能看清画面在演什么 —— 反正网页预览只是「瞄一眼」，不需要像素级还原。
//
// 返回 false 表示没在推流 / 缓冲不够（已降采样到底仍不够）/ 发送失败。
bool sendFrameRLE(const uint16_t *fb, uint16_t w, uint16_t h);

// 推流开关。fps 会被夹到 1..20。
void setStreaming(bool on, uint8_t fps = 5);
bool streaming();
uint8_t streamFps();
uint32_t framesSent();
// 距离上一帧是否已经够一个间隔（main.cpp 用它决定要不要编码）
bool streamDue(uint32_t now);
void markFrameSent(uint32_t now);

// ---------------- 配置（持久化在 NVS）----------------
// 默认值：host="papa.papaclaoud.top" port=443 path="/ws/device"
// 密钥必须显式设置才会启用。
bool configured();
void setConfig(const char *host, uint16_t port, const char *path, const char *key);
void clearConfig();
void printConfig();

// 一次性发当前状态（供 main.cpp 在屏幕变化后调用）
void pushStatus(const char *extraJson = nullptr);

}  // namespace cloud
