#pragma once
#include <cstdint>

// 动画播放：读由 scripts/make_gif_anim.py 生成的二进制（当前格式 v2）。
// 面板是只写 SPI，帧缓冲在 PSRAM，这里只负责「把第 N 帧解成 256 色索引」，
// 再由 Canvas 查调色板画到帧缓冲、按脏矩形推屏。
// ⚠️ 改了脚本的输出格式就必须同步改 anim.cpp 的 kFormatVersion —— 版本不符会拒绝加载。
namespace anim {

struct Clip {
  uint16_t w = 0, h = 0, frames = 0, delayMs = 0;
  const uint16_t *palette = nullptr;   // 256 个 RGB565
  const uint8_t *frameIndex = nullptr; // frames × 8 字节：u32 off, u32 len（相对 data）
  const uint8_t *data = nullptr;
};

void load(const uint8_t *blob, uint32_t bytes);
int count();
const Clip *at(int i);

// 解出第 frame 帧的索引到 idxBuf（w*h 字节）。
// 第 0 帧整帧写入；其余帧在 idxBuf 现有内容上叠加差分 ——
// 所以必须按 0,1,2,... 顺序调用（循环时从 0 重新整帧写）。
bool decode(const Clip &c, int frame, uint8_t *idxBuf);

}  // namespace anim
