#include "anim.h"

#include <Arduino.h>
#include <cstring>

namespace anim {
namespace {

constexpr uint32_t kHeaderLen = 8;
constexpr uint32_t kRecordLen = 24;
constexpr int      kMaxClips  = 16;
// v2：差分记录 u32 start + u16 run，start == 0xFFFFFFFF 结束。
// v1 是 u16/u16 + 0xFFFF 结束，start 最大 65534 → 单帧不能超过 65535 像素。
constexpr uint8_t  kFormatVersion = 2;
constexpr uint32_t kDeltaEnd       = 0xFFFFFFFFu;

Clip gClips[kMaxClips];
int  gCount = 0;
bool gReady = false;

inline uint16_t rd16(const uint8_t *p) { return static_cast<uint16_t>(p[0] | (p[1] << 8)); }
inline uint32_t rd32(const uint8_t *p) {
  return static_cast<uint32_t>(p[0]) | (static_cast<uint32_t>(p[1]) << 8) |
         (static_cast<uint32_t>(p[2]) << 16) | (static_cast<uint32_t>(p[3]) << 24);
}

}  // namespace

void load(const uint8_t *blob, uint32_t bytes) {
  gReady = false;
  gCount = 0;
  if (!blob || bytes < kHeaderLen || memcmp(blob, "GFX1", 4) != 0) {
    Serial.println("anim: 数据头不对，跳过");
    return;
  }
  // 版本必须对齐 —— 这里以前不校验版本，格式一改就会静默解出乱码。
  // v2 把差分记录的 start 从 u16 放宽到 u32，才能编出超过 65535 像素的帧。
  if (blob[4] != kFormatVersion) {
    Serial.printf("anim: 版本 %u 不支持（本固件需要 %u），请用当前的 make_gif_anim.py 重新生成\n",
                  static_cast<unsigned>(blob[4]), static_cast<unsigned>(kFormatVersion));
    return;
  }
  const int n = blob[5];
  if (n <= 0 || n > kMaxClips) {
    Serial.printf("anim: 数量异常 %d\n", n);
    return;
  }
  if (kHeaderLen + static_cast<uint32_t>(n) * kRecordLen > bytes) {
    Serial.println("anim: 记录区越界");
    return;
  }
  for (int i = 0; i < n; ++i) {
    const uint8_t *r = blob + kHeaderLen + i * kRecordLen;
    Clip &c = gClips[i];
    c.w        = rd16(r + 0);
    c.h        = rd16(r + 2);
    c.frames   = rd16(r + 4);
    c.delayMs  = rd16(r + 6);
    const uint32_t palOff = rd32(r + 12);
    const uint32_t idxOff = rd32(r + 16);
    const uint32_t datOff = rd32(r + 20);
    if (palOff + 512u > bytes || idxOff + static_cast<uint32_t>(c.frames) * 8u > bytes ||
        datOff > bytes) {
      Serial.printf("anim: 第 %d 部越界，跳过\n", i);
      continue;
    }
    c.palette    = reinterpret_cast<const uint16_t *>(blob + palOff);
    c.frameIndex = blob + idxOff;
    c.data       = blob + datOff;
    ++gCount;
    Serial.printf("anim: %d) %ux%u %u 帧 %ums/帧 (%u KB)\n", i, c.w, c.h, c.frames,
                  c.delayMs,
                  static_cast<unsigned>((c.w * static_cast<uint32_t>(c.h) * c.frames) / 1024u));
  }
  gReady = gCount > 0;
  Serial.printf("anim: 载入 %d 部\n", gCount);
}

int count() { return gReady ? gCount : 0; }

const Clip *at(int i) {
  if (!gReady || i < 0 || i >= gCount) return nullptr;
  return &gClips[i];
}

bool decode(const Clip &c, int frame, uint8_t *idxBuf) {
  if (!idxBuf || frame < 0 || frame >= c.frames) return false;
  const uint32_t need = static_cast<uint32_t>(c.w) * c.h;
  const uint32_t off = rd32(c.frameIndex + frame * 8);
  const uint32_t len = rd32(c.frameIndex + frame * 8 + 4);
  const uint8_t *p = c.data + off;

  if (frame == 0) {                       // 整帧
    if (len != need) return false;
    memcpy(idxBuf, p, need);
    return true;
  }
  // 差分：u32 start / u16 run / run 字节，start==0xFFFFFFFF 结束。
  // start 是「绝对像素位置」，不是相对跳过 —— 编码器就是这么写的。
  // 用 u32 是因为一帧可能有 320x240 以上像素，u16 装不下。
  const uint8_t *end = p + len;
  while (p + 4 <= end) {
    const uint32_t start = rd32(p);
    p += 4;
    if (start == kDeltaEnd) break;
    if (p + 2 > end) return false;
    const uint16_t run = rd16(p);
    p += 2;
    if (start + run > need || p + run > end) return false;
    memcpy(idxBuf + start, p, run);
    p += run;
  }
  return true;
}

}  // namespace anim
