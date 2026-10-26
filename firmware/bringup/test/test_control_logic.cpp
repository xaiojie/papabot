#include "control_logic.h"
#include <cstdio>
#include <cstring>

static int failures = 0;
static int checks = 0;
#define CHECK(expr) do { ++checks; if (!(expr)) { ++failures; std::printf("FAIL line %d: %s\n", __LINE__, #expr); } } while (false)

using namespace bringup;

static void button_bounce_is_not_multiple_presses() {
  DebouncedButton b;
  b.reset(true, 0);
  CHECK(!b.update(false, 100));
  CHECK(!b.update(true, 110));
  CHECK(!b.update(false, 120));
  CHECK(!b.update(false, 149));
  CHECK(b.update(false, 150));
  CHECK(b.pressed());
  CHECK(!b.update(false, 800));
  CHECK(!b.update(true, 900));
  CHECK(!b.update(true, 930));
  CHECK(!b.pressed());
  CHECK(!b.update(false, 1000));
  CHECK(b.update(false, 1030));
}

static void debounce_survives_millis_rollover_and_initial_hold() {
  DebouncedButton b;
  b.reset(true, 0xfffffff0u);
  CHECK(!b.update(false, 0xfffffffau));
  CHECK(!b.update(false, 23));
  CHECK(b.update(false, 24));
  b.reset(false, 100);
  CHECK(!b.update(false, 200));
  CHECK(b.pressed());
}

static void encoder_counts_complete_cycles_and_reverses() {
  QuadratureEncoder e;
  e.reset(true, true);
  e.sample(true, false); e.sample(false, false); e.sample(false, true);
  CHECK(e.count() == 0);
  e.sample(true, true);
  CHECK(e.count() == 1);
  e.sample(false, true); e.sample(false, false); e.sample(true, false); e.sample(true, true);
  CHECK(e.count() == 0);
}

static void encoder_rejects_bounce_and_illegal_two_bit_jump() {
  QuadratureEncoder e;
  e.reset(true, true);
  e.sample(true, false); e.sample(true, true); e.sample(true, false); e.sample(true, true);
  CHECK(e.count() == 0);
  e.sample(true, false); // partial movement
  e.sample(false, true); // illegal: both bits change, discard the partial cycle
  e.sample(true, true); e.sample(true, false); e.sample(false, false);
  CHECK(e.count() == 0);
  e.sample(false, true);
  CHECK(e.count() == 1);
  e.reset(true, true, 2);
  e.sample(true, false); e.sample(false, false);
  CHECK(e.count() == 1);
}

static void servo_requires_explicit_arm_and_rejects_out_of_range() {
  ServoPolicy p;
  CHECK(!p.armed());
  CHECK(!p.setTarget(1500, 0));
  CHECK(p.arm(0));
  CHECK(p.armed());
  CHECK(p.current() == 1500);
  CHECK(!p.setTarget(999, 10));
  CHECK(!p.setTarget(2001, 10));
  CHECK(!p.setTarget(-1, 10));
  CHECK(p.target() == 1500);
  CHECK(p.setTarget(1000, 10));
  CHECK(p.setTarget(2000, 10));
  p.stop();
  CHECK(!p.armed());
  CHECK(!p.setTarget(1500, 20));
}

static void servo_slew_does_not_jump_or_catch_up_after_delay() {
  ServoPolicy p;
  p.arm(100);
  p.setTarget(1600, 100);
  p.tick(119); CHECK(p.current() == 1500);
  p.tick(120); CHECK(p.current() == 1505);
  p.tick(800); CHECK(p.current() == 1510); // one small step even after loop delay
  p.setTarget(1507, 801);
  p.tick(820); CHECK(p.current() == 1507); // do not overshoot a short final step
  p.setTarget(1400, 821);
  p.tick(840); CHECK(p.current() == 1502);
}

static void timeout_cannot_be_extended_by_bad_commands_or_rearming() {
  ServoPolicy p;
  p.arm(0);
  CHECK(!p.arm(9000));
  CHECK(!p.setTarget(500, 9900));
  p.tick(9999); CHECK(p.armed());
  CHECK(p.tick(10000)); CHECK(!p.armed());
  CHECK(!p.setTarget(1500, 10001));
}

static void valid_commands_refresh_timeout_but_expired_requests_do_not() {
  ServoPolicy p;
  p.arm(0);
  CHECK(p.setTarget(1500, 9000));
  p.tick(10000); CHECK(p.armed());
  p.tick(19000); CHECK(!p.armed());
  p.arm(20000);
  CHECK(!p.setTarget(1500, 30000));
  CHECK(!p.armed());
}

static void servo_timeout_survives_millis_rollover() {
  ServoPolicy p;
  p.arm(0xfffffff0u);
  p.tick(9983); CHECK(p.armed());
  CHECK(p.tick(9984)); CHECK(!p.armed());
}

static void command_parser_does_not_accept_partial_or_extra_arguments() {
  CHECK(parseCommand("servo pulse 1500").kind == CommandKind::ServoPulse);
  CHECK(parseCommand("servo pulse 1500").value == 1500);
  CHECK(parseCommand("servo pulse 1500junk").kind == CommandKind::Invalid);
  CHECK(parseCommand("servo pulse 1500 1600").kind == CommandKind::Invalid);
  CHECK(parseCommand("servo pulse 999999999999999999999").kind == CommandKind::Invalid);
  CHECK(parseCommand("servo pulse 1499.5").kind == CommandKind::Invalid);
  CHECK(parseCommand("servo arm now").kind == CommandKind::Invalid);
  CHECK(parseCommand("screen rotation 2").kind == CommandKind::Invalid);
  CHECK(parseCommand("screen rotation 3").kind == CommandKind::ScreenRotation);
  CHECK(parseCommand("screen invert 1").kind == CommandKind::ScreenInvert);
  CHECK(parseCommand("encoder divisor 2").kind == CommandKind::EncoderDivisor);
  CHECK(parseCommand("status extra").kind == CommandKind::Invalid);
  CHECK(parseCommand("  stop \r ").kind == CommandKind::Stop);
  CHECK(parseCommand("\t \r").kind == CommandKind::Empty);
}

// Two servos: "servo pulse <us>" addresses both (index -1), and the optional
// leading channel index selects one. An out-of-range index must fail loudly
// instead of silently falling back to "both".
static void servo_pulse_selects_one_channel_or_both() {
  const Command both = parseCommand("servo pulse 1200");
  CHECK(both.kind == CommandKind::ServoPulse);
  CHECK(both.value == 1200);
  CHECK(both.index == -1);

  const Command first = parseCommand("servo pulse 0 1200");
  CHECK(first.kind == CommandKind::ServoPulse);
  CHECK(first.value == 1200);
  CHECK(first.index == 0);

  const Command second = parseCommand("servo pulse 1 1800");
  CHECK(second.kind == CommandKind::ServoPulse);
  CHECK(second.value == 1800);
  CHECK(second.index == 1);

  // Out-of-range, negative and malformed indices are rejected, not clamped.
  CHECK(parseCommand("servo pulse 2 1200").kind == CommandKind::Invalid);
  CHECK(parseCommand("servo pulse -1 1200").kind == CommandKind::Invalid);
  CHECK(parseCommand("servo pulse 0 1200junk").kind == CommandKind::Invalid);
  // A lone number stays a pulse width; its range is a run-time check, not parse time.
  const Command widthOnly = parseCommand("servo pulse 0");
  CHECK(widthOnly.kind == CommandKind::ServoPulse);
  CHECK(widthOnly.index == -1);
  CHECK(parseCommand("servo pulse 0 1500 1600").kind == CommandKind::Invalid);

  CHECK(parseCommand("servo center").kind == CommandKind::ServoCenter);
  CHECK(parseCommand("servo center 1").kind == CommandKind::Invalid);
}

static void overlong_serial_input_is_discarded_as_one_line() {
  LineBuffer b;
  for (int i = 0; i < 110; ++i) CHECK(b.push('x') == LineEvent::None);
  for (char c : "servo arm") if (c) CHECK(b.push(c) == LineEvent::None);
  CHECK(b.push('\n') == LineEvent::Overflow);
  CHECK(b.push('s') == LineEvent::None);
  b.push('t'); b.push('o'); b.push('p');
  CHECK(b.push('\r') == LineEvent::Ready);
  CHECK(std::strcmp(b.line(), "stop") == 0);
  CHECK(b.push('\n') == LineEvent::None); // CRLF is not a duplicate command
  b.push('h'); b.push('e'); b.push('l'); b.push('x'); b.push('\b'); b.push('p');
  CHECK(b.push('\n') == LineEvent::Ready);
  CHECK(std::strcmp(b.line(), "help") == 0);
}

static void memory_size_check_tolerates_heap_managed_total() {
  constexpr uint32_t expected = 8u * 1024u * 1024u;
  constexpr uint32_t tolerance = 64u * 1024u;
  CHECK(withinMemoryTolerance(expected, expected, tolerance));
  CHECK(withinMemoryTolerance(8386295u, expected, tolerance));  // measured on this LCKFB R8 board
  CHECK(withinMemoryTolerance(expected - tolerance, expected, tolerance));
  CHECK(!withinMemoryTolerance(expected - tolerance - 1u, expected, tolerance));
  CHECK(!withinMemoryTolerance(expected + 1u, expected, tolerance));  // never accept more than nominal
  CHECK(!withinMemoryTolerance(0u, expected, tolerance));  // psramFound() reported nothing
  CHECK(!withinMemoryTolerance(4u * 1024u * 1024u, expected, tolerance));  // 4 MB part must fail
}

static void wifi_connect_parses_a_utf8_ssid_and_carries_the_passphrase() {
  const Command c = parseCommand("wifi connect 示例网络 testpass123");
  CHECK(c.kind == CommandKind::WifiConnect);
  CHECK(std::strcmp(c.text1, "示例网络") == 0);
  CHECK(std::strcmp(c.text2, "testpass123") == 0);
  CHECK(parseCommand("wifi status").kind == CommandKind::WifiStatus);
  CHECK(parseCommand("wifi disconnect").kind == CommandKind::WifiDisconnect);
  CHECK(parseCommand("net test").kind == CommandKind::NetTest);
  // Missing passphrase, extra words and non-wifi 4-word lines stay invalid.
  CHECK(parseCommand("wifi connect 示例网络").kind == CommandKind::Invalid);
  CHECK(parseCommand("wifi connect a b c").kind == CommandKind::Invalid);
  CHECK(parseCommand("servo pulse 1500 1600").kind == CommandKind::Invalid);
  CHECK(parseCommand("wifi connect ssid-with-no-pass").kind == CommandKind::Invalid);
}

static void utf8_bytes_survive_the_line_buffer() {
  LineBuffer b;
  const char *line = "wifi connect 示例网络 testpass123";
  for (const char *p = line; *p; ++p) CHECK(b.push(*p) == LineEvent::None);
  CHECK(b.push('\n') == LineEvent::Ready);
  CHECK(std::strcmp(b.line(), line) == 0);
  const Command c = parseCommand(b.line());
  CHECK(c.kind == CommandKind::WifiConnect);
  CHECK(std::strcmp(c.text1, "示例网络") == 0);
  CHECK(std::strcmp(c.text2, "testpass123") == 0);
  // Control characters are still rejected even though >= 0x80 bytes are kept.
  LineBuffer d;
  CHECK(d.push('\x01') == LineEvent::None);
  CHECK(d.push('h') == LineEvent::None);
  CHECK(d.push('\n') == LineEvent::Ready);
  CHECK(std::strcmp(d.line(), "h") == 0);
}

static void mic_commands_parse_with_a_bounded_capture_window() {
  CHECK(parseCommand("mic start").kind == CommandKind::MicStart);
  CHECK(parseCommand("mic stop").kind == CommandKind::MicStop);
  CHECK(parseCommand("mic swap").kind == CommandKind::MicSwap);
  CHECK(parseCommand("mic read").kind == CommandKind::MicRead);
  CHECK(parseCommand("mic read").value == 0);  // 0 means "use the 1000 ms default" in main.cpp
  CHECK(parseCommand("mic read 50").kind == CommandKind::MicRead);
  CHECK(parseCommand("mic read 1000").kind == CommandKind::MicRead);
  CHECK(parseCommand("mic read 1000").value == 1000);
  CHECK(parseCommand("mic read 3000").kind == CommandKind::MicRead);
  // Outside 50..3000 ms the console would be blocked for too long, so it stays Invalid.
  CHECK(parseCommand("mic read 49").kind == CommandKind::Invalid);
  CHECK(parseCommand("mic read 3001").kind == CommandKind::Invalid);
  CHECK(parseCommand("mic read -100").kind == CommandKind::Invalid);
  // Nothing may be accepted by accident: bare words, extra arguments and typos.
  CHECK(parseCommand("mic").kind == CommandKind::Invalid);
  CHECK(parseCommand("mic level").kind == CommandKind::Invalid);
  CHECK(parseCommand("mic start now").kind == CommandKind::Invalid);
  CHECK(parseCommand("mic stop extra").kind == CommandKind::Invalid);
  CHECK(parseCommand("mic read 500 extra").kind == CommandKind::Invalid);
}

int main() {
  struct Test { const char *name; void (*run)(); };
  const Test tests[] = {
    {"button bounce does not multiply presses", button_bounce_is_not_multiple_presses},
    {"button startup and millis wrap", debounce_survives_millis_rollover_and_initial_hold},
    {"encoder full cycle and direction", encoder_counts_complete_cycles_and_reverses},
    {"encoder bounce and illegal transitions", encoder_rejects_bounce_and_illegal_two_bit_jump},
    {"servo arm and pulse bounds", servo_requires_explicit_arm_and_rejects_out_of_range},
    {"servo bounded slew", servo_slew_does_not_jump_or_catch_up_after_delay},
    {"invalid commands cannot prolong PWM", timeout_cannot_be_extended_by_bad_commands_or_rearming},
    {"valid commands and deadline", valid_commands_refresh_timeout_but_expired_requests_do_not},
    {"servo millis rollover", servo_timeout_survives_millis_rollover},
    {"strict command parsing", command_parser_does_not_accept_partial_or_extra_arguments},
    {"servo pulse picks one channel or both", servo_pulse_selects_one_channel_or_both},
    {"serial overflow discards entire line", overlong_serial_input_is_discarded_as_one_line},
    {"memory size tolerance for heap-managed totals", memory_size_check_tolerates_heap_managed_total},
    {"wifi connect parses utf8 ssid and passphrase", wifi_connect_parses_a_utf8_ssid_and_carries_the_passphrase},
    {"utf8 bytes survive the line buffer", utf8_bytes_survive_the_line_buffer},
    {"mic command parsing and capture window", mic_commands_parse_with_a_bounded_capture_window},
  };
  for (const auto &test : tests) {
    const int before = failures;
    test.run();
    std::printf("%s: %s\n", before == failures ? "PASS" : "FAIL", test.name);
  }
  std::printf("%zu cases, %d checks, %d failures\n", sizeof(tests) / sizeof(tests[0]), checks, failures);
  return failures == 0 ? 0 : 1;
}
