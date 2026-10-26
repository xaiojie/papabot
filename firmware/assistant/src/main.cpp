// 桌面助手 · 应用固件主程序
//
// 没有屏幕也能验证：每帧的脏矩形、字节数、实际传输耗时都会从串口报出来。
// 用 `stats on` 打开周期上报，`stats` 立即打印一次。
#include <Arduino.h>
#include <SPI.h>
#include <Adafruit_GFX.h>
#include <Adafruit_ST7789.h>
#include <Preferences.h>

#include "anim.h"
#include "servo.h"

extern const uint8_t anim_bin_start[] asm("_binary_data_anim_bin_start");
extern const uint8_t anim_bin_end[]   asm("_binary_data_anim_bin_end");
#include "apps.h"
#include "canvas.h"
#include "cloud.h"
#include "config.h"
#include "dirty.h"

using gfx::Rect;

// 前向声明（定义在本文件底部）：切屏后要把新状态推给云端。
// 必须放在匿名 namespace 【外面】，否则声明的名字空间和定义对不上，链接会找不到。
void pushCloudStatus();

namespace {

// ST7789 的 begin() 会按自己的默认频率初始化，这里固定成我们要的值
class Panel final : public Adafruit_ST7789 {
 public:
  using Adafruit_ST7789::Adafruit_ST7789;
  void begin(uint32_t = 0) override { Adafruit_ST77xx::begin(cfg::SPI_HZ_DEFAULT); }
};

SPIClass panelSpi(FSPI);
Panel display(&panelSpi, cfg::PIN_LCD_CS, cfg::PIN_LCD_DC, cfg::PIN_LCD_RST);
gfx::Canvas canvas;

apps::Id currentApp = apps::Id::Face;
// 屏幕序号：0..5 是固定六屏，之后每部 GIF 动画一屏 —— 旋钮转一圈就自然轮过所有动画。
int gScreen = 0;
int gAnimClip = -1;
bool ledBlink = false;

// 舵机：每路占一个 LEDC 通道（0..SERVO_COUNT-1），只在 arm 之后才输出。
// 路数和引脚表都在 config.h，这里不重复写死。
servo::Policy gServo[cfg::SERVO_COUNT];
bool gServoPwmOn[cfg::SERVO_COUNT] = {};
constexpr int kServoChannelBase = 0;

void ledWrite(bool on) {
  digitalWrite(cfg::PIN_LED, cfg::LED_ACTIVE_LOW ? !on : on);
}

void servoWriteUs(int i, uint16_t us) {
  // 50 Hz → 周期 20000µs；14 位分辨率 → 16384 步
  const uint32_t duty = (static_cast<uint32_t>(us) * ((1u << cfg::SERVO_RES_BITS) - 1u)) / 20000u;
  ledcWrite(kServoChannelBase + i, duty);
}

// 单路：按 armed 状态开/关 PWM 输出，并写入当前脉宽
void applyServo(int i) {
  const int ch = kServoChannelBase + i;
  if (gServo[i].armed() && !gServoPwmOn[i]) {
    ledcSetup(ch, cfg::SERVO_FREQ_HZ, cfg::SERVO_RES_BITS);
    ledcAttachPin(cfg::SERVO_PINS[i], ch);
    gServoPwmOn[i] = true;
  } else if (!gServo[i].armed() && gServoPwmOn[i]) {
    ledcWrite(ch, 0);
    ledcDetachPin(cfg::SERVO_PINS[i]);
    pinMode(cfg::SERVO_PINS[i], INPUT);     // 松力：别让 GPIO 一直驱动
    gServoPwmOn[i] = false;
  }
  if (gServo[i].armed()) servoWriteUs(i, gServo[i].current());
}

void applyAllServos() {
  for (int i = 0; i < cfg::SERVO_COUNT; ++i) applyServo(i);
}

// 解析「第几个舵机」。必须是纯数字且落在 0..SERVO_COUNT-1，否则返回 -1。
// 用它把 `servo pulse 1 1200`（1 号转到 1200）和 `servo pulse 1200`（全部转）
// 区分开 —— 靠的就是「多余的参数是不是一个合法编号」。
int parseServoIndex(const char *s) {
  if (!s || !*s) return -1;
  char *end = nullptr;
  const long n = strtol(s, &end, 10);
  if (!end || *end != '\0' || end == s) return -1;
  return (n >= 0 && n < cfg::SERVO_COUNT) ? static_cast<int>(n) : -1;
}
apps::UiContext ctx;
netlink::Weather weather;
netlink::Usage usage;
netlink::AccountQuota quota;

// ---------------- 统计 ----------------
struct Stats {
  uint32_t frames = 0;
  uint32_t flushes = 0;
  uint64_t bytesTotal = 0;
  uint32_t lastFlushUs = 0;
  uint32_t maxFlushUs = 0;
  Rect lastRect{};
  uint32_t windowStartMs = 0;
  uint32_t windowFrames = 0;
  bool periodic = true;   // 默认开：没有屏幕时靠它判断主循环是否存活
};
Stats stats;

void printStats(bool resetWindow) {
  const uint32_t now = millis();
  const uint32_t dt = now - stats.windowStartMs;
  const float fps = dt ? (stats.windowFrames * 1000.0f / dt) : 0.0f;
  Serial.printf("dirty=%dx%d bytes=%ld flush=%luus(max %luus) fps=%.1f frames=%lu\n",
                stats.lastRect.w, stats.lastRect.h,
                static_cast<long>(gfx::rectBytes(stats.lastRect)),
                static_cast<unsigned long>(stats.lastFlushUs),
                static_cast<unsigned long>(stats.maxFlushUs), fps,
                static_cast<unsigned long>(stats.frames));
  if (resetWindow) {
    stats.windowStartMs = now;
    stats.windowFrames = 0;
    stats.maxFlushUs = 0;
  }
}

// ---------------- 编码器 ----------------
volatile int32_t encCount = 0;
volatile int8_t encPartial = 0;
volatile uint8_t encState = 3;
volatile uint32_t encLastUs = 0;
portMUX_TYPE encMux = portMUX_INITIALIZER_UNLOCKED;

// 累计步数，永不清零 —— takeEncoder() 每次清零，所以 status 里的 enc 永远是 0，
// 编码器被噪声误触发时根本看不出来。这个计数器专门用来暴露那种情况。
volatile int32_t encTotal = 0;

void IRAM_ATTR encIsr() {
  // 机械编码器的触点抖动会在 1 ms 内产生成串假跳变。规定两次计数之间至少隔
  // ENCODER_MIN_GAP_US，抖动和线路噪声都过不来，正常手拧又远慢于这个间隔。
  const uint32_t nowUs = micros();
  if (nowUs - encLastUs < cfg::ENCODER_MIN_GAP_US) return;
  portENTER_CRITICAL_ISR(&encMux);
  const uint8_t next = static_cast<uint8_t>((digitalRead(cfg::PIN_ENC_A) ? 2 : 0) |
                                            (digitalRead(cfg::PIN_ENC_B) ? 1 : 0));
  const uint8_t changed = next ^ encState;
  if (changed == 3) {
    encPartial = 0;
  } else if (changed != 0) {
    encPartial += ((encState & 1) ^ ((next >> 1) & 1)) ? -1 : 1;
    if (encPartial >= static_cast<int8_t>(cfg::ENCODER_TRANSITIONS_PER_DETENT)) {
      ++encCount; ++encTotal; encPartial = 0; encLastUs = nowUs;
    } else if (encPartial <= -static_cast<int8_t>(cfg::ENCODER_TRANSITIONS_PER_DETENT)) {
      --encCount; --encTotal; encPartial = 0; encLastUs = nowUs;
    }
  }
  encState = next;
  portEXIT_CRITICAL_ISR(&encMux);
}

int32_t takeEncoder() {
  portENTER_CRITICAL(&encMux);
  const int32_t v = encCount;
  encCount = 0;
  portEXIT_CRITICAL(&encMux);
  return v;
}

// ---------------- 按键（软件消抖，稳定按下沿计数）----------------
struct Button {
  bool stable = true, candidate = true;
  uint32_t since = 0;
  bool update(bool high, uint32_t now) {
    if (high != candidate) { candidate = high; since = now; }
    if (candidate != stable && now - since >= cfg::BUTTON_DEBOUNCE_MS) {
      stable = candidate;
      return !stable;               // 只在"稳定按下"那一刻返回 true
    }
    return false;
  }
  bool pressed() const { return !stable; }
};
Button btnPush, btnKey0;
uint32_t pushCount = 0, key0Count = 0;

// ---------------- 配置（NVS 持久化，凭据不编进固件）----------------
Preferences prefs;
char nickBuf[24] = "";
char qwHost[64] = "";
char qwKey[40] = "";
char qwLoc[24] = "";
char subHost[64] = "";
char subKey[96] = "";
char adminKey[128] = "";
long accountId = 0;

// Wi-Fi 凭据（可选持久化。默认不存；用 `wifi connect <ssid> <pass>` 显式保存）
char wifiSsid[64] = "";
char wifiPass[96] = "";

void loadConfig() {
  prefs.begin("assistant", false);
  snprintf(nickBuf, sizeof nickBuf, "%s", prefs.getString("nick", cfg::DEFAULT_NICKNAME).c_str());
  snprintf(qwHost, sizeof qwHost, "%s", prefs.getString("qwhost", cfg::DEFAULT_QW_HOST).c_str());
  snprintf(qwKey, sizeof qwKey, "%s", prefs.getString("qwkey", cfg::DEFAULT_QW_KEY).c_str());
  snprintf(qwLoc, sizeof qwLoc, "%s", prefs.getString("qwloc", cfg::DEFAULT_QW_LOC).c_str());
  snprintf(subHost, sizeof subHost, "%s", prefs.getString("subhost", "").c_str());
  snprintf(subKey, sizeof subKey, "%s", prefs.getString("subkey", "").c_str());
  snprintf(adminKey, sizeof adminKey, "%s", prefs.getString("adminkey", "").c_str());
  accountId = prefs.getLong("accountid", 0);
  snprintf(wifiSsid, sizeof wifiSsid, "%s", prefs.getString("wifissid", "").c_str());
  snprintf(wifiPass, sizeof wifiPass, "%s", prefs.getString("wifipass", "").c_str());
  Serial.printf("config: nick=\"%s\" qwhost=%s qwkey=%s qwloc=%s subhost=%s subkey=%s\n",
                nickBuf, *qwHost ? qwHost : "(unset)", *qwKey ? "(set)" : "(unset)", qwLoc,
                *subHost ? subHost : "(unset)", *subKey ? "(set)" : "(unset)");
  Serial.printf("config: wifi ssid=%s pass=%s\n",
                *wifiSsid ? wifiSsid : "(unset)", *wifiPass ? "(set)" : "(unset)");
}

void fillContext() {
  ctx.clock = netlink::now();
  ctx.weather = weather;
  ctx.usage = usage;
  ctx.quota = quota;
  ctx.screenPos = gScreen;
  ctx.screenTotal = apps::screenCount();
  ctx.nickname = nickBuf;
  ctx.city = cfg::DEFAULT_CITY;
  ctx.wifiUp = netlink::wifiConnected();
  ctx.rssi = netlink::rssiDbm();
  ctx.ip = netlink::ipString();
  ctx.uptimeMs = millis();
  ctx.freeHeap = ESP.getFreeHeap();
  ctx.freePsram = ESP.getFreePsram();
  ctx.spiHz = canvas.spiHz();
}

void gotoScreen(int pos) {
  const int n = apps::screenCount();
  if (n <= 0) return;
  while (pos < 0) pos += n;
  pos %= n;
  gScreen = pos;
  const apps::Id id = apps::idAtScreen(pos);
  gAnimClip = apps::animAtScreen(pos);
  currentApp = id;
  fillContext();
  if (id == apps::Id::Anim && gAnimClip >= 0) {
    apps::enterAnim(canvas, ctx, gAnimClip);
  } else {
    apps::enter(id, canvas, ctx);
  }
  stats.lastRect = canvas.damageRect();
  stats.lastFlushUs = canvas.flush();
  ++stats.frames;
  ++stats.windowFrames;
  // 切屏后通知云端，网页上能立刻高亮对应按钮（没连云端时这是空操作）
  pushCloudStatus();
  if (stats.lastFlushUs > stats.maxFlushUs) stats.maxFlushUs = stats.lastFlushUs;
  Serial.printf("[goto] pos=%d id=%s clip=%d\n", pos, apps::name(id), gAnimClip);
  Serial.printf("screen -> %s%s  (dirty %dx%d, flush %luus)\n", apps::name(id),
                gAnimClip >= 0 ? " (动画)" : "",
                stats.lastRect.w, stats.lastRect.h,
                static_cast<unsigned long>(stats.lastFlushUs));
}

// ---------------- 串口命令 ----------------
void printHelp() {
  Serial.printf(
      "\nDesktop Assistant / assistant firmware\n"
      "  help | status | stats [on|off] | dump | dumpr   stats off also silences the heartbeat\n"
      "  next | prev | screen <0-%d|name>\n"
      "  mood [next]                  face expression\n"
      "  ntp                          start time sync\n"
      "  wifi connect <ssid> <pass>   连接并保存（开机自动重连）\n"
      "  wifi connect <ssid> <pass> ram   只连，不保存\n"
      "  wifi forget                 清除保存的凭据\n"
      "  wifi status | wifi scan | wifi off\n"
      "  cloud status                云端中转连接状态\n"
      "  cloud key <密钥>            配置设备密钥（连 papa.papaclaoud.top）\n"
      "  cloud forget                清除设备密钥\n"
      "  set nick <text>              saved to NVS\n"
      "  set qwhost <api-host>        QWeather project API Host\n"
      "  set qwkey <key> | set qwloc <location-id>\n  set subhost <host> | set adminkey <admin-...> | set account <id>\n  quota                        fetch upstream account quota now\n  set subkey <sk-...> | usage  (钱包余额，备用)\n  usage                        fetch sub2api usage now\n"
      "  weather                      fetch now (needs host+key)\n"
      "  spi <mhz>                    change SPI clock (10|20|40)\n"
      "  servo arm|center|stop [n]    舵机 ×%d 上电/回中位/松力（n 省略=全部）\n"
      "  servo pulse [n] <us>         舵机脉宽 %u..%uµs（n 省略=全部）\n"
      "  servo status                 各路舵机状态\n"
      "  config                       show stored config\n"
      "Note: credentials are never compiled in; only 'set' writes NVS.",
      apps::screenCount() - 1, cfg::SERVO_COUNT, cfg::SERVO_MIN_US, cfg::SERVO_MAX_US);
}

void printStatus() {
  fillContext();
  Serial.printf("app=%s uptime=%lus heap=%luKB psram=%luKB spi=%luMHz\n",
                apps::name(currentApp), static_cast<unsigned long>(ctx.uptimeMs / 1000),
                static_cast<unsigned long>(ctx.freeHeap / 1024),
                static_cast<unsigned long>(ctx.freePsram / 1024),
                static_cast<unsigned long>(ctx.spiHz / 1000000));
  // ⚠️ 格式符和参数必须逐个对齐。加/删参数时务必数一遍 ——
  // Arduino 的 Print::printf 没有 format 属性，-Wall 查不出这类错位，
  // 上次多插一个参数就把 mood=%s 喂成了整数，直接崩在 vfprintf 里。
  // 这里只打印**累计**编码器计数：它永不清零，能暴露噪声误触发；
  // 而 takeEncoder() 有副作用（清零），不能在打印里调用。
  Serial.printf("time=%s wifi=%s rssi=%d ip=%s push=%lu key0=%lu mood=%s enc=%ld\n",
                ctx.clock.valid ? "valid" : "invalid", ctx.wifiUp ? "up" : "down",
                ctx.rssi, ctx.ip,
                static_cast<unsigned long>(pushCount), static_cast<unsigned long>(key0Count),
                apps::moodName(),
                static_cast<long>(encTotal));
  // 舵机状态：之前完全没打印，舵机不动时无从判断是没上电还是没收到指令
  for (int i = 0; i < cfg::SERVO_COUNT; ++i) {
    Serial.printf("servo%d=%s cur=%u target=%u armed=%d gpio=%d\n",
                  i, gServoPwmOn[i] ? "ON" : "off", gServo[i].current(), gServo[i].target(),
                  gServo[i].armed() ? 1 : 0, cfg::SERVO_PINS[i]);
  }
  Serial.printf("weather=%s temp=%d text=%s\n", netlink::weatherStateName(weather.state),
                weather.tempC, weather.text[0] ? weather.text : "-");
}

void handleCommand(char *line) {
  char *save = nullptr;
  // 最多取 5 个词：wifi connect <ssid> <password> [ram] 需要第 5 个
  const char *w0 = strtok_r(line, " \t\r\n", &save);
  if (!w0) return;
  const char *w1 = strtok_r(nullptr, " \t\r\n", &save);
  const char *w2 = strtok_r(nullptr, " \t\r\n", &save);
  const char *w3 = strtok_r(nullptr, " \t\r\n", &save);
  const char *w4 = strtok_r(nullptr, " \t\r\n", &save);

  if (!strcmp(w0, "help")) { printHelp(); return; }
  if (!strcmp(w0, "status")) { printStatus(); return; }
  if (!strcmp(w0, "stats")) {
    if (w1 && !strcmp(w1, "on"))  { stats.periodic = true;  Serial.println("stats: on"); }
    else if (w1 && !strcmp(w1, "off")) { stats.periodic = false; Serial.println("stats: off"); }
    else printStats(true);
    return;
  }
  if (!strcmp(w0, "next")) { gotoScreen(gScreen + 1); return; }
  if (!strcmp(w0, "prev")) { gotoScreen(gScreen - 1); return; }
  if (!strcmp(w0, "screen") && w1) {
    for (int i = 0; i < apps::count(); ++i) {
      if (!strcmp(w1, apps::name(apps::at(i)))) { gotoScreen(i); return; }
    }
    // 名字没匹配上才当序号用。⚠️ 必须校验是【纯数字】：
    // atoi("dial") 返回 0，而 0 是合法序号（face），旧代码会默默跳到表情屏 ——
    // 网页上写错一个屏名（dial / quota）就会表现成「点哪都跳回表情」。
    char *endp = nullptr;
    const long n = strtol(w1, &endp, 10);
    if (endp && *endp == '\0' && endp != w1 && n >= 0 && n < apps::screenCount()) {
      gotoScreen(static_cast<int>(n));
      return;
    }
    Serial.printf("ERR: 没有这个屏幕 \"%s\"。可用屏名: ", w1);
    for (int i = 0; i < apps::count(); ++i) Serial.printf("%s ", apps::name(apps::at(i)));
    Serial.printf("| 序号 0..%d\n", apps::screenCount() - 1);
    return;
  }
  // 面板设置实时切换：改完立刻全屏重绘，不用重烧固件
  if (!strcmp(w0, "invert") && w1) {
    display.invertDisplay(atoi(w1) != 0);
    Serial.printf("invert = %d\n", atoi(w1) != 0);
    canvas.clear(); canvas.flush();
    apps::enter(currentApp, canvas, ctx);
    stats.lastFlushUs = canvas.flush();
    Serial.println("screen redrawn");
    return;
  }
  if (!strcmp(w0, "rotate") && w1) {
    display.setRotation(atoi(w1));
    Serial.printf("rotation = %d\n", atoi(w1));
    canvas.clear(); canvas.flush();
    apps::enter(currentApp, canvas, ctx);
    stats.lastFlushUs = canvas.flush();
    Serial.println("screen redrawn");
    return;
  }
  if (!strcmp(w0, "servo")) {
    // 用法：
    //   servo                        显示用法 + 各路状态
    //   servo status                 只显示各路状态
    //   servo arm [n]                上电回中位（n 省略 = 全部）
    //   servo pulse <us>             全部转到 us
    //   servo pulse <n> <us>         第 n 路转到 us
    //   servo center [n]             回中位
    //   servo stop [n]               松力
    //
    // 「servo pulse 1200」和「servo pulse 1 1200」靠 parseServoIndex 区分：
    // 多出来的那个参数如果能解析成合法编号，就当成编号。
    auto selName = [](int i) { return i < 0 ? "全部" : "S" + String(i); };

    if (!w1 || !strcmp(w1, "status")) {
      for (int i = 0; i < cfg::SERVO_COUNT; ++i) {
        Serial.printf("servo%d: pin=GPIO%d %s cur=%u target=%u armed=%d\n",
                      i, cfg::SERVO_PINS[i], gServoPwmOn[i] ? "PWM=ON " : "PWM=off",
                      gServo[i].current(), gServo[i].target(), gServo[i].armed() ? 1 : 0);
      }
      if (!w1) {
        Serial.printf("usage: servo arm|center|stop [n] | servo pulse [n] <%u-%u>"
                      "   （n 省略=全部，共 %d 路）\n",
                      cfg::SERVO_MIN_US, cfg::SERVO_MAX_US, cfg::SERVO_COUNT);
      }
      return;
    }

    if (!strcmp(w1, "arm")) {
      const int idx = parseServoIndex(w2);          // -1 = 全部
      const uint32_t t = millis();
      for (int i = 0; i < cfg::SERVO_COUNT; ++i) {
        if (idx >= 0 && i != idx) continue;
        const bool ok = gServo[i].arm(t);
        applyServo(i);
        Serial.printf("servo%d arm %s: %u us center, %u..%u, %lus timeout  [millis=%lu]\n",
                      i, ok ? "OK" : "(already armed)", cfg::SERVO_CENTER_US,
                      cfg::SERVO_MIN_US, cfg::SERVO_MAX_US,
                      static_cast<unsigned long>(cfg::SERVO_TIMEOUT_MS / 1000),
                      static_cast<unsigned long>(t));
      }
      return;
    }

    if (!strcmp(w1, "pulse") && w2) {
      const int idx = parseServoIndex(w2);
      const int us = (idx >= 0 && w3) ? atoi(w3) : atoi(w2);
      const uint32_t t = millis();
      // 调试：把判定依据一起打出来，方便定位「明明没到 10 秒却报超时」这类问题
      int okCount = 0;
      for (int i = 0; i < cfg::SERVO_COUNT; ++i) {
        if (idx >= 0 && i != idx) continue;
        const bool armedBefore = gServo[i].armed();
        if (gServo[i].setTarget(us, t)) {
          ++okCount;
          Serial.printf("servo%d target %d us  [millis=%lu]\n", i, us,
                        static_cast<unsigned long>(t));
        } else {
          Serial.printf("ERR: servo%d 先 servo arm；或角度超范围（只允许 %u..%u）"
                        "  [millis=%lu armedBefore=%d]\n",
                        i, cfg::SERVO_MIN_US, cfg::SERVO_MAX_US,
                        static_cast<unsigned long>(t), armedBefore ? 1 : 0);
        }
      }
      if (okCount == 0 && idx < 0) Serial.println("ERR: 所有舵机都没 armed");
      return;
    }

    if (!strcmp(w1, "center")) {
      // ⚠️ 每条命令都必须打印点什么。取景服务器是「读到串口安静下来为止」，
      // 命令一声不吭的话它会一直等到 30 秒超时 —— servo center 就踩过这个坑。
      const int idx = parseServoIndex(w2);
      const uint32_t t = millis();
      for (int i = 0; i < cfg::SERVO_COUNT; ++i) {
        if (idx >= 0 && i != idx) continue;
        if (gServo[i].setTarget(cfg::SERVO_CENTER_US, t)) {
          Serial.printf("servo%d center %u us\n", i, cfg::SERVO_CENTER_US);
        } else {
          Serial.printf("ERR: servo%d 先 servo arm（或已超时松力）\n", i);
        }
      }
      return;
    }

    if (!strcmp(w1, "stop")) {
      const int idx = parseServoIndex(w2);
      for (int i = 0; i < cfg::SERVO_COUNT; ++i) {
        if (idx >= 0 && i != idx) continue;
        gServo[i].stop(); applyServo(i);
        Serial.printf("servo%d PWM off（舵机电源没断）\n", i);
      }
      return;
    }

    Serial.printf("ERR: servo arm|center|stop [n] | servo pulse [n] <%u-%u> | servo status\n",
                  cfg::SERVO_MIN_US, cfg::SERVO_MAX_US);
    return;
  }
  if (!strcmp(w0, "mood")) {
    if (w1 && !strcmp(w1, "next")) apps::nextMood();
    gotoScreen(0);
    Serial.printf("mood=%s\n", apps::moodName());
    return;
  }
  if (!strcmp(w0, "ntp")) { netlink::startNtp(); return; }
  // wifi connect <ssid> <pass>          连接并保存到 NVS（开机自动连）
  // wifi connect <ssid> <pass> ram      只连，不保存
  if (!strcmp(w0, "wifi") && w1 && !strcmp(w1, "connect") && w2 && w3) {
    const bool persist = !(w4 && !strcmp(w4, "ram"));
    const bool ok = netlink::connectWifi(w2, w3);
    if (ok) {
      netlink::startNtp();
      gotoScreen(gScreen);
      if (persist) {
        snprintf(wifiSsid, sizeof wifiSsid, "%s", w2);
        snprintf(wifiPass, sizeof wifiPass, "%s", w3);
        prefs.putString("wifissid", wifiSsid);
        prefs.putString("wifipass", wifiPass);
        Serial.println("wifi: 凭据已保存到 NVS，开机自动重连（要清除用 `wifi forget`）");
      } else {
        Serial.println("wifi: 本次仅 RAM，不保存（去掉末尾的 ram 才会保存）");
      }
    }
    return;
  }
  if (!strcmp(w0, "wifi") && w1 && !strcmp(w1, "forget")) {
    prefs.remove("wifissid");
    prefs.remove("wifipass");
    *wifiSsid = 0;
    *wifiPass = 0;
    Serial.println("wifi: 已清除保存的凭据（当前连接不受影响，重启后不再自动连）");
    return;
  }
  if (!strcmp(w0, "wifi") && w1 && !strcmp(w1, "status")) {
    Serial.printf("wifi=%s ssid=%s ip=%s rssi=%d\n", netlink::wifiConnected() ? "up" : "down",
                  netlink::ssidString(), netlink::ipString(), netlink::rssiDbm());
    return;
  }
  if (!strcmp(w0, "wifi") && w1 && !strcmp(w1, "scan")) { netlink::scanWifi(); return; }
  if (!strcmp(w0, "wifi") && w1 && !strcmp(w1, "off")) { netlink::disconnectWifi(); return; }

  // ---------------- 云端中转（papa.papaclaoud.top）----------------
  if (!strcmp(w0, "cloud")) {
    if (w1 && !strcmp(w1, "status")) {
      Serial.printf("cloud=%s host=%s path=%s key=%s cmds=%lu reconnects=%lu\n",
                    cloud::stateName(), "(see config)", "(see config)",
                    cloud::configured() ? "(set)" : "(unset)",
                    static_cast<unsigned long>(cloud::cmdCount()),
                    static_cast<unsigned long>(cloud::reconnectCount()));
      if (*cloud::lastError()) Serial.printf("cloud lastError=%s\n", cloud::lastError());
      return;
    }
    if (w1 && !strcmp(w1, "key") && w2) {
      cloud::setConfig(nullptr, 0, nullptr, w2);
      Serial.println("cloud: 密钥已保存，重启生效（或 `cloud restart`）");
      return;
    }
    if (w1 && !strcmp(w1, "forget")) { cloud::clearConfig(); return; }
    if (w1 && !strcmp(w1, "config")) { cloud::printConfig(); return; }
    // stream on [fps] | stream off | stream
    if (w1 && !strcmp(w1, "stream")) {
      if (w2 && !strcmp(w2, "on")) {
        cloud::setStreaming(true, w3 ? static_cast<uint8_t>(atoi(w3)) : 5);
      } else if (w2 && !strcmp(w2, "off")) {
        cloud::setStreaming(false);
      } else {
        Serial.printf("stream=%s fps=%u frames=%lu\n",
                      cloud::streaming() ? "on" : "off",
                      static_cast<unsigned>(cloud::streamFps()),
                      static_cast<unsigned long>(cloud::framesSent()));
      }
      return;
    }
    Serial.println("cloud status | cloud key <密钥> | cloud forget | cloud config");
    Serial.println("cloud stream on [fps] | cloud stream off | cloud stream");
    return;
  }
  if (!strcmp(w0, "set") && w1 && w2) {
    if (!strcmp(w1, "nick"))   { snprintf(nickBuf, sizeof nickBuf, "%s", w2); prefs.putString("nick", nickBuf); }
    else if (!strcmp(w1, "qwhost")) { snprintf(qwHost, sizeof qwHost, "%s", w2); prefs.putString("qwhost", qwHost); }
    else if (!strcmp(w1, "qwkey"))  { snprintf(qwKey, sizeof qwKey, "%s", w2);  prefs.putString("qwkey", qwKey);
                                      Serial.println("set qwkey: stored (value not echoed)"); }
    else if (!strcmp(w1, "qwloc"))  { snprintf(qwLoc, sizeof qwLoc, "%s", w2);  prefs.putString("qwloc", qwLoc); }
    else if (!strcmp(w1, "subhost")) { snprintf(subHost, sizeof subHost, "%s", w2); prefs.putString("subhost", subHost); }
    else if (!strcmp(w1, "subkey"))  { snprintf(subKey, sizeof subKey, "%s", w2);  prefs.putString("subkey", subKey);
                                       Serial.println("set subkey: stored (value not echoed)"); }
    else if (!strcmp(w1, "adminkey")) { snprintf(adminKey, sizeof adminKey, "%s", w2); prefs.putString("adminkey", adminKey);
                                        Serial.println("set adminkey: stored (value not echoed)"); }
    else if (!strcmp(w1, "account")) { accountId = atol(w2); prefs.putLong("accountid", accountId);
                                       Serial.printf("set account = %ld (saved)\n", accountId); }
    else { Serial.println("ERR: unknown config key"); return; }
    if (strcmp(w1, "qwkey") && strcmp(w1, "subkey") && strcmp(w1, "adminkey") && strcmp(w1, "account"))
      Serial.printf("set %s = %s (saved)\n", w1, w2);
    gotoScreen(gScreen);
    return;
  }
  if (!strcmp(w0, "dumpr")) {
    // 行程编码 dump：这些界面大部分是纯黑，RLE 通常能压掉 90%+，
    // 串口带宽从"每帧 2-4 秒"降到"几十毫秒"，才谈得上实时看。
    // 格式：DUMPR <w> <h>，然后每行若干 9 字符的 <5位十六进制次数><4位RGB565>，最后 ENDRLE
    const uint16_t *fb = canvas.buffer();
    if (!fb) { Serial.println("ERR: no framebuffer"); return; }
    const size_t total = static_cast<size_t>(cfg::SCREEN_W) * cfg::SCREEN_H;
    Serial.printf("DUMPR %d %d\n", cfg::SCREEN_W, cfg::SCREEN_H);
    char line[200];
    int ln = 0;
    size_t i = 0;
    while (i < total) {
      const uint16_t col = fb[i];
      size_t j = i + 1;
      while (j < total && fb[j] == col && (j - i) < 0xFFFFFu) ++j;
      ln += snprintf(line + ln, sizeof(line) - static_cast<size_t>(ln), "%05x%04x",
                     static_cast<unsigned>(j - i), static_cast<unsigned>(col));
      if (ln > 180) { line[ln] = '\0'; Serial.println(line); ln = 0; }
      i = j;
    }
    if (ln) { line[ln] = '\0'; Serial.println(line); }
    Serial.println("ENDRLE");
    return;
  }
  if (!strcmp(w0, "dump")) {
    // 把 PSRAM 帧缓冲按行吐成十六进制，主机侧重建成 PNG。
    // 没有屏幕时这是唯一能"看到"实际画面的办法。
    const uint16_t *fb = canvas.buffer();
    if (!fb) { Serial.println("ERR: no framebuffer"); return; }
    Serial.printf("DUMP %d %d\n", cfg::SCREEN_W, cfg::SCREEN_H);
    char out[130];
    for (int y = 0; y < cfg::SCREEN_H; ++y) {
      for (int x = 0; x < cfg::SCREEN_W; x += 32) {
        int n = 0;
        const int lim = (x + 32 < cfg::SCREEN_W) ? 32 : (cfg::SCREEN_W - x);
        for (int i = 0; i < lim; ++i) {
          const uint16_t v = fb[static_cast<size_t>(y) * cfg::SCREEN_W + x + i];
          out[n++] = "0123456789abcdef"[(v >> 12) & 0xF];
          out[n++] = "0123456789abcdef"[(v >> 8) & 0xF];
          out[n++] = "0123456789abcdef"[(v >> 4) & 0xF];
          out[n++] = "0123456789abcdef"[v & 0xF];
        }
        out[n] = '\0';
        Serial.println(out);
      }
      if ((y & 15) == 15) Serial.flush();
    }
    Serial.println("ENDDUMP");
    return;
  }
  if (!strcmp(w0, "config")) {
    Serial.printf("nick=%s\nqwhost=%s\nqwkey=%s\nqwloc=%s\nsubhost=%s\nsubkey=%s\n"
                  "adminkey=%s\naccount=%ld\n", nickBuf,
                  *qwHost ? qwHost : "(unset)", *qwKey ? "(set)" : "(unset)", qwLoc,
                  *subHost ? subHost : "(unset)", *subKey ? "(set)" : "(unset)",
                  *adminKey ? "(set)" : "(unset)", accountId);
    return;
  }
  if (!strcmp(w0, "weather")) {
    fillContext();
    netlink::fetchWeather(weather, qwHost, qwKey, qwLoc);
    gotoScreen(3);
    printStatus();
    return;
  }
  if (!strcmp(w0, "quota")) {
    fillContext();
    netlink::fetchAccountQuota(quota, subHost, adminKey, accountId);
    gotoScreen(4);
    return;
  }
  if (!strcmp(w0, "usage")) {
    fillContext();
    netlink::fetchUsage(usage, subHost, subKey);
    gotoScreen(4);
    return;
  }
  if (!strcmp(w0, "spi") && w1) {
    const uint32_t mhz = static_cast<uint32_t>(atoi(w1));
    if (mhz >= 1 && mhz * 1000000u <= cfg::SPI_HZ_MAX) {
      canvas.setSpiHz(mhz * 1000000u);
      display.setSPISpeed(canvas.spiHz());
      Serial.printf("spi = %lu MHz\n", static_cast<unsigned long>(mhz));
      gotoScreen(gScreen);
    } else {
      Serial.printf("ERR: spi must be 1..%lu MHz\n",
                    static_cast<unsigned long>(cfg::SPI_HZ_MAX / 1000000));
    }
    return;
  }
  Serial.println("ERR: unknown command. Type help.");
}

// ---------------- 串口行缓冲 ----------------
// 每轮最多处理 64 字节，避免连续输入把测量循环饿死（bench-v1 同样的做法）。
char lineBuf[128];
size_t lineLen = 0;

void serviceSerial() {
  for (int n = 0; n < 64 && Serial.available(); ++n) {
    const int raw = Serial.read();
    if (raw < 0) break;
    const char ch = static_cast<char>(raw);
    if (ch == '\r' || ch == '\n') {
      if (lineLen) { lineBuf[lineLen] = '\0'; handleCommand(lineBuf); lineLen = 0; }
    } else if (ch == 8 || ch == 127) {
      if (lineLen) --lineLen;
    } else if (static_cast<unsigned char>(ch) >= 32u && lineLen + 1 < sizeof(lineBuf)) {
      lineBuf[lineLen++] = ch;      // 放行 >=0x80，中文 SSID 才能进来
    }
  }
}

}  // namespace

// ---------------------------------------------------------------- 云端命令桥
// cloud.cpp 收到下行命令后回调这里，直接喂给同一个命令分发器 ——
// 串口和云端走的是同一套命令，行为完全一致。
static void cloudCommandBridge(const char *line) {
  if (!line || !*line) return;
  char tmp[192];
  snprintf(tmp, sizeof tmp, "%s", line);
  handleCommand(tmp);       // handleCommand 会用 strtok_r 改缓冲区，所以传副本
  pushCloudStatus();        // 命令执行后把新状态推回网页（屏幕可能已经切了）
}

// 把「当前在哪一屏 / 什么表情」也带上，网页才能高亮对应按钮
void pushCloudStatus() {
  char extra[128];
  snprintf(extra, sizeof extra, "\"screen\":\"%s\",\"mood\":\"%s\",\"servo\":%d",
           apps::name(apps::at(gScreen)), apps::moodName(),
           [&]{ int c = 0; for (int i = 0; i < cfg::SERVO_COUNT; ++i) if (gServo[i].armed()) ++c; return c; }());
  cloud::pushStatus(extra);
}

void setup() {
  Serial.begin(115200);
  // ⚠️ 不要调 Serial.setTxTimeoutMs(0)！
  // 它会让 xRingbufferSend 完全不等待，ring buffer 一满就丢弃剩余数据 ——
  // 大块输出（dump 整屏帧缓冲）会被拦腰截断，RLE 数据错位解出花屏。
  // 而"没插 USB 时串口阻塞"这个担心本来就不成立：
  // isCDC_Connected() 在没插 USB 时返回 false，write 的 while 循环压根不执行。
  pinMode(cfg::PIN_LED, OUTPUT);
  ledWrite(false);          // 先灭，setup 结束时再亮起表示"我起来了"
  delay(300);
  Serial.println("\n=== Desktop Assistant firmware (assistant) ===");
  Serial.flush();
  printHelp();

  Serial.println("boot: config"); Serial.flush();
  loadConfig();

  // 屏幕：与 bench-v1 相同的初始化路径
  Serial.println("boot: spi"); Serial.flush();
  panelSpi.begin(cfg::PIN_LCD_SCLK, -1, cfg::PIN_LCD_MOSI, cfg::PIN_LCD_CS);
  Serial.println("boot: panel init"); Serial.flush();
  display.init(cfg::PANEL_NATIVE_W, cfg::PANEL_NATIVE_H);   // 原生竖屏，见 config.h
  Serial.println("boot: panel ok"); Serial.flush();
  display.setSPISpeed(cfg::SPI_HZ_DEFAULT);
  display.setRotation(cfg::SCREEN_ROTATION);
  display.invertDisplay(cfg::SCREEN_INVERT);
  Serial.printf("panel: ST7789 %dx%d rotation=%d spi=%luMHz\n", cfg::SCREEN_W, cfg::SCREEN_H,
                cfg::SCREEN_ROTATION,
                static_cast<unsigned long>(cfg::SPI_HZ_DEFAULT / 1000000));

  Serial.println("boot: canvas"); Serial.flush();
  anim::load(anim_bin_start, static_cast<uint32_t>(anim_bin_end - anim_bin_start));

  if (!canvas.begin(&display)) {
    Serial.println("FATAL: no PSRAM framebuffer; halting.");
    while (true) delay(1000);
  }
  display.fillScreen(ST77XX_BLACK);

  pinMode(cfg::PIN_ENC_A, INPUT_PULLUP);
  pinMode(cfg::PIN_ENC_B, INPUT_PULLUP);
  pinMode(cfg::PIN_ENC_PUSH, INPUT_PULLUP);
  pinMode(cfg::PIN_KEY0, INPUT_PULLUP);
  encState = static_cast<uint8_t>((digitalRead(cfg::PIN_ENC_A) ? 2 : 0) |
                                  (digitalRead(cfg::PIN_ENC_B) ? 1 : 0));
  attachInterrupt(digitalPinToInterrupt(cfg::PIN_ENC_A), encIsr, CHANGE);
  attachInterrupt(digitalPinToInterrupt(cfg::PIN_ENC_B), encIsr, CHANGE);
  btnPush.update(digitalRead(cfg::PIN_ENC_PUSH), millis());
  btnKey0.update(digitalRead(cfg::PIN_KEY0), millis());

  Serial.println("boot: inputs"); Serial.flush();
  stats.windowStartMs = millis();
  gotoScreen(0);
  ledWrite(true);           // 常亮 = 启动完成（之后再由心跳接管）

  // 开机自动连 Wi-Fi（只读 NVS 里保存过的凭据；没存就跳过）
  if (*wifiSsid) {
    Serial.printf("boot: 自动连接已保存的 Wi-Fi \"%s\"\n", wifiSsid);
    Serial.flush();
    if (netlink::connectWifi(wifiSsid, wifiPass)) {
      netlink::startNtp();
      gotoScreen(gScreen);   // 联网后重绘当前屏，把天气/额度补上
    } else {
      Serial.println("boot: 自动连接失败，可用 `wifi connect <ssid> <pass>` 重配");
    }
  }

  // 云端中转：注册命令桥后开始连接（Wi-Fi 没连上时会等 loop 里重试）
  cloud::setCommandHandler(cloudCommandBridge);
  cloud::begin();

  Serial.println("READY. `help` for commands, `stats on` for frame telemetry.");
  Serial.flush();
}

void loop() {
  const uint32_t now = millis();
  serviceSerial();

  // 云端中转：重连、心跳、收命令
  cloud::loop(now);

  // ---------------- Wi-Fi 自愈 ----------------
  // 目标「始终在线」：掉线后先靠驱动的 autoReconnect；15 秒还没回来就手动踢一脚。
  // 用 WiFi.reconnect() 而不是 connectWifi()，因为它不阻塞，不会卡住屏幕刷新。
  {
    static uint32_t wifiDownSince = 0;
    static uint32_t nextWifiKick = 0;
    if (netlink::wifiConnected()) {
      wifiDownSince = 0;
    } else {
      if (wifiDownSince == 0) wifiDownSince = now;
      const bool downLongEnough = (now - wifiDownSince) > 15000u;
      if (*wifiSsid && downLongEnough && now >= nextWifiKick) {
        nextWifiKick = now + 30000u;      // 最多每 30 秒踢一次
        Serial.printf("[wifi] 掉线 %lu s，调用 reconnect()\n",
                      static_cast<unsigned long>((now - wifiDownSince) / 1000u));
        netlink::reconnectWifi();
      }
    }
  }

  // 编码器：累计变化就切屏
  const int32_t steps = takeEncoder();
  if (steps != 0) gotoScreen(gScreen + steps);

  // 按键
  if (btnPush.update(digitalRead(cfg::PIN_ENC_PUSH), now)) {
    ++pushCount;
    if (currentApp == apps::Id::Face) { apps::nextMood(); gotoScreen(0); }
    else gotoScreen(gScreen);          // 静态屏按一下重画
  }
  if (btnKey0.update(digitalRead(cfg::PIN_KEY0), now)) {
    ++key0Count;
    gotoScreen(gScreen + 1);
  }

  // 应用更新 + 提交
  fillContext();
  const bool dirty = (currentApp == apps::Id::Anim && gAnimClip >= 0)
                         ? apps::updateAnim(canvas, ctx, gAnimClip, now)
                         : apps::update(currentApp, canvas, ctx, now);
  if (dirty) {
    stats.lastRect = canvas.damageRect();
    stats.lastFlushUs = canvas.flush();
    ++stats.frames;
    ++stats.windowFrames;
    stats.bytesTotal += gfx::rectBytes(stats.lastRect);
    if (stats.lastFlushUs > stats.maxFlushUs) stats.maxFlushUs = stats.lastFlushUs;
  }

  // ---------------- 画面推流 ----------------
  // 有变化才编码（省 CPU），但即使画面静止也每 3 秒补一帧 ——
  // 否则新打开的网页要等到下一次画面变化才看得到东西。
  if (cloud::streamDue(now)) {
    static uint32_t lastForceAt = 0;
    if (dirty || (now - lastForceAt) >= 3000u) {
      lastForceAt = now;
      cloud::sendFrameRLE(canvas.buffer(), cfg::SCREEN_W, cfg::SCREEN_H);
      // ⚠️ 不管成功失败都要标记「这一轮试过了」。
      // 原来只在返回 true 时标记，一旦编码失败 streamDue 就永远为真，
      // 于是每一轮 loop 都重新编码一遍 —— 照片类动画（几万个 run）会把这个
      // 变成持续的 CPU 风暴，loop 卡到 WebSocket 心跳都发不出去，直接断连。
      // 实测：切到 GIF 动画屏 + 开推流，连接 0ms 就断，就是这个原因。
      cloud::markFrameSent(now);
    }
  }

  // 秒级数据变化时重画静态屏（时钟到点、状态页刷新等）
  static uint32_t lastTick = 0;
  if (now - lastTick >= 1000u) {
    lastTick = now;
    if (currentApp == apps::Id::Sys) {
      apps::enter(currentApp, canvas, ctx);
      stats.lastRect = canvas.damageRect();
      stats.lastFlushUs = canvas.flush();
    }
  }

  // 心跳：1 Hz 闪一下，表示主循环在跑。
  // 拔了 USB 之后这是唯一能看出"主控活着"的信号 ——
  // 灯闪 = 固件在跑（问题在屏幕/接线）；灯不闪 = 主控没起来（问题在供电）。
  static uint32_t lastLed = 0;
  if (now - lastLed >= cfg::LED_HEARTBEAT_MS) {
    lastLed = now;
    ledBlink = !ledBlink;
    ledWrite(ledBlink);
  }

  // 舵机斜率推进 + 超时松力
  for (int i = 0; i < cfg::SERVO_COUNT; ++i) {
    if (gServo[i].tick(now)) {
      // 调试：超时松力时把差多少毫秒打出来，验证是不是真的到了 10 秒
      Serial.printf("[servo%d] TIMEOUT  now=%lu lastCmd=%lu delta=%lums (limit=%lums)\n",
                    i, static_cast<unsigned long>(now),
                    static_cast<unsigned long>(gServo[i].lastCommand()),
                    static_cast<unsigned long>(now - gServo[i].lastCommand()),
                    static_cast<unsigned long>(cfg::SERVO_TIMEOUT_MS));
      applyServo(i);
    } else if (gServo[i].armed()) {
      servoWriteUs(i, gServo[i].current());
    }
  }

  // 网络数据自动获取：开机拉一次，之后按间隔刷新。
  // 失败不放弃，1 分钟后重试，否则断网时开机就永远空白。
  static uint32_t lastWeatherAt = 0, lastQuotaAt = 0, nextNetTry = 0;
  if (netlink::wifiConnected() && netlink::timeValid() && now >= nextNetTry) {
    const bool needW = (lastWeatherAt == 0) || (now - lastWeatherAt >= cfg::WEATHER_REFRESH_MS);
    const bool needQ = (lastQuotaAt == 0) || (now - lastQuotaAt >= cfg::QUOTA_REFRESH_MS);
    if (needW || needQ) {
      const bool okW = needW ? netlink::fetchWeather(weather, qwHost, qwKey, qwLoc) : true;
      const bool okQ = needQ ? netlink::fetchAccountQuota(quota, subHost, adminKey, accountId) : true;
      // 成功就等一个完整周期；失败就 1 分钟后再来
      if (needW) lastWeatherAt = okW ? millis() : millis() - cfg::WEATHER_REFRESH_MS + cfg::NET_RETRY_MS;
      if (needQ) lastQuotaAt   = okQ ? millis() : millis() - cfg::QUOTA_REFRESH_MS   + cfg::NET_RETRY_MS;
      nextNetTry = millis() + 2000u;
      if (currentApp == apps::Id::Weather || currentApp == apps::Id::ChatGpt) gotoScreen(gScreen);
    }
  }

  // 心跳：确认主循环在跑（没有屏幕时最主要的存在性证据）
  static uint32_t lastBeat = 0;
  if (stats.periodic && now - lastBeat >= 2000u) {
    lastBeat = now;
    Serial.printf("[beat] app=%s frames=%lu lastDirty=%dx%d flush=%luus\n",
                  apps::name(currentApp), static_cast<unsigned long>(stats.frames),
                  stats.lastRect.w, stats.lastRect.h,
                  static_cast<unsigned long>(stats.lastFlushUs));
    Serial.flush();
  }

  if (stats.periodic && now - stats.windowStartMs >= 5000u) printStats(true);
  delay(1);
}
