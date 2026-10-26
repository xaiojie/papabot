#include <Arduino.h>
#include <SPI.h>
#include <WiFi.h>
#include <Adafruit_GFX.h>
#include <Adafruit_ST7789.h>
#include <driver/i2s.h>
#include <cmath>
#include <esp_heap_caps.h>
#include <esp_system.h>
#include "board_config.h"
#define BRINGUP_IRAM IRAM_ATTR
#include "control_logic.h"

using namespace bringup;

namespace {
enum class Mode { Passive, Screen, Servo };
Mode mode = Mode::Passive;
SPIClass displaySpi(FSPI);
class BenchDisplay final : public Adafruit_ST7789 {
 public:
  using Adafruit_ST7789::Adafruit_ST7789;
  // commonInit() calls this virtual function; keep even the init sequence at 10 MHz.
  void begin(uint32_t = 0) override { Adafruit_ST77xx::begin(config::SCREEN_SPI_HZ); }
};
BenchDisplay display(&displaySpi, config::LCD_CS, config::LCD_DC, config::LCD_RST);
QuadratureEncoder encoder;
portMUX_TYPE encoderMux = portMUX_INITIALIZER_UNLOCKED;
DebouncedButton pushButton, keyButton, bootButton;
// Two independent LEDC channels. The pin list is generated from wiring.json
// (servo.gpio / servo.gpio2), so this stays the single source of truth.
constexpr int kServoCount = static_cast<int>(config::SERVO_COUNT);
constexpr int kServoPins[kServoCount] = {config::SERVO_GPIO, config::SERVO_GPIO2};
constexpr int kServoChannels[kServoCount] = {0, 1};
static_assert(kServoCount == 2, "kServoPins/kServoChannels are written for exactly two servos");
ServoPolicy servo[kServoCount];
LineBuffer serialLine;
uint32_t pushCount = 0, keyCount = 0, bootCount = 0;
int32_t shownEncoder = INT32_MIN;
uint8_t encoderDivisor = config::SCREEN_ENCODER_TRANSITIONS_PER_DETENT;
uint8_t rotation = config::SCREEN_ROTATION;
bool inverted = config::SCREEN_INVERTED, controlsDirty = true;
bool pwmAttached = false;
uint16_t writtenPulse[kServoCount] = {0, 0};
uint32_t lastDraw = 0, lastLed = 0;
static_assert(config::SERVO_RESOLUTION_BITS <= 14, "ESP32-S3 LEDC supports at most 14-bit duty resolution");

// ---- I²S microphone (INMP441 class: 24-bit data left-justified in a 32-bit slot) ----
constexpr i2s_port_t kMicPort = I2S_NUM_0;
constexpr uint32_t kMicShift = config::MIC_SLOT_BITS - config::MIC_DATA_BITS;
constexpr int32_t kMicFullScale = 1 << (config::MIC_DATA_BITS - 1);
bool micReady = false;
int micBclk = config::MIC_BCLK;
int micWs = config::MIC_WS;
void micUninstall();  // defined with the rest of the I2S commands; stopAll() needs it early

// One accumulation window: enough to separate real sound from a dead or stuck data line.
struct MicStats {
  int32_t minValue = INT32_MAX, maxValue = INT32_MIN;
  double sumSquares = 0.0, sumValue = 0.0;
  uint32_t samples = 0, silences = 0, saturated = 0;
  void add(int32_t value) {
    if (value < minValue) minValue = value;
    if (value > maxValue) maxValue = value;
    sumSquares += static_cast<double>(value) * static_cast<double>(value);
    sumValue += static_cast<double>(value);
    ++samples;
    if (value == 0) ++silences;
    else if (value == kMicFullScale - 1 || value == -kMicFullScale) ++saturated;
  }
  double rms() const { return samples ? std::sqrt(sumSquares / samples) : 0.0; }
  // A MEMS mic sits on a DC bias of roughly 1 % of full scale, so the total RMS would
  // report a loud-looking -40 dBFS for a silent room. Level and dBFS must use the
  // AC component only: sqrt(E[x^2] - E[x]^2).
  double acRms() const {
    if (!samples) return 0.0;
    const double mean = sumValue / samples;
    const double variance = sumSquares / samples - mean * mean;
    return variance > 0.0 ? std::sqrt(variance) : 0.0;
  }
  double dc() const { return samples ? sumValue / samples : 0.0; }
  double dbfs() const { const double r = acRms(); return r > 1.0 ? 20.0 * std::log10(r / kMicFullScale) : -120.0; }
};

void micLevelBar(double dbfs, char *out, size_t size) {
  constexpr int kCells = 30;
  int filled = static_cast<int>((dbfs + 90.0) / 3.0);  // -90 dBFS .. 0 dBFS -> 0..30 cells
  if (filled < 0) filled = 0;
  if (filled > kCells) filled = kCells;
  for (int i = 0; i < kCells && static_cast<size_t>(i) + 1u < size; ++i) out[i] = i < filled ? '#' : '.';
  out[kCells < size ? kCells : size - 1] = '\0';
}

const char *modeName() {
  switch (mode) {
    case Mode::Screen: return "SCREEN";
    case Mode::Servo: return "SERVO";
    default: return "PASSIVE";
  }
}

void setLed(bool on) {
  digitalWrite(config::LED_GPIO, config::LED_ACTIVE_LOW ? !on : on);
}

void makeScreenPassive() {
  const int pins[] = {config::LCD_SCLK, config::LCD_MOSI, config::LCD_RST,
    config::LCD_DC, config::LCD_CS, config::ENC_A, config::ENC_B,
    config::ENC_PUSH, config::KEY0};
  for (int pin : pins) pinMode(pin, INPUT);
}

void IRAM_ATTR encoderIsr() {
  portENTER_CRITICAL_ISR(&encoderMux);
  encoder.sample(digitalRead(config::ENC_A), digitalRead(config::ENC_B));
  portEXIT_CRITICAL_ISR(&encoderMux);
}

int32_t encoderCount() {
  portENTER_CRITICAL(&encoderMux);
  const int32_t result = encoder.count();
  portEXIT_CRITICAL(&encoderMux);
  return result;
}

void resetEncoder() {
  portENTER_CRITICAL(&encoderMux);
  encoder.reset(digitalRead(config::ENC_A), digitalRead(config::ENC_B), encoderDivisor);
  portEXIT_CRITICAL(&encoderMux);
  controlsDirty = true;
}

void stopPwmHardware() {
  for (int i = 0; i < kServoCount; ++i) {
    if (pwmAttached) {
      ledcWrite(kServoChannels[i], 0);
      ledcDetachPin(kServoPins[i]);
    }
    digitalWrite(kServoPins[i], LOW);
    pinMode(kServoPins[i], OUTPUT);
    writtenPulse[i] = 0;
  }
  pwmAttached = false;
}

void stopScreen() {
  if (mode == Mode::Screen) {
    detachInterrupt(config::ENC_A);
    detachInterrupt(config::ENC_B);
    displaySpi.end();
    mode = Mode::Passive;
  }
  makeScreenPassive();
}

void stopAll() {
  for (int i = 0; i < kServoCount; ++i) servo[i].stop();
  stopPwmHardware();
  stopScreen();
  micUninstall();
  if (WiFi.getMode() != WIFI_OFF) {  // panic stop also drops the link; never erase profiles
    WiFi.disconnect(true, false);
    WiFi.mode(WIFI_OFF);
  }
  mode = Mode::Passive;
  Serial.println("STOP: screen pins high-Z, PWM off, I2S mic released, Wi-Fi off. External supplies are still ON.");
}

void printHelp() {
  Serial.println(
    "\nDesktop Assistant bench-v1 / serial console 115200\n"
    "  help | status | stop | !\n"
    "  selftest             PASSIVE only; chip/flash/PSRAM/64 KiB test\n"
    "  wifi scan            PASSIVE only; scan without saving credentials\n"
    "  screen start         confirm external 3.3 V and USB MCU power first\n"
    "  screen stop          release signal pins; backlight remains powered\n"
    "  screen rotation 1|3  landscape orientation\n"
    "  screen invert 0|1    choose correct black/white/color appearance\n"
    "  encoder divisor 2|4  reset count, calibrate transitions per click\n"
    "  servo arm            confirm external 5 V; no load; centers BOTH servos\n"
    "  servo pulse 1000..2000    move BOTH servos (servo0=GPIO18, servo1=GPIO15)\n"
    "  servo pulse <i> 1000..2000  move only servo i; refreshes the 10 s timeout\n"
    "  servo center         both back to 1500 us\n"
    "  servo stop           stop PWM, does NOT disconnect servo power\n"
    "  mic start            I2S RX; BCLK=GPIO4 WS=GPIO5 SD=GPIO6, L/R to GND\n"
    "  mic read 50..3000    capture and print 100 ms level lines, then a verdict\n"
    "  mic swap             re-install with BCLK/WS exchanged (silkscreen doubt)\n"
    "  mic stop             release the I2S port and its pins\n"
    "  wifi scan            list APs with RSSI; no credentials touched\n"
    "  wifi connect SSID PASS  join in RAM only; never written to NVS\n"
    "  wifi status          IP / gateway / DNS / RSSI of the current link\n"
    "  wifi disconnect      drop the link and power the radio off\n"
    "  net test             DNS + TCP + HTTP GET to www.baidu.com\n"
    "Screen and servo modes are mutually exclusive. ! stops without Enter.\n"
    "No voltage sensing or peripheral power isolation is provided by firmware.");
}

void printStatus() {
  Serial.printf("mode=%s uptime_ms=%lu heap=%u PSRAM_heap=%u flash=%u BOOT_presses=%lu\n",
    modeName(), static_cast<unsigned long>(millis()), ESP.getFreeHeap(), ESP.getPsramSize(),
    ESP.getFlashChipSize(), static_cast<unsigned long>(bootCount));
  if (mode == Mode::Screen) {
    Serial.printf("ENC=%ld PUSH=%lu KEY0=%lu rotation=%u invert=%u divisor=%u\n",
      static_cast<long>(encoderCount()), static_cast<unsigned long>(pushCount),
      static_cast<unsigned long>(keyCount), rotation, inverted, encoderDivisor);
  }
  if (WiFi.status() == WL_CONNECTED) {
    Serial.printf("Wi-Fi: %s RSSI=%d dBm IP=%s\n", WiFi.SSID().c_str(),
      static_cast<int>(WiFi.RSSI()), WiFi.localIP().toString().c_str());
  }
  for (int i = 0; i < kServoCount; ++i) {
    Serial.printf("PWM%d=%s pin=GPIO%d current_us=%u target_us=%u (external 5 V)\n",
      i, pwmAttached ? "ON" : "OFF", kServoPins[i], servo[i].current(), servo[i].target());
  }
  Serial.printf("MIC=%s BCLK=GPIO%d WS=GPIO%d SD=GPIO%d %lu Hz left channel\n",
    micReady ? "ON" : "OFF", micBclk, micWs, config::MIC_SD,
    static_cast<unsigned long>(config::MIC_SAMPLE_RATE_HZ));
}

void selftest() {
  if (mode != Mode::Passive) { Serial.println("ERR: run stop before selftest."); return; }
  Serial.printf("Chip=%s rev=%u cores=%u CPU=%u MHz SDK=%s reset_reason=%d\n",
    ESP.getChipModel(), ESP.getChipRevision(), ESP.getChipCores(), ESP.getCpuFreqMHz(),
    ESP.getSdkVersion(), static_cast<int>(esp_reset_reason()));
  // getPsramSize() is the heap-managed PSRAM total, not the physical capacity,
  // so it is a few KiB below nominal even on healthy hardware. Compare with a
  // tolerance and print the heap split so the difference stays visible.
  constexpr uint32_t kFlashExpected = 8u * 1024u * 1024u;
  constexpr uint32_t kPsramExpected = 8u * 1024u * 1024u;
  constexpr uint32_t kPsramTolerance = 64u * 1024u;
  const uint32_t flashBytes = ESP.getFlashChipSize();
  Serial.printf("%s flash: %u bytes, expected %u\n",
    flashBytes == kFlashExpected ? "PASS" : "FAIL", flashBytes, kFlashExpected);
  const uint32_t psramBytes = ESP.getPsramSize();
  Serial.printf("%s PSRAM managed: %u bytes, expected %u within %u\n",
    withinMemoryTolerance(psramBytes, kPsramExpected, kPsramTolerance) ? "PASS" : "FAIL",
    psramBytes, kPsramExpected, kPsramTolerance);
  Serial.printf("PSRAM heap free=%u min_free=%u largest_block=%u\n",
    ESP.getFreePsram(), ESP.getMinFreePsram(), ESP.getMaxAllocPsram());
  constexpr size_t words = 16384; // 64 KiB sample, not an exhaustive RAM qualification.
  volatile uint32_t *buffer = static_cast<uint32_t *>(heap_caps_malloc(words * sizeof(uint32_t), MALLOC_CAP_SPIRAM | MALLOC_CAP_8BIT));
  if (!buffer) { Serial.println("FAIL PSRAM sample allocation."); return; }
  bool good = true;
  for (uint32_t i = 0; i < words; ++i) buffer[i] = 0x5a5a0000u ^ (i * 2654435761u);
  for (uint32_t i = 0; i < words; ++i) {
    const uint32_t expected = 0x5a5a0000u ^ (i * 2654435761u);
    if (buffer[i] != expected) good = false;
    buffer[i] = ~expected;
  }
  for (uint32_t i = 0; i < words; ++i) if (buffer[i] != ~(0x5a5a0000u ^ (i * 2654435761u))) good = false;
  heap_caps_free(const_cast<uint32_t *>(buffer));
  Serial.printf("%s 64 KiB PSRAM sample pattern + inverse.\n", good ? "PASS" : "FAIL");
  Serial.println("Observe the LED heartbeat; press/release BOOT after boot, then status.");
}

const char *encryptionName(wifi_auth_mode_t auth) {
  switch (auth) {
    case WIFI_AUTH_OPEN: return "open";
    case WIFI_AUTH_WEP: return "WEP";
    case WIFI_AUTH_WPA_PSK: return "WPA";
    case WIFI_AUTH_WPA2_PSK: return "WPA2";
    case WIFI_AUTH_WPA_WPA2_PSK: return "WPA/2";
    case WIFI_AUTH_WPA2_ENTERPRISE: return "WPA2-ENT";
    case WIFI_AUTH_WPA3_PSK: return "WPA3";
    case WIFI_AUTH_WPA2_WPA3_PSK: return "WPA2/3";
    default: return "?";
  }
}

// Scan only. No credentials are accepted, stored or transmitted: this reports the
// RF path (per-AP RSSI) so the antenna and keep-out can be judged on the bench.
void scanWifi() {
  if (mode != Mode::Passive) { Serial.println("ERR: run stop before wifi scan."); return; }
  Serial.println("Scanning 2.4 GHz Wi-Fi; no credentials are stored...");
  WiFi.mode(WIFI_STA);
  WiFi.disconnect(false, false);
  const int count = WiFi.scanNetworks(false, true, false, 120);
  if (count >= 0) {
    Serial.println("  #   RSSI  ch  security  SSID");
    for (int i = 0; i < count; ++i) {
      String ssid = WiFi.SSID(i);
      if (ssid.length() == 0) ssid = "(hidden)";
      Serial.printf("%3d  %4d  %2d  %-8s  %s\n", i + 1, static_cast<int>(WiFi.RSSI(i)),
        static_cast<int>(WiFi.channel(i)), encryptionName(WiFi.encryptionType(i)), ssid.c_str());
    }
    Serial.printf("Scan completed: %d networks. Zero is not proof of a radio fault.\n", count);
    Serial.println("RSSI is the RF-path evidence: compare a known AP against a phone in the same spot.");
  } else {
    Serial.printf("Scan error: %d\n", count);
  }
  WiFi.scanDelete();
  WiFi.mode(WIFI_OFF);
  Serial.println("Wi-Fi radio powered off again.");
}

void printWifiStatus() {
  const wl_status_t link = WiFi.status();
  if (link != WL_CONNECTED) {
    Serial.printf("Wi-Fi: NOT connected (status=%d)\n", static_cast<int>(link));
    return;
  }
  Serial.printf("Wi-Fi: connected  SSID=\"%s\"  ch=%d  RSSI=%d dBm\n",
    WiFi.SSID().c_str(), static_cast<int>(WiFi.channel()), static_cast<int>(WiFi.RSSI()));
  Serial.printf("IP=%s  mask=%s  gateway=%s  DNS=%s  MAC=%s\n",
    WiFi.localIP().toString().c_str(), WiFi.subnetMask().toString().c_str(),
    WiFi.gatewayIP().toString().c_str(), WiFi.dnsIP().toString().c_str(),
    WiFi.macAddress().c_str());
}

// The passphrase is held in RAM only. WiFi.persistent() defaults to TRUE in
// Arduino-ESP32, which would commit it to NVS flash, so it is switched off
// explicitly here. Nothing about the network is written to persistent storage.
void wifiConnect(const char *ssid, const char *passphrase) {
  if (mode != Mode::Passive) { Serial.println("ERR: run stop before wifi connect."); return; }
  Serial.printf("Joining \"%s\" (passphrase accepted, never echoed or stored)...\n", ssid);
  WiFi.persistent(false);
  WiFi.mode(WIFI_STA);
  const uint32_t start = millis();
  WiFi.begin(ssid, passphrase);
  while (WiFi.status() != WL_CONNECTED && static_cast<uint32_t>(millis() - start) < 20000u) {
    delay(250);
    Serial.print('.');
  }
  Serial.println();
  if (WiFi.status() != WL_CONNECTED) {
    Serial.printf("FAIL: not associated after %lu ms (status=%d). Radio left ON; run wifi disconnect.\n",
      static_cast<unsigned long>(millis() - start), static_cast<int>(WiFi.status()));
    return;
  }
  Serial.printf("CONNECTED in %lu ms\n", static_cast<unsigned long>(millis() - start));
  printWifiStatus();
}

void wifiDisconnect() {
  WiFi.disconnect(true, false);  // radio off; never erase a stored profile
  WiFi.mode(WIFI_OFF);
  Serial.println("Wi-Fi disconnected, radio off. Nothing was written to NVS.");
}

// ICMP is not linked into the Arduino core, and carriers often drop it anyway.
// DNS + TCP + HTTP proves more: name resolution, routing and a real payload.
void netTest() {
  if (WiFi.status() != WL_CONNECTED) { Serial.println("ERR: run wifi connect first."); return; }
  const char *host = "www.baidu.com";
  IPAddress address;
  const uint32_t dnsStart = millis();
  if (!WiFi.hostByName(host, address)) { Serial.printf("FAIL DNS: cannot resolve %s\n", host); return; }
  Serial.printf("PASS DNS: %s -> %s (%lu ms)\n", host, address.toString().c_str(),
    static_cast<unsigned long>(millis() - dnsStart));

  WiFiClient client;
  const uint32_t tcpStart = millis();
  if (!client.connect(address, 80, 5000)) { Serial.println("FAIL TCP: port 80 unreachable"); return; }
  Serial.printf("PASS TCP: port 80 open (%lu ms)\n", static_cast<unsigned long>(millis() - tcpStart));

  client.printf("GET / HTTP/1.0\r\nHost: %s\r\nConnection: close\r\n\r\n", host);
  const uint32_t httpStart = millis();
  const uint32_t deadline = httpStart + 8000u;
  while (!client.available() && static_cast<int32_t>(deadline - millis()) > 0) delay(20);
  if (!client.available()) { Serial.println("FAIL HTTP: no response within 8 s"); client.stop(); return; }
  String statusLine = client.readStringUntil('\n');
  statusLine.trim();
  Serial.printf("PASS HTTP: \"%s\" (%lu ms)\n", statusLine.c_str(),
    static_cast<unsigned long>(millis() - httpStart));
  client.stop();
  Serial.println("RESULT: DNS + TCP + HTTP to www.baidu.com all succeeded.");
}

void drawStaticScreen() {
  display.fillScreen(ST77XX_BLACK);
  display.drawRect(0, 0, display.width(), display.height(), ST77XX_WHITE);
  display.setTextWrap(false);
  display.setTextSize(2);
  display.setTextColor(ST77XX_WHITE);
  display.setCursor(10, 12); display.print("DESKTOP / ST7789");
  const uint16_t colors[] = {ST77XX_RED, ST77XX_GREEN, ST77XX_BLUE, ST77XX_WHITE};
  const char *names[] = {"RED", "GREEN", "BLUE", "WHITE"};
  for (int i = 0; i < 4; ++i) {
    display.fillRect(10 + i * 75, 43, 72, 32, colors[i]);
    display.setTextSize(1); display.setCursor(12 + i * 75, 82); display.print(names[i]);
  }
  display.setCursor(8, 224); display.print("BLK=3.3V | 320x240 | TL->BR");
  display.setCursor(300, 224); display.print("BR");
  shownEncoder = INT32_MIN; controlsDirty = true;
}

void drawControls(uint32_t now) {
  if (mode != Mode::Screen) return;
  const int32_t count = encoderCount();
  if (count != shownEncoder) controlsDirty = true;
  if (!controlsDirty || static_cast<uint32_t>(now - lastDraw) < 80u) return;
  lastDraw = now; controlsDirty = false; shownEncoder = count;
  display.fillRect(8, 110, 305, 102, ST77XX_BLACK);
  display.setTextSize(2); display.setTextColor(ST77XX_CYAN);
  display.setCursor(10, 112); display.printf("ENC: %ld", static_cast<long>(count));
  display.setCursor(10, 140); display.printf("PUSH: %lu %s", static_cast<unsigned long>(pushCount), pushButton.pressed() ? "DOWN" : "UP");
  display.setCursor(10, 168); display.printf("KEY0: %lu %s", static_cast<unsigned long>(keyCount), keyButton.pressed() ? "DOWN" : "UP");
  display.setTextSize(1); display.setTextColor(ST77XX_WHITE);
  display.setCursor(10, 198); display.printf("GPIO: A7 B2 PUSH38 KEY40 / div %u", encoderDivisor);
}

void startScreen() {
  if (mode != Mode::Passive) { Serial.println("ERR: screen start requires PASSIVE; use stop first."); return; }
  Serial.println("Sending ST7789 init. Assumes measured external 3.3 V, USB MCU ON, common GND.");
  makeScreenPassive();
  displaySpi.begin(config::LCD_SCLK, -1, config::LCD_MOSI, config::LCD_CS);
  display.init(config::SCREEN_WIDTH, config::SCREEN_HEIGHT);
  display.setSPISpeed(config::SCREEN_SPI_HZ);
  display.setRotation(rotation);
  display.invertDisplay(inverted);
  drawStaticScreen();
  pushCount = keyCount = 0;
  pushButton.reset(digitalRead(config::ENC_PUSH), millis());
  keyButton.reset(digitalRead(config::KEY0), millis());
  resetEncoder();
  attachInterrupt(config::ENC_A, encoderIsr, CHANGE);
  attachInterrupt(config::ENC_B, encoderIsr, CHANGE);
  mode = Mode::Screen;
  Serial.println("SCREEN active; write-only SPI cannot identify or verify the panel. Check it visually.");
}

uint32_t pulseDuty(uint16_t us) {
  constexpr uint32_t periodUs = 1000000u / config::SERVO_FREQUENCY_HZ;
  return (static_cast<uint32_t>(us) * (1u << config::SERVO_RESOLUTION_BITS) + periodUs / 2u) / periodUs;
}

void armServo() {
  if (mode != Mode::Passive) { Serial.println("ERR: servo arm requires PASSIVE; use stop first."); return; }
  for (int i = 0; i < kServoCount; ++i) {
    const double frequency = ledcSetup(kServoChannels[i], config::SERVO_FREQUENCY_HZ, config::SERVO_RESOLUTION_BITS);
    if (frequency < 49.5 || frequency > 50.5) {
      stopPwmHardware();
      Serial.printf("ERR: 50 Hz LEDC setup failed on servo%d.\n", i);
      return;
    }
  }
  const uint32_t now = millis();
  for (int i = 0; i < kServoCount; ++i) {
    servo[i].arm(now);
    writtenPulse[i] = servo[i].current();
    ledcWrite(kServoChannels[i], pulseDuty(writtenPulse[i]));
    ledcAttachPin(kServoPins[i], kServoChannels[i]);
  }
  pwmAttached = true; mode = Mode::Servo;
  Serial.printf("ARMED: servo0=GPIO%d servo1=GPIO%d, %u us center, %u..%u us range. 10 s timeout. ! = PWM off.\n",
    kServoPins[0], kServoPins[1], config::SERVO_CENTER_US, config::SERVO_MINIMUM_US, config::SERVO_MAXIMUM_US);
}

void serviceServo(uint32_t now) {
  bool expired = false;
  for (int i = 0; i < kServoCount; ++i) expired |= servo[i].tick(now);
  bool armed = false;
  for (int i = 0; i < kServoCount; ++i) armed |= servo[i].armed();
  if (!armed && pwmAttached) {
    stopPwmHardware();
    mode = Mode::Passive;
    Serial.println(expired ? "TIMEOUT: PWM off; servos still have external power." : "PWM off.");
    return;
  }
  if (!pwmAttached) return;
  for (int i = 0; i < kServoCount; ++i) {
    if (servo[i].current() != writtenPulse[i]) {
      writtenPulse[i] = servo[i].current();
      ledcWrite(kServoChannels[i], pulseDuty(writtenPulse[i]));
    }
  }
}

// index < 0 means "every servo"; 0..kServoCount-1 drives a single channel.
void pulseServo(int index, int us) {
  const uint32_t now = millis();
  if (index >= 0 && index < kServoCount) {
    if (!servo[index].setTarget(us, now)) {
      Serial.printf("ERR: servo%d rejected %d us (armed=%d, range %u..%u us).\n",
        index, us, servo[index].armed() ? 1 : 0, config::SERVO_MINIMUM_US, config::SERVO_MAXIMUM_US);
      return;
    }
    Serial.printf("servo%d target %u us  [millis=%lu]\n", index, servo[index].target(),
      static_cast<unsigned long>(now));
    return;
  }
  bool ok = true;
  for (int i = 0; i < kServoCount; ++i) ok &= servo[i].setTarget(us, now);
  if (!ok) {
    Serial.printf("ERR: servo pulse %d rejected (armed=%d, range %u..%u us).\n",
      us, servo[0].armed() ? 1 : 0, config::SERVO_MINIMUM_US, config::SERVO_MAXIMUM_US);
    return;
  }
  Serial.printf("servo0+servo1 target %u us  [millis=%lu]\n", servo[0].target(),
    static_cast<unsigned long>(now));
}

void centerServo() {
  const uint32_t now = millis();
  bool ok = true;
  for (int i = 0; i < kServoCount; ++i) ok &= servo[i].setTarget(config::SERVO_CENTER_US, now);
  Serial.println(ok ? "servo0+servo1 -> center 1500 us" : "ERR: servo center rejected; run servo arm first.");
}

// ---- I²S microphone commands ----
bool micInstall(int bclk, int ws, int sd) {
  i2s_config_t cfg = {};
  cfg.mode = static_cast<i2s_mode_t>(I2S_MODE_MASTER | I2S_MODE_RX);
  cfg.sample_rate = config::MIC_SAMPLE_RATE_HZ;
  cfg.bits_per_sample = I2S_BITS_PER_SAMPLE_32BIT;
  cfg.channel_format = I2S_CHANNEL_FMT_ONLY_LEFT;  // L/R strapped to GND selects the left slot
  // I2S_COMM_FORMAT_STAND_I2S is an enum constant, not a macro, so it cannot be probed
  // with #if defined(). The framework version is pinned in platformio.ini.
  cfg.communication_format = I2S_COMM_FORMAT_STAND_I2S;
  cfg.intr_alloc_flags = ESP_INTR_FLAG_LEVEL1;
  cfg.dma_buf_count = 4;
  cfg.dma_buf_len = 256;
  cfg.use_apll = false;
  cfg.tx_desc_auto_clear = false;
  cfg.fixed_mclk = 0;
  if (i2s_driver_install(kMicPort, &cfg, 0, nullptr) != ESP_OK) return false;
  i2s_pin_config_t pins = {};
  pins.mck_io_num = I2S_PIN_NO_CHANGE;
  pins.bck_io_num = bclk;
  pins.ws_io_num = ws;
  pins.data_out_num = I2S_PIN_NO_CHANGE;
  pins.data_in_num = sd;
  if (i2s_set_pin(kMicPort, &pins) != ESP_OK) { i2s_driver_uninstall(kMicPort); return false; }
  i2s_zero_dma_buffer(kMicPort);
  return true;
}

void micUninstall() {
  if (micReady) { i2s_driver_uninstall(kMicPort); micReady = false; }
}

void micStart(int bclk, int ws) {
  if (mode != Mode::Passive) { Serial.println("ERR: run stop before mic start."); return; }
  micUninstall();
  if (!micInstall(bclk, ws, config::MIC_SD)) {
    Serial.printf("FAIL: I2S RX install on BCLK=%d WS=%d SD=%d.\n", bclk, ws, config::MIC_SD);
    return;
  }
  micBclk = bclk; micWs = ws; micReady = true;
  Serial.printf("MIC active: BCLK=GPIO%d WS=GPIO%d SD=GPIO%d  %lu Hz, %lu-bit slot, data %lu-bit, left channel.\n",
    micBclk, micWs, config::MIC_SD, static_cast<unsigned long>(config::MIC_SAMPLE_RATE_HZ),
    static_cast<unsigned long>(config::MIC_SLOT_BITS), static_cast<unsigned long>(config::MIC_DATA_BITS));
  Serial.println("Bit clock and WS are driven by the ESP32; the module only drives SD. Trim pots do not exist on a digital mic.");
}

void micRead(int milliseconds) {
  if (!micReady) { Serial.println("ERR: run mic start first."); return; }
  const uint32_t rate = config::MIC_SAMPLE_RATE_HZ;
  const uint32_t total = rate * static_cast<uint32_t>(milliseconds) / 1000u;
  const uint32_t blockSamples = rate / 10u;  // one printed line per 100 ms
  Serial.printf("Capturing %lu ms at %lu Hz; one line per 100 ms. dBFS is the AC level with the DC bias removed.\n",
    static_cast<unsigned long>(milliseconds), static_cast<unsigned long>(rate));
  static int32_t raw[512];
  MicStats overall, block;
  uint32_t consumed = 0, printed = 0;
  while (consumed < total) {
    size_t want = total - consumed;
    if (want > 512) want = 512;
    size_t got = 0;
    if (i2s_read(kMicPort, raw, want * sizeof(int32_t), &got, pdMS_TO_TICKS(500)) != ESP_OK || got == 0) {
      Serial.println("FAIL: i2s_read timeout or error.");
      return;
    }
    const size_t count = got / sizeof(int32_t);
    for (size_t i = 0; i < count; ++i) {
      const int32_t value = raw[i] >> kMicShift;
      overall.add(value);
      block.add(value);
    }
    consumed += count;
    while (block.samples >= blockSamples) {
      char bar[40];
      micLevelBar(block.dbfs(), bar, sizeof(bar));
      Serial.printf("  %4lu ms  dc %8.0f  pk-pk %8ld  ac-rms %8.0f  %7.1f dBFS  |%s|\n",
        static_cast<unsigned long>(printed * 100u), block.dc(),
        static_cast<long>(block.maxValue - block.minValue), block.acRms(), block.dbfs(), bar);
      block = MicStats();
      ++printed;
    }
  }
  if (!overall.samples) { Serial.println("FAIL: no samples captured."); return; }
  const double silencePct = 100.0 * overall.silences / overall.samples;
  const double saturatedPct = 100.0 * overall.saturated / overall.samples;
  char bar[40];
  micLevelBar(overall.dbfs(), bar, sizeof(bar));
  Serial.printf("SUMMARY %lu samples  dc %.0f  ac-rms %.0f  %.1f dBFS  (24-bit full scale %ld)\n",
    static_cast<unsigned long>(overall.samples), overall.dc(), overall.acRms(),
    overall.dbfs(), static_cast<long>(kMicFullScale));
  Serial.printf("all-zero %.1f%%  all-ones %.1f%%  bar: |%s|\n", silencePct, saturatedPct, bar);
  if (silencePct > 50.0 || saturatedPct > 50.0) {
    Serial.println("VERDICT: the data line looks stuck at a constant value, not a quiet room.");
    Serial.println("  Check: L/R tied to GND, SD on GPIO6, VDD 3.3 V, and the module silkscreen order.");
    Serial.println("  If SCK and WS were read off the wrong silkscreen, run mic swap and read again.");
  } else if (overall.dbfs() < -80.0) {
    Serial.println("VERDICT: frames are arriving, but everything is near the noise floor.");
    Serial.println("  Tap the desk or speak 20 cm away and re-read; a digital mic with no clock would read all-zero.");
  } else {
    Serial.println("VERDICT: real signal above the noise floor; the I2S path is alive.");
  }
}

void micSwap() {
  if (mode != Mode::Passive) { Serial.println("ERR: run stop before mic swap."); return; }
  const int bclk = micWs, ws = micBclk;
  Serial.printf("Re-installing with BCLK=GPIO%d WS=GPIO%d (exchanged).\n", bclk, ws);
  micStart(bclk, ws);
  Serial.println("Compare 'mic read 1000' against the previous wiring; keep whichever gives real signal.");
}

void execute(const Command &command) {
  switch (command.kind) {
    case CommandKind::Empty: return;
    case CommandKind::Help: printHelp(); return;
    case CommandKind::Status: printStatus(); return;
    case CommandKind::Selftest: selftest(); return;
    case CommandKind::WifiScan: scanWifi(); return;
    case CommandKind::WifiConnect: wifiConnect(command.text1, command.text2); return;
    case CommandKind::WifiStatus: printWifiStatus(); return;
    case CommandKind::WifiDisconnect: wifiDisconnect(); return;
    case CommandKind::NetTest: netTest(); return;
    case CommandKind::Stop: stopAll(); return;
    case CommandKind::ScreenStart: startScreen(); return;
    case CommandKind::ServoArm: armServo(); return;
    case CommandKind::ScreenStop:
      stopScreen(); Serial.println("Screen signal pins high-Z; backlight supply is not switched."); return;
    case CommandKind::ServoStop:
      for (int i = 0; i < kServoCount; ++i) servo[i].stop();
      stopPwmHardware();
      if (mode == Mode::Servo) mode = Mode::Passive;
      Serial.println("Servo PWM off; power is not switched."); return;
    case CommandKind::ServoPulse:
      if (mode != Mode::Servo) { Serial.println("ERR: arm first (servo arm)."); return; }
      pulseServo(command.index, command.value);
      return;
    case CommandKind::ServoCenter:
      if (mode != Mode::Servo) { Serial.println("ERR: arm first (servo arm)."); return; }
      centerServo();
      return;
    case CommandKind::MicStart: micStart(config::MIC_BCLK, config::MIC_WS); return;
    case CommandKind::MicRead: micRead(command.value > 0 ? command.value : 1000); return;
    case CommandKind::MicSwap: micSwap(); return;
    case CommandKind::MicStop:
      micUninstall();
      Serial.println("I2S port released; BCLK/WS/SD back to high-Z. The module is still powered.");
      return;
    case CommandKind::ScreenRotation:
    case CommandKind::ScreenInvert:
    case CommandKind::EncoderDivisor:
      if (mode != Mode::Screen) { Serial.println("ERR: start screen first."); return; }
      if (command.kind == CommandKind::ScreenRotation) { rotation = command.value; display.setRotation(rotation); drawStaticScreen(); }
      else if (command.kind == CommandKind::ScreenInvert) { inverted = command.value != 0; display.invertDisplay(inverted); }
      else { encoderDivisor = command.value; resetEncoder(); }
      printStatus(); return;
    default: Serial.println("ERR: invalid command. Type help."); return;
  }
}

void serviceSerial() {
  // Bound work per loop so malformed or continuous serial input cannot starve timeout handling.
  for (int n = 0; n < 64 && Serial.available(); ++n) {
    const char c = static_cast<char>(Serial.read());
    if (c == '!') { serialLine.clear(); stopAll(); continue; }
    const LineEvent event = serialLine.push(c);
    if (event == LineEvent::Ready) execute(parseCommand(serialLine.line()));
    else if (event == LineEvent::Overflow) Serial.println("ERR: overlong line discarded; nothing executed.");
  }
}
} // namespace

void setup() {
  makeScreenPassive();
  stopPwmHardware();
  pinMode(config::LED_GPIO, OUTPUT); setLed(false);
  pinMode(config::BOOT_GPIO, INPUT_PULLUP);
  bootButton.reset(digitalRead(config::BOOT_GPIO), millis());
  Serial.begin(115200);
  delay(200);
  printHelp();
  Serial.println("READY / PASSIVE: no display init; no servo PWM. Type selftest.");
}

void loop() {
  serviceServo(millis());
  serviceSerial();
  const uint32_t now = millis();
  serviceServo(now);
  if (static_cast<uint32_t>(now - lastLed) >= 100u) { lastLed = now; setLed(now % 1000u < 100u); }
  if (bootButton.update(digitalRead(config::BOOT_GPIO), now)) {
    ++bootCount; Serial.printf("BOOT press %lu\n", static_cast<unsigned long>(bootCount));
  }
  if (mode == Mode::Screen) {
    const bool oldPush = pushButton.pressed(), oldKey = keyButton.pressed();
    if (pushButton.update(digitalRead(config::ENC_PUSH), now)) { ++pushCount; controlsDirty = true; }
    if (keyButton.update(digitalRead(config::KEY0), now)) { ++keyCount; controlsDirty = true; }
    if (oldPush != pushButton.pressed() || oldKey != keyButton.pressed()) controlsDirty = true;
    drawControls(now);
  }
  delay(1);
}
