# 桌面助手开发测试工程 · bench-v1

本工程用于到货后的三个阶段：**主控自检 → 屏幕与控件 → 单个 MG90S**。不用定制 PCB。先打开 [图文接线页面](docs/index.html)，完整操作与供电顺序见 [开发测试接线与验收](docs/开发测试接线与验收.md)。

配件：立创 ESP32S3R8N8（8 MB Flash / 8 MB OPI PSRAM）、TOUGLESY 2.4 寸 ST7789+EC11 原板、MG90S 180° × 1。屏幕 VCC / BLK 用外部稳压 **3.3V**；主控用电脑 USB；单舵机另用外部 **5V**。屏幕和舵机按单通道电源分开测试。

这是可编译的模块测试程序，未连接、未烧录任何实物，实测记录留空。没有完整语音助手、中文显示界面或步态功能；现在先把硬件接口测通。当前结果见 [验证记录](docs/验证记录.md)。

## 文件入口

| 文件 | 用途 |
|---|---|
| [docs/index.html](docs/index.html) | 离线接线页面，三个测试页签，可点击突出接线、打印 |
| [docs/屏幕12针接线表.csv](docs/屏幕12针接线表.csv) | 逐针接线和开发板位置 |
| [docs/开发测试接线与验收.md](docs/开发测试接线与验收.md) | 焊接、限流、上电顺序、故障排查 |
| [docs/通电前自检与故障对照.md](docs/通电前自检与故障对照.md) | 上电前的电学自检、红线、故障对照表、到货当天时间线 |
| [docs/screen-simulator.html](docs/screen-simulator.html) | **屏幕没到货时在浏览器里预览**：像素级复刻固件绘制 + 虚拟旋钮/按键 + 中文排版草图 |
| [scripts/preflight_check.py](scripts/preflight_check.py) | 通电前自检向导；`--rehearse` 预演、`--ports` 查串口、`--from N` 续跑 |
| [docs/实机验收记录.csv](docs/实机验收记录.csv) | 到货后填写的实测记录 |
| [platformio.ini](platformio.ini) | 已固定版本的编译配置 |
| [src/main.cpp](src/main.cpp) | 主控、屏幕、串口和舵机硬件驱动 |
| [include/control_logic.h](include/control_logic.h) | 消抖、编码器、脉宽范围/超时、命令解析 |
| [wiring.json](wiring.json) | 统一接线数据；生成固件引脚、CSV 与 SVG |
| [artifacts/firmware](artifacts/firmware) | 编译后的烧录文件和地址/哈希清单 |

## 本机编译

在终端进入本文件所在目录。当前工作区已安装隔离的 PlatformIO，直接执行：

```sh
python3 scripts/generate_wiring.py
python3 scripts/test_host.py
bash scripts/pio.sh run
```

下载的独立副本如未安装 PlatformIO，先运行 `bash scripts/setup.sh`。首次需要联网下载工具链；无需管理员权限。也可在 VS Code 的 PlatformIO 中打开本文件夹编译。

工具链已确认可在本机从零重建：2026-09-10 清空 `.pio/build` 后重新编译通过（9.3 秒），主机测试 12 组 / 203 项断言 0 失败。硬件到货前也可先做通电前预演：

```sh
python3 scripts/preflight_check.py --rehearse   # 走完全部 8 阶段，不接硬件、不写记录
python3 scripts/preflight_check.py --ports      # 查当前候选串口
```

到货当天把 `--rehearse` 换成不带参数，就是逐项自检向导；安全门禁不通过会停下并给出处置办法，不会让你带着短路继续上电。

固定配置：PlatformIO Core 6.1.18；espressif32 6.12.0；Arduino-ESP32 2.0.17；Adafruit ST7735/ST7789 1.11.0、GFX 1.11.11、BusIO 1.17.0。基于 `esp32-s3-devkitc-1`，显式选择 8 MB Flash、`qio_opi` 和 `BOARD_HAS_PSRAM`。

两个控制台环境，引脚、驱动和接线校验完全相同：

| 环境 | `Serial` 走向 | 说明 |
|---|---|---|
| `lckfb_s3_bringup`（默认） | UART0 → 板载 CH340K | 交付包与验证记录按此配置生成；需要 macOS 的 CH34x 驱动 |
| `lckfb_s3_usbjtag` | USB-Serial/JTAG（原生 USB 口） | **不需要装任何驱动**；不跑 `export_firmware.py`，不会覆盖已验证产物 |

**2026-09-10 实机结论：macOS 不带 CH34x 驱动。** CH340（`1A86:7523`）在 USB 总线上枚举成功但不生成 `/dev` 节点；实测改走板载原生 USB（`303A:1001` → `/dev/cu.usbmodem*`），烧录与双向串口均通过。**当前推荐 `lckfb_s3_usbjtag`。**

编译结束的导出脚本从 PlatformIO 实际构建配置取得地址，将必要的四个镜像和 SHA-256 写入 `artifacts/firmware/flash-manifest.json`。单独的 `firmware.bin` 不是完整的首次烧录包；优先让 PlatformIO 自动烧录配套文件。

## 到货后的烧录步骤

先跑 `python3 scripts/preflight_check.py` 完成断电电学自检（尤其屏幕 VCC↔GND 短路检查），再开始烧录。

1. **只连接裸开发板 USB**，屏幕、舵机、外部电源均断开。
2. `bash scripts/pio.sh device list` 查看串口。macOS 上优先选原生 USB 口 `/dev/cu.usbmodem*`（`303A:1001`），配 `-e lckfb_s3_usbjtag`；若已装好 CH34x 驱动，也可选 `/dev/cu.wchusbserial*` 配默认环境。一个 Type-C 口经板载 USB HUB 同时接出这两路，**不要凭列表顺序选**。
3. 把下面的 `实际串口` 换成真实路径，执行：

```sh
# 推荐：原生 USB 口，不需要装驱动
bash scripts/pio.sh run -e lckfb_s3_usbjtag --target upload --upload-port 实际串口
bash scripts/pio.sh device monitor -e lckfb_s3_usbjtag --port 实际串口 --baud 115200

# 或：装好 CH34x 驱动后走 CH340（默认环境）
bash scripts/pio.sh run -e lckfb_s3_bringup --target upload --upload-port 实际串口
```

4. 如停在连接阶段，按住 BOOT、按一下 RESET，再松开 BOOT进入下载模式后重试。烧录结束按 RESET 正常启动；不要一直按住 BOOT。
5. 输入 `help` / `selftest`。串口发送设置为换行或 CRLF。退出 PlatformIO 串口监视器可按 `Ctrl+C`；再次烧录前关闭监视器。

2026-09-10 已在 USB-JTAG 环境实机烧录并跑通主控自检、Wi-Fi 扫描/连接/联网测试；未执行 `erase_flash`。

## 串口命令

| 命令 | 行为 |
|---|---|
| `help` / `status` | 帮助、模式、存储器和输入状态 |
| `selftest` | 仅待机：芯片/Flash/PSRAM信息、64 KiB PSRAM样本测试 |
| `wifi scan` | 仅待机：2.4 GHz扫描，逐AP打印RSSI/信道/加密方式，结束关闭Wi-Fi，不保存账号密码 |
| `wifi connect SSID 密码` | 仅待机：一次性联通测试。**凭据只存RAM、绝不写NVS**（已调 `WiFi.persistent(false)`），口令不回显；SSID支持UTF-8中文名 |
| `wifi status` | 当前链路的 IP / 网关 / DNS / RSSI；未连接时显示状态码 |
| `wifi disconnect` | 断开并关闭射频，不删除任何已存配置 |
| `net test` | 需先连接：对 www.baidu.com 依次做 DNS → TCP:80 → HTTP GET，逐项打印耗时 |
| `screen start` | 仅待机：按 ST7789 初始化屏幕，再显示色条/控件计数 |
| `screen rotation 1` / `screen rotation 3` | 两个横屏方向；默认 3 |
| `screen invert 0` / `screen invert 1` | 切换反色设置；默认 1，按实物颜色判断 |
| `encoder divisor 2` / `encoder divisor 4` | 调整每计数的合法相位跃迁数，同时清零；默认 4 |
| `screen stop` | 释放屏幕信号脚；背光仍由外部3.3V供电 |
| `servo arm` | 仅待机：开始输出 1500μs；初始可能直接回中位 |
| `servo pulse 1450` 等 | 仅启用状态：范围1400–1600μs，后续每20ms最多变化5μs |
| `servo stop` | 停发PWM；不切断5V |
| `stop` 或 `!` | 全部回待机；`!` 不用回车 |

舵机频率50Hz，使用ESP32-S3支持的14位LEDC分辨率。10秒无有效脉宽命令会停发PWM；`status`、无效参数不会延长超时。不开机自动扫角，也不按“0–180°”映射未校准的脉宽。这个保守小范围不能代替机械限位和带载测试。

屏幕没有MISO回读，所以程序只能发出初始化命令，**不能自动判定屏幕接上、点亮或颜色正确**。控件使用模块现有10k上拉；固件不额外打开内部上拉。显示默认240×320初始化、rotation=3后320×240，初始化与刷新SPI均设置10MHz。BLK固定3.3V，因此没有软件调光。

## 与整机版本的关系

- 屏幕9路信号和两路3.3V供电定义与RevB保持一致；引脚生成器会与工程中的原始接口表核对，独立压缩包则使用所附参考快照。
- GPIO18是本轮无PCB的单舵机临时脚，在RevB上原本未连接。最终八舵机用PCA9685，不把这根临时线视为PCB改动。
- 开发板两边20P、屏幕12P排针朝向及高度仍需实物和外壳试配。旋钮和独立按键留在完整屏幕原板上。
- 软件待机只是启动后的GPIO状态，不提供硬件掉电隔离。必须遵守USB先上、屏幕后上；屏幕先断、USB后断的受控步骤。
