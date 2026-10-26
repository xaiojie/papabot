// 桌面助手应用固件 · 板级与界面配置
// 引脚与 RevB 载板保持一致（见 pcb-design/native-rev-b/载板接口与引脚.csv）
#pragma once
#include <cstdint>

namespace cfg {

// ---------------- 屏幕（RevB J3 + J7）----------------
constexpr int PIN_LCD_SCLK = 12;
constexpr int PIN_LCD_MOSI = 11;
constexpr int PIN_LCD_RST  = 21;
constexpr int PIN_LCD_DC   = 14;
constexpr int PIN_LCD_CS   = 13;
// BLK 在载板上固定接 3.3V，没有软件调光。

constexpr int SCREEN_W = 320;
constexpr int SCREEN_H = 240;
// 面板的「原生」尺寸 —— 必须是竖屏 240x320。
// Adafruit_ST7789::init() 的参数是面板原生分辨率，传成横屏的 320x240 会让
// setRotation() 把 _width/_height 算反，并且 colstart/rowstart 算出
// (-40, 40) 的偏移：实测后果是画面整体转 90°，且地址窗口回绕，
// 一部分屏幕永远刷不到，残留旧画面。
constexpr int  PANEL_NATIVE_W = 240;
constexpr int  PANEL_NATIVE_H = 320;

constexpr int  SCREEN_ROTATION = 3;   // 横屏
// 面板反色。实测这块 TOUGLESY 模组必须为 false：
// 设成 true 会变成白底暗红（黑↔白、青↔红全对调）。
constexpr bool SCREEN_INVERT = false;

// 10 MHz 是 bench-v1 已验证过的保守值。提到 40 MHz 可把全屏刷新从 8 fps 提到 33 fps，
// 但需要实物确认时序稳定后再改。这里留成运行期可调，方便实测对比。
constexpr uint32_t SPI_HZ_DEFAULT = 10'000'000;
constexpr uint32_t SPI_HZ_MAX     = 40'000'000;

// ---------------- 控件 ----------------
constexpr int PIN_ENC_A    = 7;
constexpr int PIN_ENC_B    = 2;
constexpr int PIN_ENC_PUSH = 38;
constexpr int PIN_KEY0     = 40;

constexpr uint32_t ENCODER_TRANSITIONS_PER_DETENT = 4;
// 两次计数之间的最小间隔。机械编码器触点抖动都在 1 ms 内，手拧远慢于此。
// 太小挡不住噪声，太大限制快速拧动 —— 2 ms 对应最快 500 步/秒，够用。
constexpr uint32_t ENCODER_MIN_GAP_US = 2000;

// ---------------- 舵机 ----------------
// 2026-09-11：首测的 1400–1600µs 限幅（约 ±9°，实测行程仅 18°）**已放开**到全行程。
// 放开前已在 1400–1600 范围内确认舵机能正常往复，且负载为空载。
//
// 500–2400µs 是 MG90S 这一档舵机的通用全行程规格（50 Hz）。注意：
//   · 若舵机在某一端持续"嗡嗡"响（堵转），说明该端已到机械硬限位，
//     应立即把该端的值往中间收（例如改成 600/2350），不要硬顶着跑。
//   · 堵转电流是稳态的数倍，会发热烧线圈/崩齿轮，还可能拉低 5V 把主控带复位。
//   · 三重保护仍在：斜率限制 5µs/20ms、10 秒无指令自动松力。
// 将来装上腿以后，每个关节应各自标定实际可用范围，不要直接沿用全行程。
// 板载绿色 LED。脱离 USB 独立供电时，这是判断"主控到底在不在跑"的唯一手段 ——
// 之前 assistant 固件没管它，所以拔掉 USB 后既没串口也没灯，完全瞎猜。
constexpr int  PIN_LED        = 48;
constexpr bool LED_ACTIVE_LOW = true;
constexpr uint32_t LED_HEARTBEAT_MS = 1000;   // 1 Hz：活着

// ---------------- 舵机（多路）----------------
// 引脚按顺序对应舵机编号 0 / 1 / 2 ……
//   [0] GPIO18  右列 R8   面包板阶段就在用的那个
//   [1] GPIO15  右列 R5   第二路（2026-09-14 加）
//   [2] GPIO16  右列 R6   预留，要加第三路时取消注释
//
// 选 GPIO15/16 的原因：都在右列、挨着、空闲、非 strapping 脚、
// 不被 Octal PSRAM(GPIO33-37) 和原生 USB(GPIO19/20) 占用。
// ESP32-S3 任意 GPIO 都能做 LEDC PWM。
//
// 加一路的步骤：① 这里改 SERVO_COUNT 和数组 ② 别的不用动。
constexpr int SERVO_COUNT = 2;
constexpr int SERVO_PINS[SERVO_COUNT] = {18, 15};

constexpr uint32_t SERVO_FREQ_HZ      = 50;
constexpr uint32_t SERVO_RES_BITS     = 14;      // 20000µs / 16384 = 1.22µs 一步，够用
constexpr uint16_t SERVO_CENTER_US    = 1500;
// 1000–2000µs = 完整 0°–180°。
// 500/2400 是理论全行程，但对 SG90 来说两端已是机械死区 —— 顶死会堵转发热，
// 几十秒就能扫齿/烧线圈。200µs 余量足够覆盖舵机个体差异。
constexpr uint16_t SERVO_MIN_US       = 1000;
constexpr uint16_t SERVO_MAX_US       = 2000;
constexpr uint32_t SERVO_SLEW_STEP_US = 5;       // 每 20 ms 最多走 5µs，约 15°/s
constexpr uint32_t SERVO_SLEW_INTERVAL_MS = 20;
constexpr uint32_t SERVO_TIMEOUT_MS   = 10000;   // 10 秒没指令就松力
constexpr uint32_t BUTTON_DEBOUNCE_MS = 30;
constexpr uint32_t LONG_PRESS_MS      = 700;   // 长按阈值

// ---------------- 配色（与设计稿 A 奶油薄荷 的屏幕语言一致）----------------
constexpr uint16_t rgb565(uint8_t r, uint8_t g, uint8_t b) {
  return static_cast<uint16_t>(((r & 0xF8u) << 8) | ((g & 0xFCu) << 3) | (b >> 3));
}
constexpr uint16_t C_BG        = rgb565(0x00, 0x00, 0x00);  // 屏幕底色：黑
constexpr uint16_t C_EYE       = rgb565(0x6a, 0xd4, 0xe8);  // 主青色（眼睛/刻度/主数值）
constexpr uint16_t C_EYE_SOFT  = rgb565(0x8f, 0xe3, 0xf2);  // 次青色
constexpr uint16_t C_DIM       = rgb565(0x4b, 0x8f, 0x9c);  // 弱化文字
constexpr uint16_t C_TEXT      = rgb565(0xcf, 0xe3, 0xd8);  // 正文
constexpr uint16_t C_STATUSBAR = rgb565(0x0e, 0x1a, 0x20);  // 状态条底
constexpr uint16_t C_TICK_DIM  = rgb565(0x3d, 0x6b, 0x75);  // 分刻度
constexpr uint16_t C_RING      = rgb565(0x2b, 0x4a, 0x52);  // 表盘外圈
constexpr uint16_t C_SECOND    = rgb565(0xff, 0x8a, 0x6a);  // 秒针
constexpr uint16_t C_BAR_BG    = rgb565(0x1b, 0x2b, 0x31);  // 进度条底

// ---------------- 表情几何（对齐概念图的比例）----------------
// 眼：两条竖向胶囊；嘴：弧线；下方一行字。全部几何图形，无需位图素材。
constexpr int FACE_EYE_DX     = 52;   // 双眼中心相对屏幕中心的水平偏移
constexpr int FACE_EYE_CY     = 98;   // 眼睛中心 y
constexpr int FACE_EYE_W      = 36;
constexpr int FACE_EYE_H      = 64;
constexpr int FACE_MOUTH_CY   = 138;  // 嘴弧圆心 y（上移过，避免压到文字）
constexpr int FACE_MOUTH_R    = 36;
constexpr int FACE_TEXT_Y     = 196;

// ---------------- 表盘几何 ----------------
constexpr int ANALOG_CX = 160;
constexpr int ANALOG_CY = 116;
constexpr int ANALOG_R  = 74;

// ---------------- 默认配置（可被 NVS 覆盖）----------------
constexpr const char *DEFAULT_NICKNAME = "爬爬";
constexpr const char *DEFAULT_CITY     = "长沙 · 岳麓区";
// 和风天气：API Host 与 Key 不入库，运行时通过 config 命令写入 NVS。
constexpr const char *DEFAULT_QW_HOST  = "";   // 形如 xxxxxxxx.re.qweatherapi.com
constexpr const char *DEFAULT_QW_KEY   = "";
constexpr const char *DEFAULT_QW_LOC   = "101250109";  // 岳麓区（长沙），实测由 GeoAPI 查出

constexpr const char *NTP_SERVER_1 = "ntp.aliyun.com";
constexpr const char *NTP_SERVER_2 = "cn.pool.ntp.org";
constexpr long        TZ_OFFSET_S  = 8 * 3600;   // CST-8

// 天气刷新间隔：和风免费版有日调用上限，别刷太勤
constexpr uint32_t WEATHER_REFRESH_MS = 20u * 60u * 1000u;
// 额度（sub2api）刷新间隔。
// 2026-09-11：10 分钟 → 5 分钟。额度变化比天气频繁，10 分钟太钝；
// 5 分钟 = 每天 288 次请求，对自建 sub2api 完全没压力。
// 想立刻刷新也可以发 `quota` 命令（网页上有「刷新额度」按钮）。
constexpr uint32_t QUOTA_REFRESH_MS   = 5u * 60u * 1000u;
// 拉取失败后的重试间隔 —— 没有它的话断网开机就永远停在空状态
constexpr uint32_t NET_RETRY_MS       = 60u * 1000u;

}  // namespace cfg
