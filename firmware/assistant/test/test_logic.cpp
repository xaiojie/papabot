// 主机侧单元测试：脏矩形与 SPI 预算。这些逻辑不依赖硬件，先在这里保证正确。
#include "dirty.h"
#include <cstdio>

static int failures = 0, checks = 0;
#define CHECK(e) do { ++checks; if (!(e)) { ++failures; std::printf("FAIL line %d: %s\n", __LINE__, #e); } } while (false)

using namespace gfx;

static void clip_keeps_inside_and_drops_outside() {
  Rect a{10, 10, 20, 20};
  CHECK(clipRect(a, 320, 240));
  CHECK(a.x == 10 && a.y == 10 && a.w == 20 && a.h == 20);

  Rect b{-10, -10, 30, 30};               // 左上溢出 → 裁到 (0,0) 20x20
  CHECK(clipRect(b, 320, 240));
  CHECK(b.x == 0 && b.y == 0 && b.w == 20 && b.h == 20);

  Rect c{310, 230, 40, 40};               // 右下溢出 → 裁到 10x10
  CHECK(clipRect(c, 320, 240));
  CHECK(c.x == 310 && c.y == 230 && c.w == 10 && c.h == 10);

  Rect d{400, 10, 20, 20};                // 完全在界外
  CHECK(!clipRect(d, 320, 240));

  Rect e{10, 10, 0, 20};                  // 空矩形
  CHECK(!clipRect(e, 320, 240));
}

static void union_grows_to_cover_both() {
  Rect acc{};
  unionRect(acc, {108, 66, 36, 64});
  CHECK(acc.x == 108 && acc.y == 66 && acc.w == 36 && acc.h == 64);

  unionRect(acc, {176, 66, 36, 64});      // 另一只眼
  CHECK(acc.x == 108 && acc.y == 66);
  CHECK(acc.w == 104 && acc.h == 64);     // 108..212

  unionRect(acc, {});                     // 空矩形不改变结果
  CHECK(acc.w == 104);
}

static void budget_matches_the_measured_numbers() {
  // 全屏 320x240 @10MHz：应与实测的 122.9 ms 对上
  Rect full{0, 0, 320, 240};
  CHECK(rectBytes(full) == 153600);
  const uint32_t us = rectMicros(full, 10000000u);
  CHECK(us == 122880);                    // 122.88 ms

  // 表情+嘴区域 200x110 @10MHz ≈ 35.2 ms → 约 28 fps
  Rect face{60, 60, 200, 110};
  CHECK(rectBytes(face) == 44000);
  CHECK(rectMicros(face, 10000000u) == 35200);

  // 同样的区域 @40MHz 应快 4 倍
  CHECK(rectMicros(face, 40000000u) == 8800);

  // 除零保护
  CHECK(rectMicros(face, 0) == 0);
}

static void blink_damage_stays_small() {
  // 眨眼只改眼睛的上下边缘附近；两只眼并集应该是窄条形，远小于全屏。
  Rect acc{};
  unionRect(acc, {108, 66, 36, 8});       // 左眼上缘变化
  unionRect(acc, {176, 66, 36, 8});       // 右眼上缘变化
  CHECK(acc.w == 104 && acc.h == 8);
  const int32_t bytes = rectBytes(acc);
  CHECK(bytes == 1664);
  CHECK(bytes < rectBytes(Rect{0, 0, 320, 240}) / 50);   // 不到全屏的 2%
  CHECK(rectMicros(acc, 10000000u) < 1400);              // < 1.4 ms
}

static void second_hand_damage_is_a_thin_wedge() {
  // 秒针从 12 点转到 3 点，两帧覆盖的区域并集应远小于整个表盘
  Rect a{152, 42, 16, 74};    // 指向 12 点
  Rect b{152, 108, 74, 16};   // 指向 3 点
  Rect acc{};
  unionRect(acc, a);
  unionRect(acc, b);
  CHECK(acc.x == 152 && acc.y == 42);
  CHECK(acc.w == 74 && acc.h == 82);
  CHECK(rectBytes(acc) < rectBytes(Rect{0, 0, 148, 148}));   // 比整个表盘小
}

int main() {
  struct T { const char *n; void (*f)(); };
  const T tests[] = {
    {"clip keeps inside and drops outside", clip_keeps_inside_and_drops_outside},
    {"union grows to cover both", union_grows_to_cover_both},
    {"budget matches measured numbers", budget_matches_the_measured_numbers},
    {"blink damage stays small", blink_damage_stays_small},
    {"second hand damage is a thin wedge", second_hand_damage_is_a_thin_wedge},
  };
  for (const auto &t : tests) {
    const int before = failures;
    t.f();
    std::printf("%s: %s\n", before == failures ? "PASS" : "FAIL", t.n);
  }
  std::printf("%zu cases, %d checks, %d failures\n", sizeof(tests)/sizeof(tests[0]), checks, failures);
  return failures == 0 ? 0 : 1;
}
