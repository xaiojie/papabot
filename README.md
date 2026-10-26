# 爬爬 · PapaBot

**一只从桌面表情屏开始，逐步学会倾听、回应和行走的 ESP32-S3 四足小机器人。**

[![Host checks: 318 passed](https://img.shields.io/badge/host_checks-318_passed-2ea44f?style=flat&logo=github&logoColor=white)](#验证)
[![MCU: ESP32-S3](https://img.shields.io/badge/MCU-ESP32--S3-E7352C?style=flat&logo=espressif&logoColor=white)](firmware/README.md)
[![C++17](https://img.shields.io/badge/C%2B%2B-17-00599C?style=flat&logo=cplusplus&logoColor=white)](firmware/assistant/platformio.ini)
[![Build: PlatformIO](https://img.shields.io/badge/build-PlatformIO-F5822A?style=flat&logo=platformio&logoColor=white)](#快速开始)
[![Stage: prototype](https://img.shields.io/badge/stage-prototype-0f766e?style=flat)](#当前进度)
[![License: MIT](https://img.shields.io/badge/license-MIT-44337A?style=flat)](LICENSE)

[项目进度](项目进度总览.md) · [开发与调试](docs/guides/开发与调试.md) · [PCB 设计](pcb-design/README.md) · [结构设计](mechanical-design/README.md) · [BOM 与选型](hardware-selection/README.md) · [第三方资料](docs/references/README.md)

![爬爬 A5 整机模型渲染](docs/images/a5-hero.jpg)

*图为 A5 宽体短机身方案的 Blender 渲染。机身宽 × 深 × 高为 124 × 112 × 76 mm；含耳朵和脚垫的当前站姿外形为 162.9 × 116.5 × 122.46 mm。实物打印与整机装配尚待验证。*

## 关于爬爬

PapaBot 是一个持续开发的桌面陪伴机器人项目。它用彩屏显示表情、时钟、天气和动画，通过 Wi-Fi 与网页控制台交互；后续将接入语音对话和四足运动。

仓库收录应用固件、硬件自检工具、网页控制台、PCB 工程与制造文件、结构打印件、BOM 和参考资料，记录从模块台架到集成整机的过程。

- **看得见的交互**：中文显示、表情、数字时钟、指针表盘、天气、账号额度和系统状态；6 个固定页面加 3 部 GIF 动画，共 9 页。
- **浏览器控制**：切换页面、改变表情、读取设备状态、查看远程画面，通过 WebSocket 中转连接设备。
- **分步联调**：`bringup` 用于验证接线与外设，`assistant` 负责界面、联网和应用逻辑。
- **完整设计资料**：保留 PCB 版本、结构迭代和选型依据，方便查阅、复现与继续开发。

## 当前进度

**当前处于桌面原型与模块联调阶段。** 已有屏幕、联网和双舵机台架验证记录，语音与四足整机仍在开发。

| 模块 | 已有成果 | 下一步 |
|---|---|---|
| 显示与联网 | 旧 TOUGLESY ST7789 屏幕上的中文、表情、信息页和动画；Wi-Fi、NTP、天气与额度接口 | 新 HS24S010B 屏幕点亮与固件适配 |
| 网页控制台 | 切屏、换表情、状态回传与远程画面已有联调记录 | 配网体验、多设备与持续稳定性 |
| 舵机运动 | GPIO18 / GPIO15 双路 PWM 台架验证 | PCA9685 八路驱动、关节标定、单腿与四足步态 |
| 集成 PCB | V1.2 五页原理图、110 × 75 mm 双层板、79 个器件；已有原生 DRC 与导出核验记录 | 打样、焊接、充电及供电负载实测 |
| 结构外壳 | A5 CAD 试装版，31 个独立打印件及静态检查记录 | 关键件打印、线束避让、装配与承重验证 |
| 语音与电池 | 音频器件、2S 电池及充电方案已选型 | 语音闭环、整机温升与续航测试 |

**版本边界：** 现有固件和实机记录主要对应带 EC11 的旧屏台架；新版 HS24S010B 集成方案已移除 EC11，仍需完成适配。硬件验证记录来自 **2026 年 9 月**；本页于 **2026-10-26** 整理，并重跑本地主机测试，未重新上电验收。

逐项证据见 [项目进度总览](项目进度总览.md)，各设计版本从下方入口查阅。

## 快速开始

以下示例适用于 macOS / Linux，需 Python 3.9+；仅运行本地主机测试时还需支持 C++17 的编译器。固件目标板为 **LCKFB-ESP32S3R8N8（8 MB Flash + 8 MB Octal PSRAM）**。

```bash
git clone https://github.com/xaiojie/papabot.git
cd papabot

# 安装隔离的 PlatformIO 6.1.18 环境
bash firmware/bringup/scripts/setup.sh

# 编译应用固件：原生 USB-Serial/JTAG 控制台
env -u PYTHONPATH firmware/bringup/.venv/bin/pio run \
  --project-dir firmware/assistant -e lckfb_s3_usbjtag
```

首次接线建议先使用自检工程：

```bash
env -u PYTHONPATH firmware/bringup/.venv/bin/pio run \
  --project-dir firmware/bringup -e lckfb_s3_usbjtag
```

确认接线后，在对应编译命令末尾添加 `-t upload --upload-port /dev/cu.usbmodemXXXX` 即可烧录；替换为实际端口，串口速率为 **115200**。使用 CH340 串口时，环境改为 `lckfb_s3_assistant` 或 `lckfb_s3_bringup`。

- [开发与调试手册](docs/guides/开发与调试.md)：安装、烧录、旧屏台架引脚、串口命令和故障排查。
- [应用固件配置](firmware/assistant/include/config.h)：页面、屏幕、刷新周期与当前双路舵机设置。
- [网页控制台部署](firmware/web-console/部署记录.md)：Node.js 20+ 中转服务、前端与 HTTPS/WSS 配置。账号、密码和设备密钥在本地环境中设置。

## 硬件与结构

| 项目 | 当前方案 |
|---|---|
| 主控 | ESP32-S3，8 MB Flash + 8 MB Octal PSRAM |
| 新版显示 | HS24S010B，2.4″、240 × 320 RGB、SPI、单排 2.54 mm 10PIN；独立安装，通过线束连接主板，无旋钮 |
| 运动 | 计划 8 个 MG90S、每腿 2 个关节；当前仅有双舵机台架记录，实物型号与角度须逐个核对 |
| 音频 | INMP441 数字麦克风、MAX98357A 功放与扬声器；完整链路待实现 |
| 电池与充电 | ACE800 2S 7.4 V 电池；设计链路为 PCB J6 USB-C 5 V → IP2326 → 8.4 V 充电 |
| 集成主板 | V1.2，110 × 75 mm、2 层；保留用户 2026-09-13 最新丝印修改 |
| 当前结构 | A5 宽体短机身、屏幕近齐平、后盖 USB-C 开孔；实际接口配合仍需试装 |

[最新版 PCB 核对与备份](pcb-design/integrated-v1/user-latest-review-2026-09-13/核对结论.md) · [V1.2 装配与接线](pcb-design/integrated-v1/final-no-encoder-2026-09-12/装配与接线说明.md) · [A5 装配与打印](mechanical-design/structure-a5/README.md) · [最新 BOM 总表](hardware-selection/procurement/2026-09-12/最新BOM总表.md)

A5 之后讨论的 [前后连续圆角外观](mechanical-design/concept-rounded-body-20260915/外观与结构方案.md) 仍是概念方案，尚未写入当前模型与 STL。PCB 检查、CAD 检查和效果图各有适用范围，实体装配与运行结果会继续补充。

## 仓库导航

```text
papabot/
├── firmware/             应用固件、自检工程与网页控制台
├── pcb-design/           原理图、PCB、Gerber 与版本核对
├── mechanical-design/    结构版本、STL、渲染与试装资料
├── hardware-selection/   器件选型、采购记录与 BOM
├── design-coordination/  PCB / 结构接口与 EDA Bridge
├── docs/                 开发手册、参考资料索引与历史记录
├── scripts/              仓库检查工具
└── 项目进度总览.md        进度与验证证据入口
```

| 你想做什么 | 从这里开始 |
|---|---|
| 跑通开发板与屏幕 | [固件导航](firmware/README.md) · [自检工程](firmware/bringup/README.md) · [台架接线配置](firmware/bringup/wiring.json) |
| 修改页面与交互 | [应用固件说明](firmware/assistant/README.md) · [开发与调试手册](docs/guides/开发与调试.md) |
| 查看 PCB 或结构版本 | [PCB 导航](pcb-design/README.md) · [结构导航](mechanical-design/README.md) |
| 核对物料与供应商资料 | [选型与采购](hardware-selection/README.md) · [第三方资料索引](docs/references/README.md) |
| 了解目录与接口约定 | [仓库结构说明](docs/仓库结构.md) · [设计协同](design-coordination/README.md) |

第三方规格书、参考图与供应商资料已纳入 Git；[资料清单](docs/references/资料清单.json) 记录 **107 份文件**的路径、大小和 SHA-256，便于校验。缓存、依赖、凭据、原生 `.blend` 大文件与重复试装包的收录规则见仓库结构说明。

## 接下来

- [ ] 完成 HS24S010B 实屏适配，验证无旋钮版交互。
- [ ] 核对实物型号，完成关节标定、单腿联调和 PCA9685 八路驱动。
- [ ] 接通麦克风 → ASR → 对话 → TTS → 扬声器。
- [ ] 验证集成板充电、保护、负载压降与温升。
- [ ] 打印关键试配件，完成整机装配、四足步态与续航验收。

## 验证

```bash
python3 firmware/bringup/scripts/test_host.py
python3 firmware/assistant/scripts/test_host.py
python3 scripts/check_repository.py
```

**2026-10-26 本地结果：** `bringup` 16 组 / 293 项，`assistant` 5 组 / 25 项，合计 **318 项检查、0 失败**。首页 `host checks` 徽章是这一结果的静态快照，当前未配置 GitHub Actions 自动更新。

测试覆盖命令解析、按键与编码器逻辑、舵机限幅与超时、脏矩形和 SPI 预算；仓库检查覆盖入口链接、误收录文件与第三方资料哈希。语音、供电、步态和实体装配需要各自的硬件验收。

## 许可

本项目自有代码与设计文件采用 [MIT License](LICENSE)。第三方资料与依赖保留原作者或厂商的版权和许可，详见 [第三方资料索引](docs/references/README.md)。

当前 `cjk*.bin` 字模来源于 macOS 自带字体，再分发许可尚未确认；对外再分发前请替换为思源黑体 / Noto Sans CJK 等允许再分发的字体，并保留其许可文件。
