#include "apps.h"

#include "anim.h"

#include <Arduino.h>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <cstring>

#include "config.h"

using gfx::Canvas;

namespace apps {
namespace {

constexpr float kPi = 3.14159265358979f;

// ---------------- 表情状态 ----------------
const char *kMoods[] = {"happy", "curious", "surprised", "sleepy", "sad"};
constexpr int kMoodCount = 5;
int s_mood = 0;
uint32_t s_blinkT = 0;
bool s_blinking = false;
float s_lookX = 0, s_lookTarget = 0;
int s_lastCaptionMood = -1;

// 表情的动态区域：眼 + 嘴。文字在下方，是静态的，不参与每帧重画。
constexpr int kFaceDynX = 80, kFaceDynY = 54, kFaceDynW = 160, kFaceDynH = 136;

void statusBar(Canvas &c, const UiContext &ctx) {
  c.fillRect(0, 0, cfg::SCREEN_W, 26, cfg::C_STATUSBAR);
  c.fillCircle(16, 13, 5, ctx.wifiUp ? cfg::C_EYE : cfg::C_TICK_DIM);
  c.text(28, 5, ctx.wifiUp ? "已连接" : "无网络", cfg::C_TEXT, 2);
  char t[8];
  if (ctx.clock.valid) snprintf(t, sizeof t, "%02d:%02d", ctx.clock.hour, ctx.clock.minute);
  else                 snprintf(t, sizeof t, "--:--");
  c.text(cfg::SCREEN_W - 8 - c.textWidth(t, 2), 5, t, cfg::C_TEXT, 2);
}

// 页点用 UiContext 里的真实屏幕总数 —— 之前用 count()（枚举数量），
// 加了 GIF 动画屏之后就对不上了。
void pageDots(Canvas &c, const UiContext &ctx, int index) {
  const int n = ctx.screenTotal > 0 ? ctx.screenTotal : count();
  const int gap = n > 8 ? 13 : 16;
  const int x0 = cfg::SCREEN_W / 2 - (n - 1) * gap / 2;
  for (int k = 0; k < n; ++k) {
    c.fillCircle(x0 + k * gap, 226, 3, k == index ? cfg::C_EYE : cfg::C_TICK_DIM);
  }
}

void dateLine(char *buf, size_t n, const netlink::Clock &clk) {
  static const char *wd[] = {"周日", "周一", "周二", "周三", "周四", "周五", "周六"};
  if (!clk.valid) { snprintf(buf, n, "时间同步中"); return; }
  snprintf(buf, n, "%d年%d月%d日 %s", clk.year, clk.month, clk.day, wd[clk.weekday % 7]);
}

// ---------------- ① 表情 ----------------
void faceDraw(Canvas &c, uint32_t nowMs) {
  const int bob = static_cast<int>(std::sin(nowMs / 700.0f) * 3.0f);
  const int cy = cfg::FACE_EYE_CY + bob;

  int ew = cfg::FACE_EYE_W, eh = cfg::FACE_EYE_H;
  if (s_blinking) {
    const float ph = std::fabs(std::cos(s_blinkT / 140.0f * kPi));
    eh = static_cast<int>(6 + (cfg::FACE_EYE_H - 6) * ph);
  }
  if (s_mood == 1)      { eh = 70; ew = 34; }   // 好奇
  else if (s_mood == 3) { eh = 26; }            // 困倦
  else if (s_mood == 2) { ew = 44; eh = 44; }   // 惊讶
  else if (s_mood == 4) { eh = 58; }            // 难过

  const int cxm = cfg::SCREEN_W / 2;
  const int dx = static_cast<int>(s_lookX);
  c.stadium(cxm - cfg::FACE_EYE_DX + dx, cy, ew, eh, cfg::C_EYE);
  c.stadium(cxm + cfg::FACE_EYE_DX + dx, cy, ew, eh, cfg::C_EYE);

  const int my = cfg::FACE_MOUTH_CY + bob;
  if (s_mood == 2) {                                    // 惊讶：小圆嘴
    c.fillCircle(cxm, my + 30, 14, cfg::C_EYE);
  } else if (s_mood == 4) {                             // 难过：倒弧（∩）
    c.arcStroke(cxm, my + 50, cfg::FACE_MOUTH_R, 1.15f * kPi, 1.85f * kPi, 9, cfg::C_EYE);
  } else if (s_mood == 3) {                             // 困倦：短平线
    c.brushLine(cxm - 14, my + 34, cxm + 14, my + 34, 4, cfg::C_EYE);
  } else {                                              // 开心 / 好奇：微笑弧
    c.arcStroke(cxm, my, cfg::FACE_MOUTH_R, 0.22f * kPi, 0.78f * kPi, 9, cfg::C_EYE);
  }
}

const char *faceCaption(int mood) {
  switch (mood) {
    case 0: return "你好呀";
    case 2: return "哇！";
    case 3: return "困了";
    case 4: return "嗯";
    default: return "";
  }
}

void faceDrawCaption(Canvas &c) {
  c.fillRect(0, cfg::FACE_TEXT_Y - 6, cfg::SCREEN_W, 40, cfg::C_BG);
  const char *cap = faceCaption(s_mood);
  if (*cap) {
    c.text(cfg::SCREEN_W / 2 - c.textWidth(cap, 3) / 2, cfg::FACE_TEXT_Y, cap, cfg::C_EYE_SOFT, 3);
  }
}

// ---------------- ② 数字时钟 ----------------
void clockDigitalDraw(Canvas &c, const UiContext &ctx) {
  statusBar(c, ctx);
  char t[8];
  if (ctx.clock.valid) snprintf(t, sizeof t, "%02d:%02d", ctx.clock.hour, ctx.clock.minute);
  else                 snprintf(t, sizeof t, "--:--");
  c.text(cfg::SCREEN_W / 2 - c.textWidth(t, 10) / 2, 58, t, cfg::C_EYE, 10);

  char d[40];
  dateLine(d, sizeof d, ctx.clock);
  c.text(cfg::SCREEN_W / 2 - c.textWidth(d, 2) / 2, 152, d, cfg::C_TEXT, 2);

  const char *n = ctx.nickname;
  c.text(cfg::SCREEN_W / 2 - c.textWidth(n, 2) / 2, 186, n, cfg::C_EYE_SOFT, 2);
  pageDots(c, ctx, 1);
}

// ---------------- ③ 表盘时钟 ----------------
void analogDraw(Canvas &c, const UiContext &ctx) {
  statusBar(c, ctx);
  const int cx = cfg::ANALOG_CX, cy = cfg::ANALOG_CY, R = cfg::ANALOG_R;
  const float ah = (ctx.clock.hour % 12 + ctx.clock.minute / 60.0f) * kPi / 6.0f - kPi / 2;
  const float am = (ctx.clock.minute + ctx.clock.second / 60.0f) * kPi / 30.0f - kPi / 2;
  const float as = ctx.clock.second * kPi / 30.0f - kPi / 2;

  c.ring(cx, cy, R, 3, cfg::C_RING);
  for (int i = 0; i < 60; ++i) {
    const float a = i * kPi / 30.0f - kPi / 2;
    const bool big = (i % 5 == 0);
    const float r0 = R - (big ? 14 : 7), r1 = R - 3;
    c.brushLine(cx + static_cast<int>(std::cos(a) * r0), cy + static_cast<int>(std::sin(a) * r0),
                cx + static_cast<int>(std::cos(a) * r1), cy + static_cast<int>(std::sin(a) * r1),
                big ? 2 : 1, big ? cfg::C_EYE : cfg::C_TICK_DIM);
  }
  c.brushLine(cx, cy, cx + static_cast<int>(std::cos(ah) * R * 0.48f),
              cy + static_cast<int>(std::sin(ah) * R * 0.48f), 4, cfg::C_EYE);
  c.brushLine(cx, cy, cx + static_cast<int>(std::cos(am) * R * 0.72f),
              cy + static_cast<int>(std::sin(am) * R * 0.72f), 3, cfg::C_EYE_SOFT);
  c.brushLine(cx - static_cast<int>(std::cos(as) * 13), cy - static_cast<int>(std::sin(as) * 13),
              cx + static_cast<int>(std::cos(as) * R * 0.84f),
              cy + static_cast<int>(std::sin(as) * R * 0.84f), 1, cfg::C_SECOND);
  c.fillCircle(cx, cy, 4, cfg::C_EYE);

  char d[32];
  dateLine(d, sizeof d, ctx.clock);
  c.text(cfg::SCREEN_W / 2 - c.textWidth(d, 2) / 2, 196, d, cfg::C_DIM, 2);
  pageDots(c, ctx, 2);
}

// ---------------- ④ 天气 ----------------
// 和风 /v7/weather/now 除了温度还返回 icon 代码（100 晴、101 多云、305 小雨 …）
// 和湿度/体感/风向/风力/云量。之前只取了温度和现象，所以屏右半区整块是空的。
//
// 图标全部用画布已有的基元（圆 + 圆头粗线）现场画，不走位图：
//   · 不占 flash（位图 8 类 × 2 套尺寸至少要几十 KB）
//   · 不依赖任何素材文件，改配色只要动 cfg 里的颜色常量
//   · 脏矩形自动跟着走，和现有渲染管线一套逻辑

enum class WIcon : uint8_t { Sunny, Moon, Partly, Cloud, Rain, Thunder, Snow, Fog, Unknown };

// 和风图标代码 → 图标种类。分 8 类足够覆盖日常天气；未知代码退回问号，不画错。
WIcon weatherIconKind(const char *code) {
  const int n = atoi(code ? code : "");
  switch (n) {
    case 100: return WIcon::Sunny;                                  // 晴
    case 150: return WIcon::Moon;                                   // 晴（夜）
    case 101: case 102: case 103:                                   // 多云 / 少云 / 晴间多云
    case 151: case 152: case 153: return WIcon::Partly;
    case 104: case 154: return WIcon::Cloud;                        // 阴
    case 300: case 301: case 305: case 306: case 307: case 308:     // 阵雨 ~ 特大暴雨
    case 309: case 310: case 311: case 312: case 313: case 314:
    case 315: case 316: case 317: case 318: case 350: case 351:
    case 399: return WIcon::Rain;
    case 302: case 303: case 304: return WIcon::Thunder;            // 雷阵雨
    case 400: case 401: case 402: case 403: case 404: case 405:     // 小雪 ~ 暴雪 / 雨夹雪
    case 406: case 407: case 408: case 409: case 410: case 456:
    case 457: case 499: return WIcon::Snow;
    case 500: case 501: case 502: case 503: case 504: case 505:     // 雾 / 霾 / 沙尘
    case 506: case 507: case 508: case 509: case 510: case 511:
    case 512: case 513: case 514: case 515: case 900: case 901:
      return WIcon::Fog;
    default: return WIcon::Unknown;
  }
}

// 一朵云：三个圆堆出团块 + 一条圆头粗线做平底。整体约 0.72*S 宽、0.58*S 高。
void blobCloud(Canvas &c, int cx, int cy, int S, uint16_t col) {
  c.fillCircle(cx - S * 20 / 100, cy + S * 2 / 100,  S * 15 / 100, col);
  c.fillCircle(cx + S * 2 / 100,  cy - S * 10 / 100, S * 20 / 100, col);
  c.fillCircle(cx + S * 22 / 100, cy + S * 3 / 100,  S * 14 / 100, col);
  c.brushLine(cx - S * 20 / 100, cy + S * 13 / 100,
              cx + S * 22 / 100, cy + S * 13 / 100, S * 15 / 100, col);
}

// 阳光芒：在 r0..r1 之间均匀画 8 根圆头粗线
void sunRays(Canvas &c, int cx, int cy, int r0, int r1, int w, uint16_t col) {
  for (int i = 0; i < 8; ++i) {
    const float a = i * kPi / 4.0f;
    c.brushLine(cx + static_cast<int>(std::cos(a) * r0),
                cy + static_cast<int>(std::sin(a) * r0),
                cx + static_cast<int>(std::cos(a) * r1),
                cy + static_cast<int>(std::sin(a) * r1), w, col);
  }
}

// 降水元素：以 cx 为中心横向排 count 个。snow=true 画小十字（雪），否则画斜线（雨）
void precipitation(Canvas &c, int cx, int S, int y0, int y1, int count, bool snow, uint16_t col) {
  const int step = S * 16 / 100;
  const int x0 = cx - (count - 1) * step / 2;
  for (int i = 0; i < count; ++i) {
    const int x = x0 + i * step;
    if (snow) {
      c.brushLine(x - S * 4 / 100, y1, x + S * 4 / 100, y1, S * 2 / 100, col);
      c.brushLine(x, y1 - S * 4 / 100, x, y1 + S * 4 / 100, S * 2 / 100, col);
    } else {
      c.brushLine(x, y0, x - S * 6 / 100, y1, S * 4 / 100, col);
    }
  }
}

// 以 (cx,cy) 为中心画一个标称边长 S 的天气图标
void drawWeatherIcon(Canvas &c, int cx, int cy, int S, WIcon kind) {
  switch (kind) {
    case WIcon::Sunny: {
      const int r = S * 25 / 100;
      sunRays(c, cx, cy, r * 135 / 100, r * 180 / 100, S * 5 / 100, cfg::C_SECOND);
      c.fillCircle(cx, cy, r, cfg::C_SECOND);
      break;
    }
    case WIcon::Moon: {
      const int r = S * 30 / 100;
      c.fillCircle(cx, cy, r, cfg::C_EYE_SOFT);
      // 用底色圆"挖"掉一块得到月牙。天气屏背景是纯黑，等价于布尔差集；
      // 挖除圆的半径刻意留在图标框内，不会擦到别的元素。
      c.fillCircle(cx + r * 45 / 100, cy - r * 32 / 100, r * 92 / 100, cfg::C_BG);
      break;
    }
    case WIcon::Partly: {
      const int sr = S * 16 / 100;
      const int sx = cx - S * 16 / 100, sy = cy - S * 18 / 100;
      sunRays(c, sx, sy, sr * 135 / 100, sr * 175 / 100, S * 4 / 100, cfg::C_SECOND);
      c.fillCircle(sx, sy, sr, cfg::C_SECOND);
      blobCloud(c, cx + S * 5 / 100, cy + S * 8 / 100, S * 78 / 100, cfg::C_EYE);
      break;
    }
    case WIcon::Cloud:
      // 两朵错开，前面那朵亮、后面那朵暗，做出层次
      blobCloud(c, cx - S * 8 / 100, cy - S * 6 / 100, S * 78 / 100, cfg::C_DIM);
      blobCloud(c, cx + S * 5 / 100, cy + S * 7 / 100, S * 82 / 100, cfg::C_EYE);
      break;
    case WIcon::Rain:
      blobCloud(c, cx, cy - S * 12 / 100, S * 86 / 100, cfg::C_EYE);
      precipitation(c, cx, S, cy + S * 24 / 100, cy + S * 42 / 100, 3, false, cfg::C_EYE_SOFT);
      break;
    case WIcon::Snow:
      blobCloud(c, cx, cy - S * 12 / 100, S * 86 / 100, cfg::C_EYE);
      precipitation(c, cx, S, cy + S * 26 / 100, cy + S * 34 / 100, 3, true, cfg::C_EYE_SOFT);
      break;
    case WIcon::Thunder: {
      blobCloud(c, cx, cy - S * 14 / 100, S * 86 / 100, cfg::C_EYE);
      // 闪电用暖色，在整屏冷色里做唯一的强调色（和秒针同色）
      const int bx = cx - S * 2 / 100, by = cy + S * 18 / 100, w = S * 5 / 100;
      c.brushLine(bx - S * 9 / 100, by,                bx + S * 3 / 100,  by,                w, cfg::C_SECOND);
      c.brushLine(bx + S * 3 / 100,  by,                bx - S * 2 / 100,  by + S * 12 / 100, w, cfg::C_SECOND);
      c.brushLine(bx - S * 2 / 100,  by + S * 12 / 100, bx + S * 8 / 100,  by + S * 12 / 100, w, cfg::C_SECOND);
      c.brushLine(bx + S * 8 / 100,  by + S * 12 / 100, bx - S * 6 / 100,  by + S * 28 / 100, w, cfg::C_SECOND);
      break;
    }
    case WIcon::Fog:
      blobCloud(c, cx, cy - S * 18 / 100, S * 78 / 100, cfg::C_DIM);
      for (int i = 0; i < 3; ++i) {
        const int y = cy + S * (12 + i * 9) / 100;
        const int half = S * (34 - i * 6) / 100;
        c.brushLine(cx - half, y, cx + half, y, S * 4 / 100, cfg::C_EYE_SOFT);
      }
      break;
    default:
      c.ring(cx, cy, S * 32 / 100, 3, cfg::C_DIM);
      c.text(cx - c.textWidth("?", 4) / 2, cy - S * 16 / 100, "?", cfg::C_DIM, 4);
      break;
  }
}

void weatherDraw(Canvas &c, const UiContext &ctx) {
  statusBar(c, ctx);
  c.text(16, 32, ctx.city, cfg::C_TEXT, 2);

  if (ctx.weather.state != netlink::WeatherState::Ok) {
    const char *st = netlink::weatherStateName(ctx.weather.state);
    c.text(16, 62, "state:", cfg::C_DIM, 1);
    c.text(16 + c.textWidth("state:", 1) + 4, 62, st, cfg::C_SECOND, 1);
    if (ctx.weather.state == netlink::WeatherState::NoConfig) {
      c.text(16, 94, "先在串口配置：", cfg::C_TEXT, 2);
      c.text(16, 120, "set qwhost", cfg::C_DIM, 2);
      c.text(16, 142, "set qwkey", cfg::C_DIM, 2);
    }
    pageDots(c, ctx, 3);
    return;
  }

  const netlink::Weather &w = ctx.weather;

  // ---- 左列：现象 / 大温度 / 高低温 ----
  c.text(16, 52, w.text, cfg::C_TEXT, 2);

  char temp[8];
  snprintf(temp, sizeof temp, "%d", w.tempC);
  c.text(16, 72, temp, cfg::C_EYE, 8);
  c.text(16 + c.textWidth(temp, 8) + 6, 80, "C", cfg::C_EYE, 2);

  if (w.tempMax || w.tempMin) {
    char range[20];
    snprintf(range, sizeof range, "%d~%dC", w.tempMin, w.tempMax);
    c.text(16, 142, range, cfg::C_DIM, 2);
  }

  // ---- 右列：大天气图标（原来这半屏整块是空的）----
  drawWeatherIcon(c, 240, 92, 104, weatherIconKind(w.icon));

  if (w.updated[0]) {
    char obs[24];
    snprintf(obs, sizeof obs, "obs %s", w.updated);
    c.text(cfg::SCREEN_W - 16 - c.textWidth(obs, 1), 148, obs, cfg::C_DIM, 1);
  }

  // ---- 底部：分隔线 + 2×2 详情 ----
  const bool anyDetail = w.hasDetail && (w.humidity > 0 || w.feelsLike != 0 ||
                                        w.windScale[0] || w.cloud > 0);
  if (anyDetail) {
    c.fillRect(16, 164, cfg::SCREEN_W - 32, 1, cfg::C_RING);

    // 48 字节：windDir 最长 23 + windScale 7 + "风 " 与 "级" 的中文各 3 字节，
    // 最坏 38 字节。开 32 会让 -Wformat-truncation 报警，-Wall 下就是噪声。
    char v[48];
    int y = 172;
    if (w.humidity > 0) {
      snprintf(v, sizeof v, "湿度 %d%%", w.humidity);
      c.text(16, y, v, cfg::C_DIM, 2);
    }
    if (w.feelsLike != 0) {
      snprintf(v, sizeof v, "体感 %dC", w.feelsLike);
      c.text(180, y, v, cfg::C_DIM, 2);
    }
    y = 194;
    if (w.windScale[0]) {
      // 不要再加"风"前缀：windDir 本身就是"北风/东南风"，写成"风 北风4级"是重复的
      snprintf(v, sizeof v, "%s%s级", w.windDir, w.windScale);
      c.text(16, y, v, cfg::C_DIM, 2);
    }
    if (w.cloud > 0) {
      snprintf(v, sizeof v, "云量 %d%%", w.cloud);
      c.text(180, y, v, cfg::C_DIM, 2);
    }
  }
  pageDots(c, ctx, 3);
}

// ---------------- ⑤ 账号额度（sub2api 账号管理）----------------
void progressBar(Canvas &c, int x, int y, int w, int h, double used, double limit) {
  c.fillRect(x, y, w, h, cfg::C_BAR_BG);
  if (limit <= 0) return;
  double frac = used / limit;
  if (frac < 0) frac = 0;
  if (frac > 1) frac = 1;
  c.fillRect(x, y, static_cast<int>(w * frac), h, cfg::C_EYE);
}

// 一行「标签 …… 值」，值右对齐
void labelValue(Canvas &c, int y, const char *label, const char *value, uint16_t vcolor) {
  c.text(16, y, label, cfg::C_DIM, 2);
  c.text(cfg::SCREEN_W - 16 - c.textWidth(value, 2), y, value, vcolor, 2);
}

// 一个限额窗口：标签 + 百分比 + 进度条 + 重置时间
void windowBlock(Canvas &c, int y, const char *label, int percent, const char *reset) {
  char pct[8];
  snprintf(pct, sizeof pct, "%d%%", percent);
  c.text(16, y, label, cfg::C_TEXT, 2);
  const uint16_t col = (percent >= 100) ? cfg::C_SECOND : cfg::C_EYE;
  c.text(cfg::SCREEN_W - 16 - c.textWidth(pct, 2), y, pct, col, 2);
  progressBar(c, 16, y + 22, cfg::SCREEN_W - 32, 14, percent, 100);
  c.text(16, y + 42, "重置 ", cfg::C_DIM, 1);
  c.text(16 + c.textWidth("重置 ", 1), y + 42, reset, cfg::C_DIM, 1);
}

void chatGptDraw(Canvas &c, const UiContext &ctx) {
  statusBar(c, ctx);
  const netlink::AccountQuota &q = ctx.quota;

  if (!q.ok) {
    c.text(16, 36, "账号额度", cfg::C_TEXT, 2);
    c.text(16, 74, q.err[0] ? q.err : "正在获取…", cfg::C_SECOND, 2);
    c.text(16, 116, "串口设置：", cfg::C_TEXT, 2);
    c.text(16, 140, "set adminkey", cfg::C_DIM, 2);
    c.text(16, 164, "set account 2839", cfg::C_DIM, 2);
    c.text(16, 188, "quota", cfg::C_EYE_SOFT, 2);
    pageDots(c, ctx, 4);
    return;
  }

  // 标题行：账号名 + 限流状态
  c.text(16, 32, q.name, cfg::C_TEXT, 2);
  {
    const char *badge = q.rateLimited ? "已限流" : "正常";
    const uint16_t bcol = q.rateLimited ? cfg::C_SECOND : cfg::C_EYE;
    c.text(cfg::SCREEN_W - 16 - c.textWidth(badge, 2), 32, badge, bcol, 2);
  }

  char wl[12];
  int y = 62;
  if (q.hasPrimary) {
    netlink::windowLabel(q.primaryWindowMin, wl, sizeof wl);
    windowBlock(c, y, wl, q.primaryPercent, q.primaryReset);
    y += 74;
  }
  if (q.hasSecondary) {
    netlink::windowLabel(q.secondaryWindowMin, wl, sizeof wl);
    windowBlock(c, y, wl, q.secondaryPercent, q.secondaryReset);
    y += 74;
  }

  char val[32];
  if (q.resetCredits > 0) {
    snprintf(val, sizeof val, "%d 张", q.resetCredits);
    labelValue(c, y, "重置券", val, cfg::C_EYE_SOFT);
  }
  if (q.updatedAt[0] && q.updatedAt[0] != '-') {
    snprintf(val, sizeof val, "%s", q.updatedAt);
    c.text(cfg::SCREEN_W - 16 - c.textWidth(val, 1), 210, val, cfg::C_DIM, 1);
    c.text(16, 210, "更新", cfg::C_DIM, 1);
  }
  pageDots(c, ctx, 4);
}

// ---------------- ⑦+ 动画屏（GIF） ----------------
// 索引缓冲放 PSRAM：最大 320x240 = 76,800 字节，PSRAM 有 8 MB，不心疼。
// 每帧只在动画矩形内产生脏矩形，所以推屏耗时按动画大小算，不是整屏。
namespace {
uint8_t *gIdx = nullptr;
int      gIdxW = 0, gIdxH = 0;
int      gFrame = 0;
uint32_t gNextMs = 0;

bool ensureIdx(const anim::Clip &c) {
  if (gIdx && gIdxW == c.w && gIdxH == c.h) return true;
  if (gIdx) { free(gIdx); gIdx = nullptr; }
  const size_t need = static_cast<size_t>(c.w) * c.h;
  gIdx = static_cast<uint8_t *>(heap_caps_malloc(need, MALLOC_CAP_SPIRAM | MALLOC_CAP_8BIT));
  if (!gIdx) { Serial.println("ERR: 动画索引缓冲分配失败"); return false; }
  gIdxW = c.w;
  gIdxH = c.h;
  return true;
}
}  // namespace

// ---------------- ⑥ 状态 ----------------
void sysDraw(Canvas &c, const UiContext &ctx) {
  statusBar(c, ctx);
  c.text(16, 36, "设备状态", cfg::C_TEXT, 2);

  const char *keys[6] = {"信号", "IP", "运行", "内存", "PSRAM", "SPI"};
  char vals[6][24];
  snprintf(vals[0], sizeof vals[0], "%d dBm", ctx.rssi);
  snprintf(vals[1], sizeof vals[1], "%s", ctx.ip);
  snprintf(vals[2], sizeof vals[2], "%lu s", static_cast<unsigned long>(ctx.uptimeMs / 1000));
  snprintf(vals[3], sizeof vals[3], "%lu KB", static_cast<unsigned long>(ctx.freeHeap / 1024));
  snprintf(vals[4], sizeof vals[4], "%lu KB", static_cast<unsigned long>(ctx.freePsram / 1024));
  snprintf(vals[5], sizeof vals[5], "%lu MHz", static_cast<unsigned long>(ctx.spiHz / 1000000));

  for (int i = 0; i < 6; ++i) {
    const int y = 62 + i * 25;
    c.text(20, y, keys[i], cfg::C_DIM, 2);
    c.text(cfg::SCREEN_W - 20 - c.textWidth(vals[i], 2), y, vals[i], cfg::C_EYE, 2);
  }
  pageDots(c, ctx, 5);
}

}  // namespace

const char *name(Id id) {
  switch (id) {
    case Id::Face: return "face";
    case Id::ClockDigital: return "clock";
    case Id::ClockAnalog: return "analog";
    case Id::Weather: return "weather";
    case Id::ChatGpt: return "chatgpt";
    case Id::Sys: return "sys";
    case Id::Anim: return "anim";
    default: return "?";
  }
}

bool animated(Id id) { return id == Id::Face; }
int count() { return static_cast<int>(Id::Count); }

Id at(int index) {
  const int n = count();
  if (n <= 0) return Id::Face;
  int i = index % n;
  if (i < 0) i += n;
  return static_cast<Id>(i);
}
int indexOf(Id id) { return static_cast<int>(id); }

void nextMood() {
  s_mood = (s_mood + 1) % kMoodCount;
  s_lastCaptionMood = -1;
}
const char *moodName() { return kMoods[s_mood]; }

void enter(Id id, Canvas &c, const UiContext &ctx) {
  c.clear(cfg::C_BG);
  switch (id) {
    case Id::Face:
      s_blinking = false;
      s_blinkT = 0;
      s_lookX = s_lookTarget = 0;
      s_lastCaptionMood = -1;
      faceDraw(c, millis());
      faceDrawCaption(c);
      break;
    case Id::ClockDigital: clockDigitalDraw(c, ctx); break;
    case Id::ClockAnalog:  analogDraw(c, ctx);       break;
    case Id::Weather:      weatherDraw(c, ctx);      break;
    case Id::ChatGpt:      chatGptDraw(c, ctx);       break;
    case Id::Sys:          sysDraw(c, ctx);          break;
    default: break;
  }
}

bool update(Id id, Canvas &c, const UiContext &ctx, uint32_t nowMs) {
  static uint32_t s_lastMinuteKey = 0xFFFFFFFFu;
  static int s_lastSecond = -1;

  switch (id) {
    case Id::Face: {
      // 只擦动态区域，脏矩形自然收缩到眼睛+嘴那一块
      c.fillRect(kFaceDynX, kFaceDynY, kFaceDynW, kFaceDynH, cfg::C_BG);

      s_blinkT += 16;
      if (!s_blinking && s_blinkT > 2400u + static_cast<uint32_t>(s_mood % 3) * 700u) {
        s_blinking = true; s_blinkT = 0;
      }
      if (s_blinking && s_blinkT > 150u) { s_blinking = false; s_blinkT = 0; }
      if ((nowMs / 977u) != ((nowMs - 16u) / 977u)) {
        s_lookTarget = static_cast<float>(static_cast<int>(nowMs % 25u) - 12);
      }
      s_lookX += (s_lookTarget - s_lookX) * 0.12f;

      faceDraw(c, nowMs);
      if (s_lastCaptionMood != s_mood) { faceDrawCaption(c); s_lastCaptionMood = s_mood; }
      return true;
    }
    case Id::ClockDigital: {
      const uint32_t key = static_cast<uint32_t>(ctx.clock.hour) * 60u + ctx.clock.minute;
      if (key != s_lastMinuteKey) {
        s_lastMinuteKey = key;
        if (ctx.clock.valid) { clockDigitalDraw(c, ctx); return true; }
      }
      return false;
    }
    case Id::ClockAnalog: {
      if (ctx.clock.valid && ctx.clock.second != s_lastSecond) {
        s_lastSecond = ctx.clock.second;
        analogDraw(c, ctx);          // 每秒整盘重绘一次：占空比仅约 3.5%
        return true;
      }
      return false;
    }
    case Id::ChatGpt: {
      // 数值可能在后台下发后变化，比对一下再决定要不要重画
      static uint32_t lastSig = 0xFFFFFFFFu;
      const netlink::AccountQuota &q = ctx.quota;
      const uint32_t sig = (q.ok ? 1u : 0u) ^ (static_cast<uint32_t>(q.primaryPercent) << 1) ^
                           (static_cast<uint32_t>(q.secondaryPercent) << 9) ^
                           (static_cast<uint32_t>(q.rateLimited) << 17) ^
                           (static_cast<uint32_t>(q.resetCredits) << 18) ^
                           (static_cast<uint32_t>(q.err[0]) << 24);
      if (sig != lastSig) { lastSig = sig; chatGptDraw(c, ctx); return true; }
      return false;
    }
    default:
      return false;                  // 静态屏：只有 enter() 或数据变化时才重画
  }
}

void enterAnim(Canvas &c, const UiContext &ctx, int clip) {
  (void)ctx;
  const anim::Clip *cl = anim::at(clip);
  if (!cl) return;
  c.clear();                       // 两侧留黑边；只在进入这一屏时清一次
  if (!ensureIdx(*cl)) return;
  if (!anim::decode(*cl, 0, gIdx)) return;
  gFrame = 0;
  c.blitIndexed((cfg::SCREEN_W - cl->w) / 2, (cfg::SCREEN_H - cl->h) / 2,
                cl->w, cl->h, gIdx, cl->palette);
  gNextMs = millis() + cl->delayMs;
}

bool updateAnim(Canvas &c, const UiContext &ctx, int clip, uint32_t now) {
  (void)ctx;
  const anim::Clip *cl = anim::at(clip);
  if (!cl || !gIdx || cl->w != gIdxW || cl->h != gIdxH) return false;
  if (now < gNextMs) return false;
  gNextMs = now + cl->delayMs;
  gFrame = (gFrame + 1) % cl->frames;
  if (!anim::decode(*cl, gFrame, gIdx)) return false;
  c.blitIndexed((cfg::SCREEN_W - cl->w) / 2, (cfg::SCREEN_H - cl->h) / 2,
                cl->w, cl->h, gIdx, cl->palette);
  return true;
}

int screenCount() {
  const int n = anim::count();
  return kFixedCount + (n > 0 ? n : 0);
}

Id idAtScreen(int pos) {
  if (pos < 0) pos = 0;
  if (pos < kFixedCount) return static_cast<Id>(pos);
  return anim::count() > 0 ? Id::Anim : Id::Face;
}

int animAtScreen(int pos) {
  if (pos < kFixedCount || anim::count() <= 0) return -1;
  const int i = pos - kFixedCount;
  return (i < anim::count()) ? i : -1;
}


}  // namespace apps
