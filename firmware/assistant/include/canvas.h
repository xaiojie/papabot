// PSRAM 帧缓冲画布：所有绘图先写内存，提交时只把脏矩形推给屏。
//
// 设计取舍：每个绘图基元自动把自身范围并进脏矩形，应用层不需要手工标记 damage，
// 漏标就会花屏——自动并集虽然多算一点，但不会出错。
#pragma once
#include <Adafruit_ST7789.h>
#include <cstdint>
#include "config.h"
#include "dirty.h"

namespace gfx {

// 1bpp 中文点阵，格式见 scripts/make_cjk_font.py 的说明
class CjkFont {
 public:
  void load(const uint8_t *blob, uint32_t bytes);
  bool ready() const { return ready_; }
  int px() const { return px_; }
  // 命中则返回字形位图（逐行、行按字节对齐），否则返回 nullptr
  const uint8_t *glyph(uint16_t cp, int &w, int &h, int &rowBytes) const;

 private:
  const uint8_t *data_ = nullptr;
  uint32_t count_ = 0;
  uint32_t bitsOff_ = 0;
  uint8_t px_ = 0;
  bool ready_ = false;
};

class Canvas {
 public:
  // 在 PSRAM 里分配帧缓冲。失败返回 false（不降级到内部 RAM，150 KB 放不下）。
  bool begin(Adafruit_ST7789 *display);

  uint16_t *buffer() { return fb_; }
  int width() const { return cfg::SCREEN_W; }
  int height() const { return cfg::SCREEN_H; }

  void setSpiHz(uint32_t hz) { spiHz_ = hz; }
  uint32_t spiHz() const { return spiHz_; }

  // ---- 绘图（都会自动并入脏矩形）----
  void clear(uint16_t color = cfg::C_BG);
  void pixel(int x, int y, uint16_t color);
  void fillRect(int x, int y, int w, int h, uint16_t color);
  void rectOutline(int x, int y, int w, int h, uint16_t color);
  void fillCircle(int cx, int cy, int r, uint16_t color);
  void ring(int cx, int cy, int rOuter, int thickness, uint16_t color);
  void stadium(int cx, int cy, int w, int h, uint16_t color);          // 竖向胶囊（眼睛）
  void brushLine(int x0, int y0, int x1, int y1, int radius, uint16_t color);  // 圆头粗线
  void arcStroke(int cx, int cy, int r, float a0, float a1, int width, uint16_t color);
  // 支持 UTF-8：ASCII 走 5x7 点阵按 scale 放大；汉字查中文点阵
  // （scale<=2 用 16px，>=3 用 24px），找不到字形就画空心方块占位。
  void text(int x, int y, const char *s, uint16_t color, int scale = 1);
  // 把 256 色索引图按调色板画到 (x,y)。动画帧就是这么上屏的：
  // 索引用差分省 flash，颜色靠一次性转好的 RGB565 调色板，每个像素只做一次查表。
  void blitIndexed(int x, int y, int w, int h, const uint8_t *idx, const uint16_t *pal);
  int textWidth(const char *s, int scale = 1) const;

  // ---- 提交 ----
  // 只把脏矩形推给屏；返回本次传输耗时（微秒）。dirty 为空则什么都不做。
  uint32_t flush();
  void damageAll();
  void damage(int x, int y, int w, int h);
  const Rect &damageRect() const { return dirty_; }

 private:
  void plot(int x, int y, uint16_t color);
  void drawMono(int x, int y, const uint8_t *bits, int w, int h, int rowBytes, uint16_t color);
  const CjkFont &cjkFor(int scale) const { return (scale <= 2) ? cjk16_ : cjk24_; }

  Adafruit_ST7789 *display_ = nullptr;
  uint16_t *fb_ = nullptr;
  Rect dirty_{};
  uint32_t spiHz_ = cfg::SPI_HZ_DEFAULT;
  CjkFont cjk16_, cjk24_;
};

}  // namespace gfx
