// 脏矩形纯逻辑：不依赖 Arduino，可在主机上单元测试。
//
// 为什么需要它：ST7789 @10 MHz 全屏要 122.9 ms（8 fps），动画根本动不了；
// 只推变化区域才能到 28 fps 以上。所以每个绘图操作都要把自己的范围并进脏矩形。
#pragma once
#include <algorithm>
#include <cstdint>

namespace gfx {

struct Rect {
  int16_t x = 0, y = 0, w = 0, h = 0;
  bool empty() const { return w <= 0 || h <= 0; }
  int32_t area() const { return empty() ? 0 : static_cast<int32_t>(w) * h; }
  void reset() { x = y = w = h = 0; }
};

// 裁到 [0,W) x [0,H)；完全在界外或空矩形返回 false
inline bool clipRect(Rect &r, int W, int H) {
  if (r.w <= 0 || r.h <= 0) return false;
  int x0 = r.x, y0 = r.y;
  int x1 = static_cast<int>(r.x) + r.w;
  int y1 = static_cast<int>(r.y) + r.h;
  if (x0 < 0) x0 = 0;
  if (y0 < 0) y0 = 0;
  if (x1 > W) x1 = W;
  if (y1 > H) y1 = H;
  if (x1 <= x0 || y1 <= y0) return false;
  r = {static_cast<int16_t>(x0), static_cast<int16_t>(y0),
       static_cast<int16_t>(x1 - x0), static_cast<int16_t>(y1 - y0)};
  return true;
}

// 把 add 并入 acc；acc 为空时直接取 add
inline void unionRect(Rect &acc, const Rect &add) {
  if (add.w <= 0 || add.h <= 0) return;
  if (acc.w <= 0 || acc.h <= 0) { acc = add; return; }
  const int x0 = std::min<int>(acc.x, add.x);
  const int y0 = std::min<int>(acc.y, add.y);
  const int x1 = std::max<int>(static_cast<int>(acc.x) + acc.w, static_cast<int>(add.x) + add.w);
  const int y1 = std::max<int>(static_cast<int>(acc.y) + acc.h, static_cast<int>(add.y) + add.h);
  acc = {static_cast<int16_t>(x0), static_cast<int16_t>(y0),
         static_cast<int16_t>(x1 - x0), static_cast<int16_t>(y1 - y0)};
}

// RGB565：每像素 2 字节
inline int32_t rectBytes(const Rect &r) { return r.area() * 2; }

// 该矩形在给定 SPI 时钟下的传输时间（微秒）
inline uint32_t rectMicros(const Rect &r, uint32_t spiHz) {
  if (!spiHz) return 0;
  return static_cast<uint32_t>((static_cast<uint64_t>(rectBytes(r)) * 8ull * 1000000ull) / spiHz);
}

}  // namespace gfx
