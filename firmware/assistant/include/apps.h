// 两个程序 = 六屏，旋钮循环切换。
//   ① 表情（会动，唯一需要持续重绘的一屏）
//   ② 数字时钟  ③ 表盘时钟  ④ 天气  ⑤ ChatGPT  ⑥ 状态
//
// 重要：静态屏只在 enter() 或数据变化时重画。如果每帧都画，画布会自动标记脏矩形，
// 结果就是每帧全屏推送（10 MHz 下只有 8 fps）——这正是要避免的。
#pragma once
#include <cstdint>
#include "canvas.h"
#include "net.h"

namespace apps {

enum class Id : uint8_t { Face, ClockDigital, ClockAnalog, Weather, ChatGpt, Sys, Anim, Count };

// 固定 6 屏之外，每部 GIF 动画再占一屏 —— 旋钮转一圈就自然轮过所有动画。
constexpr int kFixedCount = 6;

// 应用层只读的一份共享数据，由 main 每帧填好
struct UiContext {
  netlink::Clock clock;
  netlink::Weather weather;
  netlink::Usage usage;
  netlink::AccountQuota quota;
  const char *nickname = "";
  const char *city = "";
  bool wifiUp = false;
  int rssi = 0;
  const char *ip = "";
  uint32_t uptimeMs = 0;
  uint32_t freeHeap = 0;
  uint32_t freePsram = 0;
  uint32_t spiHz = 0;
  int screenPos = 0;      // 当前屏幕序号
  int screenTotal = 6;    // 屏幕总数（含 GIF 动画屏）
};

const char *name(Id id);

// 屏幕序号 ↔ (Id, 动画序号) 的换算。序号 0..5 是固定屏，之后每部动画一屏。
int screenCount();
Id  idAtScreen(int pos);
int animAtScreen(int pos);          // 非动画屏返回 -1

void enterAnim(gfx::Canvas &c, const UiContext &ctx, int clip);
bool updateAnim(gfx::Canvas &c, const UiContext &ctx, int clip, uint32_t now);
bool animated(Id id);                 // true = 需要每帧 update
int  count();
Id   at(int index);
int  indexOf(Id id);

// 切屏 / 数据变化时调用：清屏并整屏重画一次
void enter(Id id, gfx::Canvas &c, const UiContext &ctx);

// 每帧调用。只有动画屏和到点的时钟屏会真正重绘，其余屏什么都不做。
// 返回 true 表示这一帧有内容变化。
bool update(Id id, gfx::Canvas &c, const UiContext &ctx, uint32_t nowMs);

// 表情专用
void nextMood();
const char *moodName();

}  // namespace apps
