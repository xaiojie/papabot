#pragma once
#include <cstdint>

#include "config.h"

// 舵机策略：纯逻辑，不碰硬件 —— 斜率限制、角度限幅、超时自动松力。
// 从 bench-v1 的 control_logic.h 移植过来，行为保持一致。
//
// 为什么要有超时：舵机堵在某个角度不动时会持续吃电流、发热烧线圈。
// 10 秒没收到新指令就自动关 PWM，是最后一道保险。
namespace servo {

class Policy {
 public:
  bool arm(uint32_t now) {
    if (armed_) return false;
    current_ = target_ = cfg::SERVO_CENTER_US;
    lastCommand_ = lastStep_ = now;
    armed_ = true;
    return true;
  }

  bool setTarget(int us, uint32_t now) {
    if (!armed_) return false;
    if (timedOut(now)) {
      stop();
      return false;
    }
    if (us < static_cast<int>(cfg::SERVO_MIN_US) ||
        us > static_cast<int>(cfg::SERVO_MAX_US)) {
      return false;
    }
    target_ = static_cast<uint16_t>(us);
    lastCommand_ = now;
    return true;
  }

  // 返回 true 表示这一刻刚因超时而断开（调用方据此关 PWM）
  bool tick(uint32_t now) {
    if (!armed_) return false;
    if (timedOut(now)) {
      stop();
      return true;
    }
    if (static_cast<uint32_t>(now - lastStep_) < cfg::SERVO_SLEW_INTERVAL_MS) return false;
    lastStep_ = now;
    const int delta = static_cast<int>(target_) - static_cast<int>(current_);
    const int step = static_cast<int>(cfg::SERVO_SLEW_STEP_US);
    current_ = static_cast<uint16_t>(
        static_cast<int>(current_) + (delta > step ? step : (delta < -step ? -step : delta)));
    return false;
  }

  void stop() { armed_ = false; }
  bool armed() const { return armed_; }
  uint16_t current() const { return current_; }
  uint16_t target() const { return target_; }
  // 调试用：外部读一下最后一次收到指令的时刻，好算超时到底差多少
  uint32_t lastCommand() const { return lastCommand_; }
  uint32_t lastStep() const { return lastStep_; }

 private:
  // ⚠️ 超时判断必须用【有符号】比较，不能用 (uint32_t)(now - lastCommand_) >= TIMEOUT。
  //
  // 2026-09-14 实测踩到的坑：loop() 顶部取了 now=16693，serviceSerial() 里处理命令时
  // 又取了 millis()=16694 存进 lastCommand_，回到 loop 底部拿旧的 now 去减，
  // 得到 -1；转成 uint32_t 变成 4294967295，`>= 10000` 立刻成立
  // —— 舵机一收到指令就"超时松力"，表现成「刚 arm 完 0.8 秒就说不 armed」。
  //
  // 有符号比较下 -1 还是 -1，不会误判；同时天然兼容 millis() 回绕
  // （回绕时差值仍在 int32 范围内，只要两次调用间隔 < 24.8 天）。
  bool timedOut(uint32_t now) const {
    return static_cast<int32_t>(now - lastCommand_) >=
           static_cast<int32_t>(cfg::SERVO_TIMEOUT_MS);
  }

  bool armed_ = false;
  uint16_t current_ = cfg::SERVO_CENTER_US;
  uint16_t target_ = cfg::SERVO_CENTER_US;
  uint32_t lastCommand_ = 0;
  uint32_t lastStep_ = 0;
};

}  // namespace servo
