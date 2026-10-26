#include "canvas.h"

#include <Arduino.h>
#include <esp_heap_caps.h>
#include <cmath>

// 由 platformio.ini 的 board_build.embed_files 嵌进来的中文点阵
extern const uint8_t cjk16_bin_start[] asm("_binary_data_cjk16_bin_start");
extern const uint8_t cjk16_bin_end[]   asm("_binary_data_cjk16_bin_end");
extern const uint8_t cjk24_bin_start[] asm("_binary_data_cjk24_bin_start");
extern const uint8_t cjk24_bin_end[]   asm("_binary_data_cjk24_bin_end");

namespace gfx {

namespace {
inline uint16_t rd16(const uint8_t *p) { return static_cast<uint16_t>(p[0] | (p[1] << 8)); }
inline uint32_t rd32(const uint8_t *p) {
  return static_cast<uint32_t>(p[0]) | (static_cast<uint32_t>(p[1]) << 8) |
         (static_cast<uint32_t>(p[2]) << 16) | (static_cast<uint32_t>(p[3]) << 24);
}
}  // namespace

// 5x7 ASCII 字模（1280 字节，取自 Adafruit GFX glcdfont.c，见 src/font_ascii.cpp）
extern const uint8_t kAscii5x7[1280];

void CjkFont::load(const uint8_t *blob, uint32_t bytes) {
  if (!blob || bytes < 16u || memcmp(blob, "CJK1", 4) != 0) {
    Serial.printf("CJK font: bad blob (%u bytes)\n", static_cast<unsigned>(bytes));
    return;
  }
  px_ = blob[4];
  count_ = rd32(blob + 8);
  bitsOff_ = rd32(blob + 12);
  if (16u + count_ * 8u > bytes || bitsOff_ > bytes) {
    Serial.println("CJK font: header out of range");
    return;
  }
  data_ = blob;
  ready_ = true;
  Serial.printf("CJK font: %upx, %u glyphs, %u KB\n", px_,
                static_cast<unsigned>(count_), static_cast<unsigned>(bytes / 1024u));
}

const uint8_t *CjkFont::glyph(uint16_t cp, int &w, int &h, int &rowBytes) const {
  if (!ready_) return nullptr;
  uint32_t lo = 0, hi = count_;               // 记录已按码点升序，二分查找
  while (lo < hi) {
    const uint32_t mid = lo + (hi - lo) / 2;
    const uint8_t *rec = data_ + 16u + mid * 8u;
    const uint16_t c = rd16(rec);
    if (c == cp) {
      w = rec[6]; h = rec[7];
      rowBytes = (w + 7) / 8;
      return data_ + bitsOff_ + rd32(rec + 2);
    }
    if (c < cp) lo = mid + 1; else hi = mid;
  }
  return nullptr;
}

void Canvas::blitIndexed(int x, int y, int w, int h, const uint8_t *idx,
                         const uint16_t *pal) {
  if (!fb_ || !idx || !pal) return;
  for (int row = 0; row < h; ++row) {
    const int py = y + row;
    if (py < 0 || py >= cfg::SCREEN_H) continue;
    const uint8_t *src = idx + static_cast<size_t>(row) * w;
    uint16_t *dst = fb_ + static_cast<size_t>(py) * cfg::SCREEN_W + x;
    for (int col = 0; col < w; ++col) {
      const int px = x + col;
      if (px < 0 || px >= cfg::SCREEN_W) continue;
      dst[col] = pal[src[col]];
    }
  }
  damage(x, y, w, h);
}

void Canvas::drawMono(int x, int y, const uint8_t *bits, int w, int h, int rowBytes,
                      uint16_t color) {
  for (int row = 0; row < h; ++row) {
    const uint8_t *src = bits + row * rowBytes;
    for (int col = 0; col < w; ++col) {
      if (src[col >> 3] & (0x80u >> (col & 7))) plot(x + col, y + row, color);
    }
  }
  damage(x, y, w, h);
}

bool Canvas::begin(Adafruit_ST7789 *display) {
  display_ = display;
  const size_t bytes = static_cast<size_t>(cfg::SCREEN_W) * cfg::SCREEN_H * sizeof(uint16_t);
  fb_ = static_cast<uint16_t *>(heap_caps_malloc(bytes, MALLOC_CAP_SPIRAM | MALLOC_CAP_8BIT));
  if (!fb_) {
    Serial.printf("ERR: framebuffer alloc failed (%u bytes PSRAM)\n", static_cast<unsigned>(bytes));
    return false;
  }
  Serial.printf("framebuffer: %u bytes in PSRAM, %u free after alloc\n",
                static_cast<unsigned>(bytes), static_cast<unsigned>(ESP.getFreePsram()));
  cjk16_.load(cjk16_bin_start, static_cast<uint32_t>(cjk16_bin_end - cjk16_bin_start));
  cjk24_.load(cjk24_bin_start, static_cast<uint32_t>(cjk24_bin_end - cjk24_bin_start));
  clear();
  return true;
}

void Canvas::damage(int x, int y, int w, int h) {
  Rect r{static_cast<int16_t>(x), static_cast<int16_t>(y),
         static_cast<int16_t>(w), static_cast<int16_t>(h)};
  if (clipRect(r, cfg::SCREEN_W, cfg::SCREEN_H)) unionRect(dirty_, r);
}

void Canvas::damageAll() {
  dirty_ = {0, 0, static_cast<int16_t>(cfg::SCREEN_W), static_cast<int16_t>(cfg::SCREEN_H)};
}

inline void Canvas::plot(int x, int y, uint16_t color) {
  if (x < 0 || y < 0 || x >= cfg::SCREEN_W || y >= cfg::SCREEN_H) return;
  fb_[static_cast<size_t>(y) * cfg::SCREEN_W + x] = color;
}

void Canvas::clear(uint16_t color) {
  const size_t n = static_cast<size_t>(cfg::SCREEN_W) * cfg::SCREEN_H;
  for (size_t i = 0; i < n; ++i) fb_[i] = color;
  damageAll();
}

void Canvas::pixel(int x, int y, uint16_t color) {
  plot(x, y, color);
  damage(x, y, 1, 1);
}

void Canvas::fillRect(int x, int y, int w, int h, uint16_t color) {
  if (w <= 0 || h <= 0) return;
  int x0 = x, y0 = y, x1 = x + w, y1 = y + h;
  if (x0 < 0) x0 = 0;
  if (y0 < 0) y0 = 0;
  if (x1 > cfg::SCREEN_W) x1 = cfg::SCREEN_W;
  if (y1 > cfg::SCREEN_H) y1 = cfg::SCREEN_H;
  if (x1 <= x0 || y1 <= y0) return;
  for (int yy = y0; yy < y1; ++yy) {
    uint16_t *row = fb_ + static_cast<size_t>(yy) * cfg::SCREEN_W;
    for (int xx = x0; xx < x1; ++xx) row[xx] = color;
  }
  damage(x0, y0, x1 - x0, y1 - y0);
}

void Canvas::rectOutline(int x, int y, int w, int h, uint16_t color) {
  fillRect(x, y, w, 1, color);
  fillRect(x, y + h - 1, w, 1, color);
  fillRect(x, y, 1, h, color);
  fillRect(x + w - 1, y, 1, h, color);
}

void Canvas::fillCircle(int cx, int cy, int r, uint16_t color) {
  if (r <= 0) return;
  for (int dy = -r; dy <= r; ++dy) {
    const int span = static_cast<int>(std::sqrt(static_cast<double>(r * r - dy * dy)));
    fillRect(cx - span, cy + dy, span * 2 + 1, 1, color);
  }
}

void Canvas::ring(int cx, int cy, int rOuter, int thickness, uint16_t color) {
  // 外圆填色，再用底色挖内圆；表盘内部本来就是底色，等价且实现简单
  fillCircle(cx, cy, rOuter, color);
  const int inner = rOuter - thickness;
  if (inner > 0) fillCircle(cx, cy, inner, cfg::C_BG);
}

void Canvas::stadium(int cx, int cy, int w, int h, uint16_t color) {
  const int r = w / 2;
  const int hh = (h < w) ? w : h;   // 高度不足时退化成圆
  fillRect(cx - r, cy - hh / 2 + r, w, hh - 2 * r, color);
  fillCircle(cx, cy - hh / 2 + r, r, color);
  fillCircle(cx, cy + hh / 2 - r, r, color);
}

void Canvas::brushLine(int x0, int y0, int x1, int y1, int radius, uint16_t color) {
  const int dx = x1 - x0, dy = y1 - y0;
  const int steps = std::max(std::abs(dx), std::abs(dy));
  if (steps == 0) { fillCircle(x0, y0, radius, color); return; }
  for (int i = 0; i <= steps; ++i) {
    const int x = x0 + dx * i / steps;
    const int y = y0 + dy * i / steps;
    fillCircle(x, y, radius, color);
  }
}

void Canvas::arcStroke(int cx, int cy, int r, float a0, float a1, int width, uint16_t color) {
  const float step = 1.0f / std::max(1.0f, r * 0.6f);   // 弧度步长，半径越大越密
  for (float a = a0; a <= a1; a += step) {
    const int x = cx + static_cast<int>(std::cos(a) * r);
    const int y = cy + static_cast<int>(std::sin(a) * r);
    fillCircle(x, y, width / 2, color);
  }
}

int Canvas::textWidth(const char *s, int scale) const {
  int w = 0;
  const uint8_t *p = reinterpret_cast<const uint8_t *>(s);
  while (*p) {
    if (*p < 0x80u) { w += 6 * scale; p += 1; continue; }
    const bool two = ((*p & 0xE0u) == 0xC0u);
    const bool three = ((*p & 0xF0u) == 0xE0u);
    if (!two && !three) { w += 6 * scale; p += 1; continue; }
    const CjkFont &f = cjkFor(scale);
    w += f.ready() ? f.px() : 24;
    p += two ? 2 : 3;
  }
  return w;
}

void Canvas::text(int x, int y, const char *s, uint16_t color, int scale) {
  int cx = x;
  const uint8_t *p = reinterpret_cast<const uint8_t *>(s);
  while (*p) {
    uint32_t cp = 0;
    int adv = 1;
    if (*p < 0x80u) {
      cp = *p;
    } else if ((*p & 0xE0u) == 0xC0u && p[1]) {
      cp = ((*p & 0x1Fu) << 6) | (p[1] & 0x3Fu); adv = 2;
    } else if ((*p & 0xF0u) == 0xE0u && p[1] && p[2]) {
      cp = ((*p & 0x0Fu) << 12) | ((p[1] & 0x3Fu) << 6) | (p[2] & 0x3Fu); adv = 3;
    } else {
      cp = '?';
    }
    p += adv;

    if (cp == '\n') { cx = x; y += 8 * scale; continue; }

    if (cp < 0x80u) {
      const uint8_t *glyphbits = &kAscii5x7[cp * 5];
      for (int col = 0; col < 5; ++col) {
        const uint8_t bits = glyphbits[col];
        for (int row = 0; row < 8; ++row) {
          if ((bits >> row) & 1) fillRect(cx + col * scale, y + row * scale, scale, scale, color);
        }
      }
      cx += 6 * scale;
      continue;
    }

    // 汉字：查点阵；查不到画空心方块占位（宽度仍按全角算，布局不塌）
    const CjkFont &f = cjkFor(scale);
    int gw = 0, gh = 0, rb = 0;
    const uint8_t *bits = f.ready() ? f.glyph(static_cast<uint16_t>(cp), gw, gh, rb) : nullptr;
    if (bits) {
      drawMono(cx, y, bits, gw, gh, rb, color);
      cx += f.px();
    } else {
      const int box = f.ready() ? f.px() : 24;
      fillRect(cx + 1, y + 1, box - 2, box - 2, color);
      fillRect(cx + 1 + scale, y + 1 + scale, box - 2 - 2 * scale, box - 2 - 2 * scale,
               cfg::C_BG);
      cx += box;
    }
  }
}

uint32_t Canvas::flush() {
  if (dirty_.empty() || !display_) { dirty_.reset(); return 0; }
  Rect d = dirty_;
  dirty_.reset();
  if (!clipRect(d, cfg::SCREEN_W, cfg::SCREEN_H)) return 0;

  const uint32_t t0 = micros();
  display_->startWrite();
  display_->setAddrWindow(d.x, d.y, d.w, d.h);
  // 子矩形在帧缓冲里不是连续的，所以按行推；地址窗口设一次后会自己按行推进。
  // writePixels 的 len 是像素数，默认参数按本机 uint16_t 顺序处理字节序。
  for (int row = 0; row < d.h; ++row) {
    display_->writePixels(fb_ + static_cast<size_t>(d.y + row) * cfg::SCREEN_W + d.x,
                          static_cast<uint32_t>(d.w));
  }
  display_->endWrite();
  return micros() - t0;
}

}  // namespace gfx
