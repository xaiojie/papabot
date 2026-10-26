#pragma once
#include <cstddef>
#include <cstdint>
#include <cerrno>
#include <climits>
#include <cstdlib>
#include <cstring>
#include "board_config.h"

#ifndef BRINGUP_IRAM
#define BRINGUP_IRAM
#endif

namespace bringup {
// ESP.getPsramSize() in Arduino-ESP32 returns the heap-managed PSRAM total
// (multi_heap total_free_bytes + total_allocated_bytes), not the physical chip
// capacity, so it lands a few KiB below the nominal size on healthy hardware.
// Comparing it to the nominal size with == reports a false FAIL, so accept a
// measured value that is at or below the nominal size and within tolerance.
constexpr bool withinMemoryTolerance(uint32_t measured, uint32_t expected, uint32_t tolerance) {
  return measured <= expected && expected - measured <= tolerance;
}

class DebouncedButton {
 public:
  void reset(bool high, uint32_t now) { stable_ = candidate_ = high; since_ = now; }
  // Return one event after a stable active-low press, never repeatedly while held.
  bool update(bool high, uint32_t now) {
    if (high != candidate_) { candidate_ = high; since_ = now; }
    if (candidate_ != stable_ && static_cast<uint32_t>(now - since_) >= 30u) {
      stable_ = candidate_;
      return !stable_;
    }
    return false;
  }
  bool pressed() const { return !stable_; }
 private:
  bool stable_ = true, candidate_ = true;
  uint32_t since_ = 0;
};
class QuadratureEncoder {
 public:
  void reset(bool a, bool b, uint8_t divisor = 4) {
    state_ = (a ? 2u : 0u) | (b ? 1u : 0u);
    partial_ = 0; count_ = 0; divisor_ = divisor == 2 ? 2 : 4;
  }
  // No tables, allocation or library calls: also used inside the GPIO ISR.
  void BRINGUP_IRAM sample(bool a, bool b) {
    const uint8_t next = (a ? 2u : 0u) | (b ? 1u : 0u);
    const uint8_t changed = next ^ state_;
    if (changed == 3u) { partial_ = 0; }
    else if (changed != 0u) {
      partial_ += ((state_ & 1u) ^ ((next >> 1u) & 1u)) ? -1 : 1;
      if (partial_ >= divisor_) {
        if (count_ < INT32_MAX) ++count_;
        partial_ = 0;
      } else if (partial_ <= -divisor_) {
        if (count_ > INT32_MIN) --count_;
        partial_ = 0;
      }
    }
    state_ = next;
  }
  int32_t count() const { return count_; }
 private:
  uint8_t state_ = 3;
  int8_t partial_ = 0, divisor_ = 4;
  int32_t count_ = 0;
};
class ServoPolicy {
 public:
  bool arm(uint32_t now) {
    if (armed_) return false;
    current_ = target_ = config::SERVO_CENTER_US;
    lastCommand_ = lastStep_ = now;
    armed_ = true;
    return true;
  }
  bool setTarget(int us, uint32_t now) {
    if (!armed_) return false;
    // ⚠️ 必须用有符号比较：loop 顶部取的 now 可能比 serviceSerial() 里写进
    // lastCommand_ 的 millis() 小 1ms，无符号相减会下溢成 4294967295，
    // 于是刚 arm 完就判超时松力。（assistant 固件 2026-09-14 实测踩过同样的坑）
    if (static_cast<int32_t>(now - lastCommand_) >=
        static_cast<int32_t>(config::SERVO_TIMEOUT_MS)) {
      stop(); return false;
    }
    if (us < static_cast<int>(config::SERVO_MINIMUM_US) || us > static_cast<int>(config::SERVO_MAXIMUM_US)) return false;
    target_ = static_cast<uint16_t>(us); lastCommand_ = now;
    return true;
  }
  // True only for a transition to timeout-disarmed. No catch-up jumps after delays.
  bool tick(uint32_t now) {
    if (!armed_) return false;
    if (static_cast<int32_t>(now - lastCommand_) >=
        static_cast<int32_t>(config::SERVO_TIMEOUT_MS)) { stop(); return true; }
    if (static_cast<uint32_t>(now - lastStep_) < config::SERVO_SLEW_INTERVAL_MS) return false;
    lastStep_ = now;
    const int delta = static_cast<int>(target_) - static_cast<int>(current_);
    const int step = config::SERVO_SLEW_STEP_US;
    current_ = static_cast<uint16_t>(static_cast<int>(current_) + (delta > step ? step : (delta < -step ? -step : delta)));
    return false;
  }
  void stop() { armed_ = false; }
  bool armed() const { return armed_; }
  uint16_t current() const { return current_; }
  uint16_t target() const { return target_; }
 private:
  bool armed_ = false;
  uint16_t current_ = config::SERVO_CENTER_US, target_ = config::SERVO_CENTER_US;
  uint32_t lastCommand_ = 0, lastStep_ = 0;
};
enum class CommandKind { Invalid, Empty, Help, Status, Selftest, WifiScan, Stop,
  ScreenStart, ScreenStop, ScreenRotation, ScreenInvert, EncoderDivisor,
  ServoArm, ServoPulse, ServoCenter, ServoStop, WifiConnect, WifiStatus, WifiDisconnect, NetTest,
  MicStart, MicRead, MicSwap, MicStop };

// SSID (up to 32 bytes) and WPA passphrase (8..63 bytes). Text is copied out of
// the tokenizer buffer instead of referenced, and raw bytes are kept so a UTF-8
// SSID survives intact.
constexpr size_t kCommandTextMax = 64;
struct Command {
  CommandKind kind;
  int value = 0;
  // -1 means "every servo"; 0..SERVO_COUNT-1 selects one channel (servo pulse <id> <us>).
  int index = -1;
  char text1[kCommandTextMax] = {};
  char text2[kCommandTextMax] = {};
};

inline bool copyCommandText(char (&dst)[kCommandTextMax], const char *src) {
  const size_t length = std::strlen(src);
  if (length == 0 || length >= kCommandTextMax) return false;
  std::memcpy(dst, src, length + 1);
  return true;
}

inline Command parseCommand(const char *input) {
  if (!input || std::strlen(input) >= 96u) return {CommandKind::Invalid, 0};
  char text[96];
  std::strcpy(text, input);
  char *words[4] = {};
  unsigned count = 0;
  for (char *part = std::strtok(text, " \t\r\n"); part; part = std::strtok(nullptr, " \t\r\n")) {
    if (count == 4u) return {CommandKind::Invalid, 0};
    words[count++] = part;
  }
  if (!count) return {CommandKind::Empty, 0};
  const auto is = [&](unsigned n, const char *word) { return n < count && std::strcmp(words[n], word) == 0; };
  if (count == 1u) {
    if (is(0, "help")) return {CommandKind::Help, 0};
    if (is(0, "status")) return {CommandKind::Status, 0};
    if (is(0, "selftest")) return {CommandKind::Selftest, 0};
    if (is(0, "stop") || is(0, "!")) return {CommandKind::Stop, 0};
  }
  if (count == 2u) {
    if (is(0, "wifi") && is(1, "scan")) return {CommandKind::WifiScan, 0};
    if (is(0, "wifi") && is(1, "status")) return {CommandKind::WifiStatus, 0};
    if (is(0, "wifi") && is(1, "disconnect")) return {CommandKind::WifiDisconnect, 0};
    if (is(0, "net") && is(1, "test")) return {CommandKind::NetTest, 0};
    if (is(0, "screen") && is(1, "start")) return {CommandKind::ScreenStart, 0};
    if (is(0, "screen") && is(1, "stop")) return {CommandKind::ScreenStop, 0};
    if (is(0, "servo") && is(1, "arm")) return {CommandKind::ServoArm, 0};
    if (is(0, "servo") && is(1, "center")) return {CommandKind::ServoCenter, 0};
    if (is(0, "servo") && is(1, "stop")) return {CommandKind::ServoStop, 0};
    if (is(0, "mic") && is(1, "start")) return {CommandKind::MicStart, 0};
    if (is(0, "mic") && is(1, "stop")) return {CommandKind::MicStop, 0};
    if (is(0, "mic") && is(1, "read")) return {CommandKind::MicRead, 0};
    if (is(0, "mic") && is(1, "swap")) return {CommandKind::MicSwap, 0};
  }
  if (count == 3u) {
    errno = 0; char *end = nullptr;
    const long value = std::strtol(words[2], &end, 10);
    if (errno || end == words[2] || *end || value < INT_MIN || value > INT_MAX) return {CommandKind::Invalid, 0};
    const int n = static_cast<int>(value);
    if (is(0, "servo") && is(1, "pulse")) return {CommandKind::ServoPulse, n};
    // 50..3000 ms keeps one capture short enough that the console stays responsive.
    if (is(0, "mic") && is(1, "read") && n >= 50 && n <= 3000) return {CommandKind::MicRead, n};
    if (is(0, "screen") && is(1, "rotation") && (n == 1 || n == 3)) return {CommandKind::ScreenRotation, n};
    if (is(0, "screen") && is(1, "invert") && (n == 0 || n == 1)) return {CommandKind::ScreenInvert, n};
    if (is(0, "encoder") && is(1, "divisor") && (n == 2 || n == 4)) return {CommandKind::EncoderDivisor, n};
  }
  if (count == 4u && is(0, "servo") && is(1, "pulse")) {
    errno = 0; char *end = nullptr;
    const long id = std::strtol(words[2], &end, 10);
    // Reject an out-of-range id loudly instead of silently falling back to "both".
    if (errno || end == words[2] || *end || id < 0 || id >= static_cast<long>(config::SERVO_COUNT)) {
      return {CommandKind::Invalid, 0};
    }
    errno = 0; end = nullptr;
    const long us = std::strtol(words[3], &end, 10);
    if (errno || end == words[3] || *end || us < INT_MIN || us > INT_MAX) return {CommandKind::Invalid, 0};
    Command command{CommandKind::ServoPulse, static_cast<int>(us)};
    command.index = static_cast<int>(id);
    return command;
  }
  if (count == 4u && is(0, "wifi") && is(1, "connect")) {
    Command command{CommandKind::WifiConnect, 0};
    if (!copyCommandText(command.text1, words[2]) || !copyCommandText(command.text2, words[3])) {
      return {CommandKind::Invalid, 0};
    }
    return command;
  }
  return {CommandKind::Invalid, 0};
}
enum class LineEvent { None, Ready, Overflow };
class LineBuffer {
 public:
  LineEvent push(char c) {
    if (completed_) { length_ = 0; completed_ = false; }
    if (c == '\r' || c == '\n') {
      if (overflow_) { clear(); return LineEvent::Overflow; }
      if (!length_) return LineEvent::None;
      text_[length_] = '\0'; completed_ = true;
      return LineEvent::Ready;
    }
    if (overflow_) return LineEvent::None;
    if (c == '\b' || c == 127) { if (length_) --length_; return LineEvent::None; }
    // Reject control characters and DEL, but keep bytes >= 0x80 so a UTF-8 SSID
    // (for example a Chinese network name) can be entered at the console.
    if ((static_cast<unsigned char>(c) < 32u && c != '\t') || static_cast<unsigned char>(c) == 127u) return LineEvent::None;
    if (length_ + 1u >= sizeof(text_)) { overflow_ = true; return LineEvent::None; }
    text_[length_++] = c;
    return LineEvent::None;
  }
  const char *line() const { return text_; }
  void clear() { length_ = 0; completed_ = overflow_ = false; text_[0] = '\0'; }
 private:
  char text_[96] = {};
  size_t length_ = 0;
  bool completed_ = false, overflow_ = false;
};
} // namespace bringup
