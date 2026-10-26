#include "net.h"

#include <Arduino.h>
#include <ArduinoJson.h>
#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <time.h>

#include "config.h"
#include "qweather_ca.h"

namespace netlink {
namespace {
bool s_ntpStarted = false;
constexpr uint16_t kHttpsPort = 443;
}

// ---------------------------------------------------------------- Wi-Fi
bool connectWifi(const char *ssid, const char *passphrase, uint32_t timeoutMs) {
  if (!ssid || !*ssid) return false;
  Serial.printf("Joining \"%s\" (passphrase not echoed, not stored)...\n", ssid);
  // Arduino-ESP32 的 WiFi.persistent 默认是 true，会把口令写进 NVS 的 WiFi 命名空间。
  // 我们用自己 "assistant" 命名空间里的 wifissid/wifipass，所以这里保持一致关掉。
  WiFi.persistent(false);
  // 掉线后由驱动自动重连（默认就是 true，这里显式写出来免得以后被改掉）
  WiFi.setAutoReconnect(true);
  WiFi.mode(WIFI_STA);
  const uint32_t start = millis();
  WiFi.begin(ssid, passphrase);
  while (WiFi.status() != WL_CONNECTED && millis() - start < timeoutMs) {
    delay(200);
    Serial.print('.');
  }
  Serial.println();
  if (WiFi.status() != WL_CONNECTED) {
    Serial.printf("FAIL: not associated after %lu ms (status=%d)\n",
                  static_cast<unsigned long>(millis() - start), static_cast<int>(WiFi.status()));
    return false;
  }
  Serial.printf("CONNECTED in %lu ms  IP=%s  RSSI=%d dBm\n",
                static_cast<unsigned long>(millis() - start),
                WiFi.localIP().toString().c_str(), static_cast<int>(WiFi.RSSI()));
  return true;
}

void reconnectWifi() {
  // 非阻塞：只踢一下驱动，不等结果。凭据还在 WiFi 驱动内存里（connectWifi 时传进去的）。
  WiFi.reconnect();
}

void disconnectWifi() {
  WiFi.disconnect(true, false);
  WiFi.mode(WIFI_OFF);
}

void scanWifi() {
  WiFi.persistent(false);
  WiFi.mode(WIFI_STA);
  WiFi.disconnect(false, false);
  Serial.println("scanning 2.4 GHz ...");
  const int n = WiFi.scanNetworks(false, true, false, 120);
  if (n <= 0) {
    Serial.printf("scan: 找到 %d 个 AP（0 不等于射频故障，但结合连接失败要怀疑信号或距离）\n", n);
  } else {
    for (int i = 0; i < n; ++i) {
      Serial.printf("  %2d  %4d dBm  ch%2d  %s\n", i + 1, static_cast<int>(WiFi.RSSI(i)),
                    static_cast<int>(WiFi.channel(i)), WiFi.SSID(i).c_str());
    }
    Serial.printf("scan: 共 %d 个\n", n);
  }
  WiFi.scanDelete();
  WiFi.mode(WIFI_OFF);
}

bool wifiConnected() { return WiFi.status() == WL_CONNECTED; }
int rssiDbm() { return wifiConnected() ? static_cast<int>(WiFi.RSSI()) : 0; }
const char *ipString() {
  static char buf[20];
  snprintf(buf, sizeof buf, "%s", WiFi.localIP().toString().c_str());
  return buf;
}
const char *ssidString() {
  static char buf[36];
  snprintf(buf, sizeof buf, "%s", WiFi.SSID().c_str());
  return buf;
}

// ---------------------------------------------------------------- NTP
void startNtp() {
  if (s_ntpStarted) return;
  configTime(cfg::TZ_OFFSET_S, 0, cfg::NTP_SERVER_1, cfg::NTP_SERVER_2);
  s_ntpStarted = true;
  Serial.printf("NTP started: %s / %s, TZ=+8\n", cfg::NTP_SERVER_1, cfg::NTP_SERVER_2);
}

bool timeValid() { return time(nullptr) > 1700000000; }

Clock now() {
  Clock c;
  if (!s_ntpStarted || !wifiConnected()) return c;
  struct tm tmnow{};
  if (!getLocalTime(&tmnow, 0)) return c;
  c.year = tmnow.tm_year + 1900;
  c.month = tmnow.tm_mon + 1;
  c.day = tmnow.tm_mday;
  c.hour = tmnow.tm_hour;
  c.minute = tmnow.tm_min;
  c.second = tmnow.tm_sec;
  c.weekday = tmnow.tm_wday;
  c.valid = timeValid();
  return c;
}

// ---------------------------------------------------------------- 天气
namespace {

const char *weatherStateNameImpl(WeatherState s) {
  switch (s) {
    case WeatherState::Idle: return "idle";
    case WeatherState::Ok: return "ok";
    case WeatherState::NoConfig: return "no-config";
    case WeatherState::HttpFail: return "http-fail";
    case WeatherState::ParseFail: return "parse-fail";
  }
  return "?";
}

// ESP32-S3 的 ROM 里带 miniz，零 flash 成本解 gzip。
// 和风的 CDN 无视 Accept-Encoding，永远回 content-encoding: gzip，所以必须自己解。
extern "C" size_t tinfl_decompress_mem_to_mem(void *pOut_buf, size_t out_buf_len,
                                              const void *pSrc_buf, size_t src_buf_len, int flags);
constexpr size_t kTinflFailed = static_cast<size_t>(-1);

// 跳过 gzip 头，再按裸 deflate 解压。返回解压字节数，失败返回 0。
size_t gunzip(const String &in, uint8_t *out, size_t outCap) {
  const uint8_t *p = reinterpret_cast<const uint8_t *>(in.c_str());
  const size_t n = in.length();
  if (n < 18 || p[0] != 0x1f || p[1] != 0x8b) return 0;   // gzip magic 1f 8b
  const uint8_t flg = p[3];
  size_t off = 10;
  if (flg & 0x04) { off += 2 + static_cast<size_t>(p[10] | (p[11] << 8)); }   // FEXTRA
  if (flg & 0x08) { while (off < n && p[off]) ++off; ++off; }                 // FNAME
  if (flg & 0x10) { while (off < n && p[off]) ++off; ++off; }                 // FCOMMENT
  if (flg & 0x02) { off += 2; }                                              // FHCRC
  if (off >= n) return 0;
  const size_t got = tinfl_decompress_mem_to_mem(out, outCap, p + off, n - off, 0);
  return (got == kTinflFailed) ? 0 : got;
}

// HTTP/1.1 下服务端常用 Transfer-Encoding: chunked。curl 会透明解码，
// 所以主机上完全看不出来；ESP32 必须自己解，否则 JSON 里混进长度行。
String dechunk(const String &in) {
  String out;
  out.reserve(in.length());
  const char *p = in.c_str();
  const size_t n = in.length();
  size_t i = 0;
  while (i < n) {
    size_t eol = i;
    while (eol < n && !(p[eol] == '\r' && eol + 1 < n && p[eol + 1] == '\n')) ++eol;
    if (eol >= n) break;
    // 长度行可能是 "1f4a" 或带扩展 "1f4a;ext"
    char lenbuf[16];
    size_t k = 0;
    for (size_t j = i; j < eol && k < sizeof(lenbuf) - 1; ++j) {
      if (p[j] == ';') break;
      lenbuf[k++] = p[j];
    }
    lenbuf[k] = '\0';
    const long len = strtol(lenbuf, nullptr, 16);
    if (len <= 0) break;                       // 0 块 = 结束
    const size_t start = eol + 2;
    if (start + static_cast<size_t>(len) > n) { // 截断保护
      out.concat(p + start, static_cast<unsigned>(n - start));
      break;
    }
    out.concat(p + start, static_cast<unsigned>(len));
    i = start + static_cast<size_t>(len) + 2;  // 跳过块尾 CRLF
  }
  return out.isEmpty() ? in : out;
}

// 一次 HTTPS GET。TLS 用固件自带的根证书校验，不做 setInsecure。
bool httpsGet(const char *host, const char *path, String &out, const char *what,
              const char *authHeader = nullptr) {
  // 放堆上：TLS 客户端对象本身不小，加上握手调用链，8 KB 的 loopTask 栈扛不住
  WiFiClientSecure *client = new WiFiClientSecure();
  client->setCACert(kQWeatherRootCa);
  client->setTimeout(10);

  const uint32_t t0 = millis();
  if (!client->connect(host, kHttpsPort)) {
    Serial.printf("weather/%s: TLS connect %s:%u failed\n", what, host, kHttpsPort);
    delete client;
    return false;
  }
  client->printf("GET %s HTTP/1.1\r\nHost: %s\r\nConnection: close\r\n"
                "Accept: application/json\r\n", path, host);
  // authHeader 是完整的请求头行（含头名），调用方自己决定用 Authorization 还是 x-api-key
  if (authHeader && *authHeader) client->printf("%s\r\n", authHeader);
  client->print("\r\n");

  const uint32_t deadline = millis() + 12000;
  int status = 0;
  bool gzipped = false;
  bool chunked = false;
  // 逐字节读响应头。**不能用 readStringUntil 的空返回值判断头部结束** ——
  // 它超时也返回空串，会被误判成"头结束"，于是状态行和响应头一起被当成正文，
  // 表现为 status=0 且 raw 比真实响应大出一整段头（实测 9976 vs 8319）。
  {
    String line;
    uint32_t lastData = millis();
    while (millis() < deadline) {
      if (client->available() <= 0) {
        if (!client->connected()) break;
        if (millis() - lastData > 4000u) break;   // 真的没数据了才算超时
        delay(5);
        continue;
      }
      const int ch = client->read();
      if (ch < 0) break;
      lastData = millis();
      if (ch == '\n') {
        if (line.length() == 0 || line == "\r") break;   // 空行 = 响应头结束
        if (line.startsWith("HTTP/")) {
          const int sp = line.indexOf(' ');
          if (sp > 0) status = line.substring(sp + 1, sp + 4).toInt();
        } else if (line.startsWith("content-encoding:") || line.startsWith("Content-Encoding:")) {
          gzipped = line.indexOf("gzip") >= 0;
        } else if (line.startsWith("transfer-encoding:") || line.startsWith("Transfer-Encoding:")) {
          chunked = line.indexOf("chunked") >= 0;
        }
        line = "";
      } else if (ch != '\r') {
        line += static_cast<char>(ch);
      }
    }
  }

  String raw;
  raw.reserve(4096);
  uint8_t chunk[512];
  while (client->connected() && millis() < deadline) {
    const int avail = client->available();
    if (avail > 0) {
      const int n = client->read(chunk, sizeof chunk);
      if (n > 0) raw.concat(reinterpret_cast<const char *>(chunk), static_cast<unsigned>(n));
    } else {
      delay(5);
    }
  }
  client->stop();
  delete client;

  if (chunked) {
    const String decoded = dechunk(raw);
    raw = decoded;
  }

  if (gzipped) {
    static uint8_t plain[24576];       // now 约 445 B，3d 约 2 KB，6 KB 足够
    const size_t got = gunzip(raw, plain, sizeof plain);
    if (got == 0) {
      Serial.printf("weather/%s: gzip 解压失败（原始 %u 字节）\n", what,
                    static_cast<unsigned>(raw.length()));
      return false;
    }
    out = String(reinterpret_cast<const char *>(plain), static_cast<unsigned>(got));
  } else {
    out = raw;
  }

  Serial.printf("weather/%s: HTTP %d, raw %u → %u bytes, %lu ms\n", what, status,
                static_cast<unsigned>(raw.length()), static_cast<unsigned>(out.length()),
                static_cast<unsigned long>(millis() - t0));
  return status == 200 && out.length() > 0;
}

}  // namespace

const char *weatherStateName(WeatherState s) { return weatherStateNameImpl(s); }

bool fetchWeather(Weather &out, const char *host, const char *key, const char *location) {
  out.lastTryMs = millis();
  out.text[0] = '\0';
  out.updated[0] = '\0';
  out.icon[0] = '\0';
  out.windDir[0] = '\0';
  out.windScale[0] = '\0';
  out.humidity = 0;
  out.feelsLike = 0;
  out.cloud = 0;
  out.hasDetail = false;

  if (!host || !*host || !key || !*key) {
    out.state = WeatherState::NoConfig;
    Serial.println("weather: API Host 或 Key 未配置，跳过");
    return false;
  }
  if (!wifiConnected()) {
    out.state = WeatherState::HttpFail;
    Serial.println("weather: Wi-Fi 未连接");
    return false;
  }
  // TLS 要验证证书有效期，系统时间不对会直接失败 —— 这一点必须说清楚。
  if (!timeValid()) {
    out.state = WeatherState::HttpFail;
    Serial.println("weather: 系统时间未同步（先跑 ntp），TLS 无法校验证书");
    return false;
  }

  char path[192];
  JsonDocument doc;
  String body;

  // ① 实时天气
  snprintf(path, sizeof path, "/v7/weather/now?location=%s&key=%s", location, key);
  if (!httpsGet(host, path, body, "now") || deserializeJson(doc, body)) {
    out.state = WeatherState::HttpFail;
    Serial.printf("weather: now 失败，原始前 160 字节: %.160s\n", body.c_str());
    return false;
  }
  if (strcmp(doc["code"] | "", "200") != 0) {
    out.state = WeatherState::ParseFail;
    Serial.printf("weather: now API code=%s\n", doc["code"] | "?");
    return false;
  }
  out.tempC = doc["now"]["temp"].as<int>();
  snprintf(out.text, sizeof out.text, "%s", doc["now"]["text"].as<const char *>() ?: "");
  // 和风的 now 里这一组字段一直都在，一起取回来给天气屏的图标和详情用
  snprintf(out.icon, sizeof out.icon, "%s", doc["now"]["icon"].as<const char *>() ?: "");
  snprintf(out.windDir, sizeof out.windDir, "%s", doc["now"]["windDir"].as<const char *>() ?: "");
  snprintf(out.windScale, sizeof out.windScale, "%s", doc["now"]["windScale"].as<const char *>() ?: "");
  out.humidity = doc["now"]["humidity"].as<int>();
  out.feelsLike = doc["now"]["feelsLike"].as<int>();
  out.cloud = doc["now"]["cloud"].as<int>();
  out.hasDetail = (doc["now"]["humidity"].is<const char *>() || doc["now"]["feelsLike"].is<const char *>());
  const char *obs = doc["now"]["obsTime"].as<const char *>() ?: "";
  // obsTime 形如 2026-09-10T17:15+08:00，只留 HH:MM
  if (strlen(obs) >= 16) snprintf(out.updated, sizeof out.updated, "%.5s", obs + 11);
  else                   snprintf(out.updated, sizeof out.updated, "%s", obs);
  out.state = WeatherState::Ok;

  // ② 今日高低温（失败不影响主数据）
  out.tempMin = out.tempMax = 0;
  snprintf(path, sizeof path, "/v7/weather/3d?location=%s&key=%s", location, key);
  JsonDocument doc3;
  if (httpsGet(host, path, body, "3d") && !deserializeJson(doc3, body) &&
      strcmp(doc3["code"] | "", "200") == 0) {
    out.tempMax = doc3["daily"][0]["tempMax"].as<int>();
    out.tempMin = doc3["daily"][0]["tempMin"].as<int>();
  }

  Serial.printf("weather OK: %d°C %s (今日 %d~%d°C) obs=%s icon=%s\n",
                out.tempC, out.text, out.tempMin, out.tempMax, out.updated,
                out.icon[0] ? out.icon : "-");
  Serial.printf("weather detail: 湿度 %d%% 体感 %d°C 云量 %d%% %s%s级\n",
                out.humidity, out.feelsLike, out.cloud,
                out.windDir[0] ? out.windDir : "-", out.windScale[0] ? out.windScale : "-");
  return true;
}

// ---------------------------------------------------------------- ChatGPT 用量
bool fetchUsage(Usage &out, const char *host, const char *apiKey) {
  out = Usage();
  out.lastTryMs = millis();

  if (!host || !*host || !apiKey || !*apiKey) {
    snprintf(out.err, sizeof out.err, "未配置 sub2api host / key");
    Serial.println("usage: 未配置 host 或 key");
    return false;
  }
  if (!wifiConnected()) { snprintf(out.err, sizeof out.err, "Wi-Fi 未连接"); return false; }
  if (!timeValid()) {
    snprintf(out.err, sizeof out.err, "系统时间未同步（先 ntp）");
    Serial.println("usage: TLS 需要正确时间，先跑 ntp");
    return false;
  }

  char auth[96];
  snprintf(auth, sizeof auth, "Authorization: Bearer %s", apiKey);
  String body;
  if (!httpsGet(host, "/v1/usage?days=1", body, "usage", auth)) {
    snprintf(out.err, sizeof out.err, "请求失败");
    return false;
  }

  JsonDocument doc;
  const DeserializationError err = deserializeJson(doc, body);
  if (err) {
    snprintf(out.err, sizeof out.err, "JSON 解析失败");
    Serial.printf("usage: JSON 解析失败 (%s): %.140s\n", err.c_str(), body.c_str());
    return false;
  }
  // 出错时服务端返回 {"code":"INVALID_API_KEY","message":"..."}
  if (doc["code"].is<const char *>()) {
    snprintf(out.err, sizeof out.err, "%.44s", doc["message"].as<const char *>() ?: "API 返回错误");
    Serial.printf("usage: 服务端错误 code=%s msg=%s\n", doc["code"].as<const char *>(),
                  doc["message"].as<const char *>() ?: "");
    return false;
  }

  snprintf(out.mode, sizeof out.mode, "%s", doc["mode"].as<const char *>() ?: "?");
  snprintf(out.plan, sizeof out.plan, "%s", doc["planName"].as<const char *>() ?: "");

  if (doc["quota"].is<JsonObject>()) {
    out.hasQuota = true;
    out.quotaLimit = doc["quota"]["limit"].as<double>();
    out.quotaUsed = doc["quota"]["used"].as<double>();
    out.quotaRemaining = doc["quota"]["remaining"].as<double>();
  }
  if (doc["subscription"].is<JsonObject>()) {
    out.hasSub = true;
    out.dayUsed = doc["subscription"]["daily_usage_usd"].as<double>();
    out.dayLimit = doc["subscription"]["daily_limit_usd"].as<double>();
    out.weekUsed = doc["subscription"]["weekly_usage_usd"].as<double>();
    out.weekLimit = doc["subscription"]["weekly_limit_usd"].as<double>();
    out.monthUsed = doc["subscription"]["monthly_usage_usd"].as<double>();
    out.monthLimit = doc["subscription"]["monthly_limit_usd"].as<double>();
  }
  // 钱包余额模式：实测 sub2api 返回 balance/remaining + usage.today/total + model_stats
  if (doc["balance"].is<double>() || doc["remaining"].is<double>()) {
    out.hasWallet = true;
    out.balance = doc["balance"].is<double>() ? doc["balance"].as<double>()
                                              : doc["remaining"].as<double>();
    const JsonObject today = doc["usage"]["today"];
    const JsonObject total = doc["usage"]["total"];
    if (!today.isNull()) {
      // actual_cost 是实际扣费；今日两者通常相同
      out.todayCost = today["actual_cost"].is<double>() ? today["actual_cost"].as<double>()
                                                        : today["cost"].as<double>();
      out.todayRequests = today["requests"].as<long>();
    }
    if (!total.isNull()) {
      out.totalCost = total["actual_cost"].is<double>() ? total["actual_cost"].as<double>()
                                                        : total["cost"].as<double>();
      out.totalRequests = total["requests"].as<long>();
      out.totalTokens = total["total_tokens"].as<long long>();
    }
    // 找消耗最高的模型
    for (JsonObject m : doc["model_stats"].as<JsonArray>()) {
      const double c = m["cost"].as<double>();
      if (c > out.topModelCost) {
        out.topModelCost = c;
        snprintf(out.topModel, sizeof out.topModel, "%s", m["model"].as<const char *>() ?: "");
      }
    }
  }

  out.ok = true;

  Serial.printf("usage OK: mode=%s", out.mode);
  if (*out.plan) Serial.printf(" plan=%s", out.plan);
  if (out.hasQuota) Serial.printf(" quota=%.3f/%.3f", out.quotaUsed, out.quotaLimit);
  if (out.hasWallet) {
    Serial.printf(" balance=%.2f today=%.4f/%ld total=%.2f/%ld top=%s(%.2f)", out.balance,
                  out.todayCost, out.todayRequests, out.totalCost, out.totalRequests,
                  out.topModel, out.topModelCost);
  }
  if (out.hasSub) {
    Serial.printf(" day=%.3f/%.3f week=%.3f/%.3f month=%.3f/%.3f",
                  out.dayUsed, out.dayLimit, out.weekUsed, out.weekLimit,
                  out.monthUsed, out.monthLimit);
  }
  Serial.println();
  return true;
}

// ---------------------------------------------------------------- 上游账号额度
void isoToShort(const char *iso, char *out, unsigned n) {
  // "2026-09-15T09:25:03+08:00" -> "09-15 09:25"；字段缺失时给 "--"
  if (!iso || strlen(iso) < 16) { snprintf(out, n, "--"); return; }
  snprintf(out, n, "%.5s %.5s", iso + 5, iso + 11);
}

void windowLabel(int minutes, char *out, unsigned n) {
  if (minutes <= 0)        snprintf(out, n, "未启用");
  else if (minutes % 1440 == 0) snprintf(out, n, "%d天", minutes / 1440);
  else if (minutes % 60 == 0)   snprintf(out, n, "%d小时", minutes / 60);
  else                          snprintf(out, n, "%d分钟", minutes);
}

bool fetchAccountQuota(AccountQuota &out, const char *host, const char *adminKey, long accountId) {
  out = AccountQuota();
  out.lastTryMs = millis();
  out.accountId = accountId;

  if (!host || !*host || !adminKey || !*adminKey) {
    snprintf(out.err, sizeof out.err, "未配置 sub2api host / admin key");
    Serial.println("quota: 未配置 host 或 admin key");
    return false;
  }
  if (accountId <= 0) {
    snprintf(out.err, sizeof out.err, "未配置账号 ID");
    return false;
  }
  if (!wifiConnected()) { snprintf(out.err, sizeof out.err, "Wi-Fi 未连接"); return false; }
  if (!timeValid()) {
    snprintf(out.err, sizeof out.err, "系统时间未同步（先 ntp）");
    return false;
  }

  char path[80];
  snprintf(path, sizeof path, "/api/v1/admin/accounts/%ld", accountId);
  char auth[128];
  snprintf(auth, sizeof auth, "x-api-key: %s", adminKey);

  String body;
  if (!httpsGet(host, path, body, "quota", auth)) {
    snprintf(out.err, sizeof out.err, "请求失败");
    return false;
  }

  JsonDocument doc;
  const DeserializationError err = deserializeJson(doc, body);
  if (err) {
    snprintf(out.err, sizeof out.err, "JSON 解析失败");
    Serial.printf("quota: 解析失败 (%s): %.140s\n", err.c_str(), body.c_str());
    return false;
  }
  // 统一响应体 {"code":0,"message":"success","data":{...}}
  if (doc["code"].is<int>() && doc["code"].as<int>() != 0) {
    snprintf(out.err, sizeof out.err, "%.44s", doc["message"].as<const char *>() ?: "接口返回错误");
    Serial.printf("quota: 服务端 code=%d msg=%s\n", doc["code"].as<int>(),
                  doc["message"].as<const char *>() ?: "");
    return false;
  }
  const JsonObject d = doc["data"];
  if (d.isNull()) { snprintf(out.err, sizeof out.err, "返回里没有 data"); return false; }

  snprintf(out.name, sizeof out.name, "%s", d["name"].as<const char *>() ?: "?");
  snprintf(out.status, sizeof out.status, "%s", d["status"].as<const char *>() ?: "?");
  const JsonObject ex = d["extra"];

  // 主窗口 / 次窗口（primary 与 7d、secondary 与 5h 实测是同一组值，优先用 primary）
  const int pPct = ex["codex_primary_used_percent"] | ex["codex_7d_used_percent"] | -1;
  const int pWin = ex["codex_primary_window_minutes"] | ex["codex_7d_window_minutes"] | 0;
  if (pPct >= 0) {
    out.hasPrimary = true;
    out.primaryPercent = pPct;
    out.primaryWindowMin = pWin;
    isoToShort(ex["codex_primary_reset_at"] | ex["codex_7d_reset_at"] | "", out.primaryReset,
               sizeof out.primaryReset);
  }
  const int sPct = ex["codex_secondary_used_percent"] | ex["codex_5h_used_percent"] | -1;
  const int sWin = ex["codex_secondary_window_minutes"] | ex["codex_5h_window_minutes"] | 0;
  if (sPct >= 0 && sWin > 0) {          // 窗口为 0 说明这套订阅没启用该窗口
    out.hasSecondary = true;
    out.secondaryPercent = sPct;
    out.secondaryWindowMin = sWin;
    isoToShort(ex["codex_secondary_reset_at"] | ex["codex_5h_reset_at"] | "", out.secondaryReset,
               sizeof out.secondaryReset);
  }
  out.resetCredits = ex["codex_reset_credit_snapshot"]["available_count"] | 0;
  isoToShort(ex["codex_usage_updated_at"] | "", out.updatedAt, sizeof out.updatedAt);

  // 限流判定：主窗口打满，或服务端标了 rate_limited
  //
  // ⚠️ 2026-09-14 修复
  // 原代码：d["rate_limited_at"].is<const char*>() && d["rate_limited_at"].as<const char*>()[0]
  //
  // 实测（2026-09-14，账号 2839）：API 明确返回 "rate_limited_at": null，
  // 数据库该列也是 NULL，schedulable=true、primary 才 39%，
  // 但设备一直显示「已限流」——说明 is<const char*>() 对 null 也返回 true
  // （ArduinoJson 里 null 是合法的字符串值），null 被当成了「有限流记录」。
  //
  // 改成显式判断：必须是【非空字符串】才算限流。null 和 "" 都不算。
  const char *rla = d["rate_limited_at"].as<const char *>();
  out.rateLimited = (out.hasPrimary && out.primaryPercent >= 100) ||
                    (rla != nullptr && rla[0] != '\0');
  out.ok = true;

  // 调试行：把判定依据原样打出来，方便下回再出问题一眼定位
  Serial.printf("quota: rate_limited_at isNull=%d raw=%s  hasPrimary=%d pct=%d\n",
                d["rate_limited_at"].isNull() ? 1 : 0,
                rla ? rla : "(null)", out.hasPrimary ? 1 : 0, out.primaryPercent);

  Serial.printf("quota OK: %s(id=%ld) status=%s rateLimited=%d primary=%d%%/%dmin reset=%s credits=%d\n",
                out.name, out.accountId, out.status, out.rateLimited ? 1 : 0, out.primaryPercent,
                out.primaryWindowMin, out.primaryReset, out.resetCredits);
  return true;
}

}  // namespace netlink
