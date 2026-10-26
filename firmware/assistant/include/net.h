// 网络层：Wi-Fi、NTP 对时、和风天气。
// 凭据策略：
//   * 任何凭据都不编进固件，默认值一律为空字符串；
//   * Wi-Fi 凭据默认【不落盘】。`wifi connect <ssid> <pass>` 显式保存到 NVS，
//     `wifi connect <ssid> <pass> ram` 只连不存，`wifi forget` 清除；
//   * 保存后 setup() 会开机自动重连（见 main.cpp）。
#pragma once
#include <cstdint>

namespace netlink {

// ---------------- Wi-Fi ----------------
// 口令不回显。是否持久化由调用方（main.cpp）决定，本函数只负责连接。
bool connectWifi(const char *ssid, const char *passphrase, uint32_t timeoutMs = 20000);
// 非阻塞地让驱动重连（凭据仍在 WiFi 驱动内存里）。
// 给 loop() 里的「掉线自愈」用 —— 不能用 connectWifi()，那会阻塞 20 秒卡住屏幕。
void reconnectWifi();
void disconnectWifi();
bool wifiConnected();
int rssiDbm();

// 扫描并打印周边 2.4G AP（诊断用），扫完关射频
void scanWifi();
const char *ipString();
const char *ssidString();

// ---------------- NTP ----------------
void startNtp();
bool timeValid();

struct Clock {
  int year = 0, month = 0, day = 0;
  int hour = 0, minute = 0, second = 0;
  int weekday = 0;   // 0=周日
  bool valid = false;
};
Clock now();

// ---------------- 天气（和风天气）----------------
enum class WeatherState : uint8_t { Idle, Ok, NoConfig, HttpFail, ParseFail };

struct Weather {
  WeatherState state = WeatherState::Idle;
  int tempC = 0;
  int tempMin = 0;
  int tempMax = 0;
  char text[28] = {};     // 天气现象，如"多云"
  char updated[16] = {};  // 观测时间 HH:MM
  // ---- 2026-09-11 新增：天气屏图标与详情 ----
  // 和风 /v7/weather/now 本来就带这些字段，之前只取了温度和天气现象，
  // 导致屏右半区整块空白。全部来自同一个响应，不额外发请求。
  char icon[8] = {};        // 图标代码，如 "101"（多云）→ apps 侧映射成矢量图标
  int  humidity = 0;        // 相对湿度 %
  int  feelsLike = 0;       // 体感温度 °C
  int  cloud = 0;           // 云量 %
  char windDir[24] = {};    // 风向，如"东南风"
  char windScale[8] = {};   // 风力等级，如"1-3"
  bool hasDetail = false;   // 以上详情是否拿到（老响应缺失时不画，避免显示 0）
  uint32_t lastTryMs = 0;
};

// host/key 为空时直接置 NoConfig，不发请求。
// 和风新版要求使用项目专属 API Host（形如 xxxxxxxx.re.qweatherapi.com）。
bool fetchWeather(Weather &out, const char *host, const char *key, const char *location);

const char *weatherStateName(WeatherState s);

// ---------------- ChatGPT 用量（自建 sub2api）----------------
// 接口：GET <base>/v1/usage，用 API Key 认证（不需要 JWT）。
// 两种返回模式都解析：有总额度 -> quota；订阅套餐 -> subscription。
struct Usage {
  bool ok = false;
  char mode[20] = {};     // quota_limited | unrestricted
  char plan[40] = {};     // 订阅模式下的套餐名
  bool hasQuota = false;
  double quotaLimit = 0, quotaUsed = 0, quotaRemaining = 0;
  bool hasSub = false;
  double dayUsed = 0, dayLimit = 0;
  double weekUsed = 0, weekLimit = 0;
  double monthUsed = 0, monthLimit = 0;
  // 钱包余额模式（sub2api 默认）：没有额度上限，只有余额 + 累计/今日消耗
  bool hasWallet = false;
  double balance = 0;
  double todayCost = 0, totalCost = 0;
  long todayRequests = 0, totalRequests = 0;
  long long totalTokens = 0;
  char topModel[28] = {};
  double topModelCost = 0;
  char err[56] = {};
  uint32_t lastTryMs = 0;
};

// host 形如 www.papaclaoud.top（只走 443）。key 为空则直接置错，不发请求。
bool fetchUsage(Usage &out, const char *host, const char *apiKey);

// ---------------- 上游账号额度（sub2api 账号管理）----------------
// 接口：GET <host>/api/v1/admin/accounts/<id>，用 admin API Key 认证
//（请求头 x-api-key: admin-...）。
// 实测额度就在 data.extra 里，不需要 POST 探测：
//   codex_primary_used_percent / codex_primary_window_minutes / codex_primary_reset_at
//   codex_secondary_*、codex_reset_credit_snapshot.available_count
struct AccountQuota {
  bool ok = false;
  long accountId = 0;
  char name[32] = {};
  char status[20] = {};        // active / rate_limited / ...
  bool rateLimited = false;
  bool hasPrimary = false;
  int primaryPercent = 0, primaryWindowMin = 0;
  char primaryReset[16] = {};  // "09-15 09:25"
  bool hasSecondary = false;
  int secondaryPercent = 0, secondaryWindowMin = 0;
  char secondaryReset[16] = {};
  int resetCredits = 0;
  char updatedAt[16] = {};
  char err[56] = {};
  uint32_t lastTryMs = 0;
};

bool fetchAccountQuota(AccountQuota &out, const char *host, const char *adminKey, long accountId);

// 把 "2026-09-15T09:25:03+08:00" 压成 "09-15 09:25"（点分纯逻辑，便于复用）
void isoToShort(const char *iso, char *out, unsigned n);
// 把窗口分钟数写成 "7天" / "5小时" / "45分钟"
void windowLabel(int minutes, char *out, unsigned n);

}  // namespace netlink
